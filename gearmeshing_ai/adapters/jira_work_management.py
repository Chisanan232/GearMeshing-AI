"""Jira Cloud implementation of the normalized work-management contract."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from json import JSONDecodeError, loads
from math import isfinite
from typing import Any, Final
from urllib.parse import urlsplit

import httpx

from gearmeshing_ai.adapters.jira_adf import adf_section_items, adf_to_text
from gearmeshing_ai.adapters.jira_errors import (
    JiraAuthenticationError,
    JiraAuthorizationError,
    JiraIssueNotFoundError,
    JiraIssueValidationError,
    JiraRateLimitError,
    JiraTransportError,
)
from gearmeshing_ai.application.ports.work_management import (
    BlockerUpdate,
    ProgressUpdate,
    ProviderCapabilities,
    ProviderCapability,
    ReadinessProblem,
    ReadinessResult,
    UpdateKind,
    UpdateReceipt,
    WorkItem,
    WorkManagementProvider,
    WorkRepository,
)

_ISSUE_KEY_PATTERN: Final = re.compile(r"^[A-Z][A-Z0-9_]{1,9}-[1-9][0-9]*$")
_FIELD_ID_PATTERN: Final = re.compile(r"^(?:customfield_[1-9][0-9]*|[a-z][a-zA-Z0-9_]*)$")
_SUCCESS_STATUSES: Final = frozenset({200, 201})


@dataclass(frozen=True, slots=True)
class JiraWorkManagementConfig:
    """Non-secret Jira mapping required to interpret an approved work item."""

    site_url: str
    repository_url_field: str
    repository_default_branch: str = "main"
    ready_label: str = "spec-ready"
    supported_issue_types: frozenset[str] = field(default_factory=lambda: frozenset({"Story", "Task"}))
    request_timeout_seconds: float = 10.0
    max_attempts: int = 3
    max_retry_delay_seconds: float = 2.0
    max_response_bytes: int = 1_000_000

    def __post_init__(self) -> None:
        if isinstance(self.supported_issue_types, (str, bytes)):
            message = "supported_issue_types must be a collection, not text."
            raise ValueError(message)
        try:
            supported_issue_types = frozenset(self.supported_issue_types)
        except TypeError as error:
            message = "supported_issue_types must be an iterable of strings."
            raise ValueError(message) from error
        object.__setattr__(self, "supported_issue_types", supported_issue_types)

        try:
            parsed = urlsplit(self.site_url)
            _ = parsed.port
        except (TypeError, ValueError) as error:
            message = "site_url must contain a valid host and port."
            raise ValueError(message) from error
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            message = "site_url must be an HTTPS URL without credentials."
            raise ValueError(message)
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            message = "site_url must not contain a path, query, or fragment."
            raise ValueError(message)
        if not _FIELD_ID_PATTERN.fullmatch(self.repository_url_field):
            message = "repository_url_field must be an explicit Jira field ID."
            raise ValueError(message)
        if not self.ready_label.strip() or any(character.isspace() for character in self.ready_label):
            message = "ready_label must be a non-empty Jira label."
            raise ValueError(message)
        if not self.supported_issue_types or any(
            not isinstance(value, str) or not value.strip() for value in self.supported_issue_types
        ):
            message = "supported_issue_types must contain non-empty strings."
            raise ValueError(message)
        if (
            isinstance(self.request_timeout_seconds, bool)
            or not isinstance(self.request_timeout_seconds, (int, float))
            or not isfinite(self.request_timeout_seconds)
            or self.request_timeout_seconds <= 0
        ):
            message = "request_timeout_seconds must be a positive finite number."
            raise ValueError(message)
        if (
            isinstance(self.max_attempts, bool)
            or not isinstance(self.max_attempts, int)
            or not 1 <= self.max_attempts <= 5
        ):
            message = "max_attempts must be an integer between one and five."
            raise ValueError(message)
        if (
            isinstance(self.max_retry_delay_seconds, bool)
            or not isinstance(self.max_retry_delay_seconds, (int, float))
            or not isfinite(self.max_retry_delay_seconds)
            or self.max_retry_delay_seconds < 0
        ):
            message = "max_retry_delay_seconds must be a non-negative finite number."
            raise ValueError(message)
        if (
            isinstance(self.max_response_bytes, bool)
            or not isinstance(self.max_response_bytes, int)
            or self.max_response_bytes <= 0
        ):
            message = "max_response_bytes must be a positive integer."
            raise ValueError(message)
        WorkRepository("https://validation.invalid/repository", self.repository_default_branch)


class JiraWorkManagementProvider(WorkManagementProvider):
    """Load spec-ready Jira issues and publish their readiness diagnostics."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        config: JiraWorkManagementConfig,
        *,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._client = client
        self._config = config
        self._sleep = sleep
        self._capabilities = ProviderCapabilities(
            provider_name="jira-cloud",
            supported=frozenset(
                {
                    ProviderCapability.RETRIEVE_WORK_ITEM,
                    ProviderCapability.VALIDATE_READINESS,
                    ProviderCapability.PUBLISH_PROGRESS,
                    ProviderCapability.PUBLISH_BLOCKER,
                }
            ),
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    async def _request_json(self, method: str, path: str, *, json: object | None = None) -> Mapping[str, Any]:
        url = f"{self._config.site_url.rstrip('/')}{path}"
        for attempt in range(self._config.max_attempts):
            retry_delay: float | None = None
            try:
                async with self._client.stream(
                    method,
                    url,
                    json=json,
                    timeout=self._config.request_timeout_seconds,
                    follow_redirects=False,
                ) as response:
                    if response.status_code == 429 and attempt + 1 < self._config.max_attempts:
                        retry_delay = self._retry_delay(response, attempt)
                    else:
                        self._raise_for_status(response)
                        content = bytearray()
                        async for chunk in response.aiter_bytes():
                            if len(content) + len(chunk) > self._config.max_response_bytes:
                                message = "Jira returned a response larger than the configured bound."
                                raise JiraTransportError(message)
                            content.extend(chunk)
                        try:
                            payload = loads(content)
                        except (JSONDecodeError, UnicodeDecodeError, ValueError) as error:
                            message = "Jira returned an invalid JSON response."
                            raise JiraTransportError(message) from error
                        if not isinstance(payload, Mapping):
                            message = "Jira returned an unexpected JSON response shape."
                            raise JiraTransportError(message)
                        return payload
            except (httpx.TimeoutException, httpx.RequestError) as error:
                message = "Jira could not be reached within the configured request bound."
                raise JiraTransportError(message) from error

            if retry_delay is not None:
                await self._sleep(retry_delay)
                continue
        message = "Jira rate limiting exceeded the configured retry bound."
        raise JiraRateLimitError(message)

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After", "")
        try:
            requested = float(retry_after)
            if not isfinite(requested) or requested < 0:
                raise ValueError
        except (OverflowError, ValueError):
            requested = float(2**attempt)
        return min(requested, self._config.max_retry_delay_seconds)

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code in _SUCCESS_STATUSES:
            return
        if response.status_code == 401:
            message = "Jira authentication failed; verify the configured credentials."
            raise JiraAuthenticationError(message)
        if response.status_code == 403:
            message = "The Jira user is not permitted to access this work item."
            raise JiraAuthorizationError(message)
        if response.status_code == 404:
            message = "The requested Jira issue was not found or is not visible."
            raise JiraIssueNotFoundError(message)
        if response.status_code == 429:
            message = "Jira rate limiting exceeded the configured retry bound."
            raise JiraRateLimitError(message)
        message = f"Jira returned HTTP {response.status_code}."
        raise JiraTransportError(message)

    @staticmethod
    def _issue_key(external_key: str) -> str:
        if not _ISSUE_KEY_PATTERN.fullmatch(external_key):
            message = "external_key must be a canonical Jira issue key."
            raise ValueError(message)
        return external_key

    async def _retrieve_work_item(self, external_key: str) -> WorkItem:
        issue_key = self._issue_key(external_key)
        fields = ",".join(("summary", "description", "issuetype", "labels", self._config.repository_url_field))
        payload = await self._request_json("GET", f"/rest/api/3/issue/{issue_key}?fields={fields}")
        readiness = self._payload_readiness(payload)
        if not readiness.ready:
            raise JiraIssueValidationError(issue_key, readiness)

        issue_fields = payload["fields"]
        assert isinstance(issue_fields, Mapping)
        issue_type = issue_fields["issuetype"]
        assert isinstance(issue_type, Mapping)
        labels = issue_fields["labels"]
        assert isinstance(labels, Sequence)
        return WorkItem(
            external_key=issue_key,
            title=issue_fields["summary"],
            specification=adf_to_text(issue_fields["description"]),
            acceptance_criteria=adf_section_items(issue_fields["description"], "Acceptance Criteria"),
            repository=WorkRepository(
                url=issue_fields[self._config.repository_url_field],
                default_branch=self._config.repository_default_branch,
            ),
            metadata={"labels": tuple(labels), "work_item_type": issue_type["name"]},
        )

    def _payload_readiness(self, payload: Mapping[str, Any]) -> ReadinessResult:
        fields = payload.get("fields")
        if not isinstance(fields, Mapping):
            return self._blocked("invalid_payload", "Jira did not return a fields object.")

        problems: list[ReadinessProblem] = []
        issue_type = fields.get("issuetype")
        issue_type_name = issue_type.get("name") if isinstance(issue_type, Mapping) else None
        if not isinstance(issue_type_name, str) or issue_type_name not in self._config.supported_issue_types:
            problems.append(
                ReadinessProblem(
                    "unsupported_issue_type",
                    "Use one of these supported Jira issue types: "
                    f"{', '.join(sorted(self._config.supported_issue_types))}.",
                )
            )
        if not isinstance(fields.get("summary"), str) or not fields["summary"].strip():
            problems.append(ReadinessProblem("missing_summary", "Add a Jira summary before marking the issue ready."))
        description = fields.get("description")
        if not adf_to_text(description):
            problems.append(
                ReadinessProblem("missing_description", "Add a Jira description before marking the issue ready.")
            )
        if not adf_section_items(description, "Acceptance Criteria"):
            problems.append(
                ReadinessProblem(
                    "missing_acceptance_criteria",
                    "Add an Acceptance Criteria section with at least one item; no criteria will be inferred.",
                )
            )
        repository_url = fields.get(self._config.repository_url_field)
        try:
            if not isinstance(repository_url, str):
                raise ValueError
            WorkRepository(repository_url, self._config.repository_default_branch)
        except ValueError:
            problems.append(
                ReadinessProblem(
                    "missing_repository",
                    f"Set Jira field {self._config.repository_url_field!r} to a credential-free HTTPS repository URL.",
                )
            )
        labels = fields.get("labels")
        if (
            not isinstance(labels, Sequence)
            or isinstance(labels, (str, bytes))
            or self._config.ready_label not in labels
        ):
            problems.append(
                ReadinessProblem(
                    "not_spec_ready",
                    f"Add the {self._config.ready_label!r} label after the specification is approved.",
                )
            )
        return ReadinessResult(ready=not problems, problems=tuple(problems))

    @staticmethod
    def _blocked(code: str, message: str) -> ReadinessResult:
        return ReadinessResult(ready=False, problems=(ReadinessProblem(code, message),))

    async def _validate_readiness(self, work_item: WorkItem) -> ReadinessResult:
        labels = work_item.metadata.get("labels", ())
        issue_type = work_item.metadata.get("work_item_type")
        problems: list[ReadinessProblem] = []
        if issue_type not in self._config.supported_issue_types:
            problems.append(ReadinessProblem("unsupported_issue_type", "The normalized work item type is unsupported."))
        if not isinstance(labels, tuple) or self._config.ready_label not in labels:
            problems.append(
                ReadinessProblem("not_spec_ready", "The normalized work item is not approved for execution.")
            )
        return ReadinessResult(ready=not problems, problems=tuple(problems))

    async def publish_readiness(self, external_key: str, readiness: ReadinessResult) -> UpdateReceipt:
        """Publish a validation outcome through guarded provider operations."""
        if readiness.ready:
            return await self.publish_progress(external_key, ProgressUpdate("Specification validation passed."))
        message = "Specification validation blocked:\n" + "\n".join(
            f"- [{problem.code}] {problem.message}" for problem in readiness.problems
        )
        return await self.publish_blocker(external_key, BlockerUpdate(message))

    async def _publish_progress(self, external_key: str, update: ProgressUpdate) -> UpdateReceipt:
        return await self._publish_comment(external_key, update.message, UpdateKind.PROGRESS)

    async def _publish_blocker(self, external_key: str, update: BlockerUpdate) -> UpdateReceipt:
        return await self._publish_comment(external_key, update.reason, UpdateKind.BLOCKER)

    async def _publish_comment(self, external_key: str, message: str, kind: UpdateKind) -> UpdateReceipt:
        issue_key = self._issue_key(external_key)
        body = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": message}]}],
            }
        }
        payload = await self._request_json("POST", f"/rest/api/3/issue/{issue_key}/comment", json=body)
        reference = payload.get("id")
        if not isinstance(reference, str) or not reference:
            message = "Jira did not return a comment identifier."
            raise JiraTransportError(message)
        return UpdateReceipt(external_key=issue_key, kind=kind, provider_reference=reference)
