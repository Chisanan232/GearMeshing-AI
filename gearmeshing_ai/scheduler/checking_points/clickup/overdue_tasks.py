"""Overdue task checking point for ClickUp.

This checking point identifies overdue ClickUp tasks and triggers escalation
workflows to ensure they receive proper attention and resolution.
"""

from datetime import datetime
from typing import Any

from gearmeshing_ai.scheduler.checking_points.base import CheckingPointType, ClickUpCheckingPoint
from gearmeshing_ai.scheduler.models.checking_point import CheckResult, CheckResultType
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData
from gearmeshing_ai.scheduler.models.workflow import AIAction


class OverdueTaskCheckingPoint(ClickUpCheckingPoint):
    """Checking point for detecting overdue ClickUp tasks.

    This checking point identifies tasks that are past their due date and
    triggers appropriate escalation workflows based on how overdue they are
    and their impact on the project.
    """

    name = "clickup_overdue_task_cp"
    type = CheckingPointType.CLICKUP_OVERDUE_TASK_CP
    description = "Detects overdue ClickUp tasks and triggers escalation"
    version = "1.0.0"

    # Default configuration
    priority = 7  # High priority for overdue tasks
    stop_on_match = False  # Don't stop processing, might have other issues

    # AI workflow configuration
    ai_workflow_enabled = True
    prompt_template_id = "clickup_overdue_task_escalation"
    agent_role = "sre"
    timeout_seconds = 900
    approval_required = False

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the overdue task checking point.

        Args:
            config: Configuration dictionary

        """
        super().__init__(config)

        # Overdue detection configuration
        self.overdue_threshold_days = self.config.get("overdue_threshold_days", 1)
        self.critical_threshold_days = self.config.get("critical_threshold_days", 7)
        self.ignore_completed = self.config.get("ignore_completed", True)

        # Escalation configuration
        self.escalation_levels = self.config.get(
            "escalation_levels",
            {
                1: "team_lead",  # 1-3 days overdue
                3: "manager",  # 3-7 days overdue
                7: "director",  # 7+ days overdue
            },
        )

        # Notification configuration
        self.notify_assignee = self.config.get("notify_assignee", True)
        self.notify_project_lead = self.config.get("notify_project_lead", True)
        self.create_incident = self.config.get("create_incident", False)

        # Priority keywords for impact assessment
        self.impact_keywords = self.config.get(
            "impact_keywords",
            [
                "production",
                "customer",
                "release",
                "deadline",
                "milestone",
                "critical",
                "blocking",
                "security",
                "compliance",
            ],
        )

    async def fetch_data(self, list_ids: list[str] | None = None) -> list[MonitoringData]:
        """Fetch overdue tasks - different logic than urgent tasks.

        This method implements specific logic for overdue tasks:
        - Uses parent's get_workspace_tasks() method
        - Fetches ALL tasks (not just high priority)
        - Filters by due date locally
        - Includes completed tasks that were overdue when completed

        Args:
            list_ids: Optional list of ClickUp list IDs to fetch from

        Returns:
            List of MonitoringData objects containing overdue tasks

        """
        list_ids = list_ids or self.config.get("list_ids", [])
        if not list_ids:
            raise ValueError("list_ids must be provided for overdue task checking")

        all_tasks = []

        for list_id in list_ids:
            # Use parent's get_workspace_tasks method (different parameters)
            tasks = await self.get_workspace_tasks(list_id=list_id)
            all_tasks.extend(tasks)

        # Filter overdue tasks locally (different filtering logic)
        overdue_tasks = self._filter_overdue_tasks(all_tasks)

        # Convert to monitoring data using parent's utility
        return self.convert_to_monitoring_data(overdue_tasks)

    def _filter_overdue_tasks(self, tasks: list[dict]) -> list[dict]:
        """Filter tasks that are overdue (different from due-soon logic).

        Args:
            tasks: List of task dictionaries

        Returns:
            List of overdue tasks

        """
        now = datetime.utcnow()
        overdue_tasks = []

        for task in tasks:
            due_date_str = task.get("due_date")
            if not due_date_str:
                continue

            try:
                due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
                if due_date < now:
                    overdue_tasks.append(task)
            except ValueError:
                continue

        return overdue_tasks

    async def evaluate(self, data: MonitoringData) -> CheckResult:
        """Evaluate ClickUp task for overdue status.

        Args:
            data: Monitoring data containing ClickUp task

        Returns:
            Check result indicating if task is overdue

        """
        start_time = datetime.utcnow()

        try:
            task_data = data.data
            task_id = task_data.get("id")
            task_name = task_data.get("name", "")
            task_description = task_data.get("description", "")
            task_status = task_data.get("status", {}).get("status", "").lower()
            task_due_date = task_data.get("due_date", "")
            task_tags = [tag.lower() for tag in task_data.get("tags", [])]
            task_priority = task_data.get("priority", "").lower()

            # Check if task should be ignored
            if self.ignore_completed and task_status in ["done", "completed", "closed"]:
                return CheckResult(
                    checking_point_name=self.name,
                    checking_point_type=self.type.value,
                    result_type=CheckResultType.NO_MATCH,
                    should_act=False,
                    reason="Task is completed, ignoring overdue status",
                    confidence=1.0,
                )

            # Check if task has a due date
            if not task_due_date:
                return CheckResult(
                    checking_point_name=self.name,
                    checking_point_type=self.type.value,
                    result_type=CheckResultType.NO_MATCH,
                    should_act=False,
                    reason="Task has no due date",
                    confidence=1.0,
                )

            # Calculate days overdue
            try:
                due_date = datetime.fromisoformat(task_due_date.replace("Z", "+00:00"))
                days_overdue = (datetime.utcnow() - due_date).days
            except (ValueError, AttributeError):
                return CheckResult(
                    checking_point_name=self.name,
                    checking_point_type=self.type.value,
                    result_type=CheckResultType.ERROR,
                    should_act=False,
                    confidence=0.0,
                    error_message=f"Invalid due date format: {task_due_date}",
                )

            # Check if task is overdue
            if days_overdue < self.overdue_threshold_days:
                return CheckResult(
                    checking_point_name=self.name,
                    checking_point_type=self.type.value,
                    result_type=CheckResultType.NO_MATCH,
                    should_act=False,
                    reason=f"Task is not overdue (due in {abs(days_overdue)} days)",
                    confidence=1.0,
                )

            # Calculate impact score
            impact_score = 0
            impact_factors = []

            # Base impact from days overdue
            if days_overdue >= self.critical_threshold_days:
                impact_score += 0.5
                impact_factors.append(f"Critical: {days_overdue} days overdue")
            elif days_overdue >= 3:
                impact_score += 0.3
                impact_factors.append(f"High: {days_overdue} days overdue")
            else:
                impact_score += 0.1
                impact_factors.append(f"Medium: {days_overdue} days overdue")

            # Check priority
            if task_priority in ["urgent", "high"]:
                impact_score += 0.2
                impact_factors.append(f"High priority: {task_priority}")

            # Check impact keywords
            text_content = f"{task_name} {task_description}".lower()
            impact_keywords_found = [kw for kw in self.impact_keywords if kw in text_content]
            if impact_keywords_found:
                impact_score += 0.3 * (len(impact_keywords_found) / len(self.impact_keywords))
                impact_factors.append(f"Impact keywords: {', '.join(impact_keywords_found)}")

            # Determine escalation level
            escalation_level = "team_lead"
            for threshold_days, level in self.escalation_levels.items():
                if days_overdue >= threshold_days:
                    escalation_level = level

            # Determine if critical escalation
            is_critical_escalation = days_overdue >= self.critical_threshold_days or impact_score >= 0.7

            # Calculate confidence
            confidence = min(impact_score * 1.3, 1.0)

            result = CheckResult(
                checking_point_name=self.name,
                checking_point_type=self.type.value,
                result_type=CheckResultType.MATCH,
                should_act=True,
                confidence=confidence,
                reason=f"Task is {days_overdue} days overdue, impact score: {impact_score:.2f}",
                context={
                    "days_overdue": days_overdue,
                    "impact_score": impact_score,
                    "impact_factors": impact_factors,
                    "escalation_level": escalation_level,
                    "is_critical_escalation": is_critical_escalation,
                    "task_priority": task_priority,
                    "impact_keywords_found": impact_keywords_found,
                },
                suggested_actions=["escalate_task", "notify_stakeholders"],
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
        """Get immediate actions for overdue task.

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
        days_overdue = result.context.get("days_overdue", 0)
        escalation_level = result.context.get("escalation_level", "team_lead")
        is_critical = result.context.get("is_critical_escalation", False)

        # Add overdue tag
        actions.append(
            {
                "type": "status_update",
                "name": "add_overdue_tag",
                "parameters": {
                    "system": "clickup",
                    "entity_id": task_id,
                    "new_status": task_data.get("status", {}).get("status", ""),
                    "reason": f"Task marked as overdue ({days_overdue} days)",
                    "add_tags": ["overdue"],
                },
            }
        )

        # Notify assignee
        assignees = task_data.get("assignees", {})
        if self.notify_assignee and assignees:
            assignee_id = list(assignees.keys())[0] if assignees else None
            if assignee_id:
                urgency = "CRITICAL" if is_critical else "HIGH"
                actions.append(
                    {
                        "type": "notification",
                        "name": "notify_assignee_overdue",
                        "parameters": {
                            "notification_type": "email",
                            "recipient": f"user_{assignee_id}@company.com",
                            "subject": f"[{urgency}] Overdue Task: {task_name}",
                            "message": f"Your task '{task_name}' is {days_overdue} days overdue. Please provide an update on the status.",
                        },
                    }
                )

        # Notify project lead
        if self.notify_project_lead:
            actions.append(
                {
                    "type": "notification",
                    "name": "notify_project_lead",
                    "parameters": {
                        "notification_type": "slack",
                        "recipient": "#project-leads",
                        "subject": f"Task Escalation: {task_name}",
                        "message": f"Task '{task_name}' (ID: {task_id}) is {days_overdue} days overdue and has been escalated to {escalation_level}.",
                    },
                }
            )

        # Create incident for critical escalations
        if is_critical and self.create_incident:
            actions.append(
                {
                    "type": "api_call",
                    "name": "create_incident",
                    "parameters": {
                        "url": "https://api.company.com/incidents",
                        "method": "POST",
                        "headers": {"Authorization": "Bearer INCIDENT_API_KEY"},
                        "data": {
                            "title": f"Critical Overdue Task: {task_name}",
                            "description": f"Task '{task_name}' is {days_overdue} days overdue and requires immediate attention.",
                            "severity": "high",
                            "task_id": task_id,
                            "escalation_level": escalation_level,
                        },
                    },
                }
            )

        return actions

    def get_after_process(self, data: MonitoringData, result: CheckResult) -> list[AIAction]:
        """Get AI workflow actions for overdue task escalation.

        Args:
            data: Monitoring data
            result: Check result

        Returns:
            List of AI workflow actions

        """
        if not self.ai_workflow_enabled or not result.should_act:
            return []

        # Create AI escalation workflow action
        ai_action = self._create_ai_action(data, result)

        # Add specific parameters for overdue task escalation
        ai_action.parameters.update(
            {
                "days_overdue": result.context.get("days_overdue", 0),
                "impact_score": result.context.get("impact_score", 0.0),
                "impact_factors": result.context.get("impact_factors", []),
                "escalation_level": result.context.get("escalation_level", "team_lead"),
                "is_critical_escalation": result.context.get("is_critical_escalation", False),
                "create_incident": self.create_incident,
            }
        )

        # Set higher timeout for complex escalation analysis
        if result.context.get("is_critical_escalation", False):
            ai_action.timeout_seconds = 1200  # 20 minutes for critical cases

        return [ai_action]
