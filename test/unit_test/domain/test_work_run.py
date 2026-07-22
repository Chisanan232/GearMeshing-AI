"""Unit tests for the WorkRun domain model."""

from uuid import UUID

import pytest

from gearmeshing_ai.domain.work_run import WorkRun, WorkRunCorrelation, WorkRunState


def make_work_run(*, pull_request_url: str | None = None) -> WorkRun:
    """Build a valid WorkRun for focused lifecycle tests."""
    return WorkRun(
        correlation=WorkRunCorrelation(
            jira_issue_key="GMAI-11",
            repository="https://github.com/Chisanan232/GearMeshing-AI",
            branch="mvp1/GMAI-11/workrun_state_model",
            agent_assembly_correlation_id="assembly-run-42",
            pull_request_url=pull_request_url,
        )
    )


def test_work_run_starts_approved_with_cross_system_correlation() -> None:
    work_run = make_work_run()

    assert isinstance(work_run.identity.run_id, UUID)
    assert work_run.state is WorkRunState.APPROVED
    assert work_run.correlation.jira_issue_key == "GMAI-11"
    assert work_run.correlation.repository == "https://github.com/Chisanan232/GearMeshing-AI"
    assert work_run.correlation.branch == "mvp1/GMAI-11/workrun_state_model"
    assert work_run.correlation.agent_assembly_correlation_id == "assembly-run-42"


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (WorkRunState.APPROVED, WorkRunState.EXECUTING),
        (WorkRunState.EXECUTING, WorkRunState.VERIFYING),
        (WorkRunState.VERIFYING, WorkRunState.REMEDIATING),
        (WorkRunState.REMEDIATING, WorkRunState.EXECUTING),
        (WorkRunState.REMEDIATING, WorkRunState.VERIFYING),
        (WorkRunState.VERIFYING, WorkRunState.PUBLISHING_DRAFT_PR),
        (WorkRunState.PUBLISHING_DRAFT_PR, WorkRunState.COMPLETED),
    ],
)
def test_work_run_accepts_happy_path_and_remediation_transitions(
    source: WorkRunState,
    target: WorkRunState,
) -> None:
    work_run = WorkRun(
        correlation=make_work_run(
            pull_request_url="https://github.com/Chisanan232/GearMeshing-AI/pull/42"
        ).correlation,
        state=source,
    )

    transitioned = work_run.transition_to(target)

    assert transitioned.state is target
    assert transitioned.identity == work_run.identity
    assert work_run.state is source
