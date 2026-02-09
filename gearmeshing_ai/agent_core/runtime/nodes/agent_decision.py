"""Agent decision node for LangGraph workflow.

This module implements the agent decision node that uses AgentFactory
to create an agent and obtain its proposal for the next action.
"""

import logging
from typing import Any

from gearmeshing_ai.agent_core.abstraction.factory import AgentFactory
from gearmeshing_ai.agent_core.models.actions import ActionProposal

from ..workflow_state import WorkflowState, WorkflowStatus

logger = logging.getLogger(__name__)


async def agent_decision_node(
    state: WorkflowState,
    agent_factory: AgentFactory,
) -> dict[str, Any]:
    """Execute agent decision node.

    This node uses AgentFactory to create an agent and obtain its proposal
    for the next action based on the current workflow state and context.

    Args:
        state: Current workflow state
        agent_factory: Agent factory instance for creating agents

    Returns:
        Dictionary containing updated workflow state with current_proposal

    Raises:
        ValueError: If agent role is not found in factory
        RuntimeError: If agent creation or execution fails
    """
    logger.debug(
        f"Agent decision node started for run_id={state.run_id}, "
        f"agent_role={state.context.agent_role}"
    )

    try:
        # Create or retrieve agent from factory
        agent = await agent_factory.get_or_create_agent(state.context.agent_role)
        logger.debug(f"Agent created/retrieved for role={state.context.agent_role}")

        # Run agent to get proposal
        proposal = await agent_factory.adapter.run(
            agent,
            state.context.task_description,
        )

        # Validate proposal type
        if not isinstance(proposal, ActionProposal):
            msg = f"Expected ActionProposal, got {type(proposal).__name__}"
            logger.error(msg)
            raise TypeError(msg)

        logger.info(
            f"Agent proposal obtained: action={proposal.action}, "
            f"reason={proposal.reason}"
        )

        # Update state with new proposal
        updated_state = state.model_copy(
            update={
                "current_proposal": proposal,
                "status": WorkflowStatus(
                    state="PROPOSAL_OBTAINED",
                    message=f"Agent proposed action: {proposal.action}",
                ),
            }
        )

        return {"state": updated_state}

    except ValueError as e:
        logger.error(f"ValueError in agent decision: {e}")
        updated_state = state.model_copy(
            update={
                "status": WorkflowStatus(
                    state="FAILED",
                    message="Agent decision failed",
                    error=str(e),
                ),
            }
        )
        return {"state": updated_state}
    except RuntimeError as e:
        logger.error(f"RuntimeError in agent decision: {e}")
        updated_state = state.model_copy(
            update={
                "status": WorkflowStatus(
                    state="FAILED",
                    message="Agent execution failed",
                    error=str(e),
                ),
            }
        )
        return {"state": updated_state}
