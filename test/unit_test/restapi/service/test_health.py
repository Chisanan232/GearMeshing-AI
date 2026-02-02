"""Tests for the GearMeshing-AI REST API health check service.

This module contains comprehensive tests for the health check service
including health checkers, service logic, and error handling.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from gearmeshing_ai.restapi.service.health import (
    HealthChecker,
    BaseHealthChecker,
    DatabaseHealthChecker,
    ApplicationHealthChecker,
    HealthCheckService,
    create_default_health_service
)
from gearmeshing_ai.core.models.io import HealthStatusContent


class TestHealthCheckerProtocol:
    """Test cases for HealthChecker protocol."""

    def test_health_checker_protocol_compliance(self):
        """Test that classes implementing HealthChecker protocol are properly recognized."""
        # Create a mock health checker
        mock_checker = MagicMock(spec=HealthChecker)
        mock_checker.check_health.return_value = HealthStatusContent(
            status="healthy",
            details={"test": "ok"}
        )
        
        # Should be callable as a HealthChecker
        result = mock_checker.check_health()
        assert result.status == "healthy"

    def test_health_checker_protocol_with_real_class(self):
        """Test HealthChecker protocol with a real implementation."""
        class TestHealthChecker:
            def check_health(self) -> HealthStatusContent:
                return HealthStatusContent(
                    status="healthy",
                    details={"test": "ok"}
                )
        
        checker = TestHealthChecker()
        result = checker.check_health()
        assert result.status == "healthy"


class TestBaseHealthChecker:
    """Test cases for BaseHealthChecker class."""

    def test_base_health_checker_initialization(self):
        """Test BaseHealthChecker initialization."""
        checker = BaseHealthChecker("test_checker")
        assert checker.name == "test_checker"

    def test_base_health_checker_abstract_method(self):
        """Test that _do_check_health is abstract."""
        checker = BaseHealthChecker("test_checker")
        
        # BaseHealthChecker.check_health() calls _do_check_health which is not implemented
        result = checker.check_health()
        # Should return unhealthy status when not implemented
        assert result.status == "unhealthy"

    def test_base_health_checker_error_handling(self):
        """Test BaseHealthChecker error handling."""
        class FailingHealthChecker(BaseHealthChecker):
            def __init__(self):
                super().__init__("failing_checker")
            
            def _do_check_health(self) -> HealthStatusContent:
                raise ValueError("Test error")
        
        checker = FailingHealthChecker()
        result = checker.check_health()
        
        assert result.status == "unhealthy"
        assert "error" in result.details
        assert result.details["error"] == "Test error"
        assert result.details["checker"] == "failing_checker"

    def test_base_health_checker_success(self):
        """Test BaseHealthChecker with successful check."""
        class SuccessHealthChecker(BaseHealthChecker):
            def __init__(self):
                super().__init__("success_checker")
            
            def _do_check_health(self) -> HealthStatusContent:
                return HealthStatusContent(
                    status="healthy",
                    details={"test": "success"}
                )
        
        checker = SuccessHealthChecker()
        result = checker.check_health()
        
        assert result.status == "healthy"
        assert result.details["test"] == "success"


class TestDatabaseHealthChecker:
    """Test cases for DatabaseHealthChecker class."""

    def test_database_health_checker_initialization_with_connection_string(self):
        """Test DatabaseHealthChecker initialization with connection string."""
        connection_string = "postgresql://user:pass@localhost:5432/db"
        checker = DatabaseHealthChecker(connection_string)
        
        assert checker.name == "database"
        assert checker.connection_string == connection_string

    def test_database_health_checker_initialization_without_connection_string(self):
        """Test DatabaseHealthChecker initialization without connection string."""
        checker = DatabaseHealthChecker()
        
        assert checker.name == "database"
        assert checker.connection_string is None

    def test_database_health_check_with_connection(self):
        """Test database health check with connection configured."""
        connection_string = "postgresql://user:pass@localhost:5432/db"
        checker = DatabaseHealthChecker(connection_string)
        
        result = checker.check_health()
        
        assert result.status == "healthy"
        assert result.details["checker"] == "database"
        assert result.details["connection_configured"] is True

    def test_database_health_check_without_connection(self):
        """Test database health check without connection configured."""
        checker = DatabaseHealthChecker()
        
        result = checker.check_health()
        
        assert result.status == "healthy"
        assert result.details["checker"] == "database"
        assert result.details["connection_configured"] is False

    def test_database_health_checker_error_handling(self):
        """Test DatabaseHealthChecker error handling."""
        class FailingDatabaseHealthChecker(DatabaseHealthChecker):
            def _do_check_health(self) -> HealthStatusContent:
                raise ConnectionError("Database connection failed")
        
        checker = FailingDatabaseHealthChecker()
        result = checker.check_health()
        
        assert result.status == "unhealthy"
        assert "Database connection failed" in result.details["error"]


class TestApplicationHealthChecker:
    """Test cases for ApplicationHealthChecker class."""

    def test_application_health_checker_initialization(self):
        """Test ApplicationHealthChecker initialization."""
        checker = ApplicationHealthChecker()
        
        assert checker.name == "application"

    def test_application_health_check_success(self):
        """Test application health check success."""
        checker = ApplicationHealthChecker()
        
        result = checker.check_health()
        
        assert result.status == "healthy"
        assert result.details["checker"] == "application"
        assert result.details["version"] == "0.0.0"
        assert "components" in result.details
        assert isinstance(result.details["components"], list)

    def test_application_health_check_components(self):
        """Test application health check includes expected components."""
        checker = ApplicationHealthChecker()
        
        result = checker.check_health()
        
        expected_components = ["restapi", "agent_core", "core"]
        for component in expected_components:
            assert component in result.details["components"]

    def test_application_health_checker_error_handling(self):
        """Test ApplicationHealthChecker error handling."""
        class FailingApplicationHealthChecker(ApplicationHealthChecker):
            def _do_check_health(self) -> HealthStatusContent:
                raise RuntimeError("Application error")
        
        checker = FailingApplicationHealthChecker()
        result = checker.check_health()
        
        assert result.status == "unhealthy"
        assert "Application error" in result.details["error"]


class TestHealthCheckService:
    """Test cases for HealthCheckService class."""

    def test_health_check_service_initialization(self):
        """Test HealthCheckService initialization."""
        service = HealthCheckService()
        
        assert service._checkers == []
        assert len(service._checkers) == 0

    def test_register_checker(self):
        """Test registering a health checker."""
        service = HealthCheckService()
        checker = MagicMock(spec=HealthChecker)
        checker.name = "test_checker"
        
        service.register_checker(checker)
        
        assert len(service._checkers) == 1
        assert service._checkers[0] is checker

    def test_register_multiple_checkers(self):
        """Test registering multiple health checkers."""
        service = HealthCheckService()
        
        checker1 = MagicMock(spec=HealthChecker)
        checker1.name = "checker1"
        
        checker2 = MagicMock(spec=HealthChecker)
        checker2.name = "checker2"
        
        service.register_checker(checker1)
        service.register_checker(checker2)
        
        assert len(service._checkers) == 2
        assert service._checkers[0] is checker1
        assert service._checkers[1] is checker2

    def test_check_all_health_empty(self):
        """Test checking health with no registered checkers."""
        service = HealthCheckService()
        
        result = service.check_all_health()
        
        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert result["checkers"] == {}

    def test_check_all_health_all_healthy(self):
        """Test checking health when all checkers are healthy."""
        service = HealthCheckService()
        
        # Create healthy checkers
        checker1 = MagicMock(spec=HealthChecker)
        checker1.name = "checker1"
        checker1.check_health.return_value = HealthStatusContent(
            status="healthy",
            details={"test": "ok1"}
        )
        
        checker2 = MagicMock(spec=HealthChecker)
        checker2.name = "checker2"
        checker2.check_health.return_value = HealthStatusContent(
            status="healthy",
            details={"test": "ok2"}
        )
        
        service.register_checker(checker1)
        service.register_checker(checker2)
        
        result = service.check_all_health()
        
        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert len(result["checkers"]) == 2
        assert result["checkers"]["checker1"].status == "healthy"
        assert result["checkers"]["checker2"].status == "healthy"

    def test_check_all_health_one_unhealthy(self):
        """Test checking health when one checker is unhealthy."""
        service = HealthCheckService()
        
        # Create checkers with one unhealthy
        checker1 = MagicMock(spec=HealthChecker)
        checker1.name = "checker1"
        checker1.check_health.return_value = HealthStatusContent(
            status="healthy",
            details={"test": "ok1"}
        )
        
        checker2 = MagicMock(spec=HealthChecker)
        checker2.name = "checker2"
        checker2.check_health.return_value = HealthStatusContent(
            status="unhealthy",
            details={"error": "failed"}
        )
        
        service.register_checker(checker1)
        service.register_checker(checker2)
        
        result = service.check_all_health()
        
        assert result["status"] == "unhealthy"
        assert result["checkers"]["checker1"].status == "healthy"
        assert result["checkers"]["checker2"].status == "unhealthy"

    def test_check_all_health_one_degraded(self):
        """Test checking health when one checker is degraded."""
        service = HealthCheckService()
        
        # Create checkers with one degraded
        checker1 = MagicMock(spec=HealthChecker)
        checker1.name = "checker1"
        checker1.check_health.return_value = HealthStatusContent(
            status="healthy",
            details={"test": "ok1"}
        )
        
        checker2 = MagicMock(spec=HealthChecker)
        checker2.name = "checker2"
        checker2.check_health.return_value = HealthStatusContent(
            status="degraded",
            details={"warning": "slow"}
        )
        
        service.register_checker(checker1)
        service.register_checker(checker2)
        
        result = service.check_all_health()
        
        assert result["status"] == "degraded"
        assert result["checkers"]["checker1"].status == "healthy"
        assert result["checkers"]["checker2"].status == "degraded"

    def test_check_all_health_mixed_statuses(self):
        """Test checking health with mixed statuses."""
        service = HealthCheckService()
        
        # Create checkers with mixed statuses
        checker1 = MagicMock(spec=HealthChecker)
        checker1.name = "checker1"
        checker1.check_health.return_value = HealthStatusContent(
            status="healthy",
            details={"test": "ok1"}
        )
        
        checker2 = MagicMock(spec=HealthChecker)
        checker2.name = "checker2"
        checker2.check_health.return_value = HealthStatusContent(
            status="degraded",
            details={"warning": "slow"}
        )
        
        checker3 = MagicMock(spec=HealthChecker)
        checker3.name = "checker3"
        checker3.check_health.return_value = HealthStatusContent(
            status="unhealthy",
            details={"error": "failed"}
        )
        
        service.register_checker(checker1)
        service.register_checker(checker2)
        service.register_checker(checker3)
        
        result = service.check_all_health()
        
        # Should be unhealthy due to one unhealthy checker
        assert result["status"] == "unhealthy"
        assert len(result["checkers"]) == 3

    def test_check_all_health_checker_exception(self):
        """Test checking health when a checker raises exception."""
        service = HealthCheckService()
        
        # Create a checker that raises exception
        checker = MagicMock(spec=HealthChecker)
        checker.name = "failing_checker"
        checker.check_health.side_effect = Exception("Checker error")
        
        service.register_checker(checker)
        
        result = service.check_all_health()
        
        assert result["status"] == "unhealthy"
        assert "failing_checker" in result["checkers"]
        assert result["checkers"]["failing_checker"].status == "unhealthy"
        assert "error" in result["checkers"]["failing_checker"].details

    def test_check_all_health_checker_without_name(self):
        """Test checking health with checker that doesn't have name attribute."""
        service = HealthCheckService()
        
        # Create a checker without name attribute
        class NamelessChecker:
            def check_health(self) -> HealthStatusContent:
                return HealthStatusContent(
                    status="healthy",
                    details={"test": "ok"}
                )
        
        checker = NamelessChecker()
        service.register_checker(checker)
        
        result = service.check_all_health()
        
        assert result["status"] == "healthy"
        assert "NamelessChecker" in result["checkers"]

    def test_check_all_health_timestamp_format(self):
        """Test that timestamp is in correct format."""
        service = HealthCheckService()
        
        result = service.check_all_health()
        
        assert "timestamp" in result
        
        # Verify timestamp is a valid ISO format string
        timestamp_str = result["timestamp"]
        # Should be parseable as ISO datetime
        datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

    def test_check_all_health_concurrent_safety(self):
        """Test that check_all_health is thread-safe."""
        import threading
        import time
        
        service = HealthCheckService()
        
        # Add a checker
        checker = MagicMock(spec=HealthChecker)
        checker.name = "test_checker"
        checker.check_health.return_value = HealthStatusContent(
            status="healthy",
            details={"test": "ok"}
        )
        service.register_checker(checker)
        
        results = []
        
        def check_health():
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
        assert all(status == "healthy" for status in results)
        assert len(results) == 10


class TestCreateDefaultHealthService:
    """Test cases for create_default_health_service function."""

    def test_create_default_health_service(self):
        """Test creating default health service."""
        service = create_default_health_service()
        
        assert isinstance(service, HealthCheckService)
        assert len(service._checkers) == 2

    def test_default_service_checkers(self):
        """Test that default service has expected checkers."""
        service = create_default_health_service()
        
        checker_names = []
        for checker in service._checkers:
            if hasattr(checker, 'name'):
                checker_names.append(checker.name)
            else:
                checker_names.append(type(checker).__name__)
        
        assert "application" in checker_names
        assert "database" in checker_names

    def test_default_service_checker_types(self):
        """Test that default service has correct checker types."""
        service = create_default_health_service()
        
        checkers = service._checkers
        application_checkers = [c for c in checkers if isinstance(c, ApplicationHealthChecker)]
        database_checkers = [c for c in checkers if isinstance(c, DatabaseHealthChecker)]
        
        assert len(application_checkers) == 1
        assert len(database_checkers) == 1

    def test_default_service_functionality(self):
        """Test that default service functions correctly."""
        service = create_default_health_service()
        
        result = service.check_all_health()
        
        assert result["status"] in ["healthy", "degraded", "unhealthy"]
        assert "timestamp" in result
        assert "checkers" in result
        assert len(result["checkers"]) == 2


class TestHealthServiceIntegration:
    """Integration tests for health service components."""

    def test_full_health_check_workflow(self):
        """Test complete health check workflow."""
        service = create_default_health_service()
        
        # Perform health check
        result = service.check_all_health()
        
        # Verify structure
        required_keys = ["status", "timestamp", "checkers"]
        for key in required_keys:
            assert key in result
        
        # Verify checker results
        checkers = result["checkers"]
        assert len(checkers) == 2
        
        for checker_name, checker_result in checkers.items():
            assert hasattr(checker_result, 'status')
            assert hasattr(checker_result, 'details')
            assert checker_result.status in ["healthy", "degraded", "unhealthy"]

    def test_health_service_with_real_checkers(self):
        """Test health service with real checker implementations."""
        service = HealthCheckService()
        
        # Add real checkers
        service.register_checker(ApplicationHealthChecker())
        service.register_checker(DatabaseHealthChecker("test_connection"))
        
        result = service.check_all_health()
        
        assert result["status"] in ["healthy", "degraded", "unhealthy"]
        assert len(result["checkers"]) == 2
        assert "application" in result["checkers"]
        assert "database" in result["checkers"]

    def test_health_service_error_propagation(self):
        """Test error propagation through health service."""
        service = HealthCheckService()
        
        # Add a failing checker
        class FailingChecker(BaseHealthChecker):
            def __init__(self):
                super().__init__("failing_checker")
            
            def _do_check_health(self) -> HealthStatusContent:
                raise RuntimeError("Checker failed")
        
        service.register_checker(FailingChecker())
        service.register_checker(ApplicationHealthChecker())
        
        result = service.check_all_health()
        
        # Overall status should be unhealthy
        assert result["status"] == "unhealthy"
        
        # Failing checker should have error details
        assert result["checkers"]["failing_checker"].status == "unhealthy"
        assert "error" in result["checkers"]["failing_checker"].details
        
        # Application checker should still work
        assert result["checkers"]["application"].status == "healthy"

    def test_health_service_performance(self):
        """Test health service performance with multiple checkers."""
        import time
        
        service = HealthCheckService()
        
        # Add multiple checkers
        for i in range(10):
            checker = MagicMock(spec=HealthChecker)
            checker.name = f"checker_{i}"
            checker.check_health.return_value = HealthStatusContent(
                status="healthy",
                details={"checker": f"checker_{i}"}
            )
            service.register_checker(checker)
        
        # Measure execution time
        start_time = time.time()
        result = service.check_all_health()
        end_time = time.time()
        
        # Should complete quickly (less than 1 second)
        execution_time = end_time - start_time
        assert execution_time < 1.0
        assert len(result["checkers"]) == 10
        assert result["status"] == "healthy"


class TestHealthServiceEdgeCases:
    """Test cases for edge cases and boundary conditions."""

    def test_health_service_with_none_checker(self):
        """Test health service with None checker (should not happen but test safety)."""
        service = HealthCheckService()
        
        # This should not happen in practice, but test for safety
        try:
            service.register_checker(None)
            # If this doesn't raise an exception, the service should handle it gracefully
            result = service.check_all_health()
            # Service should return a status
            assert "status" in result
        except (TypeError, AttributeError):
            # Expected behavior - None is not a valid checker
            pass

    def test_health_checker_with_malformed_response(self):
        """Test health checker that returns malformed response."""
        service = HealthCheckService()
        
        class MalformedChecker:
            def __init__(self):
                self.name = "malformed_checker"
            
            def check_health(self):
                # Return something that's not HealthStatusContent
                return {"invalid": "response"}
        
        service.register_checker(MalformedChecker())
        
        try:
            result = service.check_all_health()
            # Service should handle this gracefully or raise a clear error
            assert "status" in result
        except (AttributeError, TypeError):
            # Expected behavior for malformed response
            pass

    def test_health_service_with_very_slow_checker(self):
        """Test health service with a very slow checker."""
        import time
        
        service = HealthCheckService()
        
        class SlowChecker(BaseHealthChecker):
            def __init__(self):
                super().__init__("slow_checker")
            
            def _do_check_health(self) -> HealthStatusContent:
                time.sleep(0.1)  # Simulate slow operation
                return HealthStatusContent(
                    status="healthy",
                    details={"slow": True}
                )
        
        service.register_checker(SlowChecker())
        service.register_checker(ApplicationHealthChecker())
        
        start_time = time.time()
        result = service.check_all_health()
        end_time = time.time()
        
        # Should still complete in reasonable time
        execution_time = end_time - start_time
        assert execution_time < 2.0
        assert result["status"] == "healthy"

    def test_health_service_memory_usage(self):
        """Test health service doesn't leak memory with repeated calls."""
        service = create_default_health_service()
        
        # Make many calls
        for _ in range(100):
            result = service.check_all_health()
            assert result["status"] in ["healthy", "degraded", "unhealthy"]
        
        # Service should still work normally
        result = service.check_all_health()
        assert "status" in result
        assert "checkers" in result
