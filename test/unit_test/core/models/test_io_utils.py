"""Tests for the GearMeshing-AI core I/O utilities.

This module contains comprehensive tests for utility functions
that work with I/O models and create standardized responses.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from gearmeshing_ai.core.models.io.common import (
    ApiInfoContent,
    ClientInfoContent,
    ErrorContent,
    GlobalResponse,
    HealthStatus,
    HealthStatusContent,
    LivenessContent,
    LivenessStatus,
    ReadinessContent,
    ReadinessStatus,
    SimpleHealthContent,
    SimpleHealthStatus,
    WelcomeContent,
)
from gearmeshing_ai.core.models.io.utils import (
    create_api_info_response,
    create_error_response,
    create_global_response,
    create_health_response,
    create_liveness_response,
    create_readiness_response,
    create_simple_health_response,
    create_success_response,
    create_welcome_response,
    get_client_info,
    sanitize_path,
)


class TestCreateGlobalResponse:
    """Test cases for create_global_response function."""

    def test_create_global_response_success(self):
        """Test create_global_response for success case."""
        content = {"data": "test"}
        response = create_global_response(success=True, message="Operation successful", content=content)

        assert isinstance(response, GlobalResponse)
        assert response.success is True
        assert response.message == "Operation successful"
        assert response.content == content
        assert isinstance(response.timestamp, datetime)

    def test_create_global_response_error(self):
        """Test create_global_response for error case."""
        error_content = ErrorContent(error_code="TEST_ERROR", details={"error": "test error"})
        response = create_global_response(success=False, message="Operation failed", content=error_content)

        assert response.success is False
        assert response.message == "Operation failed"
        assert response.content.error_code == "TEST_ERROR"

    def test_create_global_response_without_content(self):
        """Test create_global_response without content."""
        response = create_global_response(success=True, message="No content response")

        assert response.success is True
        assert response.message == "No content response"
        assert response.content is None

    def test_create_global_response_with_custom_timestamp(self):
        """Test create_global_response with custom timestamp."""
        custom_time = datetime(2023, 1, 1, 12, 0, 0)
        response = create_global_response(success=True, message="Test", content=None, timestamp=custom_time)

        assert response.timestamp == custom_time

    def test_create_global_response_different_content_types(self):
        """Test create_global_response with different content types."""
        # String content
        response1 = create_global_response(success=True, message="String content", content="test string")
        assert response1.content == "test string"

        # Dict content
        response2 = create_global_response(success=True, message="Dict content", content={"key": "value"})
        assert response2.content == {"key": "value"}

        # List content
        response3 = create_global_response(success=True, message="List content", content=[1, 2, 3])
        assert response3.content == [1, 2, 3]


class TestCreateSuccessResponse:
    """Test cases for create_success_response function."""

    def test_create_success_response_basic(self):
        """Test create_success_response basic usage."""
        content = {"result": "success"}
        response = create_success_response(message="Operation completed", content=content)

        assert response.success is True
        assert response.message == "Operation completed"
        assert response.content == content

    def test_create_success_response_without_content(self):
        """Test create_success_response without content."""
        response = create_success_response("Simple success")

        assert response.success is True
        assert response.message == "Simple success"
        assert response.content is None

    def test_create_success_response_default_message(self):
        """Test create_success_response with default message."""
        response = create_success_response()

        assert response.success is True
        assert response.message == "Operation successful"
        assert response.content is None

    def test_create_success_response_with_complex_content(self):
        """Test create_success_response with complex content."""
        content = {
            "user": {"id": 1, "name": "John"},
            "actions": ["create", "update"],
            "metadata": {"timestamp": "2023-01-01"},
        }
        response = create_success_response(message="Complex operation", content=content)

        assert response.content == content
        assert response.content["user"]["name"] == "John"
        assert len(response.content["actions"]) == 2


class TestCreateErrorResponse:
    """Test cases for create_error_response function."""

    def test_create_error_response_basic(self):
        """Test create_error_response basic usage."""
        response = create_error_response(message="Operation failed", status_code=400)

        assert response.success is False
        assert response.message == "Operation failed"
        assert isinstance(response.content, ErrorContent)
        assert response.content.error_code == str(400)

    def test_create_error_response_with_details(self):
        """Test create_error_response with details."""
        details = {"field": "username", "error": "required"}
        response = create_error_response(message="Validation error", status_code=422, details=details)

        assert response.content.details == details
        assert response.content.error_code == "422"

    def test_create_error_response_with_error_code(self):
        """Test create_error_response with custom error code."""
        response = create_error_response(message="Custom error", status_code=500, error_code="INTERNAL_ERROR")

        assert response.content.error_code == "INTERNAL_ERROR"

    def test_create_error_response_default_values(self):
        """Test create_error_response with default values."""
        response = create_error_response()

        assert response.success is False
        assert response.message == "An error occurred"
        assert response.content.error_code == "500"
        assert response.content.details is None

    def test_create_error_response_with_stack_trace(self):
        """Test create_error_response with stack trace."""
        stack_trace = "Traceback (most recent call last):..."
        response = create_error_response(message="Server error", status_code=500, stack_trace=stack_trace)

        assert response.content.stack_trace == stack_trace


class TestCreateWelcomeResponse:
    """Test cases for create_welcome_response function."""

    def test_create_welcome_response_basic(self):
        """Test create_welcome_response basic usage."""
        response = create_welcome_response(message="Welcome to API", version="1.0.0", docs="/docs", health="/health")

        assert response.success is True
        assert isinstance(response.content, WelcomeContent)
        assert response.content.message == "Welcome to API"
        assert response.content.version == "1.0.0"
        assert response.content.docs == "/docs"
        assert response.content.health == "/health"

    def test_create_welcome_response_default_values(self):
        """Test create_welcome_response with default values."""
        response = create_welcome_response()

        assert response.content.message == "Welcome to GearMeshing-AI API"
        assert response.content.version == "0.0.0"
        assert response.content.docs == "/docs"
        assert response.content.health == "/health"

    def test_create_welcome_response_custom_values(self):
        """Test create_welcome_response with custom values."""
        response = create_welcome_response(
            message="Custom welcome", version="2.1.0", docs="/api/docs", health="/api/health"
        )

        assert response.content.message == "Custom welcome"
        assert response.content.version == "2.1.0"
        assert response.content.docs == "/api/docs"
        assert response.content.health == "/api/health"


class TestCreateApiInfoResponse:
    """Test cases for create_api_info_response function."""

    def test_create_api_info_response_basic(self):
        """Test create_api_info_response basic usage."""
        response = create_api_info_response(
            name="Test API",
            version="1.0.0",
            description="Test API description",
            endpoints=["/health", "/info"],
            documentation={"swagger": "/docs"},
        )

        assert response.success is True
        assert isinstance(response.content, ApiInfoContent)
        assert response.content.name == "Test API"
        assert response.content.version == "1.0.0"
        assert response.content.description == "Test API description"
        assert response.content.endpoints == ["/health", "/info"]
        assert response.content.documentation == {"swagger": "/docs"}

    def test_create_api_info_response_with_full_documentation(self):
        """Test create_api_info_response with full documentation."""
        documentation = {"swagger": "/docs", "redoc": "/redoc", "openapi": "/openapi.json"}
        response = create_api_info_response(
            name="Full API",
            version="1.0.0",
            description="API with full documentation",
            endpoints=["/"],
            documentation=documentation,
        )

        assert response.content.documentation == documentation
        assert len(response.content.documentation) == 3

    def test_create_api_info_response_empty_endpoints(self):
        """Test create_api_info_response with empty endpoints."""
        response = create_api_info_response(
            name="Empty API", version="1.0.0", description="API with no endpoints", endpoints=[], documentation={}
        )

        assert response.content.endpoints == []
        assert response.content.documentation == {}


class TestCreateHealthResponse:
    """Test cases for create_health_response function."""

    def test_create_health_response_healthy(self):
        """Test create_health_response for healthy status."""
        checkers = {"database": "ok", "cache": "ok"}
        details = {"uptime": "24h"}
        response = create_health_response(status=HealthStatus.HEALTHY, checkers=checkers, details=details)

        assert response.success is True
        assert isinstance(response.content, HealthStatusContent)
        assert response.content.status == HealthStatus.HEALTHY
        assert response.content.checkers == checkers
        assert response.content.details == details

    def test_create_health_response_degraded(self):
        """Test create_health_response for degraded status."""
        response = create_health_response(
            status=HealthStatus.DEGRADED, checkers={"database": "slow"}, details={"warning": "high latency"}
        )

        assert response.content.status == HealthStatus.DEGRADED
        assert response.content.checkers == {"database": "slow"}

    def test_create_health_response_unhealthy(self):
        """Test create_health_response for unhealthy status."""
        response = create_health_response(
            status=HealthStatus.UNHEALTHY, checkers={"database": "failed"}, details={"error": "connection timeout"}
        )

        assert response.content.status == HealthStatus.UNHEALTHY
        assert response.success is False  # Unhealthy should have success=False

    def test_create_health_response_without_checkers_and_details(self):
        """Test create_health_response without checkers and details."""
        response = create_health_response(status=HealthStatus.HEALTHY)

        assert response.content.status == HealthStatus.HEALTHY
        assert response.content.checkers is None
        assert response.content.details is None


class TestCreateSimpleHealthResponse:
    """Test cases for create_simple_health_response function."""

    def test_create_simple_health_response_ok(self):
        """Test create_simple_health_response for OK status."""
        response = create_simple_health_response(status=SimpleHealthStatus.OK)

        assert response.success is True
        assert isinstance(response.content, SimpleHealthContent)
        assert response.content.status == SimpleHealthStatus.OK

    def test_create_simple_health_response_error(self):
        """Test create_simple_health_response for ERROR status."""
        response = create_simple_health_response(status=SimpleHealthStatus.ERROR)

        assert response.success is False
        assert response.content.status == SimpleHealthStatus.ERROR

    def test_create_simple_health_response_default(self):
        """Test create_simple_health_response with default status."""
        response = create_simple_health_response()

        assert response.content.status == SimpleHealthStatus.OK


class TestCreateReadinessResponse:
    """Test cases for create_readiness_response function."""

    def test_create_readiness_response_ready(self):
        """Test create_readiness_response for READY status."""
        response = create_readiness_response(status=ReadinessStatus.READY)

        assert response.success is True
        assert isinstance(response.content, ReadinessContent)
        assert response.content.status == ReadinessStatus.READY

    def test_create_readiness_response_not_ready(self):
        """Test create_readiness_response for NOT_READY status."""
        response = create_readiness_response(status=ReadinessStatus.NOT_READY)

        assert response.success is False
        assert response.content.status == ReadinessStatus.NOT_READY

    def test_create_readiness_response_default(self):
        """Test create_readiness_response with default status."""
        response = create_readiness_response()

        assert response.content.status == ReadinessStatus.READY


class TestCreateLivenessResponse:
    """Test cases for create_liveness_response function."""

    def test_create_liveness_response_alive(self):
        """Test create_liveness_response for ALIVE status."""
        response = create_liveness_response(status=LivenessStatus.ALIVE)

        assert response.success is True
        assert isinstance(response.content, LivenessContent)
        assert response.content.status == LivenessStatus.ALIVE

    def test_create_liveness_response_default(self):
        """Test create_liveness_response with default status."""
        response = create_liveness_response()

        assert response.content.status == LivenessStatus.ALIVE


class TestGetClientInfo:
    """Test cases for get_client_info function."""

    def test_get_client_info_basic(self):
        """Test get_client_info with basic request info."""
        # Mock request object
        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.100"
        mock_request.headers = {"user-agent": "TestAgent/1.0"}
        mock_request.method = "POST"
        mock_request.url = "http://example.com/api/test"

        client_info = get_client_info(mock_request)

        assert isinstance(client_info, ClientInfoContent)
        assert client_info.client_ip == "192.168.1.100"
        assert client_info.user_agent == "TestAgent/1.0"
        assert client_info.method == "POST"
        assert client_info.url == "http://example.com/api/test"

    def test_get_client_info_missing_headers(self):
        """Test get_client_info with missing headers."""
        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {}  # No user-agent header
        mock_request.method = "GET"
        mock_request.url = "http://example.com"

        client_info = get_client_info(mock_request)

        assert client_info.client_ip == "127.0.0.1"
        assert client_info.user_agent == ""  # Should default to empty string
        assert client_info.method == "GET"
        assert client_info.url == "http://example.com"

    def test_get_client_info_none_client(self):
        """Test get_client_info with None client."""
        mock_request = MagicMock()
        mock_request.client = None  # No client info
        mock_request.headers = {"user-agent": "TestAgent"}
        mock_request.method = "GET"
        mock_request.url = "http://example.com"

        client_info = get_client_info(mock_request)

        assert client_info.client_ip == ""  # Should default to empty string
        assert client_info.user_agent == "TestAgent"
        assert client_info.method == "GET"
        assert client_info.url == "http://example.com"

    def test_get_client_info_complex_url(self):
        """Test get_client_info with complex URL."""
        mock_request = MagicMock()
        mock_request.client.host = "10.0.0.1"
        mock_request.headers = {"user-agent": "ComplexAgent/2.0"}
        mock_request.method = "PUT"
        mock_request.url = "https://api.example.com:8443/v1/users/123?active=true"

        client_info = get_client_info(mock_request)

        assert client_info.client_ip == "10.0.0.1"
        assert client_info.user_agent == "ComplexAgent/2.0"
        assert client_info.method == "PUT"
        assert client_info.url == "https://api.example.com:8443/v1/users/123?active=true"


class TestSanitizePath:
    """Test cases for sanitize_path function."""

    def test_sanitize_path_basic(self):
        """Test sanitize_path with basic path."""
        path = "/api/v1/users/123"
        sanitized = sanitize_path(path)

        assert sanitized == "/api/v1/users/123"

    def test_sanitize_path_with_trailing_slash(self):
        """Test sanitize_path with trailing slash."""
        path = "/api/v1/users/"
        sanitized = sanitize_path(path)

        assert sanitized == "/api/v1/users"

    def test_sanitize_path_with_multiple_slashes(self):
        """Test sanitize_path with multiple consecutive slashes."""
        path = "/api//v1///users//123"
        sanitized = sanitize_path(path)

        assert sanitized == "/api/v1/users/123"

    def test_sanitize_path_empty_path(self):
        """Test sanitize_path with empty path."""
        path = ""
        sanitized = sanitize_path(path)

        assert sanitized == "/"

    def test_sanitize_path_root_path(self):
        """Test sanitize_path with root path."""
        path = "/"
        sanitized = sanitize_path(path)

        assert sanitized == "/"

    def test_sanitize_path_with_query_params(self):
        """Test sanitize_path with query parameters."""
        path = "/api/v1/users?active=true&page=2"
        sanitized = sanitize_path(path)

        assert sanitized == "/api/v1/users"

    def test_sanitize_path_with_fragment(self):
        """Test sanitize_path with URL fragment."""
        path = "/api/v1/users#section1"
        sanitized = sanitize_path(path)

        assert sanitized == "/api/v1/users"

    def test_sanitize_path_with_query_and_fragment(self):
        """Test sanitize_path with both query and fragment."""
        path = "/api/v1/users?active=true#section1"
        sanitized = sanitize_path(path)

        assert sanitized == "/api/v1/users"

    def test_sanitize_path_with_special_characters(self):
        """Test sanitize_path with special characters."""
        path = "/api/v1/users/user-name_123"
        sanitized = sanitize_path(path)

        assert sanitized == "/api/v1/users/user-name_123"

    def test_sanitize_path_with_encoded_characters(self):
        """Test sanitize_path with URL encoded characters."""
        path = "/api/v1/users/user%20name"
        sanitized = sanitize_path(path)

        assert sanitized == "/api/v1/users/user%20name"  # Should preserve encoding

    def test_sanitize_path_very_long_path(self):
        """Test sanitize_path with very long path."""
        long_segment = "a" * 1000
        path = f"/api/v1/users/{long_segment}"
        sanitized = sanitize_path(path)

        assert sanitized == path  # Should preserve long paths

    def test_sanitize_path_with_dots(self):
        """Test sanitize_path with path segments containing dots."""
        path = "/api/v1.0/users/123.json"
        sanitized = sanitize_path(path)

        assert sanitized == "/api/v1.0/users/123.json"

    def test_sanitize_path_with_leading_trailing_spaces(self):
        """Test sanitize_path with leading/trailing whitespace."""
        path = "  /api/v1/users/123  "
        sanitized = sanitize_path(path)

        assert sanitized == "/api/v1/users/123"

    def test_sanitize_path_none_input(self):
        """Test sanitize_path with None input."""
        with pytest.raises(TypeError):
            sanitize_path(None)

    def test_sanitize_path_non_string_input(self):
        """Test sanitize_path with non-string input."""
        with pytest.raises(TypeError):
            sanitize_path(123)


class TestUtilityIntegration:
    """Integration tests for utility functions."""

    def test_response_creation_chain(self):
        """Test chaining multiple response creation functions."""
        # Create success response
        success = create_success_response(message="Operation completed", content={"result": "success"})

        # Create error response
        error = create_error_response(message="Operation failed", status_code=400, details={"field": "invalid"})

        # Verify both are valid GlobalResponse instances
        assert isinstance(success, GlobalResponse)
        assert isinstance(error, GlobalResponse)
        assert success.success is True
        assert error.success is False

    def test_health_response_consistency(self):
        """Test consistency across health response functions."""
        # Create all types of health responses
        health = create_health_response(status=HealthStatus.HEALTHY)
        simple = create_simple_health_response(status=SimpleHealthStatus.OK)
        readiness = create_readiness_response(status=ReadinessStatus.READY)
        liveness = create_liveness_response(status=LivenessStatus.ALIVE)

        # All should be GlobalResponse instances
        assert isinstance(health, GlobalResponse)
        assert isinstance(simple, GlobalResponse)
        assert isinstance(readiness, GlobalResponse)
        assert isinstance(liveness, GlobalResponse)

        # All should have success=True for healthy/ready/alive states
        assert health.success is True
        assert simple.success is True
        assert readiness.success is True
        assert liveness.success is True

    def test_utility_functions_with_real_data(self):
        """Test utility functions with realistic data."""
        # Test welcome response
        welcome = create_welcome_response(
            message="Welcome to Production API",
            version="2.1.0",
            docs="https://api.example.com/docs",
            health="https://api.example.com/health",
        )

        # Test API info response
        api_info = create_api_info_response(
            name="Production API",
            version="2.1.0",
            description="Enterprise API for production use",
            endpoints=["/health", "/info", "/users", "/orders", "/products"],
            documentation={
                "swagger": "https://api.example.com/docs",
                "redoc": "https://api.example.com/redoc",
                "openapi": "https://api.example.com/openapi.json",
            },
        )

        # Verify realistic data
        assert welcome.content.docs.startswith("https://")
        assert welcome.content.health.startswith("https://")
        assert len(api_info.content.endpoints) == 5
        assert len(api_info.content.documentation) == 3

    def test_error_response_with_realistic_error(self):
        """Test error response with realistic error scenario."""
        error_response = create_error_response(
            message="Validation failed",
            status_code=422,
            error_code="VALIDATION_ERROR",
            details={"email": {"issue": "invalid format", "provided": "not-an-email", "expected": "user@domain.com"}},
            stack_trace="Traceback (most recent call last):\n  File app.py, line 42\n...",
        )

        assert error_response.success is False
        assert error_response.content.error_code == "VALIDATION_ERROR"
        assert "email" in error_response.content.details
        assert error_response.content.stack_trace is not None

    def test_client_info_with_real_request(self):
        """Test get_client_info with realistic request data."""
        # Simulate a realistic web request
        mock_request = MagicMock()
        mock_request.client.host = "203.0.113.42"
        mock_request.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "x-forwarded-for": "203.0.113.42",
            "x-real-ip": "203.0.113.42",
        }
        mock_request.method = "POST"
        mock_request.url = "https://api.example.com/v1/users?include=profile&active=true"

        client_info = get_client_info(mock_request)

        assert client_info.client_ip == "203.0.113.42"
        assert "Mozilla" in client_info.user_agent
        assert client_info.method == "POST"
        assert "users" in client_info.url

    def test_path_sanitization_real_world_examples(self):
        """Test sanitize_path with real-world path examples."""
        test_cases = [
            ("/api/v1/users/", "/api/v1/users"),
            ("/api//v1///users//", "/api/v1/users"),
            ("/api/v1/users/?active=true", "/api/v1/users"),
            ("/api/v1/users#profile", "/api/v1/users"),
            ("/api/v1/users?active=true&page=2#profile", "/api/v1/users"),
            ("//api//v1//users//", "/api/v1/users"),
            ("/api/v1/users/123/", "/api/v1/users/123"),
            ("/", "/"),
            ("", "/"),
        ]

        for input_path, expected in test_cases:
            result = sanitize_path(input_path)
            assert result == expected, f"Failed for input: {input_path}"
