"""Approval workflow node for LangGraph workflow.

This module implements the approval workflow node that manages approval requests
and resolutions for tool executions.
"""

import logging
from typing import Any

from gearmeshing_ai.agent_core.runtime.approval_manager import ApprovalManager
from gearmeshing_ai.agent_core.runtime.policy_engine import PolicyEngine
from gearmeshing_ai.agent_core.runtime.workflow_state import WorkflowState, WorkflowStatus

logger = logging.getLogger(__name__)


async def approval_workflow_node(
    state: WorkflowState,
    policy_engine: PolicyEngine,
    approval_manager: ApprovalManager,
) -> dict[str, Any]:
    """Execute approval workflow node.

    This node manages approval requests for tool executions based on policies.
    It creates approval requests for tools that require approval and tracks
    their resolution.

    Args:
        state: Current workflow state
        policy_engine: Policy engine for approval requirements
        approval_manager: Manager for approval requests

    Returns:
        Dictionary containing updated workflow state with approval status

    Raises:
        RuntimeError: If approval workflow fails

    """
    logger.debug(f"Approval workflow node started for run_id={state.run_id}")

    try:
        # Check if there are pending approvals
        pending_approvals = approval_manager.get_pending_approvals(state.run_id)

        if pending_approvals:
            logger.info(
                f"Found {len(pending_approvals)} pending approvals for run_id={state.run_id}"
            )
            return {
                "status": WorkflowStatus(
                    state="AWAITING_APPROVAL",
                    message=f"Waiting for {len(pending_approvals)} approval(s)",
                ),
            }

        # Check if all approvals are resolved
        all_approvals = approval_manager.get_run_approvals(state.run_id)
        approved_count = len([a for a in all_approvals if a.is_approved()])
        rejected_count = len([a for a in all_approvals if a.status.value == "REJECTED"])

        if rejected_count > 0:
            logger.warning(f"Found {rejected_count} rejected approvals for run_id={state.run_id}")
            return {
                "status": WorkflowStatus(
                    state="APPROVAL_REJECTED",
                    message=f"{rejected_count} approval(s) rejected",
                ),
            }

        if approved_count > 0:
            logger.info(f"All {approved_count} approval(s) approved for run_id={state.run_id}")
            return {
                "status": WorkflowStatus(
                    state="APPROVAL_COMPLETE",
                    message=f"All {approved_count} approval(s) approved",
                ),
            }

        # No approvals needed
        logger.debug(f"No approvals needed for run_id={state.run_id}")
        return {
            "status": WorkflowStatus(
                state="APPROVAL_COMPLETE",
                message="No approvals required",
            ),
        }

    except RuntimeError as e:
        logger.error(f"RuntimeError in approval workflow: {e}")
        return {
            "status": WorkflowStatus(
                state="FAILED",
                message="Approval workflow failed",
                error=str(e),
            ),
        }

    except Exception as e:
        logger.error(f"Exception in approval workflow: {e}")
        return {
            "status": WorkflowStatus(
                state="FAILED",
                message="Approval workflow failed",
                error=str(e),
            ),
        }


async def approval_resolution_node(
    state: WorkflowState,
    approval_manager: ApprovalManager,
) -> dict[str, Any]:
    """Execute approval resolution node.

    This node processes approval resolutions and updates workflow state
    based on approval decisions.

    Args:
        state: Current workflow state
        approval_manager: Manager for approval requests

    Returns:
        Dictionary containing updated workflow state with resolution status

    Raises:
        RuntimeError: If approval resolution fails

    """
    logger.debug(f"Approval resolution node started for run_id={state.run_id}")

    try:
        # Get approval statistics
        stats = approval_manager.get_approval_stats(state.run_id)

        logger.info(
            f"Approval stats for run_id={state.run_id}: "
            f"total={stats['total']}, approved={stats['approved']}, "
            f"rejected={stats['rejected']}, pending={stats['pending']}"
        )

        # Check if all approvals are resolved
        if stats["pending"] > 0:
            logger.debug(f"Still {stats['pending']} pending approvals")
            return {
                "status": WorkflowStatus(
                    state="AWAITING_APPROVAL",
                    message=f"Waiting for {stats['pending']} approval(s)",
                ),
            }

        # All approvals resolved
        if stats["rejected"] > 0:
            logger.warning(f"Approvals rejected: {stats['rejected']}")
            return {
                "status": WorkflowStatus(
                    state="APPROVAL_REJECTED",
                    message=f"{stats['rejected']} approval(s) rejected",
                ),
            }

        logger.info(f"All approvals resolved successfully for run_id={state.run_id}")
        return {
            "status": WorkflowStatus(
                state="COMPLETED",
                message=f"All {stats['approved']} approval(s) resolved and workflow completed",
            ),
        }

    except RuntimeError as e:
        logger.error(f"RuntimeError in approval resolution: {e}")
        return {
            "status": WorkflowStatus(
                state="FAILED",
                message="Approval resolution failed",
                error=str(e),
            ),
        }

    except Exception as e:
        logger.error(f"Exception in approval resolution: {e}")
        return {
            "status": WorkflowStatus(
                state="FAILED",
                message="Approval resolution failed",
                error=str(e),
            ),
        }
