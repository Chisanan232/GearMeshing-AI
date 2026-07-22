"""Deterministic application runner for the governed MVP workflow."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from gearmeshing_ai.domain.work_run import WorkRun, WorkRunState

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


_STAGE_TARGET_STATES = {
    WorkflowStage.INGEST: WorkRunState.EXECUTING,
    WorkflowStage.EXECUTE: WorkRunState.VERIFYING,
    WorkflowStage.VERIFY: WorkRunState.REMEDIATING,
    WorkflowStage.REMEDIATE: WorkRunState.VERIFYING,
    WorkflowStage.PUBLISH: WorkRunState.PUBLISHING_DRAFT_PR,
    WorkflowStage.FINISH: WorkRunState.COMPLETED,
}


class WorkflowRunner:
    """Run the fixed MVP workflow sequentially with replay-safe boundaries."""

    def __init__(self, actions: WorkflowActions) -> None:
        self._actions = actions

    def run(self, checkpoint: WorkflowCheckpoint) -> WorkflowCheckpoint:
        """Run remaining stages until completion or the first failure."""
        current = checkpoint
        for stage in WORKFLOW_STAGE_ORDER:
            current = self.run_stage(current, stage)
            if current.failure is not None:
                break
        return current

    def run_stage(
        self,
        checkpoint: WorkflowCheckpoint,
        stage: WorkflowStage,
    ) -> WorkflowCheckpoint:
        """Run one stage, skipping it when its checkpoint already exists."""
        if stage in checkpoint.completed_stages or checkpoint.failure is not None:
            return checkpoint

        expected_stage = WORKFLOW_STAGE_ORDER[len(checkpoint.completed_stages)]
        if stage is not expected_stage:
            message = f"expected {expected_stage.value} stage, received {stage.value}"
            raise ValueError(message)

        work_run = checkpoint.work_run
        target_state = _STAGE_TARGET_STATES[stage]
        work_run.transition_to(target_state)
        context = StageContext(
            stage=stage,
            idempotency_key=f"{work_run.identity.run_id}:{stage.value}",
        )

        try:
            updated_work_run = self._actions.for_stage(stage)(work_run, context)
            self._validate_action_result(work_run, updated_work_run)
            transitioned_work_run = updated_work_run.transition_to(target_state)
        except WorkflowStageError as error:
            return self._failed_checkpoint(checkpoint, stage, error.kind, error.reason_code)
        except Exception:
            return self._failed_checkpoint(
                checkpoint,
                stage,
                WorkflowFailureKind.INTERNAL,
                "unexpected_error",
            )

        return WorkflowCheckpoint(
            work_run=transitioned_work_run,
            completed_stages=(*checkpoint.completed_stages, stage),
        )

    @staticmethod
    def _validate_action_result(original: WorkRun, updated: WorkRun) -> None:
        if not isinstance(updated, WorkRun):
            message = "stage action must return a WorkRun"
            raise TypeError(message)
        if updated.identity != original.identity:
            message = "stage action must preserve WorkRun identity"
            raise ValueError(message)
        if updated.state is not original.state:
            message = "stage action must not change WorkRun state"
            raise ValueError(message)

    @staticmethod
    def _failed_checkpoint(
        checkpoint: WorkflowCheckpoint,
        stage: WorkflowStage,
        kind: WorkflowFailureKind,
        reason_code: str,
    ) -> WorkflowCheckpoint:
        terminal_state = (
            WorkRunState.BLOCKED if checkpoint.work_run.state is WorkRunState.APPROVED else WorkRunState.FAILED
        )
        failed_work_run = checkpoint.work_run.transition_to(terminal_state)
        return WorkflowCheckpoint(
            work_run=failed_work_run,
            completed_stages=checkpoint.completed_stages,
            failure=StageFailure(stage=stage, kind=kind, reason_code=reason_code),
        )
