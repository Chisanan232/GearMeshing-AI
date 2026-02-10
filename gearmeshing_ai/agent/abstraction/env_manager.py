import os

from gearmeshing_ai.core.models.setting import AIProviderSettings


class EnvManager:
    """Manages AI Provider environment variables.

    Validates API keys and exports them to os.environ for libraries that expect them there.
    """

    def __init__(self) -> None:
        self.settings = AIProviderSettings()

    def validate_provider_keys(self, provider: str) -> bool:
        """Check if the API key for a specific provider is present."""
        provider = provider.lower()
        if provider == "openai":
            return self.settings.ai_provider.openai.api_key is not None
        if provider == "anthropic":
            return self.settings.ai_provider.anthropic.api_key is not None
        if provider == "gemini" or provider == "google":
            return self.settings.ai_provider.gemini.api_key is not None
        return False

    def export_variables(self) -> None:
        """Export the loaded settings to os.environ so that underlying SDKs.

        (like OpenAI client, Pydantic AI) can pick them up automatically.
        """
        if self.settings.ai_provider.openai.api_key:
            os.environ["OPENAI_API_KEY"] = self.settings.ai_provider.openai.api_key.get_secret_value()

        if self.settings.ai_provider.anthropic.api_key:
            os.environ["ANTHROPIC_API_KEY"] = self.settings.ai_provider.anthropic.api_key.get_secret_value()

        if self.settings.ai_provider.gemini.api_key:
            os.environ["GEMINI_API_KEY"] = self.settings.ai_provider.gemini.api_key.get_secret_value()

    def get_settings(self) -> AIProviderSettings:
        return self.settings
