"""ClickUp Checking Points Package

This package contains checking point implementations for monitoring ClickUp tasks,
including urgent task detection, overdue task escalation, and smart assignment.

Key Components:
- UrgentTasks: Detects urgent tasks that need immediate attention
- OverdueTasks: Identifies overdue tasks and triggers escalation
- Assignment: Handles smart assignment of unassigned tasks

Note: Checking points are automatically registered via the CheckingPointMeta metaclass
when they are imported. No manual registration is needed.
"""

from .assignment import SmartAssignmentCheckingPoint
from .overdue_tasks import OverdueTaskCheckingPoint
from .urgent_tasks import UrgentTaskCheckingPoint

__all__ = [
    "OverdueTaskCheckingPoint",
    "SmartAssignmentCheckingPoint",
    "UrgentTaskCheckingPoint",
]
