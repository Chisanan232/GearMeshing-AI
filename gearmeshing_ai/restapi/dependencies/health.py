"""Health service dependency for FastAPI endpoints.

This module provides dependency injection functions for health-related
endpoints following FastAPI's dependency injection pattern.
"""

from gearmeshing_ai.restapi.service.health import HealthCheckService, create_default_health_service


def get_health_service() -> HealthCheckService:
    """Dependency function to get health service instance.
    
    This follows FastAPI's dependency injection pattern and provides
    a clean way to inject the health service into endpoints.
    
    Returns:
        HealthCheckService: Health check service instance
    """
    return create_default_health_service()
