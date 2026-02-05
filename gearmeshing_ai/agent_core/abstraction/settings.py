from typing import Any

from pydantic import BaseModel, Field, SecretStr


class ModelSettings(BaseModel):
    """Settings for a specific AI model configuration.
    
    Keyed by 'customized_name' in the factory.
    """

    customized_name: str = Field(..., description="Unique name for this model configuration")
    provider: str = Field(..., description="The provider name (e.g., openai, anthropic)")
    model: str = Field(..., description="The specific model identifier (e.g., gpt-4, claude-3-opus)")
    api_key: SecretStr | None = Field(None, description="API Key for the provider")
    api_base: str | None = Field(None, description="Base URL for the API")
    temperature: float = Field(0.7, description="Sampling temperature")
    max_tokens: int | None = Field(None, description="Maximum tokens to generate")
    additional_params: dict[str, Any] = Field(default_factory=dict, description="Provider specific parameters")


class AgentSettings(BaseModel):
    """Settings for an AI agent.
    
    Keyed by 'role' in the factory.
    """

    role: str = Field(..., description="Unique role identifier for the agent")
    description: str = Field(..., description="Description of the agent's purpose")
    model_settings: ModelSettings = Field(..., description="Configuration for the underlying model")
    tools: list[str] = Field(default_factory=list, description="List of tool names/identifiers this agent can use")
    system_prompt: str | None = Field(None, description="System prompt to initialize the agent context")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata for the agent")
