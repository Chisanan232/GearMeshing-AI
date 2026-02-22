"""End-to-end tests for checking points."""

import asyncio

import pytest

from gearmeshing_ai.scheduler.checking_points.base import (
    CheckingPointType,
    ClickUpCheckingPoint,
    SlackCheckingPoint,
)
from gearmeshing_ai.scheduler.checking_points.registry import CheckingPointRegistry
from gearmeshing_ai.scheduler.models.checking_point import CheckResult
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType


class UrgentTaskCP(ClickUpCheckingPoint):
    """Urgent task checking point."""

    name = "urgent_task_cp"
    type = CheckingPointType.CLICKUP_URGENT_TASK_CP
    description = "Detects urgent ClickUp tasks"

    async def fetch_data(self, **kwargs) -> list[MonitoringData]:
        """Fetch urgent tasks."""
        return [
            MonitoringData(
                id="task_urgent_123",
                type=MonitoringDataType.CLICKUP_TASK,
                source="clickup",
                data={"id": "task_urgent_123", "name": "Urgent Task", "priority": "urgent"},
            )
        ]

    async def evaluate(self, data: MonitoringData) -> CheckResult:
        from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

        priority = data.get_data_field("priority", "").lower()
        is_urgent = priority in ["urgent", "high", "critical"]

        return CheckResult(
            checking_point_name="urgent_task_cp",
            checking_point_type="clickup_urgent_task_cp",
            result_type=CheckResultType.MATCH if is_urgent else CheckResultType.NO_MATCH,
            should_act=is_urgent,
            reason=f"Task priority is {priority}",
            confidence=0.95 if is_urgent else 0.1,
        )


class OverdueTaskCP(ClickUpCheckingPoint):
    """Overdue task checking point."""

    name = "overdue_task_cp"
    type = CheckingPointType.CLICKUP_OVERDUE_TASK_CP
    description = "Detects overdue ClickUp tasks"

    async def fetch_data(self, **kwargs) -> list[MonitoringData]:
        """Fetch overdue tasks."""
        return [
            MonitoringData(
                id="task_overdue_456",
                type=MonitoringDataType.CLICKUP_TASK,
                source="clickup",
                data={"id": "task_overdue_456", "name": "Overdue Task", "status": {"status": "overdue"}},
            )
        ]

    async def evaluate(self, data: MonitoringData) -> CheckResult:
        from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

        status = data.get_data_field("status.status", "").lower()
        is_overdue = status == "overdue"

        return CheckResult(
            checking_point_name="overdue_task_cp",
            checking_point_type="clickup_overdue_task_cp",
            result_type=CheckResultType.MATCH if is_overdue else CheckResultType.NO_MATCH,
            should_act=is_overdue,
            reason="Task is overdue",
            confidence=0.9 if is_overdue else 0.1,
        )


class HelpRequestCP(SlackCheckingPoint):
    """Help request checking point."""

    name = "help_request_cp"
    type = CheckingPointType.SLACK_HELP_REQUEST_CP
    description = "Detects help requests in Slack"

    async def fetch_data(self, **kwargs) -> list[MonitoringData]:
        """Fetch help request messages."""
        return [
            MonitoringData(
                id="msg_help_789",
                type=MonitoringDataType.SLACK_MESSAGE,
                source="slack",
                data={"text": "Help! I need urgent assistance", "user": "user_123", "channel": "general"},
            )
        ]

    async def evaluate(self, data: MonitoringData) -> CheckResult:
        from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

        text = data.get_data_field("text", "").lower()
        is_help = any(word in text for word in ["help", "urgent", "issue", "problem", "error"])

        return CheckResult(
            checking_point_name="help_request_cp",
            checking_point_type="slack_help_request_cp",
            result_type=CheckResultType.MATCH if is_help else CheckResultType.NO_MATCH,
            should_act=is_help,
            reason="Help request detected" if is_help else "Not a help request",
            confidence=0.9 if is_help else 0.1,
        )


class TestCheckingPointsE2E:
    """End-to-end tests for checking points."""

    @pytest.mark.asyncio
    async def test_complete_urgent_task_workflow(self):
        """Test complete urgent task detection and action workflow."""
        # Create checking point
        cp = UrgentTaskCP()

        # Create urgent task data
        data = MonitoringData(
            id="task_urgent_123",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_urgent_123",
                "name": "Critical Production Issue",
                "description": "Database connection timeout affecting all users",
                "priority": "urgent",
                "status": {"status": "open"},
                "assignees": {"id": "user_1", "name": "John"},
                "due_date": "2026-02-18",
                "tags": ["production", "critical"],
                "custom_fields": {"severity": "critical"},
            },
        )

        # Evaluate
        result = await cp.evaluate(data)
        assert result.should_act is True
        assert result.confidence == 0.95

        # Get AI actions
        actions = cp.get_after_process(data, result)
        assert len(actions) == 1

        action = actions[0]
        assert action.name == "urgent_task_cp_workflow"
        assert action.priority == 5  # Default priority

        # Mark data as processed
        data.mark_processed("completed")
        assert data.processing_status == "completed"

    @pytest.mark.asyncio
    async def test_multiple_checking_points_workflow(self):
        """Test multiple checking points evaluating same data."""
        # Create checking points
        urgent_cp = UrgentTaskCP()
        overdue_cp = OverdueTaskCP()

        # Create task data
        data = MonitoringData(
            id="task_multi_456",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_multi_456",
                "name": "Multi-Check Task",
                "priority": "high",
                "status": {"status": "overdue"},
            },
        )

        # Evaluate with both checking points
        urgent_result = await urgent_cp.evaluate(data)
        overdue_result = await overdue_cp.evaluate(data)

        # Both should match
        assert urgent_result.should_act is True
        assert overdue_result.should_act is True

        # Get actions from both
        urgent_actions = urgent_cp.get_after_process(data, urgent_result)
        overdue_actions = overdue_cp.get_after_process(data, overdue_result)

        assert len(urgent_actions) == 1
        assert len(overdue_actions) == 1

    @pytest.mark.asyncio
    async def test_slack_help_request_workflow(self):
        """Test Slack help request detection workflow."""
        cp = HelpRequestCP()

        # Create help request data
        data = MonitoringData(
            id="msg_help_789",
            type=MonitoringDataType.SLACK_MESSAGE,
            source="slack",
            data={
                "user": "user_123",
                "channel": "support",
                "text": "Help! Our API is experiencing critical errors",
                "thread_ts": "1234567890.123456",
                "ts": "1234567891.123456",
                "mentions": ["@support-bot"],
                "reactions": ["warning"],
            },
        )

        # Evaluate
        result = await cp.evaluate(data)
        assert result.should_act is True
        assert result.confidence == 0.9

        # Get actions
        actions = cp.get_after_process(data, result)
        assert len(actions) == 1

        action = actions[0]
        assert action.checking_point_name == "help_request_cp"

    @pytest.mark.asyncio
    async def test_registry_with_multiple_checking_points(self):
        """Test registry managing multiple checking points."""
        registry = CheckingPointRegistry()

        # Register checking points
        registry.register(UrgentTaskCP)
        registry.register(OverdueTaskCP)
        registry.register(HelpRequestCP)

        # Get all instances
        instances = registry.get_all_instances()
        assert len(instances) == 3

        # Get by type
        clickup_cps = registry.get_by_type(CheckingPointType.CLICKUP_URGENT_TASK_CP)
        assert "urgent_task_cp" in clickup_cps

        slack_cps = registry.get_by_type(CheckingPointType.SLACK_HELP_REQUEST_CP)
        assert "help_request_cp" in slack_cps

        # Get summary
        summary = registry.get_summary()
        assert summary["total_checking_points"] == 3

    @pytest.mark.asyncio
    async def test_data_filtering_through_checking_points(self):
        """Test filtering data through multiple checking points."""
        registry = CheckingPointRegistry()
        registry.register(UrgentTaskCP)
        registry.register(OverdueTaskCP)
        registry.register(HelpRequestCP)

        # Create ClickUp task data
        task_data = MonitoringData(
            id="task_filter_123",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"priority": "high", "status": {"status": "open"}},
        )

        # Get instances
        instances = registry.get_all_instances()

        # Filter applicable checking points
        applicable = {name: cp for name, cp in instances.items() if cp.can_handle(task_data)}

        # Only ClickUp checking points should handle ClickUp data
        assert "urgent_task_cp" in applicable
        assert "overdue_task_cp" in applicable
        assert "help_request_cp" not in applicable

    @pytest.mark.asyncio
    async def test_checking_point_with_configuration(self):
        """Test checking point with custom configuration."""
        config = {
            "enabled": True,
            "priority": 8,
            "stop_on_match": True,
            "timeout_seconds": 300,
            "approval_required": True,
            "ai_workflow_enabled": True,
        }

        cp = UrgentTaskCP(config)

        # Verify configuration
        assert cp.enabled is True
        assert cp.priority == 8
        assert cp.stop_on_match is True
        assert cp.approval_required is True

        # Validate
        errors = cp.validate_config()
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_checking_point_disabled(self):
        """Test disabled checking point is not evaluated."""
        config = {"enabled": False}
        cp = UrgentTaskCP(config)

        data = MonitoringData(
            id="task_disabled", type=MonitoringDataType.CLICKUP_TASK, source="clickup", data={"priority": "urgent"}
        )

        # can_handle should return False
        assert cp.can_handle(data) is False

    @pytest.mark.asyncio
    async def test_non_matching_data(self):
        """Test checking point with non-matching data."""
        cp = UrgentTaskCP()

        # Create non-urgent task
        data = MonitoringData(
            id="task_low", type=MonitoringDataType.CLICKUP_TASK, source="clickup", data={"priority": "low"}
        )

        # Evaluate
        result = await cp.evaluate(data)
        assert result.should_act is False
        assert result.confidence == 0.1

        # No actions should be created
        actions = cp.get_after_process(data, result)
        assert len(actions) == 0

    @pytest.mark.asyncio
    async def test_checking_point_summary(self):
        """Test checking point summary generation."""
        cp = UrgentTaskCP()
        summary = cp.get_summary()

        assert summary["name"] == "urgent_task_cp"
        assert summary["type"] == "clickup_urgent_task_cp"
        assert summary["description"] == "Detects urgent ClickUp tasks"
        assert summary["enabled"] is True
        assert summary["priority"] == 5

    @pytest.mark.asyncio
    async def test_concurrent_checking_point_evaluation(self):
        """Test concurrent evaluation of multiple checking points."""
        # Create checking points
        cps = [UrgentTaskCP(), OverdueTaskCP(), HelpRequestCP()]

        # Create data
        data = MonitoringData(
            id="task_concurrent",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"priority": "urgent", "status": {"status": "overdue"}},
        )

        # Evaluate concurrently
        results = await asyncio.gather(*[cp.evaluate(data) for cp in cps])

        # Verify results
        assert len(results) == 3
        assert results[0].should_act is True  # Urgent
        assert results[1].should_act is True  # Overdue
        assert results[2].should_act is False  # Not a Slack message

    @pytest.mark.asyncio
    async def test_checking_point_ai_action_generation(self):
        """Test AI action generation from checking point."""
        cp = UrgentTaskCP()

        data = MonitoringData(
            id="task_action_gen",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_action_gen",
                "name": "Critical Task",
                "priority": "urgent",
                "description": "Needs immediate attention",
                "status": {"status": "open"},
                "assignees": {},
                "due_date": "2026-02-18",
                "tags": ["critical"],
                "custom_fields": {},
            },
        )

        result = await cp.evaluate(data)
        actions = cp.get_after_process(data, result)

        assert len(actions) == 1
        action = actions[0]

        # Verify action has correct prompt variables
        assert "task_id" in action.prompt_variables
        assert "task_name" in action.prompt_variables
        assert "task_priority" in action.prompt_variables
        assert action.prompt_variables["task_priority"] == "urgent"
