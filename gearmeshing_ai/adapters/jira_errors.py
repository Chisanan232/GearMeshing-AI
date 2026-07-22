"""Typed failures exposed by the Jira work-management adapter."""

from __future__ import annotations

from gearmeshing_ai.application.ports.work_management import ReadinessResult


class JiraAdapterError(RuntimeError):
    """Base class for Jira adapter failures safe to surface to callers."""


class JiraAuthenticationError(JiraAdapterError):
    """Raised when Jira rejects the configured authentication."""


class JiraAuthorizationError(JiraAdapterError):
    """Raised when the authenticated user cannot perform an operation."""


class JiraIssueNotFoundError(JiraAdapterError):
    """Raised when Jira cannot find the requested issue."""


class JiraRateLimitError(JiraAdapterError):
    """Raised when bounded rate-limit retries are exhausted."""


class JiraTransportError(JiraAdapterError):
    """Raised when Jira cannot be reached or returns an unsafe response."""


class JiraIssueValidationError(JiraAdapterError):
    """Raised before normalization when a Jira issue is not executable."""

    def __init__(self, external_key: str, readiness: ReadinessResult) -> None:
        details = "; ".join(problem.message for problem in readiness.problems)
        super().__init__(f"Jira issue {external_key!r} is not ready: {details}")
        self.external_key = external_key
        self.readiness = readiness
