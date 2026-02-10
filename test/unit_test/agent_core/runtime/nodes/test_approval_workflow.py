"""Unit tests for Approval Workflow nodes.

Tests cover approval workflow, approval resolution, and state management.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from gearmeshing_ai.agent_core.models.actions import MCPToolInfo
from gearmeshing_ai.agent_core.runtime.approval_manager import ApprovalManager, ApprovalStatus
from gearmeshing_ai.agent_core.runtime.nodes.approval_workflow import (
    approval_resolution_node,
    approval_workflow_node,
)
from gearmeshing_ai.agent_core.runtime.policy_engine import PolicyEngine
from gearmeshing_ai.agent_core.runtime.models.workflow_state import (
    ExecutionContext,
    WorkflowState,
    WorkflowStatus,
)

from ..conftest import merge_state_update


@pytest.fixture
def sample_tool() -> MCPToolInfo:
    """Create a sample tool."""
    return MCPToolInfo(
        name="deploy_app",
        description="Deploy application",
        mcp_server="deploy_server",
        parameters={"environment": {"type": "string"}},
    )


@pytest.fixture
def execution_context() -> ExecutionContext:
    """Create a sample execution context."""
    return ExecutionContext(
        task_description="Deploy application",
        agent_role="developer",
        user_id="user_123",
    )


@pytest.fixture
def workflow_state(execution_context: ExecutionContext) -> WorkflowState:
    """Create a sample workflow state."""
    return WorkflowState(
        run_id="run_123",
        status=WorkflowStatus(state="PENDING"),
        context=execution_context,
    )


@pytest.fixture
def approval_manager() -> ApprovalManager:
    """Create an approval manager."""
    return ApprovalManager()


@pytest.fixture
def policy_engine() -> PolicyEngine:
    """Create a policy engine."""
    return PolicyEngine()


class TestApprovalWorkflowNode:
    """Tests for approval workflow node."""

    @pytest.mark.asyncio
    async def test_approval_workflow_node_no_approvals(
        self,
        workflow_state: WorkflowState,
        policy_engine: PolicyEngine,
        approval_manager: ApprovalManager,
    ) -> None:
        """Test approval workflow node with no approvals."""
        result = await approval_workflow_node(workflow_state, policy_engine, approval_manager)
        updated_state = merge_state_update(workflow_state, result)
        assert updated_state.status.state == "APPROVAL_COMPLETE"
        assert "No approvals required" in updated_state.status.message

    @pytest.mark.asyncio
    async def test_approval_workflow_node_with_pending_approvals(
        self,
        workflow_state: WorkflowState,
        policy_engine: PolicyEngine,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test approval workflow node with pending approvals."""
        approval_manager.create_approval("run_123", sample_tool, execution_context)

        result = await approval_workflow_node(workflow_state, policy_engine, approval_manager)
        updated_state = merge_state_update(workflow_state, result)
        assert updated_state.status.state == "AWAITING_APPROVAL"
        assert "Waiting for" in updated_state.status.message

    @pytest.mark.asyncio
    async def test_approval_workflow_node_with_approved_approvals(
        self,
        workflow_state: WorkflowState,
        policy_engine: PolicyEngine,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test approval workflow node with approved approvals."""
        approval = approval_manager.create_approval("run_123", sample_tool, execution_context)
        approval_manager.approve_approval(approval.approval_id, "admin_user")

        result = await approval_workflow_node(workflow_state, policy_engine, approval_manager)
        updated_state = merge_state_update(workflow_state, result)
        assert updated_state.status.state == "APPROVAL_COMPLETE"
        assert "approved" in updated_state.status.message.lower()

    @pytest.mark.asyncio
    async def test_approval_workflow_node_with_rejected_approvals(
        self,
        workflow_state: WorkflowState,
        policy_engine: PolicyEngine,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test approval workflow node with rejected approvals."""
        approval = approval_manager.create_approval("run_123", sample_tool, execution_context)
        approval_manager.reject_approval(approval.approval_id, "admin_user", "Not safe")

        result = await approval_workflow_node(workflow_state, policy_engine, approval_manager)
        updated_state = merge_state_update(workflow_state, result)
        assert updated_state.status.state == "APPROVAL_REJECTED"
        assert "rejected" in updated_state.status.message.lower()

    @pytest.mark.asyncio
    async def test_approval_workflow_node_with_mixed_approvals(
        self,
        workflow_state: WorkflowState,
        policy_engine: PolicyEngine,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test approval workflow node with mixed approval statuses."""
        approval1 = approval_manager.create_approval("run_123", sample_tool, execution_context)
        approval2 = approval_manager.create_approval("run_123", sample_tool, execution_context)

        approval_manager.approve_approval(approval1.approval_id, "admin_user")
        approval_manager.reject_approval(approval2.approval_id, "admin_user")

        result = await approval_workflow_node(workflow_state, policy_engine, approval_manager)
        updated_state = merge_state_update(workflow_state, result)
        assert updated_state.status.state == "APPROVAL_REJECTED"

    @pytest.mark.asyncio
    async def test_approval_workflow_node_preserves_run_id(
        self,
        workflow_state: WorkflowState,
        policy_engine: PolicyEngine,
        approval_manager: ApprovalManager,
    ) -> None:
        """Test approval workflow node preserves run_id."""
        result = await approval_workflow_node(workflow_state, policy_engine, approval_manager)
        updated_state = merge_state_update(workflow_state, result)
        assert updated_state.run_id == "run_123"

    @pytest.mark.asyncio
    async def test_approval_workflow_node_preserves_context(
        self,
        workflow_state: WorkflowState,
        policy_engine: PolicyEngine,
        approval_manager: ApprovalManager,
    ) -> None:
        """Test approval workflow node preserves context."""
        result = await approval_workflow_node(workflow_state, policy_engine, approval_manager)
        updated_state = merge_state_update(workflow_state, result)
        assert updated_state.context.agent_role == "developer"
        assert updated_state.context.user_id == "user_123"

    @pytest.mark.asyncio
    async def test_approval_workflow_node_error_handling(
        self,
        workflow_state: WorkflowState,
        policy_engine: PolicyEngine,
    ) -> None:
        """Test approval workflow node error handling."""
        # Create a mock that raises an error
        mock_manager = MagicMock()
        mock_manager.get_pending_approvals.side_effect = RuntimeError("Manager error")

        result = await approval_workflow_node(workflow_state, policy_engine, mock_manager)
        updated_state = merge_state_update(workflow_state, result)
        assert updated_state.status.state == "FAILED"
        assert updated_state.status.error is not None


class TestApprovalResolutionNode:
    """Tests for approval resolution node."""

    @pytest.mark.asyncio
    async def test_approval_resolution_node_no_approvals(
        self,
        workflow_state: WorkflowState,
        approval_manager: ApprovalManager,
    ) -> None:
        """Test approval resolution node with no approvals."""
        result = await approval_resolution_node(workflow_state, approval_manager)
        updated_state = merge_state_update(workflow_state, result)
        assert updated_state.status.state == "COMPLETED"

    @pytest.mark.asyncio
    async def test_approval_resolution_node_with_pending_approvals(
        self,
        workflow_state: WorkflowState,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test approval resolution node with pending approvals."""
        approval_manager.create_approval("run_123", sample_tool, execution_context)

        result = await approval_resolution_node(workflow_state, approval_manager)
        updated_state = merge_state_update(workflow_state, result)
        assert updated_state.status.state == "AWAITING_APPROVAL"

    @pytest.mark.asyncio
    async def test_approval_resolution_node_with_approved_approvals(
        self,
        workflow_state: WorkflowState,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test approval resolution node with approved approvals."""
        approval = approval_manager.create_approval("run_123", sample_tool, execution_context)
        approval_manager.approve_approval(approval.approval_id, "admin_user")

        result = await approval_resolution_node(workflow_state, approval_manager)
        updated_state = merge_state_update(workflow_state, result)
        assert updated_state.status.state == "COMPLETED"
        assert "resolved" in updated_state.status.message.lower()

    @pytest.mark.asyncio
    async def test_approval_resolution_node_with_rejected_approvals(
        self,
        workflow_state: WorkflowState,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test approval resolution node with rejected approvals."""
        approval = approval_manager.create_approval("run_123", sample_tool, execution_context)
        approval_manager.reject_approval(approval.approval_id, "admin_user", "Not safe")

        result = await approval_resolution_node(workflow_state, approval_manager)
        updated_state = merge_state_update(workflow_state, result)
        assert updated_state.status.state == "APPROVAL_REJECTED"
        assert "rejected" in updated_state.status.message.lower()

    @pytest.mark.asyncio
    async def test_approval_resolution_node_with_multiple_approvals(
        self,
        workflow_state: WorkflowState,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test approval resolution node with multiple approvals."""
        approval1 = approval_manager.create_approval("run_123", sample_tool, execution_context)
        approval2 = approval_manager.create_approval("run_123", sample_tool, execution_context)
        approval3 = approval_manager.create_approval("run_123", sample_tool, execution_context)

        approval_manager.approve_approval(approval1.approval_id, "admin_user")
        approval_manager.approve_approval(approval2.approval_id, "admin_user")
        approval_manager.approve_approval(approval3.approval_id, "admin_user")

        result = await approval_resolution_node(workflow_state, approval_manager)
        updated_state = merge_state_update(workflow_state, result)
        assert updated_state.status.state == "COMPLETED"
        assert "3" in updated_state.status.message

    @pytest.mark.asyncio
    async def test_approval_resolution_node_preserves_run_id(
        self,
        workflow_state: WorkflowState,
        approval_manager: ApprovalManager,
    ) -> None:
        """Test approval resolution node preserves run_id."""
        result = await approval_resolution_node(workflow_state, approval_manager)
        updated_state = merge_state_update(workflow_state, result)
        assert updated_state.run_id == "run_123"

    @pytest.mark.asyncio
    async def test_approval_resolution_node_error_handling(
        self,
        workflow_state: WorkflowState,
    ) -> None:
        """Test approval resolution node error handling."""
        # Create a mock that raises an error
        mock_manager = MagicMock()
        mock_manager.get_approval_stats.side_effect = RuntimeError("Manager error")

        result = await approval_resolution_node(workflow_state, mock_manager)
        updated_state = merge_state_update(workflow_state, result)
        assert updated_state.status.state == "FAILED"
        assert updated_state.status.error is not None

    @pytest.mark.asyncio
    async def test_approval_resolution_node_statistics(
        self,
        workflow_state: WorkflowState,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test approval resolution node with statistics."""
        approval1 = approval_manager.create_approval("run_123", sample_tool, execution_context)
        approval2 = approval_manager.create_approval("run_123", sample_tool, execution_context)

        approval_manager.approve_approval(approval1.approval_id, "admin_user")
        approval_manager.reject_approval(approval2.approval_id, "admin_user")

        result = await approval_resolution_node(workflow_state, approval_manager)
        updated_state = merge_state_update(workflow_state, result)
        assert updated_state.status.state == "APPROVAL_REJECTED"
        assert "1" in updated_state.status.message
