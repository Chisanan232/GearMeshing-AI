"""Comprehensive unit tests for Temporal worker.

This module implements testing patterns recommended by Temporal documentation:
- Worker lifecycle management
- Sandbox restrictions configuration
- Worker metrics and status
- WorkerManager for multi-worker coordination
- Error handling and graceful shutdown
"""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest

from gearmeshing_ai.scheduler.models.config import SchedulerTemporalConfig
from gearmeshing_ai.scheduler.temporal.worker import TemporalWorker, WorkerManager


class TestTemporalWorker:
    """Test TemporalWorker class."""

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

    def test_worker_initialization(self, worker, temporal_config):
        """Test worker initializes with correct configuration."""
        assert worker.config == temporal_config
        assert worker._worker is None
        assert worker._client is None
        assert worker.is_running() is False

    def test_is_running_false_initially(self, worker):
        """Test that worker is not running initially."""
        assert worker.is_running() is False

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, worker):
        """Test stopping a worker that is not running."""
        await worker.stop()
        assert worker.is_running() is False

    def test_get_worker_info(self, worker, temporal_config):
        """Test getting worker information."""
        info = worker.get_worker_info()

        assert info["task_queue"] == temporal_config.task_queue
        assert info["worker_count"] == temporal_config.worker_count
        assert info["running"] is False
        assert "workflows" in info
        assert "activities" in info
        assert "config" in info
        assert "SmartMonitoringWorkflow" in info["workflows"]
        assert "AIWorkflowExecutor" in info["workflows"]
        assert "fetch_monitoring_data" in info["activities"]

    @pytest.mark.asyncio
    async def test_get_worker_metrics_not_running(self, worker):
        """Test getting metrics when worker is not running."""
        metrics = await worker.get_worker_metrics()

        assert metrics["status"] == "not_running"

    def test_create_sandbox_restrictions(self, worker):
        """Test creating sandbox restrictions."""
        restrictions = worker._create_sandbox_restrictions()

        assert restrictions is not None
        assert hasattr(restrictions, "passthrough_modules")
        assert isinstance(restrictions.passthrough_modules, set)

    def test_sandbox_restrictions_includes_required_modules(self, worker):
        """Test that sandbox restrictions include required modules."""
        restrictions = worker._create_sandbox_restrictions()

        assert restrictions is not None
        assert "datetime" in restrictions.passthrough_modules
        assert "json" in restrictions.passthrough_modules
        assert "pydantic" in restrictions.passthrough_modules
        assert "gearmeshing_ai" in restrictions.passthrough_modules
        assert "os" in restrictions.passthrough_modules
        assert "sys" in restrictions.passthrough_modules

    def test_setup_signal_handlers(self, worker):
        """Test setting up signal handlers."""
        # This should not raise an error
        worker._setup_signal_handlers()

    @pytest.mark.asyncio
    async def test_context_manager(self, worker):
        """Test using worker as async context manager."""
        with patch.object(worker, "start", new_callable=AsyncMock):
            with patch.object(worker, "stop", new_callable=AsyncMock):
                async with worker as w:
                    assert w is worker
                    worker.start.assert_called_once()
                worker.stop.assert_called_once()


class TestWorkerManager:
    """Test WorkerManager class for multi-worker coordination."""

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

    @pytest.fixture
    def worker(self, temporal_config):
        """Create a TemporalWorker instance."""
        return TemporalWorker(temporal_config)

    def test_manager_initialization(self, manager):
        """Test manager initializes correctly."""
        assert manager._workers == {}
        assert manager.is_running() is False

    def test_add_worker(self, manager, worker):
        """Test adding a worker to the manager."""
        manager.add_worker("worker_1", worker)

        assert "worker_1" in manager._workers
        assert manager._workers["worker_1"] is worker

    def test_add_multiple_workers(self, manager, temporal_config):
        """Test adding multiple workers to the manager."""
        worker_1 = TemporalWorker(temporal_config)
        worker_2 = TemporalWorker(temporal_config)

        manager.add_worker("worker_1", worker_1)
        manager.add_worker("worker_2", worker_2)

        assert len(manager._workers) == 2
        assert "worker_1" in manager._workers
        assert "worker_2" in manager._workers

    def test_remove_worker(self, manager, worker):
        """Test removing a worker from the manager."""
        manager.add_worker("worker_1", worker)
        assert "worker_1" in manager._workers

        manager.remove_worker("worker_1")
        assert "worker_1" not in manager._workers

    def test_remove_non_existent_worker(self, manager):
        """Test removing a non-existent worker does not raise error."""
        manager.remove_worker("non_existent")
        # Should not raise an error

    @pytest.mark.asyncio
    async def test_stop_all_when_not_running(self, manager):
        """Test stopping all workers when manager is not running."""
        await manager.stop_all()
        assert manager.is_running() is False

    def test_get_worker_status_empty(self, manager):
        """Test getting worker status when no workers are added."""
        status = manager.get_worker_status()

        assert status == {}

    def test_get_worker_status_with_workers(self, manager, temporal_config):
        """Test getting worker status with multiple workers."""
        worker_1 = TemporalWorker(temporal_config)
        worker_2 = TemporalWorker(temporal_config)

        manager.add_worker("worker_1", worker_1)
        manager.add_worker("worker_2", worker_2)

        status = manager.get_worker_status()

        assert "worker_1" in status
        assert "worker_2" in status
        assert status["worker_1"]["task_queue"] == temporal_config.task_queue
        assert status["worker_2"]["task_queue"] == temporal_config.task_queue

    def test_is_running_false_initially(self, manager):
        """Test that manager is not running initially."""
        assert manager.is_running() is False

    @pytest.mark.asyncio
    async def test_run_worker_with_error_handling(self, manager, worker):
        """Test running worker with error handling."""
        with patch.object(worker, "run_until_shutdown", new_callable=AsyncMock):
            await manager._run_worker_with_error_handling("worker_1", worker)
            worker.run_until_shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_worker_with_error_handling_exception(self, manager, worker):
        """Test running worker with error handling when exception occurs."""
        with patch.object(worker, "run_until_shutdown", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = RuntimeError("Test error")
            # Should not raise an error
            await manager._run_worker_with_error_handling("worker_1", worker)

    @pytest.mark.asyncio
    async def test_stop_worker_with_error_handling(self, manager, worker):
        """Test stopping worker with error handling."""
        with patch.object(worker, "stop", new_callable=AsyncMock):
            await manager._stop_worker_with_error_handling("worker_1", worker)
            worker.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_worker_with_error_handling_exception(self, manager, worker):
        """Test stopping worker with error handling when exception occurs."""
        with patch.object(worker, "stop", new_callable=AsyncMock) as mock_stop:
            mock_stop.side_effect = RuntimeError("Test error")
            # Should not raise an error
            await manager._stop_worker_with_error_handling("worker_1", worker)
