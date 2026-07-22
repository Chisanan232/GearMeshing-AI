"""Contract tests for provider-neutral work-management adapters."""

from __future__ import annotations

import operator
from dataclasses import FrozenInstanceError, fields
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
    UnsupportedProviderFeatureError,
    UpdateKind,
    UpdateReceipt,
    WorkItem,
    WorkManagementContractError,
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


def test_work_item_data_is_deeply_immutable() -> None:
    item = make_work_item()

    with pytest.raises(FrozenInstanceError):
        item.title = "Changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        operator.setitem(item.metadata, "priority", "low")
    with pytest.raises(TypeError):
        operator.setitem(item.metadata["labels"], 0, "changed")


@pytest.mark.asyncio
async def test_returns_a_provider_neutral_readiness_result() -> None:
    provider = RecordingProvider()
    item = make_work_item()

    result = await provider.validate_readiness(item)

    assert result == ReadinessResult(ready=True)
    assert provider.calls == [("readiness", "WORK-42", None)]


@pytest.mark.asyncio
async def test_publishes_progress_through_the_normalized_contract() -> None:
    provider = RecordingProvider()
    update = ProgressUpdate("Implementation started", percent_complete=25)

    receipt = await provider.publish_progress("WORK-42", update)

    assert receipt == UpdateReceipt("WORK-42", UpdateKind.PROGRESS, "progress-1")
    assert provider.calls == [("progress", "WORK-42", update)]


@pytest.mark.asyncio
async def test_publishes_blockers_through_the_normalized_contract() -> None:
    provider = RecordingProvider()
    update = BlockerUpdate("Approval is required")

    receipt = await provider.publish_blocker("WORK-42", update)

    assert receipt == UpdateReceipt("WORK-42", UpdateKind.BLOCKER, "blocker-1")
    assert provider.calls == [("blocker", "WORK-42", update)]


@pytest.mark.asyncio
async def test_publishes_completion_through_the_normalized_contract() -> None:
    provider = RecordingProvider()
    update = CompletionUpdate("All acceptance criteria passed")

    receipt = await provider.publish_completion("WORK-42", update)

    assert receipt == UpdateReceipt("WORK-42", UpdateKind.COMPLETION, "completion-1")
    assert provider.calls == [("completion", "WORK-42", update)]


@pytest.mark.asyncio
async def test_publishes_artifacts_through_the_normalized_contract() -> None:
    provider = RecordingProvider()
    update = ArtifactUpdate("Draft pull request", "https://github.com/example/project/pull/1", "text/html")

    receipt = await provider.publish_artifact("WORK-42", update)

    assert receipt == UpdateReceipt("WORK-42", UpdateKind.ARTIFACT, "artifact-1")
    assert provider.calls == [("artifact", "WORK-42", update)]


@pytest.mark.asyncio
async def test_unsupported_provider_features_fail_explicitly() -> None:
    provider = RecordingProvider(frozenset({ProviderCapability.RETRIEVE_WORK_ITEM}))

    with pytest.raises(UnsupportedProviderFeatureError) as error:
        await provider.publish_progress("WORK-42", ProgressUpdate("Started"))

    assert error.value.capability is ProviderCapability.PUBLISH_PROGRESS
    assert provider.calls == []


def test_rejects_unsafe_identifiers_urls_and_metadata() -> None:
    with pytest.raises(WorkManagementContractError):
        WorkRepository("http://github.com/example/project")
    with pytest.raises(WorkManagementContractError):
        WorkItem(
            external_key="WORK 42",
            title="Title",
            specification="Specification",
            acceptance_criteria=("Criterion",),
            repository=WorkRepository("https://github.com/example/project"),
        )

    secret = "not-for-error-output"
    with pytest.raises(WorkManagementContractError) as error:
        ProgressUpdate("Started", metadata={"api_token": secret})
    assert secret not in str(error.value)


def test_contract_has_no_jira_specific_fields_or_provider_identity() -> None:
    public_names = {
        *(field.name for field in fields(WorkItem)),
        *(field.name for field in fields(ProgressUpdate)),
        *(name for name in dir(WorkManagementProvider) if not name.startswith("_")),
    }

    assert not any("jira" in name.lower() for name in public_names)
    assert ProviderCapabilities("clickup", ALL_CAPABILITIES).provider_name == "clickup"
    assert ProviderCapabilities("github-issues", ALL_CAPABILITIES).provider_name == "github-issues"
