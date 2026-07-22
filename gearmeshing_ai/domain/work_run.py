"""Framework-independent domain model for governed work execution."""

from enum import StrEnum


class InvalidWorkRunTransition(ValueError):
    """Raised when a WorkRun lifecycle transition violates domain rules."""


class WorkRunState(StrEnum):
    """Execution stages and terminal outcomes for a WorkRun."""

    APPROVED = "approved"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    REMEDIATING = "remediating"
    PUBLISHING_DRAFT_PR = "publishing_draft_pr"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        """Return whether the state represents a final WorkRun outcome."""
        return self in TERMINAL_WORK_RUN_STATES


TERMINAL_WORK_RUN_STATES = frozenset(
    {
        WorkRunState.COMPLETED,
        WorkRunState.FAILED,
        WorkRunState.BLOCKED,
        WorkRunState.CANCELLED,
    }
)

VALID_WORK_RUN_TRANSITIONS: dict[WorkRunState, frozenset[WorkRunState]] = {
    WorkRunState.APPROVED: frozenset(
        {
            WorkRunState.EXECUTING,
            WorkRunState.BLOCKED,
            WorkRunState.CANCELLED,
        }
    ),
    WorkRunState.EXECUTING: frozenset(
        {
            WorkRunState.VERIFYING,
            WorkRunState.FAILED,
            WorkRunState.BLOCKED,
            WorkRunState.CANCELLED,
        }
    ),
    WorkRunState.VERIFYING: frozenset(
        {
            WorkRunState.REMEDIATING,
            WorkRunState.PUBLISHING_DRAFT_PR,
            WorkRunState.FAILED,
            WorkRunState.BLOCKED,
            WorkRunState.CANCELLED,
        }
    ),
    WorkRunState.REMEDIATING: frozenset(
        {
            WorkRunState.EXECUTING,
            WorkRunState.VERIFYING,
            WorkRunState.FAILED,
            WorkRunState.BLOCKED,
            WorkRunState.CANCELLED,
        }
    ),
    WorkRunState.PUBLISHING_DRAFT_PR: frozenset(
        {
            WorkRunState.COMPLETED,
            WorkRunState.FAILED,
            WorkRunState.BLOCKED,
            WorkRunState.CANCELLED,
        }
    ),
    WorkRunState.COMPLETED: frozenset(),
    WorkRunState.FAILED: frozenset(),
    WorkRunState.BLOCKED: frozenset(),
    WorkRunState.CANCELLED: frozenset(),
}
