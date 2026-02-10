"""Unit tests for roles package models.

Tests for RoleDefinition and RoleMetadata models including:
- Model creation and validation
- Conversion to AgentSettings
- Loading from dictionaries
- Metadata configuration
"""

import pytest

from gearmeshing_ai.agent.roles.models.role_definition import RoleDefinition, RoleMetadata


class TestRoleMetadata:
    """Test RoleMetadata model."""

    def test_create_with_defaults(self):
        """Test creating RoleMetadata with default values."""
        metadata = RoleMetadata(
            domain="test_domain",
            decision_authority="test_authority",
        )

        assert metadata.domain == "test_domain"
        assert metadata.decision_authority == "test_authority"
        assert metadata.version == "1.0"
        assert metadata.requires_approval is False
        assert metadata.max_tokens == 2048
        assert metadata.temperature == 0.7
        assert metadata.timeout_seconds == 300
        assert metadata.cost_priority == "medium"

    def test_create_with_custom_values(self):
        """Test creating RoleMetadata with custom values."""
        metadata = RoleMetadata(
            domain="software_development",
            decision_authority="code_approval",
            version="2.0",
            requires_approval=True,
            max_tokens=4096,
            temperature=0.3,
            timeout_seconds=600,
            cost_priority="high",
            additional_metadata={"custom_key": "custom_value"},
        )

        assert metadata.domain == "software_development"
        assert metadata.decision_authority == "code_approval"
        assert metadata.version == "2.0"
        assert metadata.requires_approval is True
        assert metadata.max_tokens == 4096
        assert metadata.temperature == 0.3
        assert metadata.timeout_seconds == 600
        assert metadata.cost_priority == "high"
        assert metadata.additional_metadata == {"custom_key": "custom_value"}

    def test_metadata_validation(self):
        """Test metadata field validation."""
        # Valid temperature (0-2)
        metadata = RoleMetadata(
            domain="test",
            decision_authority="test",
            temperature=1.5,
        )
        assert metadata.temperature == 1.5

        # Valid max_tokens
        metadata = RoleMetadata(
            domain="test",
            decision_authority="test",
            max_tokens=8192,
        )
        assert metadata.max_tokens == 8192


class TestRoleDefinition:
    """Test RoleDefinition model."""

    @pytest.fixture
    def sample_metadata(self):
        """Create sample metadata."""
        return RoleMetadata(
            domain="software_development",
            decision_authority="implementation",
            temperature=0.4,
            max_tokens=3072,
        )

    @pytest.fixture
    def sample_role(self, sample_metadata):
        """Create sample role definition."""
        return RoleDefinition(
            role="dev",
            description="Senior Software Developer",
            model_provider="openai",
            model_name="gpt-4",
            customized_model_name="dev-gpt4",
            system_prompt="You are a senior software developer...",
            tools=["read_file", "write_file", "run_command"],
            metadata=sample_metadata,
        )

    def test_create_role_definition(self, sample_role):
        """Test creating RoleDefinition."""
        assert sample_role.role == "dev"
        assert sample_role.description == "Senior Software Developer"
        assert sample_role.model_provider == "openai"
        assert sample_role.model_name == "gpt-4"
        assert sample_role.customized_model_name == "dev-gpt4"
        assert sample_role.system_prompt == "You are a senior software developer..."
        assert sample_role.tools == ["read_file", "write_file", "run_command"]
        assert sample_role.metadata.domain == "software_development"

    def test_role_with_empty_tools(self, sample_metadata):
        """Test creating role with empty tools list."""
        role = RoleDefinition(
            role="marketing",
            description="Marketing Manager",
            model_provider="openai",
            model_name="gpt-4",
            customized_model_name="marketing-gpt4",
            system_prompt="You are a marketing manager...",
            tools=[],
            metadata=sample_metadata,
        )

        assert role.tools == []

    def test_to_agent_settings(self, sample_role):
        """Test converting RoleDefinition to AgentSettings."""
        from gearmeshing_ai.agent.abstraction.settings import AgentSettings

        agent_settings = sample_role.to_agent_settings()

        assert isinstance(agent_settings, AgentSettings)
        assert agent_settings.role == "dev"
        assert agent_settings.description == "Senior Software Developer"
        assert agent_settings.model_settings.provider == "openai"
        assert agent_settings.model_settings.model == "gpt-4"
        assert agent_settings.model_settings.customized_name == "dev-gpt4"
        assert agent_settings.model_settings.temperature == 0.4
        assert agent_settings.model_settings.max_tokens == 3072
        assert agent_settings.system_prompt == "You are a senior software developer..."
        assert agent_settings.tools == ["read_file", "write_file", "run_command"]

    def test_from_dict_basic(self):
        """Test creating RoleDefinition from dictionary."""
        role_dict = {
            "role": "dev_lead",
            "description": "Senior Software Architect",
            "model_settings": {
                "customized_name": "dev-lead-gpt4-turbo",
                "provider": "openai",
                "model": "gpt-4-turbo",
            },
            "system_prompt": "You are a senior architect...",
            "tools": ["read_file", "write_file"],
            "metadata": {
                "domain": "technical_leadership",
                "decision_authority": "architecture",
                "temperature": 0.3,
                "max_tokens": 4096,
            },
        }

        role = RoleDefinition.from_dict(role_dict)

        assert role.role == "dev_lead"
        assert role.description == "Senior Software Architect"
        assert role.model_provider == "openai"
        assert role.model_name == "gpt-4-turbo"
        assert role.customized_model_name == "dev-lead-gpt4-turbo"
        assert role.metadata.domain == "technical_leadership"
        assert role.metadata.temperature == 0.3

    def test_from_dict_with_defaults(self):
        """Test creating RoleDefinition from dict with missing optional fields."""
        role_dict = {
            "role": "qa",
            "description": "QA Engineer",
            "model_settings": {
                "customized_name": "qa-gpt4",
                "provider": "openai",
                "model": "gpt-4",
            },
            "system_prompt": "You are a QA engineer...",
            "metadata": {
                "domain": "quality_assurance",
                "decision_authority": "quality_assessment",
            },
        }

        role = RoleDefinition.from_dict(role_dict)

        assert role.role == "qa"
        assert role.tools == []  # Default empty list
        assert role.metadata.version == "1.0"  # Default version
        assert role.metadata.temperature == 0.7  # Default temperature

    def test_from_dict_missing_required_fields(self):
        """Test that from_dict raises error for missing required fields."""
        incomplete_dict = {
            "role": "dev",
            "description": "Developer",
            # Missing model_settings, system_prompt, metadata
        }

        with pytest.raises((KeyError, TypeError, ValueError)):
            RoleDefinition.from_dict(incomplete_dict)

    def test_role_with_multiple_tools(self, sample_metadata):
        """Test role with multiple tools."""
        tools = [
            "read_file",
            "write_file",
            "run_command",
            "query_database",
            "generate_report",
        ]

        role = RoleDefinition(
            role="dev_lead",
            description="Senior Developer",
            model_provider="openai",
            model_name="gpt-4-turbo",
            customized_model_name="dev-lead-gpt4-turbo",
            system_prompt="You are a senior developer...",
            tools=tools,
            metadata=sample_metadata,
        )

        assert len(role.tools) == 5
        assert "run_command" in role.tools
        assert "query_database" in role.tools

    def test_role_metadata_in_agent_settings(self, sample_role):
        """Test that metadata is included in AgentSettings."""
        agent_settings = sample_role.to_agent_settings()

        assert "domain" in agent_settings.metadata
        assert agent_settings.metadata["domain"] == "software_development"
        assert agent_settings.metadata["decision_authority"] == "implementation"
        assert agent_settings.metadata["temperature"] == 0.4


class TestRoleDefinitionIntegration:
    """Integration tests for RoleDefinition with other components."""

    def test_role_roundtrip_dict_conversion(self):
        """Test converting role to dict and back."""
        original_dict = {
            "role": "dev",
            "description": "Developer",
            "model_settings": {
                "customized_name": "dev-gpt4",
                "provider": "openai",
                "model": "gpt-4",
            },
            "system_prompt": "You are a developer...",
            "tools": ["read_file", "write_file"],
            "metadata": {
                "domain": "software_development",
                "decision_authority": "implementation",
                "temperature": 0.4,
            },
        }

        # Create from dict
        role = RoleDefinition.from_dict(original_dict)

        # Verify all fields match
        assert role.role == original_dict["role"]
        assert role.description == original_dict["description"]
        assert role.model_provider == original_dict["model_settings"]["provider"]
        assert role.model_name == original_dict["model_settings"]["model"]
        assert role.tools == original_dict["tools"]

    def test_multiple_roles_with_different_models(self):
        """Test creating multiple roles with different model configurations."""
        metadata = RoleMetadata(
            domain="test",
            decision_authority="test",
        )

        roles = [
            RoleDefinition(
                role="fast_role",
                description="Fast role",
                model_provider="openai",
                model_name="gpt-4",
                customized_model_name="fast-gpt4",
                system_prompt="Fast prompt",
                metadata=metadata,
            ),
            RoleDefinition(
                role="powerful_role",
                description="Powerful role",
                model_provider="openai",
                model_name="gpt-4-turbo",
                customized_model_name="powerful-gpt4-turbo",
                system_prompt="Powerful prompt",
                metadata=metadata,
            ),
        ]

        assert roles[0].model_name == "gpt-4"
        assert roles[1].model_name == "gpt-4-turbo"
        assert roles[0].customized_model_name != roles[1].customized_model_name
