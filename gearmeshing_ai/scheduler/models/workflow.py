"""Workflow-related models for the scheduler system.

This module contains models for representing AI workflows, actions, and their
execution within the Temporal workflow system.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from .base import BaseSchedulerModel


class AIActionType(str, Enum):
    """Types of AI actions that can be executed."""

    WORKFLOW_EXECUTION = "workflow_execution"
    TASK_ASSIGNMENT = "task_assignment"
    NOTIFICATION = "notification"
    DATA_PROCESSING = "data_processing"
    ESCALATION = "escalation"
    CUSTOM_ACTION = "custom_action"

    @classmethod
    def get_all_values(cls) -> list[str]:
        """Get all enum values as strings."""
        return [member.value for member in cls]


class AIAction(BaseSchedulerModel):
    """Represents an AI action to be executed as part of a workflow.

    This model encapsulates an action that should be taken by the AI system,
    including the type of action, parameters, and execution configuration.
    """

    # Action identification
    name: str = Field(..., description="Unique name of this action")
    type: AIActionType = Field(..., description="Type of action")
    workflow_name: str = Field(..., description="Name of the workflow to execute")
    checking_point_name: str = Field(..., description="Name of the checking point that triggered this action")

    # Execution configuration
    timeout_seconds: int = Field(default=600, ge=1, description="Timeout for action execution in seconds")

    retry_attempts: int = Field(default=3, ge=0, description="Number of retry attempts")

    retry_delay_seconds: int = Field(default=60, ge=0, description="Delay between retry attempts in seconds")

    # Action parameters
    parameters: dict[str, Any] = Field(default_factory=dict, description="Parameters for the action execution")

    # Prompt configuration
    prompt_template_id: str | None = Field(None, description="ID of the prompt template to use for this action")

    prompt_variables: dict[str, Any] = Field(
        default_factory=dict, description="Variables to substitute in the prompt template"
    )

    # Agent configuration
    agent_role: str | None = Field(None, description="Role of the AI agent that should execute this action")

    approval_required: bool = Field(default=False, description="Whether this action requires approval before execution")

    approval_timeout_seconds: int = Field(default=3600, ge=60, description="Timeout for approval in seconds")

    # Priority and scheduling
    priority: int = Field(default=5, ge=1, le=10, description="Priority of this action (1=lowest, 10=highest)")

    scheduled_at: datetime | None = Field(None, description="When this action should be scheduled for execution")

    # Execution tracking
    execution_id: str | None = Field(None, description="Unique ID for this specific execution")

    parent_execution_id: str | None = Field(None, description="ID of the parent execution, if this is a child action")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that action name is not empty."""
        if not v or not v.strip():
            raise ValueError("Action name cannot be empty")
        return v.strip()

    @field_validator("workflow_name")
    @classmethod
    def validate_workflow_name(cls, v: str) -> str:
        """Validate that workflow name is not empty."""
        if not v or not v.strip():
            raise ValueError("Workflow name cannot be empty")
        return v.strip()

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of this AI action.

        Returns:
            Dictionary containing key information about this action

        """
        summary = super().get_summary()
        # type is already a string due to use_enum_values config
        type_value = self.type if isinstance(self.type, str) else self.type.value
        summary.update(
            {
                "name": self.name,
                "type": type_value,
                "workflow_name": self.workflow_name,
                "checking_point_name": self.checking_point_name,
                "timeout_seconds": self.timeout_seconds,
                "priority": self.priority,
                "approval_required": self.approval_required,
                "has_prompt_template": self.prompt_template_id is not None,
                "has_agent_role": self.agent_role is not None,
                "is_scheduled": self.scheduled_at is not None,
            }
        )
        return summary

    def is_high_priority(self, threshold: int = 7) -> bool:
        """Check if this action has high priority.

        Args:
            threshold: Priority threshold (default: 7)

        Returns:
            True if priority is above threshold

        """
        return self.priority >= threshold

    def requires_approval(self) -> bool:
        """Check if this action requires approval."""
        return self.approval_required

    def is_scheduled(self) -> bool:
        """Check if this action is scheduled for future execution."""
        return self.scheduled_at is not None

    def get_execution_timeout(self) -> timedelta:
        """Get the execution timeout as a timedelta.

        Returns:
            Timeout as timedelta

        """
        return timedelta(seconds=self.timeout_seconds)

    def get_retry_delay(self) -> timedelta:
        """Get the retry delay as a timedelta.

        Returns:
            Retry delay as timedelta

        """
        return timedelta(seconds=self.retry_delay_seconds)

    def get_approval_timeout(self) -> timedelta:
        """Get the approval timeout as a timedelta.

        Returns:
            Approval timeout as timedelta

        """
        return timedelta(seconds=self.approval_timeout_seconds)


class AIWorkflowInput(BaseSchedulerModel):
    """Input data for AI workflow execution.

    This model encapsulates all the input data needed to execute an AI workflow,
    including the action to execute, the monitoring data that triggered it, and
    the checking point result.
    """

    # Core input data
    ai_action: AIAction = Field(..., description="AI action to execute")
    data_item: dict[str, Any] = Field(..., description="Monitoring data that triggered this action")
    check_result: dict[str, Any] = Field(..., description="Checking point evaluation result")

    # Execution context
    execution_context: dict[str, Any] = Field(default_factory=dict, description="Additional execution context")

    # Workflow configuration
    workflow_id: str | None = Field(None, description="Unique ID for this workflow execution")

    parent_workflow_id: str | None = Field(None, description="ID of the parent workflow, if this is a child workflow")

    # Execution options
    dry_run: bool = Field(default=False, description="Whether to run in dry-run mode (no actual actions)")

    debug_mode: bool = Field(default=False, description="Whether to run in debug mode with additional logging")

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of this workflow input.

        Returns:
            Dictionary containing key information about this input

        """
        summary = super().get_summary()
        summary.update(
            {
                "action_name": self.ai_action.name,
                "action_type": self.ai_action.type.value,
                "workflow_name": self.ai_action.workflow_name,
                "checking_point_name": self.ai_action.checking_point_name,
                "data_item_id": self.data_item.get("id"),
                "data_item_type": self.data_item.get("type"),
                "check_result_type": self.check_result.get("result_type"),
                "should_act": self.check_result.get("should_act", False),
                "dry_run": self.dry_run,
                "debug_mode": self.debug_mode,
            }
        )
        return summary


class AIWorkflowResult(BaseSchedulerModel):
    """Result of AI workflow execution.

    This model encapsulates the outcome of an AI workflow execution, including
    success/failure status, output data, and execution metadata.
    """

    # Execution result
    workflow_name: str = Field(..., description="Name of the workflow that was executed")
    checking_point_name: str = Field(..., description="Name of the checking point that triggered the workflow")
    success: bool = Field(..., description="Whether the workflow execution was successful")

    # Output data
    output: dict[str, Any] = Field(default_factory=dict, description="Output data from the workflow execution")

    # Execution metadata
    execution_id: str = Field(..., description="Unique ID for this execution")
    started_at: datetime = Field(..., description="When the workflow execution started")
    completed_at: datetime | None = Field(None, description="When the workflow execution completed")
    duration_ms: int | None = Field(None, description="Duration of execution in milliseconds")

    # Error information
    error_message: str | None = Field(None, description="Error message if execution failed")
    error_details: dict[str, Any] = Field(default_factory=dict, description="Additional error details")

    # Actions taken
    actions_taken: list[str] = Field(default_factory=list, description="List of actions that were taken")

    action_results: dict[str, Any] = Field(default_factory=dict, description="Results of individual actions")

    # Data summary
    data_summary: dict[str, Any] = Field(default_factory=dict, description="Summary of the data that was processed")

    # Approval information
    approval_required: bool = Field(default=False, description="Whether approval was required for this execution")

    approval_granted: bool = Field(default=False, description="Whether approval was granted (if required)")

    approval_details: dict[str, Any] = Field(default_factory=dict, description="Details about the approval process")

    @field_validator("workflow_name")
    @classmethod
    def validate_workflow_name(cls, v: str) -> str:
        """Validate that workflow name is not empty."""
        if not v or not v.strip():
            raise ValueError("Workflow name cannot be empty")
        return v.strip()

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of this workflow result.

        Returns:
            Dictionary containing key information about this result

        """
        summary = super().get_summary()
        summary.update(
            {
                "workflow_name": self.workflow_name,
                "checking_point_name": self.checking_point_name,
                "success": self.success,
                "execution_id": self.execution_id,
                "duration_ms": self.duration_ms,
                "actions_taken_count": len(self.actions_taken),
                "has_error": self.error_message is not None,
                "approval_required": self.approval_required,
                "approval_granted": self.approval_granted,
            }
        )
        return summary

    def is_successful(self) -> bool:
        """Check if the workflow execution was successful."""
        return self.success

    def has_actions(self) -> bool:
        """Check if any actions were taken."""
        return len(self.actions_taken) > 0

    def get_duration(self) -> timedelta | None:
        """Get the execution duration as a timedelta.

        Returns:
            Duration as timedelta, or None if not available

        """
        if self.duration_ms is not None:
            return timedelta(milliseconds=self.duration_ms)
        return None
