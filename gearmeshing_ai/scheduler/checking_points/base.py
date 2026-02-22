"""Base classes for checking point implementations.

This module provides the abstract base classes that all checking point implementations
must inherit from, ensuring consistent behavior and interface across the system.
"""

from abc import ABCMeta, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional, Dict, Type

from gearmeshing_ai.scheduler.models.checking_point import CheckResult
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType
from gearmeshing_ai.scheduler.models.workflow import AIAction, AIActionType


# Global registry for all checking point classes
_CHECKING_POINT_REGISTRY: Dict[str, Type["CheckingPoint"]] = {}


class CheckingPointMeta(ABCMeta):
    """Metaclass for automatic registration of checking point classes.
    
    When a CheckingPoint subclass is defined, this metaclass automatically
    registers it in the global registry using its 'name' attribute as the key.
    This enables dynamic discovery and instantiation of checking points without
    manual registration code.
    """

    def __new__(mcs, name: str, bases: tuple, namespace: dict, **kwargs):
        """Create a new checking point class and auto-register it.
        
        Args:
            name: Class name
            bases: Base classes
            namespace: Class namespace/attributes
            **kwargs: Additional keyword arguments
            
        Returns:
            The newly created class
        """
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        # Only register concrete checking point classes (not abstract ones)
        # Skip the base CheckingPoint class itself
        if bases and any(isinstance(base, CheckingPointMeta) for base in bases):
            # Get the checking point name
            cp_name = getattr(cls, "name", None)
            
            # Only register if it has a non-empty name and is not abstract
            if cp_name and not getattr(cls, "__abstractmethods__", None):
                _CHECKING_POINT_REGISTRY[cp_name] = cls

        return cls


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


class CheckingPoint(metaclass=CheckingPointMeta):
    """Abstract base class for all checking point implementations.

    Checking points are the core components that evaluate monitoring data and
    determine what actions should be taken. Each checking point is responsible
    for:

    1. Determining if it can handle a specific type of monitoring data
    2. Evaluating the data against its criteria
    3. Determining what actions should be taken based on the evaluation
    4. Providing AI workflow actions if needed
    
    All concrete subclasses are automatically registered in the global registry
    via the CheckingPointMeta metaclass.
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
    async def fetch_data(self, **kwargs) -> list[MonitoringData]:
        """Fetch data relevant to this checking point.

        Each checking point implements this to:
        - Use the parent's client property (access to initialized client)
        - Apply specific filters and parameters
        - Transform response data into MonitoringData objects
        - Handle pagination, rate limiting, etc.

        Args:
            **kwargs: Checking point specific parameters

        Returns:
            List of MonitoringData objects relevant to this checking point

        """
        pass

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

    async def fetch_and_evaluate(self, **kwargs) -> list[CheckResult]:
        """Complete workflow: fetch data and evaluate all items.

        This method orchestrates the complete checking point workflow:
        1. Fetch relevant data using child implementation
        2. Evaluate each data item
        3. Return all evaluation results

        Args:
            **kwargs: Parameters to pass to fetch_data()

        Returns:
            List of CheckResult objects from evaluating all fetched data

        """
        # Fetch relevant data using child implementation
        data_items = await self.fetch_data(**kwargs)

        # Evaluate each data item
        results = []
        for data_item in data_items:
            if self.can_handle(data_item):
                result = await self.evaluate(data_item)
                results.append(result)

        return results

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
    """Base class for ClickUp checking points with client initialization."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the ClickUp checking point.

        Args:
            config: Configuration dictionary

        """
        super().__init__(config)

        # ClickUp-specific configuration
        self.workspace_id = self.config.get("workspace_id")
        self.api_token = self.config.get("api_token")

        # Client will be initialized lazily through the property
        self._clickup_client = None

    async def _get_client(self):
        """Get the initialized ClickUp client with lazy loading."""
        if self._clickup_client is None:
            await self._setup_client()
        return self._clickup_client

    async def _setup_client(self) -> None:
        """Setup ClickUp client using clickup-mcp-server library."""
        from clickup_mcp import ClickUpAPIClientFactory

        # Use the ClickUp MCP server client factory
        ClickUpAPIClientFactory.reset()  # Reset to allow new instance
        self._clickup_client = ClickUpAPIClientFactory.create(
            api_token=self.api_token,
            timeout=self.config.get("timeout_seconds", 30),
            max_retries=self.config.get("max_retries", 3),
            rate_limit_requests_per_minute=self.config.get("rate_limit", 100),
        )

    def _can_handle_data_type(self, data_type: str) -> bool:
        """Check if this checking point can handle ClickUp task data."""
        return data_type == "clickup_task"

    async def get_workspace_tasks(
        self,
        list_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> list[dict]:
        """Get tasks from ClickUp workspace using MCP server client with proper data models.

        Args:
            list_id: ClickUp list ID to fetch tasks from
            status: Optional status filter
            priority: Optional priority filter

        Returns:
            List of task dictionaries

        """
        from clickup_mcp.models.dto.task import TaskListQuery

        client = await self._get_client()  # Lazy initialization happens here

        if not list_id:
            raise ValueError("list_id is required for task access")

        # Build query with proper data model
        query = TaskListQuery(limit=100, include_closed=True, page=0)

        # Use ClickUp MCP server client's task API with proper data models
        tasks = await client.task.list_in_list(list_id, query)

        # Apply additional filters if needed using typed data models
        filtered_tasks = []
        for task in tasks:
            # Filter by status using typed status info
            if status and task.status and task.status.status:
                if task.status.status.lower() != status.lower():
                    continue

            # Filter by priority using typed priority info
            if priority and task.priority and task.priority.priority:
                if task.priority.priority.lower() != priority.lower():
                    continue

            # Convert TaskResp to dict for monitoring data
            filtered_tasks.append(task.model_dump())

        return filtered_tasks

    def convert_to_monitoring_data(self, tasks: list[dict]) -> list[MonitoringData]:
        """Convert ClickUp tasks to MonitoringData objects.

        Args:
            tasks: List of task dictionaries

        Returns:
            List of MonitoringData objects

        """
        data_items = []
        for task in tasks:
            data_items.append(
                MonitoringData(
                    id=f"clickup_{task['id']}",
                    type=MonitoringDataType.CLICKUP_TASK,
                    source="clickup",
                    data=task,
                    timestamp=datetime.utcnow(),
                )
            )
        return data_items

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
    """Base class for Slack checking points with client initialization."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the Slack checking point.

        Args:
            config: Configuration dictionary

        """
        super().__init__(config)

        # Slack-specific configuration
        self.bot_token = self.config.get("bot_token")

        # Client will be initialized lazily through the property
        self._slack_client = None

    async def _get_client(self):
        """Get the initialized Slack client with lazy loading."""
        if self._slack_client is None:
            await self._setup_client()
        return self._slack_client

    async def _setup_client(self) -> None:
        """Setup Slack client using slack-mcp-server library."""
        from slack_mcp.client.manager import get_client_manager

        # Use the Slack MCP server client manager
        manager = get_client_manager()
        self._slack_client = manager.get_async_client(
            token=self.bot_token,
            use_retries=self.config.get("use_retries", True),
        )

    def _can_handle_data_type(self, data_type: str) -> bool:
        """Check if this checking point can handle Slack message data."""
        return data_type == "slack_message"

    async def get_channel_messages(
        self,
        channel: str,
        limit: int = 100,
        oldest: Optional[str] = None,
    ) -> list[dict]:
        """Get messages from a Slack channel using MCP server client with proper data models.

        Args:
            channel: Slack channel ID or name
            limit: Maximum number of messages to retrieve
            oldest: Optional timestamp to get messages after

        Returns:
            List of message dictionaries

        """
        from slack_mcp.mcp.model.input import SlackReadChannelMessagesInput

        client = await self._get_client()  # Lazy initialization happens here

        # Build input with proper data model
        input_params = SlackReadChannelMessagesInput(
            channel=channel,
            limit=limit,
            oldest=oldest,
        )

        # Use Slack MCP server client's conversations_history method
        # This returns a structured SlackChannelMessagesResponse data model
        response = await client.conversations_history(
            channel=input_params.channel,
            limit=input_params.limit,
            oldest=input_params.oldest,
        )

        # Return messages from the structured response
        # SlackChannelMessagesResponse has typed fields: ok, messages, has_more, etc.
        if response.ok and response.messages:
            return response.messages
        else:
            return []

    def convert_to_monitoring_data(self, messages: list[dict]) -> list[MonitoringData]:
        """Convert Slack messages to MonitoringData objects.

        Args:
            messages: List of message dictionaries

        Returns:
            List of MonitoringData objects

        """
        data_items = []
        for message in messages:
            data_items.append(
                MonitoringData(
                    id=f"slack_{message.get('ts', '')}",
                    type=MonitoringDataType.SLACK_MESSAGE,
                    source="slack",
                    data=message,
                    timestamp=datetime.utcnow(),
                )
            )
        return data_items

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


# ============================================================================
# Registry Utility Functions
# ============================================================================

def get_checking_point_class(name: str) -> Type[CheckingPoint]:
    """Get a checking point class by name from the registry.
    
    Args:
        name: Name of the checking point class
        
    Returns:
        The checking point class
        
    Raises:
        ValueError: If the checking point is not registered
    """
    if name not in _CHECKING_POINT_REGISTRY:
        available = list(_CHECKING_POINT_REGISTRY.keys())
        raise ValueError(
            f"Checking point '{name}' not found in registry. "
            f"Available: {available}"
        )
    return _CHECKING_POINT_REGISTRY[name]


def get_all_checking_point_classes() -> Dict[str, Type[CheckingPoint]]:
    """Get all registered checking point classes.
    
    Returns:
        Dictionary mapping checking point names to their classes
    """
    return _CHECKING_POINT_REGISTRY.copy()


def get_checking_point_classes_by_filter(**filters) -> Dict[str, Type[CheckingPoint]]:
    """Get checking point classes filtered by criteria.
    
    Supported filters:
    - name_contains: Filter by name substring (case-insensitive)
    - type_value: Filter by exact type value
    - type_contains: Filter by type substring (case-insensitive)
    - priority_min: Filter by minimum priority
    - priority_max: Filter by maximum priority
    - enabled: Filter by enabled status (True/False)
    
    Args:
        **filters: Filter criteria
        
    Returns:
        Dictionary of filtered checking point classes
        
    Example:
        # Get all urgent task checking points
        urgent_cps = get_checking_point_classes_by_filter(
            name_contains="urgent"
        )
        
        # Get high-priority checking points
        high_priority_cps = get_checking_point_classes_by_filter(
            priority_min=7
        )
        
        # Get ClickUp checking points
        clickup_cps = get_checking_point_classes_by_filter(
            type_contains="clickup"
        )
    """
    filtered = {}
    
    for cp_name, cp_class in _CHECKING_POINT_REGISTRY.items():
        match = True
        
        # Filter by name substring
        if 'name_contains' in filters:
            if filters['name_contains'].lower() not in cp_name.lower():
                match = False
        
        # Filter by exact type value
        if 'type_value' in filters and match:
            cp_type = cp_class.type.value if isinstance(cp_class.type, CheckingPointType) else cp_class.type
            if cp_type != filters['type_value']:
                match = False
        
        # Filter by type substring
        if 'type_contains' in filters and match:
            cp_type = cp_class.type.value if isinstance(cp_class.type, CheckingPointType) else cp_class.type
            if filters['type_contains'].lower() not in cp_type.lower():
                match = False
        
        # Filter by minimum priority
        if 'priority_min' in filters and match:
            if cp_class.priority < filters['priority_min']:
                match = False
        
        # Filter by maximum priority
        if 'priority_max' in filters and match:
            if cp_class.priority > filters['priority_max']:
                match = False
        
        # Filter by enabled status
        if 'enabled' in filters and match:
            if cp_class.enabled != filters['enabled']:
                match = False
        
        if match:
            filtered[cp_name] = cp_class
    
    return filtered


def get_checking_point_classes_by_type(cp_type: str | CheckingPointType) -> Dict[str, Type[CheckingPoint]]:
    """Get all checking point classes of a specific type.
    
    Args:
        cp_type: Checking point type (string or CheckingPointType enum)
        
    Returns:
        Dictionary of checking point classes of the specified type
    """
    if isinstance(cp_type, CheckingPointType):
        type_value = cp_type.value
    else:
        type_value = cp_type
    
    return get_checking_point_classes_by_filter(type_value=type_value)


def get_checking_point_count() -> int:
    """Get the total number of registered checking points.
    
    Returns:
        Number of registered checking point classes
    """
    return len(_CHECKING_POINT_REGISTRY)


def is_checking_point_registered(name: str) -> bool:
    """Check if a checking point is registered.
    
    Args:
        name: Name of the checking point
        
    Returns:
        True if registered, False otherwise
    """
    return name in _CHECKING_POINT_REGISTRY


def get_registry_summary() -> Dict[str, Any]:
    """Get a summary of the checking point registry.
    
    Returns:
        Dictionary containing registry summary information
    """
    type_counts = {}
    for cp_class in _CHECKING_POINT_REGISTRY.values():
        cp_type = cp_class.type.value if isinstance(cp_class.type, CheckingPointType) else str(cp_class.type)
        type_counts[cp_type] = type_counts.get(cp_type, 0) + 1
    
    return {
        "total_checking_points": len(_CHECKING_POINT_REGISTRY),
        "type_counts": type_counts,
        "checking_points": {
            name: {
                "name": name,
                "type": cp_class.type.value if isinstance(cp_class.type, CheckingPointType) else str(cp_class.type),
                "description": cp_class.description,
                "version": cp_class.version,
                "priority": cp_class.priority,
                "enabled": cp_class.enabled,
            }
            for name, cp_class in _CHECKING_POINT_REGISTRY.items()
        },
    }
