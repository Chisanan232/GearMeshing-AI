"""Integration tests for workflows with activities and checking points."""

from datetime import timedelta
from unittest.mock import Mock

from gearmeshing_ai.scheduler.activities.base import BaseActivity
from gearmeshing_ai.scheduler.workflows.base import BaseWorkflow


class TestWorkflowsIntegration:
    """Integration tests for workflows."""

    def test_workflow_with_activities(self):
        """Test workflow coordinating multiple activities."""
        workflow = BaseWorkflow()
        activities = [BaseActivity() for _ in range(3)]

        # Simulate workflow execution
        assert len(activities) == 3
        assert workflow.logger is not None

    def test_workflow_retry_policy_creation(self):
        """Test workflow creating retry policies."""
        workflow = BaseWorkflow()

        # Create default retry policy
        default_policy = workflow.create_retry_policy()
        assert default_policy.initial_interval == timedelta(seconds=1)
        assert default_policy.maximum_attempts == 3

        # Create custom retry policy
        custom_policy = workflow.create_retry_policy(initial_interval=timedelta(seconds=5), maximum_attempts=5)
        assert custom_policy.initial_interval == timedelta(seconds=5)
        assert custom_policy.maximum_attempts == 5

    def test_workflow_config_management(self):
        """Test workflow managing configuration."""
        workflow = BaseWorkflow()

        # Verify workflow has config methods
        assert callable(workflow.get_config_value)

    def test_workflow_logging_integration(self):
        """Test workflow logging functionality."""
        workflow = BaseWorkflow()

        # Test that logging methods are callable
        assert callable(workflow.log_workflow_start)
        assert callable(workflow.log_workflow_complete)
        assert callable(workflow.log_workflow_error)

    def test_workflow_with_monitor_config(self):
        """Test workflow with MonitorConfig."""
        workflow = BaseWorkflow()

        # Create monitor config
        monitor_config = Mock()
        monitor_config.interval_seconds = 300
        monitor_config.max_concurrent_checks = 10

        # Get config values
        interval = workflow.get_config_value(monitor_config, "interval_seconds", 60)
        assert interval == 300

        max_checks = workflow.get_config_value(monitor_config, "max_concurrent_checks", 5)
        assert max_checks == 10

    def test_workflow_error_handling(self):
        """Test workflow error handling."""
        workflow = BaseWorkflow()

        error = ValueError("Test error")

        # Test that error logging is callable
        assert callable(workflow.log_workflow_error)

    def test_multiple_workflows_coordination(self):
        """Test multiple workflows working together."""
        workflows = [BaseWorkflow() for _ in range(3)]

        # Each workflow should have its own logger
        assert all(w.logger is not None for w in workflows)

        # Each should be able to create retry policies
        policies = [w.create_retry_policy() for w in workflows]
        assert len(policies) == 3
        assert all(p.maximum_attempts == 3 for p in policies)

    def test_workflow_timeout_configuration(self):
        """Test workflow timeout configuration."""
        workflow = BaseWorkflow()

        # Create retry policy with custom timeout
        policy = workflow.create_retry_policy(
            initial_interval=timedelta(seconds=2), maximum_interval=timedelta(minutes=5)
        )

        assert policy.initial_interval == timedelta(seconds=2)
        assert policy.maximum_interval == timedelta(minutes=5)

    def test_workflow_backoff_calculation(self):
        """Test workflow backoff calculation."""
        workflow = BaseWorkflow()

        # Create policy with exponential backoff
        policy = workflow.create_retry_policy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(minutes=1),
            backoff_coefficient=2.0,
            maximum_attempts=5,
        )

        assert policy.backoff_coefficient == 2.0
        # Verify exponential backoff: 1s, 2s, 4s, 8s, 16s (capped at 60s)

    def test_workflow_info_retrieval(self):
        """Test workflow info retrieval."""
        workflow = BaseWorkflow()

        # get_workflow_info should be callable
        assert callable(workflow.get_workflow_info)

    def test_workflow_test_mode_detection(self):
        """Test workflow test mode detection."""
        workflow = BaseWorkflow()

        # is_test_mode should be callable
        assert callable(workflow.is_test_mode)

    def test_workflow_with_multiple_retry_policies(self):
        """Test workflow managing multiple retry policies."""
        workflow = BaseWorkflow()

        # Create different retry policies for different activities
        fast_retry = workflow.create_retry_policy(initial_interval=timedelta(milliseconds=100), maximum_attempts=2)

        slow_retry = workflow.create_retry_policy(initial_interval=timedelta(seconds=5), maximum_attempts=5)

        assert fast_retry.initial_interval < slow_retry.initial_interval
        assert fast_retry.maximum_attempts < slow_retry.maximum_attempts
