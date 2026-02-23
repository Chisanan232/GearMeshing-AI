"""Unit tests for schedule management."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from gearmeshing_ai.scheduler.temporal.schedules import ScheduleManager
from gearmeshing_ai.scheduler.models.config import SchedulerTemporalConfig, MonitorConfig


class TestScheduleManager:
    """Test ScheduleManager class."""

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
        client = AsyncMock()
        return client

    @pytest.fixture
    def schedule_manager(self, mock_client, temporal_config):
        """Create a ScheduleManager instance."""
        return ScheduleManager(mock_client, temporal_config)

    @pytest.mark.asyncio
    async def test_create_monitoring_schedule_with_cron(self, schedule_manager, monitor_config, mock_client):
        """Test creating a monitoring schedule with cron expression."""
        mock_handle = AsyncMock()
        mock_client.create_schedule = AsyncMock(return_value=mock_handle)

        schedule_id = "test_schedule_1"
        cron_expr = "0 9 * * *"

        result = await schedule_manager.create_monitoring_schedule(
            schedule_id=schedule_id,
            monitor_config=monitor_config,
            cron_expression=cron_expr,
        )

        assert result == schedule_id
        assert schedule_id in schedule_manager._schedules
        mock_client.create_schedule.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_monitoring_schedule_with_interval(self, schedule_manager, monitor_config, mock_client):
        """Test creating a monitoring schedule with interval."""
        mock_handle = AsyncMock()
        mock_client.create_schedule = AsyncMock(return_value=mock_handle)

        schedule_id = "test_schedule_2"
        interval_seconds = 3600

        result = await schedule_manager.create_monitoring_schedule(
            schedule_id=schedule_id,
            monitor_config=monitor_config,
            interval_seconds=interval_seconds,
        )

        assert result == schedule_id
        assert schedule_id in schedule_manager._schedules
        mock_client.create_schedule.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_monitoring_schedule_no_timing_raises_error(self, schedule_manager, monitor_config):
        """Test that creating schedule without timing raises error."""
        with pytest.raises(RuntimeError, match="Either cron_expression or interval_seconds must be provided"):
            await schedule_manager.create_monitoring_schedule(
                schedule_id="test_schedule",
                monitor_config=monitor_config,
            )

    @pytest.mark.asyncio
    async def test_create_monitoring_schedule_both_timing_raises_error(self, schedule_manager, monitor_config, mock_client):
        """Test that creating schedule with both timing raises error."""
        with pytest.raises(RuntimeError, match="Cannot specify both cron_expression and interval_seconds"):
            await schedule_manager.create_monitoring_schedule(
                schedule_id="test_schedule",
                monitor_config=monitor_config,
                cron_expression="0 9 * * *",
                interval_seconds=3600,
            )

    @pytest.mark.asyncio
    async def test_update_schedule_cron(self, schedule_manager, monitor_config, mock_client):
        """Test updating a schedule with new cron expression."""
        mock_handle = AsyncMock()
        mock_client.create_schedule = AsyncMock(return_value=mock_handle)

        schedule_id = "test_schedule"
        await schedule_manager.create_monitoring_schedule(
            schedule_id=schedule_id,
            monitor_config=monitor_config,
            cron_expression="0 9 * * *",
        )

        new_cron = "0 10 * * *"
        await schedule_manager.update_schedule(schedule_id, cron_expression=new_cron)

        assert schedule_manager._schedules[schedule_id]["cron_expression"] == new_cron
        assert schedule_manager._schedules[schedule_id]["interval_seconds"] is None

    @pytest.mark.asyncio
    async def test_update_schedule_interval(self, schedule_manager, monitor_config, mock_client):
        """Test updating a schedule with new interval."""
        mock_handle = AsyncMock()
        mock_client.create_schedule = AsyncMock(return_value=mock_handle)

        schedule_id = "test_schedule"
        await schedule_manager.create_monitoring_schedule(
            schedule_id=schedule_id,
            monitor_config=monitor_config,
            interval_seconds=3600,
        )

        new_interval = 7200
        await schedule_manager.update_schedule(schedule_id, interval_seconds=new_interval)

        assert schedule_manager._schedules[schedule_id]["interval_seconds"] == new_interval
        assert schedule_manager._schedules[schedule_id]["cron_expression"] is None

    @pytest.mark.asyncio
    async def test_update_schedule_not_found(self, schedule_manager):
        """Test updating non-existent schedule raises error."""
        with pytest.raises(RuntimeError, match="Schedule not found"):
            await schedule_manager.update_schedule("non_existent")

    @pytest.mark.asyncio
    async def test_delete_schedule(self, schedule_manager, monitor_config, mock_client):
        """Test deleting a schedule."""
        mock_handle = AsyncMock()
        mock_client.create_schedule = AsyncMock(return_value=mock_handle)

        schedule_id = "test_schedule"
        await schedule_manager.create_monitoring_schedule(
            schedule_id=schedule_id,
            monitor_config=monitor_config,
            cron_expression="0 9 * * *",
        )

        assert schedule_id in schedule_manager._schedules

        await schedule_manager.delete_schedule(schedule_id)

        assert schedule_id not in schedule_manager._schedules
        mock_handle.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_schedule_not_found(self, schedule_manager):
        """Test deleting non-existent schedule raises error."""
        with pytest.raises(RuntimeError, match="Schedule not found"):
            await schedule_manager.delete_schedule("non_existent")

    @pytest.mark.asyncio
    async def test_pause_schedule(self, schedule_manager, monitor_config, mock_client):
        """Test pausing a schedule."""
        mock_handle = AsyncMock()
        mock_client.create_schedule = AsyncMock(return_value=mock_handle)

        schedule_id = "test_schedule"
        await schedule_manager.create_monitoring_schedule(
            schedule_id=schedule_id,
            monitor_config=monitor_config,
            cron_expression="0 9 * * *",
        )

        await schedule_manager.pause_schedule(schedule_id)

        assert schedule_manager._schedules[schedule_id].get("paused") is True

    @pytest.mark.asyncio
    async def test_unpause_schedule(self, schedule_manager, monitor_config, mock_client):
        """Test unpausing a schedule."""
        mock_handle = AsyncMock()
        mock_client.create_schedule = AsyncMock(return_value=mock_handle)

        schedule_id = "test_schedule"
        await schedule_manager.create_monitoring_schedule(
            schedule_id=schedule_id,
            monitor_config=monitor_config,
            cron_expression="0 9 * * *",
        )

        await schedule_manager.pause_schedule(schedule_id)
        await schedule_manager.unpause_schedule(schedule_id)

        assert schedule_manager._schedules[schedule_id].get("paused") is False

    @pytest.mark.asyncio
    async def test_list_schedules(self, schedule_manager, monitor_config, mock_client):
        """Test listing all schedules."""
        mock_handle = AsyncMock()
        mock_client.create_schedule = AsyncMock(return_value=mock_handle)

        schedule_id_1 = "schedule_1"
        schedule_id_2 = "schedule_2"

        await schedule_manager.create_monitoring_schedule(
            schedule_id=schedule_id_1,
            monitor_config=monitor_config,
            cron_expression="0 9 * * *",
        )

        await schedule_manager.create_monitoring_schedule(
            schedule_id=schedule_id_2,
            monitor_config=monitor_config,
            interval_seconds=3600,
        )

        schedules = await schedule_manager.list_schedules()

        assert len(schedules) == 2
        assert any(s["schedule_id"] == schedule_id_1 for s in schedules)
        assert any(s["schedule_id"] == schedule_id_2 for s in schedules)

    @pytest.mark.asyncio
    async def test_get_schedule_info(self, schedule_manager, monitor_config, mock_client):
        """Test getting schedule information."""
        mock_handle = AsyncMock()
        mock_handle.describe = AsyncMock(return_value={"status": "active"})
        mock_client.create_schedule = AsyncMock(return_value=mock_handle)

        schedule_id = "test_schedule"
        await schedule_manager.create_monitoring_schedule(
            schedule_id=schedule_id,
            monitor_config=monitor_config,
            cron_expression="0 9 * * *",
        )

        info = await schedule_manager.get_schedule_info(schedule_id)

        assert info["schedule_id"] == schedule_id
        assert info["workflow"] == "SmartMonitoringWorkflow"
        assert info["cron_expression"] == "0 9 * * *"

    @pytest.mark.asyncio
    async def test_get_schedule_info_not_found(self, schedule_manager):
        """Test getting info for non-existent schedule raises error."""
        with pytest.raises(KeyError, match="Schedule not found"):
            await schedule_manager.get_schedule_info("non_existent")

    @pytest.mark.asyncio
    async def test_trigger_schedule_run(self, schedule_manager, monitor_config, mock_client):
        """Test triggering an immediate schedule run."""
        mock_handle = AsyncMock()
        mock_client.create_schedule = AsyncMock(return_value=mock_handle)
        mock_client.start_workflow = AsyncMock(return_value="workflow_123")

        schedule_id = "test_schedule"
        await schedule_manager.create_monitoring_schedule(
            schedule_id=schedule_id,
            monitor_config=monitor_config,
            cron_expression="0 9 * * *",
        )

        workflow_id = await schedule_manager.trigger_schedule_run(schedule_id)

        assert workflow_id == "workflow_123"
        mock_client.start_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_schedule_run_not_found(self, schedule_manager):
        """Test triggering run for non-existent schedule raises error."""
        with pytest.raises(KeyError, match="Schedule not found"):
            await schedule_manager.trigger_schedule_run("non_existent")

    def test_create_cron_expression(self, schedule_manager):
        """Test creating a cron expression."""
        cron = schedule_manager.create_cron_expression(
            minute="0",
            hour="9",
            day="*",
            month="*",
            day_of_week="*",
        )

        assert cron == "0 9 * * *"

    def test_create_hourly_cron(self, schedule_manager):
        """Test creating an hourly cron expression."""
        cron = schedule_manager.create_hourly_cron(minute=30)

        assert cron == "30 * * * *"

    def test_create_daily_cron(self, schedule_manager):
        """Test creating a daily cron expression."""
        cron = schedule_manager.create_daily_cron(hour=9, minute=0)

        assert cron == "0 9 * * *"

    def test_create_weekly_cron(self, schedule_manager):
        """Test creating a weekly cron expression."""
        cron = schedule_manager.create_weekly_cron(day_of_week=1, hour=9, minute=0)

        assert cron == "0 9 * * 1"

    def test_create_monthly_cron(self, schedule_manager):
        """Test creating a monthly cron expression."""
        cron = schedule_manager.create_monthly_cron(day=1, hour=9, minute=0)

        assert cron == "0 9 1 * *"
