"""Unit tests for the lightweight workflow runner."""

from gearmeshing_ai.domain.work_run import WorkRun, WorkRunCorrelation


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
