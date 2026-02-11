"""
Approval handler for managing user approval workflows.

Handles approval requests, decisions, timeouts, and state management
for workflows that require user approval.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

from .models import (
    ApprovalDecision,
    ApprovalDecisionRecord,
    ApprovalRequest,
)
from .persistence import PersistenceManager


class ApprovalHandler:
    """
    Manages approval workflows including requests, decisions, and timeouts.
    
    Handles:
    - Approval request creation and tracking
    - Approval decision submission
    - Timeout handling with auto-reject
    - Approval history and audit trail
    """

    def __init__(self, persistence_manager: Optional[PersistenceManager] = None):
        """Initialize the approval handler."""
        self.persistence_manager = persistence_manager or PersistenceManager()
        self._pending_approvals: Dict[str, ApprovalRequest] = {}
        self._approval_decisions: Dict[str, ApprovalDecision] = {}
        self._approval_events: Dict[str, asyncio.Event] = {}

    async def create_approval_request(
        self,
        run_id: str,
        operation: str,
        risk_level: str,
        description: str,
        timeout_seconds: int = 3600,
    ) -> ApprovalRequest:
        """
        Create an approval request for a risky operation.
        
        Args:
            run_id: ID of the workflow
            operation: Name of the operation
            risk_level: Risk level (low, medium, high, critical)
            description: Description of the operation
            timeout_seconds: Timeout for approval
            
        Returns:
            ApprovalRequest object
        """
        approval_request = ApprovalRequest(
            run_id=run_id,
            operation=operation,
            risk_level=risk_level,
            description=description,
            timeout_seconds=timeout_seconds,
        )

        self._pending_approvals[run_id] = approval_request
        self._approval_events[run_id] = asyncio.Event()

        # Persist approval request
        await self.persistence_manager.save_approval_request(approval_request)

        return approval_request

    async def resolve_approval(
        self,
        run_id: str,
        decision: ApprovalDecision,
        approver_id: str,
        reason: Optional[str] = None,
    ) -> ApprovalDecisionRecord:
        """
        Resolve an approval request with a decision.
        
        Args:
            run_id: ID of the workflow
            decision: APPROVED, REJECTED, or TIMEOUT
            approver_id: ID of the approver
            reason: Optional reason for the decision
            
        Returns:
            ApprovalDecisionRecord
        """
        approval_id = str(uuid4())
        record = ApprovalDecisionRecord(
            approval_id=approval_id,
            run_id=run_id,
            decision=decision,
            approver_id=approver_id,
            reason=reason,
        )

        self._approval_decisions[run_id] = decision

        # Persist decision
        await self.persistence_manager.save_approval_decision(record)

        # Signal waiting coroutine
        if run_id in self._approval_events:
            self._approval_events[run_id].set()

        return record

    async def wait_for_approval(
        self,
        run_id: str,
        timeout_seconds: int = 3600,
    ) -> ApprovalDecision:
        """
        Wait for an approval decision with timeout.
        
        Args:
            run_id: ID of the workflow
            timeout_seconds: Timeout for approval
            
        Returns:
            ApprovalDecision (APPROVED, REJECTED, or TIMEOUT)
        """
        if run_id not in self._approval_events:
            self._approval_events[run_id] = asyncio.Event()

        try:
            await asyncio.wait_for(
                self._approval_events[run_id].wait(),
                timeout=timeout_seconds,
            )
            return self._approval_decisions.get(run_id, ApprovalDecision.REJECTED)
        except asyncio.TimeoutError:
            # Auto-reject on timeout
            await self.resolve_approval(
                run_id=run_id,
                decision=ApprovalDecision.TIMEOUT,
                approver_id="system",
                reason="Approval timeout",
            )
            return ApprovalDecision.TIMEOUT

    async def get_approval_request(self, run_id: str) -> Optional[ApprovalRequest]:
        """Get the approval request for a workflow."""
        return self._pending_approvals.get(run_id)

    async def get_approval_history(
        self,
        run_id: str,
    ) -> List[ApprovalDecisionRecord]:
        """Get all approval decisions for a workflow."""
        return await self.persistence_manager.get_approval_history(run_id)

    async def is_approval_pending(self, run_id: str) -> bool:
        """Check if approval is pending for a workflow."""
        return run_id in self._pending_approvals

    async def cleanup(self, run_id: str) -> None:
        """Clean up approval state for a workflow."""
        self._pending_approvals.pop(run_id, None)
        self._approval_decisions.pop(run_id, None)
        self._approval_events.pop(run_id, None)
