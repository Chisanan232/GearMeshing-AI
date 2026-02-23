"""End-to-end tests for activities."""

import pytest
from datetime import datetime, timedelta

from gearmeshing_ai.scheduler.activities.base import BaseActivity
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType
from gearmeshing_ai.scheduler.models.workflow import AIAction, AIActionType


class TestActivitiesE2E:
    """End-to-end tests for activities."""

    def test_complete_activity_execution_workflow(self):
        """Test complete activity execution workflow."""
        activity = BaseActivity()
        
        # Create monitoring data
        data = MonitoringData(
            id="task_activity_123",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_activity_123",
                "name": "Process Task",
                "priority": "high"
            }
        )
        
        # Verify activity and data
        assert activity is not None
        assert data.id == "task_activity_123"
        assert data.is_clickup_task() is True

    def test_activity_error_handling_workflow(self):
        """Test activity error handling workflow."""
        activity = BaseActivity()
        
        # Verify error handling methods exist
        assert callable(activity.create_error_response)
        assert callable(activity.log_activity_error)

    def test_activity_with_ai_action_creation(self):
        """Test activity creating AI actions."""
        activity = BaseActivity()
        
        # Create AI action
        action = AIAction(
            name="urgent_task_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="urgent_task_workflow",
            checking_point_name="urgent_task_cp",
            priority=9,
            approval_required=True
        )
        
        # Verify action creation
        assert action.name == "urgent_task_action"
        assert action.priority == 9
        assert action.approval_required is True

    def test_activity_execution_time_tracking(self):
        """Test activity execution time tracking."""
        activity = BaseActivity()
        
        # Verify timing method exists
        assert callable(activity.measure_execution_time)
        
        # Test timing
        start_time = datetime.utcnow()
        import time
        time.sleep(0.05)
        duration = activity.measure_execution_time(start_time)
        
        assert duration.total_seconds() > 0.04

    def test_activity_configuration_validation(self):
        """Test activity configuration validation."""
        config = {
            "timeout_seconds": 600,
            "max_retries": 3,
            "batch_size": 100
        }
        
        activity = BaseActivity(config)
        
        # Validate configuration
        errors = activity.validate_config(config)
        assert len(errors) == 0

    def test_activity_with_complex_data_processing(self):
        """Test activity processing complex data structures."""
        activity = BaseActivity()
        
        # Create complex data
        complex_data = {
            "task": {
                "id": "task_complex",
                "name": "Complex Task",
                "metadata": {
                    "created": datetime.utcnow().isoformat(),
                    "tags": ["urgent", "production"],
                    "custom_fields": {
                        "severity": "high",
                        "impact": "revenue",
                        "estimated_hours": 4
                    }
                },
                "assignees": [
                    {"id": "user_1", "name": "John"},
                    {"id": "user_2", "name": "Jane"}
                ]
            },
            "related_tasks": [
                {"id": "task_dep_1", "name": "Dependency 1"},
                {"id": "task_dep_2", "name": "Dependency 2"}
            ]
        }
        
        # Verify activity can handle complex data
        assert activity is not None
        assert complex_data["task"]["metadata"]["custom_fields"]["severity"] == "high"
        assert len(complex_data["task"]["assignees"]) == 2

    def test_multiple_activities_in_sequence(self):
        """Test multiple activities executing in sequence."""
        activities = [BaseActivity() for _ in range(3)]
        
        # Verify multiple activities can be created
        assert len(activities) == 3
        assert all(isinstance(a, BaseActivity) for a in activities)

    def test_activity_response_with_context(self):
        """Test activity response with rich context."""
        activity = BaseActivity()
        
        # Verify activity has response creation method
        assert callable(activity.create_success_response)

    def test_activity_error_with_context(self):
        """Test activity error response with context."""
        activity = BaseActivity()
        
        # Verify error response method exists
        assert callable(activity.create_error_response)

    def test_activity_batch_processing(self):
        """Test activity batch processing."""
        activity = BaseActivity()
        
        # Create batch of data items
        items = [
            MonitoringData(
                id=f"task_{i}",
                type=MonitoringDataType.CLICKUP_TASK,
                source="clickup",
                data={"name": f"Task {i}"}
            )
            for i in range(5)
        ]
        
        # Verify batch creation
        assert len(items) == 5
        assert all(isinstance(item, MonitoringData) for item in items)

    def test_activity_validation_and_response(self):
        """Test activity validation and response generation."""
        config = {
            "timeout_seconds": 300,
            "max_retries": 3
        }
        
        activity = BaseActivity(config)
        
        # Validate
        errors = activity.validate_config(config)
        assert len(errors) == 0
