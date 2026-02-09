"""Policy validation node for LangGraph workflow.

This module implements the policy validation node that validates
agent proposals against configured policies.
"""

import logging
from typing import Any

from ..workflow_state import WorkflowState, WorkflowStatus

logger = logging.getLogger(__name__)


async def policy_validation_node(
    state: WorkflowState,
) -> dict[str, Any]:
    """Execute policy validation node.

    This node validates the current agent proposal against configured policies
    to determine if the action is allowed to proceed.

    Args:
        state: Current workflow state with current_proposal

    Returns:
        Dictionary containing updated workflow state with validation result

    Raises:
        ValueError: If no current proposal exists

    """
    logger.debug(f"Policy validation node started for run_id={state.run_id}")

    try:
        # Check if proposal exists
        if state.current_proposal is None:
            msg = "No current proposal to validate"
            logger.error(msg)
            raise ValueError(msg)

        proposal = state.current_proposal

        # Basic policy validation (can be extended with actual policy engine)
        logger.info(f"Validating proposal: action={proposal.action}, reason={proposal.reason}")

        # For now, all proposals are allowed (policy engine will be added in Phase 3)
        policy_approved = True
        policy_message = f"Proposal approved: {proposal.action}"

        if policy_approved:
            logger.info(policy_message)
            updated_state = state.model_copy(
                update={
                    "status": WorkflowStatus(
                        state="POLICY_APPROVED",
                        message=policy_message,
                    ),
                }
            )
        else:
            logger.warning(f"Proposal rejected by policy: {proposal.action}")
            updated_state = state.model_copy(
                update={
                    "status": WorkflowStatus(
                        state="POLICY_REJECTED",
                        message=f"Proposal rejected: {proposal.action}",
                    ),
                }
            )

        return {"state": updated_state}

    except ValueError as e:
        logger.error(f"ValueError in policy validation: {e}")
        updated_state = state.model_copy(
            update={
                "status": WorkflowStatus(
                    state="FAILED",
                    message="Policy validation failed",
                    error=str(e),
                ),
            }
        )
        return {"state": updated_state}
