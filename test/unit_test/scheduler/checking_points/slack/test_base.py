from gearmeshing_ai.scheduler.checking_points.base import (
    CheckingPointType,
)
from gearmeshing_ai.scheduler.checking_points.slack.base import SlackCheckingPoint
from gearmeshing_ai.scheduler.models.checking_point import CheckResult
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType


class TestSlackCheckingPoint:
    """Test SlackCheckingPoint base class."""

    class ConcreteSlackCP(SlackCheckingPoint):
        """Concrete Slack checking point for testing."""

        name = "slack_test"
        type = CheckingPointType.SLACK_BOT_MENTION_CP

        async def fetch_data(self, **kwargs) -> list[MonitoringData]:
            """Fetch test Slack data."""
            return [
                MonitoringData(
                    id="msg_456",
                    type=MonitoringDataType.SLACK_MESSAGE,
                    source="slack",
                    data={"user": "user_123", "channel": "general", "text": "Test message"},
                )
            ]

        async def evaluate(self, data: MonitoringData) -> CheckResult:
            return CheckResult(should_act=True, reason="test", confidence=0.9)

    def test_can_handle_slack_message(self):
        """Test can_handle accepts Slack message data."""
        cp = self.ConcreteSlackCP()
        data = MonitoringData(id="msg_456", type=MonitoringDataType.SLACK_MESSAGE, source="slack")
        assert cp.can_handle(data) is True

    def test_cannot_handle_clickup_task(self):
        """Test can_handle rejects ClickUp task data."""
        cp = self.ConcreteSlackCP()
        data = MonitoringData(id="task_123", type=MonitoringDataType.CLICKUP_TASK, source="clickup")
        assert cp._can_handle_data_type(data.type) is False

    def test_prompt_variables_include_slack_fields(self):
        """Test that prompt variables include Slack message fields."""
        cp = self.ConcreteSlackCP()
        data = MonitoringData(
            id="msg_456",
            type=MonitoringDataType.SLACK_MESSAGE,
            source="slack",
            data={
                "user": "user_123",
                "channel": "general",
                "text": "Help needed!",
                "thread_ts": "1234567890.123456",
                "ts": "1234567890.123456",
                "mentions": ["@bot"],
                "reactions": ["thumbsup"],
            },
        )
        from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

        result = CheckResult(
            checking_point_name="slack_test",
            checking_point_type="slack_help_request_cp",
            result_type=CheckResultType.MATCH,
            should_act=True,
            reason="test",
            confidence=0.9,
        )
        variables = cp._get_prompt_variables(data, result)

        assert variables["user_name"] == "user_123"
        assert variables["channel"] == "general"
        assert variables["message_text"] == "Help needed!"
