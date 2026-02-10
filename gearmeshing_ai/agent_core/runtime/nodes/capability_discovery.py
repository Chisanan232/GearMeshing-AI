"""Capability discovery node for LangGraph workflow.

This module implements the capability discovery node that discovers and filters
available tools based on the execution context.

Uses typed return models and centralized workflow state enums for type safety.
"""

import logging
from typing import Any

from ..capability_registry import CapabilityRegistry
from ..models import CapabilityDiscoveryNodeReturn, WorkflowState, WorkflowStateEnum, WorkflowStatus

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
        CapabilityDiscoveryNodeReturn with discovered capabilities and status

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
            return CapabilityDiscoveryNodeReturn(
                available_capabilities=None,
                status=WorkflowStatus(
                    state=WorkflowStateEnum.CAPABILITY_DISCOVERY_COMPLETE.value,
                    message="No capabilities available",
                ),
            ).to_dict()
        capability_count = len(updated_state.available_capabilities.tools)
        logger.info(
            f"Discovered {capability_count} capabilities for run_id={state.run_id}, "
            f"agent_role={state.context.agent_role}"
        )
        return CapabilityDiscoveryNodeReturn(
            available_capabilities=updated_state.available_capabilities,
            status=WorkflowStatus(
                state=WorkflowStateEnum.CAPABILITY_DISCOVERY_COMPLETE.value,
                message=f"Discovered {capability_count} capabilities",
            ),
        ).to_dict()

    except RuntimeError as e:
        logger.error(f"RuntimeError in capability discovery: {e}")
        return CapabilityDiscoveryNodeReturn(
            status=WorkflowStatus(
                state=WorkflowStateEnum.FAILED.value,
                message="Capability discovery failed",
                error=str(e),
            ),
        ).to_dict()

    except Exception as e:
        logger.error(f"Exception in capability discovery: {e}")
        return CapabilityDiscoveryNodeReturn(
            status=WorkflowStatus(
                state=WorkflowStateEnum.FAILED.value,
                message="Capability discovery failed",
                error=str(e),
            ),
        ).to_dict()
