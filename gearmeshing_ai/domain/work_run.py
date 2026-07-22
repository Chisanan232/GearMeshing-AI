"""Framework-independent domain model for governed work execution."""

from enum import StrEnum
from urllib.parse import urlsplit


_MAX_IDENTIFIER_LENGTH = 255
_MAX_URI_LENGTH = 2048


def _require_bounded_text(value: str, field_name: str) -> str:
    """Validate and normalize a bounded, non-sensitive identifier."""
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) > _MAX_IDENTIFIER_LENGTH:
        raise ValueError(f"{field_name} must not exceed {_MAX_IDENTIFIER_LENGTH} characters")
    if any(character.isspace() or ord(character) < 32 for character in normalized):
        raise ValueError(f"{field_name} must not contain whitespace or control characters")
    return normalized


def _require_safe_uri(value: str, field_name: str) -> str:
    """Validate a URI without accepting embedded credentials."""
    normalized = value.strip()
    if not normalized or len(normalized) > _MAX_URI_LENGTH:
        raise ValueError(f"{field_name} must be between 1 and {_MAX_URI_LENGTH} characters")

    parsed = urlsplit(normalized)
    if not parsed.scheme:
        raise ValueError(f"{field_name} must be an absolute URI")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{field_name} must not contain credentials")
    return normalized


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
