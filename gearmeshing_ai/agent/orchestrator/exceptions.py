"""
Custom exceptions for the orchestrator module.

Provides centralized exception definitions for workflow execution, approval handling,
and state management errors.
"""

from __future__ import annotations


class OrchestratorException(Exception):
    """Base exception for all orchestrator-related errors."""

    pass


class WorkflowNotFoundError(OrchestratorException):
    """Raised when workflow with given run_id not found."""

    pass


class WorkflowNotAwaitingApprovalError(OrchestratorException):
    """Raised when workflow is not in AWAITING_APPROVAL state."""

    pass


class WorkflowAlreadyCompletedError(OrchestratorException):
    """Raised when trying to approve/reject/cancel completed workflow."""

    pass


class InvalidAlternativeActionError(OrchestratorException):
    """Raised when alternative action format is invalid."""

    pass


class ApprovalTimeoutError(OrchestratorException):
    """Raised when approval timeout has been exceeded."""

    pass
