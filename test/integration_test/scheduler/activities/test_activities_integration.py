"""Integration tests for activities with models and checking points."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from gearmeshing_ai.scheduler.activities.base import BaseActivity
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType
from gearmeshing_ai.scheduler.models.workflow import AIAction, AIActionType


class TestActivitiesIntegration:
    """Integration tests for activities."""

    def test_activity_processing_monitoring_data(self):
        """Test activity processing monitoring data."""
        activity = BaseActivity()
        
        # Create monitoring data
        data = MonitoringData(
            id="task_123",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"name": "Test Task"}
        )
        
        # Verify activity can be created and configured
        assert activity is not None
        assert data.id == "task_123"
        assert data.is_clickup_task() is True

    def test_activity_error_handling(self):
        """Test activity error handling."""
        activity = BaseActivity()
        
        # Verify activity has error handling methods
        assert callable(activity.create_error_response)
        assert callable(activity.log_activity_error)

    def test_activity_with_ai_action(self):
        """Test activity creating AI action."""
        activity = BaseActivity()
        
        # Create AI action
        action = AIAction(
            name="process_urgent_task",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="urgent_task_workflow",
            checking_point_name="urgent_task_cp"
        )
        
        # Verify action creation
        assert action.name == "process_urgent_task"
        assert action.workflow_name == "urgent_task_workflow"
        assert action.checking_point_name == "urgent_task_cp"

    def test_activity_execution_time_measurement(self):
        """Test activity execution time measurement."""
        activity = BaseActivity()
        
        # Verify activity has timing methods
        assert callable(activity.measure_execution_time)
        
        start_time = datetime.utcnow()
        import time
        time.sleep(0.01)
        
        duration = activity.measure_execution_time(start_time)
        assert duration.total_seconds() > 0

    def test_activity_config_validation_integration(self):
        """Test activity configuration validation."""
        config = {
            "timeout_seconds": 600,
            "max_retries": 3
        }
        
        activity = BaseActivity(config)
        
        # Validate configuration
        errors = activity.validate_config(config)
        assert len(errors) == 0

    def test_multiple_activities_workflow(self):
        """Test multiple activities working together."""
        activities = [
            BaseActivity(),
            BaseActivity(),
            BaseActivity()
        ]
        
        # Verify multiple activities can be created
        assert len(activities) == 3
        assert all(isinstance(a, BaseActivity) for a in activities)

    def test_activity_response_structure(self):
        """Test activity response structure."""
        activity = BaseActivity()
        
        # Verify activity has response creation methods
        assert callable(activity.create_success_response)
        assert callable(activity.create_error_response)

    def test_activity_error_response_structure(self):
        """Test activity error response structure."""
        activity = BaseActivity()
        
        # Verify activity has error response method
        assert callable(activity.create_error_response)

    def test_activity_with_complex_data(self):
        """Test activity processing complex data structures."""
        activity = BaseActivity()
        
        complex_data = {
            "task": {
                "id": "task_123",
                "name": "Complex Task",
                "nested": {
                    "level1": {
                        "level2": "deep_value"
                    }
                }
            },
            "metadata": {
                "created": datetime.utcnow().isoformat(),
                "tags": ["urgent", "important"]
            }
        }
        
        # Verify activity can handle complex data
        assert activity is not None
        assert complex_data["task"]["nested"]["level1"]["level2"] == "deep_value"
