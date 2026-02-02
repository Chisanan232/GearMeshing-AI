"""End-to-end tests for GearMeshing-AI REST API workflows.

This module contains comprehensive end-to-end tests that verify
complete user workflows and real-world usage scenarios.
"""

import pytest
import json
import time
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime

from gearmeshing_ai.restapi.main import create_application
from gearmeshing_ai.restapi.service.health import (
    HealthCheckService,
    DatabaseHealthChecker,
    ApplicationHealthChecker,
    create_default_health_service
)
from gearmeshing_ai.core.models.io import (
    HealthStatus,
    SimpleHealthStatus,
    ReadinessStatus,
    LivenessStatus
)


class TestCompleteApiWorkflows:
    """End-to-end tests for complete API workflows."""

    def setup_method(self):
        """Setup test client for each test."""
        self.app = create_application()
        self.client = TestClient(self.app)

    def test_api_discovery_workflow(self):
        """Test complete API discovery workflow for new users."""
        # 1. User discovers the API root
        response = self.client.get("/")
        assert response.status_code == 200
        
        root_data = response.json()
        assert root_data["success"] is True
        assert "docs" in root_data["content"]
        assert "health" in root_data["content"]
        
        # 2. User gets detailed API information
        response = self.client.get("/info")
        assert response.status_code == 200
        
        info_data = response.json()
        assert info_data["success"] is True
        assert "endpoints" in info_data["content"]
        assert "documentation" in info_data["content"]
        
        # 3. User checks API health before using
        response = self.client.get("/health/simple")
        assert response.status_code == 200
        
        # 4. User verifies API is ready
        response = self.client.get("/health/ready")
        assert response.status_code == 200
        
        # 5. User confirms API is alive
        response = self.client.get("/health/live")
        assert response.status_code == 200

    def test_health_monitoring_workflow(self):
        """Test complete health monitoring workflow."""
        # Test health endpoints without mocking - use real service
        response = self.client.get("/health/")
        # Health check may succeed or fail depending on services
        assert response.status_code in [200, 503]
        
        # Test simple health check for load balancer
        response = self.client.get("/health/simple")
        assert response.status_code in [200, 503]
        
        # Test readiness check for orchestration
        response = self.client.get("/health/ready")
        assert response.status_code in [200, 503]
        
        # Test liveness check
        response = self.client.get("/health/live")
        assert response.status_code == 200

    def test_error_recovery_workflow(self):
        """Test error recovery workflow."""
        with patch('gearmeshing_ai.restapi.dependencies.health.create_default_health_service') as mock_create:
            mock_service = MagicMock(spec=HealthCheckService)
            
            # 1. Service fails
            mock_service.check_all_health.side_effect = ConnectionError("Database connection failed")
            mock_create.return_value = mock_service
            
            # Health endpoints should fail gracefully
            response = self.client.get("/health")
            assert response.status_code == 503
            
            response = self.client.get("/health/simple")
            assert response.status_code == 503
            
            response = self.client.get("/health/ready")
            assert response.status_code == 503
            
            # But basic endpoints should still work
            response = self.client.get("/")
            assert response.status_code == 200
            
            response = self.client.get("/info")
            assert response.status_code == 200
            
            # Liveness should still work
            response = self.client.get("/health/live")
            assert response.status_code == 200
            
            # 2. Service recovers
            mock_service.check_all_health.side_effect = None
            mock_service.check_all_health.return_value = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "checkers": {}
            }
            
            # Health endpoints should work again
            response = self.client.get("/health")
            assert response.status_code == 200
            
            response = self.client.get("/health/simple")
            assert response.status_code == 200
            
            response = self.client.get("/health/ready")
            assert response.status_code == 200

    def test_api_documentation_workflow(self):
        """Test API documentation workflow."""
        # 1. User gets API info
        response = self.client.get("/info")
        assert response.status_code == 200
        
        info_data = response.json()
        docs_url = info_data["content"]["documentation"]["swagger"]
        
        # 2. User accesses Swagger documentation
        response = self.client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # 3. User accesses ReDoc documentation
        response = self.client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # 4. User gets OpenAPI schema
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        
        schema_data = response.json()
        assert "openapi" in schema_data
        assert "info" in schema_data
        assert "paths" in schema_data
        
        # 5. Verify health endpoints are documented
        paths = schema_data["paths"]
        # Health routes may have trailing slash
        assert "/health/" in paths or "/health" in paths
        assert "/health/simple" in paths
        assert "/health/ready" in paths
        assert "/health/live" in paths


class TestRealWorldScenarios:
    """Tests for real-world usage scenarios."""

    def setup_method(self):
        """Setup test client for each test."""
        self.app = create_application()
        self.client = TestClient(self.app)

    def test_load_balancer_integration(self):
        """Test load balancer integration scenario."""
        # Load balancers typically use simple health checks
        with patch('gearmeshing_ai.restapi.dependencies.health.create_default_health_service') as mock_create:
            mock_service = MagicMock(spec=HealthCheckService)
            mock_service.check_all_health.return_value = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "checkers": {}
            }
            mock_create.return_value = mock_service
            
            # Load balancer checks simple health
            response = self.client.get("/health/simple")
            assert response.status_code == 200
            
            simple_data = response.json()
            assert simple_data["success"] is True
            assert simple_data["content"]["status"] == SimpleHealthStatus.OK
            
            # Load balancer checks liveness
            response = self.client.get("/health/live")
            assert response.status_code == 200
            
            live_data = response.json()
            assert live_data["success"] is True
            assert live_data["content"]["status"] == LivenessStatus.ALIVE

    def test_kubernetes_integration(self):
        """Test Kubernetes integration scenario."""
        with patch('gearmeshing_ai.restapi.dependencies.health.create_default_health_service') as mock_create:
            mock_service = MagicMock(spec=HealthCheckService)
            mock_service.check_all_health.return_value = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "checkers": {}
            }
            mock_create.return_value = mock_service
            
            # Kubernetes readiness probe
            response = self.client.get("/health/ready")
            assert response.status_code == 200
            
            ready_data = response.json()
            assert ready_data["success"] is True
            assert ready_data["content"]["status"] == ReadinessStatus.READY
            
            # Kubernetes liveness probe
            response = self.client.get("/health/live")
            assert response.status_code == 200
            
            live_data = response.json()
            assert live_data["success"] is True
            assert live_data["content"]["status"] == LivenessStatus.ALIVE
            
            # Kubernetes startup probe (comprehensive health)
            response = self.client.get("/health")
            assert response.status_code == 200
            
            health_data = response.json()
            assert health_data["success"] is True
            assert health_data["content"]["status"] == HealthStatus.HEALTHY

    def test_monitoring_system_integration(self):
        """Test monitoring system integration scenario."""
        with patch('gearmeshing_ai.restapi.dependencies.health.create_default_health_service') as mock_create:
            mock_service = MagicMock(spec=HealthCheckService)
            mock_service.check_all_health.return_value = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "checkers": {
                    "database": {
                        "status": "healthy",
                        "details": {
                            "connection_pool": "8/10",
                            "response_time": "12ms",
                            "last_check": datetime.utcnow().isoformat()
                        }
                    },
                    "application": {
                        "status": "healthy",
                        "details": {
                            "version": "1.0.0",
                            "uptime": "2d 14h 32m",
                            "memory_usage": "45%"
                        }
                    }
                }
            }
            mock_create.return_value = mock_service
            
            # Monitoring system gets comprehensive health
            response = self.client.get("/health")
            assert response.status_code == 200
            
            health_data = response.json()
            assert health_data["success"] is True
            
            # Verify detailed metrics are available
            checkers = health_data["content"]["checkers"]
            assert "database" in checkers
            assert "application" in checkers
            
            # Verify database metrics
            db_checker = checkers["database"]
            assert "connection_pool" in db_checker["details"]
            assert "response_time" in db_checker["details"]
            
            # Verify application metrics
            app_checker = checkers["application"]
            assert "uptime" in app_checker["details"]
            assert "memory_usage" in app_checker["details"]

    def test_api_gateway_integration(self):
        """Test API gateway integration scenario."""
        # API gateway needs to discover and route to API
        response = self.client.get("/")
        assert response.status_code == 200
        
        root_data = response.json()
        assert root_data["success"] is True
        
        # API gateway checks service health
        response = self.client.get("/health/simple")
        assert response.status_code == 200
        
        # API gateway gets service info
        response = self.client.get("/info")
        assert response.status_code == 200
        
        info_data = response.json()
        assert info_data["success"] is True
        
        # Verify API gateway has necessary information
        content = info_data["content"]
        assert "name" in content
        assert "version" in content
        assert "endpoints" in content
        
        # API gateway should know all available endpoints
        endpoints = content["endpoints"]
        expected_endpoints = ["/", "/info", "/health", "/health/simple", "/health/ready", "/health/live"]
        for endpoint in expected_endpoints:
            assert endpoint in endpoints


class TestPerformanceAndScalability:
    """Tests for performance and scalability scenarios."""

    def setup_method(self):
        """Setup test client for each test."""
        self.app = create_application()
        self.client = TestClient(self.app)

    def test_high_frequency_health_checks(self):
        """Test high-frequency health checks scenario."""
        with patch('gearmeshing_ai.restapi.dependencies.health.create_default_health_service') as mock_create:
            mock_service = MagicMock(spec=HealthCheckService)
            mock_service.check_all_health.return_value = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "checkers": {}
            }
            mock_create.return_value = mock_service
            
            # Simulate high-frequency health checks
            start_time = time.time()
            
            for _ in range(100):
                response = self.client.get("/health/simple")
                assert response.status_code == 200
            
            end_time = time.time()
            
            # Should handle high frequency checks efficiently
            total_time = end_time - start_time
            assert total_time < 5.0  # Should complete within 5 seconds
            average_time = total_time / 100
            assert average_time < 0.05  # Average should be less than 50ms

    def test_concurrent_user_simulation(self):
        """Test concurrent user simulation scenario."""
        import threading
        import time
        
        with patch('gearmeshing_ai.restapi.dependencies.health.create_default_health_service') as mock_create:
            mock_service = MagicMock(spec=HealthCheckService)
            mock_service.check_all_health.return_value = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "checkers": {}
            }
            mock_create.return_value = mock_service
            
            results = []
            
            def user_workflow():
                try:
                    # User discovers API
                    response = self.client.get("/")
                    results.append(("root", response.status_code))
                    
                    # User checks health
                    response = self.client.get("/health/simple")
                    results.append(("health", response.status_code))
                    
                    # User gets info
                    response = self.client.get("/info")
                    results.append(("info", response.status_code))
                    
                except Exception as e:
                    results.append(("error", str(e)))
            
            # Simulate 20 concurrent users
            threads = []
            for _ in range(20):
                thread = threading.Thread(target=user_workflow)
                threads.append(thread)
            
            start_time = time.time()
            
            # Start all threads
            for thread in threads:
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            end_time = time.time()
            
            # Verify all requests succeeded
            success_count = sum(1 for endpoint, status in results if status == 200)
            total_requests = len(results)
            
            assert success_count == total_requests
            assert total_requests == 60  # 20 users * 3 requests each
            
            # Should complete in reasonable time
            total_time = end_time - start_time
            assert total_time < 10.0

    def test_memory_efficiency_under_load(self):
        """Test memory efficiency under load scenario."""
        import gc
        import sys
        
        with patch('gearmeshing_ai.restapi.dependencies.health.create_default_health_service') as mock_create:
            mock_service = MagicMock(spec=HealthCheckService)
            mock_service.check_all_health.return_value = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "checkers": {}
            }
            mock_create.return_value = mock_service
            
            # Make many requests to test memory efficiency
            for i in range(500):
                response = self.client.get("/")
                assert response.status_code == 200
                
                response = self.client.get("/health")
                assert response.status_code == 200
                
                response = self.client.get("/info")
                assert response.status_code == 200
                
                # Periodically force garbage collection
                if i % 100 == 0:
                    gc.collect()
            
            # Final garbage collection
            gc.collect()
            
            # API should still work normally
            response = self.client.get("/")
            assert response.status_code == 200


class TestErrorScenarios:
    """Tests for various error scenarios."""

    def setup_method(self):
        """Setup test client for each test."""
        self.app = create_application()
        self.client = TestClient(self.app)

    def test_service_degradation_scenario(self):
        """Test gradual service degradation scenario."""
        # Test without mocking - just verify endpoints respond
        response = self.client.get("/health/")
        # May be healthy or degraded depending on actual services
        assert response.status_code in [200, 503]
        
        # Test simple health
        response = self.client.get("/health/simple")
        assert response.status_code in [200, 503]

    def test_network_connectivity_issues(self):
        """Test network connectivity issues scenario."""
        with patch('gearmeshing_ai.restapi.dependencies.health.create_default_health_service') as mock_create:
            mock_service = MagicMock(spec=HealthCheckService)
            mock_create.return_value = mock_service
            
            # Simulate network timeout
            mock_service.check_all_health.side_effect = TimeoutError("Network timeout")
            
            # Health endpoints should handle gracefully
            response = self.client.get("/health")
            assert response.status_code == 503
            
            response = self.client.get("/health/simple")
            assert response.status_code == 503
            
            response = self.client.get("/health/ready")
            assert response.status_code == 503
            
            # Basic endpoints should still work
            response = self.client.get("/")
            assert response.status_code == 200
            
            response = self.client.get("/info")
            assert response.status_code == 200
            
            # Liveness should still work
            response = self.client.get("/health/live")
            assert response.status_code == 200

    def test_cascading_failure_scenario(self):
        """Test cascading failure scenario."""
        with patch('gearmeshing_ai.restapi.dependencies.health.create_default_health_service') as mock_create:
            mock_service = MagicMock(spec=HealthCheckService)
            mock_create.return_value = mock_service
            
            # Multiple components fail
            def failing_health_check():
                raise RuntimeError("Multiple components failed")
            
            mock_service.check_all_health.side_effect = failing_health_check
            
            # All health-dependent endpoints should fail
            health_response = self.client.get("/health")
            simple_response = self.client.get("/health/simple")
            ready_response = self.client.get("/health/ready")
            
            assert health_response.status_code == 503
            assert simple_response.status_code == 503
            assert ready_response.status_code == 503
            
            # Verify error responses are consistent
            for response in [health_response, simple_response, ready_response]:
                data = response.json()
                assert "detail" in data
                assert data["detail"]["success"] is False
                assert "message" in data["detail"]


class TestSecurityAndCompliance:
    """Tests for security and compliance scenarios."""

    def setup_method(self):
        """Setup test client for each test."""
        self.app = create_application()
        self.client = TestClient(self.app)

    def test_information_disclosure_prevention(self):
        """Test that sensitive information is not disclosed."""
        # Test that 404 responses are handled properly
        response = self.client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        
        # Response should be valid JSON
        data = response.json()
        assert isinstance(data, dict)

    def test_request_validation_security(self):
        """Test request validation for security."""
        client = TestClient(create_application())
        
        # Test malicious input in URL
        response = self.client.get("/health/../etc/passwd")
        assert response.status_code == 404
        
        # Test oversized headers
        response = self.client.get(
            "/",
            headers={"User-Agent": "A" * 10000}
        )
        # Should handle gracefully (either accept or reject, but not crash)
        assert response.status_code in [200, 400, 413, 431]
        
        # Test invalid HTTP methods
        response = self.client.request("TRACE", "/")
        assert response.status_code in [405, 404]

    def test_rate_limiting_behavior(self):
        """Test behavior under potential rate limiting scenarios."""
        # Make many rapid requests
        for _ in range(50):
            response = self.client.get("/health/live")
            # Liveness should be lightweight and always work
            assert response.status_code == 200
        
        # API should still be responsive
        response = self.client.get("/")
        assert response.status_code == 200


class TestLongRunningStability:
    """Tests for long-running stability."""

    def setup_method(self):
        """Setup test client for each test."""
        self.app = create_application()
        self.client = TestClient(self.app)

    def test_extended_operation_stability(self):
        """Test API stability over extended operation."""
        with patch('gearmeshing_ai.restapi.dependencies.health.create_default_health_service') as mock_create:
            mock_service = MagicMock(spec=HealthCheckService)
            mock_service.check_all_health.return_value = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "checkers": {}
            }
            mock_create.return_value = mock_service
            
            # Simulate extended operation with periodic health checks
            start_time = time.time()
            
            for cycle in range(100):
                # Periodic health check
                response = self.client.get("/health/simple")
                assert response.status_code == 200
                
                # Normal API usage
                response = self.client.get("/")
                assert response.status_code == 200
                
                # Info endpoint
                if cycle % 10 == 0:
                    response = self.client.get("/info")
                    assert response.status_code == 200
                
                # Small delay to simulate real usage
                time.sleep(0.01)
            
            end_time = time.time()
            
            # Should complete in reasonable time
            total_time = end_time - start_time
            assert total_time < 30.0
            
            # API should still be fully functional
            response = self.client.get("/health")
            assert response.status_code == 200

    def test_resource_cleanup_verification(self):
        """Test that resources are properly cleaned up."""
        # This test verifies that the API doesn't leak resources
        # by making many requests and checking that it still works
        
        for i in range(200):
            response = self.client.get("/")
            assert response.status_code == 200
            
            response = self.client.get("/health/live")
            assert response.status_code == 200
            
            if i % 50 == 0:
                # Force garbage collection periodically
                import gc
                gc.collect()
        
        # API should still work perfectly
        response = self.client.get("/info")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "endpoints" in data["content"]
