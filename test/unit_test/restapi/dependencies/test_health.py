"""Tests for health service dependency injection.

This module contains tests for the get_health_service dependency function
used in FastAPI endpoints.
"""

from gearmeshing_ai.restapi.dependencies import get_health_service
from gearmeshing_ai.restapi.service.health import HealthCheckService


class TestGetHealthServiceDependency:
    """Test cases for get_health_service dependency function."""

    def test_get_health_service_returns_instance(self) -> None:
        """Test that get_health_service returns a HealthCheckService instance."""
        service = get_health_service()

        assert isinstance(service, HealthCheckService)

    def test_get_health_service_creates_default_service(self) -> None:
        """Test that get_health_service creates default health service."""
        service = get_health_service()

        # Default service should have checkers registered
        assert service is not None
        assert hasattr(service, "check_all_health")

    def test_get_health_service_is_callable(self) -> None:
        """Test that get_health_service is callable as a dependency."""
        # This tests that the function can be used as a FastAPI dependency
        assert callable(get_health_service)

    def test_get_health_service_multiple_calls(self) -> None:
        """Test that multiple calls to get_health_service return new instances."""
        service1 = get_health_service()
        service2 = get_health_service()

        # Each call should return a new instance
        assert service1 is not service2
        assert isinstance(service1, HealthCheckService)
        assert isinstance(service2, HealthCheckService)

    def test_get_health_service_with_dependency_injection(self) -> None:
        """Test get_health_service works with FastAPI dependency injection."""
        from fastapi import Depends, FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        @app.get("/test")  # type: ignore[misc]
        def test_endpoint(service: HealthCheckService = Depends(get_health_service)) -> dict[str, bool]:
            return {"service": service is not None}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        assert response.json()["service"] is True

    def test_get_health_service_returns_functional_service(self) -> None:
        """Test that returned service is functional."""
        service = get_health_service()

        # Service should be able to perform health checks
        result = service.check_all_health()

        assert isinstance(result, dict)
        assert "status" in result
        assert "checkers" in result
        assert "timestamp" in result

    def test_get_health_service_has_default_checkers(self) -> None:
        """Test that default service has expected checkers."""
        service = get_health_service()
        result = service.check_all_health()

        # Default service should have at least one checker
        assert len(result["checkers"]) > 0

    def test_get_health_service_status_values(self) -> None:
        """Test that health service returns valid status values."""
        service = get_health_service()
        result = service.check_all_health()

        # Status should be one of the valid values
        assert result["status"] in ["healthy", "degraded", "unhealthy"]
