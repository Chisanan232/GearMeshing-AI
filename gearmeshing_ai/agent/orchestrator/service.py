"""
OrchestratorService - Thin wrapper around runtime workflow.

Provides simple, clean API for executing AI agent workflows with approval support.
Delegates all workflow execution to the runtime package.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

from gearmeshing_ai.agent.runtime import ExecutionContext, WorkflowState, create_agent_workflow
from gearmeshing_ai.agent.orchestrator.models import (
    ApprovalDecision,
    ApprovalDecisionRecord,
    ApprovalRequest,
    WorkflowResult,
    WorkflowStatus,
)
from gearmeshing_ai.agent.orchestrator.persistence import PersistenceManager
from gearmeshing_ai.agent.orchestrator.exceptions import (
    WorkflowNotFoundError,
    WorkflowNotAwaitingApprovalError,
    WorkflowAlreadyCompletedError,
    InvalidAlternativeActionError,
    ApprovalTimeoutError,
)


class OrchestratorService:
    """
    Thin wrapper around runtime workflow.
    
    Provides simple API for executing AI agent workflows with approval support.
    Delegates execution to runtime, handles persistence and approval coordination.
    """

    def __init__(self, persistence: Optional[PersistenceManager] = None):
        """
        Initialize OrchestratorService.
        
        Args:
            persistence: PersistenceManager for state persistence
                        (defaults to in-memory if not provided)
        """
        self.persistence: PersistenceManager = persistence or PersistenceManager()

    async def run_workflow(
        self,
        task_description: str,
        agent_role: Optional[str] = None,
        user_id: str = "system",
        timeout_seconds: int = 300,
        approval_timeout_seconds: int = 3600,
    ) -> WorkflowResult:
        """
        Execute a complete AI agent workflow.
        
        Args:
            task_description: What the agent should do
            agent_role: Specific role (dev, qa, sre) or None for auto-select
            user_id: User triggering the workflow
            timeout_seconds: Maximum execution time (5 minutes default)
            approval_timeout_seconds: Max time to wait for approval (1 hour default)
        
        Returns:
            WorkflowResult with status:
            - SUCCESS: Workflow completed successfully
            - FAILED: Workflow failed
            - AWAITING_APPROVAL: Workflow paused, waiting for approval decision
            - TIMEOUT: Execution exceeded timeout
            - CANCELLED: Workflow was cancelled
        
        Raises:
            Exception: If workflow execution fails
        """
        run_id = str(uuid4())
        started_at = datetime.now(UTC)

        try:
            # 1. Create execution context
            context = ExecutionContext(
                task_description=task_description,
                agent_role=agent_role,
                user_id=user_id,
            )

            # 2. Create initial workflow state
            state = WorkflowState(
                run_id=run_id,
                context=context,
            )

            # 3. Create runtime workflow
            workflow = create_agent_workflow()

            # 4. Execute workflow (delegate to runtime)
            try:
                final_state = await asyncio.wait_for(
                    workflow.ainvoke(state),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                completed_at = datetime.now(UTC)
                duration = (completed_at - started_at).total_seconds()
                return WorkflowResult(
                    run_id=run_id,
                    status=WorkflowStatus.TIMEOUT,
                    error="Workflow execution timeout",
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_seconds=duration,
                )

            # 5. Persist state
            await self.persistence.save_workflow_state(run_id, final_state)

            # 6. Check if approval is required
            # Note: This depends on runtime's WorkflowState structure
            # Adjust based on actual WorkflowState implementation
            if hasattr(final_state, 'status') and hasattr(final_state.status, 'state'):
                if final_state.status.state == "awaiting_approval":
                    approval_request = None
                    if hasattr(final_state, 'approvals') and final_state.approvals:
                        approval_request = final_state.approvals[-1]

                    return WorkflowResult(
                        run_id=run_id,
                        status=WorkflowStatus.AWAITING_APPROVAL,
                        approval_request=approval_request,
                        started_at=started_at,
                        completed_at=None,
                    )

            # 7. Return final result
            completed_at = datetime.now(UTC)
            duration = (completed_at - started_at).total_seconds()

            output = None
            if hasattr(final_state, 'current_proposal') and final_state.current_proposal:
                output = final_state.current_proposal.dict() if hasattr(
                    final_state.current_proposal, 'dict'
                ) else final_state.current_proposal

            error = None
            if hasattr(final_state, 'status') and hasattr(final_state.status, 'error'):
                error = final_state.status.error

            return WorkflowResult(
                run_id=run_id,
                status=WorkflowStatus.SUCCESS if error is None else WorkflowStatus.FAILED,
                output=output,
                error=error,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
            )

        except Exception as e:
            completed_at = datetime.now(UTC)
            duration = (completed_at - started_at).total_seconds()
            return WorkflowResult(
                run_id=run_id,
                status=WorkflowStatus.FAILED,
                error=f"Workflow execution failed: {str(e)}",
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
            )

    async def approve_workflow(
        self,
        run_id: str,
        approver_id: str,
        reason: Optional[str] = None,
    ) -> WorkflowResult:
        """
        Approve the current proposal and resume workflow normally.
        
        Args:
            run_id: Workflow execution ID (must be in AWAITING_APPROVAL state)
            approver_id: ID of user approving
            reason: Optional reason for approval
        
        Returns:
            WorkflowResult with final execution status
        
        Raises:
            WorkflowNotFoundError: If workflow not found
            WorkflowNotAwaitingApprovalError: If workflow not awaiting approval
            ApprovalTimeoutError: If approval timeout exceeded
        """
        started_at = datetime.now(UTC)

        try:
            # 1. Load persisted state
            state = await self.persistence.load_workflow_state(run_id)
            if not state:
                raise WorkflowNotFoundError(f"Workflow {run_id} not found")

            # 2. Check if waiting for approval
            if not (hasattr(state, 'status') and hasattr(state.status, 'state')):
                raise WorkflowNotAwaitingApprovalError(
                    f"Workflow {run_id} state structure invalid"
                )

            if state.status.state != "awaiting_approval":
                raise WorkflowNotAwaitingApprovalError(
                    f"Workflow {run_id} is not awaiting approval"
                )

            # 3. Record approval decision
            approval_record = ApprovalDecisionRecord(
                approval_id=str(uuid4()),
                run_id=run_id,
                decision=ApprovalDecision.APPROVED,
                approver_id=approver_id,
                reason=reason,
            )
            await self.persistence.save_approval_decision(approval_record)

            # 4. Resume workflow execution with APPROVED decision
            workflow = create_agent_workflow()
            try:
                final_state = await workflow.ainvoke(state)
            except Exception as e:
                completed_at = datetime.now(UTC)
                duration = (completed_at - started_at).total_seconds()
                return WorkflowResult(
                    run_id=run_id,
                    status=WorkflowStatus.FAILED,
                    error=f"Workflow execution failed: {str(e)}",
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_seconds=duration,
                )

            # 5. Persist final state
            await self.persistence.save_workflow_state(run_id, final_state)

            # 6. Return final result
            completed_at = datetime.now(UTC)
            duration = (completed_at - started_at).total_seconds()

            output = None
            if hasattr(final_state, 'current_proposal') and final_state.current_proposal:
                output = final_state.current_proposal.dict() if hasattr(
                    final_state.current_proposal, 'dict'
                ) else final_state.current_proposal

            error = None
            if hasattr(final_state, 'status') and hasattr(final_state.status, 'error'):
                error = final_state.status.error

            return WorkflowResult(
                run_id=run_id,
                status=WorkflowStatus.SUCCESS if error is None else WorkflowStatus.FAILED,
                output=output,
                error=error,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
            )

        except (WorkflowNotFoundError, WorkflowNotAwaitingApprovalError, ApprovalTimeoutError):
            raise
        except Exception as e:
            completed_at = datetime.now(UTC)
            duration = (completed_at - started_at).total_seconds()
            return WorkflowResult(
                run_id=run_id,
                status=WorkflowStatus.FAILED,
                error=f"Approval processing failed: {str(e)}",
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
            )

    async def reject_workflow(
        self,
        run_id: str,
        approver_id: str,
        alternative_action: str,
        reason: str,
    ) -> WorkflowResult:
        """
        Reject the current proposal and execute an alternative action instead.
        
        Args:
            run_id: Workflow execution ID (must be in AWAITING_APPROVAL state)
            approver_id: ID of user rejecting
            alternative_action: Alternative command/action to execute
            reason: Reason for rejection and alternative choice
        
        Returns:
            WorkflowResult with final execution status
        
        Raises:
            WorkflowNotFoundError: If workflow not found
            WorkflowNotAwaitingApprovalError: If workflow not awaiting approval
            InvalidAlternativeActionError: If alternative action format invalid
            ApprovalTimeoutError: If approval timeout exceeded
        """
        started_at = datetime.now(UTC)

        try:
            # 1. Load persisted state
            state = await self.persistence.load_workflow_state(run_id)
            if not state:
                raise WorkflowNotFoundError(f"Workflow {run_id} not found")

            # 2. Check if waiting for approval
            if not (hasattr(state, 'status') and hasattr(state.status, 'state')):
                raise WorkflowNotAwaitingApprovalError(
                    f"Workflow {run_id} state structure invalid"
                )

            if state.status.state != "awaiting_approval":
                raise WorkflowNotAwaitingApprovalError(
                    f"Workflow {run_id} is not awaiting approval"
                )

            # 3. Validate alternative action format
            if not alternative_action or not isinstance(alternative_action, str):
                raise InvalidAlternativeActionError(
                    "alternative_action must be a non-empty string"
                )

            # 4. Record rejection decision with alternative action
            approval_record = ApprovalDecisionRecord(
                approval_id=str(uuid4()),
                run_id=run_id,
                decision=ApprovalDecision.REJECTED,
                approver_id=approver_id,
                reason=reason,
                metadata={
                    "alternative_action": alternative_action,
                },
            )
            await self.persistence.save_approval_decision(approval_record)

            # 5. Execute alternative action
            alternative_result = await self._execute_alternative_action(alternative_action)

            # 6. Resume workflow with REJECTED decision + alternative result
            workflow = create_agent_workflow()
            try:
                # Inject alternative result into state for LLM to process
                if hasattr(state, 'metadata'):
                    state.metadata["alternative_action"] = alternative_action
                    state.metadata["alternative_result"] = alternative_result
                    state.metadata["approval_decision"] = "rejected"

                final_state = await workflow.ainvoke(state)
            except Exception as e:
                completed_at = datetime.now(UTC)
                duration = (completed_at - started_at).total_seconds()
                return WorkflowResult(
                    run_id=run_id,
                    status=WorkflowStatus.FAILED,
                    error=f"Workflow execution failed after rejection: {str(e)}",
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_seconds=duration,
                )

            # 7. Persist final state
            await self.persistence.save_workflow_state(run_id, final_state)

            # 8. Return final result
            completed_at = datetime.now(UTC)
            duration = (completed_at - started_at).total_seconds()

            output = None
            if hasattr(final_state, 'current_proposal') and final_state.current_proposal:
                output = final_state.current_proposal.dict() if hasattr(
                    final_state.current_proposal, 'dict'
                ) else final_state.current_proposal

            error = None
            if hasattr(final_state, 'status') and hasattr(final_state.status, 'error'):
                error = final_state.status.error

            return WorkflowResult(
                run_id=run_id,
                status=WorkflowStatus.SUCCESS if error is None else WorkflowStatus.FAILED,
                output=output,
                error=error,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
            )

        except (WorkflowNotFoundError, WorkflowNotAwaitingApprovalError,
                InvalidAlternativeActionError, ApprovalTimeoutError):
            raise
        except Exception as e:
            completed_at = datetime.now(UTC)
            duration = (completed_at - started_at).total_seconds()
            return WorkflowResult(
                run_id=run_id,
                status=WorkflowStatus.FAILED,
                error=f"Rejection processing failed: {str(e)}",
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
            )

    async def cancel_workflow(
        self,
        run_id: str,
        canceller_id: str,
        reason: str,
    ) -> WorkflowResult:
        """
        Cancel a running or paused workflow completely.
        
        Args:
            run_id: Workflow execution ID
            canceller_id: ID of user cancelling
            reason: Reason for cancellation
        
        Returns:
            WorkflowResult with CANCELLED status
        
        Raises:
            WorkflowNotFoundError: If workflow not found
            WorkflowAlreadyCompletedError: If workflow already completed
        """
        try:
            # 1. Load persisted state
            state = await self.persistence.load_workflow_state(run_id)
            if not state:
                raise WorkflowNotFoundError(f"Workflow {run_id} not found")

            # 2. Check if already completed
            if hasattr(state, 'status') and hasattr(state.status, 'state'):
                if state.status.state in ["success", "failed", "cancelled", "timeout"]:
                    raise WorkflowAlreadyCompletedError(
                        f"Workflow {run_id} already completed with status {state.status.state}"
                    )

            # 3. Record cancellation
            await self.persistence.save_cancellation({
                "run_id": run_id,
                "canceller_id": canceller_id,
                "reason": reason,
                "cancelled_at": datetime.now(UTC),
            })

            # 4. Return cancelled result
            return WorkflowResult(
                run_id=run_id,
                status=WorkflowStatus.CANCELLED,
                error=f"Workflow cancelled by {canceller_id}: {reason}",
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                duration_seconds=0,
            )

        except (WorkflowNotFoundError, WorkflowAlreadyCompletedError):
            raise
        except Exception as e:
            return WorkflowResult(
                run_id=run_id,
                status=WorkflowStatus.FAILED,
                error=f"Cancellation failed: {str(e)}",
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                duration_seconds=0,
            )

    async def get_status(self, run_id: str) -> dict[str, Any]:
        """
        Get current status of a workflow execution.
        
        Args:
            run_id: Workflow execution ID
        
        Returns:
            Dictionary with status details
        
        Raises:
            WorkflowNotFoundError: If workflow not found
        """
        state = await self.persistence.load_workflow_state(run_id)
        if not state:
            raise WorkflowNotFoundError(f"Workflow {run_id} not found")

        status_dict = {
            "run_id": run_id,
            "state": getattr(state.status, 'state', 'unknown') if hasattr(state, 'status') else 'unknown',
            "created_at": getattr(state, 'created_at', None),
            "updated_at": getattr(state, 'updated_at', None),
        }

        # Add approval info if awaiting approval
        if status_dict["state"] == "awaiting_approval":
            if hasattr(state, 'approvals') and state.approvals:
                approval_req = state.approvals[-1]
                status_dict["approval_request"] = {
                    "operation": getattr(approval_req, 'operation', ''),
                    "risk_level": getattr(approval_req, 'risk_level', ''),
                    "description": getattr(approval_req, 'description', ''),
                    "created_at": getattr(approval_req, 'created_at', None),
                }

        return status_dict

    async def get_history(
        self,
        user_id: Optional[str] = None,
        agent_role: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Get workflow execution history.
        
        Args:
            user_id: Filter by user (optional)
            agent_role: Filter by agent role (optional)
            status: Filter by status (optional)
            limit: Number of results
            offset: Pagination offset
        
        Returns:
            List of workflow history entries
        """
        return await self.persistence.get_workflow_history(
            user_id=user_id,
            agent_role=agent_role,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def get_approval_history(
        self,
        run_id: Optional[str] = None,
        approver_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Get approval decision history.
        
        Args:
            run_id: Filter by workflow ID (optional)
            approver_id: Filter by approver (optional)
            status: Filter by status (optional)
            limit: Number of results
            offset: Pagination offset
        
        Returns:
            List of approval history entries
        """
        return await self.persistence.get_approval_history(
            run_id=run_id,
            approver_id=approver_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def _execute_alternative_action(self, alternative_action: str) -> dict[str, Any]:
        """
        Execute an alternative action.
        
        Args:
            alternative_action: Action to execute (e.g., "run_command: npm test")
        
        Returns:
            Dictionary with execution result
        """
        try:
            if alternative_action.startswith("run_command:"):
                command = alternative_action.replace("run_command:", "").strip()
                # TODO: Implement actual command execution
                # For now, return mock result
                return {
                    "status": "executed",
                    "command": command,
                    "output": f"Executed: {command}",
                    "exit_code": 0,
                }
            elif alternative_action == "skip_step":
                return {
                    "status": "skipped",
                    "action": "skip_step",
                }
            else:
                return {
                    "status": "unknown",
                    "action": alternative_action,
                    "error": f"Unknown alternative action: {alternative_action}",
                }
        except Exception as e:
            return {
                "status": "failed",
                "action": alternative_action,
                "error": str(e),
            }
