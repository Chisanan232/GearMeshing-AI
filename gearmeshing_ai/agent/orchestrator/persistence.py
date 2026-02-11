"""
Persistence manager for workflow state and event storage.

Handles saving and retrieving workflow state, events, approvals, and checkpoints
from various storage backends (database, redis, filesystem).
"""

from __future__ import annotations

from typing import Any, Optional

from .models import (
    ApprovalDecisionRecord,
    ApprovalRequest,
    WorkflowCheckpoint,
    WorkflowEvent,
)
from .backends.base import PersistenceBackend
from .backends.local import LocalPersistenceBackend


class PersistenceManager:
    """
    Manages persistence of workflow state, events, and approvals.
    
    Supports multiple backends:
    - local: In-memory storage (default, for testing/development)
    - database: SQL database (TODO: not implemented yet)
    - redis: Redis cache (TODO: not implemented yet)
    - filesystem: Local filesystem (TODO: not implemented yet)
    """

    def __init__(self, backend: str = "local", **backend_kwargs) -> None:
        """
        Initialize the persistence manager.
        
        Args:
            backend: Storage backend type:
                     - "local": In-memory storage (default, for testing/development)
                     - "database": SQL database (TODO: not implemented yet)
                     - "redis": Redis cache (TODO: not implemented yet)
            **backend_kwargs: Additional arguments for specific backends
        """
        self.backend_type = backend
        self._backend = self._create_backend(backend, **backend_kwargs)

    def _create_backend(self, backend: str, **kwargs) -> PersistenceBackend:
        """
        Create a persistence backend instance.
        
        Args:
            backend: Backend type
            **kwargs: Backend-specific arguments
        
        Returns:
            PersistenceBackend instance
        """
        if backend == "local":
            return LocalPersistenceBackend()
        elif backend == "database":
            # TODO: Implement database backend
            from .backends.database import DatabasePersistenceBackend
            connection_string = kwargs.get("connection_string", "sqlite:///orchestrator.db")
            return DatabasePersistenceBackend(connection_string)
        elif backend == "redis":
            # TODO: Implement redis backend
            from .backends.redis import RedisPersistenceBackend
            host = kwargs.get("host", "localhost")
            port = kwargs.get("port", 6379)
            db = kwargs.get("db", 0)
            return RedisPersistenceBackend(host, port, db)
        else:
            raise ValueError(f"Unknown backend type: {backend}")

    # Delegate to backend
    async def save_event(self, event: WorkflowEvent) -> None:
        """Save a workflow event."""
        # Events are not yet stored in backend, keep in-memory for now
        pass

    async def get_events(self, run_id: str) -> list[WorkflowEvent]:
        """Get all events for a workflow."""
        # Events are not yet stored in backend
        return []

    async def save_approval_request(self, run_id: str, request: ApprovalRequest) -> None:
        """Save an approval request."""
        await self._backend.save_approval_request(run_id, request)

    async def get_approval_request(self, run_id: str) -> ApprovalRequest | None:
        """Get the approval request for a workflow."""
        # TODO: Implement in backend
        return None

    async def save_approval_decision(self, decision: ApprovalDecisionRecord) -> None:
        """Save an approval decision."""
        await self._backend.save_approval_decision(decision)

    async def get_approval_history_by_run(self, run_id: str) -> list[ApprovalDecisionRecord]:
        """Get all approval decisions for a workflow."""
        # TODO: Implement in backend to return ApprovalDecisionRecord objects
        return []

    async def save_checkpoint(self, checkpoint: WorkflowCheckpoint) -> None:
        """Save a workflow checkpoint."""
        # Checkpoints are handled by workflow state persistence
        pass

    async def get_checkpoint(self, run_id: str) -> WorkflowCheckpoint | None:
        """Get the latest checkpoint for a workflow."""
        # Checkpoints are handled by workflow state persistence
        return None

    async def delete_checkpoint(self, run_id: str) -> None:
        """Delete checkpoints for a workflow."""
        # Checkpoints are handled by workflow state persistence
        pass

    async def clear(self) -> None:
        """Clear all persisted data (for testing)."""
        await self._backend.clear()

    async def save_workflow_state(self, run_id: str, state: Any) -> None:
        """Save workflow state for resumption."""
        await self._backend.save_workflow_state(run_id, state)

    async def load_workflow_state(self, run_id: str) -> Optional[Any]:
        """Load workflow state for resumption."""
        return await self._backend.load_workflow_state(run_id)

    async def delete_workflow_state(self, run_id: str) -> None:
        """Delete workflow state after completion."""
        await self._backend.delete_workflow_state(run_id)

    async def save_cancellation(self, cancellation: dict[str, Any]) -> None:
        """Save workflow cancellation record."""
        await self._backend.save_cancellation(cancellation)

    async def get_workflow_history(
        self,
        user_id: Optional[str] = None,
        agent_role: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get workflow execution history with filtering."""
        return await self._backend.get_workflow_history(
            user_id=user_id,
            agent_role=agent_role,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def get_approval_history(
        self,
        run_id: Optional[str] = None,
        approver_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get approval decision history with filtering."""
        return await self._backend.get_approval_history(
            run_id=run_id,
            approver_id=approver_id,
            status=status,
            limit=limit,
            offset=offset,
        )
