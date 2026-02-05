from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAIConfig(BaseModel):
    """OpenAI configuration settings."""

    api_key: SecretStr | None = Field(None, description="OpenAI API key")
    model: str = Field("gpt-4o", description="Default OpenAI model")
    temperature: float = Field(0.7, description="Sampling temperature")
    max_tokens: int | None = Field(None, description="Maximum tokens to generate")

    model_config = ConfigDict(strict=False)


class AnthropicConfig(BaseModel):
    """Anthropic configuration settings."""

    api_key: SecretStr | None = Field(None, description="Anthropic API key")
    model: str = Field("claude-3-5-sonnet-20241022", description="Default Anthropic model")
    temperature: float = Field(0.7, description="Sampling temperature")
    max_tokens: int | None = Field(None, description="Maximum tokens to generate")

    model_config = ConfigDict(strict=False)


class GeminiConfig(BaseModel):
    """Google Gemini configuration settings."""

    api_key: SecretStr | None = Field(None, description="Google Gemini API key")
    model: str = Field("gemini-1.5-pro", description="Default Gemini model")
    temperature: float = Field(0.7, description="Sampling temperature")
    max_tokens: int | None = Field(None, description="Maximum tokens to generate")

    model_config = ConfigDict(strict=False)


class AIProviderConfig(BaseModel):
    """AI provider configuration container."""

    openai: OpenAIConfig = Field(default_factory=OpenAIConfig, description="OpenAI configuration")
    anthropic: AnthropicConfig = Field(default_factory=AnthropicConfig, description="Anthropic configuration")
    gemini: GeminiConfig = Field(default_factory=GeminiConfig, description="Google Gemini configuration")

    model_config = ConfigDict(strict=False)


class AIProviderSettings(BaseSettings):
    """Settings for AI Model Providers (OpenAI, Anthropic, etc.).

    Uses nested structure with double underscore delimiter.
    Environment variables should be formatted as:
    - AI_PROVIDER__OPENAI__API_KEY
    - AI_PROVIDER__ANTHROPIC__API_KEY
    - AI_PROVIDER__GEMINI__API_KEY

    Usage:
    - settings.ai_provider.openai.api_key
    - settings.ai_provider.anthropic.model
    - settings.ai_provider.gemini.temperature
    """

    # AI Provider configurations (nested)
    ai_provider: AIProviderConfig = Field(default_factory=AIProviderConfig, description="AI provider configurations")

    # Common settings
    default_provider: str = Field("openai", description="Default AI provider to use")
    default_model: str = Field("gpt-4o", description="Default model to use")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )
