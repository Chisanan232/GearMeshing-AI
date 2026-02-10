"""Pytest configuration for agent roles integration tests."""

import pytest
import gearmeshing_ai.agent.roles.registry as registry_module
import gearmeshing_ai.agent.roles.loader as loader_module


@pytest.fixture(autouse=True)
def reset_global_registry():
    """Reset global registry and loader before each test to avoid pollution."""
    # Clear the global registry before each test
    registry_module._global_registry = None
    loader_module._global_loader = None
    yield
    # Clean up after test
    registry_module._global_registry = None
    loader_module._global_loader = None
