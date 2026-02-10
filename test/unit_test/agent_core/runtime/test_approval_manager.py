"""Unit tests for Approval Manager.

Tests cover approval creation, tracking, resolution, and lifecycle management.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from gearmeshing_ai.agent_core.models.actions import MCPToolInfo
from gearmeshing_ai.agent_core.runtime.approval_manager import (
    ApprovalManager,
    ApprovalRequest,
    ApprovalStatus,
)
from gearmeshing_ai.agent_core.runtime.workflow_state import ExecutionContext


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
def approval_manager() -> ApprovalManager:
    """Create an approval manager."""
    return ApprovalManager()


class TestApprovalRequest:
    """Tests for ApprovalRequest."""

    def test_approval_request_initialization(
        self,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test ApprovalRequest initialization."""
        approval = ApprovalRequest("run_123", sample_tool, execution_context)

        assert approval.run_id == "run_123"
        assert approval.tool == sample_tool
        assert approval.context == execution_context
        assert approval.status == ApprovalStatus.PENDING
        assert approval.resolved_at is None
        assert approval.resolved_by is None

    def test_approval_request_approve(
        self,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test approving an approval request."""
        approval = ApprovalRequest("run_123", sample_tool, execution_context)

        approval.approve("admin_user", "Looks good")

        assert approval.status == ApprovalStatus.APPROVED
        assert approval.resolved_by == "admin_user"
        assert approval.resolution_reason == "Looks good"
        assert approval.resolved_at is not None

    def test_approval_request_reject(
        self,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test rejecting an approval request."""
        approval = ApprovalRequest("run_123", sample_tool, execution_context)

        approval.reject("admin_user", "Not safe")

        assert approval.status == ApprovalStatus.REJECTED
        assert approval.resolved_by == "admin_user"
        assert approval.resolution_reason == "Not safe"
        assert approval.resolved_at is not None

    def test_approval_request_is_approved(
        self,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test is_approved check."""
        approval = ApprovalRequest("run_123", sample_tool, execution_context)

        assert approval.is_approved() is False

        approval.approve("admin_user")

        assert approval.is_approved() is True

    def test_approval_request_is_pending(
        self,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test is_pending check."""
        approval = ApprovalRequest("run_123", sample_tool, execution_context)

        assert approval.is_pending() is True

        approval.approve("admin_user")

        assert approval.is_pending() is False

    def test_approval_request_is_expired(
        self,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test is_expired check."""
        approval = ApprovalRequest("run_123", sample_tool, execution_context, timeout_seconds=1)

        assert approval.is_expired() is False

        # Simulate time passing
        approval.created_at = datetime.utcnow() - timedelta(seconds=2)
        approval.expires_at = datetime.utcnow() - timedelta(seconds=1)

        assert approval.is_expired() is True
        assert approval.status == ApprovalStatus.EXPIRED

    def test_approval_request_to_dict(
        self,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test converting approval to dictionary."""
        approval = ApprovalRequest("run_123", sample_tool, execution_context)
        approval.approve("admin_user", "Approved")

        approval_dict = approval.to_dict()

        assert approval_dict["run_id"] == "run_123"
        assert approval_dict["tool_name"] == "deploy_app"
        assert approval_dict["status"] == "APPROVED"
        assert approval_dict["resolved_by"] == "admin_user"


class TestApprovalManager:
    """Tests for ApprovalManager."""

    def test_approval_manager_initialization(self) -> None:
        """Test ApprovalManager initialization."""
        manager = ApprovalManager()

        assert len(manager.approvals) == 0
        assert len(manager.run_approvals) == 0

    def test_approval_manager_create_approval(
        self,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test creating an approval."""
        approval = approval_manager.create_approval("run_123", sample_tool, execution_context)

        assert approval.run_id == "run_123"
        assert approval.tool == sample_tool
        assert approval.status == ApprovalStatus.PENDING
        assert approval.approval_id in approval_manager.approvals

    def test_approval_manager_get_approval(
        self,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test getting an approval by ID."""
        created = approval_manager.create_approval("run_123", sample_tool, execution_context)
        retrieved = approval_manager.get_approval(created.approval_id)

        assert retrieved is not None
        assert retrieved.approval_id == created.approval_id

    def test_approval_manager_get_nonexistent_approval(
        self,
        approval_manager: ApprovalManager,
    ) -> None:
        """Test getting a nonexistent approval."""
        approval = approval_manager.get_approval("nonexistent")

        assert approval is None

    def test_approval_manager_get_run_approvals(
        self,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test getting all approvals for a run."""
        approval_manager.create_approval("run_123", sample_tool, execution_context)
        approval_manager.create_approval("run_123", sample_tool, execution_context)
        approval_manager.create_approval("run_456", sample_tool, execution_context)

        run_123_approvals = approval_manager.get_run_approvals("run_123")
        run_456_approvals = approval_manager.get_run_approvals("run_456")

        assert len(run_123_approvals) == 2
        assert len(run_456_approvals) == 1

    def test_approval_manager_get_pending_approvals(
        self,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test getting pending approvals for a run."""
        approval1 = approval_manager.create_approval("run_123", sample_tool, execution_context)
        approval2 = approval_manager.create_approval("run_123", sample_tool, execution_context)

        approval1.approve("admin")

        pending = approval_manager.get_pending_approvals("run_123")

        assert len(pending) == 1
        assert pending[0].approval_id == approval2.approval_id

    def test_approval_manager_approve_approval(
        self,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test approving an approval."""
        approval = approval_manager.create_approval("run_123", sample_tool, execution_context)

        result = approval_manager.approve_approval(approval.approval_id, "admin_user", "OK")

        assert result is True
        assert approval.status == ApprovalStatus.APPROVED
        assert approval.resolved_by == "admin_user"

    def test_approval_manager_approve_nonexistent(
        self,
        approval_manager: ApprovalManager,
    ) -> None:
        """Test approving a nonexistent approval."""
        result = approval_manager.approve_approval("nonexistent", "admin_user")

        assert result is False

    def test_approval_manager_approve_already_approved(
        self,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test approving an already approved approval."""
        approval = approval_manager.create_approval("run_123", sample_tool, execution_context)
        approval_manager.approve_approval(approval.approval_id, "admin_user")

        result = approval_manager.approve_approval(approval.approval_id, "admin_user2")

        assert result is False

    def test_approval_manager_reject_approval(
        self,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test rejecting an approval."""
        approval = approval_manager.create_approval("run_123", sample_tool, execution_context)

        result = approval_manager.reject_approval(approval.approval_id, "admin_user", "Not safe")

        assert result is True
        assert approval.status == ApprovalStatus.REJECTED
        assert approval.resolved_by == "admin_user"

    def test_approval_manager_cancel_run_approvals(
        self,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test cancelling all approvals for a run."""
        approval1 = approval_manager.create_approval("run_123", sample_tool, execution_context)
        approval2 = approval_manager.create_approval("run_123", sample_tool, execution_context)
        approval3 = approval_manager.create_approval("run_123", sample_tool, execution_context)

        approval_manager.approve_approval(approval1.approval_id, "admin")

        cancelled_count = approval_manager.cancel_run_approvals("run_123")

        assert cancelled_count == 2  # Only pending approvals
        assert approval2.status == ApprovalStatus.CANCELLED
        assert approval3.status == ApprovalStatus.CANCELLED

    def test_approval_manager_get_approval_stats(
        self,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test getting approval statistics."""
        approval1 = approval_manager.create_approval("run_123", sample_tool, execution_context)
        approval2 = approval_manager.create_approval("run_123", sample_tool, execution_context)
        approval3 = approval_manager.create_approval("run_123", sample_tool, execution_context)

        approval_manager.approve_approval(approval1.approval_id, "admin")
        approval_manager.reject_approval(approval2.approval_id, "admin")

        stats = approval_manager.get_approval_stats("run_123")

        assert stats["total"] == 3
        assert stats["approved"] == 1
        assert stats["rejected"] == 1
        assert stats["pending"] == 1

    def test_approval_manager_clear_run_approvals(
        self,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test clearing all approvals for a run."""
        approval1 = approval_manager.create_approval("run_123", sample_tool, execution_context)
        approval2 = approval_manager.create_approval("run_123", sample_tool, execution_context)

        approval_manager.clear_run_approvals("run_123")

        assert len(approval_manager.get_run_approvals("run_123")) == 0
        assert approval1.approval_id not in approval_manager.approvals
        assert approval2.approval_id not in approval_manager.approvals

    def test_approval_manager_multiple_runs(
        self,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test managing approvals for multiple runs."""
        approval_manager.create_approval("run_123", sample_tool, execution_context)
        approval_manager.create_approval("run_123", sample_tool, execution_context)
        approval_manager.create_approval("run_456", sample_tool, execution_context)

        stats_123 = approval_manager.get_approval_stats("run_123")
        stats_456 = approval_manager.get_approval_stats("run_456")

        assert stats_123["total"] == 2
        assert stats_456["total"] == 1

    def test_approval_manager_timeout_configuration(
        self,
        approval_manager: ApprovalManager,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test approval timeout configuration."""
        approval = approval_manager.create_approval(
            "run_123",
            sample_tool,
            execution_context,
            timeout_seconds=7200,
        )

        expected_expiry = approval.created_at + timedelta(seconds=7200)
        assert approval.expires_at == expected_expiry
