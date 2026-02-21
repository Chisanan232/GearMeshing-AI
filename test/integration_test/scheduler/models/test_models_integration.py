"""Integration tests for scheduler models."""

from datetime import datetime

from gearmeshing_ai.scheduler.models.checking_point import CheckResult
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType
from gearmeshing_ai.scheduler.models.workflow import AIAction, AIActionType


class TestModelsIntegration:
    """Integration tests for scheduler models working together."""

    def test_monitoring_data_with_ai_action(self):
        """Test MonitoringData and AIAction working together."""
        # Create monitoring data
        data = MonitoringData(
            id="task_123",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"name": "Urgent Task", "priority": "high", "description": "This needs immediate attention"},
        )

        # Create AI action based on the data
        action = AIAction(
            name="urgent_task_workflow",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="clickup_urgent_triage",
            checking_point_name="urgent_task_cp",
            parameters={"data": data.model_dump()},
            prompt_variables={
                "task_id": data.get_data_field("id"),
                "task_name": data.get_data_field("name"),
                "task_priority": data.get_data_field("priority"),
            },
        )

        assert action.parameters["data"]["id"] == "task_123"
        assert action.prompt_variables["task_name"] == "Urgent Task"

    def test_check_result_with_monitoring_data(self):
        """Test CheckResult with MonitoringData."""
        from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

        data = MonitoringData(
            id="msg_456",
            type=MonitoringDataType.SLACK_MESSAGE,
            source="slack",
            data={"user": "user_123", "text": "Help needed!"},
        )

        result = CheckResult(
            checking_point_name="help_request_cp",
            checking_point_type="slack_help_request_cp",
            result_type=CheckResultType.MATCH,
            should_act=True,
            reason="Help request detected",
            confidence=0.95,
        )

        # Simulate processing
        data.mark_processed("completed")

        assert data.processing_status == "completed"
        assert result.should_act is True
        assert result.confidence == 0.95

    def test_monitoring_data_error_handling_with_processing(self):
        """Test error handling in monitoring data processing."""
        data = MonitoringData(
            id="email_789",
            type=MonitoringDataType.EMAIL_ALERT,
            source="email",
            data={"subject": "Critical", "body": "System down"},
        )

        # Simulate processing with errors
        try:
            # Simulate some processing error
            raise ValueError("Failed to parse email")
        except ValueError as e:
            data.add_error(str(e))

        assert len(data.processing_errors) == 1
        assert data.processing_status == "failed"

    def test_timestamped_model_with_monitoring_data(self):
        """Test TimestampedModel behavior with MonitoringData."""
        data1 = MonitoringData(id="task_1", type=MonitoringDataType.CLICKUP_TASK, source="clickup")

        original_updated = data1.updated_at

        # Modify the data
        data1.set_data_field("status", "completed")

        # Check that timestamps are maintained
        assert data1.created_at is not None
        assert data1.updated_at is not None

    def test_ai_action_with_check_result(self):
        """Test AIAction creation based on CheckResult."""
        from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

        result = CheckResult(
            checking_point_name="overdue_task_cp",
            checking_point_type="clickup_overdue_task_cp",
            result_type=CheckResultType.MATCH,
            should_act=True,
            reason="Overdue task detected",
            confidence=0.88,
            context={"days_overdue": 5},
        )

        action = AIAction(
            name="overdue_escalation",
            type=AIActionType.ESCALATION,
            workflow_name="task_escalation_workflow",
            checking_point_name="overdue_task_cp",
            priority=9,  # High priority for overdue
            approval_required=True,
            parameters={"check_result": result.model_dump()},
        )

        assert action.priority == 9
        assert action.approval_required is True
        assert action.parameters["check_result"]["confidence"] == 0.88

    def test_multiple_monitoring_data_processing_workflow(self):
        """Test processing multiple monitoring data items."""
        from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

        # Create multiple data items
        items = [
            MonitoringData(
                id=f"task_{i}",
                type=MonitoringDataType.CLICKUP_TASK,
                source="clickup",
                data={"name": f"Task {i}", "priority": "high" if i % 2 == 0 else "low"},
            )
            for i in range(5)
        ]

        # Process each item
        for item in items:
            should_act = item.get_data_field("priority") == "high"
            result = CheckResult(
                checking_point_name="priority_cp",
                checking_point_type="custom_cp",
                result_type=CheckResultType.MATCH if should_act else CheckResultType.NO_MATCH,
                should_act=should_act,
                reason="Priority check",
                confidence=0.9,
            )

            if result.should_act:
                item.mark_processed("completed")
            else:
                item.mark_processed("skipped")

        # Verify processing
        completed = [item for item in items if item.processing_status == "completed"]
        assert len(completed) == 3  # 5 items, 3 with high priority

    def test_model_serialization_deserialization(self):
        """Test serialization and deserialization of models."""
        # Create complex data structure
        data = MonitoringData(
            id="task_123",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"name": "Test", "nested": {"field": "value"}},
            metadata={"source_url": "https://example.com"},
        )

        # Serialize
        json_str = data.model_dump_json()

        # Deserialize
        restored = MonitoringData.model_validate_json(json_str)

        assert restored.id == data.id
        assert restored.get_data_field("nested.field") == "value"
        assert restored.metadata["source_url"] == "https://example.com"

    def test_ai_action_with_all_fields(self):
        """Test AIAction with all optional fields populated."""
        action = AIAction(
            name="comprehensive_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="comprehensive_workflow",
            checking_point_name="comprehensive_cp",
            timeout_seconds=900,
            retry_attempts=5,
            retry_delay_seconds=120,
            parameters={"key": "value"},
            prompt_template_id="template_123",
            prompt_variables={"var1": "val1"},
            agent_role="sre",
            approval_required=True,
            approval_timeout_seconds=7200,
            priority=10,
            scheduled_at=datetime.utcnow(),
            execution_id="exec_123",
            parent_execution_id="parent_123",
        )

        summary = action.get_summary()
        assert summary["name"] == "comprehensive_action"
        assert summary["type"] == "workflow_execution"
        assert summary["priority"] == 10
        assert summary["approval_required"] is True

    def test_monitoring_data_with_multiple_data_types(self):
        """Test handling different monitoring data types."""
        data_types = [
            (MonitoringDataType.CLICKUP_TASK, "clickup", {"id": "task_1"}),
            (MonitoringDataType.SLACK_MESSAGE, "slack", {"user": "user_1"}),
            (MonitoringDataType.EMAIL_ALERT, "email", {"subject": "Alert"}),
        ]

        for data_type, source, data_dict in data_types:
            data = MonitoringData(id=f"item_{source}", type=data_type, source=source, data=data_dict)

            # Verify type checking methods work
            if data_type == MonitoringDataType.CLICKUP_TASK:
                assert data.is_clickup_task() is True
            elif data_type == MonitoringDataType.SLACK_MESSAGE:
                assert data.is_slack_message() is True
            elif data_type == MonitoringDataType.EMAIL_ALERT:
                assert data.is_email_alert() is True
