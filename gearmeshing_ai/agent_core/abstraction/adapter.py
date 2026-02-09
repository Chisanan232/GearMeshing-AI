from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from .settings import AgentSettings


class AgentAdapter(ABC):
    """Abstract base class for AI agent framework adapters.

    Implementations should wrap specific frameworks like Pydantic AI, phidata, etc.
    Enhanced with tool registration capabilities.
    """

    @abstractmethod
    def create_agent(self, settings: AgentSettings, tools: list[Any]) -> Any:
        """Create and return the specific framework agent instance.

        Args:
            settings: The comprehensive settings for the agent.
            tools: A list of instantiated tool objects (format depends on the specific framework,
                   but usually the adapter handles the conversion if generic tools are passed).

        Returns:
            An instance of the agent in the specific framework.

        """
        pass

    @abstractmethod
    async def run(self, agent: Any, prompt: str, **kwargs: Any) -> Any:
        """Run the agent with a prompt.

        Args:
            agent: The agent instance created by create_agent.
            prompt: The input prompt/query.
            **kwargs: Additional arguments for execution.

        Returns:
            The response from the agent.

        """
        pass

    @abstractmethod
    async def run_stream(self, agent: Any, prompt: str, **kwargs: Any) -> AsyncGenerator[str, None]:
        """Run the agent with a prompt in streaming mode.

        Args:
            agent: The agent instance created by create_agent.
            prompt: The input prompt/query.
            **kwargs: Additional arguments for execution.

        Returns:
            An asynchronous iterator yielding response chunks.

        """
        pass

    def _register_tools(self, agent: Any) -> None:
        """Template method to register all available tools with the agent.

        This method calls all protected tool registration methods in sequence.
        Subclasses can override to customize tool registration behavior.

        Args:
            agent: The framework-specific agent instance

        """
        # Register file operation tools
        self._register_file_tools(agent)

        # Register command execution tools
        self._register_command_tools(agent)

        # Future tool categories can be added here
        self._register_system_tools(agent)

    def _register_file_tools(self, agent: Any) -> None:
        """Register file operation tools (read, write, list) with the agent.

        Default implementation calls specific file tool registration methods.
        Subclasses should override to implement framework-specific registration.
        """
        self._register_tool_read_file(agent)
        self._register_tool_write_file(agent)
        self._register_tool_list_files(agent)

    def _register_command_tools(self, agent: Any) -> None:
        """Register command execution tools with the agent.

        Default implementation calls specific command tool registration methods.
        Subclasses should override to implement framework-specific registration.
        """
        self._register_tool_run_command(agent)

    def _register_system_tools(self, agent: Any) -> None:
        """Register system-level tools (environment, process, etc.) with the agent.

        Placeholder for future system tool implementations.
        Subclasses should override to implement framework-specific registration.
        """
        pass

    # Protected tool-specific registration methods
    def _register_tool_read_file(self, agent: Any) -> None:
        """Register read_file tool with the agent.

        Subclasses MUST implement this method for their specific framework.
        """
        raise NotImplementedError

    def _register_tool_write_file(self, agent: Any) -> None:
        """Register write_file tool with the agent.

        Subclasses MUST implement this method for their specific framework.
        """
        raise NotImplementedError

    def _register_tool_list_files(self, agent: Any) -> None:
        """Register list_files tool with the agent.

        Subclasses MUST implement this method for their specific framework.
        """
        raise NotImplementedError

    def _register_tool_run_command(self, agent: Any) -> None:
        """Register run_command tool with the agent.

        Subclasses MUST implement this method for their specific framework.
        """
        raise NotImplementedError
