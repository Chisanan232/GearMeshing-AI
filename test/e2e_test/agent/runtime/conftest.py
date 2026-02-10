"""Pytest configuration and fixtures for E2E workflow tests."""

from unittest.mock import MagicMock

import pytest

from gearmeshing_ai.agent.runtime.approval_manager import ApprovalManager
from gearmeshing_ai.agent.runtime.capability_registry import CapabilityRegistry
from gearmeshing_ai.agent.runtime.langgraph_workflow import create_agent_workflow
from test.e2e_test.agent.runtime.fixtures.approval_simulator import ApprovalSimulator
from test.e2e_test.agent.runtime.fixtures.mock_mcp_client import MockMCPClient
from test.e2e_test.agent.runtime.fixtures.policy_configurator import PolicyConfigurator
from test.e2e_test.agent.runtime.fixtures.test_model import HybridTestModel
from test.e2e_test.agent.runtime.fixtures.workflow_executor import WorkflowExecutor
from gearmeshing_ai.agent.roles.registry import get_global_registry
from gearmeshing_ai.agent.roles.models.role_definition import RoleDefinition, RoleMetadata
import gearmeshing_ai.agent.roles.registry as registry_module
import gearmeshing_ai.agent.roles.loader as loader_module


@pytest.fixture(autouse=True)
def reset_and_register_roles():
    """Reset global registry and register required roles for E2E tests."""
    # Clear the global registry before each test
    registry_module._global_registry = None
    loader_module._global_loader = None
    
    # Get the global registry and register required roles
    registry = get_global_registry()
    
    # Define roles needed for E2E tests
    roles_data = {
        "developer": {
            "description": "Software Developer",
            "domain": "software_development",
            "authority": "implementation",
        },
        "devops": {
            "description": "DevOps Engineer",
            "domain": "infrastructure",
            "authority": "deployment",
        },
        "dba": {
            "description": "Database Administrator",
            "domain": "database_management",
            "authority": "data_management",
        },
        "admin": {
            "description": "System Administrator",
            "domain": "system_administration",
            "authority": "full_access",
        },
        "qa": {
            "description": "QA Engineer",
            "domain": "quality_assurance",
            "authority": "quality_assessment",
        },
    }
    
    # Register roles
    for role_name, role_info in roles_data.items():
        metadata = RoleMetadata(
            domain=role_info["domain"],
            decision_authority=role_info["authority"],
        )
        
        role = RoleDefinition(
            role=role_name,
            description=role_info["description"],
            model_provider="openai",
            model_name="gpt-4",
            customized_model_name=f"{role_name}-gpt4",
            system_prompt=f"You are a {role_name}...",
            metadata=metadata,
        )
        
        registry.register(role)
    
    yield
    
    # Clean up after test
    registry_module._global_registry = None
    loader_module._global_loader = None


@pytest.fixture
def test_model():
    """Test model fixture - uses hybrid approach."""
    return HybridTestModel(use_real=False)


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client fixture."""
    return MockMCPClient()


@pytest.fixture
def approval_simulator():
    """Approval simulator fixture."""
    simulator = ApprovalSimulator()
    simulator.set_auto_approve(True)  # Auto-approve for faster tests
    return simulator


@pytest.fixture
def policy_configurator():
    """Policy configurator fixture."""
    return PolicyConfigurator()


@pytest.fixture
def policy_engine(policy_configurator):
    """Policy engine fixture."""
    return policy_configurator.get_policy_engine()


@pytest.fixture
def approval_manager():
    """Approval manager fixture."""
    return ApprovalManager()


@pytest.fixture
def capability_registry(mock_mcp_client):
    """Capability registry fixture."""
    return CapabilityRegistry(mock_mcp_client)


@pytest.fixture
def mock_agent_factory(test_model):
    """Mock agent factory fixture."""
    from unittest.mock import AsyncMock

    async def mock_run(agent, prompt):
        """Mock run that properly awaits the test model."""
        return await test_model.process_prompt(prompt)

    factory = MagicMock()

    # Mock the async methods
    factory.get_or_create_agent = AsyncMock(return_value=test_model)

    # Mock the adapter with async run method
    factory.adapter = MagicMock()
    factory.adapter.run = AsyncMock(side_effect=mock_run)

    return factory


@pytest.fixture
def workflow(mock_agent_factory, mock_mcp_client, policy_engine, approval_manager, capability_registry):
    """Workflow fixture - creates complete LangGraph workflow."""
    return create_agent_workflow(
        mock_agent_factory,
        mock_mcp_client,
        capability_registry=capability_registry,
        policy_engine=policy_engine,
        approval_manager=approval_manager,
    )


@pytest.fixture
def workflow_executor(workflow, approval_manager):
    """Workflow executor fixture."""
    return WorkflowExecutor(workflow, approval_manager)
