"""Capability discovery node for LangGraph workflow.

This module implements the capability discovery node that discovers and filters
available tools based on the execution context.
"""

import logging
from typing import Any

from ..capability_registry import CapabilityRegistry
from ..workflow_state import WorkflowState, WorkflowStatus

logger = logging.getLogger(__name__)


async def capability_discovery_node(
    state: WorkflowState,
    capability_registry: CapabilityRegistry,
) -> dict[str, Any]:
    """Execute capability discovery node.

    This node discovers available capabilities from MCP servers and filters them
    based on the execution context and agent role.

    Args:
        state: Current workflow state
        capability_registry: Registry for capability management

    Returns:
        Dictionary containing updated workflow state with available capabilities

    Raises:
        RuntimeError: If capability discovery fails

    """
    logger.debug(f"Capability discovery node started for run_id={state.run_id}")

    try:
        # Update workflow state with available capabilities
        updated_state = await capability_registry.update_workflow_state(state)

        # Verify capabilities were discovered
        if updated_state.available_capabilities is None:
            logger.warning(f"No capabilities discovered for run_id={state.run_id}")
            updated_state = updated_state.model_copy(
                update={
                    "status": WorkflowStatus(
                        state="CAPABILITY_DISCOVERY_COMPLETE",
                        message="No capabilities available",
                    ),
                }
            )
        else:
            capability_count = len(updated_state.available_capabilities.tools)
            logger.info(
                f"Discovered {capability_count} capabilities for run_id={state.run_id}, "
                f"agent_role={state.context.agent_role}"
            )
            updated_state = updated_state.model_copy(
                update={
                    "status": WorkflowStatus(
                        state="CAPABILITY_DISCOVERY_COMPLETE",
                        message=f"Discovered {capability_count} capabilities",
                    ),
                }
            )

        return {"state": updated_state}

    except RuntimeError as e:
        logger.error(f"RuntimeError in capability discovery: {e}")
        updated_state = state.model_copy(
            update={
                "status": WorkflowStatus(
                    state="FAILED",
                    message="Capability discovery failed",
                    error=str(e),
                ),
            }
        )
        return {"state": updated_state}

    except Exception as e:
        logger.error(f"Exception in capability discovery: {e}")
        updated_state = state.model_copy(
            update={
                "status": WorkflowStatus(
                    state="FAILED",
                    message="Capability discovery failed",
                    error=str(e),
                ),
            }
        )
        return {"state": updated_state}
