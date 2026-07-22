"""Contract tests for provider-neutral coding executors."""

from pathlib import Path

import pytest

from gearmeshing_ai.application.ports.coding_executor import (
    ApprovedSpecification,
    CodingExecutionRequest,
    CodingExecutionResult,
    ExecutionConstraints,
    ExecutionFailure,
    ExecutionFailureKind,
    ExecutionStatus,
    ExecutorCapabilities,
    ExecutorFeature,
    RepositoryContext,
    ToolPermission,
)
from test.contract_test.application.fake_coding_executor import FakeCancellationSignal, FakeCodingExecutor


def build_request() -> CodingExecutionRequest:
    """Build a valid request shared by isolated contract tests."""
    return CodingExecutionRequest(
        execution_id="execution-1",
        repository=RepositoryContext(
            repository_root=Path("/workspace/repository"),
            worktree_root=Path("/workspace/repository/.worktrees/GMAI-20"),
            base_revision="eee2f63",
        ),
        specification=ApprovedSpecification(
            identifier="GMAI-20",
            revision="1",
            approval_reference="jira:GMAI-20:approved",
            content="Implement the coding executor contract.",
        ),
        constraints=ExecutionConstraints(writable_paths=(Path("gearmeshing_ai/application/ports"),)),
        allowed_tools=(ToolPermission("filesystem.read"), ToolPermission("filesystem.write")),
        timeout_seconds=300,
    )


def build_capabilities() -> ExecutorCapabilities:
    """Build provider-neutral capabilities for the deterministic fake."""
    return ExecutorCapabilities(
        executor_id="deterministic-test-executor",
        features=frozenset(ExecutorFeature),
        supported_tools=frozenset({"filesystem.read", "filesystem.write"}),
        max_timeout_seconds=600,
    )


def build_result(status: ExecutionStatus) -> CodingExecutionResult:
    """Build a valid terminal result for each supported status."""
    failure_kinds = {
        ExecutionStatus.BLOCKED: ExecutionFailureKind.BLOCKED,
        ExecutionStatus.CANCELLED: ExecutionFailureKind.CANCELLED,
        ExecutionStatus.TIMED_OUT: ExecutionFailureKind.TIMEOUT,
        ExecutionStatus.FAILED: ExecutionFailureKind.PROVIDER,
    }
    failure = None
    if status is not ExecutionStatus.COMPLETED:
        failure = ExecutionFailure(
            kind=failure_kinds[status],
            code=status.value.upper(),
            safe_message=f"Execution reached {status.value}.",
        )
    return CodingExecutionResult(
        execution_id="execution-1",
        status=status,
        summary=f"Execution reached {status.value}.",
        failure=failure,
    )


def test_repository_context_rejects_worktree_escape() -> None:
    """A worktree outside its repository cannot be passed to an adapter."""
    with pytest.raises(ValueError, match="contained"):
        RepositoryContext(
            repository_root=Path("/workspace/repository"),
            worktree_root=Path("/workspace/other"),
            base_revision="main",
        )
