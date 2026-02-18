from typing import Any

import logging

from ..models.actions import MCPToolCatalog
from .adapter import AgentAdapter
from .cache import AgentCache
from .mcp import MCPClientAbstraction
from .settings import AgentSettings, ModelSettings


logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory class for creating and managing AI agents.

    Handles settings management, tool retrieval via MCP, and caching.
    Enhanced to support proposal-only agents.
    """

    def __init__(
        self, adapter: AgentAdapter, mcp_client: MCPClientAbstraction | None = None, proposal_mode: bool = False
    ):
        self.adapter = adapter
        self.mcp_client = mcp_client
        self.proposal_mode = proposal_mode
        self.cache = AgentCache()
        self._tool_catalog: MCPToolCatalog | None = None

        # In-memory storage for settings templates
        self._agent_settings_registry: dict[str, AgentSettings] = {}
        self._model_settings_registry: dict[str, ModelSettings] = {}

    def register_agent_settings(self, settings: AgentSettings) -> None:
        """Register an agent configuration using its role as the key."""
        self._agent_settings_registry[settings.role] = settings

    def register_model_settings(self, settings: ModelSettings) -> None:
        """Register a model configuration using its customized_name as the key."""
        self._model_settings_registry[settings.customized_name] = settings

    def get_agent_settings(self, role: str) -> AgentSettings | None:
        return self._agent_settings_registry.get(role)

    def get_model_settings(self, customized_name: str) -> ModelSettings | None:
        return self._model_settings_registry.get(customized_name)

    async def initialize_proposal_mode(self):
        """Initialize proposal mode with tool discovery.
        
        In proposal mode, tool discovery is optional - if MCP servers are not available,
        the agent will still work but without access to external tools.
        """
        if self.proposal_mode and self.mcp_client:
            logger.info("Initializing proposal mode - attempting MCP tool discovery")
            try:
                self._tool_catalog = await self.mcp_client.discover_tools_for_agent()
                logger.info(f"Discovered {len(self._tool_catalog.tools) if self._tool_catalog else 0} MCP tools")
            except Exception as e:
                logger.warning(f"MCP tool discovery failed (continuing without tools): {e!s}")
                # In proposal mode, tool discovery is optional - create empty catalog
                from gearmeshing_ai.agent.models.actions import MCPToolCatalog
                self._tool_catalog = MCPToolCatalog(tools=[])
                logger.debug("Created empty tool catalog for proposal mode")

            # Update adapter with tool catalog if it's a proposal adapter
            if hasattr(self.adapter, "tool_catalog"):
                self.adapter.tool_catalog = self._tool_catalog
                logger.debug("Updated adapter with tool catalog")
        else:
            logger.debug("Proposal mode not enabled or no MCP client available")

    async def get_or_create_agent(self, role: str, override_settings: dict[str, Any] | None = None) -> Any:
        """Retrieve an agent from cache or create a new one.
        Enhanced to support proposal-only mode.
        """
        # For proposal mode, check if we need to initialize
        if self.proposal_mode and not self._tool_catalog:
            await self.initialize_proposal_mode()

        # check cache first
        cache_key = f"{role}_proposal" if self.proposal_mode else role
        cached_agent = self.cache.get(cache_key)
        if cached_agent and not override_settings:
            return cached_agent

        # Retrieve settings
        agent_settings = self.get_agent_settings(role)
        if not agent_settings:
            # If not in registry, maybe we can construct it or fail
            # For now, let's assume it must be registered or we'd need to pass full settings object
            msg = f"No agent settings registered for role: {role}"
            raise ValueError(msg)

        # Apply overrides if needed
        if override_settings:
            # This is a bit complex with Pydantic, might need copy update
            agent_settings = agent_settings.model_copy(update=override_settings)

        # Get tools (only for traditional mode)
        tools = []
        if not self.proposal_mode and self.mcp_client and agent_settings.tools:
            tools = await self.mcp_client.get_tools(agent_settings.tools)

        # Create agent via adapter
        agent = self.adapter.create_agent(agent_settings, tools)

        # Cache the agent
        self.cache.set(cache_key, agent)

        return agent

    async def execute_proposal(self, action: str, parameters: dict) -> dict:
        """Execute a proposal using MCP client."""
        if not self.proposal_mode or not self.mcp_client:
            raise ValueError("Proposal mode not enabled or MCP client not available")

        return await self.mcp_client.execute_proposed_tool(action, parameters)

    async def run_proposal_task(self, role: str, task: str, context: dict = None) -> dict:
        """Run a complete proposal task: get proposal + execute."""
        # Create proposal-only agent
        agent = await self.get_or_create_agent(role)

        # Get proposal from agent
        proposal = await self.adapter.run(agent, task, context=context or {})

        # Execute the proposal
        result = await self.execute_proposal(proposal.action, proposal.parameters or {})

        return {"proposal": proposal.dict(), "execution": result}
