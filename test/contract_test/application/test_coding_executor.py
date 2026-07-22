"""Contract tests for provider-neutral coding executors."""

from pathlib import Path

import pytest

from gearmeshing_ai.application.ports.coding_executor import (
    ApprovedSpecification,
    CodingExecutionRequest,
    CodingExecutionResult,
    ExecutionArtifact,
    ExecutionConstraints,
    ExecutionEvent,
    ExecutionEventKind,
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


def test_tool_permission_rejects_command_arguments() -> None:
    """Tool grants cannot smuggle shell arguments into the contract."""
    with pytest.raises(ValueError, match="unsupported characters"):
        ToolPermission("git status --porcelain")


def test_approved_specification_repr_hides_content() -> None:
    """Approved specification content is excluded from routine diagnostics."""
    specification = build_request().specification

    assert specification.content not in repr(specification)


def test_fake_executor_exposes_provider_neutral_capabilities() -> None:
    """Orchestration can select an executor without provider-specific types."""
    capabilities = build_capabilities()
    executor = FakeCodingExecutor(capabilities=capabilities, result=build_result(ExecutionStatus.COMPLETED))

    assert executor.capabilities == capabilities


@pytest.mark.asyncio
@pytest.mark.parametrize("status", tuple(ExecutionStatus))
async def test_fake_executor_returns_every_terminal_status(status: ExecutionStatus) -> None:
    """The fake deterministically represents every terminal contract outcome."""
    request = build_request()
    expected = build_result(status)
    executor = FakeCodingExecutor(capabilities=build_capabilities(), result=expected)

    async def ignore_event(_event: object) -> None:
        return None

    async def ignore_artifact(_artifact: object) -> None:
        return None

    actual = await executor.execute(
        request,
        on_event=ignore_event,
        on_artifact=ignore_artifact,
        cancellation=FakeCancellationSignal(),
    )

    assert actual == expected


@pytest.mark.asyncio
async def test_fake_executor_streams_events_and_artifacts_in_order() -> None:
    """Callbacks receive the deterministic event and artifact script."""
    events = (
        ExecutionEvent(0, ExecutionEventKind.STARTED, "Started."),
        ExecutionEvent(1, ExecutionEventKind.FINISHED, "Finished."),
    )
    artifact = ExecutionArtifact(
        name="verification",
        relative_path=Path("reports/verification.json"),
        media_type="application/json",
        size_bytes=2,
        sha256="0" * 64,
    )
    executor = FakeCodingExecutor(
        capabilities=build_capabilities(),
        result=build_result(ExecutionStatus.COMPLETED),
        events=events,
        artifacts=(artifact,),
    )
    received_events: list[ExecutionEvent] = []
    received_artifacts: list[ExecutionArtifact] = []

    async def capture_event(event: ExecutionEvent) -> None:
        received_events.append(event)

    async def capture_artifact(item: ExecutionArtifact) -> None:
        received_artifacts.append(item)

    await executor.execute(
        build_request(),
        on_event=capture_event,
        on_artifact=capture_artifact,
        cancellation=FakeCancellationSignal(),
    )

    assert received_events == list(events)
    assert received_artifacts == [artifact]


@pytest.mark.asyncio
async def test_fake_executor_honors_cancellation_before_execution() -> None:
    """A pre-cancelled request returns the canonical cancelled result."""
    signal = FakeCancellationSignal()
    signal.cancel()
    executor = FakeCodingExecutor(
        capabilities=build_capabilities(),
        result=build_result(ExecutionStatus.COMPLETED),
    )

    async def ignore_event(_event: object) -> None:
        return None

    async def ignore_artifact(_artifact: object) -> None:
        return None

    result = await executor.execute(
        build_request(),
        on_event=ignore_event,
        on_artifact=ignore_artifact,
        cancellation=signal,
    )

    assert result.status is ExecutionStatus.CANCELLED
    assert result.failure is not None
    assert result.failure.kind is ExecutionFailureKind.CANCELLED
