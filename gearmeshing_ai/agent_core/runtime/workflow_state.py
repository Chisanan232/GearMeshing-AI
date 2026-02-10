"""Backward compatibility module for workflow state models.

DEPRECATED: This module is maintained for backward compatibility only.
New code should import from gearmeshing_ai.agent_core.runtime.models instead.

Example:
    # Old (deprecated):
    from gearmeshing_ai.agent_core.runtime.workflow_state import WorkflowState
    
    # New (preferred):
    from gearmeshing_ai.agent_core.runtime.models import WorkflowState
"""

# Re-export from new location for backward compatibility
from gearmeshing_ai.agent_core.runtime.models.workflow_state import (
    ExecutionContext,
    WorkflowState,
    WorkflowStatus,
)

__all__ = [
    "ExecutionContext",
    "WorkflowState",
    "WorkflowStatus",
]
