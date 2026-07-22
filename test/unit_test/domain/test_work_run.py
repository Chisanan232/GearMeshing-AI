"""Unit tests for the WorkRun domain model."""

from gearmeshing_ai.domain.work_run import WorkRun, WorkRunCorrelation


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
