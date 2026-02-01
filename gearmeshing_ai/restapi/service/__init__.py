"""Service package for GearMeshing-AI REST API.

This package contains business logic services organized by functionality,
following duck typing principles for clean, maintainable code.
"""

from .health import (
    HealthChecker,
    BaseHealthChecker,
    DatabaseHealthChecker,
    ApplicationHealthChecker,
    HealthCheckService,
    create_default_health_service
)

__all__ = [
    "HealthChecker",
    "BaseHealthChecker",
    "DatabaseHealthChecker",
    "ApplicationHealthChecker",
    "HealthCheckService",
    "create_default_health_service"
]