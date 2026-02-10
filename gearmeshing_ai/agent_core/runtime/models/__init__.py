"""Runtime workflow models package.

This package contains all data models and enums for the LangGraph workflow system:
- WorkflowState and related models (workflow_state.py)
- WorkflowStateEnum and state constants (workflow_states.py)
- Typed node return models (node_returns.py)
"""

from gearmeshing_ai.agent_core.runtime.models.node_returns import (
    AgentDecisionNodeReturn,
    ApprovalCheckNodeReturn,
    ApprovalResolutionNodeReturn,
    ApprovalWorkflowNodeReturn,
    CapabilityDiscoveryNodeReturn,
    CompletionCheckNodeReturn,
    ErrorHandlerNodeReturn,
    NodeReturn,
    NodeReturnBase,
    PolicyValidationNodeReturn,
    ResultProcessingNodeReturn,
)
from gearmeshing_ai.agent_core.runtime.models.workflow_state import (
    ExecutionContext,
    WorkflowState,
    WorkflowStatus,
)
from gearmeshing_ai.agent_core.runtime.models.workflow_states import (
    COMPLETION_STATES,
    CONTINUING_STATES,
    ERROR_STATES,
    STATE_CATEGORIES,
    WorkflowStateCategory,
    WorkflowStateEnum,
)

__all__ = [
    # Workflow state models
    "ExecutionContext",
    "WorkflowState",
    "WorkflowStatus",
    # Workflow state enums
    "WorkflowStateEnum",
    "WorkflowStateCategory",
    "STATE_CATEGORIES",
    "COMPLETION_STATES",
    "CONTINUING_STATES",
    "ERROR_STATES",
    # Node return models
    "NodeReturnBase",
    "CapabilityDiscoveryNodeReturn",
    "AgentDecisionNodeReturn",
    "PolicyValidationNodeReturn",
    "ApprovalCheckNodeReturn",
    "ApprovalWorkflowNodeReturn",
    "ResultProcessingNodeReturn",
    "CompletionCheckNodeReturn",
    "ErrorHandlerNodeReturn",
    "ApprovalResolutionNodeReturn",
    "NodeReturn",
]
