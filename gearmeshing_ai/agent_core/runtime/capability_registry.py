"""Capability Registry for managing available tools and capabilities.

This module implements the Capability Registry that manages tool discovery,
filtering, and context-aware capability selection for agent workflows.
"""

import logging
from typing import Any

from gearmeshing_ai.agent_core.abstraction.mcp import MCPClientAbstraction
from gearmeshing_ai.agent_core.models.actions import MCPToolCatalog, MCPToolInfo

from .models import ExecutionContext, WorkflowState

logger = logging.getLogger(__name__)


class CapabilityRegistry:
    """Registry for managing available capabilities and tools.

    This class manages tool discovery from MCP servers, capability filtering,
    and context-aware capability selection for agent workflows.

    Attributes:
        mcp_client: MCP client for discovering tools
        _catalog_cache: Cached tool catalog
        _filtered_capabilities: Cached filtered capabilities

    """

    def __init__(self, mcp_client: MCPClientAbstraction) -> None:
        """Initialize the Capability Registry.

        Args:
            mcp_client: MCP client for tool discovery

        """
        self.mcp_client = mcp_client
        self._catalog_cache: MCPToolCatalog | None = None
        self._filtered_capabilities: dict[str, list[MCPToolInfo]] = {}
        logger.debug("CapabilityRegistry initialized")

    async def discover_capabilities(self) -> MCPToolCatalog:
        """Discover available capabilities from MCP servers.

        Returns:
            MCPToolCatalog containing all available tools

        Raises:
            RuntimeError: If capability discovery fails

        """
        logger.info("Discovering capabilities from MCP servers")

        try:
            # Discover tools from MCP client
            catalog = await self.mcp_client.discover_tools_for_agent()

            # Cache the catalog
            self._catalog_cache = catalog
            logger.info(f"Discovered {len(catalog.tools)} capabilities")

            return catalog

        except Exception as e:
            logger.error(f"Failed to discover capabilities: {e}")
            raise RuntimeError(f"Capability discovery failed: {e}") from e

    async def get_all_capabilities(self) -> MCPToolCatalog:
        """Get all available capabilities.

        Returns cached catalog if available, otherwise discovers new capabilities.

        Returns:
            MCPToolCatalog containing all available tools

        """
        if self._catalog_cache is not None:
            logger.debug("Returning cached capabilities")
            return self._catalog_cache

        return await self.discover_capabilities()

    async def filter_capabilities(
        self,
        context: ExecutionContext,
        capability_filter: dict[str, Any] | None = None,
    ) -> list[MCPToolInfo]:
        """Filter capabilities based on execution context.

        Args:
            context: Execution context for filtering
            capability_filter: Optional custom filter criteria

        Returns:
            List of filtered MCPToolInfo objects

        """
        logger.debug(f"Filtering capabilities for context: agent_role={context.agent_role}")

        try:
            # Get all capabilities
            catalog = await self.get_all_capabilities()

            # Apply context-based filtering
            filtered_tools: list[MCPToolInfo] = []

            for tool in catalog.tools:
                if self._matches_context(tool, context, capability_filter):
                    filtered_tools.append(tool)

            logger.info(f"Filtered to {len(filtered_tools)} capabilities for role={context.agent_role}")

            # Cache filtered results
            self._filtered_capabilities[context.agent_role] = filtered_tools

            return filtered_tools

        except Exception as e:
            logger.error(f"Failed to filter capabilities: {e}")
            return []

    def _matches_context(
        self,
        tool: MCPToolInfo,
        context: ExecutionContext,
        custom_filter: dict[str, Any] | None = None,
    ) -> bool:
        """Check if a tool matches the execution context.

        Args:
            tool: Tool to check
            context: Execution context
            custom_filter: Optional custom filter criteria

        Returns:
            True if tool matches context, False otherwise

        """
        # Basic context matching - can be extended with policies
        # For now, all tools are available to all roles
        if custom_filter:
            # Apply custom filter if provided
            if "excluded_tools" in custom_filter:
                if tool.name in custom_filter["excluded_tools"]:
                    return False

            if "required_tags" in custom_filter:
                tool_tags = set(tool.tags or [])
                required_tags = set(custom_filter["required_tags"])
                if not required_tags.issubset(tool_tags):
                    return False

        return True

    async def update_workflow_state(
        self,
        state: WorkflowState,
    ) -> WorkflowState:
        """Update workflow state with available capabilities.

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state with available_capabilities

        """
        logger.debug(f"Updating workflow state with capabilities for run_id={state.run_id}")

        try:
            # Get filtered capabilities for the agent role
            filtered_tools = await self.filter_capabilities(state.context)

            # Create catalog with filtered tools
            filtered_catalog = MCPToolCatalog(tools=filtered_tools)

            # Update state with available capabilities
            updated_state = state.model_copy(update={"available_capabilities": filtered_catalog})

            logger.info(f"Updated workflow state with {len(filtered_tools)} capabilities")

            return updated_state

        except Exception as e:
            logger.error(f"Failed to update workflow state with capabilities: {e}")
            return state

    def clear_cache(self) -> None:
        """Clear cached capabilities.

        This is useful when capabilities change or for testing.

        """
        logger.debug("Clearing capability cache")
        self._catalog_cache = None
        self._filtered_capabilities.clear()

    def get_capability_by_name(self, name: str) -> MCPToolInfo | None:
        """Get a specific capability by name.

        Args:
            name: Name of the capability

        Returns:
            MCPToolInfo if found, None otherwise

        """
        if self._catalog_cache is None:
            logger.warning("Catalog not cached, cannot get capability by name")
            return None

        for tool in self._catalog_cache.tools:
            if tool.name == name:
                return tool

        return None
