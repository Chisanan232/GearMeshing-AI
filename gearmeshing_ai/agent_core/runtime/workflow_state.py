"""Workflow state model for LangGraph agent execution.

This module defines the core state data structure for the LangGraph workflow,
integrating with existing ActionProposal and MCPToolCatalog models.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from gearmeshing_ai.agent_core.models.actions import ActionProposal, MCPToolCatalog


class ExecutionContext(BaseModel):
    """Execution context for workflow operations.

    Attributes:
        task_description: Description of the task to be executed
        agent_role: Role of the agent performing the task
        user_id: ID of the user initiating the workflow
        metadata: Additional context information

    """

    task_description: str = Field(..., description="Task description")
    agent_role: str = Field(..., description="Agent role")
    user_id: str = Field(..., description="User ID")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context metadata",
    )


class WorkflowStatus(BaseModel):
    """Workflow execution status.

    Attributes:
        state: Current workflow state (PENDING, RUNNING, PAUSED, COMPLETED, FAILED)
        message: Status message
        error: Error message if failed

    """

    state: str = Field(..., description="Current workflow state")
    message: str = Field(default="", description="Status message")
    error: str | None = Field(default=None, description="Error message if failed")


class WorkflowState(BaseModel):
    """LangGraph workflow state.

    This model represents the complete state of a workflow execution,
    integrating with existing ActionProposal and MCPToolCatalog models.

    Attributes:
        run_id: Unique identifier for the workflow run
        status: Current workflow status
        context: Execution context
        current_proposal: Current agent proposal (ActionProposal)
        available_capabilities: Available tools catalog (MCPToolCatalog)
        decisions: List of agent decisions made during execution
        executions: List of execution events
        approvals: List of approval records
        created_at: Workflow creation timestamp
        updated_at: Last update timestamp

    """

    run_id: str = Field(..., description="Workflow run ID")
    status: WorkflowStatus = Field(..., description="Current workflow status")
    context: ExecutionContext = Field(..., description="Execution context")
    current_proposal: ActionProposal | None = Field(
        default=None,
        description="Current agent proposal",
    )
    available_capabilities: MCPToolCatalog | None = Field(
        default=None,
        description="Available tools catalog",
    )
    decisions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Agent decisions history",
    )
    executions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Execution events history",
    )
    approvals: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Approval records",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Workflow creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "run_id": "run_123",
                "status": {
                    "state": "RUNNING",
                    "message": "Agent decision in progress",
                },
                "context": {
                    "task_description": "Run unit tests",
                    "agent_role": "developer",
                    "user_id": "user_123",
                    "metadata": {},
                },
                "current_proposal": None,
                "available_capabilities": None,
                "decisions": [],
                "executions": [],
                "approvals": [],
            }
        }
