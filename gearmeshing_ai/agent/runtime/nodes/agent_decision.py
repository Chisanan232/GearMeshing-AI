"""Agent decision node for LangGraph workflow.

This module implements the agent decision node that uses AgentFactory
to create an agent and obtain its proposal for the next action.

Uses typed return models and centralized workflow state enums for type safety.
"""

import logging
from typing import Any

from gearmeshing_ai.agent.abstraction.factory import AgentFactory
from gearmeshing_ai.agent.models.actions import ActionProposal

from ..models import AgentDecisionNodeReturn, WorkflowState, WorkflowStateEnum, WorkflowStatus

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
    logger.debug(f"Agent decision node started for run_id={state.run_id}, agent_role={state.context.agent_role}")

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

        logger.info(f"Agent proposal obtained: action={proposal.action}, reason={proposal.reason}")

        # Update state with new proposal using typed return
        return AgentDecisionNodeReturn(
            current_proposal=proposal,
            status=WorkflowStatus(
                state=WorkflowStateEnum.PROPOSAL_OBTAINED.value,
                message=f"Agent proposed action: {proposal.action}",
            ),
        ).to_dict()

    except ValueError as e:
        logger.error(f"ValueError in agent decision: {e}")
        return AgentDecisionNodeReturn(
            status=WorkflowStatus(
                state=WorkflowStateEnum.FAILED.value,
                message="Agent decision failed",
                error=str(e),
            ),
        ).to_dict()
    except RuntimeError as e:
        logger.error(f"RuntimeError in agent decision: {e}")
        return AgentDecisionNodeReturn(
            status=WorkflowStatus(
                state=WorkflowStateEnum.FAILED.value,
                message="Agent execution failed",
                error=str(e),
            ),
        ).to_dict()
