"""Contract tests for provider-neutral work-management adapters."""

from __future__ import annotations

from typing import Any

import pytest

from gearmeshing_ai.application.ports.work_management import (
    ArtifactUpdate,
    BlockerUpdate,
    CompletionUpdate,
    ProgressUpdate,
    ProviderCapabilities,
    ProviderCapability,
    ReadinessResult,
    UpdateKind,
    UpdateReceipt,
    WorkItem,
    WorkManagementProvider,
    WorkRepository,
)


ALL_CAPABILITIES = frozenset(ProviderCapability)


def make_work_item() -> WorkItem:
    """Build a normalized item shared by contract scenarios."""

    return WorkItem(
        external_key="WORK-42",
        title="  Implement guarded execution  ",
        specification="  Execute an approved specification.  ",
        acceptance_criteria=("  Emit reviewable evidence.  ",),
        repository=WorkRepository("https://github.com/example/project"),
        metadata={"priority": "high", "labels": ["mvp-1"]},
    )


class RecordingProvider(WorkManagementProvider):
    """Minimal reusable adapter used to exercise the application port."""

    def __init__(self, supported: frozenset[ProviderCapability] = ALL_CAPABILITIES) -> None:
        self._capabilities = ProviderCapabilities("recording", supported)
        self.calls: list[tuple[str, str, Any]] = []

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    async def _retrieve_work_item(self, external_key: str) -> WorkItem:
        self.calls.append(("retrieve", external_key, None))
        return make_work_item()

    async def _validate_readiness(self, work_item: WorkItem) -> ReadinessResult:
        self.calls.append(("readiness", work_item.external_key, None))
        return ReadinessResult(ready=True)

    async def _publish_progress(self, external_key: str, update: ProgressUpdate) -> UpdateReceipt:
        self.calls.append(("progress", external_key, update))
        return UpdateReceipt(external_key, UpdateKind.PROGRESS, "progress-1")

    async def _publish_blocker(self, external_key: str, update: BlockerUpdate) -> UpdateReceipt:
        self.calls.append(("blocker", external_key, update))
        return UpdateReceipt(external_key, UpdateKind.BLOCKER, "blocker-1")

    async def _publish_completion(self, external_key: str, update: CompletionUpdate) -> UpdateReceipt:
        self.calls.append(("completion", external_key, update))
        return UpdateReceipt(external_key, UpdateKind.COMPLETION, "completion-1")

    async def _publish_artifact(self, external_key: str, update: ArtifactUpdate) -> UpdateReceipt:
        self.calls.append(("artifact", external_key, update))
        return UpdateReceipt(external_key, UpdateKind.ARTIFACT, "artifact-1")


@pytest.mark.asyncio
async def test_retrieves_a_normalized_work_item_by_external_key() -> None:
    provider = RecordingProvider()

    item = await provider.retrieve_work_item("  WORK-42  ")

    assert provider.calls == [("retrieve", "WORK-42", None)]
    assert item.title == "Implement guarded execution"
    assert item.specification == "Execute an approved specification."
    assert item.acceptance_criteria == ("Emit reviewable evidence.",)
    assert item.repository == WorkRepository("https://github.com/example/project", "main")
