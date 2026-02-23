"""Urgent task checking point for ClickUp.

This checking point identifies urgent ClickUp tasks that require immediate
attention and triggers appropriate AI workflows for triage and action.
"""

from datetime import datetime, timedelta
from typing import Any

from gearmeshing_ai.scheduler.checking_points.base import CheckingPointType
from gearmeshing_ai.scheduler.models.checking_point import CheckResult, CheckResultType
from gearmeshing_ai.scheduler.models.monitoring import ClickUpTaskModel, MonitoringData
from gearmeshing_ai.scheduler.models.workflow import AIAction

from .base import ClickUpCheckingPoint


class UrgentTaskCheckingPoint(ClickUpCheckingPoint):
    """Checking point for detecting urgent ClickUp tasks.

    This checking point identifies tasks that are marked as urgent or have
    characteristics that indicate they need immediate attention, such as
    high priority, upcoming due dates, or critical keywords.
    """

    name = "clickup_urgent_task_cp"
    type = CheckingPointType.CLICKUP_URGENT_TASK_CP
    description = "Detects urgent ClickUp tasks that need immediate attention"
    version = "1.0.0"

    # Default configuration
    priority = 8  # High priority for urgent tasks
    stop_on_match = True  # Stop processing further checking points for urgent tasks

    # AI workflow configuration
    ai_workflow_enabled = True
    prompt_template_id = "clickup_urgent_task_triage"
    agent_role = "dev"
    timeout_seconds = 600
    approval_required = False

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the urgent task checking point.

        Args:
            config: Configuration dictionary

        """
        super().__init__(config)

        # Urgent task detection configuration
        self.urgent_keywords = self.config.get(
            "urgent_keywords",
            [
                "urgent",
                "critical",
                "emergency",
                "asap",
                "immediate",
                "priority",
                "production",
                "hotfix",
                "break",
                "down",
                "fail",
                "error",
            ],
        )

        self.priority_levels = self.config.get("priority_levels", ["urgent", "high"])
        self.due_date_threshold_hours = self.config.get("due_date_threshold_hours", 24)
        self.require_due_date = self.config.get("require_due_date", False)

        # Notification configuration
        self.notify_channel = self.config.get("notify_channel", "#alerts")
        self.notify_assignee = self.config.get("notify_assignee", True)
        self.create_follow_up = self.config.get("create_follow_up", True)

    async def fetch_data(self, list_ids: list[str] | None = None) -> list[MonitoringData[ClickUpTaskModel]]:
        """Fetch urgent tasks using parent's initialized client.

        This method implements the specific data fetching logic for urgent tasks:
        - Uses parent's get_workspace_tasks() method
        - Fetches tasks with high priority levels
        - Fetches tasks due soon
        - Applies urgent keyword filters

        Args:
            list_ids: Optional list of ClickUp list IDs to fetch from

        Returns:
            List of MonitoringData objects containing ClickUpTaskModel data

        """
        list_ids = list_ids or self.config.get("list_ids", [])
        if not list_ids:
            raise ValueError("list_ids must be provided for urgent task checking")

        all_urgent_tasks = []

        for list_id in list_ids:
            # Use parent's get_workspace_tasks method with initialized client
            high_priority_tasks = await self.get_workspace_tasks(
                list_id=list_id,
                priority="urgent",  # ClickUp API specific
            )
            all_urgent_tasks.extend(high_priority_tasks)

            # Fetch tasks due soon
            due_soon_tasks = await self.get_workspace_tasks(
                list_id=list_id,
                status="in_progress",  # Only active tasks
            )
            # Filter by due date locally
            due_soon_tasks = self._filter_tasks_due_soon(due_soon_tasks)
            all_urgent_tasks.extend(due_soon_tasks)

        # Convert to monitoring data using parent's utility with typed ClickUpTaskModel
        return self.convert_to_monitoring_data(all_urgent_tasks)

    def _filter_tasks_due_soon(self, tasks: list["TaskResp"]) -> list["TaskResp"]:
        """Filter tasks that are due within the threshold.

        Args:
            tasks: List of TaskResp objects from ClickUp API

        Returns:
            List of TaskResp objects due within the threshold

        """
        from clickup_mcp.models.dto.task import TaskResp

        threshold = datetime.utcnow() + timedelta(hours=self.due_date_threshold_hours)

        due_soon_tasks: list[TaskResp] = []
        for task in tasks:
            # TaskResp.due_date is in milliseconds (epoch time)
            if task.due_date:
                try:
                    # Convert milliseconds to seconds for datetime
                    due_date = datetime.fromtimestamp(task.due_date / 1000)
                    if due_date <= threshold:
                        due_soon_tasks.append(task)
                except (ValueError, OSError):
                    continue  # Skip invalid dates

        return due_soon_tasks

    async def evaluate(self, data: MonitoringData) -> CheckResult:
        """Evaluate ClickUp task data for urgency.

        Args:
            data: Monitoring data containing ClickUp task

        Returns:
            Check result indicating if task is urgent

        """
        start_time = datetime.utcnow()

        try:
            task_data = data.data
            task_name = task_data.get("name", "")
            task_description = task_data.get("description", "")
            task_priority = task_data.get("priority", "").lower()
            task_status = task_data.get("status", {}).get("status", "").lower()
            task_due_date = task_data.get("due_date", "")
            task_tags = [tag.lower() for tag in task_data.get("tags", [])]

            # Check if task is already completed
            if task_status in ["done", "completed", "closed"]:
                return CheckResult(
                    checking_point_name=self.name,
                    checking_point_type=self.type.value,
                    result_type=CheckResultType.NO_MATCH,
                    should_act=False,
                    reason="Task is already completed",
                    confidence=1.0,
                )

            # Calculate urgency score
            urgency_score = 0
            urgency_reasons = []

            # Check priority level
            if task_priority in self.priority_levels:
                urgency_score += 0.4
                urgency_reasons.append(f"High priority: {task_priority}")

            # Check urgent keywords in name and description
            text_content = f"{task_name} {task_description}".lower()
            keyword_matches = [kw for kw in self.urgent_keywords if kw in text_content]
            if keyword_matches:
                urgency_score += 0.3 * (len(keyword_matches) / len(self.urgent_keywords))
                urgency_reasons.append(f"Urgent keywords: {', '.join(keyword_matches)}")

            # Check tags for urgency indicators
            urgent_tags = [tag for tag in task_tags if tag in self.urgent_keywords]
            if urgent_tags:
                urgency_score += 0.2
                urgency_reasons.append(f"Urgent tags: {', '.join(urgent_tags)}")

            # Check due date proximity
            if task_due_date:
                try:
                    due_date = datetime.fromisoformat(task_due_date.replace("Z", "+00:00"))
                    hours_until_due = (due_date - datetime.utcnow()).total_seconds() / 3600

                    if hours_until_due <= self.due_date_threshold_hours:
                        urgency_score += 0.3
                        urgency_reasons.append(f"Due in {hours_until_due:.1f} hours")
                except (ValueError, AttributeError):
                    pass  # Invalid due date format
            elif self.require_due_date:
                urgency_score -= 0.1  # Penalize if due date is required but missing

            # Determine if task is urgent
            is_urgent = urgency_score >= 0.5
            confidence = min(urgency_score * 1.2, 1.0)  # Scale confidence

            if is_urgent:
                result = CheckResult(
                    checking_point_name=self.name,
                    checking_point_type=self.type.value,
                    result_type=CheckResultType.MATCH,
                    should_act=True,
                    confidence=confidence,
                    reason=f"Task identified as urgent: {'; '.join(urgency_reasons)}",
                    context={
                        "urgency_score": urgency_score,
                        "urgency_reasons": urgency_reasons,
                        "task_priority": task_priority,
                        "keyword_matches": keyword_matches,
                        "urgent_tags": urgent_tags,
                    },
                    suggested_actions=["triage_task", "notify_team"],
                )
            else:
                result = CheckResult(
                    checking_point_name=self.name,
                    checking_point_type=self.type.value,
                    result_type=CheckResultType.NO_MATCH,
                    should_act=False,
                    confidence=confidence,
                    reason=f"Task does not meet urgency criteria (score: {urgency_score:.2f})",
                    context={
                        "urgency_score": urgency_score,
                    },
                )

            # Set evaluation duration
            execution_time = datetime.utcnow() - start_time
            result.evaluation_duration_ms = int(execution_time.total_seconds() * 1000)

            return result

        except Exception as e:
            return CheckResult(
                checking_point_name=self.name,
                checking_point_type=self.type.value,
                result_type=CheckResultType.ERROR,
                should_act=False,
                confidence=0.0,
                error_message=str(e),
            )

    def get_actions(self, data: MonitoringData, result: CheckResult) -> list[dict[str, Any]]:
        """Get immediate actions for urgent task.

        Args:
            data: Monitoring data
            result: Check result

        Returns:
            List of immediate actions

        """
        actions = []
        task_data = data.data
        task_id = task_data.get("id")
        task_name = task_data.get("name", "")

        # Add urgent tag to task
        actions.append(
            {
                "type": "status_update",
                "name": "add_urgent_tag",
                "parameters": {
                    "system": "clickup",
                    "entity_id": task_id,
                    "new_status": task_data.get("status", {}).get("status", ""),
                    "reason": "Marked as urgent by automated monitoring",
                    "add_tags": ["urgent"],
                },
            }
        )

        # Send notification to channel
        if self.notify_channel:
            actions.append(
                {
                    "type": "notification",
                    "name": "notify_urgent_task",
                    "parameters": {
                        "notification_type": "slack",
                        "recipient": self.notify_channel,
                        "subject": f"🚨 Urgent Task Detected: {task_name}",
                        "message": f"Urgent task '{task_name}' (ID: {task_id}) requires immediate attention. Reason: {result.reason}",
                    },
                }
            )

        # Notify assignee if exists
        assignees = task_data.get("assignees", {})
        if self.notify_assignee and assignees:
            assignee_id = list(assignees.keys())[0] if assignees else None
            if assignee_id:
                actions.append(
                    {
                        "type": "notification",
                        "name": "notify_assignee",
                        "parameters": {
                            "notification_type": "email",
                            "recipient": f"user_{assignee_id}@company.com",
                            "subject": f"Urgent Task Assigned: {task_name}",
                            "message": f"You have been assigned an urgent task '{task_name}' that requires immediate attention.",
                        },
                    }
                )

        return actions

    def get_after_process(self, data: MonitoringData, result: CheckResult) -> list[AIAction]:
        """Get AI workflow actions for urgent task triage.

        Args:
            data: Monitoring data
            result: Check result

        Returns:
            List of AI workflow actions

        """
        if not self.ai_workflow_enabled or not result.should_act:
            return []

        # Create AI triage workflow action
        ai_action = self._create_ai_action(data, result)

        # Add specific parameters for urgent task triage
        ai_action.parameters.update(
            {
                "urgency_level": "high" if result.confidence >= 0.8 else "medium",
                "urgency_score": result.context.get("urgency_score", 0.0),
                "urgency_reasons": result.context.get("urgency_reasons", []),
                "create_follow_up": self.create_follow_up,
            }
        )

        return [ai_action]
