"""Shared fixtures and utilities for runtime unit tests."""

from gearmeshing_ai.agent_core.runtime.models import WorkflowState


def merge_state_update(state: WorkflowState, update: dict) -> WorkflowState:
    """Simulate LangGraph's state merging behavior.

    LangGraph merges partial updates returned by nodes into the full state.
    This helper simulates that behavior for testing.
    """
    if not update:
        return state
    return state.model_copy(update=update)
