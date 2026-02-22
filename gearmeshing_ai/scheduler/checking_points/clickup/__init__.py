"""ClickUp Checking Points Package

This package contains checking point implementations for monitoring ClickUp tasks,
including urgent task detection, overdue task escalation, and smart assignment.

Key Components:
- UrgentTasks: Detects urgent tasks that need immediate attention
- OverdueTasks: Identifies overdue tasks and triggers escalation
- Assignment: Handles smart assignment of unassigned tasks
"""

from .urgent_tasks import UrgentTaskCheckingPoint
from .overdue_tasks import OverdueTaskCheckingPoint
from .assignment import SmartAssignmentCheckingPoint

__all__ = [
    "UrgentTaskCheckingPoint",
    "OverdueTaskCheckingPoint",
    "SmartAssignmentCheckingPoint",
]
