"""Pytest configuration and fixtures for E2E workflow tests."""

import pytest
from unittest.mock import MagicMock

from gearmeshing_ai.agent_core.runtime.langgraph_workflow import create_agent_workflow
from gearmeshing_ai.agent_core.runtime.approval_manager import ApprovalManager
from gearmeshing_ai.agent_core.runtime.capability_registry import CapabilityRegistry
from gearmeshing_ai.agent_core.runtime.policy_engine import PolicyEngine

from test.e2e_test.agent_core.runtime.fixtures.test_model import HybridTestModel
from test.e2e_test.agent_core.runtime.fixtures.mock_mcp_client import MockMCPClient
from test.e2e_test.agent_core.runtime.fixtures.approval_simulator import ApprovalSimulator
from test.e2e_test.agent_core.runtime.fixtures.workflow_executor import WorkflowExecutor
from test.e2e_test.agent_core.runtime.fixtures.policy_configurator import PolicyConfigurator


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
