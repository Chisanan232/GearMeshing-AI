"""GearMeshing-AI Event-Driven Scheduler Package

This package provides a sophisticated, human-like automation system that proactively
monitors external systems (ClickUp, Slack, etc.) and makes intelligent decisions
to take actions using Temporal workflows.

Key Features:
- Event-driven architecture with Temporal workflow orchestration
- Code-based checking points for flexible monitoring logic
- AI-powered decision making and action execution
- Comprehensive CLI management interface
- Production-ready monitoring and observability

Main Components:
- Models: Data schemas and configuration models
- Workflows: Temporal workflow definitions
- Activities: Temporal activity implementations
- Checking Points: Monitoring logic implementations
- Prompts: AI prompt template management
- Config: Configuration management
- Temporal: Temporal client and worker setup
"""

from .models import (
    BaseSchedulerModel,
    MonitorConfig,
    SchedulerConfig,
    MonitoringData,
    MonitoringDataType,
    CheckResult,
    AIAction,
    AIWorkflowInput,
    AIWorkflowResult,
)

from .workflows import (
    SmartMonitoringWorkflow,
    AIWorkflowExecutor,
)

from .checking_points import (
    CheckingPoint,
    CheckingPointType,
    checking_point_registry,
)

from .config import (
    get_scheduler_settings,
)

from .temporal import (
    TemporalClient,
    TemporalWorker,
)

__version__ = "1.0.0"
__all__ = [
    # Models
    "BaseSchedulerModel",
    "MonitorConfig",
    "MonitoringData",
    "MonitoringDataType",
    "CheckResult",
    "AIAction",
    "AIWorkflowInput",
    "AIWorkflowResult",
    # Workflows
    "SmartMonitoringWorkflow",
    "AIWorkflowExecutor",
    # Checking Points
    "CheckingPoint",
    "CheckingPointType",
    "checking_point_registry",
    # Config
    "SchedulerConfig",
    "get_scheduler_settings",
    # Temporal
    "TemporalClient",
    "TemporalWorker",
]
