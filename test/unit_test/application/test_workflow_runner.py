"""Unit tests for the lightweight workflow runner."""

from gearmeshing_ai.application.workflow_runner import (
    WORKFLOW_STAGE_ORDER,
    StageContext,
    WorkflowActions,
    WorkflowCheckpoint,
    WorkflowRunner,
    WorkflowStage,
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


def test_runner_completes_the_mocked_golden_path_in_order() -> None:
    observed_stages: list[WorkflowStage] = []

    def record_stage(work_run: WorkRun, context: StageContext) -> WorkRun:
        observed_stages.append(context.stage)
        if context.stage is WorkflowStage.PUBLISH:
            return work_run.associate_pull_request(
                "https://github.com/Chisanan232/GearMeshing-AI/pull/13"
            )
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
    assert (
        result.work_run.correlation.pull_request_url
        == "https://github.com/Chisanan232/GearMeshing-AI/pull/13"
    )
    assert result.failure is None
