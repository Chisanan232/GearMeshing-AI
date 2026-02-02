"""FastAPI dependency injection functions for the REST API.

This package provides dependency injection functions following FastAPI's
dependency injection pattern for use across router endpoints.
"""

from .health import get_health_service

__all__ = ["get_health_service"]
