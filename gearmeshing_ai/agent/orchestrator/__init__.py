"""
Orchestrator module for managing AI agent workflows.

Provides high-level functions for triggering, monitoring, and managing
AI agent workflows with support for user approval workflows, state persistence,
and comprehensive event callbacks.
"""

from gearmeshing_ai.agent.orchestrator.service import OrchestratorService
from gearmeshing_ai.agent.orchestrator.approval_workflow import ApprovalWorkflow
from gearmeshing_ai.agent.orchestrator.models import (
    WorkflowResult,
    WorkflowStatus,
    ApprovalRequest,
    ApprovalDecision,
    ApprovalDecisionRecord,
    WorkflowCallbacks,
    OrchestratorConfig,
)
from gearmeshing_ai.agent.orchestrator.persistence import PersistenceManager
from gearmeshing_ai.agent.orchestrator.exceptions import (
    OrchestratorException,
    WorkflowNotFoundError,
    WorkflowNotAwaitingApprovalError,
    WorkflowAlreadyCompletedError,
    InvalidAlternativeActionError,
    ApprovalTimeoutError,
)


# Simple API functions for external use
_default_service = None


def _get_service() -> OrchestratorService:
    """Get or create default OrchestratorService instance."""
    global _default_service
    if _default_service is None:
        _default_service = OrchestratorService()
    return _default_service


async def run_agent_workflow(
    task_description: str,
    agent_role: str | None = None,
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
        WorkflowResult with execution status
    """
    service = _get_service()
    return await service.run_workflow(
        task_description=task_description,
        agent_role=agent_role,
        user_id=user_id,
        timeout_seconds=timeout_seconds,
        approval_timeout_seconds=approval_timeout_seconds,
    )


async def approve_workflow(
    run_id: str,
    approver_id: str,
    reason: str | None = None,
) -> WorkflowResult:
    """
    Approve the current proposal and resume workflow normally.
    
    Args:
        run_id: Workflow execution ID
        approver_id: ID of user approving
        reason: Optional reason for approval
    
    Returns:
        WorkflowResult with final execution status
    """
    service = _get_service()
    return await service.approve_workflow(
        run_id=run_id,
        approver_id=approver_id,
        reason=reason,
    )


async def reject_workflow(
    run_id: str,
    approver_id: str,
    alternative_action: str,
    reason: str,
) -> WorkflowResult:
    """
    Reject the current proposal and execute an alternative action instead.
    
    Args:
        run_id: Workflow execution ID
        approver_id: ID of user rejecting
        alternative_action: Alternative command/action to execute
        reason: Reason for rejection and alternative choice
    
    Returns:
        WorkflowResult with final execution status
    """
    service = _get_service()
    return await service.reject_workflow(
        run_id=run_id,
        approver_id=approver_id,
        alternative_action=alternative_action,
        reason=reason,
    )


async def cancel_workflow(
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
    """
    service = _get_service()
    return await service.cancel_workflow(
        run_id=run_id,
        canceller_id=canceller_id,
        reason=reason,
    )


async def get_workflow_status(run_id: str) -> dict:
    """
    Get current status of a workflow execution.
    
    Args:
        run_id: Workflow execution ID
    
    Returns:
        Dictionary with status details
    """
    service = _get_service()
    return await service.get_status(run_id)


async def get_workflow_history(
    user_id: str | None = None,
    agent_role: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
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
    service = _get_service()
    return await service.get_history(
        user_id=user_id,
        agent_role=agent_role,
        status=status,
        limit=limit,
        offset=offset,
    )


async def get_approval_history(
    run_id: str | None = None,
    approver_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
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
    service = _get_service()
    return await service.get_approval_history(
        run_id=run_id,
        approver_id=approver_id,
        status=status,
        limit=limit,
        offset=offset,
    )


__all__ = [
    # New API (recommended)
    "run_agent_workflow",
    "approve_workflow",
    "reject_workflow",
    "cancel_workflow",
    "get_workflow_status",
    "get_workflow_history",
    "get_approval_history",
    # Service classes
    "OrchestratorService",
    "ApprovalWorkflow",
    "PersistenceManager",
    # Models
    "WorkflowResult",
    "WorkflowStatus",
    "ApprovalRequest",
    "ApprovalDecision",
    "ApprovalDecisionRecord",
    "WorkflowCallbacks",
    "OrchestratorConfig",
    # Exceptions
    "OrchestratorException",
    "WorkflowNotFoundError",
    "WorkflowNotAwaitingApprovalError",
    "WorkflowAlreadyCompletedError",
    "InvalidAlternativeActionError",
    "ApprovalTimeoutError",
]
