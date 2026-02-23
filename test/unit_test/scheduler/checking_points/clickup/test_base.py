from gearmeshing_ai.scheduler.checking_points.base import (
    CheckingPointType,
)
from gearmeshing_ai.scheduler.checking_points.clickup.base import ClickUpCheckingPoint
from gearmeshing_ai.scheduler.models.checking_point import CheckResult
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType


class TestClickUpCheckingPoint:
    """Test ClickUpCheckingPoint base class."""

    class ConcreteClickUpCP(ClickUpCheckingPoint):
        """Concrete ClickUp checking point for testing."""

        name = "clickup_test"
        type = CheckingPointType.CLICKUP_URGENT_TASK_CP

        async def fetch_data(self, **kwargs) -> list[MonitoringData]:
            """Fetch test ClickUp data."""
            return [
                MonitoringData(
                    id="task_123",
                    type=MonitoringDataType.CLICKUP_TASK,
                    source="clickup",
                    data={"id": "task_123", "name": "Test Task"},
                )
            ]

        async def evaluate(self, data: MonitoringData) -> CheckResult:
            return CheckResult(should_act=True, reason="test", confidence=0.9)

    def test_can_handle_clickup_task(self):
        """Test can_handle accepts ClickUp task data."""
        cp = self.ConcreteClickUpCP()
        data = MonitoringData(id="task_123", type=MonitoringDataType.CLICKUP_TASK, source="clickup")
        assert cp.can_handle(data) is True

    def test_cannot_handle_slack_message(self):
        """Test can_handle rejects Slack message data."""
        cp = self.ConcreteClickUpCP()
        data = MonitoringData(id="msg_456", type=MonitoringDataType.SLACK_MESSAGE, source="slack")
        # Note: _can_handle_data_type only checks type, can_handle also checks enabled
        assert cp._can_handle_data_type(data.type) is False

    def test_prompt_variables_include_task_fields(self):
        """Test that prompt variables include ClickUp task fields."""
        cp = self.ConcreteClickUpCP()
        data = MonitoringData(
            id="task_123",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_123",
                "name": "Test Task",
                "description": "Test description",
                "priority": "high",
                "status": {"status": "open"},
                "assignees": {"id": "user_1", "name": "John"},
                "due_date": "2026-02-28",
                "tags": ["urgent"],
                "custom_fields": {"field1": "value1"},
            },
        )
        from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

        result = CheckResult(
            checking_point_name="clickup_test",
            checking_point_type="clickup_urgent_task_cp",
            result_type=CheckResultType.MATCH,
            should_act=True,
            reason="test",
            confidence=0.9,
        )
        variables = cp._get_prompt_variables(data, result)

        assert variables["task_id"] == "task_123"
        assert variables["task_name"] == "Test Task"
        assert variables["task_priority"] == "high"
