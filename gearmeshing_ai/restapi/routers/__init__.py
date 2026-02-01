"""Router package for GearMeshing-AI REST API.

This package contains all API routers organized by functionality,
following duck typing principles for clean, maintainable code.
"""

from .health import get_health_router

__all__ = ["get_health_router"]
