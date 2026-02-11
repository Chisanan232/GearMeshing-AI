"""
Persistence manager for workflow state and event storage.

Handles saving and retrieving workflow state, events, approvals, and checkpoints
from various storage backends (database, redis, filesystem).
"""

from __future__ import annotations

from .models import (
    ApprovalDecisionRecord,
    ApprovalRequest,
    WorkflowCheckpoint,
    WorkflowEvent,
)


class PersistenceManager:
    """
    Manages persistence of workflow state, events, and approvals.
    
    Supports multiple backends:
    - local: In-memory storage (default, for testing/development)
    - database: SQL database (TODO: not implemented yet)
    - redis: Redis cache (TODO: not implemented yet)
    - filesystem: Local filesystem (TODO: not implemented yet)
    """

    def __init__(self, backend: str = "local") -> None:
        """
        Initialize the persistence manager.
        
        Args:
            backend: Storage backend type. Currently only "local" (in-memory) is supported.
                     TODO: Implement database, redis, and filesystem backends for production use.
        """
        self.backend = backend
        # TODO: Add support for actual database persistence backends (PostgreSQL, MongoDB, etc.)
        # Currently only in-memory storage is implemented
        self._in_memory_store: dict[str, list[object]] = {
            "events": [],
            "approvals": [],
            "checkpoints": [],
            "decisions": [],
        }

    async def save_event(self, event: WorkflowEvent) -> None:
        """Save a workflow event."""
        self._in_memory_store["events"].append(event)

    async def get_events(self, run_id: str) -> list[WorkflowEvent]:
        """Get all events for a workflow."""
        return [
            e for e in self._in_memory_store["events"]
            if e.run_id == run_id
        ]

    async def save_approval_request(self, request: ApprovalRequest) -> None:
        """Save an approval request."""
        self._in_memory_store["approvals"].append(request)

    async def get_approval_request(self, run_id: str) -> ApprovalRequest | None:
        """Get the approval request for a workflow."""
        for approval in self._in_memory_store["approvals"]:
            if approval.run_id == run_id:
                return approval
        return None

    async def save_approval_decision(self, decision: ApprovalDecisionRecord) -> None:
        """Save an approval decision."""
        self._in_memory_store["decisions"].append(decision)

    async def get_approval_history(self, run_id: str) -> list[ApprovalDecisionRecord]:
        """Get all approval decisions for a workflow."""
        return [
            d for d in self._in_memory_store["decisions"]
            if d.run_id == run_id
        ]

    async def save_checkpoint(self, checkpoint: WorkflowCheckpoint) -> None:
        """Save a workflow checkpoint."""
        self._in_memory_store["checkpoints"].append(checkpoint)

    async def get_checkpoint(self, run_id: str) -> WorkflowCheckpoint | None:
        """Get the latest checkpoint for a workflow."""
        checkpoints = [
            c for c in self._in_memory_store["checkpoints"]
            if c.run_id == run_id
        ]
        return checkpoints[-1] if checkpoints else None

    async def delete_checkpoint(self, run_id: str) -> None:
        """Delete checkpoints for a workflow."""
        self._in_memory_store["checkpoints"] = [
            c for c in self._in_memory_store["checkpoints"]
            if c.run_id != run_id
        ]

    async def clear(self) -> None:
        """Clear all persisted data (for testing)."""
        self._in_memory_store = {
            "events": [],
            "approvals": [],
            "checkpoints": [],
            "decisions": [],
        }
