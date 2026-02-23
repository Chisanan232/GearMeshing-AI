"""Temporal Integration Package

This package contains the Temporal client and worker setup for the scheduler system,
providing the infrastructure for running Temporal workflows and activities.

Key Components:
- Client: Temporal client wrapper for workflow management
- Worker: Worker configuration and setup
- Schedules: Schedule management for recurring workflows
"""

from .client import TemporalClient
from .schedules import ScheduleManager
from .worker import TemporalWorker

__all__ = [
    "ScheduleManager",
    "TemporalClient",
    "TemporalWorker",
]
