"""Base classes for checking point implementations.

This module provides the abstract base classes that all checking point implementations
must inherit from, ensuring consistent behavior and interface across the system.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from gearmeshing_ai.scheduler.models.checking_point import CheckResult
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData
from gearmeshing_ai.scheduler.models.workflow import AIAction, AIActionType


class CheckingPointType(str, Enum):
    """Types of checking points available in the system."""

    CLICKUP_URGENT_TASK_CP = "clickup_urgent_task_cp"
    CLICKUP_OVERDUE_TASK_CP = "clickup_overdue_task_cp"
    CLICKUP_UNASSIGNED_TASK_CP = "clickup_unassigned_task_cp"
    CLICKUP_SMART_ASSIGNMENT_CP = "clickup_smart_assignment_cp"

    SLACK_BOT_MENTION_CP = "slack_bot_mention_cp"
    SLACK_HELP_REQUEST_CP = "slack_help_request_cp"
    SLACK_VIP_USER_CP = "slack_vip_user_cp"

    EMAIL_ALERT_CP = "email_alert_cp"

    CUSTOM_CP = "custom_cp"

    @classmethod
    def get_all_values(cls) -> list[str]:
        """Get all enum values as strings."""
        return [member.value for member in cls]

    @classmethod
    def get_clickup_types(cls) -> list[str]:
        """Get all ClickUp checking point types."""
        return [
            cls.CLICKUP_URGENT_TASK_CP.value,
            cls.CLICKUP_OVERDUE_TASK_CP.value,
            cls.CLICKUP_UNASSIGNED_TASK_CP.value,
            cls.CLICKUP_SMART_ASSIGNMENT_CP.value,
        ]

    @classmethod
    def get_slack_types(cls) -> list[str]:
        """Get all Slack checking point types."""
        return [
            cls.SLACK_BOT_MENTION_CP.value,
            cls.SLACK_HELP_REQUEST_CP.value,
            cls.SLACK_VIP_USER_CP.value,
        ]

    @classmethod
    def get_email_types(cls) -> list[str]:
        """Get all email checking point types."""
        return [cls.EMAIL_ALERT_CP.value]

    @classmethod
    def get_custom_types(cls) -> list[str]:
        """Get all custom checking point types."""
        return [cls.CUSTOM_CP.value]


class CheckingPoint(ABC):
    """Abstract base class for all checking point implementations.

    Checking points are the core components that evaluate monitoring data and
    determine what actions should be taken. Each checking point is responsible
    for:

    1. Determining if it can handle a specific type of monitoring data
    2. Evaluating the data against its criteria
    3. Determining what actions should be taken based on the evaluation
    4. Providing AI workflow actions if needed
    """

    # Class attributes that must be defined by subclasses
    name: str = ""
    type: CheckingPointType = CheckingPointType.CUSTOM_CP
    description: str = ""
    version: str = "1.0.0"

    # Configuration attributes
    enabled: bool = True
    priority: int = 5  # 1=lowest, 10=highest
    stop_on_match: bool = False  # Stop processing further checking points if this matches

    # AI workflow configuration
    ai_workflow_enabled: bool = True
    prompt_template_id: str | None = None
    agent_role: str | None = None
    timeout_seconds: int = 600
    approval_required: bool = False
    approval_timeout_seconds: int = 3600

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the checking point.

        Args:
            config: Configuration dictionary for this checking point

        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", self.enabled)
        self.priority = self.config.get("priority", self.priority)
        self.stop_on_match = self.config.get("stop_on_match", self.stop_on_match)

        # AI workflow configuration
        self.ai_workflow_enabled = self.config.get("ai_workflow_enabled", self.ai_workflow_enabled)
        self.prompt_template_id = self.config.get("prompt_template_id", self.prompt_template_id)
        self.agent_role = self.config.get("agent_role", self.agent_role)
        self.timeout_seconds = self.config.get("timeout_seconds", self.timeout_seconds)
        self.approval_required = self.config.get("approval_required", self.approval_required)
        self.approval_timeout_seconds = self.config.get("approval_timeout_seconds", self.approval_timeout_seconds)

    @abstractmethod
    async def evaluate(self, data: MonitoringData) -> CheckResult:
        """Evaluate monitoring data against this checking point's criteria.

        This is the main method that checking points must implement. It should
        evaluate the provided data and return a CheckResult indicating whether
        the checking point matched and what actions should be taken.

        Args:
            data: Monitoring data to evaluate

        Returns:
            CheckResult with evaluation outcome

        """
        pass

    def can_handle(self, data: MonitoringData) -> bool:
        """Check if this checking point can handle the given monitoring data.

        This method allows checking points to filter data they're interested in
        before performing expensive evaluation operations.

        Args:
            data: Monitoring data to check

        Returns:
            True if this checking point can handle the data, False otherwise

        """
        if not self.enabled:
            return False

        # Default implementation checks if the checking point type matches the data type
        return self._can_handle_data_type(data.type)

    def _can_handle_data_type(self, data_type: str) -> bool:
        """Check if this checking point can handle the given data type.

        Args:
            data_type: Monitoring data type

        Returns:
            True if this checking point can handle the data type

        """
        # This can be overridden by subclasses for more specific logic
        return True

    def get_actions(self, data: MonitoringData, result: CheckResult) -> list[dict[str, Any]]:
        """Get immediate actions to take based on the evaluation result.

        This method returns a list of immediate actions that should be taken
        without involving AI workflows. These are typically simple actions
        like sending notifications or updating status.

        Args:
            data: Monitoring data that was evaluated
            result: Evaluation result

        Returns:
            List of action dictionaries

        """
        # Default implementation returns no immediate actions
        return []

    def get_after_process(self, data: MonitoringData, result: CheckResult) -> list[AIAction]:
        """Get AI workflow actions to take after processing.

        This method returns a list of AI workflow actions that should be taken
        after the immediate actions. These typically involve AI-powered decision
        making and complex workflows.

        Args:
            data: Monitoring data that was evaluated
            result: Evaluation result

        Returns:
            List of AI workflow actions

        """
        if not self.ai_workflow_enabled or not result.should_act:
            return []

        # Default implementation creates a basic AI action
        return [self._create_ai_action(data, result)]

    def _create_ai_action(self, data: MonitoringData, result: CheckResult) -> AIAction:
        """Create an AI action for this checking point.

        Args:
            data: Monitoring data
            result: Evaluation result

        Returns:
            AI action instance

        """
        action_name = f"{self.name}_workflow"
        workflow_name = f"{self.type}_workflow"

        return AIAction(
            name=action_name,
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name=workflow_name,
            checking_point_name=self.name,
            timeout_seconds=self.timeout_seconds,
            prompt_template_id=self.prompt_template_id,
            agent_role=self.agent_role,
            approval_required=self.approval_required,
            approval_timeout_seconds=self.approval_timeout_seconds,
            priority=self.priority,
            parameters={
                "data": data.model_dump(),
                "result": result.model_dump(),
                "config": self.config,
            },
            prompt_variables=self._get_prompt_variables(data, result),
        )

    def _get_prompt_variables(self, data: MonitoringData, result: CheckResult) -> dict[str, Any]:
        """Get variables for prompt template substitution.

        Args:
            data: Monitoring data
            result: Evaluation result

        Returns:
            Dictionary of prompt variables

        """
        return {
            "checking_point_name": self.name,
            "checking_point_type": self.type.value,
            "checking_point_reason": result.reason,
            "confidence": result.confidence,
            "data": data.data,
            "data_id": data.id,
            "data_source": data.source,
            "data_timestamp": data.timestamp.isoformat(),
        }

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of this checking point.

        Returns:
            Dictionary containing key information about this checking point

        """
        return {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "version": self.version,
            "enabled": self.enabled,
            "priority": self.priority,
            "stop_on_match": self.stop_on_match,
            "ai_workflow_enabled": self.ai_workflow_enabled,
            "prompt_template_id": self.prompt_template_id,
            "agent_role": self.agent_role,
            "timeout_seconds": self.timeout_seconds,
            "approval_required": self.approval_required,
        }

    def validate_config(self) -> list[str]:
        """Validate the checking point configuration.

        Returns:
            List of validation error messages, empty if valid

        """
        errors = []

        if not self.name:
            errors.append("Checking point name cannot be empty")

        if not self.type:
            errors.append("Checking point type cannot be empty")

        if self.timeout_seconds <= 0:
            errors.append("Timeout seconds must be positive")

        if self.priority < 1 or self.priority > 10:
            errors.append("Priority must be between 1 and 10")

        return errors

    def __str__(self) -> str:
        """String representation of this checking point."""
        return f"{self.name} ({self.type.value})"

    def __repr__(self) -> str:
        """Detailed string representation of this checking point."""
        return (
            f"{self.__class__.__name__}(name='{self.name}', type='{self.type.value}', "
            f"enabled={self.enabled}, priority={self.priority})"
        )


class ClickUpCheckingPoint(CheckingPoint):
    """Base class for ClickUp checking points."""

    def _can_handle_data_type(self, data_type: str) -> bool:
        """Check if this checking point can handle ClickUp task data."""
        return data_type == "clickup_task"

    def _get_prompt_variables(self, data: MonitoringData, result: CheckResult) -> dict[str, Any]:
        """Get ClickUp-specific prompt variables."""
        variables = super()._get_prompt_variables(data, result)

        # Add ClickUp-specific variables
        task_data = data.data
        variables.update(
            {
                "task_id": task_data.get("id"),
                "task_name": task_data.get("name"),
                "task_description": task_data.get("description", ""),
                "task_priority": task_data.get("priority", ""),
                "task_status": task_data.get("status", {}).get("status", ""),
                "task_assignee": task_data.get("assignees", {}),
                "task_due_date": task_data.get("due_date", ""),
                "task_tags": task_data.get("tags", []),
                "task_custom_fields": task_data.get("custom_fields", {}),
            }
        )

        return variables


class SlackCheckingPoint(CheckingPoint):
    """Base class for Slack checking points."""

    def _can_handle_data_type(self, data_type: str) -> bool:
        """Check if this checking point can handle Slack message data."""
        return data_type == "slack_message"

    def _get_prompt_variables(self, data: MonitoringData, result: CheckResult) -> dict[str, Any]:
        """Get Slack-specific prompt variables."""
        variables = super()._get_prompt_variables(data, result)

        # Add Slack-specific variables
        message_data = data.data
        variables.update(
            {
                "user_name": message_data.get("user"),
                "channel": message_data.get("channel"),
                "message_text": message_data.get("text", ""),
                "thread_ts": message_data.get("thread_ts"),
                "timestamp": message_data.get("ts"),
                "mentions": message_data.get("mentions", []),
                "reactions": message_data.get("reactions", []),
            }
        )

        return variables


class EmailCheckingPoint(CheckingPoint):
    """Base class for email checking points."""

    def _can_handle_data_type(self, data_type: str) -> bool:
        """Check if this checking point can handle email alert data."""
        return data_type == "email_alert"

    def _get_prompt_variables(self, data: MonitoringData, result: CheckResult) -> dict[str, Any]:
        """Get email-specific prompt variables."""
        variables = super()._get_prompt_variables(data, result)

        # Add email-specific variables
        email_data = data.data
        variables.update(
            {
                "sender": email_data.get("from"),
                "subject": email_data.get("subject", ""),
                "body": email_data.get("body", ""),
                "priority": email_data.get("priority", ""),
                "recipients": email_data.get("recipients", []),
                "attachments": email_data.get("attachments", []),
            }
        )

        return variables


class CustomCheckingPoint(CheckingPoint):
    """Base class for custom checking points."""

    def _can_handle_data_type(self, data_type: str) -> bool:
        """Custom checking points can handle any data type by default."""
        return True
