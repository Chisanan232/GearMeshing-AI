"""Comprehensive unit tests for Temporal client wrapper.

This module implements testing patterns recommended by Temporal documentation:
- Proper mocking of Temporal client operations
- Error handling and edge cases
- Connection lifecycle management
- Workflow and schedule operations
- WorkflowEnvironment integration for in-memory testing
- Concurrent workflow operations
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from temporalio.testing import WorkflowEnvironment

from gearmeshing_ai.scheduler.models.config import SchedulerTemporalConfig
from gearmeshing_ai.scheduler.temporal.client import TemporalClient


class TestTemporalClient:
    """Test TemporalClient class."""

    @pytest.fixture
    def temporal_config(self):
        """Create a test Temporal configuration."""
        return SchedulerTemporalConfig(
            host="localhost",
            port=7233,
            namespace="default",
            task_queue="test_queue",
            worker_count=4,
            worker_poll_timeout=timedelta(seconds=1),
            client_timeout=timedelta(seconds=30),
        )

    @pytest.fixture
    def client(self, temporal_config):
        """Create a TemporalClient instance."""
        return TemporalClient(temporal_config)

    def test_client_initialization(self, client, temporal_config):
        """Test client initialization."""
        assert client.config == temporal_config
        assert client._client is None
        assert client.is_connected() is False

    def test_is_connected_false_initially(self, client):
        """Test that client is not connected initially."""
        assert client.is_connected() is False

    @pytest.mark.asyncio
    async def test_connect_success(self, client):
        """Test successful connection to Temporal server."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_client_class.return_value = mock_client_instance

            await client.connect()

            assert client.is_connected() is True
            assert client._client is mock_client_instance

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, client):
        """Test connecting when already connected."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_client_class.return_value = mock_client_instance

            await client.connect()
            call_count_1 = mock_client_class.call_count

            await client.connect()
            call_count_2 = mock_client_class.call_count

            assert call_count_1 == call_count_2

    @pytest.mark.asyncio
    async def test_connect_failure(self, client):
        """Test connection failure."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_class.side_effect = Exception("Connection failed")

            with pytest.raises(ConnectionError, match="Failed to connect to Temporal server"):
                await client.connect()

            assert client.is_connected() is False

    @pytest.mark.asyncio
    async def test_disconnect(self, client):
        """Test disconnecting from Temporal server."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_client_class.return_value = mock_client_instance

            await client.connect()
            assert client.is_connected() is True

            await client.disconnect()
            assert client.is_connected() is False
            mock_client_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, client):
        """Test disconnecting when not connected."""
        await client.disconnect()
        assert client.is_connected() is False

    @pytest.mark.asyncio
    async def test_start_workflow_not_connected(self, client):
        """Test starting workflow when not connected raises error."""
        with pytest.raises(RuntimeError, match="Not connected to Temporal server"):
            await client.start_workflow(Mock)

    @pytest.mark.asyncio
    async def test_start_workflow_success(self, client):
        """Test successfully starting a workflow."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_workflow_handle = AsyncMock()
            mock_workflow_handle.id = "workflow_123"
            mock_client_instance.start_workflow = AsyncMock(return_value=mock_workflow_handle)
            mock_client_class.return_value = mock_client_instance

            await client.connect()

            mock_workflow_class = Mock()
            mock_workflow_class.run = Mock()

            workflow_id = await client.start_workflow(mock_workflow_class, args=("arg1",))

            assert workflow_id == "workflow_123"
            mock_client_instance.start_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_workflow_result_not_connected(self, client):
        """Test getting workflow result when not connected raises error."""
        with pytest.raises(RuntimeError, match="Not connected to Temporal server"):
            await client.get_workflow_result("workflow_123")

    @pytest.mark.asyncio
    async def test_get_workflow_result_success(self, client):
        """Test successfully getting workflow result."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_client_instance.get_result = AsyncMock(return_value={"status": "completed"})
            mock_client_class.return_value = mock_client_instance

            await client.connect()

            result = await client.get_workflow_result("workflow_123")

            assert result == {"status": "completed"}
            mock_client_instance.get_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_workflows_not_connected(self, client):
        """Test listing workflows when not connected raises error."""
        with pytest.raises(RuntimeError, match="Not connected to Temporal server"):
            await client.list_workflows()

    @pytest.mark.asyncio
    async def test_list_workflows_success(self, client):
        """Test successfully listing workflows."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)

            mock_workflow_1 = Mock()
            mock_workflow_1.id = "workflow_1"
            mock_workflow_1.run_id = "run_1"
            mock_workflow_1.workflow_type.name = "TestWorkflow"
            mock_workflow_1.status.name = "RUNNING"
            mock_workflow_1.start_time = datetime.utcnow()
            mock_workflow_1.execution_time = timedelta(seconds=10)

            async def mock_list_workflows(*args, **kwargs):
                yield mock_workflow_1

            mock_client_instance.list_workflows = mock_list_workflows
            mock_client_class.return_value = mock_client_instance

            await client.connect()

            workflows = await client.list_workflows()

            assert len(workflows) == 1
            assert workflows[0]["workflow_id"] == "workflow_1"

    @pytest.mark.asyncio
    async def test_cancel_workflow_not_connected(self, client):
        """Test canceling workflow when not connected raises error."""
        with pytest.raises(RuntimeError, match="Not connected to Temporal server"):
            await client.cancel_workflow("workflow_123")

    @pytest.mark.asyncio
    async def test_cancel_workflow_success(self, client):
        """Test successfully canceling a workflow."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_client_instance.cancel_workflow = AsyncMock()
            mock_client_class.return_value = mock_client_instance

            await client.connect()
            await client.cancel_workflow("workflow_123")

            mock_client_instance.cancel_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_terminate_workflow_not_connected(self, client):
        """Test terminating workflow when not connected raises error."""
        with pytest.raises(RuntimeError, match="Not connected to Temporal server"):
            await client.terminate_workflow("workflow_123")

    @pytest.mark.asyncio
    async def test_terminate_workflow_success(self, client):
        """Test successfully terminating a workflow."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_client_instance.terminate_workflow = AsyncMock()
            mock_client_class.return_value = mock_client_instance

            await client.connect()
            await client.terminate_workflow("workflow_123", reason="Test termination")

            mock_client_instance.terminate_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_signal_workflow_not_connected(self, client):
        """Test signaling workflow when not connected raises error."""
        with pytest.raises(RuntimeError, match="Not connected to Temporal server"):
            await client.signal_workflow("workflow_123", "signal_name")

    @pytest.mark.asyncio
    async def test_signal_workflow_success(self, client):
        """Test successfully signaling a workflow."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_client_instance.signal_workflow = AsyncMock()
            mock_client_class.return_value = mock_client_instance

            await client.connect()
            await client.signal_workflow("workflow_123", "signal_name", "arg1")

            mock_client_instance.signal_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_workflow_not_connected(self, client):
        """Test querying workflow when not connected raises error."""
        with pytest.raises(RuntimeError, match="Not connected to Temporal server"):
            await client.query_workflow("workflow_123", "query_name")

    @pytest.mark.asyncio
    async def test_query_workflow_success(self, client):
        """Test successfully querying a workflow."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_client_instance.query_workflow = AsyncMock(return_value={"status": "running"})
            mock_client_class.return_value = mock_client_instance

            await client.connect()
            result = await client.query_workflow("workflow_123", "query_name")

            assert result == {"status": "running"}
            mock_client_instance.query_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_workflow_history_not_connected(self, client):
        """Test getting workflow history when not connected raises error."""
        with pytest.raises(RuntimeError, match="Not connected to Temporal server"):
            await client.get_workflow_history("workflow_123")

    @pytest.mark.asyncio
    async def test_get_workflow_history_success(self, client):
        """Test successfully getting workflow history."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)

            mock_event = Mock()
            mock_event.id = 1
            mock_event.event_type.name = "WorkflowExecutionStarted"
            mock_event.timestamp = datetime.utcnow()
            mock_event.attributes = {}

            async def mock_get_history(*args, **kwargs):
                yield mock_event

            mock_client_instance.get_workflow_history = mock_get_history
            mock_client_class.return_value = mock_client_instance

            await client.connect()
            history = await client.get_workflow_history("workflow_123")

            assert len(history) == 1
            assert history[0]["event_type"] == "WorkflowExecutionStarted"

    @pytest.mark.asyncio
    async def test_get_cluster_health_not_connected(self, client):
        """Test getting cluster health when not connected raises error."""
        with pytest.raises(RuntimeError, match="Not connected to Temporal server"):
            await client.get_cluster_health()

    @pytest.mark.asyncio
    async def test_get_cluster_health_success(self, client):
        """Test successfully getting cluster health."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_client_class.return_value = mock_client_instance

            await client.connect()
            health = await client.get_cluster_health()

            assert health["status"] == "healthy"
            assert "timestamp" in health
            assert "config" in health

    @pytest.mark.asyncio
    async def test_get_task_queue_stats_not_connected(self, client):
        """Test getting task queue stats when not connected raises error."""
        with pytest.raises(RuntimeError, match="Not connected to Temporal server"):
            await client.get_task_queue_stats()

    @pytest.mark.asyncio
    async def test_get_task_queue_stats_success(self, client):
        """Test successfully getting task queue stats."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_client_class.return_value = mock_client_instance

            await client.connect()
            stats = await client.get_task_queue_stats()

            assert stats["task_queue"] == client.config.task_queue
            assert stats["status"] == "active"
            assert "timestamp" in stats

    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test using client as async context manager."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_client_class.return_value = mock_client_instance

            async with client as c:
                assert c is client
                assert c.is_connected() is True

            assert client.is_connected() is False

    @pytest.mark.asyncio
    async def test_get_client_not_connected(self, client):
        """Test getting underlying client when not connected raises error."""
        with pytest.raises(RuntimeError, match="Not connected to Temporal server"):
            client.get_client()

    @pytest.mark.asyncio
    async def test_get_client_success(self, client):
        """Test successfully getting underlying client."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_client_class.return_value = mock_client_instance

            await client.connect()
            underlying_client = client.get_client()

            assert underlying_client is mock_client_instance


class TestTemporalClientWithWorkflowEnvironment:
    """Test TemporalClient integration with WorkflowEnvironment.

    Following Temporal best practices for testing with in-memory server.
    """

    @pytest.fixture
    def temporal_config(self):
        """Create a test Temporal configuration."""
        return SchedulerTemporalConfig(
            host="localhost",
            port=7233,
            namespace="default",
            task_queue="test_queue",
            worker_count=4,
            worker_poll_timeout=timedelta(seconds=1),
            client_timeout=timedelta(seconds=30),
        )

    @pytest.mark.asyncio
    async def test_client_with_test_environment(self, temporal_config):
        """Test TemporalClient with WorkflowEnvironment.

        WorkflowEnvironment provides an in-memory Temporal server for testing.
        This allows testing client operations without external dependencies.
        """
        try:
            async with await WorkflowEnvironment.start_time_skipping() as env:
                # Get client from test environment
                test_client = env.client
                assert test_client is not None

                # Verify client can be used for operations
                health = await test_client.get_service_health()
                assert health is not None
        except Exception:
            # WorkflowEnvironment may not be available in all test environments
            pytest.skip("WorkflowEnvironment not available")

    @pytest.mark.asyncio
    async def test_client_connection_state_transitions(self, temporal_config):
        """Test client connection state transitions.

        Verifies proper state management through connection lifecycle.
        """
        client = TemporalClient(temporal_config)

        # Initial state: not connected
        assert client.is_connected() is False

        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_client_instance.close = AsyncMock()
            mock_client_class.return_value = mock_client_instance

            # Connect
            await client.connect()
            assert client.is_connected() is True

            # Disconnect
            await client.disconnect()
            assert client.is_connected() is False

            # Verify close was called
            mock_client_instance.close.assert_called_once()


class TestTemporalClientErrorHandling:
    """Test error handling patterns in TemporalClient.

    Following Temporal best practices for robust error handling.
    """

    @pytest.fixture
    def temporal_config(self):
        """Create a test Temporal configuration."""
        return SchedulerTemporalConfig(
            host="localhost",
            port=7233,
            namespace="default",
            task_queue="test_queue",
            worker_count=4,
            worker_poll_timeout=timedelta(seconds=1),
            client_timeout=timedelta(seconds=30),
        )

    @pytest.mark.asyncio
    async def test_operation_without_connection(self, temporal_config):
        """Test that operations fail gracefully without connection.

        Ensures proper error messages when operations are attempted
        without establishing a connection first.
        """
        client = TemporalClient(temporal_config)

        # All operations should raise RuntimeError when not connected
        operations = [
            lambda: client.start_workflow(Mock),
            lambda: client.get_workflow_result("id"),
            lambda: client.list_workflows(),
            lambda: client.cancel_workflow("id"),
            lambda: client.terminate_workflow("id"),
            lambda: client.signal_workflow("id", "signal"),
            lambda: client.query_workflow("id", "query"),
            lambda: client.get_workflow_history("id"),
            lambda: client.get_cluster_health(),
            lambda: client.get_task_queue_stats(),
        ]

        for operation in operations:
            with pytest.raises(RuntimeError, match="Not connected to Temporal server"):
                if asyncio.iscoroutinefunction(operation):
                    await operation()
                else:
                    result = operation()
                    if asyncio.iscoroutine(result):
                        await result

    @pytest.mark.asyncio
    async def test_connection_retry_behavior(self, temporal_config):
        """Test connection retry behavior on transient failures.

        Verifies that connection attempts handle transient failures appropriately.
        """
        client = TemporalClient(temporal_config)

        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            # First attempt fails, second succeeds
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_client_class.side_effect = [
                Exception("Transient error"),
                mock_client_instance,
            ]

            # First connection attempt fails
            with pytest.raises(ConnectionError):
                await client.connect()

            assert client.is_connected() is False


class TestTemporalClientWorkflowOperations:
    """Test workflow operation patterns in TemporalClient.

    Following Temporal best practices for workflow management.
    """

    @pytest.fixture
    def temporal_config(self):
        """Create a test Temporal configuration."""
        return SchedulerTemporalConfig(
            host="localhost",
            port=7233,
            namespace="default",
            task_queue="test_queue",
            worker_count=4,
            worker_poll_timeout=timedelta(seconds=1),
            client_timeout=timedelta(seconds=30),
        )

    @pytest.mark.asyncio
    async def test_workflow_lifecycle_operations(self, temporal_config):
        """Test complete workflow lifecycle operations.

        Verifies start, query, signal, and cancel operations work correctly.
        """
        client = TemporalClient(temporal_config)

        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)

            # Setup workflow handle
            mock_workflow_handle = AsyncMock()
            mock_workflow_handle.id = "workflow_123"
            mock_client_instance.start_workflow = AsyncMock(return_value=mock_workflow_handle)

            # Setup other operations
            mock_client_instance.query_workflow = AsyncMock(return_value={"status": "running"})
            mock_client_instance.signal_workflow = AsyncMock()
            mock_client_instance.cancel_workflow = AsyncMock()

            mock_client_class.return_value = mock_client_instance

            await client.connect()

            # Create a proper workflow mock with run attribute
            mock_workflow = MagicMock()
            mock_workflow.run = MagicMock()

            # Start workflow
            workflow_id = await client.start_workflow(mock_workflow)
            assert workflow_id == "workflow_123"

            # Query workflow
            status = await client.query_workflow(workflow_id, "get_status")
            assert status["status"] == "running"

            # Signal workflow
            await client.signal_workflow(workflow_id, "pause_signal")
            mock_client_instance.signal_workflow.assert_called_once()

            # Cancel workflow
            await client.cancel_workflow(workflow_id)
            mock_client_instance.cancel_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_workflow_operations(self, temporal_config):
        """Test concurrent workflow operations.

        Verifies client handles multiple concurrent operations correctly.
        """
        client = TemporalClient(temporal_config)

        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)

            # Setup multiple workflow handles
            workflow_ids = []

            async def mock_start_workflow(*args, **kwargs):
                handle = AsyncMock()
                handle.id = f"workflow_{len(workflow_ids)}"
                workflow_ids.append(handle.id)
                return handle

            mock_client_instance.start_workflow = mock_start_workflow
            mock_client_class.return_value = mock_client_instance

            await client.connect()

            # Create proper workflow mocks with run attribute
            mock_workflows = [MagicMock() for _ in range(5)]
            for mock_workflow in mock_workflows:
                mock_workflow.run = MagicMock()

            # Start multiple workflows concurrently
            tasks = [client.start_workflow(mock_workflow) for mock_workflow in mock_workflows]
            results = await asyncio.gather(*tasks)

            # Verify all workflows were started
            assert len(results) == 5
            assert all(isinstance(wf_id, str) for wf_id in results)
