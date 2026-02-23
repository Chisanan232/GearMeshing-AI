"""Schedule management for the scheduler system.

This module provides functionality for managing Temporal schedules,
including creating, updating, and deleting recurring workflows.
"""

from datetime import datetime
from typing import Any

from temporalio.client import Client

from gearmeshing_ai.scheduler.models.config import MonitorConfig, SchedulerTemporalConfig


class ScheduleManager:
    """Manager for Temporal schedules.

    This class provides functionality for managing Temporal schedules,
    allowing for the creation, update, and deletion of recurring workflows.
    """

    def __init__(self, client: Client, config: SchedulerTemporalConfig) -> None:
        """Initialize the schedule manager.

        Args:
            client: Temporal client
            config: Temporal configuration

        """
        self.client = client
        self.config = config
        self._schedules: dict[str, dict[str, Any]] = {}

    async def create_monitoring_schedule(
        self,
        schedule_id: str,
        monitor_config: MonitorConfig,
        cron_expression: str | None = None,
        interval_seconds: int | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> str:
        """Create a monitoring workflow schedule.

        Args:
            schedule_id: Unique schedule identifier
            monitor_config: Monitoring configuration
            cron_expression: Optional cron expression
            interval_seconds: Optional interval in seconds
            start_at: Optional start time
            end_at: Optional end time

        Returns:
            Schedule ID

        """
        try:
            # Validate schedule parameters
            if not cron_expression and not interval_seconds:
                raise ValueError("Either cron_expression or interval_seconds must be provided")

            if cron_expression and interval_seconds:
                raise ValueError("Cannot specify both cron_expression and interval_seconds")

            # Create schedule specification
            schedule_spec = {
                "id": schedule_id,
                "workflow": "SmartMonitoringWorkflow",
                "args": (monitor_config,),
                "memo": {
                    "schedule_type": "monitoring",
                    "config_name": monitor_config.name,
                    "created_at": datetime.utcnow().isoformat(),
                },
            }

            # Add timing information
            if cron_expression:
                schedule_spec["cron"] = cron_expression
            elif interval_seconds:
                schedule_spec["interval"] = f"{interval_seconds}s"

            if start_at:
                schedule_spec["start_at"] = start_at

            if end_at:
                schedule_spec["end_at"] = end_at

            # Create the schedule
            schedule_handle = await self.client.create_schedule(**schedule_spec)

            # Store schedule information
            self._schedules[schedule_id] = {
                "schedule_id": schedule_id,
                "workflow": "SmartMonitoringWorkflow",
                "monitor_config": monitor_config,
                "cron_expression": cron_expression,
                "interval_seconds": interval_seconds,
                "start_at": start_at,
                "end_at": end_at,
                "created_at": datetime.utcnow(),
                "handle": schedule_handle,
            }

            return schedule_id

        except Exception as e:
            raise RuntimeError(f"Failed to create monitoring schedule: {e!s}")

    async def update_schedule(
        self,
        schedule_id: str,
        cron_expression: str | None = None,
        interval_seconds: int | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        paused: bool | None = None,
    ) -> None:
        """Update an existing schedule.

        Args:
            schedule_id: Schedule ID
            cron_expression: Optional new cron expression
            interval_seconds: Optional new interval in seconds
            start_at: Optional new start time
            end_at: Optional new end time
            paused: Optional pause state

        """
        try:
            if schedule_id not in self._schedules:
                raise KeyError(f"Schedule not found: {schedule_id}")

            schedule_info = self._schedules[schedule_id]

            # Prepare update specification
            update_spec = {}

            if cron_expression is not None:
                update_spec["cron"] = cron_expression
                schedule_info["cron_expression"] = cron_expression
                # Clear interval if setting cron
                update_spec["interval"] = None
                schedule_info["interval_seconds"] = None

            elif interval_seconds is not None:
                update_spec["interval"] = f"{interval_seconds}s"
                schedule_info["interval_seconds"] = interval_seconds
                # Clear cron if setting interval
                update_spec["cron"] = None
                schedule_info["cron_expression"] = None

            if start_at is not None:
                update_spec["start_at"] = start_at
                schedule_info["start_at"] = start_at

            if end_at is not None:
                update_spec["end_at"] = end_at
                schedule_info["end_at"] = end_at

            if paused is not None:
                update_spec["paused"] = paused
                schedule_info["paused"] = paused

            # Update the schedule
            if update_spec:
                await schedule_info["handle"].update(**update_spec)
                schedule_info["updated_at"] = datetime.utcnow()

        except Exception as e:
            raise RuntimeError(f"Failed to update schedule {schedule_id}: {e!s}")

    async def delete_schedule(self, schedule_id: str) -> None:
        """Delete a schedule.

        Args:
            schedule_id: Schedule ID

        """
        try:
            if schedule_id not in self._schedules:
                raise KeyError(f"Schedule not found: {schedule_id}")

            schedule_info = self._schedules[schedule_id]
            await schedule_info["handle"].delete()
            del self._schedules[schedule_id]

        except Exception as e:
            raise RuntimeError(f"Failed to delete schedule {schedule_id}: {e!s}")

    async def pause_schedule(self, schedule_id: str) -> None:
        """Pause a schedule.

        Args:
            schedule_id: Schedule ID

        """
        await self.update_schedule(schedule_id, paused=True)

    async def unpause_schedule(self, schedule_id: str) -> None:
        """Unpause a schedule.

        Args:
            schedule_id: Schedule ID

        """
        await self.update_schedule(schedule_id, paused=False)

    async def list_schedules(self) -> list[dict[str, Any]]:
        """List all schedules.

        Returns:
            List of schedule information

        """
        schedules = []

        for schedule_id, schedule_info in self._schedules.items():
            schedule_data = {
                "schedule_id": schedule_id,
                "workflow": schedule_info["workflow"],
                "config_name": schedule_info["monitor_config"].name,
                "cron_expression": schedule_info.get("cron_expression"),
                "interval_seconds": schedule_info.get("interval_seconds"),
                "start_at": schedule_info.get("start_at"),
                "end_at": schedule_info.get("end_at"),
                "created_at": schedule_info.get("created_at"),
                "updated_at": schedule_info.get("updated_at"),
                "paused": schedule_info.get("paused", False),
            }
            schedules.append(schedule_data)

        return schedules

    async def get_schedule_info(self, schedule_id: str) -> dict[str, Any]:
        """Get information about a specific schedule.

        Args:
            schedule_id: Schedule ID

        Returns:
            Schedule information

        """
        if schedule_id not in self._schedules:
            raise KeyError(f"Schedule not found: {schedule_id}")

        schedule_info = self._schedules[schedule_id]

        # Get schedule description from Temporal
        try:
            description = await schedule_info["handle"].describe()
        except Exception:
            description = None

        return {
            "schedule_id": schedule_id,
            "workflow": schedule_info["workflow"],
            "monitor_config": schedule_info["monitor_config"].model_dump(),
            "cron_expression": schedule_info.get("cron_expression"),
            "interval_seconds": schedule_info.get("interval_seconds"),
            "start_at": schedule_info.get("start_at"),
            "end_at": schedule_info.get("end_at"),
            "created_at": schedule_info.get("created_at"),
            "updated_at": schedule_info.get("updated_at"),
            "paused": schedule_info.get("paused", False),
            "description": description,
        }

    async def get_schedule_runs(
        self,
        schedule_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get recent runs for a schedule.

        Args:
            schedule_id: Schedule ID
            limit: Maximum number of runs to return

        Returns:
            List of workflow run information

        """
        if schedule_id not in self._schedules:
            raise KeyError(f"Schedule not found: {schedule_id}")

        try:
            # This would require additional Temporal API calls
            # For now, return empty list
            return []

        except Exception as e:
            raise RuntimeError(f"Failed to get schedule runs for {schedule_id}: {e!s}")

    async def trigger_schedule_run(self, schedule_id: str) -> str:
        """Trigger an immediate run of a schedule.

        Args:
            schedule_id: Schedule ID

        Returns:
            Workflow execution ID

        """
        if schedule_id not in self._schedules:
            raise KeyError(f"Schedule not found: {schedule_id}")

        schedule_info = self._schedules[schedule_id]
        monitor_config = schedule_info["monitor_config"]

        try:
            # Start the workflow immediately
            workflow_id = await self.client.start_workflow(
                "SmartMonitoringWorkflow",
                args=(monitor_config,),
                id=f"{schedule_id}-manual-{datetime.utcnow().timestamp()}",
            )

            return workflow_id

        except Exception as e:
            raise RuntimeError(f"Failed to trigger schedule run for {schedule_id}: {e!s}")

    def create_cron_expression(
        self,
        minute: str = "*",
        hour: str = "*",
        day: str = "*",
        month: str = "*",
        day_of_week: str = "*",
    ) -> str:
        """Create a cron expression.

        Args:
            minute: Minute (0-59)
            hour: Hour (0-23)
            day: Day of month (1-31)
            month: Month (1-12)
            day_of_week: Day of week (0-7, where 0 and 7 are Sunday)

        Returns:
            Cron expression string

        """
        return f"{minute} {hour} {day} {month} {day_of_week}"

    def create_hourly_cron(self, minute: int = 0) -> str:
        """Create an hourly cron expression.

        Args:
            minute: Minute of the hour (0-59)

        Returns:
            Cron expression string

        """
        return self.create_cron_expression(minute=str(minute))

    def create_daily_cron(self, hour: int = 9, minute: int = 0) -> str:
        """Create a daily cron expression.

        Args:
            hour: Hour of day (0-23)
            minute: Minute of hour (0-59)

        Returns:
            Cron expression string

        """
        return self.create_cron_expression(minute=str(minute), hour=str(hour))

    def create_weekly_cron(self, day_of_week: int = 1, hour: int = 9, minute: int = 0) -> str:
        """Create a weekly cron expression.

        Args:
            day_of_week: Day of week (0-7, where 0 and 7 are Sunday)
            hour: Hour of day (0-23)
            minute: Minute of hour (0-59)

        Returns:
            Cron expression string

        """
        return self.create_cron_expression(minute=str(minute), hour=str(hour), day_of_week=str(day_of_week))

    def create_monthly_cron(self, day: int = 1, hour: int = 9, minute: int = 0) -> str:
        """Create a monthly cron expression.

        Args:
            day: Day of month (1-31)
            hour: Hour of day (0-23)
            minute: Minute of hour (0-59)

        Returns:
            Cron expression string

        """
        return self.create_cron_expression(minute=str(minute), hour=str(hour), day=str(day))
