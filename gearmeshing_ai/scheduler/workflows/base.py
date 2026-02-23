"""Base workflow utilities for the scheduler system.

This module provides base classes and common functionality for all Temporal
workflows in the scheduler system.
"""

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

from gearmeshing_ai.scheduler.models.config import MonitorConfig


class BaseWorkflow:
    """Base class for all scheduler workflows.

    Provides common functionality and utilities for Temporal workflows,
    including logging, error handling, and activity execution helpers.
    """

    def __init__(self) -> None:
        """Initialize the base workflow."""
        self.logger = workflow.logger

    async def execute_activity_with_retry(
        self,
        activity: Any,
        *args: Any,
        timeout: timedelta | None = None,
        retry_policy: RetryPolicy | None = None,
        **kwargs: Any,
    ) -> Any:
        """Execute an activity with retry policy.

        Args:
            activity: Activity to execute
            *args: Activity arguments
            timeout: Activity timeout
            retry_policy: Retry policy for the activity
            **kwargs: Additional keyword arguments

        Returns:
            Activity result

        """
        # Default retry policy if not provided
        if retry_policy is None:
            retry_policy = RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(minutes=1),
                backoff_coefficient=2.0,
                maximum_attempts=3,
            )

        # Default timeout if not provided
        if timeout is None:
            timeout = timedelta(minutes=5)

        return await workflow.execute_activity(
            activity,
            *args,
            start_to_close_timeout=timeout,
            retry_policy=retry_policy,
            **kwargs,
        )

    async def execute_child_workflow_with_timeout(
        self,
        child_workflow: Any,
        *args: Any,
        timeout: timedelta | None = None,
        **kwargs: Any,
    ) -> Any:
        """Execute a child workflow with timeout.

        Args:
            child_workflow: Child workflow to execute
            *args: Workflow arguments
            timeout: Workflow timeout
            **kwargs: Additional keyword arguments

        Returns:
            Child workflow result

        """
        # Default timeout if not provided
        if timeout is None:
            timeout = timedelta(minutes=10)

        return await workflow.execute_child_workflow(
            child_workflow,
            *args,
            execution_timeout=timeout,
            **kwargs,
        )

    def log_workflow_start(self, workflow_name: str, **context: Any) -> None:
        """Log workflow start with context.

        Args:
            workflow_name: Name of the workflow
            **context: Additional context information

        """
        self.logger.info(
            f"Starting workflow: {workflow_name}",
            extra={
                "workflow_name": workflow_name,
                "workflow_id": workflow.info().workflow_id,
                "run_id": workflow.info().run_id,
                **context,
            },
        )

    def log_workflow_complete(self, workflow_name: str, **context: Any) -> None:
        """Log workflow completion with context.

        Args:
            workflow_name: Name of the workflow
            **context: Additional context information

        """
        self.logger.info(
            f"Completed workflow: {workflow_name}",
            extra={
                "workflow_name": workflow_name,
                "workflow_id": workflow.info().workflow_id,
                "run_id": workflow.info().run_id,
                **context,
            },
        )

    def log_workflow_error(self, workflow_name: str, error: Exception, **context: Any) -> None:
        """Log workflow error with context.

        Args:
            workflow_name: Name of the workflow
            error: Error that occurred
            **context: Additional context information

        """
        self.logger.error(
            f"Error in workflow: {workflow_name}: {error!s}",
            extra={
                "workflow_name": workflow_name,
                "workflow_id": workflow.info().workflow_id,
                "run_id": workflow.info().run_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                **context,
            },
            exc_info=True,
        )

    def get_workflow_info(self) -> dict[str, Any]:
        """Get current workflow information.

        Returns:
            Dictionary containing workflow information

        """
        info = workflow.info()
        return {
            "workflow_id": info.workflow_id,
            "run_id": info.run_id,
            "workflow_type": info.workflow_type.name,
            "attempt": info.attempt,
            "execution_timeout": info.execution_timeout.total_seconds() if info.execution_timeout else None,
            "run_timeout": info.run_timeout.total_seconds() if info.run_timeout else None,
        }

    async def sleep_with_backoff(self, base_delay: timedelta, max_delay: timedelta, attempt: int) -> None:
        """Sleep with exponential backoff.

        Args:
            base_delay: Base delay duration
            max_delay: Maximum delay duration
            attempt: Current attempt number

        """
        # Calculate exponential backoff delay
        delay = min(base_delay * (2**attempt), max_delay)
        await asyncio.sleep(delay.total_seconds())

    def create_retry_policy(
        self,
        initial_interval: timedelta = timedelta(seconds=1),
        maximum_interval: timedelta = timedelta(minutes=1),
        backoff_coefficient: float = 2.0,
        maximum_attempts: int = 3,
    ) -> RetryPolicy:
        """Create a retry policy with specified parameters.

        Args:
            initial_interval: Initial retry interval
            maximum_interval: Maximum retry interval
            backoff_coefficient: Backoff coefficient
            maximum_attempts: Maximum number of attempts

        Returns:
            Configured retry policy

        """
        return RetryPolicy(
            initial_interval=initial_interval,
            maximum_interval=maximum_interval,
            backoff_coefficient=backoff_coefficient,
            maximum_attempts=maximum_attempts,
        )

    def is_test_mode(self) -> bool:
        """Check if workflow is running in test mode.

        Returns:
            True if running in test mode

        """
        # Check if test mode is indicated in workflow info or environment
        info = workflow.info()
        return (hasattr(info, "test_mode") and info.test_mode) or workflow.info().workflow_type.name.startswith("test_")

    def get_config_value(self, config: MonitorConfig, key: str, default: Any = None) -> Any:
        """Get a configuration value with fallback to default.

        Args:
            config: Configuration object
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default

        """
        if hasattr(config, key):
            return getattr(config, key)
        return default
