from typing import Any

from .adapter import AgentAdapter
from .cache import AgentCache
from .mcp import MCPClientAbstraction
from .settings import AgentSettings, ModelSettings


class AgentFactory:
    """Factory class for creating and managing AI agents.
    Handles settings management, tool retrieval via MCP, and caching.
    """

    def __init__(self, adapter: AgentAdapter, mcp_client: MCPClientAbstraction | None = None):
        self.adapter = adapter
        self.mcp_client = mcp_client
        self.cache = AgentCache()

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

    async def get_or_create_agent(self, role: str, override_settings: dict[str, Any] | None = None) -> Any:
        """Retrieves an agent from cache or creates a new one.

        Args:
            role: The role identifier for the agent.
            override_settings: Optional dictionary to override registered settings (not used if cached).

        Returns:
            The instantiated agent object.

        Raises:
            ValueError: If settings for the role are not found.

        """
        # check cache first
        cached_agent = self.cache.get(role)
        if cached_agent and not override_settings:
            return cached_agent

        # Retrieve settings
        agent_settings = self.get_agent_settings(role)
        if not agent_settings:
            # If not in registry, maybe we can construct it or fail
            # For now, let's assume it must be registered or we'd need to pass full settings object
            raise ValueError(f"No agent settings registered for role: {role}")

        # Apply overrides if needed (simple shallow merge for now)
        if override_settings:
            # This is a bit complex with Pydantic, might need copy update
            agent_settings = agent_settings.model_copy(update=override_settings)

        # Get tools
        tools = []
        if self.mcp_client and agent_settings.tools:
            tools = await self.mcp_client.get_tools(agent_settings.tools)

        # Create agent via adapter
        agent = self.adapter.create_agent(agent_settings, tools)

        # Cache the agent
        self.cache.set(role, agent)

        return agent
