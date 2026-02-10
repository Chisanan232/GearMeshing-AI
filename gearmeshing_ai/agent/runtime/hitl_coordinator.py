"""Human-in-the-Loop (HITL) Coordinator for managing human approvals and interventions.

This module implements the HITL Coordinator that manages approval requests,
human decisions, and workflow resumption.
"""

import logging
from typing import Any

from gearmeshing_ai.agent.models.actions import MCPToolInfo

from .approval_manager import ApprovalManager, ApprovalRequest, ApprovalStatus
from .policy_engine import PolicyEngine
from .models import ExecutionContext, WorkflowState

logger = logging.getLogger(__name__)


class HITLCoordinator:
    """Coordinator for Human-in-the-Loop workflow management.

    Manages approval requests, human decisions, and workflow state transitions
    for human-in-the-loop agent execution.

    Attributes:
        approval_manager: Manager for approval requests
        policy_engine: Engine for policy enforcement
        pending_interventions: Dictionary of pending human interventions

    """

    def __init__(
        self,
        approval_manager: ApprovalManager,
        policy_engine: PolicyEngine,
    ) -> None:
        """Initialize HITLCoordinator.

        Args:
            approval_manager: Manager for approval requests
            policy_engine: Engine for policy enforcement

        """
        self.approval_manager = approval_manager
        self.policy_engine = policy_engine
        self.pending_interventions: dict[str, dict[str, Any]] = {}
        logger.debug("HITLCoordinator initialized")

    def request_approval(
        self,
        run_id: str,
        tool: MCPToolInfo,
        context: ExecutionContext,
        timeout_seconds: int = 3600,
    ) -> ApprovalRequest:
        """Request human approval for a tool execution.

        Args:
            run_id: Workflow run ID
            tool: Tool requiring approval
            context: Execution context
            timeout_seconds: Timeout for approval in seconds

        Returns:
            Created approval request

        """
        logger.info(f"Requesting approval for tool {tool.name} in run {run_id}")

        approval = self.approval_manager.create_approval(
            run_id,
            tool,
            context,
            timeout_seconds,
        )

        # Track as pending intervention
        self.pending_interventions[approval.approval_id] = {
            "type": "approval",
            "run_id": run_id,
            "tool_name": tool.name,
            "created_at": approval.created_at.isoformat(),
            "expires_at": approval.expires_at.isoformat(),
        }

        return approval

    def submit_approval_decision(
        self,
        approval_id: str,
        approved: bool,
        decided_by: str,
        reason: str = "",
    ) -> bool:
        """Submit a human approval decision.

        Args:
            approval_id: Approval request ID
            approved: True if approved, False if rejected
            decided_by: User who made the decision
            reason: Reason for decision

        Returns:
            True if decision was processed successfully, False otherwise

        """
        logger.info(f"Processing approval decision for {approval_id}: approved={approved}")

        approval = self.approval_manager.get_approval(approval_id)
        if approval is None:
            logger.warning(f"Approval {approval_id} not found")
            return False

        if approved:
            success = self.approval_manager.approve_approval(approval_id, decided_by, reason)
        else:
            success = self.approval_manager.reject_approval(approval_id, decided_by, reason)

        if success:
            # Remove from pending interventions
            if approval_id in self.pending_interventions:
                del self.pending_interventions[approval_id]
            logger.info(f"Approval decision processed for {approval_id}")

        return success

    def get_pending_interventions(self, run_id: str) -> list[dict[str, Any]]:
        """Get pending human interventions for a run.

        Args:
            run_id: Workflow run ID

        Returns:
            List of pending interventions

        """
        interventions = []
        for intervention_id, intervention in self.pending_interventions.items():
            if intervention.get("run_id") == run_id:
                interventions.append({
                    "intervention_id": intervention_id,
                    **intervention,
                })

        logger.debug(f"Found {len(interventions)} pending interventions for run {run_id}")
        return interventions

    def can_resume_workflow(self, run_id: str) -> tuple[bool, str]:
        """Check if a workflow can be resumed.

        Args:
            run_id: Workflow run ID

        Returns:
            Tuple of (can_resume, reason)

        """
        pending_approvals = self.approval_manager.get_pending_approvals(run_id)

        if pending_approvals:
            return False, f"{len(pending_approvals)} approval(s) still pending"

        all_approvals = self.approval_manager.get_run_approvals(run_id)
        rejected_count = len([a for a in all_approvals if a.status == ApprovalStatus.REJECTED])

        if rejected_count > 0:
            return False, f"{rejected_count} approval(s) rejected"

        return True, "All approvals resolved"

    def get_intervention_status(self, approval_id: str) -> dict[str, Any]:
        """Get the status of a human intervention.

        Args:
            approval_id: Approval request ID

        Returns:
            Dictionary with intervention status

        """
        approval = self.approval_manager.get_approval(approval_id)
        if approval is None:
            return {"status": "not_found"}

        return {
            "approval_id": approval_id,
            "status": approval.status.value,
            "tool_name": approval.tool.name,
            "created_at": approval.created_at.isoformat(),
            "expires_at": approval.expires_at.isoformat(),
            "resolved_at": approval.resolved_at.isoformat() if approval.resolved_at else None,
            "resolved_by": approval.resolved_by,
            "resolution_reason": approval.resolution_reason,
            "is_expired": approval.is_expired(),
        }

    def get_run_intervention_summary(self, run_id: str) -> dict[str, Any]:
        """Get a summary of all interventions for a run.

        Args:
            run_id: Workflow run ID

        Returns:
            Dictionary with intervention summary

        """
        stats = self.approval_manager.get_approval_stats(run_id)
        pending_interventions = self.get_pending_interventions(run_id)

        can_resume, resume_reason = self.can_resume_workflow(run_id)

        return {
            "run_id": run_id,
            "total_approvals": stats["total"],
            "approved": stats["approved"],
            "rejected": stats["rejected"],
            "pending": stats["pending"],
            "expired": stats["expired"],
            "cancelled": stats["cancelled"],
            "pending_interventions": pending_interventions,
            "can_resume": can_resume,
            "resume_reason": resume_reason,
        }

    def clear_run_interventions(self, run_id: str) -> int:
        """Clear all interventions for a run.

        Args:
            run_id: Workflow run ID

        Returns:
            Number of interventions cleared

        """
        pending = self.get_pending_interventions(run_id)
        cleared_count = 0

        for intervention in pending:
            intervention_id = intervention["intervention_id"]
            if intervention_id in self.pending_interventions:
                del self.pending_interventions[intervention_id]
                cleared_count += 1

        self.approval_manager.clear_run_approvals(run_id)
        logger.debug(f"Cleared {cleared_count} interventions for run {run_id}")

        return cleared_count
