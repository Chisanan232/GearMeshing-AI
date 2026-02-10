from collections.abc import AsyncIterator

from gearmeshing_ai.agent.abstraction.env_manager import EnvManager
from gearmeshing_ai.agent.abstraction.factory import AgentFactory
from gearmeshing_ai.agent.abstraction.settings import AgentSettings, ModelSettings
from gearmeshing_ai.agent.adapters.pydantic_ai import PydanticAIAdapter
from gearmeshing_ai.core.utils.logging_config import get_logger

logger = get_logger(__name__)


class AgentCLIService:
    """Service to handle the core logic of running agents from the CLI."""

    def __init__(self):
        self.env_manager = EnvManager()
        self.adapter = PydanticAIAdapter()
        self.factory = AgentFactory(adapter=self.adapter)

    def validate_environment(self, provider: str) -> bool:
        """Validates if the environment is ready for the specified provider."""
        return self.env_manager.validate_provider_keys(provider)

    def prepare_environment(self) -> None:
        """Exports environment variables for the adapter."""
        self.env_manager.export_variables()

    async def initialize_agent(self, agent_id: str, provider: str, model: str) -> None:
        """Registers settings and initializes the agent configuration."""
        # 1. Register Model Settings
        model_settings = ModelSettings(customized_name=f"cli-{provider}-{model}", provider=provider, model=model)
        self.factory.register_model_settings(model_settings)

        # 2. Register Agent Settings
        # In a real scenario, we might load this from a DB or file.
        # For CLI ad-hoc run, we create a default one if not exists or overwrite.
        agent_settings = AgentSettings(
            role=agent_id,
            description="CLI Agent",
            model_settings=model_settings,
            system_prompt="You are a helpful AI assistant running in a CLI environment.",
        )
        self.factory.register_agent_settings(agent_settings)

        # Ensure agent can be created (warmup)
        await self.factory.get_or_create_agent(agent_id)

    async def run_chat_stream(self, agent_id: str, message: str) -> AsyncIterator[str]:
        """Run the agent with a message and return a stream of response chunks."""
        agent = await self.factory.get_or_create_agent(agent_id)
        async for chunk in self.adapter.run_stream(agent, message):
            yield chunk

    def list_agents(self, status: str | None, limit: int) -> list[dict]:
        """List agents based on status and limit."""
        # TODO: Implement actual listing from cache or storage
        return [{"id": "placeholder", "status": "unknown"}]

    def create_agent(self, name: str, model: str, description: str | None, config_file: str | None) -> dict:
        """Create a new agent configuration."""
        # TODO: Implement actual creation persistence
        return {
            "name": name,
            "model": model,
            "description": description,
            "config_file": config_file,
            "status": "created",
        }

    def stop_agent(self, agent_id: str, force: bool) -> bool:
        """Stop a running agent."""
        # TODO: Implement actual stop logic
        return True

    def get_agent_status(self, agent_id: str, detailed: bool) -> dict:
        """Retrieve the status of an agent."""
        # TODO: Implement actual status retrieval
        return {"id": agent_id, "status": "idle", "detailed_info": {} if detailed else None}

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent configuration."""
        # TODO: Implement actual deletion logic
        return True
