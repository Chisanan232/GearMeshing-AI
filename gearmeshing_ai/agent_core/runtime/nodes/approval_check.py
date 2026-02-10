"""Approval check node for LangGraph workflow.

This module implements the approval check node that determines if a proposal
requires human approval before execution.

Uses typed return models and centralized workflow state enums for type safety.
"""

import logging
from typing import Any

from ..models import ApprovalCheckNodeReturn, WorkflowState, WorkflowStateEnum, WorkflowStatus

logger = logging.getLogger(__name__)


async def approval_check_node(
    state: WorkflowState,
) -> dict[str, Any]:
    """Execute approval check node.

    This node checks if the current proposal requires human approval
    before proceeding with execution.

    Args:
        state: Current workflow state with current_proposal

    Returns:
        Dictionary containing updated workflow state with approval decision

    Raises:
        ValueError: If no current proposal exists

    """
    logger.debug(f"Approval check node started for run_id={state.run_id}")

    try:
        # Check if proposal exists
        if state.current_proposal is None:
            msg = "No current proposal for approval check"
            logger.error(msg)
            raise ValueError(msg)

        proposal = state.current_proposal

        # Check if approval is required (can be extended with approval policy)
        # For now, assume no approval required unless explicitly set
        requires_approval = False

        if requires_approval:
            logger.info(f"Approval required for action: {proposal.action}")
            return ApprovalCheckNodeReturn(
                status=WorkflowStatus(
                    state=WorkflowStateEnum.AWAITING_APPROVAL.value,
                    message=f"Awaiting approval for: {proposal.action}",
                ),
            ).to_dict()
        logger.info(f"No approval required for action: {proposal.action}")
        return ApprovalCheckNodeReturn(
            status=WorkflowStatus(
                state=WorkflowStateEnum.APPROVAL_SKIPPED.value,
                message=f"Proceeding without approval: {proposal.action}",
            ),
        ).to_dict()

    except ValueError as e:
        logger.error(f"ValueError in approval check: {e}")
        return ApprovalCheckNodeReturn(
            status=WorkflowStatus(
                state=WorkflowStateEnum.FAILED.value,
                message="Approval check failed",
                error=str(e),
            ),
        ).to_dict()
