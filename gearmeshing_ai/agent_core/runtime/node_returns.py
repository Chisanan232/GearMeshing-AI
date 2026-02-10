"""Typed data models for LangGraph node return values.

This module defines structured return types for workflow nodes to provide:
1. Type safety and IDE autocomplete
2. Clear documentation of what each node returns
3. Validation of node outputs
4. Easier maintenance and extension

WHY THIS MATTERS
================

LangGraph nodes return dictionaries that are merged into the workflow state.
Without type hints, it's unclear what keys are valid or what types they contain.

Before (hard to maintain):
    def my_node(state: WorkflowState) -> dict:
        return {
            "status": WorkflowStatus(...),
            "available_capabilities": MCPToolCatalog(...),
        }
    # What other keys can I return? What are the types?

After (clear and maintainable):
    def my_node(state: WorkflowState) -> CapabilityDiscoveryNodeReturn:
        return CapabilityDiscoveryNodeReturn(
            available_capabilities=catalog,
            status=status,
        )
    # IDE shows all available fields, types are validated

USAGE IN NODES
==============

from gearmeshing_ai.agent_core.runtime.node_returns import (
    CapabilityDiscoveryNodeReturn,
    AgentDecisionNodeReturn,
)

async def capability_discovery_node(state: WorkflowState) -> dict:
    # ... node logic ...
    return CapabilityDiscoveryNodeReturn(
        available_capabilities=catalog,
        status=status,
    ).model_dump(exclude_none=True)

VALIDATION
==========

Each return type is a Pydantic model that:
- Validates field types at creation time
- Provides IDE autocomplete
- Documents required vs optional fields
- Can be extended with custom fields
- Serializes to dict for LangGraph compatibility
"""

from typing import Any, Optional
from pydantic import BaseModel, Field

from gearmeshing_ai.agent_core.models.actions import MCPToolCatalog, ActionProposal
from gearmeshing_ai.agent_core.runtime.workflow_state import WorkflowStatus


class NodeReturnBase(BaseModel):
    """Base class for all node return types.
    
    Provides common functionality for node returns:
    - Validation of field types
    - Conversion to dict for LangGraph
    - Documentation of fields
    """

    class Config:
        """Pydantic config for node returns."""
        arbitrary_types_allowed = True
        extra = "forbid"  # Prevent accidental extra fields

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for LangGraph state update.
        
        Returns:
            Dictionary with only non-None fields (for partial updates)
        """
        return self.model_dump(exclude_none=True)


class CapabilityDiscoveryNodeReturn(NodeReturnBase):
    """Return type for capability_discovery_node.
    
    This node discovers available capabilities from MCP servers.
    
    Fields:
        available_capabilities: Discovered tool catalog
        status: Updated workflow status
    
    Example:
        return CapabilityDiscoveryNodeReturn(
            available_capabilities=catalog,
            status=WorkflowStatus(state="CAPABILITY_DISCOVERY_COMPLETE", ...),
        )
    """

    available_capabilities: Optional[MCPToolCatalog] = Field(
        default=None,
        description="Discovered tool catalog from MCP servers"
    )
    status: WorkflowStatus = Field(
        description="Updated workflow status after capability discovery"
    )


class AgentDecisionNodeReturn(NodeReturnBase):
    """Return type for agent_decision_node.
    
    This node generates an agent proposal for the next action.
    
    Fields:
        current_proposal: Agent's proposed action
        status: Updated workflow status
        decisions: List of decision records (appended to state)
    
    Example:
        return AgentDecisionNodeReturn(
            current_proposal=proposal,
            status=WorkflowStatus(state="PROPOSAL_OBTAINED", ...),
        )
    """

    current_proposal: Optional[ActionProposal] = Field(
        default=None,
        description="Agent's proposed action"
    )
    status: WorkflowStatus = Field(
        description="Updated workflow status after agent decision"
    )
    decisions: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Decision records to append to history"
    )


class PolicyValidationNodeReturn(NodeReturnBase):
    """Return type for policy_validation_node.
    
    This node validates the agent proposal against policies.
    
    Fields:
        status: Updated workflow status (POLICY_APPROVED or POLICY_REJECTED)
    
    Example:
        return PolicyValidationNodeReturn(
            status=WorkflowStatus(state="POLICY_APPROVED", ...),
        )
    """

    status: WorkflowStatus = Field(
        description="Updated workflow status after policy validation"
    )


class ApprovalCheckNodeReturn(NodeReturnBase):
    """Return type for approval_check_node.
    
    This node determines if approval is required for the proposal.
    
    Fields:
        status: Updated workflow status
        approvals: Approval records if approval is required
    
    Example:
        return ApprovalCheckNodeReturn(
            status=WorkflowStatus(state="APPROVAL_REQUIRED", ...),
            approvals=[approval_record],
        )
    """

    status: WorkflowStatus = Field(
        description="Updated workflow status after approval check"
    )
    approvals: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Approval records if approval is required"
    )


class ApprovalWorkflowNodeReturn(NodeReturnBase):
    """Return type for approval_workflow_node.
    
    This node manages the approval workflow.
    
    Fields:
        status: Updated workflow status
        approvals: Updated approval records
    
    Example:
        return ApprovalWorkflowNodeReturn(
            status=WorkflowStatus(state="APPROVAL_COMPLETE", ...),
        )
    """

    status: WorkflowStatus = Field(
        description="Updated workflow status after approval workflow"
    )
    approvals: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Updated approval records"
    )


class ResultProcessingNodeReturn(NodeReturnBase):
    """Return type for result_processing_node.
    
    This node processes execution results.
    
    Fields:
        status: Updated workflow status
        executions: Execution records
    
    Example:
        return ResultProcessingNodeReturn(
            status=WorkflowStatus(state="RESULTS_PROCESSED", ...),
        )
    """

    status: WorkflowStatus = Field(
        description="Updated workflow status after result processing"
    )
    executions: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Execution records"
    )


class CompletionCheckNodeReturn(NodeReturnBase):
    """Return type for completion_check_node.
    
    This node determines if the workflow is complete.
    
    Fields:
        status: Updated workflow status (COMPLETED or CONTINUING)
    
    Example:
        return CompletionCheckNodeReturn(
            status=WorkflowStatus(state="COMPLETED", ...),
        )
    """

    status: WorkflowStatus = Field(
        description="Updated workflow status after completion check"
    )


class ErrorHandlerNodeReturn(NodeReturnBase):
    """Return type for error_handler_node.
    
    This node handles workflow errors.
    
    Fields:
        status: Updated workflow status (ERROR_HANDLED or FAILED)
        executions: Updated execution records
    
    Example:
        return ErrorHandlerNodeReturn(
            status=WorkflowStatus(state="ERROR_HANDLED", ...),
        )
    """

    status: WorkflowStatus = Field(
        description="Updated workflow status after error handling"
    )
    executions: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Updated execution records"
    )


class ApprovalResolutionNodeReturn(NodeReturnBase):
    """Return type for approval_resolution_node.
    
    This node resolves pending approvals.
    
    Fields:
        status: Updated workflow status
        approvals: Resolved approval records
    
    Example:
        return ApprovalResolutionNodeReturn(
            status=WorkflowStatus(state="APPROVAL_RESOLVED", ...),
        )
    """

    status: WorkflowStatus = Field(
        description="Updated workflow status after approval resolution"
    )
    approvals: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Resolved approval records"
    )


# Type alias for any node return
NodeReturn = (
    CapabilityDiscoveryNodeReturn
    | AgentDecisionNodeReturn
    | PolicyValidationNodeReturn
    | ApprovalCheckNodeReturn
    | ApprovalWorkflowNodeReturn
    | ResultProcessingNodeReturn
    | CompletionCheckNodeReturn
    | ErrorHandlerNodeReturn
    | ApprovalResolutionNodeReturn
)
