"""Backward compatibility module for node return types.

DEPRECATED: This module is maintained for backward compatibility only.
New code should import from gearmeshing_ai.agent_core.runtime.models instead.

Example:
    # Old (deprecated):
    from gearmeshing_ai.agent_core.runtime.node_returns import CapabilityDiscoveryNodeReturn
    
    # New (preferred):
    from gearmeshing_ai.agent_core.runtime.models import CapabilityDiscoveryNodeReturn
"""

# Re-export from new location for backward compatibility
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

__all__ = [
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
