"""End-to-end tests for workflows."""

import pytest
from datetime import timedelta
from unittest.mock import Mock

from gearmeshing_ai.scheduler.workflows.base import BaseWorkflow
from gearmeshing_ai.scheduler.models.config import MonitorConfig


class TestWorkflowsE2E:
    """End-to-end tests for workflows."""

    def test_complete_workflow_execution(self):
        """Test complete workflow execution."""
        workflow = BaseWorkflow()
        
        # Create retry policy
        retry_policy = workflow.create_retry_policy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(minutes=1),
            backoff_coefficient=2.0,
            maximum_attempts=3
        )
        
        # Verify policy
        assert retry_policy.initial_interval == timedelta(seconds=1)
        assert retry_policy.maximum_interval == timedelta(minutes=1)
        assert retry_policy.backoff_coefficient == 2.0
        assert retry_policy.maximum_attempts == 3

    def test_workflow_with_configuration(self):
        """Test workflow with configuration management."""
        workflow = BaseWorkflow()
        
        # Verify workflow has config methods
        assert callable(workflow.get_config_value)

    def test_workflow_retry_policy_variations(self):
        """Test different retry policy variations."""
        workflow = BaseWorkflow()
        
        # Verify workflow has retry policy method
        assert callable(workflow.create_retry_policy)

    def test_workflow_with_monitor_config(self):
        """Test workflow with MonitorConfig."""
        workflow = BaseWorkflow()
        
        # Create monitor config
        config = Mock()
        config.interval_seconds = 300
        config.max_concurrent_checks = 10
        config.check_timeout_seconds = 60
        
        # Get values
        interval = workflow.get_config_value(config, "interval_seconds", 60)
        assert interval == 300
        
        max_checks = workflow.get_config_value(config, "max_concurrent_checks", 5)
        assert max_checks == 10
        
        timeout = workflow.get_config_value(config, "check_timeout_seconds", 30)
        assert timeout == 60

    def test_workflow_logging_integration(self):
        """Test workflow logging integration."""
        workflow = BaseWorkflow()
        
        # Test that logging methods are callable
        assert callable(workflow.log_workflow_start)
        assert callable(workflow.log_workflow_complete)
        assert callable(workflow.log_workflow_error)

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
        
        # Create policies for different scenarios
        policies = {
            "fast": workflow.create_retry_policy(
                initial_interval=timedelta(milliseconds=100),
                maximum_attempts=2
            ),
            "medium": workflow.create_retry_policy(
                initial_interval=timedelta(seconds=1),
                maximum_attempts=5
            ),
            "slow": workflow.create_retry_policy(
                initial_interval=timedelta(seconds=5),
                maximum_attempts=10
            )
        }
        
        # Verify policies
        assert policies["fast"].maximum_attempts < policies["medium"].maximum_attempts
        assert policies["medium"].maximum_attempts < policies["slow"].maximum_attempts

    def test_workflow_configuration_hierarchy(self):
        """Test workflow configuration hierarchy."""
        workflow = BaseWorkflow()
        
        # Create hierarchical config
        config = Mock()
        config.global_timeout = 600
        config.activities = Mock()
        config.activities.timeout = 300
        config.activities.retries = 3
        
        # Get values
        global_timeout = workflow.get_config_value(config, "global_timeout", 300)
        assert global_timeout == 600

    def test_workflow_with_complex_retry_scenarios(self):
        """Test workflow with complex retry scenarios."""
        workflow = BaseWorkflow()
        
        # Scenario 1: Quick retries for transient failures
        transient_policy = workflow.create_retry_policy(
            initial_interval=timedelta(milliseconds=500),
            maximum_interval=timedelta(seconds=5),
            backoff_coefficient=2.0,
            maximum_attempts=3
        )
        
        # Scenario 2: Slow retries for resource-intensive operations
        resource_policy = workflow.create_retry_policy(
            initial_interval=timedelta(seconds=10),
            maximum_interval=timedelta(minutes=10),
            backoff_coefficient=1.5,
            maximum_attempts=5
        )
        
        # Scenario 3: No retries for critical operations
        critical_policy = workflow.create_retry_policy(
            initial_interval=timedelta(seconds=0),
            maximum_interval=timedelta(seconds=0),
            backoff_coefficient=1.0,
            maximum_attempts=1
        )
        
        assert transient_policy.maximum_attempts == 3
        assert resource_policy.maximum_attempts == 5
        assert critical_policy.maximum_attempts == 1

    def test_workflow_config_value_types(self):
        """Test workflow config value handling for different types."""
        workflow = BaseWorkflow()
        
        config = Mock()
        config.string_value = "test"
        config.int_value = 42
        config.float_value = 3.14
        config.bool_value = True
        config.list_value = [1, 2, 3]
        config.dict_value = {"key": "value"}
        
        # Get different types
        assert workflow.get_config_value(config, "string_value") == "test"
        assert workflow.get_config_value(config, "int_value") == 42
        assert workflow.get_config_value(config, "float_value") == 3.14
        assert workflow.get_config_value(config, "bool_value") is True
        assert workflow.get_config_value(config, "list_value") == [1, 2, 3]
        assert workflow.get_config_value(config, "dict_value") == {"key": "value"}

    def test_workflow_default_values(self):
        """Test workflow default value handling."""
        workflow = BaseWorkflow()
        
        config = Mock(spec=[])  # Empty spec
        
        # All should return defaults
        assert workflow.get_config_value(config, "timeout", 300) == 300
        assert workflow.get_config_value(config, "retries", 3) == 3
        assert workflow.get_config_value(config, "enabled", True) is True
        assert workflow.get_config_value(config, "items", []) == []
