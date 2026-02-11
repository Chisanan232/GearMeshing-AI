"""
ApprovalWorkflow - Handles approval pause/resume coordination.

Manages approval state transitions, alternative action execution,
and coordination with runtime's ApprovalManager.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

from .models import (
    ApprovalDecision,
    ApprovalDecisionRecord,
    ApprovalRequest,
)
from .persistence import PersistenceManager


class ApprovalWorkflow:
    """
    Handles approval pause/resume coordination.
    
    Manages approval state transitions, alternative action execution,
    and coordination with runtime's ApprovalManager.
    """

    def __init__(self, persistence: Optional[PersistenceManager] = None):
        """
        Initialize ApprovalWorkflow.
        
        Args:
            persistence: PersistenceManager for state persistence
        """
        self.persistence = persistence or PersistenceManager()
        self._approval_events: dict[str, asyncio.Event] = {}
        self._approval_decisions: dict[str, ApprovalDecisionRecord] = {}

    async def pause_for_approval(
        self,
        run_id: str,
        approval_request: ApprovalRequest,
        timeout_seconds: int = 3600,
    ) -> None:
        """
        Pause workflow for approval.
        
        Args:
            run_id: Workflow execution ID
            approval_request: Approval request details
            timeout_seconds: Timeout for approval
        """
        # Create approval event for this workflow
        self._approval_events[run_id] = asyncio.Event()

        # Persist approval request
        await self.persistence.save_approval_request(run_id, approval_request)

        # Set timeout for auto-rejection
        asyncio.create_task(
            self._auto_reject_on_timeout(run_id, timeout_seconds)
        )

    async def resume_with_approval(
        self,
        run_id: str,
        approver_id: str,
        reason: Optional[str] = None,
    ) -> ApprovalDecisionRecord:
        """
        Resume workflow with approval decision.
        
        Args:
            run_id: Workflow execution ID
            approver_id: ID of user approving
            reason: Reason for approval
        
        Returns:
            ApprovalDecisionRecord
        """
        decision_record = ApprovalDecisionRecord(
            approval_id=str(uuid4()),
            run_id=run_id,
            decision=ApprovalDecision.APPROVED,
            approver_id=approver_id,
            reason=reason,
        )

        # Store decision
        self._approval_decisions[run_id] = decision_record

        # Signal approval event
        if run_id in self._approval_events:
            self._approval_events[run_id].set()

        # Persist decision
        await self.persistence.save_approval_decision(decision_record)

        return decision_record

    async def resume_with_rejection(
        self,
        run_id: str,
        approver_id: str,
        alternative_action: str,
        reason: str,
    ) -> ApprovalDecisionRecord:
        """
        Resume workflow with rejection and alternative action.
        
        Args:
            run_id: Workflow execution ID
            approver_id: ID of user rejecting
            alternative_action: Alternative action to execute
            reason: Reason for rejection
        
        Returns:
            ApprovalDecisionRecord with alternative action
        """
        decision_record = ApprovalDecisionRecord(
            approval_id=str(uuid4()),
            run_id=run_id,
            decision=ApprovalDecision.REJECTED,
            approver_id=approver_id,
            alternative_action=alternative_action,
            reason=reason,
        )

        # Store decision
        self._approval_decisions[run_id] = decision_record

        # Signal approval event
        if run_id in self._approval_events:
            self._approval_events[run_id].set()

        # Persist decision
        await self.persistence.save_approval_decision(decision_record)

        return decision_record

    async def wait_for_approval(
        self,
        run_id: str,
        timeout_seconds: int = 3600,
    ) -> Optional[ApprovalDecisionRecord]:
        """
        Wait for approval decision.
        
        Args:
            run_id: Workflow execution ID
            timeout_seconds: Timeout for approval
        
        Returns:
            ApprovalDecisionRecord if decision made, None if timeout
        """
        if run_id not in self._approval_events:
            self._approval_events[run_id] = asyncio.Event()

        try:
            await asyncio.wait_for(
                self._approval_events[run_id].wait(),
                timeout=timeout_seconds,
            )
            return self._approval_decisions.get(run_id)
        except asyncio.TimeoutError:
            # Auto-reject on timeout
            decision_record = ApprovalDecisionRecord(
                approval_id=str(uuid4()),
                run_id=run_id,
                decision=ApprovalDecision.TIMEOUT,
                approver_id="system",
                reason="Approval timeout exceeded",
            )
            self._approval_decisions[run_id] = decision_record
            await self.persistence.save_approval_decision(decision_record)
            return decision_record

    async def _auto_reject_on_timeout(
        self,
        run_id: str,
        timeout_seconds: int,
    ) -> None:
        """
        Auto-reject approval on timeout.
        
        Args:
            run_id: Workflow execution ID
            timeout_seconds: Timeout duration
        """
        try:
            await asyncio.sleep(timeout_seconds)

            # Check if decision already made
            if run_id in self._approval_decisions:
                return

            # Auto-reject on timeout
            decision_record = ApprovalDecisionRecord(
                approval_id=str(uuid4()),
                run_id=run_id,
                decision=ApprovalDecision.TIMEOUT,
                approver_id="system",
                reason="Approval timeout exceeded - auto-rejected",
            )

            self._approval_decisions[run_id] = decision_record

            # Signal approval event
            if run_id in self._approval_events:
                self._approval_events[run_id].set()

            # Persist decision
            await self.persistence.save_approval_decision(decision_record)

        except Exception as e:
            print(f"Error in auto-reject timeout for {run_id}: {str(e)}")

    async def get_approval_status(self, run_id: str) -> dict[str, Any]:
        """
        Get approval status for a workflow.
        
        Args:
            run_id: Workflow execution ID
        
        Returns:
            Dictionary with approval status
        """
        decision = self._approval_decisions.get(run_id)

        if decision:
            return {
                "run_id": run_id,
                "status": decision.decision.value,
                "approver_id": decision.approver_id,
                "decided_at": decision.decided_at,
                "reason": decision.reason,
                "alternative_action": decision.alternative_action,
            }

        return {
            "run_id": run_id,
            "status": "pending",
        }

    async def cleanup(self, run_id: str) -> None:
        """
        Clean up approval state for a workflow.
        
        Args:
            run_id: Workflow execution ID
        """
        # Remove event
        if run_id in self._approval_events:
            del self._approval_events[run_id]

        # Keep decision record for history
        # Don't delete from _approval_decisions
