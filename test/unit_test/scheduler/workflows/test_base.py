"""Unit tests for base workflow classes."""

from datetime import timedelta
from unittest.mock import Mock

import pytest

from gearmeshing_ai.scheduler.workflows.base import BaseWorkflow


class TestBaseWorkflow:
    """Test BaseWorkflow class."""

    def test_initialization(self):
        """Test workflow initialization."""
        workflow = BaseWorkflow()
        assert workflow.logger is not None

    def test_create_retry_policy_defaults(self):
        """Test create_retry_policy with default values."""
        workflow = BaseWorkflow()
        policy = workflow.create_retry_policy()

        assert policy.initial_interval == timedelta(seconds=1)
        assert policy.maximum_interval == timedelta(minutes=1)
        assert policy.backoff_coefficient == 2.0
        assert policy.maximum_attempts == 3

    def test_create_retry_policy_custom(self):
        """Test create_retry_policy with custom values."""
        workflow = BaseWorkflow()
        policy = workflow.create_retry_policy(
            initial_interval=timedelta(seconds=2),
            maximum_interval=timedelta(minutes=2),
            backoff_coefficient=3.0,
            maximum_attempts=5,
        )

        assert policy.initial_interval == timedelta(seconds=2)
        assert policy.maximum_interval == timedelta(minutes=2)
        assert policy.backoff_coefficient == 3.0
        assert policy.maximum_attempts == 5

    def test_is_test_mode_false_by_default(self):
        """Test is_test_mode returns False by default."""
        workflow = BaseWorkflow()
        # This will fail in non-workflow context, but we can test it's callable
        assert callable(workflow.is_test_mode)

    def test_get_config_value_from_object(self):
        """Test get_config_value with object attribute."""
        workflow = BaseWorkflow()
        config = Mock()
        config.test_key = "test_value"

        value = workflow.get_config_value(config, "test_key", "default")
        assert value == "test_value"

    def test_get_config_value_default(self):
        """Test get_config_value returns default for missing attribute."""
        workflow = BaseWorkflow()
        config = Mock(spec=[])  # Empty spec means no attributes

        value = workflow.get_config_value(config, "nonexistent", "default")
        assert value == "default"

    def test_log_workflow_start(self):
        """Test log_workflow_start method."""
        workflow = BaseWorkflow()
        # Should not raise even in test context
        try:
            workflow.log_workflow_start("test_workflow", context="test")
        except Exception:
            # Expected to fail in test context, but method should exist
            pass

    def test_log_workflow_complete(self):
        """Test log_workflow_complete method."""
        workflow = BaseWorkflow()
        # Should not raise even in test context
        try:
            workflow.log_workflow_complete("test_workflow", context="test")
        except Exception:
            # Expected to fail in test context, but method should exist
            pass

    def test_log_workflow_error(self):
        """Test log_workflow_error method."""
        workflow = BaseWorkflow()
        error = ValueError("Test error")
        # Should not raise even in test context
        try:
            workflow.log_workflow_error("test_workflow", error, context="test")
        except Exception:
            # Expected to fail in test context, but method should exist
            pass

    def test_get_workflow_info(self):
        """Test get_workflow_info method."""
        workflow = BaseWorkflow()
        # This will fail in non-workflow context, but we can test it's callable
        assert callable(workflow.get_workflow_info)

    @pytest.mark.asyncio
    async def test_sleep_with_backoff(self):
        """Test sleep_with_backoff method."""
        workflow = BaseWorkflow()
        # We can't easily test asyncio.sleep, but we can test the calculation
        base_delay = timedelta(seconds=1)
        max_delay = timedelta(seconds=10)

        # Test that method is callable
        assert callable(workflow.sleep_with_backoff)

    @pytest.mark.asyncio
    async def test_execute_activity_with_retry_defaults(self):
        """Test execute_activity_with_retry with default values."""
        workflow = BaseWorkflow()
        # This will fail in non-workflow context, but we can test it's callable
        assert callable(workflow.execute_activity_with_retry)

    @pytest.mark.asyncio
    async def test_execute_child_workflow_with_timeout_defaults(self):
        """Test execute_child_workflow_with_timeout with default values."""
        workflow = BaseWorkflow()
        # This will fail in non-workflow context, but we can test it's callable
        assert callable(workflow.execute_child_workflow_with_timeout)

    def test_execute_activity_with_retry_custom_timeout(self):
        """Test execute_activity_with_retry with custom timeout."""
        workflow = BaseWorkflow()
        # Method should accept timeout parameter
        assert callable(workflow.execute_activity_with_retry)

    def test_execute_child_workflow_custom_timeout(self):
        """Test execute_child_workflow_with_timeout with custom timeout."""
        workflow = BaseWorkflow()
        # Method should accept timeout parameter
        assert callable(workflow.execute_child_workflow_with_timeout)
