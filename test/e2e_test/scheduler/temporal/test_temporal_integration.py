"""End-to-end tests for Temporal integration.

This module provides comprehensive end-to-end tests for the temporal scheduler package,
verifying all core features work together correctly:
- TemporalClient: Connection, workflow management, monitoring
- TemporalWorker: Worker lifecycle, configuration, sandbox setup
- ScheduleManager: Schedule lifecycle, cron expressions, triggering
- WorkerManager: Multi-worker coordination and management
- Integration: All components working together
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from gearmeshing_ai.scheduler.models.config import MonitorConfig, SchedulerTemporalConfig
from gearmeshing_ai.scheduler.temporal.client import TemporalClient
from gearmeshing_ai.scheduler.temporal.schedules import ScheduleManager
from gearmeshing_ai.scheduler.temporal.worker import TemporalWorker, WorkerManager


class TestTemporalClientIntegration:
    """End-to-end tests for TemporalClient."""

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

    @pytest.mark.asyncio
    async def test_client_full_lifecycle(self, client):
        """Test complete client lifecycle: connect, use, disconnect."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_client_instance.close = AsyncMock()
            mock_client_class.return_value = mock_client_instance

            # Connect
            await client.connect()
            assert client.is_connected() is True

            # Use client
            assert client.get_client() is mock_client_instance

            # Disconnect
            await client.disconnect()
            assert client.is_connected() is False
            mock_client_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_lifecycle(self, client):
        """Test complete workflow lifecycle: start, query, cancel."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)

            mock_workflow_handle = AsyncMock()
            mock_workflow_handle.id = "workflow_123"
            mock_client_instance.start_workflow = AsyncMock(return_value=mock_workflow_handle)
            mock_client_instance.query_workflow = AsyncMock(return_value={"status": "running"})
            mock_client_instance.cancel_workflow = AsyncMock()

            mock_client_class.return_value = mock_client_instance

            await client.connect()

            # Start workflow
            mock_workflow_class = Mock()
            mock_workflow_class.run = Mock()
            workflow_id = await client.start_workflow(mock_workflow_class)
            assert workflow_id == "workflow_123"

            # Query workflow
            status = await client.query_workflow(workflow_id, "get_status")
            assert status["status"] == "running"

            # Cancel workflow
            await client.cancel_workflow(workflow_id)
            mock_client_instance.cancel_workflow.assert_called_once()

            await client.disconnect()

    @pytest.mark.asyncio
    async def test_multiple_workflows_management(self, client):
        """Test managing multiple workflows concurrently."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)

            workflow_ids = []

            async def mock_start_workflow(*args, **kwargs):
                handle = AsyncMock()
                handle.id = f"workflow_{len(workflow_ids)}"
                workflow_ids.append(handle.id)
                return handle

            mock_client_instance.start_workflow = mock_start_workflow
            mock_client_class.return_value = mock_client_instance

            await client.connect()

            # Start multiple workflows
            mock_workflow_class = Mock()
            mock_workflow_class.run = Mock()

            ids = []
            for i in range(3):
                wf_id = await client.start_workflow(mock_workflow_class)
                ids.append(wf_id)

            assert len(ids) == 3
            assert all(isinstance(wf_id, str) for wf_id in ids)

            await client.disconnect()

    @pytest.mark.asyncio
    async def test_workflow_result_retrieval(self, client):
        """Test retrieving workflow execution results."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_client_instance.get_result = AsyncMock(return_value={"result": "success", "data": "test_data"})
            mock_client_class.return_value = mock_client_instance

            await client.connect()

            # Get workflow result
            result = await client.get_workflow_result("workflow_123")
            assert result["result"] == "success"
            assert result["data"] == "test_data"

            await client.disconnect()

    @pytest.mark.asyncio
    async def test_list_workflows(self, client):
        """Test listing all workflows."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)

            mock_workflow_1 = Mock()
            mock_workflow_1.id = "workflow_1"
            mock_workflow_1.run_id = "run_1"
            mock_workflow_1.workflow_type.name = "TestWorkflow"
            mock_workflow_1.status.name = "COMPLETED"
            mock_workflow_1.start_time = datetime.utcnow()
            mock_workflow_1.execution_time = timedelta(seconds=10)

            async def mock_list_workflows(*args, **kwargs):
                yield mock_workflow_1

            mock_client_instance.list_workflows = mock_list_workflows
            mock_client_class.return_value = mock_client_instance

            await client.connect()

            # List workflows
            workflows = await client.list_workflows()
            assert len(workflows) == 1
            assert workflows[0]["workflow_id"] == "workflow_1"
            assert workflows[0]["status"] == "COMPLETED"

            await client.disconnect()

    @pytest.mark.asyncio
    async def test_client_context_manager(self, client):
        """Test using client as async context manager."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_client_instance.close = AsyncMock()
            mock_client_class.return_value = mock_client_instance

            async with client as c:
                assert c.is_connected() is True
                assert c is client

            assert client.is_connected() is False
            mock_client_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_queue_stats(self, client):
        """Test retrieving task queue statistics."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_client_class.return_value = mock_client_instance

            await client.connect()

            # Get task queue stats
            stats = await client.get_task_queue_stats()
            assert stats["task_queue"] == client.config.task_queue
            assert stats["status"] == "active"
            assert "timestamp" in stats

            await client.disconnect()


class TestScheduleManagerIntegration:
    """End-to-end tests for ScheduleManager."""

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
    def monitor_config(self):
        """Create a test monitor configuration."""
        return MonitorConfig(
            name="test_monitor",
            enabled=True,
            checking_points=[],
        )

    @pytest.fixture
    def mock_client(self):
        """Create a mock Temporal client."""
        return AsyncMock()

    @pytest.fixture
    def schedule_manager(self, mock_client, temporal_config):
        """Create a ScheduleManager instance."""
        return ScheduleManager(mock_client, temporal_config)

    @pytest.mark.asyncio
    async def test_schedule_full_lifecycle(self, schedule_manager, monitor_config, mock_client):
        """Test complete schedule lifecycle: create, update, pause, unpause, delete."""
        mock_handle = AsyncMock()
        mock_handle.describe = AsyncMock(return_value={"status": "active"})
        mock_handle.update = AsyncMock()
        mock_handle.delete = AsyncMock()
        mock_client.create_schedule = AsyncMock(return_value=mock_handle)

        schedule_id = "test_schedule"

        # Create schedule
        result = await schedule_manager.create_monitoring_schedule(
            schedule_id=schedule_id,
            monitor_config=monitor_config,
            cron_expression="0 9 * * *",
        )
        assert result == schedule_id

        # Get schedule info
        info = await schedule_manager.get_schedule_info(schedule_id)
        assert info["schedule_id"] == schedule_id

        # Update schedule
        await schedule_manager.update_schedule(schedule_id, cron_expression="0 10 * * *")
        assert schedule_manager._schedules[schedule_id]["cron_expression"] == "0 10 * * *"

        # Pause schedule
        await schedule_manager.pause_schedule(schedule_id)
        assert schedule_manager._schedules[schedule_id].get("paused") is True

        # Unpause schedule
        await schedule_manager.unpause_schedule(schedule_id)
        assert schedule_manager._schedules[schedule_id].get("paused") is False

        # Delete schedule
        await schedule_manager.delete_schedule(schedule_id)
        assert schedule_id not in schedule_manager._schedules
        mock_handle.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_schedules_management(self, schedule_manager, monitor_config, mock_client):
        """Test managing multiple schedules concurrently."""
        mock_handle = AsyncMock()
        mock_client.create_schedule = AsyncMock(return_value=mock_handle)

        # Create multiple schedules
        schedule_ids = []
        for i in range(3):
            schedule_id = f"schedule_{i}"
            await schedule_manager.create_monitoring_schedule(
                schedule_id=schedule_id,
                monitor_config=monitor_config,
                cron_expression=f"0 {9 + i} * * *",
            )
            schedule_ids.append(schedule_id)

        # List all schedules
        schedules = await schedule_manager.list_schedules()
        assert len(schedules) == 3

        # Update each schedule
        for schedule_id in schedule_ids:
            await schedule_manager.update_schedule(schedule_id, interval_seconds=3600)

        # Verify updates
        for schedule_id in schedule_ids:
            info = await schedule_manager.get_schedule_info(schedule_id)
            assert info["interval_seconds"] == 3600

    @pytest.mark.asyncio
    async def test_schedule_cron_expression_helpers(self, schedule_manager):
        """Test cron expression helper methods."""
        # Hourly
        hourly_cron = schedule_manager.create_hourly_cron(minute=30)
        assert hourly_cron == "30 * * * *"

        # Daily
        daily_cron = schedule_manager.create_daily_cron(hour=9, minute=0)
        assert daily_cron == "0 9 * * *"

        # Weekly
        weekly_cron = schedule_manager.create_weekly_cron(day_of_week=1, hour=9, minute=0)
        assert weekly_cron == "0 9 * * 1"

        # Monthly
        monthly_cron = schedule_manager.create_monthly_cron(day=1, hour=9, minute=0)
        assert monthly_cron == "0 9 1 * *"

    @pytest.mark.asyncio
    async def test_trigger_schedule_run(self, schedule_manager, monitor_config, mock_client):
        """Test triggering an immediate schedule run."""
        mock_handle = AsyncMock()
        mock_client.create_schedule = AsyncMock(return_value=mock_handle)
        mock_client.start_workflow = AsyncMock(return_value="triggered_workflow_123")

        # Create schedule
        schedule_id = "test_schedule"
        await schedule_manager.create_monitoring_schedule(
            schedule_id=schedule_id,
            monitor_config=monitor_config,
            cron_expression="0 9 * * *",
        )

        # Trigger immediate run
        workflow_id = await schedule_manager.trigger_schedule_run(schedule_id)
        assert workflow_id == "triggered_workflow_123"
        mock_client.start_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_with_time_constraints(self, schedule_manager, monitor_config, mock_client):
        """Test creating schedule with start and end time constraints."""
        mock_handle = AsyncMock()
        mock_handle.describe = AsyncMock(return_value={"status": "active"})
        mock_client.create_schedule = AsyncMock(return_value=mock_handle)

        schedule_id = "constrained_schedule"
        start_time = datetime.utcnow() + timedelta(hours=1)
        end_time = datetime.utcnow() + timedelta(days=30)

        # Create schedule with time constraints
        result = await schedule_manager.create_monitoring_schedule(
            schedule_id=schedule_id,
            monitor_config=monitor_config,
            cron_expression="0 9 * * *",
            start_at=start_time,
            end_at=end_time,
        )

        assert result == schedule_id
        info = await schedule_manager.get_schedule_info(schedule_id)
        assert info["start_at"] == start_time
        assert info["end_at"] == end_time

    @pytest.mark.asyncio
    async def test_schedule_run_history(self, schedule_manager, monitor_config, mock_client):
        """Test retrieving schedule run history."""
        mock_handle = AsyncMock()
        mock_client.create_schedule = AsyncMock(return_value=mock_handle)

        schedule_id = "history_schedule"
        await schedule_manager.create_monitoring_schedule(
            schedule_id=schedule_id,
            monitor_config=monitor_config,
            cron_expression="0 9 * * *",
        )

        # Get schedule runs (currently returns empty list)
        runs = await schedule_manager.get_schedule_runs(schedule_id)
        assert isinstance(runs, list)


class TestWorkerIntegration:
    """End-to-end tests for TemporalWorker."""

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
    def worker(self, temporal_config):
        """Create a TemporalWorker instance."""
        return TemporalWorker(temporal_config)

    def test_worker_configuration(self, worker, temporal_config):
        """Test worker configuration is properly set."""
        info = worker.get_worker_info()

        assert info["task_queue"] == temporal_config.task_queue
        assert info["worker_count"] == temporal_config.worker_count
        assert "SmartMonitoringWorkflow" in info["workflows"]
        assert "AIWorkflowExecutor" in info["workflows"]
        assert "fetch_monitoring_data" in info["activities"]
        assert "evaluate_checking_point" in info["activities"]

    def test_sandbox_configuration(self, worker):
        """Test sandbox configuration is properly set."""
        restrictions = worker._create_sandbox_restrictions()

        # Verify sandbox restrictions are created
        assert restrictions is not None
        assert hasattr(restrictions, "passthrough_modules")

        # Verify modules are in passthrough_modules
        assert "datetime" in restrictions.passthrough_modules
        assert "pydantic" in restrictions.passthrough_modules
        assert "gearmeshing_ai" in restrictions.passthrough_modules
        assert "json" in restrictions.passthrough_modules
        assert "os" in restrictions.passthrough_modules

    @pytest.mark.asyncio
    async def test_worker_metrics(self, worker):
        """Test retrieving worker metrics."""
        # Metrics when not running
        metrics = await worker.get_worker_metrics()
        assert metrics["status"] == "not_running"

    def test_worker_context_manager(self, worker):
        """Test using worker as async context manager."""
        # Verify context manager methods exist
        assert hasattr(worker, "__aenter__")
        assert hasattr(worker, "__aexit__")

    def test_worker_signal_handler_setup(self, worker):
        """Test signal handler setup for graceful shutdown."""
        # Should not raise any errors
        worker._setup_signal_handlers()
        assert worker.is_running() is False


class TestWorkerManagerIntegration:
    """End-to-end tests for WorkerManager."""

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
    def manager(self):
        """Create a WorkerManager instance."""
        return WorkerManager()

    def test_multi_worker_setup(self, manager, temporal_config):
        """Test setting up multiple workers with different configurations."""
        # Create workers with different task queues
        configs = [
            SchedulerTemporalConfig(
                host="localhost",
                port=7233,
                namespace="default",
                task_queue=f"queue_{i}",
                worker_count=4,
                worker_poll_timeout=timedelta(seconds=1),
                client_timeout=timedelta(seconds=30),
            )
            for i in range(3)
        ]

        workers = [TemporalWorker(config) for config in configs]

        for i, worker in enumerate(workers):
            manager.add_worker(f"worker_{i}", worker)

        # Verify all workers are added
        status = manager.get_worker_status()
        assert len(status) == 3

        # Verify each worker has correct configuration
        for i in range(3):
            assert f"worker_{i}" in status
            assert status[f"worker_{i}"]["task_queue"] == f"queue_{i}"

    def test_worker_lifecycle_management(self, manager, temporal_config):
        """Test adding and removing workers."""
        worker_1 = TemporalWorker(temporal_config)
        worker_2 = TemporalWorker(temporal_config)

        # Add workers
        manager.add_worker("worker_1", worker_1)
        manager.add_worker("worker_2", worker_2)
        assert len(manager._workers) == 2

        # Remove one worker
        manager.remove_worker("worker_1")
        assert len(manager._workers) == 1
        assert "worker_1" not in manager._workers
        assert "worker_2" in manager._workers

        # Remove remaining worker
        manager.remove_worker("worker_2")
        assert len(manager._workers) == 0

    @pytest.mark.asyncio
    async def test_concurrent_worker_stop_all(self, manager, temporal_config):
        """Test stopping all workers concurrently."""
        worker_1 = TemporalWorker(temporal_config)
        worker_2 = TemporalWorker(temporal_config)
        worker_3 = TemporalWorker(temporal_config)

        manager.add_worker("worker_1", worker_1)
        manager.add_worker("worker_2", worker_2)
        manager.add_worker("worker_3", worker_3)

        # Stop all workers
        await manager.stop_all()

        # Verify all workers are stopped
        assert manager.is_running() is False
        assert all(not worker.is_running() for worker in manager._workers.values())

    def test_manager_worker_error_handling(self, manager, temporal_config):
        """Test error handling in worker management."""
        # Remove non-existent worker should not raise error
        manager.remove_worker("non_existent")

        # Add and remove workers should work correctly
        worker = TemporalWorker(temporal_config)
        manager.add_worker("test_worker", worker)
        assert "test_worker" in manager._workers

        manager.remove_worker("test_worker")
        assert "test_worker" not in manager._workers


class TestTemporalComponentsIntegration:
    """End-to-end tests for all Temporal components working together."""

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
    def monitor_config(self):
        """Create a test monitor configuration."""
        return MonitorConfig(
            name="test_monitor",
            enabled=True,
            checking_points=[],
        )

    @pytest.mark.asyncio
    async def test_complete_temporal_workflow(self, temporal_config, monitor_config):
        """Test complete workflow with client, worker, and schedules."""
        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_service_health = AsyncMock(return_value=True)
            mock_client_instance.close = AsyncMock()

            mock_handle = AsyncMock()
            mock_handle.id = "workflow_123"
            mock_handle.describe = AsyncMock(return_value={"status": "active"})
            mock_handle.delete = AsyncMock()

            mock_client_instance.create_schedule = AsyncMock(return_value=mock_handle)
            mock_client_instance.start_workflow = AsyncMock(return_value=mock_handle)

            mock_client_class.return_value = mock_client_instance

            # Initialize components
            client = TemporalClient(temporal_config)
            worker = TemporalWorker(temporal_config)
            schedule_manager = ScheduleManager(mock_client_instance, temporal_config)

            # Connect client
            await client.connect()
            assert client.is_connected() is True

            # Create schedule
            schedule_id = "monitoring_schedule"
            await schedule_manager.create_monitoring_schedule(
                schedule_id=schedule_id,
                monitor_config=monitor_config,
                cron_expression="0 9 * * *",
            )

            # Verify schedule was created
            info = await schedule_manager.get_schedule_info(schedule_id)
            assert info["schedule_id"] == schedule_id

            # Verify worker is configured
            worker_info = worker.get_worker_info()
            assert worker_info["task_queue"] == temporal_config.task_queue

            # Clean up
            await schedule_manager.delete_schedule(schedule_id)
            await client.disconnect()
            assert client.is_connected() is False

    @pytest.mark.asyncio
    async def test_error_handling_across_components(self, temporal_config):
        """Test error handling across all components."""
        # Test client connection error
        client = TemporalClient(temporal_config)

        with patch("gearmeshing_ai.scheduler.temporal.client.Client") as mock_client_class:
            mock_client_class.side_effect = Exception("Connection failed")

            with pytest.raises(ConnectionError):
                await client.connect()

        # Test schedule manager with invalid schedule
        mock_client = AsyncMock()
        schedule_manager = ScheduleManager(mock_client, temporal_config)

        with pytest.raises(KeyError):
            await schedule_manager.get_schedule_info("non_existent")

        # Test worker initialization (should not raise)
        worker = TemporalWorker(temporal_config)
        assert worker.is_running() is False
