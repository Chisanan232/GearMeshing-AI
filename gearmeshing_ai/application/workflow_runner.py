"""Deterministic application runner for the governed MVP workflow."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from gearmeshing_ai.domain.work_run import WorkRun

_MAX_REASON_CODE_LENGTH = 64


class WorkflowStage(StrEnum):
    """Ordered stages in the lightweight proof-of-concept workflow."""

    INGEST = "ingest"
    EXECUTE = "execute"
    VERIFY = "verify"
    REMEDIATE = "remediate"
    PUBLISH = "publish"
    FINISH = "finish"


WORKFLOW_STAGE_ORDER = (
    WorkflowStage.INGEST,
    WorkflowStage.EXECUTE,
    WorkflowStage.VERIFY,
    WorkflowStage.REMEDIATE,
    WorkflowStage.PUBLISH,
    WorkflowStage.FINISH,
)


class WorkflowFailureKind(StrEnum):
    """Stable classifications suitable for policy and retry decisions."""

    INVALID_INPUT = "invalid_input"
    POLICY = "policy"
    TRANSIENT = "transient"
    INTERNAL = "internal"


def _validate_reason_code(reason_code: str) -> str:
    normalized = reason_code.strip().lower()
    if not normalized or len(normalized) > _MAX_REASON_CODE_LENGTH:
        message = f"reason_code must be between 1 and {_MAX_REASON_CODE_LENGTH} characters"
        raise ValueError(message)
    if any(not (character.isalnum() or character in {"-", "_"}) for character in normalized):
        message = "reason_code must contain only letters, numbers, hyphens, or underscores"
        raise ValueError(message)
    return normalized


class WorkflowStageError(RuntimeError):
    """A stage failure with a safe, bounded machine-readable reason."""

    def __init__(self, kind: WorkflowFailureKind, reason_code: str) -> None:
        if not isinstance(kind, WorkflowFailureKind):
            message = "kind must be a WorkflowFailureKind"
            raise TypeError(message)
        self.kind = kind
        self.reason_code = _validate_reason_code(reason_code)
        super().__init__(self.reason_code)


@dataclass(frozen=True, slots=True)
class StageContext:
    """Stable stage metadata for adapter-level idempotency keys."""

    stage: WorkflowStage
    idempotency_key: str


class StageAction(Protocol):
    """Framework-neutral boundary implemented by workflow stage adapters."""

    def __call__(self, work_run: WorkRun, context: StageContext) -> WorkRun:
        """Perform a stage and return the updated WorkRun."""
        ...


@dataclass(frozen=True, slots=True)
class WorkflowActions:
    """Explicit action dependencies for every workflow stage."""

    ingest: StageAction
    execute: StageAction
    verify: StageAction
    remediate: StageAction
    publish: StageAction
    finish: StageAction

    def for_stage(self, stage: WorkflowStage) -> StageAction:
        """Return the action configured for ``stage``."""
        actions: dict[WorkflowStage, StageAction] = {
            WorkflowStage.INGEST: self.ingest,
            WorkflowStage.EXECUTE: self.execute,
            WorkflowStage.VERIFY: self.verify,
            WorkflowStage.REMEDIATE: self.remediate,
            WorkflowStage.PUBLISH: self.publish,
            WorkflowStage.FINISH: self.finish,
        }
        return actions[stage]


@dataclass(frozen=True, slots=True)
class StageFailure:
    """Non-sensitive failure record captured at a stage boundary."""

    stage: WorkflowStage
    kind: WorkflowFailureKind
    reason_code: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_code", _validate_reason_code(self.reason_code))


@dataclass(frozen=True, slots=True)
class WorkflowCheckpoint:
    """Replayable workflow progress returned after each stage boundary."""

    work_run: WorkRun
    completed_stages: tuple[WorkflowStage, ...] = ()
    failure: StageFailure | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.work_run, WorkRun):
            message = "work_run must be a WorkRun"
            raise TypeError(message)
        expected_prefix = WORKFLOW_STAGE_ORDER[: len(self.completed_stages)]
        if self.completed_stages != expected_prefix:
            message = "completed_stages must be a canonical workflow prefix"
            raise ValueError(message)
        if self.failure is not None and not self.work_run.state.is_terminal:
            message = "a failed checkpoint must contain a terminal WorkRun"
            raise ValueError(message)
