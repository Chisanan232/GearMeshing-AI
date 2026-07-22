"""Provider-neutral contract for work-management integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Final, Never, final
from urllib.parse import urlsplit

_MAX_IDENTIFIER_LENGTH: Final = 255
_MAX_TEXT_LENGTH: Final = 100_000
_SENSITIVE_METADATA_KEYS: Final = frozenset(
    {
        "access_token",
        "api_key",
        "api_token",
        "authorization",
        "client_secret",
        "password",
        "private_key",
        "refresh_token",
        "secret",
    }
)


class WorkManagementContractError(ValueError):
    """Base error raised before unsafe data reaches a provider adapter."""


class UnsupportedProviderFeatureError(WorkManagementContractError):
    """Raised when an adapter does not declare a requested capability."""

    def __init__(self, provider_name: str, capability: ProviderCapability) -> None:
        super().__init__(f"Provider {provider_name!r} does not support {capability.value!r}.")
        self.provider_name = provider_name
        self.capability = capability


class ProviderCapability(StrEnum):
    """Operations that a work-management provider may support."""

    RETRIEVE_WORK_ITEM = "retrieve_work_item"
    VALIDATE_READINESS = "validate_readiness"
    PUBLISH_PROGRESS = "publish_progress"
    PUBLISH_BLOCKER = "publish_blocker"
    PUBLISH_COMPLETION = "publish_completion"
    PUBLISH_ARTIFACT = "publish_artifact"


class UpdateKind(StrEnum):
    """Provider-neutral update categories."""

    PROGRESS = "progress"
    BLOCKER = "blocker"
    COMPLETION = "completion"
    ARTIFACT = "artifact"


def _invalid(message: str) -> Never:
    raise WorkManagementContractError(message)


def _normalize_text(value: str, field_name: str, *, max_length: int = _MAX_TEXT_LENGTH) -> str:
    if not isinstance(value, str):
        _invalid(f"{field_name} must be a string.")
    normalized = value.strip()
    if not normalized:
        _invalid(f"{field_name} must not be empty.")
    if len(normalized) > max_length:
        _invalid(f"{field_name} exceeds its maximum length.")
    if any(ord(character) < 32 and character not in "\n\t" for character in normalized):
        _invalid(f"{field_name} contains control characters.")
    return normalized


def _normalize_identifier(value: str, field_name: str = "external_key") -> str:
    normalized = _normalize_text(value, field_name, max_length=_MAX_IDENTIFIER_LENGTH)
    if any(character.isspace() for character in normalized):
        _invalid(f"{field_name} must not contain whitespace.")
    return normalized


def _normalize_url(value: str, field_name: str, *, schemes: frozenset[str]) -> str:
    normalized = _normalize_text(value, field_name, max_length=2_048)
    parsed = urlsplit(normalized)
    if parsed.scheme.lower() not in schemes:
        _invalid(f"{field_name} uses an unsupported URL scheme.")
    if parsed.scheme.lower() == "https" and not parsed.hostname:
        _invalid(f"{field_name} must include a host.")
    if parsed.username is not None or parsed.password is not None:
        _invalid(f"{field_name} must not contain credentials.")
    return normalized


def _freeze_metadata(value: Any, *, path: str = "metadata") -> Any:
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                _invalid(f"{path} keys must be strings.")
            normalized_key = _normalize_text(key, f"{path} key", max_length=128)
            if normalized_key.lower() in _SENSITIVE_METADATA_KEYS:
                _invalid(f"{path} contains a sensitive key: {normalized_key!r}.")
            frozen[normalized_key] = _freeze_metadata(item, path=f"{path}.{normalized_key}")
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_metadata(item, path=path) for item in value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    _invalid(f"{path} contains an unsupported value type.")


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    """Identity and supported operations declared by an adapter."""

    provider_name: str
    supported: frozenset[ProviderCapability]

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_name", _normalize_identifier(self.provider_name, "provider_name"))
        object.__setattr__(self, "supported", frozenset(self.supported))
        if not all(isinstance(capability, ProviderCapability) for capability in self.supported):
            _invalid("supported must contain ProviderCapability values.")

    def require(self, capability: ProviderCapability) -> None:
        """Raise explicitly when the provider does not support an operation."""
        if capability not in self.supported:
            raise UnsupportedProviderFeatureError(self.provider_name, capability)


@dataclass(frozen=True, slots=True)
class WorkRepository:
    """Normalized repository coordinates for an approved work item."""

    url: str
    default_branch: str = "main"

    def __post_init__(self) -> None:
        object.__setattr__(self, "url", _normalize_url(self.url, "repository.url", schemes=frozenset({"https"})))
        object.__setattr__(
            self,
            "default_branch",
            _normalize_identifier(self.default_branch, "repository.default_branch"),
        )


@dataclass(frozen=True, slots=True)
class WorkItem:
    """Approved work specification independent of any provider payload."""

    external_key: str
    title: str
    specification: str
    acceptance_criteria: tuple[str, ...]
    repository: WorkRepository
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "external_key", _normalize_identifier(self.external_key))
        object.__setattr__(self, "title", _normalize_text(self.title, "title", max_length=1_000))
        object.__setattr__(self, "specification", _normalize_text(self.specification, "specification"))
        criteria = tuple(
            _normalize_text(criterion, "acceptance_criteria item", max_length=10_000)
            for criterion in self.acceptance_criteria
        )
        if not criteria:
            _invalid("acceptance_criteria must not be empty.")
        object.__setattr__(self, "acceptance_criteria", criteria)
        if not isinstance(self.repository, WorkRepository):
            _invalid("repository must be a WorkRepository.")
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class ReadinessProblem:
    """A provider-neutral reason that work cannot start."""

    code: str
    message: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _normalize_identifier(self.code, "readiness.code"))
        object.__setattr__(self, "message", _normalize_text(self.message, "readiness.message", max_length=10_000))


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    """Result of validating whether an approved work item is executable."""

    ready: bool
    problems: tuple[ReadinessProblem, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "problems", tuple(self.problems))
        if self.ready and self.problems:
            _invalid("A ready result must not contain problems.")
        if not self.ready and not self.problems:
            _invalid("A non-ready result must contain at least one problem.")


@dataclass(frozen=True, slots=True)
class ProgressUpdate:
    """Progress information to publish for a work item."""

    message: str
    percent_complete: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "message", _normalize_text(self.message, "progress.message", max_length=10_000))
        if self.percent_complete is not None and not 0 <= self.percent_complete <= 100:
            _invalid("percent_complete must be between 0 and 100.")
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class BlockerUpdate:
    """A blocker to publish for a work item."""

    reason: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason", _normalize_text(self.reason, "blocker.reason", max_length=10_000))
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class CompletionUpdate:
    """Completion evidence to publish for a work item."""

    summary: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", _normalize_text(self.summary, "completion.summary", max_length=10_000))
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class ArtifactUpdate:
    """A reviewable artifact produced while executing a work item."""

    name: str
    url: str
    media_type: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _normalize_text(self.name, "artifact.name", max_length=1_000))
        object.__setattr__(self, "url", _normalize_url(self.url, "artifact.url", schemes=frozenset({"https"})))
        object.__setattr__(self, "media_type", _normalize_text(self.media_type, "artifact.media_type", max_length=255))
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class UpdateReceipt:
    """Provider acknowledgement of a published update."""

    external_key: str
    kind: UpdateKind
    provider_reference: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "external_key", _normalize_identifier(self.external_key))
        object.__setattr__(
            self,
            "provider_reference",
            _normalize_identifier(self.provider_reference, "provider_reference"),
        )


class WorkManagementProvider(ABC):
    """Guarded application port implemented by Jira, ClickUp, or GitHub adapters."""

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Declare the provider identity and supported operations."""

    @final
    async def retrieve_work_item(self, external_key: str) -> WorkItem:
        """Retrieve one approved work item by its provider-neutral external key."""
        self.capabilities.require(ProviderCapability.RETRIEVE_WORK_ITEM)
        return await self._retrieve_work_item(_normalize_identifier(external_key))

    @abstractmethod
    async def _retrieve_work_item(self, external_key: str) -> WorkItem:
        """Perform provider-specific work-item retrieval."""

    @final
    async def validate_readiness(self, work_item: WorkItem) -> ReadinessResult:
        """Validate whether a normalized work item is ready for execution."""
        self.capabilities.require(ProviderCapability.VALIDATE_READINESS)
        return await self._validate_readiness(work_item)

    async def _validate_readiness(self, work_item: WorkItem) -> ReadinessResult:
        raise UnsupportedProviderFeatureError(self.capabilities.provider_name, ProviderCapability.VALIDATE_READINESS)

    @final
    async def publish_progress(self, external_key: str, update: ProgressUpdate) -> UpdateReceipt:
        """Publish a progress update."""
        self.capabilities.require(ProviderCapability.PUBLISH_PROGRESS)
        return await self._publish_progress(_normalize_identifier(external_key), update)

    async def _publish_progress(self, external_key: str, update: ProgressUpdate) -> UpdateReceipt:
        raise UnsupportedProviderFeatureError(self.capabilities.provider_name, ProviderCapability.PUBLISH_PROGRESS)

    @final
    async def publish_blocker(self, external_key: str, update: BlockerUpdate) -> UpdateReceipt:
        """Publish a blocker update."""
        self.capabilities.require(ProviderCapability.PUBLISH_BLOCKER)
        return await self._publish_blocker(_normalize_identifier(external_key), update)

    async def _publish_blocker(self, external_key: str, update: BlockerUpdate) -> UpdateReceipt:
        raise UnsupportedProviderFeatureError(self.capabilities.provider_name, ProviderCapability.PUBLISH_BLOCKER)

    @final
    async def publish_completion(self, external_key: str, update: CompletionUpdate) -> UpdateReceipt:
        """Publish a completion update."""
        self.capabilities.require(ProviderCapability.PUBLISH_COMPLETION)
        return await self._publish_completion(_normalize_identifier(external_key), update)

    async def _publish_completion(self, external_key: str, update: CompletionUpdate) -> UpdateReceipt:
        raise UnsupportedProviderFeatureError(self.capabilities.provider_name, ProviderCapability.PUBLISH_COMPLETION)

    @final
    async def publish_artifact(self, external_key: str, update: ArtifactUpdate) -> UpdateReceipt:
        """Publish a reviewable artifact."""
        self.capabilities.require(ProviderCapability.PUBLISH_ARTIFACT)
        return await self._publish_artifact(_normalize_identifier(external_key), update)

    async def _publish_artifact(self, external_key: str, update: ArtifactUpdate) -> UpdateReceipt:
        raise UnsupportedProviderFeatureError(self.capabilities.provider_name, ProviderCapability.PUBLISH_ARTIFACT)
