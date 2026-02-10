"""Unit tests for roles package service.

Tests for RoleService including:
- Loading and registering roles
- High-level API operations
- Integration with AgentFactory
- Role management operations
"""

import pytest
from unittest.mock import Mock, MagicMock

from gearmeshing_ai.agent.roles.service import RoleService, get_global_role_service
from gearmeshing_ai.agent.roles.registry import RoleRegistry
from gearmeshing_ai.agent.roles.loader import RoleLoader
from gearmeshing_ai.agent.roles.selector import RoleSelector
from gearmeshing_ai.agent.roles.models.role_definition import RoleDefinition, RoleMetadata


@pytest.fixture
def mock_factory():
    """Create a mock AgentFactory."""
    factory = Mock()
    factory.register_agent_settings = Mock()
    return factory


@pytest.fixture
def registry():
    """Create a fresh registry."""
    return RoleRegistry()


@pytest.fixture
def loader(registry):
    """Create a loader with registry."""
    return RoleLoader(registry)


@pytest.fixture
def service(mock_factory, registry, loader):
    """Create a RoleService with mocks."""
    return RoleService(
        agent_factory=mock_factory,
        registry=registry,
        loader=loader,
    )


@pytest.fixture
def sample_role():
    """Create a sample role."""
    metadata = RoleMetadata(
        domain="software_development",
        decision_authority="implementation",
    )

    return RoleDefinition(
        role="dev",
        description="Developer",
        model_provider="openai",
        model_name="gpt-4",
        customized_model_name="dev-gpt4",
        system_prompt="You are a developer...",
        tools=["read_file", "write_file"],
        metadata=metadata,
    )


class TestRoleService:
    """Test RoleService functionality."""

    def test_register_role(self, service, sample_role):
        """Test registering a single role."""
        service.register_role(sample_role)

        assert service.registry.exists("dev")
        service.agent_factory.register_agent_settings.assert_called_once()

    def test_register_role_without_factory(self, registry, loader):
        """Test registering role without factory."""
        service = RoleService(
            agent_factory=None,
            registry=registry,
            loader=loader,
        )

        metadata = RoleMetadata(
            domain="test",
            decision_authority="test",
        )

        role = RoleDefinition(
            role="test",
            description="Test",
            model_provider="openai",
            model_name="gpt-4",
            customized_model_name="test-gpt4",
            system_prompt="Test",
            metadata=metadata,
        )

        service.register_role(role)

        assert service.registry.exists("test")

    def test_get_role(self, service, sample_role):
        """Test getting a role."""
        service.register_role(sample_role)

        role = service.get_role("dev")

        assert role.role == "dev"
        assert role.description == "Developer"

    def test_get_role_nonexistent(self, service):
        """Test getting non-existent role raises error."""
        with pytest.raises(ValueError):
            service.get_role("nonexistent")

    def test_validate_role(self, service, sample_role):
        """Test validating a role."""
        service.register_role(sample_role)

        assert service.validate_role("dev") is True
        assert service.validate_role("nonexistent") is False

    def test_list_available_roles(self, service, sample_role):
        """Test listing available roles."""
        service.register_role(sample_role)

        roles = service.list_available_roles()

        assert len(roles) == 1
        assert "dev" in roles

    def test_get_role_info(self, service, sample_role):
        """Test getting role information."""
        service.register_role(sample_role)

        info = service.get_role_info("dev")

        assert info["role"] == "dev"
        assert info["description"] == "Developer"
        assert info["model_provider"] == "openai"

    def test_suggest_role(self, service, sample_role):
        """Test suggesting a role."""
        service.register_role(sample_role)

        # Add more roles for better suggestion
        metadata = RoleMetadata(
            domain="quality_assurance",
            decision_authority="quality_assessment",
        )
        qa_role = RoleDefinition(
            role="qa",
            description="QA Engineer",
            model_provider="openai",
            model_name="gpt-4",
            customized_model_name="qa-gpt4",
            system_prompt="You are a QA engineer...",
            metadata=metadata,
        )
        service.register_role(qa_role)

        role = service.suggest_role("Create test cases")

        assert role == "qa"

    def test_suggest_role_no_match(self, service, sample_role):
        """Test suggesting role with no match."""
        service.register_role(sample_role)

        role = service.suggest_role("xyz abc def")

        assert role is None

    def test_get_role_for_task_with_preference(self, service, sample_role):
        """Test getting role for task with preference."""
        service.register_role(sample_role)

        role = service.get_role_for_task(
            "Some task",
            preferred_role="dev",
        )

        assert role == "dev"

    def test_get_role_for_task_without_preference(self, service, sample_role):
        """Test getting role for task without preference."""
        service.register_role(sample_role)

        metadata = RoleMetadata(
            domain="quality_assurance",
            decision_authority="quality_assessment",
        )
        qa_role = RoleDefinition(
            role="qa",
            description="QA Engineer",
            model_provider="openai",
            model_name="gpt-4",
            customized_model_name="qa-gpt4",
            system_prompt="You are a QA engineer...",
            metadata=metadata,
        )
        service.register_role(qa_role)

        role = service.get_role_for_task("Create test cases")

        assert role == "qa"

    def test_get_roles_by_domain(self, service, sample_role):
        """Test getting roles by domain."""
        service.register_role(sample_role)

        roles = service.get_roles_by_domain("software_development")

        assert len(roles) == 1
        assert "dev" in roles

    def test_get_roles_by_authority(self, service, sample_role):
        """Test getting roles by authority."""
        service.register_role(sample_role)

        roles = service.get_roles_by_authority("implementation")

        assert len(roles) == 1
        assert "dev" in roles

    def test_print_available_roles(self, service, sample_role, capsys):
        """Test printing available roles."""
        service.register_role(sample_role)

        service.print_available_roles()

        captured = capsys.readouterr()

        assert "Available Roles" in captured.out
        assert "dev" in captured.out


class TestRoleServiceWithFactory:
    """Test RoleService integration with AgentFactory."""

    def test_load_and_register_roles_calls_factory(self, registry, loader, mock_factory, tmp_path):
        """Test that load_and_register_roles registers with factory."""
        import yaml

        # Create temporary YAML file
        config = {
            "roles": {
                "dev": {
                    "description": "Developer",
                    "model_settings": {
                        "customized_name": "dev-gpt4",
                        "provider": "openai",
                        "model": "gpt-4",
                    },
                    "system_prompt": "You are a developer...",
                    "metadata": {
                        "domain": "software_development",
                        "decision_authority": "implementation",
                    },
                },
            }
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        service = RoleService(
            agent_factory=mock_factory,
            registry=registry,
            loader=loader,
        )

        roles = service.load_and_register_roles(str(config_file))

        assert len(roles) == 1
        mock_factory.register_agent_settings.assert_called_once()

    def test_load_and_register_roles_without_factory(self, registry, loader, tmp_path):
        """Test loading and registering roles without factory."""
        import yaml

        config = {
            "roles": {
                "dev": {
                    "description": "Developer",
                    "model_settings": {
                        "customized_name": "dev-gpt4",
                        "provider": "openai",
                        "model": "gpt-4",
                    },
                    "system_prompt": "You are a developer...",
                    "metadata": {
                        "domain": "software_development",
                        "decision_authority": "implementation",
                    },
                },
            }
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        service = RoleService(
            agent_factory=None,
            registry=registry,
            loader=loader,
        )

        roles = service.load_and_register_roles(str(config_file))

        assert len(roles) == 1
        # Loader registers with its own registry
        assert loader.registry.exists("dev")


class TestGlobalRoleService:
    """Test global RoleService singleton."""

    def test_get_global_role_service_singleton(self):
        """Test that get_global_role_service returns same instance."""
        service1 = get_global_role_service()
        service2 = get_global_role_service()

        assert service1 is service2

    def test_get_global_role_service_with_factory(self, mock_factory):
        """Test creating global service with factory."""
        # Clear any existing global instance first
        import gearmeshing_ai.agent.roles.service as service_module
        service_module._global_service = None

        service = get_global_role_service(mock_factory)

        assert service.agent_factory is mock_factory


class TestRoleServiceEdgeCases:
    """Test edge cases for RoleService."""

    def test_service_with_empty_registry(self, mock_factory):
        """Test service with empty registry."""
        service = RoleService(agent_factory=mock_factory)

        assert service.list_available_roles() == []
        assert service.suggest_role("any task") is None

    def test_service_register_multiple_roles(self, service):
        """Test registering multiple roles."""
        for i in range(5):
            metadata = RoleMetadata(
                domain=f"domain_{i}",
                decision_authority=f"authority_{i}",
            )

            role = RoleDefinition(
                role=f"role_{i}",
                description=f"Role {i}",
                model_provider="openai",
                model_name="gpt-4",
                customized_model_name=f"role-{i}-gpt4",
                system_prompt=f"Prompt {i}",
                metadata=metadata,
            )

            service.register_role(role)

        assert len(service.list_available_roles()) == 5

    def test_service_overwrite_role(self, service, sample_role):
        """Test overwriting an existing role."""
        service.register_role(sample_role)

        # Create updated role
        metadata = RoleMetadata(
            domain="software_development",
            decision_authority="implementation",
        )

        updated_role = RoleDefinition(
            role="dev",
            description="Updated Developer",
            model_provider="openai",
            model_name="gpt-4-turbo",
            customized_model_name="dev-gpt4-turbo",
            system_prompt="Updated prompt...",
            metadata=metadata,
        )

        service.register_role(updated_role)

        role = service.get_role("dev")

        assert role.description == "Updated Developer"
        assert role.model_name == "gpt-4-turbo"
