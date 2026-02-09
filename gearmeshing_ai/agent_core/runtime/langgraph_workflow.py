"""LangGraph workflow definition for AI agent execution.

This module defines the LangGraph workflow that orchestrates the execution
of AI agents with policy validation, approval checks, and result processing.
"""

import logging
from typing import Any

from langgraph.graph import StateGraph

from gearmeshing_ai.agent_core.abstraction.factory import AgentFactory
from gearmeshing_ai.agent_core.abstraction.mcp import MCPClientAbstraction

from .nodes import (
    agent_decision_node,
    approval_check_node,
    completion_check_node,
    error_handler_node,
    policy_validation_node,
    result_processing_node,
)
from .workflow_state import WorkflowState

logger = logging.getLogger(__name__)


def create_agent_workflow(
    agent_factory: AgentFactory,
    mcp_client: MCPClientAbstraction,
) -> Any:
    """Create and compile the LangGraph workflow.

    This function creates a LangGraph workflow that orchestrates AI agent
    execution with the following node sequence:
    1. Agent Decision - Get agent proposal
    2. Policy Validation - Validate against policies
    3. Approval Check - Check if approval is needed
    4. Result Processing - Process execution results
    5. Completion Check - Determine if workflow is complete
    6. Error Handler - Handle any errors

    Args:
        agent_factory: Factory for creating AI agents
        mcp_client: MCP client for tool execution

    Returns:
        Compiled LangGraph workflow graph

    Raises:
        ValueError: If workflow creation fails
    """
    logger.info("Creating LangGraph workflow")

    try:
        # Create state graph
        workflow = StateGraph(WorkflowState)

        # Add nodes to the graph
        logger.debug("Adding nodes to workflow graph")

        # Agent decision node
        workflow.add_node(
            "agent_decision",
            lambda state: agent_decision_node(state, agent_factory),
        )

        # Policy validation node
        workflow.add_node(
            "policy_validation",
            lambda state: policy_validation_node(state),
        )

        # Approval check node
        workflow.add_node(
            "approval_check",
            lambda state: approval_check_node(state),
        )

        # Result processing node
        workflow.add_node(
            "result_processing",
            lambda state: result_processing_node(state),
        )

        # Completion check node
        workflow.add_node(
            "completion_check",
            lambda state: completion_check_node(state),
        )

        # Error handler node
        workflow.add_node(
            "error_handler",
            lambda state: error_handler_node(state),
        )

        # Set entry point
        logger.debug("Setting workflow entry point")
        workflow.set_entry_point("agent_decision")

        # Add edges between nodes
        logger.debug("Adding edges between nodes")

        # Agent decision -> Policy validation
        workflow.add_edge("agent_decision", "policy_validation")

        # Policy validation -> Approval check or Error handler
        def policy_validation_router(state: WorkflowState) -> str:
            """Route based on policy validation result."""
            if state.status.state == "POLICY_REJECTED":
                return "error_handler"
            return "approval_check"

        workflow.add_conditional_edges(
            "policy_validation",
            policy_validation_router,
            {
                "approval_check": "approval_check",
                "error_handler": "error_handler",
            },
        )

        # Approval check -> Result processing
        workflow.add_edge("approval_check", "result_processing")

        # Result processing -> Completion check
        workflow.add_edge("result_processing", "completion_check")

        # Completion check -> End or Error handler
        def completion_router(state: WorkflowState) -> str:
            """Route based on completion status."""
            if state.status.error:
                return "error_handler"
            return "__end__"

        workflow.add_conditional_edges(
            "completion_check",
            completion_router,
            {
                "error_handler": "error_handler",
                "__end__": "__end__",
            },
        )

        # Error handler -> End
        workflow.add_edge("error_handler", "__end__")

        # Compile the workflow
        logger.info("Compiling LangGraph workflow")
        compiled_workflow = workflow.compile()

        logger.info("LangGraph workflow created and compiled successfully")
        return compiled_workflow

    except Exception as e:
        logger.error(f"Failed to create LangGraph workflow: {e}")
        raise ValueError(f"Workflow creation failed: {e}") from e
