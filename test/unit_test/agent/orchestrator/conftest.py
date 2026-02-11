"""Pytest fixtures for orchestrator unit tests."""

from __future__ import annotations

import pytest

from gearmeshing_ai.agent.orchestrator.approval_workflow import ApprovalWorkflow
from gearmeshing_ai.agent.orchestrator.models import OrchestratorConfig
from gearmeshing_ai.agent.orchestrator.persistence import PersistenceManager
from gearmeshing_ai.agent.orchestrator.service import OrchestratorService


@pytest.fixture
def persistence_manager() -> PersistenceManager:
    """Create a persistence manager for testing."""
    return PersistenceManager(backend="local")


@pytest.fixture
def orchestrator_service(
    persistence_manager: PersistenceManager,
) -> OrchestratorService:
    """Create an orchestrator service for testing."""
    return OrchestratorService(persistence=persistence_manager)


@pytest.fixture
def approval_workflow(
    persistence_manager: PersistenceManager,
) -> ApprovalWorkflow:
    """Create an approval workflow for testing."""
    return ApprovalWorkflow(persistence=persistence_manager)


@pytest.fixture
def orchestrator_config() -> OrchestratorConfig:
    """Create an orchestrator config for testing."""
    return OrchestratorConfig(
        default_timeout_seconds=10,
        default_approval_timeout_seconds=5,
        enable_event_logging=True,
    )
