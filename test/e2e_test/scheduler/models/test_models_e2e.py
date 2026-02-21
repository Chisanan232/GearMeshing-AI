"""End-to-end tests for scheduler models."""

from datetime import datetime

from gearmeshing_ai.scheduler.models.checking_point import CheckResult
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType
from gearmeshing_ai.scheduler.models.workflow import AIAction, AIActionType


class TestModelsE2E:
    """End-to-end tests for scheduler models."""

    def test_complete_monitoring_workflow(self):
        """Test complete monitoring data workflow."""
        # Create monitoring data from external system
        data = MonitoringData(
            id="task_12345",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_12345",
                "name": "Critical Production Bug",
                "description": "Database connection timeout in production",
                "priority": "urgent",
                "status": {"status": "open"},
                "assignees": {"id": "user_1", "name": "John Doe"},
                "due_date": "2026-02-20",
                "tags": ["production", "critical"],
                "custom_fields": {"severity": "high", "impact": "revenue"},
            },
            metadata={"source_url": "https://clickup.com/tasks/12345"},
        )

        # Verify data integrity
        assert data.id == "task_12345"
        assert data.is_clickup_task() is True
        assert data.processing_status == "pending"

        # Simulate checking point evaluation
        from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

        result = CheckResult(
            checking_point_name="urgent_task_cp",
            checking_point_type="clickup_urgent_task_cp",
            result_type=CheckResultType.MATCH,
            should_act=True,
            reason="Critical production issue detected",
            confidence=0.98,
        )

        # Create AI action based on evaluation
        action = AIAction(
            name="critical_bug_triage",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="critical_bug_triage_workflow",
            checking_point_name="urgent_task_cp",
            priority=10,
            approval_required=True,
            parameters={"task_data": data.model_dump()},
            prompt_variables={
                "task_id": data.get_data_field("id"),
                "task_name": data.get_data_field("name"),
                "task_priority": data.get_data_field("priority"),
                "severity": data.get_data_field("custom_fields.severity"),
            },
        )

        # Verify action creation
        assert action.approval_required is True
        assert action.priority == 10
        assert action.prompt_variables["severity"] == "high"

        # Mark data as processed
        data.mark_processed("completed")
        assert data.processing_status == "completed"
        assert data.processed_at is not None

    def test_slack_message_help_request_workflow(self):
        """Test Slack message help request workflow."""
        # Create Slack message data
        data = MonitoringData(
            id="msg_slack_789",
            type=MonitoringDataType.SLACK_MESSAGE,
            source="slack",
            data={
                "user": "user_slack_123",
                "channel": "support",
                "text": "Help! Our API is down and customers are complaining",
                "thread_ts": "1234567890.123456",
                "ts": "1234567891.123456",
                "mentions": ["@support-bot"],
                "reactions": ["warning"],
            },
            metadata={"channel_name": "support", "user_name": "alice"},
        )

        # Verify data
        assert data.is_slack_message() is True
        assert data.get_data_field("channel") == "support"
        assert "API is down" in data.get_data_field("text")

        # Simulate evaluation
        from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

        result = CheckResult(
            checking_point_name="help_request_cp",
            checking_point_type="slack_help_request_cp",
            result_type=CheckResultType.MATCH,
            should_act=True,
            reason="Critical support request detected",
            confidence=0.95,
        )

        # Create escalation action
        action = AIAction(
            name="critical_support_escalation",
            type=AIActionType.ESCALATION,
            workflow_name="support_escalation_workflow",
            checking_point_name="help_request_cp",
            priority=9,
            approval_required=True,
            approval_timeout_seconds=1800,
            parameters={"message_data": data.model_dump()},
        )

        assert action.type == AIActionType.ESCALATION
        assert action.approval_timeout_seconds == 1800

    def test_email_alert_incident_workflow(self):
        """Test email alert incident response workflow."""
        # Create email alert data
        data = MonitoringData(
            id="email_alert_456",
            type=MonitoringDataType.EMAIL_ALERT,
            source="email",
            data={
                "from": "alerts@monitoring.example.com",
                "subject": "CRITICAL: Database CPU at 95%",
                "body": "Database server CPU usage is at 95%. Immediate action required.",
                "priority": "critical",
                "recipients": ["ops@example.com", "devops@example.com"],
                "attachments": ["metrics.pdf"],
            },
            metadata={"alert_id": "alert_456", "service": "database"},
        )

        # Verify data
        assert data.is_email_alert() is True
        assert data.get_data_field("priority") == "critical"

        # Simulate evaluation
        from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

        result = CheckResult(
            checking_point_name="email_alert_cp",
            checking_point_type="email_alert_cp",
            result_type=CheckResultType.MATCH,
            should_act=True,
            reason="Critical infrastructure alert",
            confidence=0.99,
        )

        # Create incident action
        action = AIAction(
            name="critical_incident_response",
            type=AIActionType.ESCALATION,
            workflow_name="incident_response_workflow",
            checking_point_name="email_alert_cp",
            priority=10,
            approval_required=False,  # Automatic for critical incidents
            parameters={"alert_data": data.model_dump()},
        )

        assert action.approval_required is False
        assert action.priority == 10

    def test_data_serialization_deserialization_roundtrip(self):
        """Test complete serialization/deserialization roundtrip."""
        # Create complex data
        original_data = MonitoringData(
            id="task_roundtrip",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_roundtrip",
                "name": "Test Task",
                "nested": {"level1": {"level2": {"value": "deep_value"}}},
                "list": [1, 2, 3, 4, 5],
            },
            metadata={"key": "value"},
        )

        # Serialize to JSON
        json_str = original_data.model_dump_json()

        # Deserialize from JSON
        restored_data = MonitoringData.model_validate_json(json_str)

        # Verify roundtrip
        assert restored_data.id == original_data.id
        assert restored_data.type == original_data.type
        assert restored_data.get_data_field("nested.level1.level2.value") == "deep_value"
        assert restored_data.metadata == original_data.metadata

    def test_multiple_data_items_processing_pipeline(self):
        """Test processing multiple data items through a pipeline."""
        # Create multiple data items
        items = [
            MonitoringData(
                id=f"task_{i}",
                type=MonitoringDataType.CLICKUP_TASK,
                source="clickup",
                data={"id": f"task_{i}", "name": f"Task {i}", "priority": "urgent" if i % 2 == 0 else "low"},
            )
            for i in range(10)
        ]

        # Process items
        results = []
        for item in items:
            # Evaluate
            from gearmeshing_ai.scheduler.models.checking_point import CheckResultType

            is_urgent = item.get_data_field("priority") == "urgent"
            result = CheckResult(
                checking_point_name="priority_cp",
                checking_point_type="custom_cp",
                result_type=CheckResultType.MATCH if is_urgent else CheckResultType.NO_MATCH,
                should_act=is_urgent,
                reason="Priority check",
                confidence=0.9 if is_urgent else 0.1,
            )

            # Create action if needed
            if result.should_act:
                action = AIAction(
                    name=f"process_{item.id}",
                    type=AIActionType.WORKFLOW_EXECUTION,
                    workflow_name="task_workflow",
                    checking_point_name="priority_cp",
                    parameters={"item_id": item.id},
                )
                results.append(action)

            # Mark as processed
            item.mark_processed("completed" if result.should_act else "skipped")

        # Verify results
        assert len(results) == 5  # 5 urgent items out of 10
        assert all(item.processing_status == "completed" or item.processing_status == "skipped" for item in items)

    def test_ai_action_with_all_features(self):
        """Test AI action with all features enabled."""
        action = AIAction(
            name="comprehensive_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="comprehensive_workflow",
            checking_point_name="comprehensive_cp",
            timeout_seconds=1200,
            retry_attempts=5,
            retry_delay_seconds=120,
            parameters={"param1": "value1", "nested": {"param2": "value2"}},
            prompt_template_id="template_comprehensive",
            prompt_variables={"var1": "value1", "var2": "value2"},
            agent_role="sre",
            approval_required=True,
            approval_timeout_seconds=7200,
            priority=10,
            scheduled_at=datetime.utcnow(),
            execution_id="exec_comprehensive",
            parent_execution_id="parent_comprehensive",
        )

        # Serialize and deserialize
        json_str = action.model_dump_json()
        restored = AIAction.model_validate_json(json_str)

        # Verify all fields
        assert restored.name == action.name
        assert restored.timeout_seconds == 1200
        assert restored.retry_attempts == 5
        assert restored.approval_required is True
        assert restored.priority == 10
        assert restored.parameters["nested"]["param2"] == "value2"

    def test_error_handling_in_data_processing(self):
        """Test error handling during data processing."""
        data = MonitoringData(id="error_test", type=MonitoringDataType.CLICKUP_TASK, source="clickup")

        # Simulate multiple errors
        errors = ["Failed to fetch task details", "Invalid priority field", "Missing required assignee"]

        for error in errors:
            data.add_error(error)

        # Verify error handling
        assert len(data.processing_errors) == 3
        assert data.processing_status == "failed"
        assert all(error in data.processing_errors for error in errors)

    def test_data_field_operations(self):
        """Test complex data field operations."""
        data = MonitoringData(
            id="field_ops_test",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "task": {
                    "id": "task_1",
                    "name": "Test",
                    "metadata": {"created": "2026-02-18", "tags": ["tag1", "tag2"]},
                }
            },
        )

        # Get nested fields
        task_id = data.get_data_field("task.id")
        assert task_id == "task_1"

        created = data.get_data_field("task.metadata.created")
        assert created == "2026-02-18"

        # Set nested fields
        data.set_data_field("task.status", "completed")
        assert data.get_data_field("task.status") == "completed"

        data.set_data_field("task.metadata.updated", "2026-02-19")
        assert data.get_data_field("task.metadata.updated") == "2026-02-19"

    def test_monitoring_data_summary_generation(self):
        """Test monitoring data summary generation."""
        data = MonitoringData(
            id="summary_test",
            type=MonitoringDataType.SLACK_MESSAGE,
            source="slack",
            data={"user": "user_1", "text": "Help!"},
            metadata={"channel": "support"},
        )

        summary = data.get_summary()

        # Verify summary contains key information
        assert summary["id"] == "summary_test"
        assert summary["type"] == "slack_message"
        assert summary["source"] == "slack"
        assert summary["processing_status"] == "pending"
        assert "data_keys" in summary
        assert "user" in summary["data_keys"]
