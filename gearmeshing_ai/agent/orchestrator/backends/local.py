"""
Local (in-memory) persistence backend.

Used for testing and development. All data is stored in memory and lost on restart.
"""

from __future__ import annotations

from typing import Any, Optional

from .base import PersistenceBackend


class LocalPersistenceBackend(PersistenceBackend):
    """
    In-memory persistence backend for testing and development.
    
    All data is stored in memory and lost on process restart.
    """

    def __init__(self):
        """Initialize local persistence backend."""
        self._workflow_states: dict[str, Any] = {}
        self._approval_decisions: list[Any] = []
        self._cancellations: list[dict[str, Any]] = []
        self._approval_requests: dict[str, Any] = {}
        self._workflow_history: list[dict[str, Any]] = []

    async def save_workflow_state(self, run_id: str, state: Any) -> None:
        """Save workflow state for resumption."""
        self._workflow_states[run_id] = state

    async def load_workflow_state(self, run_id: str) -> Optional[Any]:
        """Load workflow state for resumption."""
        return self._workflow_states.get(run_id)

    async def delete_workflow_state(self, run_id: str) -> None:
        """Delete workflow state after completion."""
        if run_id in self._workflow_states:
            del self._workflow_states[run_id]

    async def save_approval_decision(self, decision: Any) -> None:
        """Save an approval decision."""
        self._approval_decisions.append(decision)

    async def get_approval_history(
        self,
        run_id: Optional[str] = None,
        approver_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get approval decision history with filtering."""
        history = []
        for decision in self._approval_decisions:
            entry = {
                "run_id": decision.run_id,
                "decision": decision.decision.value,
                "approver_id": decision.approver_id,
                "decided_at": decision.decided_at,
                "reason": decision.reason,
                "alternative_action": decision.alternative_action,
                "status": decision.decision.value,
            }
            history.append(entry)

        # Filter by run_id if provided
        if run_id:
            history = [h for h in history if h.get("run_id") == run_id]

        # Filter by approver_id if provided
        if approver_id:
            history = [h for h in history if h.get("approver_id") == approver_id]

        # Filter by status if provided
        if status:
            history = [h for h in history if h.get("status") == status]

        # Apply pagination
        return history[offset:offset + limit]

    async def save_cancellation(self, cancellation: dict[str, Any]) -> None:
        """Save workflow cancellation record."""
        self._cancellations.append(cancellation)

    async def get_workflow_history(
        self,
        user_id: Optional[str] = None,
        agent_role: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get workflow execution history with filtering."""
        history = self._workflow_history.copy()

        # Filter by user_id if provided
        if user_id:
            history = [h for h in history if h.get("user_id") == user_id]

        # Filter by agent_role if provided
        if agent_role:
            history = [h for h in history if h.get("agent_role") == agent_role]

        # Filter by status if provided
        if status:
            history = [h for h in history if h.get("status") == status]

        # Apply pagination
        return history[offset:offset + limit]

    async def save_approval_request(self, run_id: str, request: Any) -> None:
        """Save an approval request."""
        self._approval_requests[run_id] = request

    async def clear(self) -> None:
        """Clear all persisted data (for testing)."""
        self._workflow_states.clear()
        self._approval_decisions.clear()
        self._cancellations.clear()
        self._approval_requests.clear()
        self._workflow_history.clear()
