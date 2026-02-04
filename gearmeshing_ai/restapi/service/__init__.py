"""Service package for GearMeshing-AI REST API.

This package contains business logic services organized by functionality,
following duck typing principles for clean, maintainable code.
"""

from .health import (
    ApplicationHealthChecker,
    BaseHealthChecker,
    DatabaseHealthChecker,
    HealthChecker,
    HealthCheckService,
    create_default_health_service,
)

__all__ = [
    "ApplicationHealthChecker",
    "BaseHealthChecker",
    "DatabaseHealthChecker",
    "HealthCheckService",
    "HealthChecker",
    "create_default_health_service",
]
