"""Unit tests for monitoring data models."""

import pytest
from pydantic import ValidationError

from gearmeshing_ai.scheduler.models.monitoring import (
    MonitoringData,
    MonitoringDataType,
)


class TestMonitoringDataType:
    """Test MonitoringDataType enum."""

    def test_all_enum_values(self):
        """Test that all enum values are defined."""
        assert MonitoringDataType.CLICKUP_TASK.value == "clickup_task"
        assert MonitoringDataType.SLACK_MESSAGE.value == "slack_message"
        assert MonitoringDataType.EMAIL_ALERT.value == "email_alert"
        assert MonitoringDataType.WEBHOOK_EVENT.value == "webhook_event"
        assert MonitoringDataType.CUSTOM_DATA.value == "custom_data"

    def test_get_all_values(self):
        """Test get_all_values method."""
        values = MonitoringDataType.get_all_values()
        assert len(values) == 5
        assert "clickup_task" in values
        assert "slack_message" in values
        assert "email_alert" in values


class TestMonitoringData:
    """Test MonitoringData model."""

    def test_create_clickup_task_data(self):
        """Test creating ClickUp task monitoring data."""
        data = MonitoringData(
            id="task_123",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"name": "Test Task", "priority": "high"},
        )
        assert data.id == "task_123"
        assert data.type == MonitoringDataType.CLICKUP_TASK
        assert data.source == "clickup"
        assert data.data["name"] == "Test Task"

    def test_create_slack_message_data(self):
        """Test creating Slack message monitoring data."""
        data = MonitoringData(
            id="msg_456",
            type=MonitoringDataType.SLACK_MESSAGE,
            source="slack",
            data={"user": "user_123", "text": "Help!"},
        )
        assert data.id == "msg_456"
        assert data.type == MonitoringDataType.SLACK_MESSAGE
        assert data.source == "slack"

    def test_create_email_alert_data(self):
        """Test creating email alert monitoring data."""
        data = MonitoringData(
            id="email_789",
            type=MonitoringDataType.EMAIL_ALERT,
            source="email",
            data={"subject": "Critical Alert", "body": "System down"},
        )
        assert data.id == "email_789"
        assert data.type == MonitoringDataType.EMAIL_ALERT

    def test_empty_id_validation(self):
        """Test that empty ID is rejected."""
        with pytest.raises(ValidationError):
            MonitoringData(id="", type=MonitoringDataType.CLICKUP_TASK, source="clickup")

    def test_empty_source_validation(self):
        """Test that empty source is rejected."""
        with pytest.raises(ValidationError):
            MonitoringData(id="task_123", type=MonitoringDataType.CLICKUP_TASK, source="")

    def test_default_processing_status(self):
        """Test default processing status is pending."""
        data = MonitoringData(id="task_123", type=MonitoringDataType.CLICKUP_TASK, source="clickup")
        assert data.processing_status == "pending"

    def test_get_summary(self):
        """Test get_summary method."""
        data = MonitoringData(
            id="task_123", type=MonitoringDataType.CLICKUP_TASK, source="clickup", data={"name": "Test"}
        )
        summary = data.get_summary()
        assert summary["id"] == "task_123"
        assert summary["type"] == "clickup_task"
        assert summary["source"] == "clickup"
        assert summary["processing_status"] == "pending"
        assert "data_keys" in summary
        assert "name" in summary["data_keys"]

    def test_get_data_field_simple(self):
        """Test getting a simple data field."""
        data = MonitoringData(
            id="task_123", type=MonitoringDataType.CLICKUP_TASK, source="clickup", data={"name": "Test Task"}
        )
        assert data.get_data_field("name") == "Test Task"

    def test_get_data_field_nested(self):
        """Test getting a nested data field."""
        data = MonitoringData(
            id="task_123",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"task": {"name": "Test", "priority": "high"}},
        )
        assert data.get_data_field("task.name") == "Test"
        assert data.get_data_field("task.priority") == "high"

    def test_get_data_field_default(self):
        """Test getting a non-existent field returns default."""
        data = MonitoringData(id="task_123", type=MonitoringDataType.CLICKUP_TASK, source="clickup")
        assert data.get_data_field("nonexistent") is None
        assert data.get_data_field("nonexistent", "default") == "default"

    def test_set_data_field_simple(self):
        """Test setting a simple data field."""
        data = MonitoringData(id="task_123", type=MonitoringDataType.CLICKUP_TASK, source="clickup")
        data.set_data_field("name", "New Task")
        assert data.get_data_field("name") == "New Task"

    def test_set_data_field_nested(self):
        """Test setting a nested data field."""
        data = MonitoringData(id="task_123", type=MonitoringDataType.CLICKUP_TASK, source="clickup")
        data.set_data_field("task.name", "Nested Task")
        assert data.get_data_field("task.name") == "Nested Task"

    def test_mark_processed(self):
        """Test marking data as processed."""
        data = MonitoringData(id="task_123", type=MonitoringDataType.CLICKUP_TASK, source="clickup")
        assert data.processing_status == "pending"
        assert data.processed_at is None

        data.mark_processed()
        assert data.processing_status == "completed"
        assert data.processed_at is not None

    def test_mark_processed_with_status(self):
        """Test marking data with custom status."""
        data = MonitoringData(id="task_123", type=MonitoringDataType.CLICKUP_TASK, source="clickup")
        data.mark_processed("skipped")
        assert data.processing_status == "skipped"

    def test_add_error(self):
        """Test adding processing errors."""
        data = MonitoringData(id="task_123", type=MonitoringDataType.CLICKUP_TASK, source="clickup")
        assert len(data.processing_errors) == 0

        data.add_error("Error 1")
        assert len(data.processing_errors) == 1
        assert data.processing_errors[0] == "Error 1"
        assert data.processing_status == "failed"

    def test_is_clickup_task(self):
        """Test is_clickup_task method."""
        clickup_data = MonitoringData(id="task_123", type=MonitoringDataType.CLICKUP_TASK, source="clickup")
        slack_data = MonitoringData(id="msg_456", type=MonitoringDataType.SLACK_MESSAGE, source="slack")
        assert clickup_data.is_clickup_task() is True
        assert slack_data.is_clickup_task() is False

    def test_is_slack_message(self):
        """Test is_slack_message method."""
        slack_data = MonitoringData(id="msg_456", type=MonitoringDataType.SLACK_MESSAGE, source="slack")
        clickup_data = MonitoringData(id="task_123", type=MonitoringDataType.CLICKUP_TASK, source="clickup")
        assert slack_data.is_slack_message() is True
        assert clickup_data.is_slack_message() is False

    def test_is_email_alert(self):
        """Test is_email_alert method."""
        email_data = MonitoringData(id="email_789", type=MonitoringDataType.EMAIL_ALERT, source="email")
        slack_data = MonitoringData(id="msg_456", type=MonitoringDataType.SLACK_MESSAGE, source="slack")
        assert email_data.is_email_alert() is True
        assert slack_data.is_email_alert() is False

    def test_get_task_id_from_clickup(self):
        """Test getting task ID from ClickUp data."""
        data = MonitoringData(
            id="task_123",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"id": "task_123"},  # Need to set id in data field
        )
        assert data.get_task_id() == "task_123"

    def test_get_user_id_from_slack(self):
        """Test getting user ID from Slack data."""
        data = MonitoringData(
            id="msg_456", type=MonitoringDataType.SLACK_MESSAGE, source="slack", data={"user": "user_789"}
        )
        assert data.get_user_id() == "user_789"

    def test_metadata_field(self):
        """Test metadata field."""
        data = MonitoringData(
            id="task_123",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            metadata={"source_url": "https://example.com"},
        )
        assert data.metadata["source_url"] == "https://example.com"
