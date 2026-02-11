"""Pytest fixtures for orchestrator E2E tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from gearmeshing_ai.agent.orchestrator.approval import ApprovalHandler
from gearmeshing_ai.agent.orchestrator.engine import OrchestratorEngine
from gearmeshing_ai.agent.orchestrator.models import OrchestratorConfig
from gearmeshing_ai.agent.orchestrator.persistence import PersistenceManager


@pytest.fixture
async def persistence_manager() -> AsyncGenerator[PersistenceManager]:
    """Create a persistence manager for E2E testing."""
    manager = PersistenceManager(backend="database")
    yield manager
    await manager.clear()


@pytest.fixture
async def approval_handler(
    persistence_manager: PersistenceManager,
) -> ApprovalHandler:
    """Create an approval handler for E2E testing."""
    return ApprovalHandler(persistence_manager=persistence_manager)


@pytest.fixture
async def orchestrator_engine(
    persistence_manager: PersistenceManager,
    approval_handler: ApprovalHandler,
) -> OrchestratorEngine:
    """Create an orchestrator engine for E2E testing."""
    config = OrchestratorConfig(
        default_timeout_seconds=60,
        default_approval_timeout_seconds=30,
        enable_event_logging=True,
    )
    return OrchestratorEngine(
        config=config,
        persistence_manager=persistence_manager,
        approval_handler=approval_handler,
    )
