"""Backward compatibility module for workflow state enums.

DEPRECATED: This module is maintained for backward compatibility only.
New code should import from gearmeshing_ai.agent_core.runtime.models instead.

Example:
    # Old (deprecated):
    from gearmeshing_ai.agent_core.runtime.workflow_states import WorkflowStateEnum
    
    # New (preferred):
    from gearmeshing_ai.agent_core.runtime.models import WorkflowStateEnum
"""

# Re-export from new location for backward compatibility
from gearmeshing_ai.agent_core.runtime.models.workflow_states import (
    COMPLETION_STATES,
    CONTINUING_STATES,
    ERROR_STATES,
    STATE_CATEGORIES,
    WorkflowStateCategory,
    WorkflowStateEnum,
)

__all__ = [
    "WorkflowStateEnum",
    "WorkflowStateCategory",
    "STATE_CATEGORIES",
    "COMPLETION_STATES",
    "CONTINUING_STATES",
    "ERROR_STATES",
]
