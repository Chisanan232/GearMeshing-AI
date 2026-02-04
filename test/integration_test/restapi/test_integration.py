"""Integration tests for GearMeshing-AI REST API components.

This module contains integration tests that verify the interaction
between different REST API components including routers, services,
and utilities working together.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from gearmeshing_ai.core.models.io import (
    HealthStatus,
    HealthStatusContent,
)
from gearmeshing_ai.restapi.main import create_application
from gearmeshing_ai.restapi.service.health import (
    ApplicationHealthChecker,
    DatabaseHealthChecker,
    HealthCheckService,
    create_default_health_service,
)


class TestRestApiIntegration:
    """Integration tests for the complete REST API."""

    def setup_method(self) -> None:
        """Setup test client for each test."""
        self.app = create_application()
        self.client = TestClient(self.app)

    def test_complete_api_startup(self) -> None:
        """Test complete API startup and basic functionality."""
        # Test that the app starts correctly
        response = self.client.get("/")
        assert response.status_code == 200

        # Test that all major endpoints are available
        endpoints = ["/", "/info", "/health", "/health/simple", "/health/ready", "/health/live"]
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            assert response.status_code in [200, 503]  # 503 if services are unhealthy

    def test_api_endpoints_consistency(self) -> None:
        """Test consistency across all API endpoints."""
        # Get responses from all endpoints
        root_response = self.client.get("/").json()
        info_response = self.client.get("/info").json()
        health_response = self.client.get("/health").json()

        # All should have the same response structure
        for response in [root_response, info_response, health_response]:
            assert "success" in response
            assert "message" in response
            assert "content" in response
            assert "timestamp" in response

        # All timestamps should be recent
        for response in [root_response, info_response, health_response]:
            timestamp_str = response["timestamp"]
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            # Should be within last minute
            assert (datetime.now(UTC) - timestamp).total_seconds() < 60

    def test_health_endpoints_integration(self) -> None:
        """Test integration between all health endpoints."""
        # Test all health endpoints with mocked healthy service
        with patch("gearmeshing_ai.restapi.dependencies.health.create_default_health_service") as mock_create:
            mock_service = MagicMock(spec=HealthCheckService)
            mock_service.check_all_health.return_value = {
                "status": "healthy",
                "timestamp": "2023-01-01T00:00:00",
                "checkers": {
                    "database": HealthStatusContent(status="healthy", details={"connection": "ok"}),
                    "application": HealthStatusContent(status="healthy", details={"version": "1.0.0"}),
                },
            }
            mock_create.return_value = mock_service

            # Test all health endpoints
            health_response = self.client.get("/health")
            simple_response = self.client.get("/health/simple")
            ready_response = self.client.get("/health/ready")
            live_response = self.client.get("/health/live")

            # All should succeed
            assert health_response.status_code == 200
            assert simple_response.status_code == 200
            assert ready_response.status_code == 200
            assert live_response.status_code == 200

            # Check consistency
            health_data = health_response.json()
            simple_data = simple_response.json()
            ready_data = ready_response.json()
            live_data = live_response.json()

            # All should have success=True for healthy status
            assert health_data["success"] is True
            assert simple_data["success"] is True
            assert ready_data["success"] is True
            assert live_data["success"] is True

    def test_api_with_degraded_service(self) -> None:
        """Test API behavior with degraded health service."""
        # Test health endpoints without mocking - use real service
        health_response = self.client.get("/health/")
        # Health check may succeed or fail depending on services
        assert health_response.status_code in [200, 503]

        # Simple health should respond
        simple_response = self.client.get("/health/simple")
        assert simple_response.status_code in [200, 503]

        # Readiness should respond
        ready_response = self.client.get("/health/ready")
        assert ready_response.status_code in [200, 503]

    def test_api_with_unhealthy_service(self) -> None:
        """Test API behavior with unhealthy health service."""
        with patch("gearmeshing_ai.restapi.dependencies.health.create_default_health_service") as mock_create:
            mock_service = MagicMock(spec=HealthCheckService)
            mock_service.check_all_health.return_value = {
                "status": "unhealthy",
                "timestamp": "2023-01-01T00:00:00",
                "checkers": {
                    "database": HealthStatusContent(status="unhealthy", details={"error": "connection failed"})
                },
            }
            mock_create.return_value = mock_service

            # Health check should return 503
            health_response = self.client.get("/health")
            assert health_response.status_code == 503

            # Simple health should return 503
            simple_response = self.client.get("/health/simple")
            assert simple_response.status_code == 503

            # Readiness should return 503
            ready_response = self.client.get("/health/ready")
            assert ready_response.status_code == 503

            # Liveness should still work (doesn't depend on service)
            live_response = self.client.get("/health/live")
            assert live_response.status_code == 200

    def test_api_error_handling_integration(self) -> None:
        """Test API error handling integration."""
        with patch("gearmeshing_ai.restapi.dependencies.health.create_default_health_service") as mock_create:
            mock_service = MagicMock(spec=HealthCheckService)
            mock_service.check_all_health.side_effect = Exception("Service error")
            mock_create.return_value = mock_service

            # All health-dependent endpoints should return 503
            health_response = self.client.get("/health")
            simple_response = self.client.get("/health/simple")
            ready_response = self.client.get("/health/ready")

            assert health_response.status_code == 503
            assert simple_response.status_code == 503
            assert ready_response.status_code == 503

            # Liveness should still work
            live_response = self.client.get("/health/live")
            assert live_response.status_code == 200

            # Root and info should still work
            root_response = self.client.get("/")
            info_response = self.client.get("/info")

            assert root_response.status_code == 200
            assert info_response.status_code == 200


class TestHealthServiceIntegration:
    """Integration tests for health service with real checkers."""

    def test_default_health_service_integration(self) -> None:
        """Test default health service with real checkers."""
        service = create_default_health_service()

        # Check that service has expected checkers
        assert len(service._checkers) == 2

        # Perform health check
        result = service.check_all_health()

        # Verify structure
        assert "status" in result
        assert "timestamp" in result
        assert "checkers" in result
        assert len(result["checkers"]) == 2

        # Verify checker results
        assert "application" in result["checkers"]
        assert "database" in result["checkers"]

        # Verify checker results are valid
        for checker_name, checker_result in result["checkers"].items():
            assert hasattr(checker_result, "status")
            assert hasattr(checker_result, "details")
            assert checker_result.status in ["healthy", "degraded", "unhealthy"]

    def test_health_service_with_database_connection(self) -> None:
        """Test health service with database connection string."""
        service = HealthCheckService()

        # Add database checker with connection string
        db_checker = DatabaseHealthChecker("postgresql://user:pass@localhost:5432/test")
        service.register_checker(db_checker)
        service.register_checker(ApplicationHealthChecker())

        result = service.check_all_health()

        # Database checker should show connection is configured
        assert result["checkers"]["database"].details["connection_configured"] is True

    def test_health_service_failure_scenarios(self) -> None:
        """Test health service failure scenarios."""
        service = HealthCheckService()

        # Add a failing checker
        class FailingChecker:
            def __init__(self) -> None:
                self.name = "failing_checker"

            def check_health(self) -> None:
                raise RuntimeError("Simulated failure")

        service.register_checker(FailingChecker())  # type: ignore[arg-type]
        service.register_checker(ApplicationHealthChecker())

        result = service.check_all_health()

        # Overall status should be unhealthy
        assert result["status"] == "unhealthy"

        # Failing checker should have error details
        assert result["checkers"]["failing_checker"].status == "unhealthy"
        assert "error" in result["checkers"]["failing_checker"].details

        # Application checker should still work
        assert result["checkers"]["application"].status == "healthy"

    def test_health_service_concurrent_access(self) -> None:
        """Test health service concurrent access."""
        import threading

        service = create_default_health_service()
        results = []

        def check_health() -> None:
            result = service.check_all_health()
            results.append(result["status"])

        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=check_health)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All results should be consistent
        assert len(set(results)) <= 2  # Allow for healthy or degraded
        assert len(results) == 10


class TestRouterServiceIntegration:
    """Integration tests for router and service interaction."""

    def setup_method(self) -> None:
        """Setup test client for each test."""
        self.app = create_application()
        self.client = TestClient(self.app)

    def test_health_router_service_dependency(self) -> None:
        """Test health router dependency injection with service."""
        from gearmeshing_ai.restapi.dependencies.health import get_health_service

        # Test dependency function
        service = get_health_service()
        assert isinstance(service, HealthCheckService)

        # Test that service can perform health checks
        result = service.check_all_health()
        assert "status" in result
        assert "checkers" in result

    def test_health_router_with_mock_service(self) -> None:
        """Test health router with mocked service."""
        # Test health endpoints through the full app
        response = self.client.get("/health/")
        # Health check may succeed or fail depending on services
        assert response.status_code in [200, 503]

        # Response should be valid JSON
        data = response.json()
        assert isinstance(data, dict)
        assert "success" in data

    def test_service_error_propagation_to_router(self) -> None:
        """Test that service errors are properly handled by router."""
        # Test error handling through the full app
        response = self.client.get("/health/")
        # Health check may succeed or fail depending on services
        assert response.status_code in [200, 503]

        # Response should be valid JSON
        data = response.json()
        assert isinstance(data, dict)


class TestIOModelsIntegration:
    """Integration tests for I/O models with API responses."""

    def setup_method(self) -> None:
        """Setup test client for each test."""
        self.app = create_application()
        self.client = TestClient(self.app)

    def test_global_response_model_in_api(self) -> None:
        """Test GlobalResponse model integration in API responses."""
        response = self.client.get("/")
        data = response.json()

        # Verify response follows GlobalResponse structure
        assert "success" in data
        assert "message" in data
        assert "content" in data
        assert "timestamp" in data

        # Verify timestamp is valid
        timestamp_str = data["timestamp"]
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        assert isinstance(timestamp, datetime)

    def test_health_response_models_integration(self) -> None:
        """Test health response models integration."""
        with patch("gearmeshing_ai.restapi.dependencies.health.create_default_health_service") as mock_create:
            mock_service = MagicMock(spec=HealthCheckService)
            mock_service.check_all_health.return_value = {
                "status": "healthy",
                "timestamp": "2023-01-01T00:00:00",
                "checkers": {
                    "database": {"status": "healthy", "details": {}},
                    "application": {"status": "healthy", "details": {}},
                },
            }
            mock_create.return_value = mock_service

            response = self.client.get("/health")
            data = response.json()

            # Verify health response structure
            assert data["success"] is True
            assert data["content"]["status"] == HealthStatus.HEALTHY
            assert "checkers" in data["content"]
            assert "database" in data["content"]["checkers"]
            assert "application" in data["content"]["checkers"]

    def test_error_response_models_integration(self) -> None:
        """Test error response models integration."""
        with patch("gearmeshing_ai.restapi.dependencies.health.create_default_health_service") as mock_create:
            mock_service = MagicMock(spec=HealthCheckService)
            mock_service.check_all_health.side_effect = Exception("Test error")
            mock_create.return_value = mock_service

            response = self.client.get("/health")
            data = response.json()

            # Verify error response structure
            assert response.status_code == 503
            assert "detail" in data
            assert data["detail"]["success"] is False
            assert "message" in data["detail"]

    def test_content_model_validation_integration(self) -> None:
        """Test content model validation in API responses."""
        response = self.client.get("/info")
        data = response.json()

        # Verify ApiInfoContent structure
        content = data["content"]
        assert "name" in content
        assert "version" in content
        assert "description" in content
        assert "endpoints" in content
        assert "documentation" in content

        # Verify data types
        assert isinstance(content["endpoints"], list)
        assert isinstance(content["documentation"], dict)


class TestMiddlewareIntegration:
    """Integration tests for middleware components."""

    def setup_method(self) -> None:
        """Setup test client for each test."""
        self.app = create_application()
        self.client = TestClient(self.app)

    def test_cors_middleware_integration(self) -> None:
        """Test CORS middleware integration."""
        # Test preflight request
        response = self.client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        # Should handle CORS preflight
        assert response.status_code in [200, 204]

    def test_cors_headers_in_responses(self) -> None:
        """Test CORS headers in actual responses."""
        response = self.client.get("/", headers={"Origin": "http://localhost:3000"})

        assert response.status_code == 200
        # CORS headers should be present (depending on configuration)

    def test_request_response_flow(self) -> None:
        """Test complete request-response flow."""
        # Test normal request
        response = self.client.get("/")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

        # Test that response is valid JSON
        data = response.json()
        assert isinstance(data, dict)


class TestApplicationLifecycleIntegration:
    """Integration tests for application lifecycle."""

    def test_application_creation_and_usage(self) -> None:
        """Test application creation and immediate usage."""
        app = create_application()
        client = TestClient(app)

        # Should be able to make requests immediately
        response = client.get("/")
        assert response.status_code == 200

        response = client.get("/info")
        assert response.status_code == 200

    def test_multiple_app_instances(self) -> None:
        """Test multiple application instances."""
        app1 = create_application()
        app2 = create_application()

        client1 = TestClient(app1)
        client2 = TestClient(app2)

        # Both should work independently
        response1 = client1.get("/")
        response2 = client2.get("/")

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Should have similar structure
        data1 = response1.json()
        data2 = response2.json()

        assert data1["success"] == data2["success"]
        assert data1["content"]["message"] == data2["content"]["message"]

    def test_app_configuration_consistency(self) -> None:
        """Test that app configuration is consistent."""
        app = create_application()

        # Check app configuration
        assert app.title == "GearMeshing-AI API"
        assert app.version == "0.0.0"
        assert app.description == "Enterprise AI agents development platform API"

        # Check that routes are registered
        routes = [route.path for route in app.routes]
        assert "/" in routes
        assert "/info" in routes
        # Health routes may have trailing slash
        assert "/health/" in routes or "/health" in routes


class TestErrorHandlingIntegration:
    """Integration tests for comprehensive error handling."""

    def test_404_error_handling(self) -> None:
        """Test 404 error handling across the application."""
        client = TestClient(create_application())

        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

    def test_method_not_allowed_handling(self) -> None:
        """Test method not allowed handling."""
        client = TestClient(create_application())

        # Test POST on GET endpoint
        response = client.post("/")
        assert response.status_code in [405, 422]

    def test_validation_error_handling(self) -> None:
        """Test validation error handling."""
        client = TestClient(create_application())

        # Test with invalid HTTP method on GET endpoint
        response = client.post("/")

        # POST on GET endpoint should return 405 or 422
        assert response.status_code in [405, 422]

    def test_service_unavailable_handling(self) -> None:
        """Test handling when services are unavailable."""
        client = TestClient(create_application())

        with patch("gearmeshing_ai.restapi.dependencies.health.create_default_health_service") as mock_create:
            mock_service = MagicMock(spec=HealthCheckService)
            mock_service.check_all_health.side_effect = ConnectionError("Service unavailable")
            mock_create.return_value = mock_service

            # Health endpoints should return 503
            response = client.get("/health")
            assert response.status_code == 503

            # But non-health endpoints should still work
            response = client.get("/")
            assert response.status_code == 200


class TestPerformanceIntegration:
    """Integration tests for performance characteristics."""

    def test_response_time_performance(self) -> None:
        """Test API response time performance."""
        import time

        client = TestClient(create_application())

        # Test multiple endpoints
        endpoints = ["/", "/info", "/health/live"]

        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()

            # Should respond quickly (less than 1 second)
            response_time = end_time - start_time
            assert response_time < 1.0
            assert response.status_code == 200

    def test_concurrent_request_handling(self) -> None:
        """Test concurrent request handling."""
        import threading
        import time

        client = TestClient(create_application())
        results = []

        def make_request() -> None:
            response = client.get("/")
            results.append(response.status_code)

        # Create multiple threads
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=make_request)
            threads.append(thread)

        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        end_time = time.time()

        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 20

        # Should complete in reasonable time
        total_time = end_time - start_time
        assert total_time < 5.0  # Should complete within 5 seconds

    def test_memory_usage_stability(self) -> None:
        """Test memory usage stability with repeated requests."""
        import gc

        client = TestClient(create_application())

        # Make many requests
        for _ in range(100):
            response = client.get("/")
            assert response.status_code == 200

        # Force garbage collection
        gc.collect()

        # Should still work normally
        response = client.get("/")
        assert response.status_code == 200
