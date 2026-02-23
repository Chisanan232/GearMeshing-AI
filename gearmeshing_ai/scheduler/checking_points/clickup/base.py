from abc import ABC
from datetime import datetime
from typing import Any

from clickup_mcp.models.dto.task import TaskListQuery, TaskResp

from gearmeshing_ai.scheduler.checking_points.base import CheckingPoint
from gearmeshing_ai.scheduler.models.checking_point import CheckResult
from gearmeshing_ai.scheduler.models.monitoring import ClickUpTaskModel, MonitoringData, MonitoringDataType


class ClickUpCheckingPoint(CheckingPoint, ABC):
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
        list_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
    ) -> list[TaskResp]:
        """Get tasks from ClickUp workspace using MCP server client with proper data models.

        Args:
            list_id: ClickUp list ID to fetch tasks from
            status: Optional status filter
            priority: Optional priority filter

        Returns:
            List of TaskResp objects containing task data with proper typing

        """
        client = await self._get_client()  # Lazy initialization happens here

        if not list_id:
            raise ValueError("list_id is required for task access")

        # Build query with proper data model
        query = TaskListQuery(limit=100, include_closed=True, page=0)

        # Use ClickUp MCP server client's task API with proper data models
        tasks = await client.task.list_in_list(list_id, query)

        # Apply additional filters if needed using typed data models
        filtered_tasks: list[TaskResp] = []
        for task in tasks:
            # Filter by status using typed status info
            if status and task.status and task.status.status:
                if task.status.status.lower() != status.lower():
                    continue

            # Filter by priority using typed priority info
            if priority and task.priority and task.priority.priority:
                if task.priority.priority.lower() != priority.lower():
                    continue

            # Keep TaskResp objects for type safety and clarity
            filtered_tasks.append(task)

        return filtered_tasks

    def convert_to_monitoring_data(self, tasks: list[TaskResp]) -> list[MonitoringData[ClickUpTaskModel]]:
        """Convert ClickUp tasks to MonitoringData objects with typed task models.

        Args:
            tasks: List of TaskResp objects from ClickUp API

        Returns:
            List of MonitoringData objects containing ClickUpTaskModel data

        """
        data_items: list[MonitoringData[ClickUpTaskModel]] = []
        for task in tasks:
            # Convert TaskResp to ClickUpTaskModel for type-safe data handling
            task_model = ClickUpTaskModel.from_task_resp(task)
            data_items.append(
                MonitoringData(
                    id=f"clickup_{task.id}",
                    type=MonitoringDataType.CLICKUP_TASK,
                    source="clickup",
                    data=task_model,
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
