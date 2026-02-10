"""Completion check node for LangGraph workflow.

This module implements the completion check node that determines if the
workflow has completed successfully or needs to continue.
"""

import logging
from typing import Any

from ..workflow_state import WorkflowState, WorkflowStatus

logger = logging.getLogger(__name__)


async def completion_check_node(
    state: WorkflowState,
) -> dict[str, Any]:
    """Execute completion check node.

    This node checks if the workflow has completed successfully or if
    additional iterations are needed.

    Args:
        state: Current workflow state

    Returns:
        Dictionary containing updated workflow state with completion status

    """
    logger.debug(f"Completion check node started for run_id={state.run_id}")

    try:
        # Check current status
        current_status = state.status.state

        # Determine if workflow is complete
        completion_states = {"RESULTS_PROCESSED", "POLICY_REJECTED", "ERROR_HANDLED", "APPROVAL_RESOLVED"}
        is_complete = current_status in completion_states

        if is_complete:
            logger.info(f"Workflow completed for run_id={state.run_id}, final_state={current_status}")
            return {
                "status": WorkflowStatus(
                    state="COMPLETED",
                    message=f"Workflow completed with state: {current_status}",
                ),
            }
        else:
            logger.debug(f"Workflow continuing for run_id={state.run_id}, current_state={current_status}")
            return {
                "status": WorkflowStatus(
                    state="CONTINUING",
                    message=f"Workflow continuing from state: {current_status}",
                ),
            }

    except Exception as e:
        logger.error(f"Exception in completion check: {e}")
        return {
            "status": WorkflowStatus(
                state="FAILED",
                message="Completion check failed",
                error=str(e),
            ),
        }
