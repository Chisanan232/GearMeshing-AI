"""Unit tests for the lightweight workflow runner."""

from dataclasses import replace

import pytest

from gearmeshing_ai.application.workflow_runner import (
    WORKFLOW_STAGE_ORDER,
    StageContext,
    StageFailure,
    WorkflowActions,
    WorkflowCheckpoint,
    WorkflowFailureKind,
    WorkflowRunner,
    WorkflowStage,
    WorkflowStageError,
)
from gearmeshing_ai.domain.work_run import (
    ArtifactReference,
    EventReference,
    WorkRun,
    WorkRunCorrelation,
    WorkRunState,
)


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


def test_failed_checkpoint_enforces_stage_and_terminal_state() -> None:
    completed_stages = (WorkflowStage.INGEST, WorkflowStage.EXECUTE)
    failed_work_run = replace(make_work_run(), state=WorkRunState.FAILED)
    failure = StageFailure(
        stage=WorkflowStage.VERIFY,
        kind=WorkflowFailureKind.POLICY,
        reason_code="approval_missing",
    )

    checkpoint = WorkflowCheckpoint(
        work_run=failed_work_run,
        completed_stages=completed_stages,
        failure=failure,
    )

    assert checkpoint.failure is failure
    with pytest.raises(ValueError, match="immediately follow"):
        WorkflowCheckpoint(
            work_run=failed_work_run,
            completed_stages=completed_stages,
            failure=replace(failure, stage=WorkflowStage.REMEDIATE),
        )
    with pytest.raises(ValueError, match="invalid terminal"):
        WorkflowCheckpoint(
            work_run=replace(failed_work_run, state=WorkRunState.BLOCKED),
            completed_stages=completed_stages,
            failure=failure,
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


def test_stage_action_cannot_change_stable_correlation() -> None:
    def alter_branch(work_run: WorkRun, context: StageContext) -> WorkRun:
        del context
        correlation = replace(work_run.correlation, branch="unauthorized/branch")
        return replace(work_run, correlation=correlation)

    actions = WorkflowActions(
        ingest=alter_branch,
        execute=alter_branch,
        verify=alter_branch,
        remediate=alter_branch,
        publish=alter_branch,
        finish=alter_branch,
    )

    result = WorkflowRunner(actions).run(WorkflowCheckpoint(work_run=make_work_run()))

    assert result.completed_stages == ()
    assert result.work_run.state is WorkRunState.BLOCKED
    assert result.failure is not None
    assert result.failure.kind is WorkflowFailureKind.INTERNAL


def test_draft_pr_association_is_publish_only_and_write_once() -> None:
    first_pr = "https://github.com/Chisanan232/GearMeshing-AI/pull/13"
    replacement_pr = "https://github.com/Chisanan232/GearMeshing-AI/pull/99"

    def associate_early(work_run: WorkRun, context: StageContext) -> WorkRun:
        del context
        return work_run.associate_pull_request(first_pr)

    early_actions = WorkflowActions(
        ingest=associate_early,
        execute=associate_early,
        verify=associate_early,
        remediate=associate_early,
        publish=associate_early,
        finish=associate_early,
    )

    early_result = WorkflowRunner(early_actions).run(WorkflowCheckpoint(work_run=make_work_run()))

    assert early_result.completed_stages == ()
    assert early_result.failure is not None

    def overwrite_at_publish(work_run: WorkRun, context: StageContext) -> WorkRun:
        if context.stage is WorkflowStage.PUBLISH:
            return work_run.associate_pull_request(replacement_pr)
        return work_run

    overwrite_actions = WorkflowActions(
        ingest=overwrite_at_publish,
        execute=overwrite_at_publish,
        verify=overwrite_at_publish,
        remediate=overwrite_at_publish,
        publish=overwrite_at_publish,
        finish=overwrite_at_publish,
    )
    existing_pr_run = make_work_run().associate_pull_request(first_pr)

    overwrite_result = WorkflowRunner(overwrite_actions).run(WorkflowCheckpoint(work_run=existing_pr_run))

    assert overwrite_result.completed_stages == WORKFLOW_STAGE_ORDER[:4]
    assert overwrite_result.work_run.correlation.pull_request_url == first_pr
    assert overwrite_result.failure is not None
    assert overwrite_result.failure.stage is WorkflowStage.PUBLISH


def test_stage_action_cannot_remove_or_replace_existing_evidence() -> None:
    artifact = ArtifactReference(
        artifact_id="specification",
        kind="jira-specification",
        uri="artifact://specifications/GMAI-13",
    )
    event = EventReference(event_id="approved-13", event_type="work.approved")
    work_run = make_work_run().with_artifact_reference(artifact).with_event_reference(event)

    def remove_artifact(work_run: WorkRun, context: StageContext) -> WorkRun:
        del context
        return replace(work_run, artifact_references=())

    remove_actions = WorkflowActions(
        ingest=remove_artifact,
        execute=remove_artifact,
        verify=remove_artifact,
        remediate=remove_artifact,
        publish=remove_artifact,
        finish=remove_artifact,
    )

    removed_result = WorkflowRunner(remove_actions).run(WorkflowCheckpoint(work_run=work_run))

    assert removed_result.failure is not None
    assert removed_result.work_run.artifact_references == (artifact,)

    replacement_event = EventReference(event_id="replacement-13", event_type="work.replaced")

    def replace_event(work_run: WorkRun, context: StageContext) -> WorkRun:
        del context
        return replace(work_run, event_references=(replacement_event,))

    replace_actions = WorkflowActions(
        ingest=replace_event,
        execute=replace_event,
        verify=replace_event,
        remediate=replace_event,
        publish=replace_event,
        finish=replace_event,
    )

    replaced_result = WorkflowRunner(replace_actions).run(WorkflowCheckpoint(work_run=work_run))

    assert replaced_result.failure is not None
    assert replaced_result.work_run.event_references == (event,)
