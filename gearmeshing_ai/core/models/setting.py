from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AIProviderSettings(BaseSettings):
    """Settings for AI Model Providers (OpenAI, Anthropic, etc.).

    Reads from environment variables or .env file.
    """

    openai_api_key: SecretStr | None = Field(None, alias="OPENAI_API_KEY")
    anthropic_api_key: SecretStr | None = Field(None, alias="ANTHROPIC_API_KEY")
    gemini_api_key: SecretStr | None = Field(None, alias="GEMINI_API_KEY")

    # Common settings
    default_model_provider: str = Field("openai", alias="DEFAULT_MODEL_PROVIDER")
    default_model_name: str = Field("gpt-4o", alias="DEFAULT_MODEL_NAME")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
