from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from .settings import AgentSettings


class AgentAdapter(ABC):
    """Abstract base class for AI agent framework adapters.
    
    Implementations should wrap specific frameworks like Pydantic AI, phidata, etc.
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
