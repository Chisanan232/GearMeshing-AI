"""Deterministic test double for the coding executor contract."""

from asyncio import Event

from gearmeshing_ai.application.ports.coding_executor import (
    ArtifactCallback,
    CancellationSignal,
    CodingExecutionRequest,
    CodingExecutionResult,
    CodingExecutor,
    EventCallback,
    ExecutionArtifact,
    ExecutionEvent,
    ExecutionFailure,
    ExecutionFailureKind,
    ExecutionStatus,
    ExecutorCapabilities,
)


class FakeCancellationSignal:
    """In-memory cancellation signal with deterministic state changes."""

    def __init__(self) -> None:
        self._event = Event()

    @property
    def cancelled(self) -> bool:
        """Return whether the signal has been cancelled."""
        return self._event.is_set()

    def cancel(self) -> None:
        """Request cancellation."""
        self._event.set()

    async def wait(self) -> None:
        """Wait until cancellation is requested."""
        await self._event.wait()


class FakeCodingExecutor(CodingExecutor):
    """Replay a fixed execution script without invoking external commands."""

    def __init__(
        self,
        *,
        capabilities: ExecutorCapabilities,
        result: CodingExecutionResult,
        events: tuple[ExecutionEvent, ...] = (),
        artifacts: tuple[ExecutionArtifact, ...] = (),
    ) -> None:
        self._capabilities = capabilities
        self._result = result
        self._events = tuple(events)
        self._artifacts = tuple(artifacts)
        self.requests: list[CodingExecutionRequest] = []

    @property
    def capabilities(self) -> ExecutorCapabilities:
        """Return the fixed capabilities for this test double."""
        return self._capabilities

    async def execute(
        self,
        request: CodingExecutionRequest,
        *,
        on_event: EventCallback,
        on_artifact: ArtifactCallback,
        cancellation: CancellationSignal,
    ) -> CodingExecutionResult:
        """Replay the configured event and artifact sequence."""
        self.requests.append(request)
        if cancellation.cancelled:
            return _cancelled_result(request.execution_id)
        if self._result.execution_id != request.execution_id:
            message = "scripted result must match the request execution ID"
            raise ValueError(message)

        for event in self._events:
            if cancellation.cancelled:
                return _cancelled_result(request.execution_id)
            await on_event(event)
        for artifact in self._artifacts:
            if cancellation.cancelled:
                return _cancelled_result(request.execution_id)
            await on_artifact(artifact)
        return self._result


def _cancelled_result(execution_id: str) -> CodingExecutionResult:
    """Create the canonical deterministic cancellation result."""
    return CodingExecutionResult(
        execution_id=execution_id,
        status=ExecutionStatus.CANCELLED,
        summary="Execution cancelled.",
        failure=ExecutionFailure(
            kind=ExecutionFailureKind.CANCELLED,
            code="CANCELLED",
            safe_message="Execution was cancelled by orchestration.",
        ),
    )
