"""Agent decision node for LangGraph workflow.

This module implements the agent decision node that uses AgentFactory
to create an agent and obtain its proposal for the next action.

Integrates with the roles package for role validation, selection, and management.
Uses typed return models and centralized workflow state enums for type safety.
"""

import logging
from typing import Any

from gearmeshing_ai.agent.abstraction.factory import AgentFactory
from gearmeshing_ai.agent.models.actions import ActionProposal
from gearmeshing_ai.agent.roles.registry import get_global_registry
from gearmeshing_ai.agent.roles.selector import RoleSelector

from ..models import AgentDecisionNodeReturn, WorkflowState, WorkflowStateEnum, WorkflowStatus

logger = logging.getLogger(__name__)


async def agent_decision_node(
    state: WorkflowState,
    agent_factory: AgentFactory,
    role_selector: RoleSelector | None = None,
    auto_select_role: bool = False,
) -> dict[str, Any]:
    """Execute agent decision node with role support.

    This node uses AgentFactory to create an agent and obtain its proposal
    for the next action based on the current workflow state and context.

    Supports role validation and automatic role selection based on task description.

    Args:
        state: Current workflow state
        agent_factory: Agent factory instance for creating agents
        role_selector: RoleSelector instance for role management (optional)
        auto_select_role: If True, auto-select role based on task if not specified

    Returns:
        Dictionary containing updated workflow state with current_proposal

    Raises:
        ValueError: If agent role is not found or invalid
        RuntimeError: If agent creation or execution fails

    """
    logger.debug(
        f"Agent decision node started for run_id={state.run_id}, "
        f"agent_role={state.context.agent_role}, auto_select={auto_select_role}"
    )

    try:
        # Initialize role selector if not provided
        if role_selector is None:
            role_selector = RoleSelector(get_global_registry())

        # Determine the role to use
        agent_role = state.context.agent_role

        # Validate or auto-select role
        if not agent_role:
            if auto_select_role:
                # Auto-select role based on task description
                agent_role = role_selector.suggest_role(state.context.task_description)
                if not agent_role:
                    msg = f"Could not auto-select role for task: {state.context.task_description[:50]}..."
                    logger.error(msg)
                    raise ValueError(msg)
                logger.info(f"Auto-selected role: {agent_role}")
                state.context.agent_role = agent_role
            else:
                msg = "No agent role specified in context"
                logger.error(msg)
                raise ValueError(msg)
        else:
            # Validate specified role
            if not role_selector.validate_role(agent_role):
                msg = f"Invalid agent role: {agent_role}"
                logger.error(msg)
                raise ValueError(msg)
            logger.debug(f"Role validated: {agent_role}")

        # Create or retrieve agent from factory
        agent = await agent_factory.get_or_create_agent(agent_role)
        logger.debug(f"Agent created/retrieved for role={agent_role}")

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
                message=f"Agent proposed action: {proposal.action} (role: {agent_role})",
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
    except TypeError as e:
        logger.error(f"TypeError in agent decision: {e}")
        return AgentDecisionNodeReturn(
            status=WorkflowStatus(
                state=WorkflowStateEnum.FAILED.value,
                message="Invalid proposal type",
                error=str(e),
            ),
        ).to_dict()
