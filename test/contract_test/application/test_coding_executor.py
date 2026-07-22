"""Contract tests for provider-neutral coding executors."""

from pathlib import Path
from typing import cast

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


def test_repository_context_accepts_sibling_worktree() -> None:
    """A standard sibling worktree is a valid isolated execution root."""
    context = RepositoryContext(
        repository_root=Path("/workspace/GearMeshing-AI/gearmeshing-ai"),
        worktree_root=Path("/workspace/GearMeshing-AI/.worktrees/GMAI-20"),
        base_revision="main",
    )

    assert context.worktree_root == Path("/workspace/GearMeshing-AI/.worktrees/GMAI-20")


@pytest.mark.parametrize(
    ("repository_root", "worktree_root"),
    [
        (Path("repository"), Path("/workspace/worktree")),
        (Path("/workspace/repository"), Path("worktree")),
    ],
)
def test_repository_context_rejects_relative_roots(repository_root: Path, worktree_root: Path) -> None:
    """Relative roots cannot create an ambiguous execution boundary."""
    with pytest.raises(ValueError, match="must be absolute"):
        RepositoryContext(
            repository_root=repository_root,
            worktree_root=worktree_root,
            base_revision="main",
        )


def test_repository_context_rejects_identical_normalized_roots() -> None:
    """Equivalent roots cannot blur the primary checkout and worktree."""
    with pytest.raises(ValueError, match="must be distinct"):
        RepositoryContext(
            repository_root=Path("/workspace/repository"),
            worktree_root=Path("/workspace/other/../repository"),
            base_revision="main",
        )


def test_constraints_snapshot_caller_writable_paths() -> None:
    """Caller mutation cannot expand a frozen constraint boundary."""
    caller_paths = [Path("src")]
    constraints = ExecutionConstraints(writable_paths=cast("tuple[Path, ...]", caller_paths))

    caller_paths.append(Path("secrets"))

    assert constraints.writable_paths == (Path("src"),)


def test_request_snapshots_caller_tool_permissions() -> None:
    """Caller mutation cannot expand a frozen request's tool grants."""
    template = build_request()
    caller_tools = [ToolPermission("filesystem.read")]
    request = CodingExecutionRequest(
        execution_id=template.execution_id,
        repository=template.repository,
        specification=template.specification,
        constraints=template.constraints,
        allowed_tools=cast("tuple[ToolPermission, ...]", caller_tools),
        timeout_seconds=template.timeout_seconds,
    )

    caller_tools.append(ToolPermission("filesystem.write"))

    assert request.allowed_tools == (ToolPermission("filesystem.read"),)


def test_result_snapshots_caller_artifacts() -> None:
    """Caller mutation cannot change a frozen execution result."""
    artifact = ExecutionArtifact(
        name="report",
        relative_path=Path("report.json"),
        media_type="application/json",
        size_bytes=2,
        sha256="0" * 64,
    )
    caller_artifacts = [artifact]
    result = CodingExecutionResult(
        execution_id="execution-1",
        status=ExecutionStatus.COMPLETED,
        summary="Complete.",
        artifacts=cast("tuple[ExecutionArtifact, ...]", caller_artifacts),
    )

    caller_artifacts.clear()

    assert result.artifacts == (artifact,)


def test_capabilities_snapshot_caller_collections() -> None:
    """Caller mutation cannot change frozen executor capabilities."""
    caller_features = {ExecutorFeature.EVENT_STREAMING}
    caller_tools = {"filesystem.read"}
    capabilities = ExecutorCapabilities(
        executor_id="executor",
        features=cast("frozenset[ExecutorFeature]", caller_features),
        supported_tools=cast("frozenset[str]", caller_tools),
        max_timeout_seconds=60,
    )

    caller_features.add(ExecutorFeature.CANCELLATION)
    caller_tools.add("filesystem.write")

    assert capabilities.features == frozenset({ExecutorFeature.EVENT_STREAMING})
    assert capabilities.supported_tools == frozenset({"filesystem.read"})


def test_integer_limits_reject_boolean_values() -> None:
    """Boolean values cannot masquerade as integer resource metadata."""
    with pytest.raises(ValueError, match="positive integers"):
        ExecutionConstraints(writable_paths=(Path("src"),), max_changed_files=True)

    with pytest.raises(ValueError, match="non-negative integer"):
        ExecutionEvent(sequence=False, kind=ExecutionEventKind.STARTED, message="Started.")

    with pytest.raises(ValueError, match="non-negative integer"):
        ExecutionArtifact(
            name="report",
            relative_path=Path("report.json"),
            media_type="application/json",
            size_bytes=False,
            sha256="0" * 64,
        )


@pytest.mark.parametrize("timeout", [True, float("nan"), float("inf")])
def test_timeout_limits_reject_non_finite_or_boolean_values(timeout: float) -> None:
    """Timeouts must be real, finite duration limits."""
    template = build_request()
    with pytest.raises(ValueError, match="positive and finite"):
        CodingExecutionRequest(
            execution_id=template.execution_id,
            repository=template.repository,
            specification=template.specification,
            constraints=template.constraints,
            allowed_tools=template.allowed_tools,
            timeout_seconds=timeout,
        )

    with pytest.raises(ValueError, match="positive and finite"):
        ExecutorCapabilities(
            executor_id="executor",
            features=frozenset(),
            supported_tools=frozenset(),
            max_timeout_seconds=timeout,
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


def test_result_rejects_mismatched_failure_classification() -> None:
    """Timeouts cannot be reported with a provider-failure classification."""
    failure = ExecutionFailure(
        kind=ExecutionFailureKind.PROVIDER,
        code="PROVIDER_ERROR",
        safe_message="Provider unavailable.",
    )

    with pytest.raises(ValueError, match="does not match"):
        CodingExecutionResult(
            execution_id="execution-1",
            status=ExecutionStatus.TIMED_OUT,
            summary="Execution timed out.",
            failure=failure,
        )
