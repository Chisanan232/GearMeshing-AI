"""Integration tests for checking points with registry and models."""

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
    """Urgent task checking point for testing."""

    name = "urgent_task_cp"
    type = CheckingPointType.CLICKUP_URGENT_TASK_CP
    description = "Detects urgent ClickUp tasks"

    async def fetch_data(self, **kwargs) -> list[MonitoringData]:
        """Fetch urgent tasks for testing."""
        return [
            MonitoringData(
                id="task_123",
                type=MonitoringDataType.CLICKUP_TASK,
                source="clickup",
                data={"name": "Critical Bug", "priority": "urgent"},
            )
        ]

    async def evaluate(self, data: MonitoringData) -> CheckResult:
        """Evaluate if task is urgent."""
        from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

        priority = data.get_data_field("priority", "").lower()
        is_urgent = priority in ["urgent", "high"]

        return CheckResult(
            checking_point_name="urgent_task_cp",
            checking_point_type="clickup_urgent_task_cp",
            result_type=CheckResultType.MATCH if is_urgent else CheckResultType.NO_MATCH,
            should_act=is_urgent,
            reason=f"Task priority is {priority}",
            confidence=0.95 if is_urgent else 0.1,
        )


class HelpRequestCP(SlackCheckingPoint):
    """Help request checking point for testing."""

    name = "help_request_cp"
    type = CheckingPointType.SLACK_HELP_REQUEST_CP
    description = "Detects help requests in Slack"

    async def fetch_data(self, **kwargs) -> list[MonitoringData]:
        """Fetch help request messages for testing."""
        return [
            MonitoringData(
                id="msg_789",
                type=MonitoringDataType.SLACK_MESSAGE,
                source="slack",
                data={"text": "Help! I need urgent assistance", "user": "user_123", "channel": "general"},
            )
        ]

    async def evaluate(self, data: MonitoringData) -> CheckResult:
        """Evaluate if message is a help request."""
        from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

        text = data.get_data_field("text", "").lower()
        is_help = any(word in text for word in ["help", "urgent", "issue", "problem"])

        return CheckResult(
            checking_point_name="help_request_cp",
            checking_point_type="slack_help_request_cp",
            result_type=CheckResultType.MATCH if is_help else CheckResultType.NO_MATCH,
            should_act=is_help,
            reason="Help request detected" if is_help else "Not a help request",
            confidence=0.9 if is_help else 0.1,
        )


class TestCheckingPointsIntegration:
    """Integration tests for checking points."""

    @pytest.mark.asyncio
    async def test_urgent_task_detection(self):
        """Test urgent task detection workflow."""
        cp = UrgentTaskCP()

        # Test urgent task
        urgent_data = MonitoringData(
            id="task_123",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"name": "Critical Bug", "priority": "urgent"},
        )

        result = await cp.evaluate(urgent_data)
        assert result.should_act is True
        assert result.confidence == 0.95

        # Get AI actions
        actions = cp.get_after_process(urgent_data, result)
        assert len(actions) == 1
        assert actions[0].checking_point_name == "urgent_task_cp"

    @pytest.mark.asyncio
    async def test_non_urgent_task_ignored(self):
        """Test that non-urgent tasks are ignored."""
        cp = UrgentTaskCP()

        normal_data = MonitoringData(
            id="task_456",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"name": "Regular Task", "priority": "low"},
        )

        result = await cp.evaluate(normal_data)
        assert result.should_act is False
        assert result.confidence == 0.1

        # No AI actions for non-urgent
        actions = cp.get_after_process(normal_data, result)
        assert len(actions) == 0

    @pytest.mark.asyncio
    async def test_help_request_detection(self):
        """Test help request detection workflow."""
        cp = HelpRequestCP()

        help_data = MonitoringData(
            id="msg_789",
            type=MonitoringDataType.SLACK_MESSAGE,
            source="slack",
            data={"user": "user_123", "text": "Help! I have an urgent issue"},
        )

        result = await cp.evaluate(help_data)
        assert result.should_act is True
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_registry_with_multiple_checking_points(self):
        """Test registry managing multiple checking points."""
        registry = CheckingPointRegistry()

        # Register checking points
        registry.register(UrgentTaskCP)
        registry.register(HelpRequestCP)

        # Get all instances
        instances = registry.get_all_instances()
        assert len(instances) == 2
        assert "urgent_task_cp" in instances
        assert "help_request_cp" in instances

        # Get by type
        clickup_cps = registry.get_by_type(CheckingPointType.CLICKUP_URGENT_TASK_CP)
        assert "urgent_task_cp" in clickup_cps

        slack_cps = registry.get_by_type(CheckingPointType.SLACK_HELP_REQUEST_CP)
        assert "help_request_cp" in slack_cps

    @pytest.mark.asyncio
    async def test_checking_point_filtering_workflow(self):
        """Test filtering data through multiple checking points."""
        registry = CheckingPointRegistry()
        registry.register(UrgentTaskCP)
        registry.register(HelpRequestCP)

        # Create ClickUp task data
        task_data = MonitoringData(
            id="task_123",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"name": "Urgent Bug", "priority": "urgent"},
        )

        # Get all instances
        instances = registry.get_all_instances()

        # Filter which checking points can handle this data
        applicable_cps = {name: cp for name, cp in instances.items() if cp.can_handle(task_data)}

        # Only urgent_task_cp should handle ClickUp data
        assert "urgent_task_cp" in applicable_cps
        assert "help_request_cp" not in applicable_cps

    @pytest.mark.asyncio
    async def test_checking_point_with_config(self):
        """Test checking point with configuration."""
        config = {
            "enabled": True,
            "priority": 8,
            "stop_on_match": True,
            "timeout_seconds": 300,
            "approval_required": True,
        }

        cp = UrgentTaskCP(config)

        assert cp.enabled is True
        assert cp.priority == 8
        assert cp.stop_on_match is True
        assert cp.timeout_seconds == 300
        assert cp.approval_required is True

    @pytest.mark.asyncio
    async def test_checking_point_validation(self):
        """Test checking point configuration validation."""
        cp = UrgentTaskCP()

        # Valid configuration
        errors = cp.validate_config()
        assert len(errors) == 0

        # Invalid configuration
        cp.priority = 11  # Out of range
        errors = cp.validate_config()
        assert len(errors) > 0

    @pytest.mark.asyncio
    async def test_checking_point_summary(self):
        """Test checking point summary generation."""
        cp = UrgentTaskCP()
        summary = cp.get_summary()

        assert summary["name"] == "urgent_task_cp"
        assert summary["type"] == "clickup_urgent_task_cp"
        assert summary["enabled"] is True
        assert summary["priority"] == 5

    @pytest.mark.asyncio
    async def test_ai_action_creation_from_checking_point(self):
        """Test AI action creation from checking point evaluation."""
        cp = UrgentTaskCP()

        data = MonitoringData(
            id="task_123",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_123",
                "name": "Critical Bug",
                "priority": "urgent",
                "description": "System crash",
                "status": {"status": "open"},
                "assignees": {},
                "due_date": "2026-02-20",
                "tags": ["critical"],
                "custom_fields": {},
            },
        )

        result = await cp.evaluate(data)
        actions = cp.get_after_process(data, result)

        # Verify actions are created
        assert isinstance(actions, list)

    @pytest.mark.asyncio
    async def test_disabled_checking_point_not_evaluated(self):
        """Test that disabled checking points are not evaluated."""
        config = {"enabled": False}
        cp = UrgentTaskCP(config)

        data = MonitoringData(
            id="task_123", type=MonitoringDataType.CLICKUP_TASK, source="clickup", data={"priority": "urgent"}
        )

        # can_handle should return False for disabled checking point
        assert cp.can_handle(data) is False

    @pytest.mark.asyncio
    async def test_checking_point_stop_on_match(self):
        """Test stop_on_match behavior."""
        config = {"stop_on_match": True}
        cp = UrgentTaskCP(config)

        data = MonitoringData(
            id="task_123", type=MonitoringDataType.CLICKUP_TASK, source="clickup", data={"priority": "urgent"}
        )

        result = await cp.evaluate(data)

        # If stop_on_match is True and result matches, further checking points should be skipped
        assert cp.stop_on_match is True
        assert result.should_act is True
