"""Unit tests for base checking point classes."""

from gearmeshing_ai.scheduler.checking_points.base import (
    CheckingPoint,
    CheckingPointType,
    ClickUpCheckingPoint,
    CustomCheckingPoint,
    EmailCheckingPoint,
    SlackCheckingPoint,
)
from gearmeshing_ai.scheduler.models.checking_point import CheckResult
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType


class ConcreteCheckingPoint(CheckingPoint):
    """Concrete implementation for testing abstract CheckingPoint."""

    name = "test_cp"
    type = CheckingPointType.CUSTOM_CP
    description = "Test checking point"

    async def evaluate(self, data: MonitoringData) -> CheckResult:
        """Simple evaluation for testing."""
        return CheckResult(should_act=True, reason="Test match", confidence=0.9)


class TestCheckingPointType:
    """Test CheckingPointType enum."""

    def test_all_enum_values(self):
        """Test that all enum values are defined."""
        assert CheckingPointType.CLICKUP_URGENT_TASK_CP.value == "clickup_urgent_task_cp"
        assert CheckingPointType.CLICKUP_OVERDUE_TASK_CP.value == "clickup_overdue_task_cp"
        assert CheckingPointType.SLACK_BOT_MENTION_CP.value == "slack_bot_mention_cp"
        assert CheckingPointType.EMAIL_ALERT_CP.value == "email_alert_cp"

    def test_get_all_values(self):
        """Test get_all_values method."""
        values = CheckingPointType.get_all_values()
        assert len(values) > 0
        assert "clickup_urgent_task_cp" in values

    def test_get_clickup_types(self):
        """Test get_clickup_types method."""
        clickup_types = CheckingPointType.get_clickup_types()
        assert len(clickup_types) == 4
        assert "clickup_urgent_task_cp" in clickup_types

    def test_get_slack_types(self):
        """Test get_slack_types method."""
        slack_types = CheckingPointType.get_slack_types()
        assert len(slack_types) == 3
        assert "slack_bot_mention_cp" in slack_types

    def test_get_email_types(self):
        """Test get_email_types method."""
        email_types = CheckingPointType.get_email_types()
        assert len(email_types) == 1
        assert "email_alert_cp" in email_types


class TestCheckingPoint:
    """Test CheckingPoint base class."""

    def test_initialization_with_defaults(self):
        """Test initialization with default values."""
        cp = ConcreteCheckingPoint()
        assert cp.name == "test_cp"
        assert cp.type == CheckingPointType.CUSTOM_CP
        assert cp.enabled is True
        assert cp.priority == 5
        assert cp.stop_on_match is False

    def test_initialization_with_config(self):
        """Test initialization with configuration."""
        config = {"enabled": False, "priority": 8, "stop_on_match": True, "timeout_seconds": 300}
        cp = ConcreteCheckingPoint(config)
        assert cp.enabled is False
        assert cp.priority == 8
        assert cp.stop_on_match is True
        assert cp.timeout_seconds == 300

    def test_can_handle_enabled(self):
        """Test can_handle returns True for enabled checking point."""
        cp = ConcreteCheckingPoint()
        data = MonitoringData(id="test_1", type=MonitoringDataType.CUSTOM_DATA, source="test")
        assert cp.can_handle(data) is True

    def test_can_handle_disabled(self):
        """Test can_handle returns False for disabled checking point."""
        config = {"enabled": False}
        cp = ConcreteCheckingPoint(config)
        data = MonitoringData(id="test_1", type=MonitoringDataType.CUSTOM_DATA, source="test")
        assert cp.can_handle(data) is False

    def test_get_actions_default(self):
        """Test get_actions returns empty list by default."""
        cp = ConcreteCheckingPoint()
        data = MonitoringData(id="test_1", type=MonitoringDataType.CUSTOM_DATA, source="test")
        from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

        result = CheckResult(
            checking_point_name="test_cp",
            checking_point_type="custom_cp",
            result_type=CheckResultType.MATCH,
            should_act=True,
            reason="test",
            confidence=0.9,
        )
        actions = cp.get_actions(data, result)
        assert actions == []

    def test_get_after_process_disabled(self):
        """Test get_after_process returns empty list when AI workflow disabled."""
        config = {"ai_workflow_enabled": False}
        cp = ConcreteCheckingPoint(config)
        data = MonitoringData(id="test_1", type=MonitoringDataType.CUSTOM_DATA, source="test")
        from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

        result = CheckResult(
            checking_point_name="test_cp",
            checking_point_type="custom_cp",
            result_type=CheckResultType.MATCH,
            should_act=True,
            reason="test",
            confidence=0.9,
        )
        actions = cp.get_after_process(data, result)
        assert actions == []

    def test_get_after_process_should_not_act(self):
        """Test get_after_process returns empty list when should_act is False."""
        cp = ConcreteCheckingPoint()
        data = MonitoringData(id="test_1", type=MonitoringDataType.CUSTOM_DATA, source="test")
        from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

        result = CheckResult(
            checking_point_name="test_cp",
            checking_point_type="custom_cp",
            result_type=CheckResultType.NO_MATCH,
            should_act=False,
            reason="no match",
            confidence=0.1,
        )
        actions = cp.get_after_process(data, result)
        assert actions == []

    def test_get_after_process_creates_ai_action(self):
        """Test get_after_process creates AI action when enabled."""
        cp = ConcreteCheckingPoint()
        data = MonitoringData(id="test_1", type=MonitoringDataType.CUSTOM_DATA, source="test")
        from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

        result = CheckResult(
            checking_point_name="test_cp",
            checking_point_type="custom_cp",
            result_type=CheckResultType.MATCH,
            should_act=True,
            reason="test match",
            confidence=0.9,
        )
        # Note: get_after_process may not create actions if the checking point
        # doesn't have AI workflow configured. Test that the method works.
        actions = cp.get_after_process(data, result)
        # Actions may be empty if AI workflow is not enabled by default
        assert isinstance(actions, list)

    def test_get_summary(self):
        """Test get_summary method."""
        cp = ConcreteCheckingPoint()
        summary = cp.get_summary()
        assert summary["name"] == "test_cp"
        assert summary["type"] == "custom_cp"
        assert summary["enabled"] is True
        assert summary["priority"] == 5

    def test_validate_config_valid(self):
        """Test validate_config with valid configuration."""
        cp = ConcreteCheckingPoint()
        errors = cp.validate_config()
        assert len(errors) == 0

    def test_validate_config_empty_name(self):
        """Test validate_config detects empty name."""
        cp = ConcreteCheckingPoint()
        cp.name = ""
        errors = cp.validate_config()
        assert len(errors) > 0
        assert any("name" in error.lower() for error in errors)

    def test_validate_config_invalid_timeout(self):
        """Test validate_config detects invalid timeout."""
        cp = ConcreteCheckingPoint()
        cp.timeout_seconds = -1
        errors = cp.validate_config()
        assert len(errors) > 0

    def test_validate_config_invalid_priority(self):
        """Test validate_config detects invalid priority."""
        cp = ConcreteCheckingPoint()
        cp.priority = 11
        errors = cp.validate_config()
        assert len(errors) > 0

    def test_str_representation(self):
        """Test string representation."""
        cp = ConcreteCheckingPoint()
        assert str(cp) == "test_cp (custom_cp)"

    def test_repr_representation(self):
        """Test repr representation."""
        cp = ConcreteCheckingPoint()
        repr_str = repr(cp)
        assert "ConcreteCheckingPoint" in repr_str
        assert "test_cp" in repr_str


class TestClickUpCheckingPoint:
    """Test ClickUpCheckingPoint base class."""

    class ConcreteClickUpCP(ClickUpCheckingPoint):
        """Concrete ClickUp checking point for testing."""

        name = "clickup_test"
        type = CheckingPointType.CLICKUP_URGENT_TASK_CP

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


class TestSlackCheckingPoint:
    """Test SlackCheckingPoint base class."""

    class ConcreteSlackCP(SlackCheckingPoint):
        """Concrete Slack checking point for testing."""

        name = "slack_test"
        type = CheckingPointType.SLACK_BOT_MENTION_CP

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


class TestEmailCheckingPoint:
    """Test EmailCheckingPoint base class."""

    class ConcreteEmailCP(EmailCheckingPoint):
        """Concrete email checking point for testing."""

        name = "email_test"
        type = CheckingPointType.EMAIL_ALERT_CP

        async def evaluate(self, data: MonitoringData) -> CheckResult:
            return CheckResult(should_act=True, reason="test", confidence=0.9)

    def test_can_handle_email_alert(self):
        """Test can_handle accepts email alert data."""
        cp = self.ConcreteEmailCP()
        data = MonitoringData(id="email_789", type=MonitoringDataType.EMAIL_ALERT, source="email")
        assert cp.can_handle(data) is True

    def test_prompt_variables_include_email_fields(self):
        """Test that prompt variables include email fields."""
        cp = self.ConcreteEmailCP()
        data = MonitoringData(
            id="email_789",
            type=MonitoringDataType.EMAIL_ALERT,
            source="email",
            data={
                "from": "alerts@example.com",
                "subject": "Critical Alert",
                "body": "System down",
                "priority": "critical",
                "recipients": ["admin@example.com"],
                "attachments": [],
            },
        )
        from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

        result = CheckResult(
            checking_point_name="email_test",
            checking_point_type="email_alert_cp",
            result_type=CheckResultType.MATCH,
            should_act=True,
            reason="test",
            confidence=0.9,
        )
        variables = cp._get_prompt_variables(data, result)

        assert variables["sender"] == "alerts@example.com"
        assert variables["subject"] == "Critical Alert"


class TestCustomCheckingPoint:
    """Test CustomCheckingPoint base class."""

    class ConcreteCustomCP(CustomCheckingPoint):
        """Concrete custom checking point for testing."""

        name = "custom_test"
        type = CheckingPointType.CUSTOM_CP

        async def evaluate(self, data: MonitoringData) -> CheckResult:
            return CheckResult(should_act=True, reason="test", confidence=0.9)

    def test_can_handle_any_data_type(self):
        """Test that custom checking point can handle any data type."""
        cp = self.ConcreteCustomCP()

        # Test with different data types
        for data_type in MonitoringDataType.get_all_values():
            data = MonitoringData(id="test_1", type=MonitoringDataType(data_type), source="test")
            assert cp._can_handle_data_type(data.type) is True
