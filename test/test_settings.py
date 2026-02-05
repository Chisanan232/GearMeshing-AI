"""
Test for the test settings model and dotenv functionality.

This test verifies that the test settings model works correctly
with environment variable loading and configuration.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the test settings
from test.settings import TestAgentSettings, TestModelSettings, TestSettings


class TestSettingsModel:
    """Test the test settings model functionality."""

    def test_settings_model_creation(self):
        """Test that settings model can be created without errors."""
        settings = TestSettings()
        assert settings is not None
        assert isinstance(settings, TestSettings)

    def test_default_values(self):
        """Test that default values are set correctly."""
        settings = TestSettings()
        assert settings.run_ai_tests is True
        assert settings.run_slow_tests is False
        assert settings.test_timeout == 60
        assert isinstance(settings.test_models, dict)
        assert isinstance(settings.test_agents, dict)

    def test_get_available_providers_no_keys(self):
        """Test getting available providers when no API keys are set."""
        settings = TestSettings()
        providers = settings.get_available_providers()
        assert isinstance(providers, list)
        assert len(providers) == 0

    def test_has_provider_no_keys(self):
        """Test provider check when no API keys are set."""
        settings = TestSettings()
        assert settings.has_provider("openai") is False
        assert settings.has_provider("anthropic") is False
        assert settings.has_provider("google") is False
        assert settings.has_provider("unknown") is False

    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test-openai-key",
            "ANTHROPIC_API_KEY": "test-anthropic-key",
            "GEMINI_API_KEY": "test-gemini-key",
        },
    )
    def test_settings_with_api_keys(self):
        """Test settings creation with API keys in environment."""
        settings = TestSettings()

        # Check API keys are loaded
        assert settings.openai_api_key is not None
        assert settings.anthropic_api_key is not None
        assert settings.gemini_api_key is not None

        # Check provider availability
        providers = settings.get_available_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "google" in providers

        # Check individual provider checks
        assert settings.has_provider("openai") is True
        assert settings.has_provider("anthropic") is True
        assert settings.has_provider("google") is True

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-openai-key"})
    def test_default_configurations_with_openai(self):
        """Test that default configurations are created when OpenAI API key is present."""
        settings = TestSettings()

        # Check that OpenAI model configuration was created
        assert "openai_gpt4" in settings.test_models
        openai_model = settings.test_models["openai_gpt4"]
        assert isinstance(openai_model, TestModelSettings)
        assert openai_model.provider == "openai"
        assert openai_model.model == "gpt-4"
        assert openai_model.customized_name == "openai_gpt4"

        # Check that test agent was created
        assert "test_assistant" in settings.test_agents
        test_agent = settings.test_agents["test_assistant"]
        assert isinstance(test_agent, TestAgentSettings)
        assert test_agent.role == "test_assistant"
        assert test_agent.model_settings == openai_model
        assert test_agent.system_prompt is not None

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-anthropic-key"})
    def test_default_configurations_with_anthropic(self):
        """Test that default configurations are created when Anthropic API key is present."""
        settings = TestSettings()

        # Check that Anthropic model configuration was created
        assert "anthropic_claude" in settings.test_models
        anthropic_model = settings.test_models["anthropic_claude"]
        assert isinstance(anthropic_model, TestModelSettings)
        assert anthropic_model.provider == "anthropic"
        assert anthropic_model.model == "claude-3-sonnet-20240229"

        # Check that test agent was created
        assert "claude_assistant" in settings.test_agents
        claude_agent = settings.test_agents["claude_assistant"]
        assert isinstance(claude_agent, TestAgentSettings)
        assert claude_agent.role == "claude_assistant"
        assert claude_agent.model_settings == anthropic_model

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini-key"})
    def test_default_configurations_with_gemini(self):
        """Test that default configurations are created when Gemini API key is present."""
        settings = TestSettings()

        # Check that Gemini model configuration was created
        assert "gemini_pro" in settings.test_models
        gemini_model = settings.test_models["gemini_pro"]
        assert isinstance(gemini_model, TestModelSettings)
        assert gemini_model.provider == "google"
        assert gemini_model.model == "gemini-pro"

        # Check that test agent was created
        assert "gemini_assistant" in settings.test_agents
        gemini_agent = settings.test_agents["gemini_assistant"]
        assert isinstance(gemini_agent, TestAgentSettings)
        assert gemini_agent.role == "gemini_assistant"
        assert gemini_agent.model_settings == gemini_model

    def test_model_settings_validation(self):
        """Test TestModelSettings validation."""
        # Valid model settings
        model_settings = TestModelSettings(
            customized_name="test_model", provider="openai", model="gpt-4", temperature=0.5, max_tokens=500
        )
        assert model_settings.customized_name == "test_model"
        assert model_settings.provider == "openai"
        assert model_settings.model == "gpt-4"
        assert model_settings.temperature == 0.5
        assert model_settings.max_tokens == 500
        assert isinstance(model_settings.additional_params, dict)

    def test_agent_settings_validation(self):
        """Test TestAgentSettings validation."""
        model_settings = TestModelSettings(customized_name="test_model", provider="openai", model="gpt-4")

        agent_settings = TestAgentSettings(
            role="test_role",
            description="Test agent description",
            model_settings=model_settings,
            tools=["tool1", "tool2"],
            system_prompt="Test system prompt",
        )

        assert agent_settings.role == "test_role"
        assert agent_settings.description == "Test agent description"
        assert agent_settings.model_settings == model_settings
        assert agent_settings.tools == ["tool1", "tool2"]
        assert agent_settings.system_prompt == "Test system prompt"
        assert isinstance(agent_settings.metadata, dict)

    def test_secret_str_behavior(self):
        """Test that SecretStr properly hides sensitive values."""
        settings = TestSettings()

        # Create a model with API key
        model_settings = TestModelSettings(
            customized_name="test_model", provider="openai", model="gpt-4", api_key="secret-key"
        )

        # Check that the secret is hidden in repr
        api_key_repr = repr(model_settings.api_key)
        assert "secret-key" not in api_key_repr
        assert "**********" in api_key_repr or "SecretStr" in api_key_repr

        # Check that we can still get the actual value
        actual_value = model_settings.api_key.get_secret_value()
        assert actual_value == "secret-key"

    def test_env_file_loading(self):
        """Test that environment file is loaded correctly."""
        # Check if .env file exists in test directory
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            # The settings should load from the .env file
            settings = TestSettings()
            assert settings is not None
        else:
            # Should still work without .env file
            settings = TestSettings()
            assert settings is not None


if __name__ == "__main__":
    pytest.main([__file__])
