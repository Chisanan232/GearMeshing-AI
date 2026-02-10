"""Completion check node for LangGraph workflow.

This module implements the completion check node that determines if the
workflow has completed successfully or needs to continue.

Uses typed return models and centralized workflow state enums for type safety
and maintainability.
"""

import logging
from typing import Any

from ..node_returns import CompletionCheckNodeReturn
from ..workflow_state import WorkflowState, WorkflowStatus
from ..workflow_states import WorkflowStateEnum, COMPLETION_STATES

logger = logging.getLogger(__name__)


async def completion_check_node(
    state: WorkflowState,
) -> dict[str, Any]:
    """Execute completion check node.

    This node checks if the workflow has completed successfully or if
    additional iterations are needed.

    State Transitions:
        RESULTS_PROCESSED → COMPLETED
        POLICY_REJECTED → COMPLETED
        ERROR_HANDLED → COMPLETED
        APPROVAL_RESOLVED → COMPLETED
        [other states] → CONTINUING

    Args:
        state: Current workflow state

    Returns:
        CompletionCheckNodeReturn with updated completion status

    """
    logger.debug(f"Completion check node started for run_id={state.run_id}")

    try:
        # Check current status
        current_status = state.status.state

        # Determine if workflow is complete using centralized state set
        is_complete = current_status in COMPLETION_STATES

        if is_complete:
            logger.info(f"Workflow completed for run_id={state.run_id}, final_state={current_status}")
            return CompletionCheckNodeReturn(
                status=WorkflowStatus(
                    state=WorkflowStateEnum.COMPLETED.value,
                    message=f"Workflow completed with state: {current_status}",
                ),
            ).to_dict()
        else:
            logger.debug(f"Workflow continuing for run_id={state.run_id}, current_state={current_status}")
            return CompletionCheckNodeReturn(
                status=WorkflowStatus(
                    state=WorkflowStateEnum.CONTINUING.value,
                    message=f"Workflow continuing from state: {current_status}",
                ),
            ).to_dict()

    except Exception as e:
        logger.error(f"Exception in completion check: {e}")
        return CompletionCheckNodeReturn(
            status=WorkflowStatus(
                state=WorkflowStateEnum.FAILED.value,
                message="Completion check failed",
                error=str(e),
            ),
        ).to_dict()
