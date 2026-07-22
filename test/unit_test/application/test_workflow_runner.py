"""Unit tests for the lightweight workflow runner."""

from dataclasses import replace

import pytest

from gearmeshing_ai.application.workflow_runner import (
    WORKFLOW_STAGE_ORDER,
    StageContext,
    WorkflowActions,
    WorkflowCheckpoint,
    WorkflowFailureKind,
    WorkflowRunner,
    WorkflowStage,
    WorkflowStageError,
)
from gearmeshing_ai.domain.work_run import WorkRun, WorkRunCorrelation, WorkRunState


def make_work_run() -> WorkRun:
    """Build an approved WorkRun for application runner tests."""
    return WorkRun(
        correlation=WorkRunCorrelation(
            jira_issue_key="GMAI-13",
            repository="https://github.com/Chisanan232/GearMeshing-AI",
            branch="mvp1/GMAI-13/poc_workflow_runner",
            agent_assembly_correlation_id="assembly-run-13",
        )
    )


def test_checkpoint_enforces_workrun_state_for_every_completed_prefix() -> None:
    states_after_prefix = (
        WorkRunState.APPROVED,
        WorkRunState.EXECUTING,
        WorkRunState.VERIFYING,
        WorkRunState.REMEDIATING,
        WorkRunState.VERIFYING,
        WorkRunState.PUBLISHING_DRAFT_PR,
        WorkRunState.COMPLETED,
    )

    for prefix_length, expected_state in enumerate(states_after_prefix):
        work_run = make_work_run()
        if expected_state is WorkRunState.COMPLETED:
            work_run = work_run.associate_pull_request("https://github.com/Chisanan232/GearMeshing-AI/pull/13")
        work_run = replace(work_run, state=expected_state)
        completed_stages = WORKFLOW_STAGE_ORDER[:prefix_length]

        checkpoint = WorkflowCheckpoint(
            work_run=work_run,
            completed_stages=completed_stages,
        )

        assert checkpoint.work_run.state is expected_state
        invalid_state = WorkRunState.EXECUTING if expected_state is WorkRunState.APPROVED else WorkRunState.APPROVED
        with pytest.raises(ValueError, match="does not match"):
            WorkflowCheckpoint(
                work_run=replace(work_run, state=invalid_state),
                completed_stages=completed_stages,
            )


def test_runner_completes_the_mocked_golden_path_in_order() -> None:
    observed_stages: list[WorkflowStage] = []

    def record_stage(work_run: WorkRun, context: StageContext) -> WorkRun:
        observed_stages.append(context.stage)
        if context.stage is WorkflowStage.PUBLISH:
            return work_run.associate_pull_request("https://github.com/Chisanan232/GearMeshing-AI/pull/13")
        return work_run

    actions = WorkflowActions(
        ingest=record_stage,
        execute=record_stage,
        verify=record_stage,
        remediate=record_stage,
        publish=record_stage,
        finish=record_stage,
    )

    result = WorkflowRunner(actions).run(WorkflowCheckpoint(work_run=make_work_run()))

    assert tuple(observed_stages) == WORKFLOW_STAGE_ORDER
    assert result.completed_stages == WORKFLOW_STAGE_ORDER
    assert result.work_run.state is WorkRunState.COMPLETED
    assert result.work_run.correlation.pull_request_url == "https://github.com/Chisanan232/GearMeshing-AI/pull/13"
    assert result.failure is None


def test_failed_stage_records_classification_and_stops_advancement() -> None:
    observed_stages: list[WorkflowStage] = []

    def fail_verification(work_run: WorkRun, context: StageContext) -> WorkRun:
        observed_stages.append(context.stage)
        if context.stage is WorkflowStage.VERIFY:
            raise WorkflowStageError(WorkflowFailureKind.POLICY, "approval_missing")
        return work_run

    actions = WorkflowActions(
        ingest=fail_verification,
        execute=fail_verification,
        verify=fail_verification,
        remediate=fail_verification,
        publish=fail_verification,
        finish=fail_verification,
    )

    result = WorkflowRunner(actions).run(WorkflowCheckpoint(work_run=make_work_run()))

    assert observed_stages == [
        WorkflowStage.INGEST,
        WorkflowStage.EXECUTE,
        WorkflowStage.VERIFY,
    ]
    assert result.completed_stages == (WorkflowStage.INGEST, WorkflowStage.EXECUTE)
    assert result.work_run.state is WorkRunState.FAILED
    assert result.failure is not None
    assert result.failure.stage is WorkflowStage.VERIFY
    assert result.failure.kind is WorkflowFailureKind.POLICY
    assert result.failure.reason_code == "approval_missing"


def test_rerunning_a_completed_stage_skips_its_side_effect() -> None:
    call_count = 0

    def count_call(work_run: WorkRun, context: StageContext) -> WorkRun:
        nonlocal call_count
        del context
        call_count += 1
        return work_run

    actions = WorkflowActions(
        ingest=count_call,
        execute=count_call,
        verify=count_call,
        remediate=count_call,
        publish=count_call,
        finish=count_call,
    )
    runner = WorkflowRunner(actions)
    initial = WorkflowCheckpoint(work_run=make_work_run())

    completed = runner.run_stage(initial, WorkflowStage.INGEST)
    replayed = runner.run_stage(completed, WorkflowStage.INGEST)

    assert call_count == 1
    assert replayed is completed
    assert replayed.completed_stages == (WorkflowStage.INGEST,)


def test_unexpected_failure_does_not_expose_exception_details() -> None:
    def expose_secret(work_run: WorkRun, context: StageContext) -> WorkRun:
        if context.stage is WorkflowStage.INGEST:
            sensitive_message = "token=do-not-record"
            raise RuntimeError(sensitive_message)
        return work_run

    actions = WorkflowActions(
        ingest=expose_secret,
        execute=expose_secret,
        verify=expose_secret,
        remediate=expose_secret,
        publish=expose_secret,
        finish=expose_secret,
    )

    result = WorkflowRunner(actions).run(WorkflowCheckpoint(work_run=make_work_run()))

    assert result.work_run.state is WorkRunState.BLOCKED
    assert result.failure is not None
    assert result.failure.kind is WorkflowFailureKind.INTERNAL
    assert result.failure.reason_code == "unexpected_error"
    assert "do-not-record" not in repr(result)
