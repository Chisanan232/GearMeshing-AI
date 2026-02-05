from typing import Any, List, Optional, AsyncIterator
import asyncio

# pydantic_ai imports
from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.gemini import GeminiModel

from ..abstraction.adapter import AgentAdapter
from ..abstraction.settings import AgentSettings

class PydanticAIAdapter(AgentAdapter):
    """
    Adapter implementation for Pydantic AI framework.
    """

    def _get_model(self, provider: str, model_name: str) -> Any:
        """Factory for Pydantic AI models."""
        provider = provider.lower()
        if provider == "openai":
            return OpenAIModel(model_name)
        elif provider == "anthropic":
            return AnthropicModel(model_name)
        elif provider in ["google", "gemini"]:
            return GeminiModel(model_name)
        else:
            # Fallback or default to string which Pydantic AI might handle or fail
            return f"{provider}:{model_name}"

    def create_agent(self, settings: AgentSettings, tools: List[Any]) -> Any:
        """
        Creates a Pydantic AI Agent instance.
        """
        model_instance = self._get_model(
            settings.model_settings.provider, 
            settings.model_settings.model
        )
        
        # Pydantic AI Agent initialization
        agent = PydanticAgent(
            model=model_instance,
            system_prompt=settings.system_prompt,
            # tools=tools # TODO: Map MCP tools to Pydantic AI tools if necessary
        )
        
        # Attach metadata or settings to the agent instance if needed for debugging
        return agent

    async def run(self, agent: Any, prompt: str, **kwargs) -> Any:
        """
        Runs the Pydantic AI agent.
        """
        if not isinstance(agent, PydanticAgent):
             raise ValueError("Agent must be an instance of pydantic_ai.Agent")

        result = await agent.run(prompt)
        return result.output

    async def run_stream(self, agent: Any, prompt: str, **kwargs) -> AsyncIterator[str]:
        """
        Runs the Pydantic AI agent in streaming mode.
        """
        if not isinstance(agent, PydanticAgent):
             raise ValueError("Agent must be an instance of pydantic_ai.Agent")

        async with agent.run_stream(prompt) as result:
            async for message in result.stream_text():
                yield message
