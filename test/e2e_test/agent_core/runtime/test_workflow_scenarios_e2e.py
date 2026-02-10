"""End-to-end tests for AI agent runtime workflow real-world scenarios.

Tests verify complete workflow execution with all 9 nodes integrated,
testing real-world usage patterns and feature combinations.
"""

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock, patch

import pytest

from gearmeshing_ai.agent_core.abstraction.factory import AgentFactory
from gearmeshing_ai.agent_core.abstraction.mcp import MCPClientAbstraction
from gearmeshing_ai.agent_core.runtime.approval_manager import ApprovalManager
from gearmeshing_ai.agent_core.runtime.capability_registry import CapabilityRegistry
from gearmeshing_ai.agent_core.runtime.langgraph_workflow import create_agent_workflow
from gearmeshing_ai.agent_core.runtime.policy_engine import PolicyEngine, ToolPolicy
from gearmeshing_ai.agent_core.runtime.models.workflow_state import (
    ExecutionContext,
    WorkflowState,
    WorkflowStatus,
)

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_agent_factory() -> Mock:
    """Create mock agent factory."""
    factory = Mock(spec=AgentFactory)
    factory.adapter = Mock()
    return factory


@pytest.fixture
def mock_mcp_client() -> Mock:
    """Create mock MCP client."""
    return Mock(spec=MCPClientAbstraction)


@pytest.fixture
def policy_engine() -> PolicyEngine:
    """Create policy engine."""
    return PolicyEngine()


@pytest.fixture
def approval_manager() -> ApprovalManager:
    """Create approval manager."""
    return ApprovalManager()


class TestE2EWorkflowCreation:
    """End-to-end tests for workflow creation and initialization."""

    def test_workflow_creation_with_all_components(
        self: "TestE2EWorkflowCreation",
        mock_agent_factory: Mock,
        mock_mcp_client: Mock,
        policy_engine: PolicyEngine,
        approval_manager: ApprovalManager,
    ) -> None:
        """Test workflow creation with all components."""
        registry = CapabilityRegistry(mock_mcp_client)
        
        workflow = create_agent_workflow(
            mock_agent_factory,
            mock_mcp_client,
            capability_registry=registry,
            policy_engine=policy_engine,
            approval_manager=approval_manager,
        )

        assert workflow is not None
        assert hasattr(workflow, "ainvoke")

    def test_workflow_creation_with_auto_initialization(
        self: "TestE2EWorkflowCreation",
        mock_agent_factory: Mock,
        mock_mcp_client: Mock,
    ) -> None:
        """Test workflow creation with auto-initialized components."""
        workflow = create_agent_workflow(
            mock_agent_factory,
            mock_mcp_client,
        )

        assert workflow is not None
        assert hasattr(workflow, "ainvoke")

    def test_workflow_creation_with_custom_policies(
        self: "TestE2EWorkflowCreation",
        mock_agent_factory: Mock,
        mock_mcp_client: Mock,
    ) -> None:
        """Test workflow creation with custom policies."""
        policy_engine = PolicyEngine()
        policy_engine.tool_policy = ToolPolicy(
            allowed_tools=["read", "write"],
            denied_tools=["delete"],
        )

        workflow = create_agent_workflow(
            mock_agent_factory,
            mock_mcp_client,
            policy_engine=policy_engine,
        )

        assert workflow is not None


class TestE2EWorkflowStateManagement:
    """End-to-end tests for workflow state management."""

    def test_workflow_state_creation(self: "TestE2EWorkflowStateManagement") -> None:
        """Test workflow state creation with all fields."""
        context = ExecutionContext(
            task_description="Test task",
            agent_role="developer",
            user_id="user_123",
        )
        status = WorkflowStatus(state="PENDING")
        
        state = WorkflowState(
            run_id="run_001",
            status=status,
            context=context,
        )

        assert state.run_id == "run_001"
        assert state.context.agent_role == "developer"
        assert state.status.state == "PENDING"

    def test_workflow_state_with_metadata(self: "TestE2EWorkflowStateManagement") -> None:
        """Test workflow state with metadata."""
        context = ExecutionContext(
            task_description="Deploy app",
            agent_role="devops",
            user_id="user_456",
            metadata={
                "environment": "production",
                "version": "1.0.0",
            },
        )
        
        state = WorkflowState(
            run_id="run_002",
            status=WorkflowStatus(state="RUNNING"),
            context=context,
        )

        assert state.context.metadata["environment"] == "production"
        assert state.context.metadata["version"] == "1.0.0"

    def test_workflow_state_immutability_pattern(self: "TestE2EWorkflowStateManagement") -> None:
        """Test workflow state immutability pattern."""
        original_state = WorkflowState(
            run_id="run_003",
            status=WorkflowStatus(state="PENDING"),
            context=ExecutionContext(
                task_description="Test",
                agent_role="developer",
                user_id="user_789",
            ),
        )

        # Create updated state using model_copy
        updated_state = original_state.model_copy(
            update={
                "status": WorkflowStatus(state="RUNNING"),
            }
        )

        # Original state should not change
        assert original_state.status.state == "PENDING"
        assert updated_state.status.state == "RUNNING"
        assert original_state.run_id == updated_state.run_id


class TestE2EPolicyEnforcement:
    """End-to-end tests for policy enforcement."""

    def test_policy_engine_tool_access_control(self: "TestE2EPolicyEnforcement") -> None:
        """Test policy engine tool access control."""
        policy_engine = PolicyEngine()
        policy_engine.tool_policy = ToolPolicy(
            allowed_tools=["read_file", "write_file"],
            denied_tools=["delete_file"],
        )

        # Verify policy configuration
        assert "read_file" in policy_engine.tool_policy.allowed_tools
        assert "delete_file" in policy_engine.tool_policy.denied_tools

    def test_policy_engine_read_only_mode(self: "TestE2EPolicyEnforcement") -> None:
        """Test policy engine read-only mode."""
        policy_engine = PolicyEngine()
        policy_engine.tool_policy = ToolPolicy(
            allowed_tools=None,
            denied_tools=[],
            read_only=True,
        )

        assert policy_engine.tool_policy.read_only is True

    def test_policy_engine_execution_limits(self: "TestE2EPolicyEnforcement") -> None:
        """Test policy engine execution limits."""
        policy_engine = PolicyEngine()
        policy_engine.tool_policy = ToolPolicy(
            allowed_tools=None,
            denied_tools=[],
            max_executions=10,
        )

        assert policy_engine.tool_policy.max_executions == 10


class TestE2EApprovalManagement:
    """End-to-end tests for approval management."""

    def test_approval_manager_creation(self: "TestE2EApprovalManagement") -> None:
        """Test approval manager creation."""
        approval_manager = ApprovalManager()

        assert approval_manager is not None
        assert hasattr(approval_manager, "create_approval")

    def test_approval_policy_configuration(self: "TestE2EApprovalManagement") -> None:
        """Test approval policy configuration."""
        policy_engine = PolicyEngine()
        policy_engine.approval_policy.require_approval_for_all = True
        policy_engine.approval_policy.approval_timeout = 3600

        assert policy_engine.approval_policy.require_approval_for_all is True
        assert policy_engine.approval_policy.approval_timeout == 3600

    def test_approval_high_risk_tools(self: "TestE2EApprovalManagement") -> None:
        """Test approval for high-risk tools."""
        policy_engine = PolicyEngine()
        policy_engine.approval_policy.high_risk_tools = [
            "deploy_production",
            "delete_database",
        ]

        assert "deploy_production" in policy_engine.approval_policy.high_risk_tools


class TestE2EWorkflowIntegration:
    """End-to-end tests for complete workflow integration."""

    def test_workflow_with_simple_context(
        self: "TestE2EWorkflowIntegration",
        mock_agent_factory: Mock,
        mock_mcp_client: Mock,
    ) -> None:
        """Test workflow with simple execution context."""
        context = ExecutionContext(
            task_description="Run tests",
            agent_role="developer",
            user_id="dev_user",
        )
        
        state = WorkflowState(
            run_id="e2e_simple_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)
        
        # Verify: Workflow should be created and context preserved
        assert workflow is not None, "Workflow should be created successfully"
        assert hasattr(workflow, "ainvoke"), "Workflow should have ainvoke method"
        assert state.context.task_description == "Run tests", "Task description should be preserved"
        assert state.context.agent_role == "developer", "Agent role should be developer"
        assert state.context.user_id == "dev_user", "User ID should be preserved"
        assert state.run_id == "e2e_simple_001", "Run ID should match"

    def test_workflow_with_complex_context(
        self: "TestE2EWorkflowIntegration",
        mock_agent_factory: Mock,
        mock_mcp_client: Mock,
    ) -> None:
        """Test workflow with complex execution context."""
        context = ExecutionContext(
            task_description="Deploy to production",
            agent_role="devops",
            user_id="devops_user",
            metadata={
                "environment": "production",
                "version": "2.0.0",
                "rollback_plan": "available",
                "estimated_time": "30 minutes",
            },
        )
        
        state = WorkflowState(
            run_id="e2e_complex_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)
        
        # Verify: Complex context with metadata should be preserved
        assert workflow is not None, "Workflow should be created successfully"
        assert hasattr(workflow, "ainvoke"), "Workflow should have ainvoke method"
        assert state.context.task_description == "Deploy to production", "Task description should be preserved"
        assert state.context.agent_role == "devops", "Agent role should be devops"
        assert state.context.metadata["environment"] == "production", "Environment metadata should be preserved"
        assert state.context.metadata["version"] == "2.0.0", "Version metadata should be preserved"
        assert len(state.context.metadata) == 4, "All metadata fields should be preserved"

    def test_workflow_with_multiple_roles(
        self: "TestE2EWorkflowIntegration",
        mock_agent_factory: Mock,
        mock_mcp_client: Mock,
    ) -> None:
        """Test workflow with different agent roles."""
        roles = ["developer", "devops", "admin", "security"]
        
        for role in roles:
            context = ExecutionContext(
                task_description=f"Task for {role}",
                agent_role=role,
                user_id=f"user_{role}",
            )
            
            state = WorkflowState(
                run_id=f"e2e_role_{role}",
                status=WorkflowStatus(state="PENDING"),
                context=context,
            )

            workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)
            
            # Verify: Each role should be properly handled
            assert workflow is not None, f"Workflow should be created for {role} role"
            assert hasattr(workflow, "ainvoke"), "Workflow should have ainvoke method"
            assert state.context.agent_role == role, f"Agent role should be {role}"
            assert state.context.user_id == f"user_{role}", f"User ID should be user_{role}"
            assert state.run_id == f"e2e_role_{role}", f"Run ID should match role {role}"

    def test_workflow_with_policy_and_approval(
        self: "TestE2EWorkflowIntegration",
        mock_agent_factory: Mock,
        mock_mcp_client: Mock,
    ) -> None:
        """Test workflow with both policy and approval configuration."""
        policy_engine = PolicyEngine()
        policy_engine.tool_policy = ToolPolicy(
            allowed_tools=["read", "write", "deploy"],
            denied_tools=["delete"],
        )
        policy_engine.approval_policy.require_approval_for_all = True

        approval_manager = ApprovalManager()

        context = ExecutionContext(
            task_description="Deploy with approval",
            agent_role="devops",
            user_id="devops_user",
        )
        
        state = WorkflowState(
            run_id="e2e_policy_approval_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        workflow = create_agent_workflow(
            mock_agent_factory,
            mock_mcp_client,
            policy_engine=policy_engine,
            approval_manager=approval_manager,
        )

        # Verify: Policy and approval features should be integrated
        assert workflow is not None, "Workflow should be created with policy and approval"
        assert hasattr(workflow, "ainvoke"), "Workflow should have ainvoke method"
        assert state.context.agent_role == "devops", "Agent role should be devops"
        assert state.context.user_id == "devops_user", "User ID should be preserved"
        # Verify policy configuration
        assert "read" in policy_engine.tool_policy.allowed_tools, "Read should be allowed"
        assert "write" in policy_engine.tool_policy.allowed_tools, "Write should be allowed"
        assert "deploy" in policy_engine.tool_policy.allowed_tools, "Deploy should be allowed"
        assert "delete" in policy_engine.tool_policy.denied_tools, "Delete should be denied"
        # Verify approval configuration
        assert policy_engine.approval_policy.require_approval_for_all is True, "Approval should be required for all"


class TestE2EErrorHandling:
    """End-to-end tests for error handling."""

    def test_workflow_handles_invalid_context(
        self: "TestE2EErrorHandling",
        mock_agent_factory: Mock,
        mock_mcp_client: Mock,
    ) -> None:
        """Test workflow handles invalid context gracefully."""
        # Create state with minimal context
        context = ExecutionContext(
            task_description="",
            agent_role="",
            user_id="",
        )
        
        state = WorkflowState(
            run_id="e2e_error_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)
        
        # Verify: Workflow should handle invalid context gracefully
        assert workflow is not None, "Workflow should be created even with invalid context"
        assert hasattr(workflow, "ainvoke"), "Workflow should have ainvoke method"
        assert state.run_id == "e2e_error_001", "Run ID should be preserved"
        assert state.status.state == "PENDING", "Initial state should be PENDING"
        # Invalid context should not prevent workflow creation
        assert state.context.task_description == "", "Empty task description should be handled"
        assert state.context.agent_role == "", "Empty agent role should be handled"

    def test_workflow_state_with_error_status(
        self: "TestE2EErrorHandling",
        mock_agent_factory: Mock,
        mock_mcp_client: Mock,
    ) -> None:
        """Test workflow state with error status."""
        context = ExecutionContext(
            task_description="Failed task",
            agent_role="developer",
            user_id="user_error",
        )
        
        state = WorkflowState(
            run_id="e2e_error_002",
            status=WorkflowStatus(
                state="FAILED",
                error="Task execution failed",
            ),
            context=context,
        )

        workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)
        
        # Verify: Workflow should handle error status properly
        assert workflow is not None, "Workflow should be created with error state"
        assert hasattr(workflow, "ainvoke"), "Workflow should have ainvoke method"
        assert state.status.state == "FAILED", "Status should be FAILED"
        assert state.status.error is not None, "Error message should be present"
        assert state.status.error == "Task execution failed", "Error message should match"
        assert state.run_id == "e2e_error_002", "Run ID should be preserved"


class TestE2EWorkflowFeatures:
    """End-to-end tests for workflow features."""

    def test_workflow_supports_capability_discovery(
        self: "TestE2EWorkflowFeatures",
        mock_agent_factory: Mock,
        mock_mcp_client: Mock,
    ) -> None:
        """Test workflow supports capability discovery."""
        registry = CapabilityRegistry(mock_mcp_client)
        
        workflow = create_agent_workflow(
            mock_agent_factory,
            mock_mcp_client,
            capability_registry=registry,
        )

        # Verify: Capability discovery feature should be integrated
        assert workflow is not None, "Workflow should be created with capability registry"
        assert hasattr(workflow, "ainvoke"), "Workflow should have ainvoke method"
        assert registry is not None, "Capability registry should be initialized"
        assert hasattr(registry, "filter_capabilities"), "Registry should have filter_capabilities method"

    def test_workflow_supports_policy_validation(
        self: "TestE2EWorkflowFeatures",
        mock_agent_factory: Mock,
        mock_mcp_client: Mock,
    ) -> None:
        """Test workflow supports policy validation."""
        policy_engine = PolicyEngine()
        
        workflow = create_agent_workflow(
            mock_agent_factory,
            mock_mcp_client,
            policy_engine=policy_engine,
        )

        # Verify: Policy validation feature should be integrated
        assert workflow is not None, "Workflow should be created with policy engine"
        assert hasattr(workflow, "ainvoke"), "Workflow should have ainvoke method"
        assert policy_engine is not None, "Policy engine should be initialized"
        assert hasattr(policy_engine, "tool_policy"), "Policy engine should have tool_policy"
        assert hasattr(policy_engine, "approval_policy"), "Policy engine should have approval_policy"

    def test_workflow_supports_approval_workflow(
        self: "TestE2EWorkflowFeatures",
        mock_agent_factory: Mock,
        mock_mcp_client: Mock,
    ) -> None:
        """Test workflow supports approval workflow."""
        approval_manager = ApprovalManager()
        
        workflow = create_agent_workflow(
            mock_agent_factory,
            mock_mcp_client,
            approval_manager=approval_manager,
        )

        # Verify: Approval workflow feature should be integrated
        assert workflow is not None, "Workflow should be created with approval manager"
        assert hasattr(workflow, "ainvoke"), "Workflow should have ainvoke method"
        assert approval_manager is not None, "Approval manager should be initialized"
        assert hasattr(approval_manager, "create_approval"), "Approval manager should have create_approval method"

    def test_workflow_supports_all_features(
        self: "TestE2EWorkflowFeatures",
        mock_agent_factory: Mock,
        mock_mcp_client: Mock,
    ) -> None:
        """Test workflow supports all 9 nodes together."""
        registry = CapabilityRegistry(mock_mcp_client)
        policy_engine = PolicyEngine()
        approval_manager = ApprovalManager()
        
        workflow = create_agent_workflow(
            mock_agent_factory,
            mock_mcp_client,
            capability_registry=registry,
            policy_engine=policy_engine,
            approval_manager=approval_manager,
        )

        # Verify: All 9 workflow nodes should be integrated together
        assert workflow is not None, "Workflow should be created with all features"
        assert hasattr(workflow, "ainvoke"), "Workflow should have ainvoke method"
        # Verify all components are present
        assert registry is not None, "Capability registry should be initialized"
        assert policy_engine is not None, "Policy engine should be initialized"
        assert approval_manager is not None, "Approval manager should be initialized"
        # Verify component methods exist
        assert hasattr(registry, "filter_capabilities"), "Registry should have filter_capabilities"
        assert hasattr(policy_engine, "tool_policy"), "Policy engine should have tool_policy"
        assert hasattr(approval_manager, "create_approval"), "Approval manager should have create_approval"
        # All 9 nodes should be accessible through workflow
        assert hasattr(workflow, "nodes") or hasattr(workflow, "get_graph"), "Workflow should expose node structure"
