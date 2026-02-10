from abc import ABC, abstractmethod
from typing import Any

from ..models.actions import MCPToolCatalog


class MCPClientAbstraction(ABC):
    """Abstract base class for an MCP (Model Context Protocol) Client.

    This abstraction allows the AgentFactory to fetch tools without knowing the implementation details.
    """

    # Optional attributes for testing/mock implementations
    error_rate: float = 0.0
    request_history: list[dict[str, Any]] = []  # noqa: RUF012

    @abstractmethod
    async def get_tools(self, tool_names: list[str]) -> list[Any]:
        """Fetch tool implementations based on their names.

        Args:
            tool_names: A list of strings identifying the requested tools.

        Returns:
            A list of tool objects compatible with the agent framework
            (or generic objects that the adapter can convert).

        """
        pass

    # NEW METHODS FOR PROPOSAL-ONLY AGENTS
    @abstractmethod
    async def discover_tools_for_agent(self) -> MCPToolCatalog:
        """Discover all available tools and return tool info for LLM understanding.

        Returns:
            MCPToolCatalog with tool information formatted for agent consumption.

        """
        pass

    @abstractmethod
    async def execute_proposed_tool(self, tool_name: str, parameters: dict) -> dict:
        """Execute a tool by name (system execution of agent proposal).

        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool execution

        Returns:
            Execution result with success/error information

        """
        pass
