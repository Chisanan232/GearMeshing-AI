"""Pytest fixtures for orchestrator integration tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from gearmeshing_ai.agent.orchestrator.service import OrchestratorService
from gearmeshing_ai.agent.orchestrator.approval_workflow import ApprovalWorkflow
from gearmeshing_ai.agent.orchestrator.models import OrchestratorConfig
from gearmeshing_ai.agent.orchestrator.persistence import PersistenceManager


@pytest.fixture
async def persistence_manager() -> AsyncGenerator[PersistenceManager]:
    """Create a persistence manager for integration testing."""
    manager = PersistenceManager(backend="local")
    yield manager
    await manager.clear()


@pytest.fixture
async def orchestrator_service(
    persistence_manager: PersistenceManager,
) -> OrchestratorService:
    """Create an orchestrator service for integration testing."""
    return OrchestratorService(persistence=persistence_manager)


@pytest.fixture
async def approval_workflow(
    persistence_manager: PersistenceManager,
) -> ApprovalWorkflow:
    """Create an approval workflow for integration testing."""
    return ApprovalWorkflow(persistence=persistence_manager)


@pytest.fixture
def orchestrator_config() -> OrchestratorConfig:
    """Create an orchestrator config for integration testing."""
    return OrchestratorConfig(
        default_timeout_seconds=30,
        default_approval_timeout_seconds=10,
        enable_event_logging=True,
    )
