"""Provider-neutral contract for executing approved coding work."""

from dataclasses import dataclass
from enum import StrEnum
from os.path import abspath
from pathlib import Path


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
