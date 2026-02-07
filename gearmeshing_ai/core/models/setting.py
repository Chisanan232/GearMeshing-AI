from typing import Optional

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


# =====================================================================
# MCP (Model Context Protocol) Configuration Models
# =====================================================================


class MCPGatewayConfig(BaseModel):
    """MCP Gateway configuration."""

    url: str = Field(default="http://mcp-gateway:4444", description="MCP Gateway base URL")
    token: Optional[SecretStr] = Field(default=None, description="MCP Gateway authentication token")
    db_url: SecretStr = Field(
        default=SecretStr("postgresql+psycopg://ai_dev:changeme@postgres:5432/ai_dev"),
        description="MCP Gateway PostgreSQL database URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", description="MCP Gateway Redis connection URL")
    admin_password: SecretStr = Field(default=SecretStr("adminpass"), description="MCP Gateway admin password")
    admin_email: str = Field(default="admin@example.com", description="MCP Gateway admin email address")
    admin_full_name: str = Field(default="Admin User", description="MCP Gateway admin full name")
    jwt_secret: SecretStr = Field(
        default=SecretStr("my-test-key"), description="MCP Gateway JWT secret key for token signing"
    )

    model_config = ConfigDict(strict=False)


class MCPConfig(BaseModel):
    """MCP (Model Context Protocol) configuration container."""

    gateway: MCPGatewayConfig = Field(default_factory=MCPGatewayConfig, description="MCP Gateway configuration")

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

    # =====================================================================
    # MCP Configuration for Tests
    # =====================================================================
    mcp: MCPConfig = Field(
        default_factory=MCPConfig,
        description="MCP configuration (Slack, ClickUp, GitHub, Gateway)",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

settings = AIProviderSettings()
