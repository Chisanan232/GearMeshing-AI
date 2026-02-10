"""Pytest configuration for agent runtime nodes tests."""

import pytest

import gearmeshing_ai.agent.roles.registry as registry_module
from gearmeshing_ai.agent.roles.models.role_definition import RoleDefinition, RoleMetadata
from gearmeshing_ai.agent.roles.registry import RoleRegistry
from gearmeshing_ai.agent.roles.selector import RoleSelector


@pytest.fixture(autouse=True)
def reset_global_registry():
    """Reset global registry before each test to avoid pollution."""
    # Clear the global registry before each test
    registry_module._global_registry = None
    yield
    # Clean up after test
    registry_module._global_registry = None


@pytest.fixture
def mock_role_registry():
    """Create a mock role registry with developer role registered."""
    registry = RoleRegistry()

    # Register developer role
    metadata = RoleMetadata(
        domain="software_development",
        decision_authority="implementation",
    )
    developer_role = RoleDefinition(
        role="developer",
        description="Software Developer",
        model_provider="openai",
        model_name="gpt-4",
        customized_model_name="dev-gpt4",
        system_prompt="You are a software developer...",
        metadata=metadata,
    )
    registry.register(developer_role)

    return registry


@pytest.fixture
def mock_role_selector(mock_role_registry):
    """Create a role selector with developer role."""
    return RoleSelector(mock_role_registry)
