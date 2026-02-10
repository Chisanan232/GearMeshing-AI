"""Workflow state enums and constants for LangGraph agent execution.

This module centralizes all valid workflow states as enums to prevent string
literal errors and improve type safety across the codebase.

USAGE
=====

Instead of:
    WorkflowStatus(state="COMPLETED", message="...")

Use:
    WorkflowStatus(state=WorkflowStateEnum.COMPLETED.value, message="...")

Or with type checking:
    from gearmeshing_ai.agent_core.runtime.workflow_states import WorkflowStateEnum
    
    state_value: str = WorkflowStateEnum.COMPLETED.value
"""

from enum import Enum


class WorkflowStateEnum(str, Enum):
    """Enumeration of all valid workflow states.
    
    This enum centralizes workflow state definitions to prevent string literal
    errors and provide IDE autocomplete support.
    
    State Transitions:
        PENDING → RUNNING → [various processing states] → COMPLETED/FAILED
    
    State Categories:
        - Initial: PENDING
        - Processing: RUNNING, PROPOSAL_OBTAINED, POLICY_APPROVED, AWAITING_APPROVAL, etc.
        - Terminal: COMPLETED, FAILED
        - Special: CONTINUING (workflow continues to next iteration)
    """

    # Initial state
    PENDING = "PENDING"
    
    # Processing states - Agent decision phase
    RUNNING = "RUNNING"
    PROPOSAL_OBTAINED = "PROPOSAL_OBTAINED"
    
    # Processing states - Policy validation phase
    POLICY_APPROVED = "POLICY_APPROVED"
    POLICY_REJECTED = "POLICY_REJECTED"
    
    # Processing states - Approval phase
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVAL_SKIPPED = "APPROVAL_SKIPPED"
    APPROVAL_COMPLETE = "APPROVAL_COMPLETE"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
    
    # Processing states - Capability discovery
    CAPABILITY_DISCOVERY_COMPLETE = "CAPABILITY_DISCOVERY_COMPLETE"
    
    # Processing states - Execution and results
    EXECUTION_FAILED = "EXECUTION_FAILED"
    RESULTS_PROCESSED = "RESULTS_PROCESSED"
    
    # Processing states - Error handling
    ERROR_HANDLED = "ERROR_HANDLED"
    
    # Terminal states
    COMPLETED = "COMPLETED"
    CONTINUING = "CONTINUING"
    FAILED = "FAILED"
    
    # Approval resolution states
    APPROVAL_RESOLVED = "APPROVAL_RESOLVED"


class WorkflowStateCategory(str, Enum):
    """Categories of workflow states for routing and logic decisions.
    
    This helps organize states into logical groups for conditional logic.
    """

    INITIAL = "INITIAL"
    PROCESSING = "PROCESSING"
    TERMINAL = "TERMINAL"
    ERROR = "ERROR"


# Mapping of states to their categories
STATE_CATEGORIES = {
    WorkflowStateEnum.PENDING: WorkflowStateCategory.INITIAL,
    WorkflowStateEnum.RUNNING: WorkflowStateCategory.PROCESSING,
    WorkflowStateEnum.PROPOSAL_OBTAINED: WorkflowStateCategory.PROCESSING,
    WorkflowStateEnum.POLICY_APPROVED: WorkflowStateCategory.PROCESSING,
    WorkflowStateEnum.POLICY_REJECTED: WorkflowStateCategory.ERROR,
    WorkflowStateEnum.AWAITING_APPROVAL: WorkflowStateCategory.PROCESSING,
    WorkflowStateEnum.APPROVAL_REQUIRED: WorkflowStateCategory.PROCESSING,
    WorkflowStateEnum.APPROVAL_SKIPPED: WorkflowStateCategory.PROCESSING,
    WorkflowStateEnum.APPROVAL_COMPLETE: WorkflowStateCategory.PROCESSING,
    WorkflowStateEnum.APPROVAL_REJECTED: WorkflowStateCategory.ERROR,
    WorkflowStateEnum.CAPABILITY_DISCOVERY_COMPLETE: WorkflowStateCategory.PROCESSING,
    WorkflowStateEnum.EXECUTION_FAILED: WorkflowStateCategory.ERROR,
    WorkflowStateEnum.RESULTS_PROCESSED: WorkflowStateCategory.PROCESSING,
    WorkflowStateEnum.ERROR_HANDLED: WorkflowStateCategory.ERROR,
    WorkflowStateEnum.COMPLETED: WorkflowStateCategory.TERMINAL,
    WorkflowStateEnum.CONTINUING: WorkflowStateCategory.PROCESSING,
    WorkflowStateEnum.FAILED: WorkflowStateCategory.TERMINAL,
    WorkflowStateEnum.APPROVAL_RESOLVED: WorkflowStateCategory.TERMINAL,
}

# States that indicate workflow completion (terminal states)
COMPLETION_STATES = {
    WorkflowStateEnum.COMPLETED,
    WorkflowStateEnum.FAILED,
    WorkflowStateEnum.APPROVAL_RESOLVED,
    WorkflowStateEnum.RESULTS_PROCESSED,
    WorkflowStateEnum.POLICY_REJECTED,
    WorkflowStateEnum.ERROR_HANDLED,
}

# States that indicate workflow should continue processing
CONTINUING_STATES = {
    WorkflowStateEnum.CONTINUING,
    WorkflowStateEnum.RUNNING,
}

# States that indicate an error occurred
ERROR_STATES = {
    WorkflowStateEnum.POLICY_REJECTED,
    WorkflowStateEnum.APPROVAL_REJECTED,
    WorkflowStateEnum.EXECUTION_FAILED,
    WorkflowStateEnum.FAILED,
}
