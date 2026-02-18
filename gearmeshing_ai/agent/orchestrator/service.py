"""OrchestratorService - Thin wrapper around runtime workflow.

Provides simple, clean API for executing AI agent workflows with approval support.
Delegates all workflow execution to the runtime package.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from gearmeshing_ai.agent.orchestrator.exceptions import (
    ApprovalTimeoutError,
    InvalidAlternativeActionError,
    WorkflowAlreadyCompletedError,
    WorkflowNotAwaitingApprovalError,
    WorkflowNotFoundError,
)
from gearmeshing_ai.agent.orchestrator.models import (
    ApprovalDecision,
    ApprovalDecisionRecord,
    WorkflowResult,
    WorkflowStatus,
)
from gearmeshing_ai.agent.orchestrator.persistence import PersistenceManager
from gearmeshing_ai.agent.runtime import ExecutionContext, WorkflowState, create_agent_workflow
from gearmeshing_ai.agent.runtime.models import WorkflowStatus as RuntimeWorkflowStatus
from gearmeshing_ai.agent.abstraction.factory import AgentFactory
from gearmeshing_ai.agent.mcp.client.core import MCPClient
from gearmeshing_ai.agent.adapters.pydantic_ai import PydanticAIAdapter
from gearmeshing_ai.agent.models.actions import MCPToolCatalog


logger = logging.getLogger(__name__)


class OrchestratorService:
    """Thin wrapper around runtime workflow.

    Provides simple API for executing AI agent workflows with approval support.
    Delegates execution to runtime, handles persistence and approval coordination.
    """

    def __init__(self, persistence: PersistenceManager | None = None):
        """Initialize OrchestratorService.

        Args:
            persistence: PersistenceManager for state persistence
                        (defaults to in-memory if not provided)

        """
        self.persistence: PersistenceManager = persistence or PersistenceManager()

    def _create_workflow(self) -> Any:
        """Create LangGraph workflow with required dependencies.
        
        Returns:
            Compiled LangGraph workflow graph
        """
        try:
            # Create adapter with empty tool catalog for proposal mode
            adapter = PydanticAIAdapter(proposal_mode=True, tool_catalog=MCPToolCatalog(tools=[]))
            
            # Create MCP client with proper configuration
            # Note: MCPClient requires a transport to be set via set_transport()
            # For now, we create it without transport - the runtime will handle tool discovery
            mcp_client = MCPClient()
            logger.debug("Created MCPClient for workflow")
            
            # Create agent factory with adapter and MCP client
            agent_factory = AgentFactory(adapter=adapter, mcp_client=mcp_client, proposal_mode=True)
            
            # Create and return workflow
            logger.debug("Creating LangGraph workflow with agent factory and MCP client")
            return create_agent_workflow(
                agent_factory=agent_factory,
                mcp_client=mcp_client,
                # Use default values for optional parameters
                capability_registry=None,
                policy_engine=None,
                approval_manager=None
            )
        except Exception as e:
            logger.error(f"Failed to create workflow: {e}", exc_info=True)
            raise ValueError(f"Workflow creation failed: {e}") from e

    async def run_workflow(
        self,
        task_description: str,
        agent_role: str | None = None,
        user_id: str = "system",
        timeout_seconds: int = 300,
        approval_timeout_seconds: int = 3600,
    ) -> WorkflowResult:
        """Execute a complete AI agent workflow.

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

        logger.info(f"Starting workflow {run_id}: task='{task_description}', role='{agent_role}', user='{user_id}'")

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
                status=RuntimeWorkflowStatus(
                    state="pending",
                    message="Workflow initialized"
                ),
                context=context,
            )

            # 3. Create runtime workflow
            logger.debug(f"Creating LangGraph workflow for run_id={run_id}")
            workflow = self._create_workflow()

            # 4. Execute workflow (delegate to runtime)
            logger.info(f"Executing workflow {run_id} with {timeout_seconds}s timeout")
            try:
                final_state = await asyncio.wait_for(
                    workflow.ainvoke(state),
                    timeout=timeout_seconds,
                )
            except TimeoutError:
                logger.warning(f"Workflow {run_id} timed out after {timeout_seconds}s")
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
            if hasattr(final_state, "status") and hasattr(final_state.status, "state"):
                if final_state.status.state == "awaiting_approval":
                    logger.info(f"Workflow {run_id} requires approval - pausing execution")
                    approval_request = None
                    if hasattr(final_state, "approvals") and final_state.approvals:
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
            if hasattr(final_state, "current_proposal") and final_state.current_proposal:
                output = (
                    final_state.current_proposal.dict()
                    if hasattr(final_state.current_proposal, "dict")
                    else final_state.current_proposal
                )

            error = None
            if hasattr(final_state, "status") and hasattr(final_state.status, "error"):
                error = final_state.status.error

            final_status = WorkflowStatus.SUCCESS if error is None else WorkflowStatus.FAILED
            logger.info(f"Workflow {run_id} completed: status={final_status.value}, duration={duration:.1f}s")

            return WorkflowResult(
                run_id=run_id,
                status=final_status,
                output=output,
                error=error,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
            )

        except Exception as e:
            logger.error(f"Workflow {run_id} failed: {e!s}", exc_info=True)
            completed_at = datetime.now(UTC)
            duration = (completed_at - started_at).total_seconds()
            return WorkflowResult(
                run_id=run_id,
                status=WorkflowStatus.FAILED,
                error=f"Workflow execution failed: {e!s}",
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
            )

    async def approve_workflow(
        self,
        run_id: str,
        approver_id: str,
        reason: str | None = None,
    ) -> WorkflowResult:
        """Approve the current proposal and resume workflow normally.

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

        logger.info(f"Processing approval for workflow {run_id}: decision={reason}, approver={approver_id}")

        try:
            # 1. Load persisted state
            state = await self.persistence.load_workflow_state(run_id)
            if not state:
                logger.warning(f"Workflow {run_id} not found for approval")
                raise WorkflowNotFoundError(f"Workflow {run_id} not found")

            # 2. Check if waiting for approval
            if not (hasattr(state, "status") and hasattr(state.status, "state")):
                logger.error(f"Workflow {run_id} state structure invalid for approval")
                raise WorkflowNotAwaitingApprovalError(f"Workflow {run_id} state structure invalid")

            if state.status.state != "awaiting_approval":
                logger.warning(f"Workflow {run_id} not awaiting approval (current state: {state.status.state})")
                raise WorkflowNotAwaitingApprovalError(f"Workflow {run_id} is not awaiting approval")

            # 3. Record approval decision
            approval_record = ApprovalDecisionRecord(
                approval_id=str(uuid4()),
                run_id=run_id,
                decision=ApprovalDecision.APPROVED,
                approver_id=approver_id,
                reason=reason,
            )
            await self.persistence.save_approval_decision(approval_record)
            logger.debug(f"Recorded approval decision for workflow {run_id}: {approval_record.decision.value}")

            # 4. Resume workflow execution with APPROVED decision
            logger.info(f"Resuming workflow {run_id} after approval")
            workflow = self._create_workflow()
            try:
                final_state = await workflow.ainvoke(state)
            except Exception as e:
                logger.error(f"Workflow {run_id} failed after approval: {e!s}", exc_info=True)
                completed_at = datetime.now(UTC)
                duration = (completed_at - started_at).total_seconds()
                return WorkflowResult(
                    run_id=run_id,
                    status=WorkflowStatus.FAILED,
                    error=f"Workflow execution failed: {e!s}",
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
            if hasattr(final_state, "current_proposal") and final_state.current_proposal:
                output = (
                    final_state.current_proposal.dict()
                    if hasattr(final_state.current_proposal, "dict")
                    else final_state.current_proposal
                )

            error = None
            if hasattr(final_state, "status") and hasattr(final_state.status, "error"):
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
                error=f"Approval processing failed: {e!s}",
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
        """Reject the current proposal and execute an alternative action instead.

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

        logger.info(f"Processing rejection for workflow {run_id}: alternative='{alternative_action}', approver={approver_id}")

        try:
            # 1. Load persisted state
            logger.debug(f"Loading state for workflow {run_id}")
            state = await self.persistence.load_workflow_state(run_id)
            if not state:
                logger.warning(f"Workflow {run_id} not found for rejection")
                raise WorkflowNotFoundError(f"Workflow {run_id} not found")

            # 2. Check if waiting for approval
            if not (hasattr(state, "status") and hasattr(state.status, "state")):
                logger.error(f"Workflow {run_id} state structure invalid for rejection")
                raise WorkflowNotAwaitingApprovalError(f"Workflow {run_id} state structure invalid")

            if state.status.state != "awaiting_approval":
                logger.warning(f"Workflow {run_id} not awaiting approval (current state: {state.status.state})")
                raise WorkflowNotAwaitingApprovalError(f"Workflow {run_id} is not awaiting approval")

            # 3. Validate alternative action format
            logger.debug(f"Validating alternative action for workflow {run_id}: {alternative_action}")
            if not alternative_action or not isinstance(alternative_action, str):
                logger.error(f"Invalid alternative action for workflow {run_id}: {alternative_action}")
                raise InvalidAlternativeActionError("alternative_action must be a non-empty string")

            # 4. Record rejection decision with alternative action
            logger.debug(f"Recording rejection decision for workflow {run_id}")
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
            logger.info(f"Recorded rejection decision for workflow {run_id}: alternative='{alternative_action}'")

            # 5. Execute alternative action
            logger.debug(f"Executing alternative action for workflow {run_id}: {alternative_action}")
            alternative_result = await self._execute_alternative_action(alternative_action)

            # 6. Resume workflow with REJECTED decision + alternative result
            logger.info(f"Resuming workflow {run_id} after rejection")
            workflow = self._create_workflow()
            try:
                # Inject alternative result into state for LLM to process
                if hasattr(state, "metadata"):
                    state.metadata["alternative_action"] = alternative_action
                    state.metadata["alternative_result"] = alternative_result
                    state.metadata["approval_decision"] = "rejected"

                final_state = await workflow.ainvoke(state)
            except Exception as e:
                logger.error(f"Workflow {run_id} failed after rejection: {e!s}", exc_info=True)
                completed_at = datetime.now(UTC)
                duration = (completed_at - started_at).total_seconds()
                return WorkflowResult(
                    run_id=run_id,
                    status=WorkflowStatus.FAILED,
                    error=f"Workflow execution failed after rejection: {e!s}",
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
            if hasattr(final_state, "current_proposal") and final_state.current_proposal:
                output = (
                    final_state.current_proposal.dict()
                    if hasattr(final_state.current_proposal, "dict")
                    else final_state.current_proposal
                )

            error = None
            if hasattr(final_state, "status") and hasattr(final_state.status, "error"):
                error = final_state.status.error

            final_status = WorkflowStatus.SUCCESS if error is None else WorkflowStatus.FAILED
            logger.info(f"Workflow {run_id} completed after rejection: status={final_status.value}, duration={duration:.1f}s")

            return WorkflowResult(
                run_id=run_id,
                status=final_status,
                output=output,
                error=error,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
            )

        except (
            WorkflowNotFoundError,
            WorkflowNotAwaitingApprovalError,
            InvalidAlternativeActionError,
            ApprovalTimeoutError,
        ):
            raise
        except Exception as e:
            logger.error(f"Rejection processing failed for workflow {run_id}: {e!s}", exc_info=True)
            completed_at = datetime.now(UTC)
            duration = (completed_at - started_at).total_seconds()
            return WorkflowResult(
                run_id=run_id,
                status=WorkflowStatus.FAILED,
                error=f"Rejection processing failed: {e!s}",
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
        """Cancel a running or paused workflow completely.

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
        logger.info(f"Processing cancellation for workflow {run_id}: canceller={canceller_id}, reason='{reason}'")

        try:
            # 1. Load persisted state
            logger.debug(f"Loading state for workflow {run_id}")
            state = await self.persistence.load_workflow_state(run_id)
            if not state:
                logger.warning(f"Workflow {run_id} not found for cancellation")
                raise WorkflowNotFoundError(f"Workflow {run_id} not found")

            # 2. Check if already completed
            if hasattr(state, "status") and hasattr(state.status, "state"):
                if state.status.state in ["success", "failed", "cancelled", "timeout"]:
                    logger.warning(f"Workflow {run_id} already completed with status {state.status.state}")
                    raise WorkflowAlreadyCompletedError(
                        f"Workflow {run_id} already completed with status {state.status.state}"
                    )

            # 3. Record cancellation
            logger.debug(f"Recording cancellation for workflow {run_id}")
            await self.persistence.save_cancellation(
                {
                    "run_id": run_id,
                    "canceller_id": canceller_id,
                    "reason": reason,
                    "cancelled_at": datetime.now(UTC),
                }
            )

            # 4. Return cancelled result
            logger.info(f"Workflow {run_id} successfully cancelled")
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
            logger.error(f"Cancellation failed for workflow {run_id}: {e!s}", exc_info=True)
            return WorkflowResult(
                run_id=run_id,
                status=WorkflowStatus.FAILED,
                error=f"Cancellation failed: {e!s}",
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                duration_seconds=0,
            )

    async def get_status(self, run_id: str) -> dict[str, Any]:
        """Get current status of a workflow execution.

        Args:
            run_id: Workflow execution ID

        Returns:
            Dictionary with status details

        Raises:
            WorkflowNotFoundError: If workflow not found

        """
        state = await self.persistence.load_workflow_state(run_id)
        if not state:
            logger.warning(f"Status query failed - workflow {run_id} not found")
            raise WorkflowNotFoundError(f"Workflow {run_id} not found")

        status_dict = {
            "run_id": run_id,
            "state": getattr(state.status, "state", "unknown") if hasattr(state, "status") else "unknown",
            "created_at": getattr(state, "created_at", None),
            "updated_at": getattr(state, "updated_at", None),
        }

        # Add approval info if awaiting approval
        if status_dict["state"] == "awaiting_approval":
            if hasattr(state, "approvals") and state.approvals:
                approval_req = state.approvals[-1]
                status_dict["approval_request"] = {
                    "operation": getattr(approval_req, "operation", ""),
                    "risk_level": getattr(approval_req, "risk_level", ""),
                    "description": getattr(approval_req, "description", ""),
                    "created_at": getattr(approval_req, "created_at", None),
                }

        logger.debug(f"Workflow {run_id} status: {status_dict['state']}")
        return status_dict

    async def get_history(
        self,
        user_id: str | None = None,
        agent_role: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get workflow execution history.

        Args:
            user_id: Filter by user (optional)
            agent_role: Filter by agent role (optional)
            status: Filter by status (optional)
            limit: Number of results
            offset: Pagination offset

        Returns:
            List of workflow history entries

        """
        logger.debug(f"Querying workflow history: user={user_id}, role={agent_role}, status={status}, limit={limit}, offset={offset}")
        history = await self.persistence.get_workflow_history(
            user_id=user_id,
            agent_role=agent_role,
            status=status,
            limit=limit,
            offset=offset,
        )
        logger.info(f"Retrieved {len(history)} workflow history entries")
        return history

    async def get_approval_history(
        self,
        run_id: str | None = None,
        approver_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get approval decision history.

        Args:
            run_id: Filter by workflow ID (optional)
            approver_id: Filter by approver (optional)
            status: Filter by status (optional)
            limit: Number of results
            offset: Pagination offset

        Returns:
            List of approval history entries

        """
        logger.debug(f"Querying approval history: run_id={run_id}, approver={approver_id}, status={status}, limit={limit}, offset={offset}")
        history = await self.persistence.get_approval_history(
            run_id=run_id,
            approver_id=approver_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        logger.info(f"Retrieved {len(history)} approval history entries")
        return history

    async def _execute_alternative_action(self, alternative_action: str) -> dict[str, Any]:
        """Execute an alternative action.

        Args:
            alternative_action: Action to execute (e.g., "run_command: npm test")

        Returns:
            Dictionary with execution result

        """
        logger.debug(f"Executing alternative action: {alternative_action}")
        try:
            if alternative_action.startswith("run_command:"):
                command = alternative_action.replace("run_command:", "").strip()
                logger.debug(f"Executing command: {command}")
                # TODO: Implement actual command execution
                # For now, return mock result
                result = {
                    "status": "executed",
                    "command": command,
                    "output": f"Executed: {command}",
                    "exit_code": 0,
                }
                logger.info(f"Alternative action executed successfully: {alternative_action}")
                return result
            if alternative_action == "skip_step":
                logger.debug("Skipping step as alternative action")
                result = {
                    "status": "skipped",
                    "action": "skip_step",
                }
                logger.info("Alternative action executed successfully: skip_step")
                return result
            logger.warning(f"Unknown alternative action: {alternative_action}")
            result = {
                "status": "unknown",
                "action": alternative_action,
                "error": f"Unknown alternative action: {alternative_action}",
            }
            return result
        except Exception as e:
            logger.error(f"Alternative action execution failed: {alternative_action} - {e!s}", exc_info=True)
            return {
                "status": "failed",
                "action": alternative_action,
                "error": str(e),
            }
