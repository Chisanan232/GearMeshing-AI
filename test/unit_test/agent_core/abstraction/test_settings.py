"""
Unit tests for agent abstraction settings models.
"""

import pytest
from pydantic import ValidationError

from gearmeshing_ai.agent_core.abstraction.settings import AgentSettings, ModelSettings


class TestModelSettings:
    """Test cases for ModelSettings class."""

    def test_model_settings_creation_with_required_fields(self) -> None:
        """Test creating ModelSettings with only required fields."""
        settings = ModelSettings(customized_name="test-model", provider="openai", model="gpt-4")

        assert settings.customized_name == "test-model"
        assert settings.provider == "openai"
        assert settings.model == "gpt-4"
        assert settings.api_key is None
        assert settings.api_base is None
        assert settings.temperature == 0.7
        assert settings.max_tokens is None
        assert settings.additional_params == {}

    def test_model_settings_creation_with_all_fields(self) -> None:
        """Test creating ModelSettings with all fields."""
        api_key = "sk-test-key"
        settings = ModelSettings(
            customized_name="complete-model",
            provider="anthropic",
            model="claude-3-opus",
            api_key=api_key,
            api_base="https://api.anthropic.com",
            temperature=0.5,
            max_tokens=4096,
            additional_params={"top_p": 0.9, "frequency_penalty": 0.1},
        )

        assert settings.customized_name == "complete-model"
        assert settings.provider == "anthropic"
        assert settings.model == "claude-3-opus"
        assert settings.api_key is not None and settings.api_key.get_secret_value() == api_key
        assert settings.api_base == "https://api.anthropic.com"
        assert settings.temperature == 0.5
        assert settings.max_tokens == 4096
        assert settings.additional_params == {"top_p": 0.9, "frequency_penalty": 0.1}

    def test_model_settings_validation_errors(self) -> None:
        """Test validation errors for missing required fields."""
        # Missing customized_name
        with pytest.raises(ValidationError) as exc_info:
            ModelSettings(provider="openai", model="gpt-4")
        assert "customized_name" in str(exc_info.value)

        # Missing provider
        with pytest.raises(ValidationError) as exc_info:
            ModelSettings(customized_name="test", model="gpt-4")
        assert "provider" in str(exc_info.value)

        # Missing model
        with pytest.raises(ValidationError) as exc_info:
            ModelSettings(customized_name="test", provider="openai")
        assert "model" in str(exc_info.value)

    def test_model_settings_temperature_validation(self) -> None:
        """Test temperature field validation."""
        # Valid temperature values
        settings = ModelSettings(customized_name="test", provider="openai", model="gpt-4", temperature=0.0)
        assert settings.temperature == 0.0

        settings = ModelSettings(customized_name="test", provider="openai", model="gpt-4", temperature=1.0)
        assert settings.temperature == 1.0

        # Temperature should accept float values
        settings = ModelSettings(customized_name="test", provider="openai", model="gpt-4", temperature=0.123)
        assert settings.temperature == 0.123

    def test_model_settings_secret_str_behavior(self) -> None:
        """Test SecretStr behavior for API key."""
        api_key = "sk-secret-key"
        settings = ModelSettings(customized_name="test", provider="openai", model="gpt-4", api_key=api_key)

        # SecretStr should mask the value in repr
        assert "sk-secret-key" not in repr(settings.api_key)
        assert "**********" in repr(settings.api_key) or "SecretStr" in repr(settings.api_key)

        # But get_secret_value() should return the actual value
        assert settings.api_key is not None and settings.api_key.get_secret_value() == api_key

    def test_model_settings_additional_params_mutation(self) -> None:
        """Test that additional_params can be modified after creation."""
        settings = ModelSettings(
            customized_name="test", provider="openai", model="gpt-4", additional_params={"initial": "value"}
        )

        # Modify additional_params
        settings.additional_params["new_key"] = "new_value"
        assert settings.additional_params == {"initial": "value", "new_key": "new_value"}

    def test_model_settings_model_copy_with_update(self) -> None:
        """Test model_copy with update functionality."""
        original = ModelSettings(customized_name="test", provider="openai", model="gpt-4", temperature=0.7)

        updated = original.model_copy(update={"temperature": 0.5, "max_tokens": 1000})

        assert updated.customized_name == "test"
        assert updated.provider == "openai"
        assert updated.model == "gpt-4"
        assert updated.temperature == 0.5
        assert updated.max_tokens == 1000

        # Original should be unchanged
        assert original.temperature == 0.7
        assert original.max_tokens is None


class TestAgentSettings:
    """Test cases for AgentSettings class."""

    def test_agent_settings_creation_with_required_fields(self) -> None:
        """Test creating AgentSettings with only required fields."""
        model_settings = ModelSettings(customized_name="test-model", provider="openai", model="gpt-4")

        agent_settings = AgentSettings(role="test-agent", description="A test agent", model_settings=model_settings)

        assert agent_settings.role == "test-agent"
        assert agent_settings.description == "A test agent"
        assert agent_settings.model_settings == model_settings
        assert agent_settings.tools == []
        assert agent_settings.system_prompt is None
        assert agent_settings.metadata == {}

    def test_agent_settings_creation_with_all_fields(self) -> None:
        """Test creating AgentSettings with all fields."""
        model_settings = ModelSettings(
            customized_name="complete-model", provider="anthropic", model="claude-3-opus", api_key="sk-test-key"
        )

        agent_settings = AgentSettings(
            role="complete-agent",
            description="A complete test agent",
            model_settings=model_settings,
            tools=["calculator", "weather"],
            system_prompt="You are a helpful assistant.",
            metadata={"version": "1.0", "author": "test"},
        )

        assert agent_settings.role == "complete-agent"
        assert agent_settings.description == "A complete test agent"
        assert agent_settings.model_settings == model_settings
        assert agent_settings.tools == ["calculator", "weather"]
        assert agent_settings.system_prompt == "You are a helpful assistant."
        assert agent_settings.metadata == {"version": "1.0", "author": "test"}

    def test_agent_settings_validation_errors(self) -> None:
        """Test validation errors for missing required fields."""
        model_settings = ModelSettings(customized_name="test-model", provider="openai", model="gpt-4")

        # Missing role
        with pytest.raises(ValidationError) as exc_info:
            AgentSettings(description="Test agent", model_settings=model_settings)
        assert "role" in str(exc_info.value)

        # Missing description
        with pytest.raises(ValidationError) as exc_info:
            AgentSettings(role="test", model_settings=model_settings)
        assert "description" in str(exc_info.value)

        # Missing model_settings
        with pytest.raises(ValidationError) as exc_info:
            AgentSettings(role="test", description="Test agent")
        assert "model_settings" in str(exc_info.value)

    def test_agent_settings_tools_list_behavior(self) -> None:
        """Test tools field behavior."""
        model_settings = ModelSettings(customized_name="test", provider="openai", model="gpt-4")

        # Default empty list
        agent_settings = AgentSettings(role="test", description="Test", model_settings=model_settings)
        assert agent_settings.tools == []

        # With tools
        agent_settings = AgentSettings(
            role="test", description="Test", model_settings=model_settings, tools=["tool1", "tool2", "tool3"]
        )
        assert agent_settings.tools == ["tool1", "tool2", "tool3"]

    def test_agent_settings_metadata_mutation(self) -> None:
        """Test that metadata can be modified after creation."""
        model_settings = ModelSettings(customized_name="test", provider="openai", model="gpt-4")

        agent_settings = AgentSettings(
            role="test", description="Test", model_settings=model_settings, metadata={"initial": "value"}
        )

        # Modify metadata
        agent_settings.metadata["new_key"] = "new_value"
        assert agent_settings.metadata == {"initial": "value", "new_key": "new_value"}

    def test_agent_settings_model_copy_with_update(self) -> None:
        """Test model_copy with update functionality."""
        model_settings = ModelSettings(customized_name="test", provider="openai", model="gpt-4")

        original = AgentSettings(
            role="test-agent", description="Original description", model_settings=model_settings, tools=["tool1"]
        )

        updated = original.model_copy(
            update={
                "description": "Updated description",
                "tools": ["tool1", "tool2"],
                "system_prompt": "Updated system prompt",
            }
        )

        assert updated.role == "test-agent"
        assert updated.description == "Updated description"
        assert updated.model_settings == model_settings
        assert updated.tools == ["tool1", "tool2"]
        assert updated.system_prompt == "Updated system prompt"

        # Original should be unchanged
        assert original.description == "Original description"
        assert original.tools == ["tool1"]
        assert original.system_prompt is None

    def test_agent_settings_nested_model_validation(self) -> None:
        """Test that nested ModelSettings are properly validated."""
        # Invalid nested model settings should cause validation error
        with pytest.raises(ValidationError):
            AgentSettings(
                role="test",
                description="Test",
                model_settings="invalid_model_settings",  # Should be ModelSettings instance
            )

    def test_agent_settings_serialization(self) -> None:
        """Test serialization behavior."""
        model_settings = ModelSettings(customized_name="test", provider="openai", model="gpt-4", api_key="sk-secret")

        agent_settings = AgentSettings(
            role="test", description="Test", model_settings=model_settings, metadata={"key": "value"}
        )

        # Test model_dump (SecretStr is included but masked)
        data = agent_settings.model_dump()
        assert data["role"] == "test"
        assert data["description"] == "Test"
        model_data = data["model_settings"]
        # SecretStr is included but shows as masked
        assert "api_key" in model_data
        # The repr shows masked, the actual string representation is just the masked value
        api_key_repr = repr(model_data["api_key"])
        assert "**********" in api_key_repr

        # Test that we can get the actual secret value
        assert model_data["api_key"] is not None
        actual_value = model_data["api_key"].get_secret_value()
        assert actual_value == "sk-secret"
