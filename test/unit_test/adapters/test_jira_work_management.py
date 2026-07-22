"""Tests for the Jira work-management adapter."""

from __future__ import annotations

import httpx
import pytest

from gearmeshing_ai.adapters.jira_errors import JiraIssueValidationError
from gearmeshing_ai.adapters.jira_work_management import (
    JiraWorkManagementConfig,
    JiraWorkManagementProvider,
)
from test.unit_test.adapters.jira_work_management_fixtures import jira_issue_payload


@pytest.mark.asyncio
async def test_ready_issue_is_normalized_without_inventing_requirements() -> None:
    payload = jira_issue_payload(criteria=("First approved outcome.", "Second approved outcome."))

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/api/3/issue/GMAI-17"
        assert request.url.params["fields"] == "summary,description,issuetype,labels,customfield_12345"
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = JiraWorkManagementProvider(
            client,
            JiraWorkManagementConfig(
                site_url="https://mock.atlassian.net",
                repository_url_field="customfield_12345",
            ),
        )
        work_item = await provider.retrieve_work_item("GMAI-17")
        readiness = await provider.validate_readiness(work_item)

    assert work_item.title == "Load approved Jira work item"
    assert work_item.specification.startswith("User Value\n\nDeliver only the approved behavior.")
    assert work_item.acceptance_criteria == ("First approved outcome.", "Second approved outcome.")
    assert work_item.repository.url == "https://github.com/example/gearmeshing-ai"
    assert work_item.repository.default_branch == "main"
    assert work_item.metadata["labels"] == ("mvp-1", "spec-ready")
    assert readiness.ready is True


@pytest.mark.asyncio
async def test_incomplete_issue_reports_missing_criteria_and_repository() -> None:
    payload = jira_issue_payload(criteria=(), repository_url=None)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ) as client:
        provider = JiraWorkManagementProvider(
            client,
            JiraWorkManagementConfig(
                site_url="https://mock.atlassian.net",
                repository_url_field="customfield_12345",
            ),
        )
        with pytest.raises(JiraIssueValidationError) as captured:
            await provider.retrieve_work_item("GMAI-17")

    problems = {problem.code: problem.message for problem in captured.value.readiness.problems}
    assert "missing_acceptance_criteria" in problems
    assert "no criteria will be inferred" in problems["missing_acceptance_criteria"]
    assert "missing_repository" in problems
    assert "customfield_12345" in problems["missing_repository"]


@pytest.mark.asyncio
async def test_unsupported_issue_type_is_blocked() -> None:
    payload = jira_issue_payload(issue_type="Epic")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ) as client:
        provider = JiraWorkManagementProvider(
            client,
            JiraWorkManagementConfig(
                site_url="https://mock.atlassian.net",
                repository_url_field="customfield_12345",
            ),
        )
        with pytest.raises(JiraIssueValidationError) as captured:
            await provider.retrieve_work_item("GMAI-17")

    assert captured.value.readiness.problems[0].code == "unsupported_issue_type"
    assert "Story, Task" in captured.value.readiness.problems[0].message
