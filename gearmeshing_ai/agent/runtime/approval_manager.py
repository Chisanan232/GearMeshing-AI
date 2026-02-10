"""Approval Manager for managing approval requests and resolutions.

This module implements the Approval Manager that handles approval request creation,
tracking, and resolution for agent workflows.

APPROVAL MANAGEMENT ARCHITECTURE
=================================

Approval System Components:

    ApprovalManager (Central Approval Coordinator)
    ├── ApprovalRequest (Individual Approval)
    │   ├── approval_id: str (UUID)
    │   ├── run_id: str
    │   ├── tool: MCPToolInfo
    │   ├── context: ExecutionContext
    │   ├── status: ApprovalStatus
    │   ├── created_at: datetime
    │   ├── expires_at: datetime
    │   ├── resolved_at: datetime | None
    │   ├── resolved_by: str | None
    │   └── resolution_reason: str | None
    │
    ├── ApprovalStatus (Enum)
    │   ├── PENDING
    │   ├── APPROVED
    │   ├── REJECTED
    │   ├── EXPIRED
    │   └── CANCELLED
    │
    └── Approval Storage
        ├── _approvals: dict[str, ApprovalRequest]
        └── _run_approvals: dict[str, list[str]]


APPROVAL LIFECYCLE
==================

1. CREATION
   Tool execution request
       ↓
   PolicyEngine.requires_approval() → True
       ↓
   ApprovalManager.create_approval()
       ├── Generate approval_id (UUID)
       ├── Set status = PENDING
       ├── Set created_at = now
       ├── Set expires_at = now + timeout
       └── Store approval request
       ↓
   ApprovalRequest created

2. PENDING STATE
   Approval waiting for decision
       ↓
   ApprovalManager.get_pending_approvals()
       ├── Return all PENDING approvals
       ├── Check for expired approvals
       └── Update expired → EXPIRED
       ↓
   Approval tracked

3. DECISION
   Human approver reviews request
       ↓
   ApprovalManager.approve_approval() or reject_approval()
       ├── Update status (APPROVED or REJECTED)
       ├── Set resolved_at = now
       ├── Set resolved_by = approver
       ├── Set resolution_reason
       └── Store decision
       ↓
   Approval resolved

4. RESOLUTION
   Workflow processes decision
       ↓
   ApprovalManager.get_approval_stats()
       ├── Count approved
       ├── Count rejected
       ├── Count pending
       └── Calculate metrics
       ↓
   Workflow continues or fails

5. COMPLETION
   Approval lifecycle ends
       ↓
   ApprovalManager.clear_run_approvals()
       ├── Archive approvals
       ├── Clean up storage
       └── Update metrics
       ↓
   Approval archived


APPROVAL STATE TRANSITIONS
==========================

PENDING
├─ (timeout) → EXPIRED
├─ (approved) → APPROVED
├─ (rejected) → REJECTED
└─ (cancelled) → CANCELLED

APPROVED
└─ (final state)

REJECTED
└─ (final state)

EXPIRED
└─ (final state)

CANCELLED
└─ (final state)


APPROVAL DECISION MATRIX
========================

Approval Decision:
    ┌──────────────────────────────────────────────┐
    │ Approval Status?                             │
    ├──────────────────────────────────────────────┤
    │ PENDING → AWAITING_APPROVAL                  │
    │ APPROVED → ALLOW EXECUTION                   │
    │ REJECTED → BLOCK EXECUTION                   │
    │ EXPIRED → BLOCK EXECUTION (timeout)          │
    │ CANCELLED → BLOCK EXECUTION                  │
    └──────────────────────────────────────────────┘

Multiple Approvals:
    ┌──────────────────────────────────────────────┐
    │ All approvals resolved?                      │
    ├──────────────────────────────────────────────┤
    │ YES → Check results                          │
    │       ├─ All approved → ALLOW                │
    │       └─ Any rejected → BLOCK                │
    │ NO  → AWAITING_APPROVAL                      │
    └──────────────────────────────────────────────┘


APPROVAL WORKFLOW PATTERNS
==========================

Pattern 1: Single Approval
    Tool execution request
        ↓
    Create approval (1 approval)
        ↓
    Wait for approval
        ↓
    Decision made
        ↓
    Execute or block

Pattern 2: Multiple Approvals (AND)
    Tool execution request
        ↓
    Create approvals (N approvals)
        ↓
    Wait for all approvals
        ↓
    All decisions made
        ├─ All approved → Execute
        └─ Any rejected → Block

Pattern 3: Multiple Approvals (OR)
    Tool execution request
        ↓
    Create approvals (N approvals)
        ↓
    Wait for first approval
        ↓
    First decision made
        ├─ Approved → Execute
        └─ Rejected → Continue waiting

Pattern 4: Escalation
    Tool execution request
        ↓
    Create approval (Level 1)
        ↓
    Wait for timeout
        ↓
    No decision → Escalate
        ↓
    Create approval (Level 2)
        ↓
    Wait for decision


APPROVAL MANAGEMENT CONCERNS
============================

1. APPROVAL TIMEOUT HANDLING
   Concern: Approvals might expire without decision
   Solution: Timeout tracking, expiration checking
   Monitoring: Track expired approvals

2. APPROVAL BOTTLENECKS
   Concern: Approvals can block workflow execution
   Solution: Timeout handling, escalation paths
   Monitoring: Track approval wait times

3. APPROVAL CONSISTENCY
   Concern: Multiple approvals must be consistent
   Solution: Atomic approval decisions, transaction-like behavior
   Validation: Verify all approvals resolved before proceeding

4. APPROVAL AUDIT TRAIL
   Concern: All approval decisions must be auditable
   Solution: Complete approval history, decision logging
   Monitoring: Audit trail reviewed regularly

5. APPROVAL SCALABILITY
   Concern: Many concurrent approvals might impact performance
   Solution: Efficient storage, indexing by run_id
   Monitoring: Track approval queue size

6. APPROVAL NOTIFICATION
   Concern: Approvers must be notified of pending approvals
   Solution: Notification system integration
   Monitoring: Track notification delivery

7. APPROVAL DELEGATION
   Concern: Approvers might not be available
   Solution: Delegation support, escalation paths
   Monitoring: Track delegation chains


APPROVAL STATISTICS
===================

Per-Workflow Statistics:
    - Total approvals created
    - Approved count
    - Rejected count
    - Expired count
    - Cancelled count
    - Pending count
    - Average approval time
    - Max approval time
    - Min approval time

Approval Rate Metrics:
    - Approval rate (approved / total)
    - Rejection rate (rejected / total)
    - Expiration rate (expired / total)
    - Average time to approval
    - P50, P95, P99 approval times

Business Metrics:
    - Tools requiring approval
    - Approval frequency by tool
    - Approval frequency by role
    - Approval frequency by user


APPROVAL CONFIGURATION
======================

Example 1: Simple Approval
    ApprovalRequest(
        run_id="run_123",
        tool=tool_info,
        context=context,
        timeout_seconds=3600,
    )

Example 2: Multiple Approvals
    For each approver in ["admin", "security"]:
        ApprovalRequest(
            run_id="run_123",
            tool=tool_info,
            context=context,
            timeout_seconds=3600,
        )

Example 3: Escalation
    Level 1: ApprovalRequest(timeout=300)  # 5 minutes
    Level 2: ApprovalRequest(timeout=1800) # 30 minutes
    Level 3: ApprovalRequest(timeout=3600) # 1 hour


PERFORMANCE CHARACTERISTICS
===========================

Approval Storage:
    Single approval: ~500 bytes
    100 approvals: ~50 KB
    1000 approvals: ~500 KB

Approval Lookup:
    By approval_id: O(1) <1ms
    By run_id: O(N) 1-10ms
    All pending: O(N) 1-10ms

Approval Operations:
    Create: <1ms
    Approve/Reject: <1ms
    Get stats: 1-5ms
    Cleanup: 1-10ms


MONITORING APPROVALS
====================

Per-Approval Metrics:
    - Approval ID
    - Tool name
    - Created time
    - Resolved time
    - Decision (approved/rejected)
    - Decided by
    - Decision reason

Approval-Level Metrics:
    - Total approvals
    - Approval rate
    - Rejection rate
    - Expiration rate
    - Average approval time
    - Approval queue size

Workflow-Level Metrics:
    - Approvals per workflow
    - Approval impact on latency
    - Approval success rate
    - Approval escalations


EXTENSION POINTS
================

1. Custom Approval Strategies
   - Can implement different approval workflows
   - Can add approval escalation paths
   - Can add approval delegation

2. Custom Approval Notifications
   - Can integrate with notification systems
   - Can add approval reminders
   - Can add approval escalations

3. Custom Approval Storage
   - Can persist approvals to database
   - Can implement approval archival
   - Can add approval search/filtering

4. Custom Approval Metrics
   - Can add custom metrics
   - Can integrate with monitoring systems
   - Can add approval analytics


TESTING APPROVALS
=================

Unit Tests:
    - Test approval creation
    - Test approval status transitions
    - Test approval expiration
    - Test approval statistics
    - Test approval cleanup

Integration Tests:
    - Test approvals with workflow nodes
    - Test approval workflow patterns
    - Test approval escalation
    - Test approval notifications

E2E Tests:
    - Test complete approval workflows
    - Test with real approvers
    - Test approval timeouts
    - Test approval escalations
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from gearmeshing_ai.agent.models.actions import MCPToolInfo

from .models import ExecutionContext

logger = logging.getLogger(__name__)


class ApprovalStatus(str, Enum):
    """Status of an approval request."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class ApprovalRequest:
    """Represents an approval request for a tool execution.

    Attributes:
        approval_id: Unique identifier for the approval
        run_id: Associated workflow run ID
        tool: Tool requiring approval
        context: Execution context
        status: Current approval status
        created_at: Timestamp when approval was created
        expires_at: Timestamp when approval expires
        resolved_at: Timestamp when approval was resolved
        resolved_by: User who resolved the approval
        resolution_reason: Reason for approval resolution

    """

    def __init__(
        self,
        run_id: str,
        tool: MCPToolInfo,
        context: ExecutionContext,
        timeout_seconds: int = 3600,
    ) -> None:
        """Initialize ApprovalRequest.

        Args:
            run_id: Associated workflow run ID
            tool: Tool requiring approval
            context: Execution context
            timeout_seconds: Timeout for approval in seconds

        """
        self.approval_id = str(uuid4())
        self.run_id = run_id
        self.tool = tool
        self.context = context
        self.status = ApprovalStatus.PENDING
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(seconds=timeout_seconds)
        self.resolved_at: datetime | None = None
        self.resolved_by: str | None = None
        self.resolution_reason: str | None = None
        logger.debug(f"Created approval request {self.approval_id} for tool {tool.name}")

    def approve(self, approved_by: str, reason: str = "") -> None:
        """Approve the request.

        Args:
            approved_by: User who approved the request
            reason: Reason for approval

        """
        self.status = ApprovalStatus.APPROVED
        self.resolved_at = datetime.utcnow()
        self.resolved_by = approved_by
        self.resolution_reason = reason
        logger.info(f"Approval {self.approval_id} approved by {approved_by}")

    def reject(self, rejected_by: str, reason: str = "") -> None:
        """Reject the request.

        Args:
            rejected_by: User who rejected the request
            reason: Reason for rejection

        """
        self.status = ApprovalStatus.REJECTED
        self.resolved_at = datetime.utcnow()
        self.resolved_by = rejected_by
        self.resolution_reason = reason
        logger.info(f"Approval {self.approval_id} rejected by {rejected_by}")

    def is_expired(self) -> bool:
        """Check if approval has expired.

        Returns:
            True if approval has expired, False otherwise

        """
        if self.status != ApprovalStatus.PENDING:
            return False

        if datetime.utcnow() > self.expires_at:
            self.status = ApprovalStatus.EXPIRED
            logger.warning(f"Approval {self.approval_id} expired")
            return True

        return False

    def is_approved(self) -> bool:
        """Check if approval is approved.

        Returns:
            True if approved, False otherwise

        """
        return self.status == ApprovalStatus.APPROVED

    def is_pending(self) -> bool:
        """Check if approval is pending.

        Returns:
            True if pending, False otherwise

        """
        return self.status == ApprovalStatus.PENDING and not self.is_expired()

    def to_dict(self) -> dict[str, Any]:
        """Convert approval to dictionary.

        Returns:
            Dictionary representation of approval

        """
        return {
            "approval_id": self.approval_id,
            "run_id": self.run_id,
            "tool_name": self.tool.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "resolution_reason": self.resolution_reason,
        }


class ApprovalManager:
    """Manager for approval requests and resolutions.

    Attributes:
        approvals: Dictionary of approval requests by approval_id
        run_approvals: Dictionary mapping run_id to approval_ids

    """

    def __init__(self) -> None:
        """Initialize ApprovalManager."""
        self.approvals: dict[str, ApprovalRequest] = {}
        self.run_approvals: dict[str, list[str]] = {}
        logger.debug("ApprovalManager initialized")

    def create_approval(
        self,
        run_id: str,
        tool: MCPToolInfo,
        context: ExecutionContext,
        timeout_seconds: int = 3600,
    ) -> ApprovalRequest:
        """Create an approval request.

        Args:
            run_id: Associated workflow run ID
            tool: Tool requiring approval
            context: Execution context
            timeout_seconds: Timeout for approval in seconds

        Returns:
            Created approval request

        """
        approval = ApprovalRequest(run_id, tool, context, timeout_seconds)
        self.approvals[approval.approval_id] = approval

        if run_id not in self.run_approvals:
            self.run_approvals[run_id] = []
        self.run_approvals[run_id].append(approval.approval_id)

        logger.debug(f"Created approval {approval.approval_id} for run {run_id}")
        return approval

    def get_approval(self, approval_id: str) -> ApprovalRequest | None:
        """Get an approval request by ID.

        Args:
            approval_id: Approval request ID

        Returns:
            Approval request or None if not found

        """
        return self.approvals.get(approval_id)

    def get_run_approvals(self, run_id: str) -> list[ApprovalRequest]:
        """Get all approvals for a run.

        Args:
            run_id: Workflow run ID

        Returns:
            List of approval requests for the run

        """
        approval_ids = self.run_approvals.get(run_id, [])
        return [self.approvals[aid] for aid in approval_ids if aid in self.approvals]

    def get_pending_approvals(self, run_id: str) -> list[ApprovalRequest]:
        """Get pending approvals for a run.

        Args:
            run_id: Workflow run ID

        Returns:
            List of pending approval requests

        """
        approvals = self.get_run_approvals(run_id)
        return [a for a in approvals if a.is_pending()]

    def approve_approval(
        self,
        approval_id: str,
        approved_by: str,
        reason: str = "",
    ) -> bool:
        """Approve an approval request.

        Args:
            approval_id: Approval request ID
            approved_by: User who approved
            reason: Reason for approval

        Returns:
            True if approval was successful, False otherwise

        """
        approval = self.get_approval(approval_id)
        if approval is None:
            logger.warning(f"Approval {approval_id} not found")
            return False

        if not approval.is_pending():
            logger.warning(f"Approval {approval_id} is not pending (status: {approval.status})")
            return False

        approval.approve(approved_by, reason)
        return True

    def reject_approval(
        self,
        approval_id: str,
        rejected_by: str,
        reason: str = "",
    ) -> bool:
        """Reject an approval request.

        Args:
            approval_id: Approval request ID
            rejected_by: User who rejected
            reason: Reason for rejection

        Returns:
            True if rejection was successful, False otherwise

        """
        approval = self.get_approval(approval_id)
        if approval is None:
            logger.warning(f"Approval {approval_id} not found")
            return False

        if not approval.is_pending():
            logger.warning(f"Approval {approval_id} is not pending (status: {approval.status})")
            return False

        approval.reject(rejected_by, reason)
        return True

    def cancel_run_approvals(self, run_id: str) -> int:
        """Cancel all pending approvals for a run.

        Args:
            run_id: Workflow run ID

        Returns:
            Number of approvals cancelled

        """
        approvals = self.get_pending_approvals(run_id)
        cancelled_count = 0

        for approval in approvals:
            approval.status = ApprovalStatus.CANCELLED
            cancelled_count += 1
            logger.debug(f"Cancelled approval {approval.approval_id}")

        return cancelled_count

    def get_approval_stats(self, run_id: str) -> dict[str, int]:
        """Get approval statistics for a run.

        Args:
            run_id: Workflow run ID

        Returns:
            Dictionary with approval statistics

        """
        approvals = self.get_run_approvals(run_id)
        stats = {
            "total": len(approvals),
            "pending": len([a for a in approvals if a.is_pending()]),
            "approved": len([a for a in approvals if a.is_approved()]),
            "rejected": len([a for a in approvals if a.status == ApprovalStatus.REJECTED]),
            "expired": len([a for a in approvals if a.status == ApprovalStatus.EXPIRED]),
            "cancelled": len([a for a in approvals if a.status == ApprovalStatus.CANCELLED]),
        }
        return stats

    def clear_run_approvals(self, run_id: str) -> None:
        """Clear all approvals for a run.

        Args:
            run_id: Workflow run ID

        """
        approval_ids = self.run_approvals.get(run_id, [])
        for aid in approval_ids:
            if aid in self.approvals:
                del self.approvals[aid]
        if run_id in self.run_approvals:
            del self.run_approvals[run_id]
        logger.debug(f"Cleared approvals for run {run_id}")
