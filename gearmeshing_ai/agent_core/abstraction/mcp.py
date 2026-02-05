from abc import ABC, abstractmethod
from typing import Any


class MCPClientAbstraction(ABC):
    """Abstract base class for an MCP (Model Context Protocol) Client.
    This abstraction allows the AgentFactory to fetch tools without knowing the implementation details.
    """

    @abstractmethod
    async def get_tools(self, tool_names: list[str]) -> list[Any]:
        """Fetches tool implementations based on their names.

        Args:
            tool_names: A list of strings identifying the requested tools.

        Returns:
            A list of tool objects compatible with the agent framework
            (or generic objects that the adapter can convert).

        """
        pass
