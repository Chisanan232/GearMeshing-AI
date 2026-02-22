"""Smart assignment checking point for ClickUp.

This checking point identifies unassigned high-priority tasks and uses AI
to make intelligent assignment recommendations based on team skills, workload,
and task requirements.
"""

from datetime import datetime
from typing import Any

from gearmeshing_ai.scheduler.checking_points.base import CheckingPointType, ClickUpCheckingPoint
from gearmeshing_ai.scheduler.models.checking_point import CheckResult, CheckResultType
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData
from gearmeshing_ai.scheduler.models.workflow import AIAction


class SmartAssignmentCheckingPoint(ClickUpCheckingPoint):
    """Checking point for smart assignment of unassigned tasks.

    This checking point identifies unassigned tasks, particularly high-priority
    ones, and uses AI to recommend optimal assignments based on team member
    skills, current workload, and task requirements.
    """

    name = "clickup_smart_assignment_cp"
    type = CheckingPointType.CLICKUP_SMART_ASSIGNMENT_CP
    description = "Intelligently assigns unassigned high-priority tasks"
    version = "1.0.0"

    # Default configuration
    priority = 6  # Medium-high priority for assignment
    stop_on_match = False  # Don't stop processing

    # AI workflow configuration
    ai_workflow_enabled = True
    prompt_template_id = "clickup_smart_assignment"
    agent_role = "dev"
    timeout_seconds = 600
    approval_required = True  # Require approval for assignments

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the smart assignment checking point.

        Args:
            config: Configuration dictionary

        """
        super().__init__(config)

        # Assignment criteria configuration
        self.priority_thresholds = self.config.get("priority_thresholds", ["high", "urgent"])
        self.ignore_statuses = self.config.get("ignore_statuses", ["done", "completed", "closed"])
        self.max_unassigned_age_hours = self.config.get("max_unassigned_age_hours", 24)
        self.require_tags = self.config.get("require_tags", [])
        self.exclude_tags = self.config.get("exclude_tags", ["blocked", "waiting"])

        # Team configuration
        self.team_members = self.config.get(
            "team_members",
            [
                {"id": "dev_1", "name": "Senior Developer", "skills": ["backend", "api", "database"], "max_tasks": 5},
                {"id": "dev_2", "name": "Frontend Developer", "skills": ["frontend", "ui", "react"], "max_tasks": 6},
                {
                    "id": "dev_3",
                    "name": "Full Stack Developer",
                    "skills": ["backend", "frontend", "api"],
                    "max_tasks": 4,
                },
                {
                    "id": "dev_4",
                    "name": "DevOps Engineer",
                    "skills": ["devops", "infrastructure", "deployment"],
                    "max_tasks": 7,
                },
            ],
        )

        # Assignment rules
        self.assignment_rules = self.config.get(
            "assignment_rules",
            {
                "backend_tasks": ["dev_1", "dev_3"],
                "frontend_tasks": ["dev_2", "dev_3"],
                "devops_tasks": ["dev_4"],
                "urgent_tasks": ["dev_1", "dev_3"],  # More experienced for urgent tasks
            },
        )

        self.default_assignee = self.config.get("default_assignee", "dev_1")
        self.auto_assign = self.config.get("auto_assign", False)  # Require approval by default

        # Notification configuration
        self.notify_new_assignee = self.config.get("notify_new_assignee", True)
        self.notify_team_lead = self.config.get("notify_team_lead", True)

    async def fetch_data(self, list_ids: list[str] | None = None) -> list[MonitoringData[dict[str, Any]]]:
        """Fetch unassigned tasks from ClickUp workspace.

        This method fetches unassigned high-priority tasks that need smart assignment.
        It uses the parent's initialized client to retrieve tasks from specified lists.

        Args:
            list_ids: Optional list of ClickUp list IDs to fetch tasks from

        Returns:
            List of MonitoringData objects containing unassigned tasks

        """
        try:
            # Get tasks from workspace (uses parent's client)
            tasks = await self.get_workspace_tasks(list_id=None, status=None, priority=None)

            # Filter for unassigned tasks (TaskResp objects have assignees as a list)
            unassigned_tasks = [task for task in tasks if not task.assignees]

            # Convert to MonitoringData
            return self.convert_to_monitoring_data(unassigned_tasks)

        except Exception as e:
            self.logger.error(f"Error fetching unassigned tasks: {e}")
            return []

    async def evaluate(self, data: MonitoringData) -> CheckResult:
        """Evaluate ClickUp task for assignment needs.

        Args:
            data: Monitoring data containing ClickUp task

        Returns:
            Check result indicating if task needs assignment

        """
        start_time = datetime.utcnow()

        try:
            task_data = data.data
            task_id = task_data.get("id")
            task_name = task_data.get("name", "")
            task_description = task_data.get("description", "")
            task_priority = task_data.get("priority", "").lower()
            task_status = task_data.get("status", {}).get("status", "").lower()
            task_tags = [tag.lower() for tag in task_data.get("tags", [])]
            task_created_date = task_data.get("date_created", "")
            assignees = task_data.get("assignees", {})

            # Check if task should be ignored
            if task_status in self.ignore_statuses:
                return CheckResult(
                    checking_point_name=self.name,
                    checking_point_type=self.type.value,
                    result_type=CheckResultType.NO_MATCH,
                    should_act=False,
                    reason=f"Task status '{task_status}' is ignored",
                    confidence=1.0,
                )

            # Check if task is already assigned
            if assignees:
                return CheckResult(
                    checking_point_name=self.name,
                    checking_point_type=self.type.value,
                    result_type=CheckResultType.NO_MATCH,
                    should_act=False,
                    reason="Task is already assigned",
                    confidence=1.0,
                )

            # Check priority threshold
            if task_priority not in self.priority_thresholds:
                return CheckResult(
                    checking_point_name=self.name,
                    checking_point_type=self.type.value,
                    result_type=CheckResultType.NO_MATCH,
                    should_act=False,
                    reason=f"Task priority '{task_priority}' is below threshold",
                    confidence=1.0,
                )

            # Check required tags
            if self.require_tags:
                missing_tags = [tag for tag in self.require_tags if tag not in task_tags]
                if missing_tags:
                    return CheckResult(
                        checking_point_name=self.name,
                        checking_point_type=self.type.value,
                        result_type=CheckResultType.NO_MATCH,
                        should_act=False,
                        reason=f"Missing required tags: {', '.join(missing_tags)}",
                        confidence=1.0,
                    )

            # Check excluded tags
            excluded_tags_found = [tag for tag in self.exclude_tags if tag in task_tags]
            if excluded_tags_found:
                return CheckResult(
                    checking_point_name=self.name,
                    checking_point_type=self.type.value,
                    result_type=CheckResultType.NO_MATCH,
                    should_act=False,
                    reason=f"Task has excluded tags: {', '.join(excluded_tags_found)}",
                    confidence=1.0,
                )

            # Check task age (how long it's been unassigned)
            hours_unassigned = 0
            if task_created_date:
                try:
                    created_date = datetime.fromisoformat(task_created_date.replace("Z", "+00:00"))
                    hours_unassigned = (datetime.utcnow() - created_date).total_seconds() / 3600
                except (ValueError, AttributeError):
                    pass  # Invalid date format

            if hours_unassigned < self.max_unassigned_age_hours:
                return CheckResult(
                    checking_point_name=self.name,
                    checking_point_type=self.type.value,
                    result_type=CheckResultType.NO_MATCH,
                    should_act=False,
                    reason=f"Task is only {hours_unassigned:.1f} hours old (threshold: {self.max_unassigned_age_hours})",
                    confidence=1.0,
                )

            # Analyze task requirements
            task_content = f"{task_name} {task_description}".lower()

            # Determine task category based on keywords
            task_categories = []
            category_keywords = {
                "backend": ["api", "server", "database", "backend", "microservice", "service"],
                "frontend": ["ui", "frontend", "react", "vue", "css", "javascript", "interface"],
                "devops": ["deploy", "infrastructure", "ci/cd", "docker", "kubernetes", "devops"],
                "testing": ["test", "testing", "qa", "quality", "automation"],
                "documentation": ["doc", "documentation", "readme", "guide", "manual"],
            }

            for category, keywords in category_keywords.items():
                if any(keyword in task_content for keyword in keywords):
                    task_categories.append(category)

            # If no specific category, default to general
            if not task_categories:
                task_categories = ["general"]

            # Calculate assignment confidence
            confidence_factors = []

            # High priority increases confidence
            if task_priority == "urgent":
                confidence_factors.append("Urgent priority")
                base_confidence = 0.8
            elif task_priority == "high":
                confidence_factors.append("High priority")
                base_confidence = 0.7
            else:
                base_confidence = 0.6

            # Age increases confidence
            if hours_unassigned >= 48:
                confidence_factors.append(f"Very old ({hours_unassigned:.0f} hours)")
                base_confidence += 0.1
            elif hours_unassigned >= 24:
                confidence_factors.append(f"Old ({hours_unassigned:.0f} hours)")
                base_confidence += 0.05

            # Clear category increases confidence
            if len(task_categories) == 1:
                confidence_factors.append(f"Clear category: {task_categories[0]}")
                base_confidence += 0.05

            confidence = min(base_confidence, 1.0)

            result = CheckResult(
                checking_point_name=self.name,
                checking_point_type=self.type.value,
                result_type=CheckResultType.MATCH,
                should_act=True,
                confidence=confidence,
                reason=f"Unassigned {task_priority} task ({hours_unassigned:.1f} hours old) needs assignment",
                context={
                    "hours_unassigned": hours_unassigned,
                    "task_priority": task_priority,
                    "task_categories": task_categories,
                    "confidence_factors": confidence_factors,
                    "available_team_members": len(self.team_members),
                },
                suggested_actions=["smart_assign", "notify_team"],
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
        """Get immediate actions for unassigned task.

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
        task_priority = task_data.get("priority", "")

        # Add assignment-needed tag
        actions.append(
            {
                "type": "status_update",
                "name": "mark_needs_assignment",
                "parameters": {
                    "system": "clickup",
                    "entity_id": task_id,
                    "new_status": task_data.get("status", {}).get("status", ""),
                    "reason": "Task marked as needing smart assignment",
                    "add_tags": ["needs_assignment"],
                },
            }
        )

        # Notify team lead about unassigned task
        if self.notify_team_lead:
            hours_unassigned = result.context.get("hours_unassigned", 0)
            actions.append(
                {
                    "type": "notification",
                    "name": "notify_team_lead_assignment",
                    "parameters": {
                        "notification_type": "slack",
                        "recipient": "#team-leads",
                        "subject": f"Unassigned Task: {task_name}",
                        "message": f"High-priority task '{task_name}' (ID: {task_id}) has been unassigned for {hours_unassigned:.1f} hours and needs smart assignment.",
                    },
                }
            )

        return actions

    def get_after_process(self, data: MonitoringData, result: CheckResult) -> list[AIAction]:
        """Get AI workflow actions for smart assignment.

        Args:
            data: Monitoring data
            result: Check result

        Returns:
            List of AI workflow actions

        """
        if not self.ai_workflow_enabled or not result.should_act:
            return []

        # Create AI assignment workflow action
        ai_action = self._create_ai_action(data, result)

        # Add specific parameters for smart assignment
        ai_action.parameters.update(
            {
                "task_categories": result.context.get("task_categories", []),
                "hours_unassigned": result.context.get("hours_unassigned", 0),
                "team_members": self.team_members,
                "assignment_rules": self.assignment_rules,
                "default_assignee": self.default_assignee,
                "auto_assign": self.auto_assign,
            }
        )

        # Override approval requirement based on auto_assign setting
        ai_action.approval_required = not self.auto_assign

        return [ai_action]
