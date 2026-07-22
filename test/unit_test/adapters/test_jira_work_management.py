"""Tests for the Jira work-management adapter."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from gearmeshing_ai.adapters.jira_errors import (
    JiraAuthorizationError,
    JiraIssueValidationError,
    JiraRateLimitError,
)
from gearmeshing_ai.adapters.jira_work_management import (
    JiraWorkManagementConfig,
    JiraWorkManagementProvider,
)
from gearmeshing_ai.application.ports.work_management import ReadinessProblem, ReadinessResult, UpdateKind
from test.unit_test.adapters.jira_work_management_fixtures import jira_issue_payload


@pytest.mark.asyncio  # type: ignore[untyped-decorator, unused-ignore]
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


@pytest.mark.asyncio  # type: ignore[untyped-decorator, unused-ignore]
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


@pytest.mark.asyncio  # type: ignore[untyped-decorator, unused-ignore]
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


@pytest.mark.asyncio  # type: ignore[untyped-decorator, unused-ignore]
async def test_inaccessible_issue_maps_to_safe_authorization_error() -> None:
    secret = "not-a-real-token"
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(403, json={"errorMessages": [secret]})),
        headers={"Authorization": f"Basic {secret}"},
    ) as client:
        provider = JiraWorkManagementProvider(
            client,
            JiraWorkManagementConfig(
                site_url="https://mock.atlassian.net",
                repository_url_field="customfield_12345",
            ),
        )
        with pytest.raises(JiraAuthorizationError) as captured:
            await provider.retrieve_work_item("GMAI-17")

    assert secret not in str(captured.value)
    assert "not permitted" in str(captured.value)


@pytest.mark.asyncio  # type: ignore[untyped-decorator, unused-ignore]
async def test_blocked_validation_is_publishable_as_jira_comment() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/rest/api/3/issue/GMAI-17/comment"
        assert b"missing_repository" in request.content
        return httpx.Response(201, json={"id": "10042"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = JiraWorkManagementProvider(
            client,
            JiraWorkManagementConfig(
                site_url="https://mock.atlassian.net",
                repository_url_field="customfield_12345",
            ),
        )
        receipt = await provider.publish_readiness(
            "GMAI-17",
            ReadinessResult(
                ready=False,
                problems=(ReadinessProblem("missing_repository", "Set the approved repository URL."),),
            ),
        )

    assert receipt.kind is UpdateKind.BLOCKER
    assert receipt.provider_reference == "10042"


@pytest.mark.asyncio  # type: ignore[untyped-decorator, unused-ignore]
async def test_issue_without_spec_ready_label_is_blocked() -> None:
    payload = jira_issue_payload(labels=["mvp-1"])

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

    assert captured.value.readiness.problems[-1].code == "not_spec_ready"
    assert "spec-ready" in captured.value.readiness.problems[-1].message


@pytest.mark.asyncio  # type: ignore[untyped-decorator, unused-ignore]
async def test_rate_limit_retries_are_bounded() -> None:
    attempts = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(429, headers={"Retry-After": "60"}, json={})

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = JiraWorkManagementProvider(
            client,
            JiraWorkManagementConfig(
                site_url="https://mock.atlassian.net",
                repository_url_field="customfield_12345",
                max_attempts=2,
                max_retry_delay_seconds=1.5,
            ),
            sleep=record_sleep,
        )
        with pytest.raises(JiraRateLimitError):
            await provider.retrieve_work_item("GMAI-17")

    assert attempts == 2
    assert delays == [1.5]


@pytest.mark.asyncio  # type: ignore[untyped-decorator, unused-ignore]
async def test_unsafe_issue_key_is_rejected_before_http_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        pytest.fail(f"Unexpected request: {request.url}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = JiraWorkManagementProvider(
            client,
            JiraWorkManagementConfig(
                site_url="https://mock.atlassian.net",
                repository_url_field="customfield_12345",
            ),
        )
        with pytest.raises(ValueError, match="canonical Jira issue key"):
            await provider.retrieve_work_item("GMAI-17/../admin")


def test_config_defensively_freezes_supported_issue_types() -> None:
    mutable_issue_types = {"Story"}

    config = JiraWorkManagementConfig(
        site_url="https://mock.atlassian.net",
        repository_url_field="customfield_12345",
        supported_issue_types=mutable_issue_types,  # type: ignore[arg-type]
    )
    mutable_issue_types.add("Epic")

    assert config.supported_issue_types == frozenset({"Story"})


@pytest.mark.parametrize(  # type: ignore[untyped-decorator, unused-ignore]
    ("field_name", "value", "message"),
    [
        ("request_timeout_seconds", float("nan"), "positive finite number"),
        ("request_timeout_seconds", float("inf"), "positive finite number"),
        ("request_timeout_seconds", True, "positive finite number"),
        ("max_retry_delay_seconds", float("-inf"), "non-negative finite number"),
        ("max_retry_delay_seconds", True, "non-negative finite number"),
        ("max_attempts", True, "integer between one and five"),
        ("max_attempts", 2.5, "integer between one and five"),
        ("max_response_bytes", True, "positive integer"),
        ("max_response_bytes", 1024.5, "positive integer"),
    ],
)
def test_config_rejects_unsafe_numeric_bounds(field_name: str, value: object, message: str) -> None:
    values: dict[str, Any] = {
        "site_url": "https://mock.atlassian.net",
        "repository_url_field": "customfield_12345",
        field_name: value,
    }

    with pytest.raises(ValueError, match=message):
        JiraWorkManagementConfig(**values)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator, unused-ignore]
    "retry_after", ["nan", "inf", "-inf"]
)
@pytest.mark.asyncio  # type: ignore[untyped-decorator, unused-ignore]
async def test_non_finite_retry_after_uses_bounded_exponential_delay(retry_after: str) -> None:
    attempts = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(429, headers={"Retry-After": retry_after}, json={})
        return httpx.Response(200, json=jira_issue_payload())

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = JiraWorkManagementProvider(
            client,
            JiraWorkManagementConfig(
                site_url="https://mock.atlassian.net",
                repository_url_field="customfield_12345",
                max_retry_delay_seconds=1.5,
            ),
            sleep=record_sleep,
        )
        work_item = await provider.retrieve_work_item("GMAI-17")

    assert work_item.external_key == "GMAI-17"
    assert delays == [1.0, 1.5]


def test_config_rejects_text_as_issue_type_collection() -> None:
    with pytest.raises(ValueError, match="must be a collection"):
        JiraWorkManagementConfig(
            site_url="https://mock.atlassian.net",
            repository_url_field="customfield_12345",
            supported_issue_types="Story",  # type: ignore[arg-type]
        )
