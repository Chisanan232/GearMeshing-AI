"""Base persistence backend interface.

Defines the interface that all persistence backends must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PersistenceBackend(ABC):
    """Abstract base class for persistence backends.

    All persistence backends must implement this interface.
    """

    @abstractmethod
    async def save_workflow_state(self, run_id: str, state: Any) -> None:
        """Save workflow state for resumption."""
        pass

    @abstractmethod
    async def load_workflow_state(self, run_id: str) -> Any | None:
        """Load workflow state for resumption."""
        pass

    @abstractmethod
    async def delete_workflow_state(self, run_id: str) -> None:
        """Delete workflow state after completion."""
        pass

    @abstractmethod
    async def save_approval_decision(self, decision: Any) -> None:
        """Save an approval decision."""
        pass

    @abstractmethod
    async def get_approval_history(
        self,
        run_id: str | None = None,
        approver_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get approval decision history with filtering."""
        pass

    @abstractmethod
    async def save_cancellation(self, cancellation: dict[str, Any]) -> None:
        """Save workflow cancellation record."""
        pass

    @abstractmethod
    async def get_workflow_history(
        self,
        user_id: str | None = None,
        agent_role: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get workflow execution history with filtering."""
        pass

    @abstractmethod
    async def save_approval_request(self, run_id: str, request: Any) -> None:
        """Save an approval request."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all persisted data (for testing)."""
        pass
