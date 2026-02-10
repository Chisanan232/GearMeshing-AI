"""Error handler node for LangGraph workflow.

This module implements the error handler node that processes and logs
errors that occur during workflow execution.

Uses typed return models and centralized workflow state enums for type safety.
"""

import logging
from typing import Any

from ..node_returns import ErrorHandlerNodeReturn
from ..workflow_state import WorkflowState, WorkflowStatus
from ..workflow_states import WorkflowStateEnum

logger = logging.getLogger(__name__)


async def error_handler_node(
    state: WorkflowState,
) -> dict[str, Any]:
    """Execute error handler node.

    This node handles errors that occur during workflow execution,
    logging them and updating the workflow status appropriately.

    Args:
        state: Current workflow state

    Returns:
        Dictionary containing updated workflow state with error status

    """
    logger.debug(f"Error handler node started for run_id={state.run_id}")

    # Check if there's an error in the current status
    if state.status.error:
        logger.error(f"Error detected in workflow: {state.status.error}, state={state.status.state}")

        # Log error details
        error_record: dict[str, Any] = {
            "timestamp": state.updated_at.isoformat(),
            "error": state.status.error,
            "state": state.status.state,
            "message": state.status.message,
        }

        # Add error to executions history
        updated_executions = state.executions + [error_record]

        logger.info(f"Error handled and logged for run_id={state.run_id}")
        return ErrorHandlerNodeReturn(
            executions=updated_executions,
            status=WorkflowStatus(
                state=WorkflowStateEnum.ERROR_HANDLED.value,
                message="Error has been logged and handled",
                error=state.status.error,
            ),
        ).to_dict()

    # No error to handle
    logger.debug(f"No error to handle for run_id={state.run_id}")
    return {}
