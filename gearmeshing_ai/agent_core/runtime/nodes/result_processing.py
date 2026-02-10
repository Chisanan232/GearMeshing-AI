"""Result processing node for LangGraph workflow.

This module implements the result processing node that processes and logs
the results of action execution.

Uses typed return models and centralized workflow state enums for type safety.
"""

import logging
from typing import Any

from ..models import ResultProcessingNodeReturn, WorkflowState, WorkflowStateEnum, WorkflowStatus

logger = logging.getLogger(__name__)


async def result_processing_node(
    state: WorkflowState,
) -> dict[str, Any]:
    """Execute result processing node.

    This node processes the results of action execution, logging them
    and updating the workflow state accordingly.

    Args:
        state: Current workflow state with execution results

    Returns:
        Dictionary containing updated workflow state with processed results

    """
    logger.debug(f"Result processing node started for run_id={state.run_id}")

    try:
        # Check if there are execution results to process
        if not state.executions:
            logger.debug(f"No execution results to process for run_id={state.run_id}")
            return ResultProcessingNodeReturn(
                status=WorkflowStatus(
                    state=WorkflowStateEnum.RESULTS_PROCESSED.value,
                    message="No execution results to process",
                ),
            ).to_dict()

        # Get the latest execution result
        latest_execution = state.executions[-1]
        logger.info(f"Processing execution result: {latest_execution.get('action', 'unknown')}")

        # Validate execution result
        if "error" in latest_execution:
            logger.error(f"Execution failed: {latest_execution['error']}")
            return ResultProcessingNodeReturn(
                status=WorkflowStatus(
                    state=WorkflowStateEnum.EXECUTION_FAILED.value,
                    message=f"Execution failed: {latest_execution['error']}",
                    error=latest_execution.get("error"),
                ),
            ).to_dict()
        logger.info(f"Execution succeeded: {latest_execution.get('action')}")
        return ResultProcessingNodeReturn(
            status=WorkflowStatus(
                state=WorkflowStateEnum.RESULTS_PROCESSED.value,
                message=f"Results processed for action: {latest_execution.get('action')}",
            ),
        ).to_dict()

    except Exception as e:
        logger.error(f"Exception in result processing: {e}")
        return ResultProcessingNodeReturn(
            status=WorkflowStatus(
                state=WorkflowStateEnum.FAILED.value,
                message="Result processing failed",
                error=str(e),
            ),
        ).to_dict()
