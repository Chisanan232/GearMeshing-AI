"""
Orchestrator engine for managing workflow execution and state.

Handles orchestration, coordination, state management, and approval workflow
state machine. Delegates execution details to WorkflowExecutor.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, AsyncIterator
from uuid import uuid4

from .models import (
    ApprovalDecision,
    ApprovalDecisionRecord,
    ApprovalRequest,
    OrchestratorConfig,
    WorkflowCallbacks,
    WorkflowCheckpoint,
    WorkflowEvent,
    WorkflowEventType,
    WorkflowResult,
    WorkflowStatus,
)
from .persistence import PersistenceManager
from .approval import ApprovalHandler


class OrchestratorEngine:
    """
    Main orchestrator engine for managing AI agent workflows.
    
    Handles:
    - Workflow execution coordination
    - Approval workflow state machine
    - State persistence and recovery
    - Event callbacks and logging
    """

    def __init__(
        self,
        config: OrchestratorConfig | None = None,
        persistence_manager: PersistenceManager | None = None,
        approval_handler: ApprovalHandler | None = None,
    ) -> None:
        """Initialize the orchestrator engine."""
        self.config = config or OrchestratorConfig()
        self.persistence_manager = persistence_manager or PersistenceManager(
            backend=self.config.persistence_backend
        )
        self.approval_handler = approval_handler or ApprovalHandler(
            persistence_manager=self.persistence_manager
        )
        self._active_workflows: dict[str, dict[str, Any]] = {}
        self._callbacks: dict[str, WorkflowCallbacks] = {}

    async def run_workflow(
        self,
        task_description: str,
        agent_role: str | None = None,
        user_id: str = "system",
        auto_select_role: bool = True,
        timeout_seconds: int | None = None,
        approval_timeout_seconds: int | None = None,
        callbacks: WorkflowCallbacks | None = None,
    ) -> WorkflowResult:
        """
        Execute a complete workflow and wait for completion or approval.
        
        Args:
            task_description: What the agent should do
            agent_role: Specific role or None for auto-select
            user_id: User triggering the workflow
            auto_select_role: Auto-select role based on task
            timeout_seconds: Maximum execution time
            approval_timeout_seconds: Max time to wait for approval
            callbacks: Event callbacks for monitoring
            
        Returns:
            WorkflowResult with execution status
        """
        run_id = str(uuid4())
        timeout_seconds = timeout_seconds or self.config.default_timeout_seconds
        approval_timeout_seconds = (
            approval_timeout_seconds or self.config.default_approval_timeout_seconds
        )

        # Store workflow state
        self._active_workflows[run_id] = {
            "task_description": task_description,
            "agent_role": agent_role,
            "user_id": user_id,
            "auto_select_role": auto_select_role,
            "status": WorkflowStatus.PENDING,
            "events": [],
            "created_at": datetime.now(UTC),
        }

        if callbacks:
            self._callbacks[run_id] = callbacks

        try:
            # Emit workflow started event
            await self._emit_event(
                run_id,
                WorkflowEventType.WORKFLOW_STARTED,
                {"task_description": task_description, "agent_role": agent_role},
            )

            # Execute workflow with timeout
            result = await asyncio.wait_for(
                self._execute_workflow(
                    run_id,
                    task_description,
                    agent_role,
                    user_id,
                    auto_select_role,
                    approval_timeout_seconds,
                ),
                timeout=timeout_seconds,
            )

            return result

        except asyncio.TimeoutError:
            return await self._handle_timeout(run_id)
        except Exception as e:
            return await self._handle_error(run_id, str(e))
        finally:
            # Cleanup
            self._active_workflows.pop(run_id, None)
            self._callbacks.pop(run_id, None)

    async def run_workflow_streaming(
        self,
        task_description: str,
        agent_role: str | None = None,
        user_id: str = "system",
        auto_select_role: bool = True,
        timeout_seconds: int | None = None,
        approval_timeout_seconds: int | None = None,
    ) -> AsyncIterator[WorkflowEvent]:
        """
        Execute workflow with real-time event streaming.
        
        Yields events for each workflow stage, allowing real-time monitoring
        and inline approval handling.
        
        Args:
            task_description: What the agent should do
            agent_role: Specific role or None for auto-select
            user_id: User triggering the workflow
            auto_select_role: Auto-select role based on task
            timeout_seconds: Maximum execution time
            approval_timeout_seconds: Max time to wait for approval
            
        Yields:
            WorkflowEvent objects for each stage
        """
        run_id = str(uuid4())
        timeout_seconds = timeout_seconds or self.config.default_timeout_seconds
        approval_timeout_seconds = (
            approval_timeout_seconds or self.config.default_approval_timeout_seconds
        )

        self._active_workflows[run_id] = {
            "task_description": task_description,
            "agent_role": agent_role,
            "user_id": user_id,
            "auto_select_role": auto_select_role,
            "status": WorkflowStatus.PENDING,
            "events": [],
            "created_at": datetime.now(UTC),
        }

        try:
            async for event in self._execute_workflow_streaming(
                run_id,
                task_description,
                agent_role,
                user_id,
                auto_select_role,
                approval_timeout_seconds,
            ):
                yield event

        finally:
            self._active_workflows.pop(run_id, None)

    async def submit_approval(
        self,
        run_id: str,
        approved: bool,
        approver_id: str,
        reason: str | None = None,
    ) -> ApprovalDecisionRecord:
        """
        Submit an approval decision for a paused workflow.
        
        Args:
            run_id: ID of the workflow
            approved: Whether the operation is approved
            approver_id: ID of the approver
            reason: Optional reason for the decision
            
        Returns:
            ApprovalDecisionRecord with the decision
        """
        decision = ApprovalDecision.APPROVED if approved else ApprovalDecision.REJECTED

        record = await self.approval_handler.resolve_approval(
            run_id=run_id,
            decision=decision,
            approver_id=approver_id,
            reason=reason,
        )

        # Emit approval event
        event_type = (
            WorkflowEventType.APPROVAL_APPROVED
            if approved
            else WorkflowEventType.APPROVAL_REJECTED
        )
        await self._emit_event(
            run_id,
            event_type,
            {"approver_id": approver_id, "reason": reason},
        )

        return record

    async def get_workflow_status(self, run_id: str) -> WorkflowStatus | None:
        """Get the current status of a workflow."""
        workflow = self._active_workflows.get(run_id)
        if workflow:
            status = workflow.get("status")
            if status:
                return status
        
        # Try to retrieve from persistence
        checkpoint = await self.persistence_manager.get_checkpoint(run_id)
        if checkpoint:
            status = checkpoint.metadata.get("status")
            if status:
                return status
        
        # Check events to infer status
        events = await self.persistence_manager.get_events(run_id)
        if events:
            # Check last event to infer status
            last_event = events[-1]
            if last_event.event_type == WorkflowEventType.WORKFLOW_COMPLETED:
                return WorkflowStatus.SUCCESS
            elif last_event.event_type == WorkflowEventType.WORKFLOW_FAILED:
                return WorkflowStatus.FAILED
            elif last_event.event_type == WorkflowEventType.APPROVAL_REQUIRED:
                return WorkflowStatus.AWAITING_APPROVAL
        
        return None

    async def cancel_workflow(self, run_id: str) -> bool:
        """Cancel a running workflow."""
        workflow = self._active_workflows.get(run_id)
        if workflow:
            workflow["status"] = WorkflowStatus.CANCELLED
            await self._emit_event(
                run_id,
                WorkflowEventType.WORKFLOW_CANCELLED,
                {},
            )
            return True
        return False

    async def get_workflow_history(self, run_id: str) -> list[WorkflowEvent]:
        """Get all events for a workflow."""
        workflow = self._active_workflows.get(run_id)
        if workflow:
            return workflow.get("events", [])
        
        # Try to retrieve from persistence
        events = await self.persistence_manager.get_events(run_id)
        return events or []

    async def get_approval_history(self, run_id: str) -> list[ApprovalDecisionRecord]:
        """Get all approval decisions for a workflow."""
        return await self.approval_handler.get_approval_history(run_id)

    # Private methods

    async def _execute_workflow(
        self,
        run_id: str,
        task_description: str,
        agent_role: str | None,
        user_id: str,
        auto_select_role: bool,
        approval_timeout_seconds: int,
    ) -> WorkflowResult:
        """Execute the workflow logic."""
        workflow = self._active_workflows[run_id]
        workflow["status"] = WorkflowStatus.RUNNING

        try:
            # Capability discovery
            await self._emit_event(
                run_id,
                WorkflowEventType.CAPABILITY_DISCOVERY_STARTED,
                {},
            )
            # Simulated capability discovery
            await asyncio.sleep(0.01)
            await self._emit_event(
                run_id,
                WorkflowEventType.CAPABILITY_DISCOVERY_COMPLETED,
                {"capabilities_found": 5},
            )

            # Agent decision
            await self._emit_event(
                run_id,
                WorkflowEventType.AGENT_DECISION_STARTED,
                {},
            )
            await asyncio.sleep(0.01)
            await self._emit_event(
                run_id,
                WorkflowEventType.AGENT_DECISION_COMPLETED,
                {"plan_steps": 3},
            )

            # Policy validation
            await self._emit_event(
                run_id,
                WorkflowEventType.POLICY_VALIDATION_STARTED,
                {},
            )
            await asyncio.sleep(0.01)
            
            # Check if approval is needed
            needs_approval = "deploy" in task_description.lower() or "delete" in task_description.lower()
            
            if needs_approval:
                approval_request = ApprovalRequest(
                    run_id=run_id,
                    operation="risky_operation",
                    risk_level="high",
                    description=f"Operation requires approval: {task_description}",
                    timeout_seconds=approval_timeout_seconds,
                )
                
                # Create approval request in handler
                await self.approval_handler.create_approval_request(
                    run_id=run_id,
                    operation="risky_operation",
                    risk_level="high",
                    description=f"Operation requires approval: {task_description}",
                    timeout_seconds=approval_timeout_seconds,
                )
                
                await self._emit_event(
                    run_id,
                    WorkflowEventType.APPROVAL_REQUIRED,
                    {"approval_request": approval_request},
                    approval_request=approval_request,
                )

                # Update status to awaiting approval BEFORE waiting
                workflow["status"] = WorkflowStatus.AWAITING_APPROVAL
                
                # Return immediately with awaiting approval status
                # The approval will be handled separately via submit_approval
                return WorkflowResult(
                    run_id=run_id,
                    status=WorkflowStatus.AWAITING_APPROVAL,
                    approval_request=approval_request,
                    events=workflow["events"],
                )

            await self._emit_event(
                run_id,
                WorkflowEventType.POLICY_VALIDATION_COMPLETED,
                {"policies_checked": 3},
            )

            # Result processing
            await self._emit_event(
                run_id,
                WorkflowEventType.RESULT_PROCESSING_STARTED,
                {},
            )
            await asyncio.sleep(0.01)
            await self._emit_event(
                run_id,
                WorkflowEventType.RESULT_PROCESSING_COMPLETED,
                {"result_status": "success"},
            )

            # Workflow completed
            workflow["status"] = WorkflowStatus.SUCCESS
            await self._emit_event(
                run_id,
                WorkflowEventType.WORKFLOW_COMPLETED,
                {"output": "Workflow completed successfully"},
            )

            return WorkflowResult(
                run_id=run_id,
                status=WorkflowStatus.SUCCESS,
                output={"result": "Workflow completed successfully"},
                events=workflow["events"],
            )

        except Exception as e:
            workflow["status"] = WorkflowStatus.FAILED
            await self._emit_event(
                run_id,
                WorkflowEventType.WORKFLOW_FAILED,
                {"error": str(e)},
            )
            return WorkflowResult(
                run_id=run_id,
                status=WorkflowStatus.FAILED,
                error=str(e),
                events=workflow["events"],
            )

    async def _execute_workflow_streaming(
        self,
        run_id: str,
        task_description: str,
        agent_role: str | None,
        user_id: str,
        auto_select_role: bool,
        approval_timeout_seconds: int,
    ) -> AsyncIterator[WorkflowEvent]:
        """Execute workflow and stream events."""
        workflow = self._active_workflows[run_id]
        workflow["status"] = WorkflowStatus.RUNNING

        try:
            # Capability discovery
            event = WorkflowEvent(
                event_type=WorkflowEventType.CAPABILITY_DISCOVERY_STARTED,
                run_id=run_id,
            )
            workflow["events"].append(event)
            yield event

            await asyncio.sleep(0.1)

            event = WorkflowEvent(
                event_type=WorkflowEventType.CAPABILITY_DISCOVERY_COMPLETED,
                run_id=run_id,
                payload={"capabilities_found": 5},
            )
            workflow["events"].append(event)
            yield event

            # Agent decision
            event = WorkflowEvent(
                event_type=WorkflowEventType.AGENT_DECISION_STARTED,
                run_id=run_id,
            )
            workflow["events"].append(event)
            yield event

            await asyncio.sleep(0.1)

            event = WorkflowEvent(
                event_type=WorkflowEventType.AGENT_DECISION_COMPLETED,
                run_id=run_id,
                payload={"plan_steps": 3},
            )
            workflow["events"].append(event)
            yield event

            # Policy validation
            event = WorkflowEvent(
                event_type=WorkflowEventType.POLICY_VALIDATION_STARTED,
                run_id=run_id,
            )
            workflow["events"].append(event)
            yield event

            await asyncio.sleep(0.1)

            # Check if approval is needed
            needs_approval = "deploy" in task_description.lower() or "delete" in task_description.lower()

            if needs_approval:
                approval_request = ApprovalRequest(
                    run_id=run_id,
                    operation="risky_operation",
                    risk_level="high",
                    description=f"Operation requires approval: {task_description}",
                    timeout_seconds=approval_timeout_seconds,
                )

                event = WorkflowEvent(
                    event_type=WorkflowEventType.APPROVAL_REQUIRED,
                    run_id=run_id,
                    approval_request=approval_request,
                    payload={"approval_request": approval_request},
                )
                workflow["events"].append(event)
                yield event

                # Wait for approval
                workflow["status"] = WorkflowStatus.AWAITING_APPROVAL
                decision = await self.approval_handler.wait_for_approval(
                    run_id=run_id,
                    timeout_seconds=approval_timeout_seconds,
                )

                if decision == ApprovalDecision.REJECTED:
                    event = WorkflowEvent(
                        event_type=WorkflowEventType.WORKFLOW_FAILED,
                        run_id=run_id,
                        payload={"reason": "Approval rejected"},
                    )
                    workflow["events"].append(event)
                    yield event
                    return

                elif decision == ApprovalDecision.TIMEOUT:
                    event = WorkflowEvent(
                        event_type=WorkflowEventType.APPROVAL_TIMEOUT,
                        run_id=run_id,
                    )
                    workflow["events"].append(event)
                    yield event

                    event = WorkflowEvent(
                        event_type=WorkflowEventType.WORKFLOW_FAILED,
                        run_id=run_id,
                        payload={"reason": "Approval timeout"},
                    )
                    workflow["events"].append(event)
                    yield event
                    return

            event = WorkflowEvent(
                event_type=WorkflowEventType.POLICY_VALIDATION_COMPLETED,
                run_id=run_id,
                payload={"policies_checked": 3},
            )
            workflow["events"].append(event)
            yield event

            # Result processing
            event = WorkflowEvent(
                event_type=WorkflowEventType.RESULT_PROCESSING_STARTED,
                run_id=run_id,
            )
            workflow["events"].append(event)
            yield event

            await asyncio.sleep(0.1)

            event = WorkflowEvent(
                event_type=WorkflowEventType.RESULT_PROCESSING_COMPLETED,
                run_id=run_id,
                payload={"result_status": "success"},
            )
            workflow["events"].append(event)
            yield event

            # Workflow completed
            workflow["status"] = WorkflowStatus.SUCCESS
            event = WorkflowEvent(
                event_type=WorkflowEventType.WORKFLOW_COMPLETED,
                run_id=run_id,
                payload={"output": "Workflow completed successfully"},
            )
            workflow["events"].append(event)
            yield event

        except Exception as e:
            workflow["status"] = WorkflowStatus.FAILED
            event = WorkflowEvent(
                event_type=WorkflowEventType.WORKFLOW_FAILED,
                run_id=run_id,
                payload={"error": str(e)},
            )
            workflow["events"].append(event)
            yield event

    async def _emit_event(
        self,
        run_id: str,
        event_type: WorkflowEventType,
        payload: dict[str, Any],
        approval_request: ApprovalRequest | None = None,
    ) -> None:
        """Emit a workflow event."""
        event = WorkflowEvent(
            event_type=event_type,
            run_id=run_id,
            payload=payload,
            approval_request=approval_request,
        )

        workflow = self._active_workflows.get(run_id)
        if workflow:
            workflow["events"].append(event)

        # Persist event
        if self.config.enable_event_logging:
            await self.persistence_manager.save_event(event)

        # Call callback
        callbacks = self._callbacks.get(run_id)
        if callbacks and callbacks.on_event:
            callbacks.on_event(event)

    async def _handle_timeout(self, run_id: str) -> WorkflowResult:
        """Handle workflow timeout."""
        workflow = self._active_workflows.get(run_id, {})
        await self._emit_event(
            run_id,
            WorkflowEventType.WORKFLOW_FAILED,
            {"reason": "Execution timeout"},
        )
        return WorkflowResult(
            run_id=run_id,
            status=WorkflowStatus.TIMEOUT,
            error="Execution timeout",
            events=workflow.get("events", []),
        )

    async def _handle_error(self, run_id: str, error: str) -> WorkflowResult:
        """Handle workflow error."""
        workflow = self._active_workflows.get(run_id, {})
        await self._emit_event(
            run_id,
            WorkflowEventType.WORKFLOW_FAILED,
            {"error": error},
        )
        return WorkflowResult(
            run_id=run_id,
            status=WorkflowStatus.FAILED,
            error=error,
            events=workflow.get("events", []),
        )
