"""Provider-neutral contract for executing approved coding work."""

from enum import StrEnum


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
