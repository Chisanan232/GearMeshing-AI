"""Temporal client wrapper for the scheduler system.

This module provides a wrapper around the Temporal client with additional
functionality for workflow management, monitoring, and error handling.
"""

from datetime import datetime, timedelta
from typing import Any

from temporalio.client import Client
from temporalio.common import RetryPolicy

from gearmeshing_ai.scheduler.models.config import SchedulerTemporalConfig


class TemporalClient:
    """Temporal client wrapper with enhanced functionality.

    This class provides a wrapper around the Temporal client with additional
    methods for workflow management, monitoring, and error handling specific
    to the scheduler system.
    """

    def __init__(self, config: SchedulerTemporalConfig) -> None:
        """Initialize the Temporal client.

        Args:
            config: Temporal configuration

        """
        self.config = config
        self._client: Client | None = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to the Temporal server."""
        if self._connected and self._client:
            return

        try:
            # Create TLS configuration if needed
            tls_config = None
            # Add TLS configuration here if required

            # Create client
            self._client = Client(
                target_host=f"{self.config.host}:{self.config.port}",
                namespace=self.config.namespace,
                tls=tls_config,
                default_retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(minutes=1),
                    backoff_coefficient=2.0,
                    maximum_attempts=3,
                ),
            )

            # Test connection
            await self._client.get_service_health()
            self._connected = True

        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Failed to connect to Temporal server: {e!s}")

    async def disconnect(self) -> None:
        """Disconnect from the Temporal server."""
        if self._client:
            await self._client.close()
            self._client = None
            self._connected = False

    def is_connected(self) -> bool:
        """Check if connected to Temporal server.

        Returns:
            True if connected, False otherwise

        """
        return self._connected and self._client is not None

    async def start_workflow(
        self,
        workflow_class: type,
        args: tuple = (),
        **kwargs: Any,
    ) -> str:
        """Start a Temporal workflow.

        Args:
            workflow_class: Workflow class to start
            args: Workflow arguments
            **kwargs: Additional workflow parameters

        Returns:
            Workflow execution ID

        """
        if not self._client:
            raise RuntimeError("Not connected to Temporal server")

        try:
            result = await self._client.start_workflow(workflow_class.run, args=args, **kwargs)
            return result.id

        except Exception as e:
            raise RuntimeError(f"Failed to start workflow: {e!s}")

    async def get_workflow_result(
        self,
        workflow_id: str,
        run_id: str | None = None,
        timeout: timedelta | None = None,
    ) -> Any:
        """Get the result of a workflow.

        Args:
            workflow_id: Workflow ID
            run_id: Optional run ID
            timeout: Optional timeout

        Returns:
            Workflow result

        """
        if not self._client:
            raise RuntimeError("Not connected to Temporal server")

        try:
            result = await self._client.get_result(
                workflow_id,
                run_id=run_id,
                timeout=timeout or self.config.client_timeout,
            )
            return result

        except Exception as e:
            raise RuntimeError(f"Failed to get workflow result: {e!s}")

    async def list_workflows(
        self,
        page_size: int = 100,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        """List workflows.

        Args:
            page_size: Page size for results
            query: Optional query filter

        Returns:
            List of workflow information

        """
        if not self._client:
            raise RuntimeError("Not connected to Temporal server")

        try:
            workflows = []
            async for workflow in self._client.list_workflows(
                page_size=page_size,
                query=query,
            ):
                workflows.append(
                    {
                        "workflow_id": workflow.id,
                        "run_id": workflow.run_id,
                        "workflow_type": workflow.workflow_type.name,
                        "status": workflow.status.name,
                        "start_time": workflow.start_time,
                        "execution_time": workflow.execution_time,
                    }
                )

            return workflows

        except Exception as e:
            raise RuntimeError(f"Failed to list workflows: {e!s}")

    async def cancel_workflow(self, workflow_id: str, run_id: str | None = None) -> None:
        """Cancel a workflow.

        Args:
            workflow_id: Workflow ID
            run_id: Optional run ID

        """
        if not self._client:
            raise RuntimeError("Not connected to Temporal server")

        try:
            await self._client.cancel_workflow(workflow_id, run_id)

        except Exception as e:
            raise RuntimeError(f"Failed to cancel workflow: {e!s}")

    async def terminate_workflow(
        self,
        workflow_id: str,
        run_id: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Terminate a workflow.

        Args:
            workflow_id: Workflow ID
            run_id: Optional run ID
            reason: Optional termination reason

        """
        if not self._client:
            raise RuntimeError("Not connected to Temporal server")

        try:
            await self._client.terminate_workflow(workflow_id, run_id, reason)

        except Exception as e:
            raise RuntimeError(f"Failed to terminate workflow: {e!s}")

    async def signal_workflow(
        self,
        workflow_id: str,
        signal_name: str,
        run_id: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Send a signal to a workflow.

        Args:
            workflow_id: Workflow ID
            signal_name: Name of the signal
            run_id: Optional run ID
            *args: Signal arguments
            **kwargs: Signal keyword arguments

        """
        if not self._client:
            raise RuntimeError("Not connected to Temporal server")

        try:
            await self._client.signal_workflow(workflow_id, signal_name, run_id, *args, **kwargs)

        except Exception as e:
            raise RuntimeError(f"Failed to signal workflow: {e!s}")

    async def query_workflow(
        self,
        workflow_id: str,
        query_name: str,
        run_id: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Query a workflow.

        Args:
            workflow_id: Workflow ID
            query_name: Name of the query
            run_id: Optional run ID
            *args: Query arguments
            **kwargs: Query keyword arguments

        Returns:
            Query result

        """
        if not self._client:
            raise RuntimeError("Not connected to Temporal server")

        try:
            result = await self._client.query_workflow(workflow_id, query_name, run_id, *args, **kwargs)
            return result

        except Exception as e:
            raise RuntimeError(f"Failed to query workflow: {e!s}")

    async def get_workflow_history(
        self,
        workflow_id: str,
        run_id: str | None = None,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        """Get workflow execution history.

        Args:
            workflow_id: Workflow ID
            run_id: Optional run ID
            page_size: Page size for results

        Returns:
            List of history events

        """
        if not self._client:
            raise RuntimeError("Not connected to Temporal server")

        try:
            history_events = []
            async for event in self._client.get_workflow_history(
                workflow_id,
                run_id,
                page_size=page_size,
            ):
                history_events.append(
                    {
                        "event_id": event.id,
                        "event_type": event.event_type.name,
                        "timestamp": event.timestamp,
                        "attributes": event.attributes,
                    }
                )

            return history_events

        except Exception as e:
            raise RuntimeError(f"Failed to get workflow history: {e!s}")

    async def get_cluster_health(self) -> dict[str, Any]:
        """Get Temporal cluster health information.

        Returns:
            Cluster health information

        """
        if not self._client:
            raise RuntimeError("Not connected to Temporal server")

        try:
            health = await self._client.get_service_health()

            return {
                "status": "healthy" if health else "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "config": {
                    "host": self.config.host,
                    "port": self.config.port,
                    "namespace": self.config.namespace,
                },
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "config": {
                    "host": self.config.host,
                    "port": self.config.port,
                    "namespace": self.config.namespace,
                },
            }

    async def get_task_queue_stats(self, task_queue: str | None = None) -> dict[str, Any]:
        """Get task queue statistics.

        Args:
            task_queue: Optional task queue name (uses default if None)

        Returns:
            Task queue statistics

        """
        if not self._client:
            raise RuntimeError("Not connected to Temporal server")

        queue_name = task_queue or self.config.task_queue

        try:
            # This would require additional Temporal API calls
            # For now, return basic information
            return {
                "task_queue": queue_name,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "active",
            }

        except Exception as e:
            return {
                "task_queue": queue_name,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "error": str(e),
            }

    async def __aenter__(self) -> "TemporalClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()

    def get_client(self) -> Client:
        """Get the underlying Temporal client.

        Returns:
            Temporal client instance

        Raises:
            RuntimeError: If not connected

        """
        if not self._client:
            raise RuntimeError("Not connected to Temporal server")

        return self._client
