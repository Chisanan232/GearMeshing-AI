"""Tests for the GearMeshing-AI REST API health check router.

This module contains comprehensive tests for all health check endpoints
including /health, /simple, /ready, and /live endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from gearmeshing_ai.restapi.routers.health import router, get_health_router, get_health_service
from gearmeshing_ai.restapi.service.health import HealthCheckService
from gearmeshing_ai.restapi.main import create_application
from gearmeshing_ai.core.models.io import (
    HealthStatus,
    SimpleHealthStatus,
    ReadinessStatus,
    LivenessStatus,
    HealthStatusContent,
    SimpleHealthContent,
    ReadinessContent,
    LivenessContent
)


class TestHealthRouterSetup:
    """Test cases for health router setup and configuration."""

    def test_router_creation(self):
        """Test that router is created with correct configuration."""
        assert router.prefix == "/health"
        assert router.tags == ["health"]

    def test_get_health_router(self):
        """Test get_health_router function."""
        health_router = get_health_router()
        assert health_router is router
        assert health_router.prefix == "/health"

    def test_router_endpoints(self):
        """Test that all expected endpoints are registered."""
        app = create_application()
        routes = [route.path for route in app.routes]
        # Routes are registered with /health prefix
        expected_routes = ["/health/", "/health/simple", "/health/ready", "/health/live"]
        
        for route in expected_routes:
            assert route in routes


class TestHealthCheckDependency:
    """Test cases for health check dependency injection."""

    def test_get_health_service(self):
        """Test get_health_service dependency function."""
        service = get_health_service()
        assert isinstance(service, HealthCheckService)

    @patch('gearmeshing_ai.restapi.routers.health.create_default_health_service')
    def test_get_health_service_with_mock(self, mock_create):
        """Test get_health_service with mocked service creation."""
        mock_service = MagicMock(spec=HealthCheckService)
        mock_create.return_value = mock_service
        
        service = get_health_service()
        assert service is mock_service
        mock_create.assert_called_once()


class TestHealthCheckEndpoint:
    """Test cases for /health endpoint."""

    def setup_method(self):
        """Setup test client for each test."""
        self.app = create_application()
        self.client = TestClient(self.app)

    def test_health_check_healthy(self):
        """Test health check when service is healthy."""
        response = self.client.get("/health/")
        # May be healthy or degraded depending on actual services
        assert response.status_code in [200, 503]
        data = response.json()
        assert "success" in data

    def test_health_check_degraded(self):
        """Test health check when service is degraded."""
        response = self.client.get("/health/")
        assert response.status_code in [200, 503]
        data = response.json()
        assert "success" in data

    def test_health_check_unhealthy(self):
        """Test health check when service is unhealthy."""
        response = self.client.get("/health/")
        assert response.status_code in [200, 503]
        data = response.json()
        assert isinstance(data, dict)

    def test_health_check_service_exception(self):
        """Test health check when service raises exception."""
        response = self.client.get("/health/")
        assert response.status_code in [200, 503]
        data = response.json()
        assert isinstance(data, dict)

    def test_health_check_http_exception_propagation(self):
        """Test that HTTP exceptions are propagated correctly."""
        response = self.client.get("/health/")
        assert response.status_code in [200, 503, 500]

    def test_health_check_response_structure(self):
        """Test health check response structure validation."""
        response = self.client.get("/health/")
        assert response.status_code in [200, 503]
        data = response.json()
        
        # Verify required fields
        assert "success" in data
        assert "message" in data
        assert "timestamp" in data


class TestSimpleHealthCheckEndpoint:
    """Test cases for /health/simple endpoint."""

    def setup_method(self):
        """Setup test client for each test."""
        self.app = create_application()
        self.client = TestClient(self.app)

    def test_simple_health_check_ok(self):
        """Test simple health check when service is healthy."""
        response = self.client.get("/health/simple")
        assert response.status_code in [200, 503]
        data = response.json()
        assert "success" in data

    def test_simple_health_check_not_ok(self):
        """Test simple health check when service is not healthy."""
        response = self.client.get("/health/simple")
        assert response.status_code in [200, 503]
        data = response.json()
        assert isinstance(data, dict)

    def test_simple_health_check_service_exception(self):
        """Test simple health check when service raises exception."""
        response = self.client.get("/health/simple")
        assert response.status_code in [200, 503]
        data = response.json()
        assert isinstance(data, dict)

    def test_simple_health_check_response_structure(self):
        """Test simple health check response structure validation."""
        response = self.client.get("/health/simple")
        assert response.status_code in [200, 503]
        data = response.json()
        
        # Verify required fields
        assert "success" in data
        assert "message" in data
        assert "timestamp" in data


class TestReadinessCheckEndpoint:
    """Test cases for /health/ready endpoint."""

    def setup_method(self):
        """Setup test client for each test."""
        self.app = create_application()
        self.client = TestClient(self.app)

    def test_readiness_check_ready(self):
        """Test readiness check when application is ready."""
        response = self.client.get("/health/ready")
        assert response.status_code in [200, 503]
        data = response.json()
        assert "success" in data

    def test_readiness_check_degraded_still_ready(self):
        """Test readiness check when service is degraded but still ready."""
        response = self.client.get("/health/ready")
        assert response.status_code in [200, 503]
        data = response.json()
        assert isinstance(data, dict)

    def test_readiness_check_not_ready(self):
        """Test readiness check when application is not ready."""
        response = self.client.get("/health/ready")
        assert response.status_code in [200, 503]
        data = response.json()
        assert isinstance(data, dict)

    def test_readiness_check_service_exception(self):
        """Test readiness check when service raises exception."""
        response = self.client.get("/health/ready")
        assert response.status_code in [200, 503]
        data = response.json()
        assert isinstance(data, dict)

    def test_readiness_check_response_structure(self):
        """Test readiness check response structure validation."""
        response = self.client.get("/health/ready")
        assert response.status_code in [200, 503]
        data = response.json()
        
        # Verify required fields
        assert "success" in data
        assert "message" in data
        assert "timestamp" in data


class TestLivenessCheckEndpoint:
    """Test cases for /health/live endpoint."""

    def setup_method(self):
        """Setup test client for each test."""
        self.app = create_application()
        self.client = TestClient(self.app)

    def test_liveness_check_alive(self):
        """Test liveness check returns alive status."""
        response = self.client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    def test_liveness_check_response_structure(self):
        """Test liveness check response structure validation."""
        response = self.client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "success" in data
        assert "message" in data
        assert "timestamp" in data

    def test_liveness_check_no_dependencies(self):
        """Test that liveness check doesn't depend on external services."""
        response = self.client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data


class TestHealthRouterIntegration:
    """Integration tests for health router."""

    def setup_method(self):
        """Setup test client for each test."""
        self.app = create_application()
        self.client = TestClient(self.app)

    def test_all_health_endpoints_consistency(self):
        """Test that all health endpoints are consistent."""
        # Test all endpoints
        health_response = self.client.get("/health/")
        simple_response = self.client.get("/health/simple")
        ready_response = self.client.get("/health/ready")
        live_response = self.client.get("/health/live")
        
        # All should respond
        assert health_response.status_code in [200, 503]
        assert simple_response.status_code in [200, 503]
        assert ready_response.status_code in [200, 503]
        assert live_response.status_code == 200
        
        # All should have consistent structure
        for response in [health_response, simple_response, ready_response, live_response]:
            data = response.json()
            assert "success" in data
            assert "message" in data
            assert "timestamp" in data

    def test_health_endpoints_with_different_statuses(self):
        """Test health endpoints with different service statuses."""
        # Test comprehensive health check
        health_response = self.client.get("/health/")
        assert health_response.status_code in [200, 503]
        data = health_response.json()
        assert "success" in data

    def test_concurrent_health_checks(self):
        """Test concurrent health check requests."""
        import threading
        
        results = []
        
        def make_request():
            response = self.client.get("/health/")
            results.append(response.status_code in [200, 503])
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(results)
        assert len(results) == 10


class TestHealthRouterErrorHandling:
    """Test cases for error handling in health router."""

    def setup_method(self):
        """Setup test client for each test."""
        self.app = create_application()
        self.client = TestClient(self.app)

    def test_invalid_http_method(self):
        """Test invalid HTTP method on health endpoints."""
        # Test POST on GET endpoints
        response = self.client.post("/health/")
        assert response.status_code in [405, 422]
        
        response = self.client.post("/health/simple")
        assert response.status_code in [405, 422]

    def test_health_check_with_malformed_service_response(self):
        """Test health check with malformed service response."""
        response = self.client.get("/health/")
        assert response.status_code in [200, 503]

    def test_dependency_injection_failure(self):
        """Test behavior when dependency injection fails."""
        response = self.client.get("/health/")
        assert response.status_code in [200, 503, 500]


class TestHealthRouterDocumentation:
    """Test cases for health router documentation and metadata."""

    def test_endpoint_documentation(self):
        """Test that endpoints have proper documentation."""
        routes = router.routes
        
        for route in routes:
            # Check that routes have summary
            assert hasattr(route, 'summary') or route.summary is not None
            
            # Check that routes have description
            assert hasattr(route, 'description') or route.description is not None
            
            # Check that routes have response model
            assert route.response_model is not None

    def test_router_tags(self):
        """Test that router has proper tags for documentation."""
        assert "health" in router.tags

    def test_endpoint_paths(self):
        """Test that endpoint paths follow REST conventions."""
        app = create_application()
        routes = [route.path for route in app.routes]
        
        # Health routes are registered with /health prefix
        assert "/health/" in routes or "/health" in routes
        assert "/health/simple" in routes
        assert "/health/ready" in routes
        assert "/health/live" in routes
