"""Framework-independent domain model for governed work execution."""

from dataclasses import dataclass, field, replace
from enum import StrEnum
import re
from urllib.parse import urlsplit
from uuid import UUID, uuid4


_MAX_IDENTIFIER_LENGTH = 255
_MAX_URI_LENGTH = 2048
_JIRA_ISSUE_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*-[1-9][0-9]*$")


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


def _require_jira_issue_key(value: str) -> str:
    """Validate a canonical Jira issue key."""
    normalized = value.strip().upper()
    if not _JIRA_ISSUE_KEY_PATTERN.fullmatch(normalized):
        raise ValueError("jira_issue_key must use the PROJECT-123 format")
    return normalized


def _require_https_url(value: str, field_name: str) -> str:
    """Validate an HTTPS URL suitable for cross-system correlation."""
    normalized = _require_safe_uri(value, field_name)
    parsed = urlsplit(normalized)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"{field_name} must be an HTTPS URL")
    return normalized


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    """Stable pointer to an artifact produced or consumed by a WorkRun."""

    artifact_id: str
    kind: str
    uri: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_id", _require_bounded_text(self.artifact_id, "artifact_id"))
        object.__setattr__(self, "kind", _require_bounded_text(self.kind, "kind"))
        object.__setattr__(self, "uri", _require_safe_uri(self.uri, "uri"))


@dataclass(frozen=True, slots=True)
class EventReference:
    """Stable identifier for an event associated with a WorkRun."""

    event_id: str
    event_type: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", _require_bounded_text(self.event_id, "event_id"))
        object.__setattr__(self, "event_type", _require_bounded_text(self.event_type, "event_type"))


@dataclass(frozen=True, slots=True)
class WorkRunCorrelation:
    """Identifiers used to correlate a WorkRun across governed systems."""

    jira_issue_key: str
    repository: str
    branch: str
    agent_assembly_correlation_id: str
    pull_request_url: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "jira_issue_key", _require_jira_issue_key(self.jira_issue_key))
        object.__setattr__(self, "repository", _require_https_url(self.repository, "repository"))
        object.__setattr__(self, "branch", _require_bounded_text(self.branch, "branch"))
        object.__setattr__(
            self,
            "agent_assembly_correlation_id",
            _require_bounded_text(
                self.agent_assembly_correlation_id,
                "agent_assembly_correlation_id",
            ),
        )
        if self.pull_request_url is not None:
            object.__setattr__(
                self,
                "pull_request_url",
                _require_https_url(self.pull_request_url, "pull_request_url"),
            )


@dataclass(frozen=True, slots=True)
class WorkRunIdentity:
    """Stable internal identity for one WorkRun."""

    run_id: UUID

    @classmethod
    def new(cls) -> "WorkRunIdentity":
        """Create a WorkRun identity using a random, non-semantic identifier."""
        return cls(run_id=uuid4())

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, UUID):
            raise TypeError("run_id must be a UUID")


class InvalidWorkRunTransitionError(ValueError):
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


@dataclass(frozen=True, slots=True)
class WorkRun:
    """Immutable aggregate describing one governed work execution."""

    correlation: WorkRunCorrelation
    identity: WorkRunIdentity = field(default_factory=WorkRunIdentity.new)
    state: WorkRunState = WorkRunState.APPROVED
    artifact_references: tuple[ArtifactReference, ...] = ()
    event_references: tuple[EventReference, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.correlation, WorkRunCorrelation):
            raise TypeError("correlation must be a WorkRunCorrelation")
        if not isinstance(self.identity, WorkRunIdentity):
            raise TypeError("identity must be a WorkRunIdentity")
        if not isinstance(self.state, WorkRunState):
            raise TypeError("state must be a WorkRunState")
        if not isinstance(self.artifact_references, tuple) or any(
            not isinstance(reference, ArtifactReference) for reference in self.artifact_references
        ):
            raise TypeError("artifact_references must contain only ArtifactReference values")
        if not isinstance(self.event_references, tuple) or any(
            not isinstance(reference, EventReference) for reference in self.event_references
        ):
            raise TypeError("event_references must contain only EventReference values")

    def transition_to(self, target: WorkRunState) -> "WorkRun":
        """Return a new WorkRun in ``target`` when the transition is valid."""
        if not isinstance(target, WorkRunState):
            raise TypeError("target must be a WorkRunState")
        if target not in VALID_WORK_RUN_TRANSITIONS[self.state]:
            raise InvalidWorkRunTransitionError(f"cannot transition from {self.state} to {target}")
        if target is WorkRunState.COMPLETED and self.correlation.pull_request_url is None:
            raise InvalidWorkRunTransitionError("a completed WorkRun must reference its Draft PR")
        return replace(self, state=target)

    def associate_pull_request(self, pull_request_url: str) -> "WorkRun":
        """Return a new WorkRun correlated with its Draft pull request."""
        correlation = replace(self.correlation, pull_request_url=pull_request_url)
        return replace(self, correlation=correlation)

    def with_artifact_reference(self, reference: ArtifactReference) -> "WorkRun":
        """Return a new WorkRun containing one additional artifact reference."""
        if not isinstance(reference, ArtifactReference):
            raise TypeError("reference must be an ArtifactReference")
        if reference in self.artifact_references:
            return self
        return replace(self, artifact_references=(*self.artifact_references, reference))

    def with_event_reference(self, reference: EventReference) -> "WorkRun":
        """Return a new WorkRun containing one additional event reference."""
        if not isinstance(reference, EventReference):
            raise TypeError("reference must be an EventReference")
        if reference in self.event_references:
            return self
        return replace(self, event_references=(*self.event_references, reference))
