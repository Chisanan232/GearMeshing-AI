"""Provider-neutral contract for executing approved coding work."""

from dataclasses import dataclass, field
from enum import StrEnum
from os.path import abspath
from pathlib import Path
from re import fullmatch


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


@dataclass(frozen=True, slots=True)
class RepositoryContext:
    """Repository and isolated worktree selected for an execution."""

    repository_root: Path
    worktree_root: Path
    base_revision: str

    def __post_init__(self) -> None:
        """Reject ambiguous or out-of-repository execution paths."""
        if not self.repository_root.is_absolute() or not self.worktree_root.is_absolute():
            message = "repository and worktree paths must be absolute"
            raise ValueError(message)

        repository_root = Path(abspath(self.repository_root))
        worktree_root = Path(abspath(self.worktree_root))
        try:
            worktree_root.relative_to(repository_root)
        except ValueError as error:
            message = "worktree path must be contained by the repository root"
            raise ValueError(message) from error

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
        if not self.writable_paths:
            message = "at least one writable path is required"
            raise ValueError(message)
        if any(path.is_absolute() or ".." in path.parts for path in self.writable_paths):
            message = "writable paths must be relative and must not traverse parents"
            raise ValueError(message)
        if self.max_changed_files < 1 or self.max_output_bytes < 1:
            message = "execution resource limits must be positive"
            raise ValueError(message)


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
        if self.timeout_seconds <= 0:
            message = "execution timeout must be positive"
            raise ValueError(message)
        tool_ids = tuple(tool.identifier for tool in self.allowed_tools)
        if len(tool_ids) != len(set(tool_ids)):
            message = "allowed tool permissions must be unique"
            raise ValueError(message)
