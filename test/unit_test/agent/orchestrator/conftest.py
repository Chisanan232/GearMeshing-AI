"""Pytest fixtures for orchestrator unit tests."""

from __future__ import annotations

import pytest

from gearmeshing_ai.agent.orchestrator.approval import ApprovalHandler
from gearmeshing_ai.agent.orchestrator.engine import OrchestratorEngine
from gearmeshing_ai.agent.orchestrator.executor import WorkflowExecutor
from gearmeshing_ai.agent.orchestrator.models import OrchestratorConfig
from gearmeshing_ai.agent.orchestrator.persistence import PersistenceManager


@pytest.fixture
def persistence_manager() -> PersistenceManager:
    """Create a persistence manager for testing."""
    return PersistenceManager(backend="database")


@pytest.fixture
def approval_handler(
    persistence_manager: PersistenceManager,
) -> ApprovalHandler:
    """Create an approval handler for testing."""
    return ApprovalHandler(persistence_manager=persistence_manager)


@pytest.fixture
def executor() -> WorkflowExecutor:
    """Create a workflow executor for testing."""
    return WorkflowExecutor(
        max_retries=3,
        retry_delay_seconds=0.1,
        timeout_seconds=5,
    )


@pytest.fixture
def orchestrator_config() -> OrchestratorConfig:
    """Create an orchestrator config for testing."""
    return OrchestratorConfig(
        default_timeout_seconds=10,
        default_approval_timeout_seconds=5,
        enable_event_logging=True,
    )


@pytest.fixture
def orchestrator_engine(
    orchestrator_config: OrchestratorConfig,
) -> OrchestratorEngine:
    """Create an orchestrator engine for testing."""
    return OrchestratorEngine(config=orchestrator_config)
