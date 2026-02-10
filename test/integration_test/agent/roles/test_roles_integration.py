"""Integration tests for roles package.

Tests for complete roles package functionality including:
- End-to-end role loading and registration
- Integration with AgentFactory
- Integration with agent_decision_node
- Multi-role workflows
"""

import pytest
import tempfile
from pathlib import Path
import yaml

from gearmeshing_ai.agent.roles.service import RoleService
from gearmeshing_ai.agent.roles.loader import load_default_roles
from gearmeshing_ai.agent.roles.selector import RoleSelector
from gearmeshing_ai.agent.roles.registry import RoleRegistry
from gearmeshing_ai.agent.abstraction.factory import AgentFactory
from gearmeshing_ai.agent.abstraction.adapter import AgentAdapter
from gearmeshing_ai.agent.models.actions import ActionProposal
from unittest.mock import Mock, AsyncMock, MagicMock


@pytest.fixture
def mock_adapter():
    """Create a mock adapter."""
    adapter = Mock(spec=AgentAdapter)
    adapter.create_agent = Mock(return_value=Mock())
    adapter.run = AsyncMock(
        return_value=ActionProposal(
            action="test_action",
            reason="test reason",
            parameters={"key": "value"},
        )
    )
    return adapter


@pytest.fixture
def agent_factory(mock_adapter):
    """Create an AgentFactory with mock adapter."""
    return AgentFactory(adapter=mock_adapter)


@pytest.fixture
def temp_config_file():
    """Create a temporary configuration file with multiple roles."""
    config = {
        "roles": {
            "marketing": {
                "description": "Product Marketing Manager",
                "model_settings": {
                    "customized_name": "marketing-gpt4",
                    "provider": "openai",
                    "model": "gpt-4",
                },
                "system_prompt": "You are a product marketing manager...",
                "tools": ["read_file", "query_database"],
                "metadata": {
                    "domain": "product_marketing",
                    "decision_authority": "positioning_and_messaging",
                    "temperature": 0.8,
                    "max_tokens": 2048,
                },
            },
            "dev": {
                "description": "Senior Software Developer",
                "model_settings": {
                    "customized_name": "dev-gpt4",
                    "provider": "openai",
                    "model": "gpt-4",
                },
                "system_prompt": "You are a senior software developer...",
                "tools": ["read_file", "write_file", "run_command"],
                "metadata": {
                    "domain": "software_development",
                    "decision_authority": "implementation",
                    "temperature": 0.4,
                    "max_tokens": 3072,
                },
            },
            "qa": {
                "description": "Senior QA Engineer",
                "model_settings": {
                    "customized_name": "qa-gpt4",
                    "provider": "openai",
                    "model": "gpt-4",
                },
                "system_prompt": "You are a senior QA engineer...",
                "tools": ["read_file", "write_file"],
                "metadata": {
                    "domain": "quality_assurance",
                    "decision_authority": "quality_assessment",
                    "temperature": 0.4,
                    "max_tokens": 3072,
                },
            },
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink()


class TestRolesIntegration:
    """Integration tests for roles package."""

    def test_load_and_register_with_factory(self, agent_factory, temp_config_file):
        """Test loading roles and registering with factory."""
        service = RoleService(agent_factory=agent_factory)

        roles = service.load_and_register_roles(temp_config_file)

        assert len(roles) == 3
        assert agent_factory.get_agent_settings("dev") is not None
        assert agent_factory.get_agent_settings("qa") is not None
        assert agent_factory.get_agent_settings("marketing") is not None

    def test_role_settings_conversion_to_agent_settings(self, agent_factory, temp_config_file):
        """Test that role settings are correctly converted to AgentSettings."""
        service = RoleService(agent_factory=agent_factory)
        service.load_and_register_roles(temp_config_file)

        dev_settings = agent_factory.get_agent_settings("dev")

        assert dev_settings.role == "dev"
        assert dev_settings.description == "Senior Software Developer"
        assert dev_settings.model_settings.provider == "openai"
        assert dev_settings.model_settings.model == "gpt-4"
        assert dev_settings.model_settings.temperature == 0.4
        assert dev_settings.model_settings.max_tokens == 3072
        assert "read_file" in dev_settings.tools
        assert "write_file" in dev_settings.tools
        assert "run_command" in dev_settings.tools

    def test_role_selector_with_loaded_roles(self, agent_factory, temp_config_file):
        """Test role selector with loaded roles."""
        service = RoleService(agent_factory=agent_factory)
        service.load_and_register_roles(temp_config_file)

        selector = RoleSelector(service.registry)

        # Test validation
        assert selector.validate_role("dev")
        assert selector.validate_role("qa")
        assert selector.validate_role("marketing")

        # Test suggestion
        assert selector.suggest_role("Implement new feature") == "dev"
        assert selector.suggest_role("Create test cases") == "qa"
        assert selector.suggest_role("Analyze market positioning") == "marketing"

    def test_multiple_roles_with_different_models(self, agent_factory, temp_config_file):
        """Test that different roles can have different model configurations."""
        service = RoleService(agent_factory=agent_factory)
        service.load_and_register_roles(temp_config_file)

        dev_settings = agent_factory.get_agent_settings("dev")
        qa_settings = agent_factory.get_agent_settings("qa")
        marketing_settings = agent_factory.get_agent_settings("marketing")

        # All should have same provider but potentially different models
        assert dev_settings.model_settings.provider == "openai"
        assert qa_settings.model_settings.provider == "openai"
        assert marketing_settings.model_settings.provider == "openai"

        # Check temperature differences
        assert dev_settings.model_settings.temperature == 0.4
        assert qa_settings.model_settings.temperature == 0.4
        assert marketing_settings.model_settings.temperature == 0.8

    def test_role_tools_configuration(self, agent_factory, temp_config_file):
        """Test that roles have correct tool configurations."""
        service = RoleService(agent_factory=agent_factory)
        service.load_and_register_roles(temp_config_file)

        dev_settings = agent_factory.get_agent_settings("dev")
        qa_settings = agent_factory.get_agent_settings("qa")
        marketing_settings = agent_factory.get_agent_settings("marketing")

        # Dev should have more tools
        assert len(dev_settings.tools) == 3
        assert "run_command" in dev_settings.tools

        # QA should have fewer tools
        assert len(qa_settings.tools) == 2
        assert "run_command" not in qa_settings.tools

        # Marketing should have specific tools
        assert len(marketing_settings.tools) == 2
        assert "query_database" in marketing_settings.tools

    def test_default_roles_loading(self, agent_factory):
        """Test loading default roles from package."""
        roles = load_default_roles()

        assert len(roles) == 6

        # Register with factory
        for role in roles:
            agent_settings = role.to_agent_settings()
            agent_factory.register_agent_settings(agent_settings)

        # Verify all roles are registered
        assert agent_factory.get_agent_settings("marketing") is not None
        assert agent_factory.get_agent_settings("planner") is not None
        assert agent_factory.get_agent_settings("dev_lead") is not None
        assert agent_factory.get_agent_settings("dev") is not None
        assert agent_factory.get_agent_settings("qa") is not None
        assert agent_factory.get_agent_settings("sre") is not None

    def test_role_registry_persistence_across_operations(self, temp_config_file):
        """Test that role registry persists across multiple operations."""
        from gearmeshing_ai.agent.roles.loader import RoleLoader
        
        registry = RoleRegistry()
        loader = RoleLoader(registry)
        service = RoleService(registry=registry, loader=loader)

        # Load roles
        service.load_and_register_roles(temp_config_file)

        # Verify roles are in loader's registry (loader registers roles)
        assert len(loader.registry) == 3

        # Create selector and verify it sees the roles
        selector = RoleSelector(loader.registry)
        assert len(selector.list_available_roles()) == 3

        # Get role info
        info = selector.get_role_info("dev")
        assert info["role"] == "dev"

    def test_role_filtering_by_domain(self, agent_factory, temp_config_file):
        """Test filtering roles by domain."""
        service = RoleService(agent_factory=agent_factory)
        service.load_and_register_roles(temp_config_file)

        dev_roles = service.get_roles_by_domain("software_development")
        assert len(dev_roles) == 1
        assert "dev" in dev_roles

        qa_roles = service.get_roles_by_domain("quality_assurance")
        assert len(qa_roles) == 1
        assert "qa" in qa_roles

    def test_role_filtering_by_authority(self, agent_factory, temp_config_file):
        """Test filtering roles by decision authority."""
        service = RoleService(agent_factory=agent_factory)
        service.load_and_register_roles(temp_config_file)

        impl_roles = service.get_roles_by_authority("implementation")
        assert len(impl_roles) == 1
        assert "dev" in impl_roles

        qa_roles = service.get_roles_by_authority("quality_assessment")
        assert len(qa_roles) == 1
        assert "qa" in qa_roles

    def test_complete_workflow_with_roles(self, agent_factory, temp_config_file):
        """Test complete workflow: load roles, select, and get agent settings."""
        # Step 1: Load and register roles
        service = RoleService(agent_factory=agent_factory)
        service.load_and_register_roles(temp_config_file)

        # Step 2: Select role based on task
        selector = RoleSelector(service.registry)
        selected_role = selector.suggest_role("Implement authentication module")
        assert selected_role == "dev"

        # Step 3: Get agent settings for selected role
        agent_settings = agent_factory.get_agent_settings(selected_role)
        assert agent_settings is not None
        assert agent_settings.role == "dev"

        # Step 4: Verify system prompt is set
        assert "developer" in agent_settings.system_prompt.lower()

    def test_role_metadata_preservation(self, agent_factory, temp_config_file):
        """Test that role metadata is preserved through conversion."""
        service = RoleService(agent_factory=agent_factory)
        service.load_and_register_roles(temp_config_file)

        dev_settings = agent_factory.get_agent_settings("dev")

        assert "domain" in dev_settings.metadata
        assert dev_settings.metadata["domain"] == "software_development"
        assert dev_settings.metadata["decision_authority"] == "implementation"
        assert dev_settings.metadata["temperature"] == 0.4

    def test_role_system_prompt_preservation(self, agent_factory, temp_config_file):
        """Test that system prompts are correctly preserved."""
        service = RoleService(agent_factory=agent_factory)
        service.load_and_register_roles(temp_config_file)

        dev_settings = agent_factory.get_agent_settings("dev")
        qa_settings = agent_factory.get_agent_settings("qa")

        assert "developer" in dev_settings.system_prompt.lower()
        assert "QA" in qa_settings.system_prompt or "qa" in qa_settings.system_prompt.lower()

    def test_error_handling_invalid_role_access(self, agent_factory, temp_config_file):
        """Test error handling when accessing invalid role."""
        service = RoleService(agent_factory=agent_factory)
        service.load_and_register_roles(temp_config_file)

        with pytest.raises(ValueError):
            service.get_role("nonexistent_role")

    def test_error_handling_invalid_config_file(self, agent_factory):
        """Test error handling with invalid config file."""
        service = RoleService(agent_factory=agent_factory)

        with pytest.raises(FileNotFoundError):
            service.load_and_register_roles("/nonexistent/path/config.yaml")

    def test_role_suggestion_accuracy(self, agent_factory, temp_config_file):
        """Test accuracy of role suggestion with various task descriptions."""
        service = RoleService(agent_factory=agent_factory)
        service.load_and_register_roles(temp_config_file)

        test_cases = [
            ("Implement user authentication", "dev"),
            ("Write unit tests", "qa"),
            ("Quality assurance testing", "qa"),
            ("Analyze customer feedback", "marketing"),
            ("Create marketing copy", "marketing"),
        ]

        for task, expected_role in test_cases:
            suggested = service.suggest_role(task)
            assert suggested == expected_role, f"Failed for task: {task}"

    def test_multiple_service_instances(self, agent_factory, temp_config_file):
        """Test creating multiple service instances with same factory."""
        service1 = RoleService(agent_factory=agent_factory)
        service1.load_and_register_roles(temp_config_file)

        # Create another service with same factory
        service2 = RoleService(agent_factory=agent_factory)

        # Both should have access to registered roles
        assert service1.list_available_roles() == service2.list_available_roles()

    def test_role_overwrite_behavior(self, agent_factory, temp_config_file):
        """Test behavior when overwriting existing roles."""
        service = RoleService(agent_factory=agent_factory)
        service.load_and_register_roles(temp_config_file)

        original_role = service.get_role("dev")
        assert original_role.description == "Senior Software Developer"

        # Create updated role with same name
        from gearmeshing_ai.agent.roles.models.role_definition import RoleMetadata, RoleDefinition

        metadata = RoleMetadata(
            domain="software_development",
            decision_authority="implementation",
        )

        updated_role = RoleDefinition(
            role="dev",
            description="Updated Developer Role",
            model_provider="openai",
            model_name="gpt-4-turbo",
            customized_model_name="dev-gpt4-turbo",
            system_prompt="Updated system prompt...",
            metadata=metadata,
        )

        service.register_role(updated_role)

        # Verify update
        updated = service.get_role("dev")
        assert updated.description == "Updated Developer Role"
        assert updated.model_name == "gpt-4-turbo"
