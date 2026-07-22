"""Provider-neutral contract for executing approved coding work."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from os.path import abspath
from pathlib import Path
from re import fullmatch
from typing import Protocol


class ExecutionStatus(StrEnum):
    """Terminal states returned by a coding executor."""

    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    FAILED = "failed"


class ExecutionFailureKind(StrEnum):
    """Stable failure classifications independent of executor providers."""

    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    POLICY = "policy"
    PROVIDER = "provider"
    INTERNAL = "internal"


class ExecutionEventKind(StrEnum):
    """Portable event categories emitted during execution."""

    STARTED = "started"
    PROGRESS = "progress"
    TOOL_STARTED = "tool_started"
    TOOL_FINISHED = "tool_finished"
    FINISHED = "finished"


class ExecutorFeature(StrEnum):
    """Discoverable behaviors that an executor adapter may support."""

    EVENT_STREAMING = "event_streaming"
    ARTIFACT_STREAMING = "artifact_streaming"
    CANCELLATION = "cancellation"


@dataclass(frozen=True, slots=True)
class RepositoryContext:
    """Repository and isolated worktree selected for an execution."""

    repository_root: Path
    worktree_root: Path
    base_revision: str

    def __post_init__(self) -> None:
        """Reject ambiguous repository or worktree execution paths."""
        if not self.repository_root.is_absolute() or not self.worktree_root.is_absolute():
            message = "repository and worktree paths must be absolute"
            raise ValueError(message)

        repository_root = Path(abspath(self.repository_root))
        worktree_root = Path(abspath(self.worktree_root))
        if repository_root == worktree_root:
            message = "repository and worktree paths must be distinct"
            raise ValueError(message)

        if not self.base_revision.strip():
            message = "base revision must not be empty"
            raise ValueError(message)

        object.__setattr__(self, "repository_root", repository_root)
        object.__setattr__(self, "worktree_root", worktree_root)


@dataclass(frozen=True, slots=True)
class ApprovedSpecification:
    """Immutable snapshot of the specification approved for execution."""

    identifier: str
    revision: str
    approval_reference: str
    content: str = field(repr=False)

    def __post_init__(self) -> None:
        """Require explicit identity, approval, and executable content."""
        required_values = (self.identifier, self.revision, self.approval_reference, self.content)
        if any(not value.strip() for value in required_values):
            message = "approved specification fields must not be empty"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ExecutionConstraints:
    """Provider-neutral security and resource boundaries for an execution."""

    writable_paths: tuple[Path, ...]
    network_access: bool = False
    max_changed_files: int = 100
    max_output_bytes: int = 1_000_000

    def __post_init__(self) -> None:
        """Ensure writable paths cannot escape the selected worktree."""
        writable_paths = tuple(self.writable_paths)
        if not writable_paths:
            message = "at least one writable path is required"
            raise ValueError(message)
        if any(path.is_absolute() or ".." in path.parts for path in writable_paths):
            message = "writable paths must be relative and must not traverse parents"
            raise ValueError(message)
        resource_limits = (self.max_changed_files, self.max_output_bytes)
        if any(isinstance(limit, bool) or not isinstance(limit, int) or limit < 1 for limit in resource_limits):
            message = "execution resource limits must be positive integers"
            raise ValueError(message)

        object.__setattr__(self, "writable_paths", writable_paths)


@dataclass(frozen=True, slots=True)
class ToolPermission:
    """Opaque tool capability granted to an executor, without command arguments."""

    identifier: str

    def __post_init__(self) -> None:
        """Restrict permissions to auditable tool identifiers."""
        if fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}", self.identifier) is None:
            message = "tool identifier contains unsupported characters"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class CodingExecutionRequest:
    """Complete, approved input for one isolated coding execution."""

    execution_id: str
    repository: RepositoryContext
    specification: ApprovedSpecification
    constraints: ExecutionConstraints
    allowed_tools: tuple[ToolPermission, ...]
    timeout_seconds: float

    def __post_init__(self) -> None:
        """Reject ambiguous execution identity, timeout, or tool grants."""
        if not self.execution_id.strip():
            message = "execution ID must not be empty"
            raise ValueError(message)
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
        ):
            message = "execution timeout must be positive and finite"
            raise ValueError(message)
        allowed_tools = tuple(self.allowed_tools)
        tool_ids = tuple(tool.identifier for tool in allowed_tools)
        if len(tool_ids) != len(set(tool_ids)):
            message = "allowed tool permissions must be unique"
            raise ValueError(message)

        object.__setattr__(self, "allowed_tools", allowed_tools)


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    """Ordered progress notification emitted by an executor."""

    sequence: int
    kind: ExecutionEventKind
    message: str = field(repr=False)

    def __post_init__(self) -> None:
        """Require non-negative ordering and a useful safe message."""
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 0:
            message = "event sequence must be a non-negative integer"
            raise ValueError(message)
        if not self.message.strip():
            message = "event message must not be empty"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ExecutionArtifact:
    """Metadata reference to an artifact retained inside the worktree."""

    name: str
    relative_path: Path
    media_type: str
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        """Reject artifact metadata that could reference external paths."""
        if not self.name.strip() or not self.media_type.strip():
            message = "artifact name and media type must not be empty"
            raise ValueError(message)
        if self.relative_path.is_absolute() or ".." in self.relative_path.parts:
            message = "artifact path must remain relative to the worktree"
            raise ValueError(message)
        if self.size_bytes < 0:
            message = "artifact size must not be negative"
            raise ValueError(message)
        if fullmatch(r"[0-9a-f]{64}", self.sha256) is None:
            message = "artifact SHA-256 must be lowercase hexadecimal"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ExecutionFailure:
    """Sanitized, portable failure information safe for orchestration."""

    kind: ExecutionFailureKind
    code: str
    safe_message: str = field(repr=False)
    retryable: bool = False

    def __post_init__(self) -> None:
        """Require a stable machine code and non-empty operator message."""
        if fullmatch(r"[A-Z][A-Z0-9_]{0,63}", self.code) is None:
            message = "failure code must be an uppercase machine identifier"
            raise ValueError(message)
        if not self.safe_message.strip():
            message = "failure message must not be empty"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class CodingExecutionResult:
    """Terminal outcome of one coding execution."""

    execution_id: str
    status: ExecutionStatus
    summary: str = field(repr=False)
    artifacts: tuple[ExecutionArtifact, ...] = ()
    failure: ExecutionFailure | None = None

    def __post_init__(self) -> None:
        """Keep status and failure classification internally consistent."""
        if not self.execution_id.strip() or not self.summary.strip():
            message = "result identity and summary must not be empty"
            raise ValueError(message)
        if self.status is ExecutionStatus.COMPLETED:
            if self.failure is not None:
                message = "completed results must not include a failure"
                raise ValueError(message)
            return
        if self.failure is None:
            message = "non-completed results must include a classified failure"
            raise ValueError(message)

        allowed_failure_kinds = {
            ExecutionStatus.BLOCKED: {ExecutionFailureKind.BLOCKED, ExecutionFailureKind.POLICY},
            ExecutionStatus.CANCELLED: {ExecutionFailureKind.CANCELLED},
            ExecutionStatus.TIMED_OUT: {ExecutionFailureKind.TIMEOUT},
            ExecutionStatus.FAILED: {
                ExecutionFailureKind.INTERNAL,
                ExecutionFailureKind.POLICY,
                ExecutionFailureKind.PROVIDER,
            },
        }
        if self.failure.kind not in allowed_failure_kinds[self.status]:
            message = "result status does not match its failure classification"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ExecutorCapabilities:
    """Provider-neutral metadata used to select a compatible executor."""

    executor_id: str
    features: frozenset[ExecutorFeature]
    supported_tools: frozenset[str]
    max_timeout_seconds: float

    def __post_init__(self) -> None:
        """Validate advertised capability identifiers and resource limits."""
        if not self.executor_id.strip():
            message = "executor ID must not be empty"
            raise ValueError(message)
        if any(fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}", tool) is None for tool in self.supported_tools):
            message = "supported tool identifier contains unsupported characters"
            raise ValueError(message)
        if self.max_timeout_seconds <= 0:
            message = "maximum timeout must be positive"
            raise ValueError(message)


type EventCallback = Callable[[ExecutionEvent], Awaitable[None]]
type ArtifactCallback = Callable[[ExecutionArtifact], Awaitable[None]]


class CancellationSignal(Protocol):
    """Cooperative cancellation boundary supplied by orchestration."""

    @property
    def cancelled(self) -> bool:
        """Return whether cancellation has been requested."""
        ...

    async def wait(self) -> None:
        """Wait until cancellation is requested."""
        ...


class CodingExecutor(Protocol):
    """Port implemented by Codex or any future coding provider adapter."""

    @property
    def capabilities(self) -> ExecutorCapabilities:
        """Describe executor features without exposing provider internals."""
        ...

    async def execute(
        self,
        request: CodingExecutionRequest,
        *,
        on_event: EventCallback,
        on_artifact: ArtifactCallback,
        cancellation: CancellationSignal,
    ) -> CodingExecutionResult:
        """Execute approved work while streaming observable progress."""
        ...
