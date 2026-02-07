"""
Test settings model for GearMeshing-AI smoke tests.

This module provides a Pydantic-based settings model specifically for testing,
with environment variable loading from a test-specific .env file.
"""

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from gearmeshing_ai.core.models.setting import MCPConfig as BaseMCPConfig


class TestOpenAIConfig(BaseModel):
    """Test OpenAI configuration settings."""

    api_key: SecretStr | None = Field(None, description="OpenAI API key")
    model: str = Field("gpt-4", description="Default OpenAI test model")
    temperature: float = Field(0.7, description="Sampling temperature")
    max_tokens: int = Field(1000, description="Maximum tokens to generate")

    model_config = ConfigDict(strict=False)


class TestAnthropicConfig(BaseModel):
    """Test Anthropic configuration settings."""

    api_key: SecretStr | None = Field(None, description="Anthropic API key")
    model: str = Field("claude-3-sonnet-20240229", description="Default Anthropic test model")
    temperature: float = Field(0.7, description="Sampling temperature")
    max_tokens: int = Field(1000, description="Maximum tokens to generate")

    model_config = ConfigDict(strict=False)


class TestGeminiConfig(BaseModel):
    """Test Google Gemini configuration settings."""

    api_key: SecretStr | None = Field(None, description="Google Gemini API key")
    model: str = Field("gemini-pro", description="Default Gemini test model")
    temperature: float = Field(0.7, description="Sampling temperature")
    max_tokens: int = Field(1000, description="Maximum tokens to generate")

    model_config = ConfigDict(strict=False)


class TestXAIConfig(BaseModel):
    """Test xAI (Grok) configuration settings."""

    api_key: SecretStr | None = Field(None, description="xAI API key")
    model: str = Field("grok-beta", description="Default xAI test model")
    temperature: float = Field(0.7, description="Sampling temperature")
    max_tokens: int = Field(1000, description="Maximum tokens to generate")

    model_config = ConfigDict(strict=False)


class TestClickUpServerConfig(BaseModel):
    """Test ClickUp MCP server configuration settings."""

    server_host: str = Field("0.0.0.0", description="ClickUp MCP server host")
    server_port: str = Field("8082", description="ClickUp MCP server port")
    mcp_transport: str = Field("sse", description="MCP transport method")
    api_token: SecretStr | None = Field(SecretStr("your-clickup-api-token"), description="ClickUp API token")
    mq_backend: str = Field("redis", description="Message queue backend for ClickUp MCP server")

    model_config = ConfigDict(strict=False)


class TestGitHubServerConfig(BaseModel):
    """Test GitHub MCP server configuration settings."""

    token: SecretStr | None = Field(None, description="GitHub personal access token")
    toolsets: str = Field("all", description="GitHub toolsets to use")
    default_repo: str | None = Field(None, description="Default GitHub repository")

    model_config = ConfigDict(strict=False)


class TestAtlassianServerConfig(BaseModel):
    """Test Atlassian/Jira MCP server configuration settings."""

    base_url: str | None = Field(None, description="Atlassian base URL")
    email: str | None = Field(None, description="Atlassian email")
    api_token: SecretStr | None = Field(None, description="Atlassian API token")

    model_config = ConfigDict(strict=False)


class TestGrafanaServerConfig(BaseModel):
    """Test Grafana MCP server configuration settings."""

    url: str | None = Field(None, description="Grafana URL")
    api_token: SecretStr | None = Field(None, description="Grafana API token")

    model_config = ConfigDict(strict=False)


class TestLokiServerConfig(BaseModel):
    """Test Loki MCP server configuration settings."""

    url: str | None = Field(None, description="Loki URL")
    api_token: SecretStr | None = Field(None, description="Loki API token")

    model_config = ConfigDict(strict=False)


class TestSlackServerConfig(BaseModel):
    """Test Slack MCP server configuration settings."""

    host: str = Field("0.0.0", description="Slack MCP server host")
    port: str = Field("8081", description="Slack MCP server port")
    mcp_transport: str = Field("sse", description="MCP transport method")
    bot_token: SecretStr | None = Field(None, description="Slack bot token")
    bot_id: str | None = Field(None, description="Slack bot ID")
    app_id: str | None = Field(None, description="Slack app ID")
    user_token: SecretStr | None = Field(None, description="Slack user token")
    signing_secret: SecretStr | None = Field(None, description="Slack signing secret")
    mq_backend: str = Field("redis", description="Message queue backend for Slack MCP server")

    model_config = ConfigDict(strict=False)


class TestMCPServerConfig(BaseModel):
    """Test MCP server configurations container."""

    slack: TestSlackServerConfig = Field(
        default_factory=TestSlackServerConfig, description="Slack MCP server configuration"
    )
    clickup: TestClickUpServerConfig = Field(
        default_factory=TestClickUpServerConfig, description="ClickUp MCP server configuration"
    )
    github: TestGitHubServerConfig = Field(
        default_factory=TestGitHubServerConfig, description="GitHub MCP server configuration"
    )
    atlassian: TestAtlassianServerConfig = Field(
        default_factory=TestAtlassianServerConfig, description="Atlassian MCP server configuration"
    )
    grafana: TestGrafanaServerConfig = Field(
        default_factory=TestGrafanaServerConfig, description="Grafana MCP server configuration"
    )
    loki: TestLokiServerConfig = Field(
        default_factory=TestLokiServerConfig, description="Loki MCP server configuration"
    )

    model_config = ConfigDict(strict=False)


class TestMCPConfig(BaseMCPConfig):
    """Test MCP configuration with server support."""

    server: TestMCPServerConfig | None = Field(None, description="MCP server configurations")

    model_config = ConfigDict(strict=False)


class TestModelSettings(BaseModel):
    """Test settings for a specific AI model configuration."""

    customized_name: str = Field(..., description="Unique name for this model configuration")
    provider: str = Field(..., description="The provider name (e.g., openai, anthropic)")
    model: str = Field(..., description="The specific model identifier (e.g., gpt-4, claude-3-opus)")
    api_key: SecretStr | None = Field(None, description="API Key for the provider")
    api_base: str | None = Field(None, description="Base URL for the API")
    temperature: float = Field(0.7, description="Sampling temperature")
    max_tokens: int | None = Field(None, description="Maximum tokens to generate")
    additional_params: dict[str, Any] = Field(default_factory=dict, description="Provider specific parameters")

    model_config = ConfigDict(strict=False)


class TestAgentSettings(BaseModel):
    """Test settings for an AI agent."""

    role: str = Field(..., description="Unique role identifier for the agent")
    description: str = Field(..., description="Description of the agent's purpose")
    model_settings: TestModelSettings = Field(..., description="Configuration for the underlying model")
    tools: list[str] = Field(default_factory=list, description="List of tool names/identifiers this agent can use")
    system_prompt: str | None = Field(None, description="System prompt to initialize the agent context")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata for the agent")

    model_config = ConfigDict(strict=False)


class AIProviderConfig(BaseModel):
    """AI provider configuration container for tests."""

    openai: TestOpenAIConfig = Field(default_factory=TestOpenAIConfig, description="OpenAI test configuration")
    anthropic: TestAnthropicConfig = Field(
        default_factory=TestAnthropicConfig, description="Anthropic test configuration"
    )
    gemini: TestGeminiConfig = Field(default_factory=TestGeminiConfig, description="Gemini test configuration")
    xai: TestXAIConfig = Field(default_factory=TestXAIConfig, description="xAI test configuration")

    model_config = ConfigDict(strict=False)


class TestSettings(BaseSettings):
    """Main test settings container for GearMeshing-AI tests.

    Uses nested structure with double underscore delimiter.
    Environment variables should be formatted as:
    - AI_PROVIDER__OPENAI__API_KEY
    - AI_PROVIDER__ANTHROPIC__API_KEY
    - AI_PROVIDER__GEMINI__API_KEY
    - AI_PROVIDER__XAI__API_KEY
    - MCP__GATEWAY__JWT_SECRET
    - MCP__GATEWAY__ADMIN_EMAIL
    - MCP__GATEWAY__ADMIN_PASSWORD
    - MCP__GATEWAY__ADMIN_FULL_NAME
    - MCP__GATEWAY__URL
    - MCP__GATEWAY__TOKEN
    - MCP__GATEWAY__DB_URL
    - MCP__GATEWAY__REDIS_URL
    - MCP__SERVER__SLACK__HOST
    - MCP__SERVER__SLACK__PORT
    - MCP__SERVER__SLACK__MCP_TRANSPORT
    - MCP__SERVER__SLACK__BOT_TOKEN
    - MCP__SERVER__SLACK__BOT_ID
    - MCP__SERVER__SLACK__APP_ID
    - MCP__SERVER__SLACK__USER_TOKEN
    - MCP__SERVER__SLACK__SIGNING_SECRET
    - MCP__SERVER__SLACK__MQ_BACKEND
    - MCP__SERVER__CLICKUP__SERVER_HOST
    - MCP__SERVER__CLICKUP__SERVER_PORT
    - MCP__SERVER__CLICKUP__MCP_TRANSPORT
    - MCP__SERVER__CLICKUP__API_TOKEN
    - MCP__SERVER__CLICKUP__MQ_BACKEND
    - MCP__SERVER__GITHUB__TOKEN
    - MCP__SERVER__GITHUB__TOOLSETS
    - MCP__SERVER__GITHUB__DEFAULT_REPO
    - MCP__SERVER__ATLASSIAN__BASE_URL
    - MCP__SERVER__ATLASSIAN__EMAIL
    - MCP__SERVER__ATLASSIAN__API_TOKEN
    - MCP__SERVER__GRAFANA__URL
    - MCP__SERVER__GRAFANA__API_TOKEN
    - MCP__SERVER__LOKI__URL
    - MCP__SERVER__LOKI__API_TOKEN
    """

    # AI Provider configurations (nested)
    ai_provider: AIProviderConfig = Field(
        default_factory=lambda: AIProviderConfig(), description="AI provider configurations"
    )

    # =====================================================================
    # MCP Configuration for Tests
    # =====================================================================
    mcp: TestMCPConfig = Field(
        default_factory=TestMCPConfig,
        description="MCP configuration (Slack, ClickUp, GitHub, Gateway)",
    )

    # MCP Server configurations (nested)
    # mcp_server: TestMCPServerConfig = Field(
    #     default_factory=TestMCPServerConfig, description="MCP server configurations"
    # )

    # Test execution flags
    run_ai_tests: bool = Field(True, description="Whether to run tests that call real AI models")
    run_slow_tests: bool = Field(False, description="Whether to run slow integration tests")
    test_timeout: int = Field(60, description="Timeout for individual tests in seconds")

    # Model configurations for testing
    test_models: dict[str, TestModelSettings] = Field(default_factory=dict, description="Test model configurations")
    test_agents: dict[str, TestAgentSettings] = Field(default_factory=dict, description="Test agent configurations")

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._setup_default_configurations()

    def _setup_default_configurations(self) -> None:
        """Setup default test configurations if API keys are available."""

        # Initialize MCP server configurations if not already set
        if self.mcp.server is None:
            self.mcp.server = TestMCPServerConfig()

        # Default OpenAI model configuration
        if self.ai_provider.openai.api_key:
            self.test_models["openai_gpt4"] = TestModelSettings(
                customized_name="openai_gpt4",
                provider="openai",
                model=self.ai_provider.openai.model,
                api_key=self.ai_provider.openai.api_key,
                temperature=self.ai_provider.openai.temperature,
                max_tokens=self.ai_provider.openai.max_tokens,
            )

            self.test_agents["test_assistant"] = TestAgentSettings(
                role="test_assistant",
                description="A test assistant for smoke testing",
                model_settings=self.test_models["openai_gpt4"],
                system_prompt="You are a helpful test assistant. Respond briefly and accurately.",
                tools=[],
            )

        # Default Anthropic model configuration
        if self.ai_provider.anthropic.api_key:
            self.test_models["anthropic_claude"] = TestModelSettings(
                customized_name="anthropic_claude",
                provider="anthropic",
                model=self.ai_provider.anthropic.model,
                api_key=self.ai_provider.anthropic.api_key,
                temperature=self.ai_provider.anthropic.temperature,
                max_tokens=self.ai_provider.anthropic.max_tokens,
            )

        # Default Gemini model configuration
        if self.ai_provider.gemini.api_key:
            self.test_models["gemini_pro"] = TestModelSettings(
                customized_name="gemini_pro",
                provider="gemini",
                model=self.ai_provider.gemini.model,
                api_key=self.ai_provider.gemini.api_key,
                temperature=self.ai_provider.gemini.temperature,
                max_tokens=self.ai_provider.gemini.max_tokens,
            )

        # Default xAI model configuration
        if self.ai_provider.xai.api_key:
            self.test_models["xai_grok"] = TestModelSettings(
                customized_name="xai_grok",
                provider="xai",
                model=self.ai_provider.xai.model,
                api_key=self.ai_provider.xai.api_key,
                temperature=self.ai_provider.xai.temperature,
                max_tokens=self.ai_provider.xai.max_tokens,
            )

    @property
    def openai(self) -> TestOpenAIConfig:
        """Get OpenAI configuration."""
        return self.ai_provider.openai

    @property
    def anthropic(self) -> TestAnthropicConfig:
        """Get Anthropic configuration."""
        return self.ai_provider.anthropic

    @property
    def gemini(self) -> TestGeminiConfig:
        """Get Gemini configuration."""
        return self.ai_provider.gemini

    @property
    def xai(self) -> TestXAIConfig:
        """Get xAI configuration."""
        return self.ai_provider.xai

    @property
    def server(self) -> TestMCPServerConfig:
        """Get MCP server configurations."""
        return self.mcp.server

    def get_available_providers(self) -> list[str]:
        """Get list of available AI providers based on API keys."""
        providers = []
        if self.ai_provider.openai.api_key:
            providers.append("openai")
        if self.ai_provider.anthropic.api_key:
            providers.append("anthropic")
        if self.ai_provider.gemini.api_key:
            providers.append("gemini")
        if self.ai_provider.xai.api_key:
            providers.append("xai")
        return providers

    def has_provider(self, provider: str) -> bool:
        """Check if a specific provider has API key configured."""
        provider = provider.lower()
        if provider == "openai":
            return bool(self.ai_provider.openai.api_key)
        if provider == "anthropic":
            return bool(self.ai_provider.anthropic.api_key)
        if provider == "gemini" or provider == "google":
            return bool(self.ai_provider.gemini.api_key)
        if provider == "xai" or provider == "grok":
            return bool(self.ai_provider.xai.api_key)
        return False


def export_api_keys_to_env() -> None:
    """Export API keys from test_settings to environment variables for smoke tests."""
    # Export OpenAI API key
    if test_settings.ai_provider.openai.api_key:
        os.environ["OPENAI_API_KEY"] = test_settings.ai_provider.openai.api_key.get_secret_value()

    # Export Anthropic API key
    if test_settings.ai_provider.anthropic.api_key:
        os.environ["ANTHROPIC_API_KEY"] = test_settings.ai_provider.anthropic.api_key.get_secret_value()

    # Export Gemini API key
    if test_settings.ai_provider.gemini.api_key:
        os.environ["GOOGLE_API_KEY"] = test_settings.ai_provider.gemini.api_key.get_secret_value()

    # Export xAI API key
    if test_settings.ai_provider.xai.api_key:
        os.environ["XAI_API_KEY"] = test_settings.ai_provider.xai.api_key.get_secret_value()


# Create singleton instance and export API keys
test_settings = TestSettings()
export_api_keys_to_env()
