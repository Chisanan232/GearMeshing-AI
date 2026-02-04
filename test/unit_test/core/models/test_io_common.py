"""Tests for the GearMeshing-AI core I/O models.

This module contains comprehensive tests for Pydantic models,
enums, and type aliases used across the project.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from gearmeshing_ai.core.models.io.common import (
    ApiInfoContent,
    ApiInfoResponseType,
    # Base models
    BaseResponseModel,
    ClientInfoContent,
    ClientInfoResponseType,
    ErrorContent,
    ErrorResponseType,
    GlobalResponse,
    # Type aliases
    GlobalResponseType,
    HealthResponseType,
    # Enums
    HealthStatus,
    # Content models
    HealthStatusContent,
    LivenessContent,
    LivenessResponseType,
    LivenessStatus,
    ReadinessContent,
    ReadinessResponseType,
    ReadinessStatus,
    SimpleHealthContent,
    SimpleHealthResponseType,
    SimpleHealthStatus,
    WelcomeContent,
    WelcomeResponseType,
)


class TestStatusEnums:
    """Test cases for status enumeration classes."""

    def test_health_status_enum_values(self) -> None:
        """Test HealthStatus enum values."""
        assert str(HealthStatus.HEALTHY) == "healthy"
        assert str(HealthStatus.UNHEALTHY) == "unhealthy"
        assert str(HealthStatus.DEGRADED) == "degraded"

        # Test all values are strings
        for status in HealthStatus:
            assert isinstance(status.value, str)

    def test_health_status_enum_iteration(self) -> None:
        """Test HealthStatus enum iteration."""
        statuses = list(HealthStatus)
        expected = [HealthStatus.HEALTHY, HealthStatus.UNHEALTHY, HealthStatus.DEGRADED]

        assert len(statuses) == 3
        for expected_status in expected:
            assert expected_status in statuses

    def test_simple_health_status_enum_values(self) -> None:
        """Test SimpleHealthStatus enum values."""
        assert str(SimpleHealthStatus.OK) == "ok"
        assert str(SimpleHealthStatus.ERROR) == "error"

        # Test all values are strings
        for status in SimpleHealthStatus:
            assert isinstance(status.value, str)

    def test_readiness_status_enum_values(self) -> None:
        """Test ReadinessStatus enum values."""
        assert str(ReadinessStatus.READY) == "ready"
        assert str(ReadinessStatus.NOT_READY) == "not_ready"

        # Test all values are strings
        for status in ReadinessStatus:
            assert isinstance(status.value, str)

    def test_liveness_status_enum_values(self) -> None:
        """Test LivenessStatus enum values."""
        assert str(LivenessStatus.ALIVE) == "alive"

        # Test all values are strings
        for status in LivenessStatus:
            assert isinstance(status.value, str)

    def test_enum_string_representation(self) -> None:
        """Test enum string representation."""
        assert str(HealthStatus.HEALTHY) == "healthy"
        assert str(SimpleHealthStatus.OK) == "ok"
        assert str(ReadinessStatus.READY) == "ready"
        assert str(LivenessStatus.ALIVE) == "alive"

    def test_enum_equality(self) -> None:
        """Test enum equality comparisons."""
        assert str(HealthStatus.HEALTHY) == "healthy"
        assert HealthStatus.HEALTHY == HealthStatus.HEALTHY
        # Different enum values are never equal - using type: ignore for comparison
        assert HealthStatus.HEALTHY != HealthStatus.UNHEALTHY  # type: ignore
        assert str(HealthStatus.HEALTHY) != "invalid"

    def test_enum_hashability(self) -> None:
        """Test that enums are hashable (can be used as dict keys)."""
        status_dict = {HealthStatus.HEALTHY: "All good", HealthStatus.UNHEALTHY: "Something wrong"}

        assert status_dict[HealthStatus.HEALTHY] == "All good"
        assert status_dict[HealthStatus.UNHEALTHY] == "Something wrong"


class TestBaseResponseModel:
    """Test cases for BaseResponseModel class."""

    def test_base_response_model_timestamp_generation(self) -> None:
        """Test that timestamp is automatically generated."""
        model = BaseResponseModel()

        assert isinstance(model.timestamp, datetime)
        assert model.timestamp <= datetime.now(UTC)

    def test_base_response_model_custom_timestamp(self) -> None:
        """Test BaseResponseModel with custom timestamp."""
        custom_time = datetime(2023, 1, 1, 12, 0, 0)
        model = BaseResponseModel(timestamp=custom_time)

        assert model.timestamp == custom_time

    def test_base_response_model_json_serialization(self) -> None:
        """Test BaseResponseModel JSON serialization."""
        model = BaseResponseModel()

        json_data = model.model_dump_json()
        assert "timestamp" in json_data

        # Should be valid JSON
        import json

        parsed = json.loads(json_data)
        assert "timestamp" in parsed

    def test_base_response_model_datetime_encoding(self) -> None:
        """Test datetime encoding in JSON."""
        custom_time = datetime(2023, 1, 1, 12, 0, 0)
        model = BaseResponseModel(timestamp=custom_time)

        json_data = model.model_dump()
        assert "timestamp" in json_data
        # Timestamp should be encoded as ISO string
        assert isinstance(json_data["timestamp"], str)

    def test_base_response_model_config(self) -> None:
        """Test BaseResponseModel configuration."""
        # Test that model has correct configuration
        model = BaseResponseModel()

        # Test populate_by_name
        model_with_alias = BaseResponseModel(**{"timestamp": datetime.now(UTC)})
        assert model_with_alias.timestamp is not None

        # Test str_strip_whitespace (if applicable)
        # This would be tested with string fields in subclasses


class TestGlobalResponse:
    """Test cases for GlobalResponse generic class."""

    def test_global_response_basic_creation(self) -> None:
        """Test basic GlobalResponse creation."""
        response: GlobalResponse[dict[str, str]] = GlobalResponse(success=True, message="Test successful", content={"data": "test"})

        assert response.success is True
        assert response.message == "Test successful"
        assert response.content == {"data": "test"}
        assert isinstance(response.timestamp, datetime)

    def test_global_response_with_none_content(self) -> None:
        """Test GlobalResponse with None content."""
        response: GlobalResponse[None] = GlobalResponse(success=False, message="Test failed")

        assert response.success is False
        assert response.message == "Test failed"
        assert response.content is None

    def test_global_response_with_different_content_types(self) -> None:
        """Test GlobalResponse with different content types."""
        # String content
        response1: GlobalResponse[str] = GlobalResponse(success=True, message="String content", content="test string")
        assert response1.content == "test string"

        # Dict content
        response2: GlobalResponse[dict[str, str]] = GlobalResponse(success=True, message="Dict content", content={"key": "value"})
        assert response2.content == {"key": "value"}

        # List content
        response3: GlobalResponse[list[int]] = GlobalResponse(success=True, message="List content", content=[1, 2, 3])
        assert response3.content == [1, 2, 3]

    def test_global_response_validation(self) -> None:
        """Test GlobalResponse field validation."""
        # Test with invalid success type
        with pytest.raises(ValidationError):
            GlobalResponse(
                success="not_boolean",  # Should be boolean
                message="Test",
            )

        # Test with invalid message type
        with pytest.raises(ValidationError):
            GlobalResponse(
                success=True,
                message=123,  # Should be string
            )

    def test_global_response_generic_type(self) -> None:
        """Test GlobalResponse generic type behavior."""
        # Test with specific type
        dict_response: GlobalResponseType[dict[str, str]] = GlobalResponse(
            success=True, message="Dict response", content={"key": "value"}
        )

        assert isinstance(dict_response.content, dict)
        assert dict_response.content["key"] == "value"

    def test_global_response_serialization(self) -> None:
        """Test GlobalResponse serialization."""
        response: GlobalResponse[dict[str, str]] = GlobalResponse(success=True, message="Test response", content={"data": "test"})

        # Test dict serialization
        data = response.model_dump()
        assert data["success"] is True
        assert data["message"] == "Test response"
        assert data["content"] == {"data": "test"}
        assert "timestamp" in data

        # Test JSON serialization
        json_data = response.model_dump_json()
        assert "success" in json_data
        assert "message" in json_data
        assert "content" in json_data


class TestContentModels:
    """Test cases for content model classes."""

    def test_health_status_content_creation(self) -> None:
        """Test HealthStatusContent creation."""
        content = HealthStatusContent(
            status=HealthStatus.HEALTHY, checkers={"database": "ok"}, details={"version": "1.0.0"}
        )

        assert content.status == HealthStatus.HEALTHY
        assert content.checkers == {"database": "ok"}
        assert content.details == {"version": "1.0.0"}

    def test_health_status_content_defaults(self) -> None:
        """Test HealthStatusContent with default values."""
        content = HealthStatusContent(status=HealthStatus.HEALTHY)

        assert content.status == HealthStatus.HEALTHY
        assert content.checkers is None
        assert content.details is None

    def test_health_status_content_validation(self) -> None:
        """Test HealthStatusContent validation."""
        # Test with invalid status
        with pytest.raises(ValidationError):
            HealthStatusContent(status="invalid_status")

        # Test with valid status as string
        content = HealthStatusContent(status="healthy")
        assert content.status == HealthStatus.HEALTHY

    def test_simple_health_content_creation(self) -> None:
        """Test SimpleHealthContent creation."""
        content = SimpleHealthContent(status=SimpleHealthStatus.OK)

        assert content.status == SimpleHealthStatus.OK

    def test_readiness_content_creation(self) -> None:
        """Test ReadinessContent creation."""
        content = ReadinessContent(status=ReadinessStatus.READY)

        assert content.status == ReadinessStatus.READY

    def test_liveness_content_creation(self) -> None:
        """Test LivenessContent creation."""
        content = LivenessContent(status=LivenessStatus.ALIVE)

        assert content.status == LivenessStatus.ALIVE

    def test_welcome_content_creation(self) -> None:
        """Test WelcomeContent creation."""
        content = WelcomeContent(message="Welcome to API", version="1.0.0", docs="/docs", health="/health")

        assert content.message == "Welcome to API"
        assert content.version == "1.0.0"
        assert content.docs == "/docs"
        assert content.health == "/health"

    def test_welcome_content_validation(self) -> None:
        """Test WelcomeContent validation."""
        # Test with missing required fields
        with pytest.raises(ValidationError):
            WelcomeContent(message="Welcome")  # Missing other required fields

    def test_api_info_content_creation(self) -> None:
        """Test ApiInfoContent creation."""
        content = ApiInfoContent(
            name="Test API",
            version="1.0.0",
            description="Test API description",
            endpoints=["/health", "/info"],
            documentation={"swagger": "/docs", "redoc": "/redoc"},
        )

        assert content.name == "Test API"
        assert content.version == "1.0.0"
        assert content.description == "Test API description"
        assert content.endpoints == ["/health", "/info"]
        assert content.documentation == {"swagger": "/docs", "redoc": "/redoc"}

    def test_api_info_content_validation(self) -> None:
        """Test ApiInfoContent validation."""
        # Test with invalid endpoints type
        with pytest.raises(ValidationError):
            ApiInfoContent(
                name="Test API",
                version="1.0.0",
                description="Test",
                endpoints="not_a_list",  # Should be list
                documentation={},
            )

    def test_client_info_content_creation(self) -> None:
        """Test ClientInfoContent creation."""
        content = ClientInfoContent(
            client_ip="192.168.1.1", user_agent="Mozilla/5.0...", method="GET", url="http://example.com/test"
        )

        assert content.client_ip == "192.168.1.1"
        assert content.user_agent == "Mozilla/5.0..."
        assert content.method == "GET"
        assert content.url == "http://example.com/test"

    def test_error_content_creation(self) -> None:
        """Test ErrorContent creation."""
        content = ErrorContent(error_code="VALIDATION_ERROR", details={"field": "invalid"}, stack_trace="Traceback...")

        assert content.error_code == "VALIDATION_ERROR"
        assert content.details == {"field": "invalid"}
        assert content.stack_trace == "Traceback..."

    def test_error_content_defaults(self) -> None:
        """Test ErrorContent with default values."""
        content = ErrorContent()

        assert content.error_code is None
        assert content.details is None
        assert content.stack_trace is None


class TestTypeAliases:
    """Test cases for type aliases."""

    def test_health_response_type(self) -> None:
        """Test HealthResponseType type alias."""
        response: HealthResponseType = GlobalResponse(
            success=True,
            message="Health check",
            content=HealthStatusContent(status=HealthStatus.HEALTHY, details={"test": "ok"}),
        )

        assert response.success is True
        assert isinstance(response.content, HealthStatusContent)
        assert response.content.status == HealthStatus.HEALTHY

    def test_simple_health_response_type(self) -> None:
        """Test SimpleHealthResponseType type alias."""
        response: SimpleHealthResponseType = GlobalResponse(
            success=True, message="Simple health", content=SimpleHealthContent(status=SimpleHealthStatus.OK)
        )

        assert isinstance(response.content, SimpleHealthContent)
        assert response.content.status == SimpleHealthStatus.OK

    def test_readiness_response_type(self) -> None:
        """Test ReadinessResponseType type alias."""
        response: ReadinessResponseType = GlobalResponse(
            success=True, message="Readiness check", content=ReadinessContent(status=ReadinessStatus.READY)
        )

        assert isinstance(response.content, ReadinessContent)
        assert response.content.status == ReadinessStatus.READY

    def test_liveness_response_type(self) -> None:
        """Test LivenessResponseType type alias."""
        response: LivenessResponseType = GlobalResponse(
            success=True, message="Liveness check", content=LivenessContent(status=LivenessStatus.ALIVE)
        )

        assert isinstance(response.content, LivenessContent)
        assert response.content.status == LivenessStatus.ALIVE

    def test_welcome_response_type(self) -> None:
        """Test WelcomeResponseType type alias."""
        response: WelcomeResponseType = GlobalResponse(
            success=True,
            message="Welcome",
            content=WelcomeContent(message="Welcome to API", version="1.0.0", docs="/docs", health="/health"),
        )

        assert isinstance(response.content, WelcomeContent)
        assert response.content.message == "Welcome to API"

    def test_api_info_response_type(self) -> None:
        """Test ApiInfoResponseType type alias."""
        response: ApiInfoResponseType = GlobalResponse(
            success=True,
            message="API info",
            content=ApiInfoContent(
                name="Test API",
                version="1.0.0",
                description="Test API",
                endpoints=["/health"],
                documentation={"swagger": "/docs"},
            ),
        )

        assert isinstance(response.content, ApiInfoContent)
        assert response.content.name == "Test API"

    def test_client_info_response_type(self) -> None:
        """Test ClientInfoResponseType type alias."""
        response: ClientInfoResponseType = GlobalResponse(
            success=True,
            message="Client info",
            content=ClientInfoContent(
                client_ip="127.0.0.1", user_agent="Test Agent", method="POST", url="http://test.com"
            ),
        )

        assert isinstance(response.content, ClientInfoContent)
        assert response.content.client_ip == "127.0.0.1"

    def test_error_response_type(self) -> None:
        """Test ErrorResponseType type alias."""
        response: ErrorResponseType = GlobalResponse(
            success=False,
            message="Error occurred",
            content=ErrorContent(error_code="TEST_ERROR", details={"error": "test error"}),
        )

        assert isinstance(response.content, ErrorContent)
        assert response.content.error_code == "TEST_ERROR"


class TestModelInheritance:
    """Test cases for model inheritance and relationships."""

    def test_content_models_inherit_from_basemodel(self) -> None:
        """Test that all content models inherit from BaseModel."""
        content_models = [
            HealthStatusContent,
            SimpleHealthContent,
            ReadinessContent,
            LivenessContent,
            WelcomeContent,
            ApiInfoContent,
            ClientInfoContent,
            ErrorContent,
        ]

        for model_class in content_models:
            # Check that it's a Pydantic BaseModel
            assert hasattr(model_class, "model_validate")
            assert hasattr(model_class, "model_dump")

    def test_global_response_inherits_from_base_response_model(self) -> None:
        """Test GlobalResponse inheritance."""
        response: GlobalResponse[None] = GlobalResponse(success=True, message="Test")

        # Should have timestamp from BaseResponseModel
        assert hasattr(response, "timestamp")
        assert isinstance(response.timestamp, datetime)

    def test_model_schema_generation(self) -> None:
        """Test that models generate valid schemas."""
        # Test GlobalResponse schema
        schema = GlobalResponse.model_json_schema()
        assert "properties" in schema
        assert "success" in schema["properties"]
        assert "message" in schema["properties"]
        assert "content" in schema["properties"]
        assert "timestamp" in schema["properties"]

    def test_model_copy(self) -> None:
        """Test model copying functionality."""
        original: GlobalResponse[dict[str, str]] = GlobalResponse(success=True, message="Test", content={"data": "test"})

        copied = original.model_copy()

        assert copied.success == original.success
        assert copied.message == original.message
        assert copied.content == original.content
        assert copied.timestamp == original.timestamp

    def test_model_equality(self) -> None:
        """Test model equality comparison."""
        timestamp = datetime.now(UTC)
        response1: GlobalResponse[dict[str, str]] = GlobalResponse(success=True, message="Test", content={"data": "test"}, timestamp=timestamp)

        response2: GlobalResponse[dict[str, str]] = GlobalResponse(success=True, message="Test", content={"data": "test"}, timestamp=timestamp)

        # Models with same data should be equal
        assert response1.model_dump() == response2.model_dump()


class TestModelValidationEdgeCases:
    """Test cases for edge cases in model validation."""

    def test_global_response_with_empty_content(self) -> None:
        """Test GlobalResponse with empty content."""
        response: GlobalResponse[dict[str, str]] = GlobalResponse(success=True, message="Test", content={})

        assert response.content == {}

    def test_content_models_with_extra_fields(self) -> None:
        """Test content models with extra fields (should be rejected)."""
        # Test with extra fields (should fail validation)
        with pytest.raises(ValidationError):
            HealthStatusContent(status=HealthStatus.HEALTHY, extra_field="not_allowed")

    def test_enum_validation_with_invalid_values(self) -> None:
        """Test enum validation with invalid string values."""
        # Test that invalid enum values are rejected
        with pytest.raises(ValidationError):
            HealthStatusContent(status="invalid_status_value")

    def test_datetime_field_validation(self) -> None:
        """Test datetime field validation."""
        # Test with invalid datetime
        with pytest.raises(ValidationError):
            BaseResponseModel(timestamp="not_a_datetime")

    def test_nested_model_validation(self) -> None:
        """Test validation of nested models."""
        # Test GlobalResponse with invalid nested content
        with pytest.raises(ValidationError):
            GlobalResponse(
                success=True,
                message="Test",
                content=HealthStatusContent(
                    status="invalid_status"  # Should be valid enum
                ),
            )

    def test_large_data_handling(self) -> None:
        """Test handling of large data in content."""
        large_dict = {f"key_{i}": f"value_{i}" for i in range(1000)}

        response: GlobalResponse[dict[str, str]] = GlobalResponse(success=True, message="Large data test", content=large_dict)

        # MyPy: content is guaranteed to be dict[str, str] here
        content: dict[str, str] = response.content  # type: ignore

        assert len(content) == 1000
        assert content["key_0"] == "value_0"
        assert content["key_999"] == "value_999"


class TestModelSerialization:
    """Test cases for model serialization and deserialization."""

    def test_json_roundtrip(self) -> None:
        """Test JSON serialization and deserialization roundtrip."""
        original: GlobalResponse[HealthStatusContent] = GlobalResponse(
            success=True,
            message="Test message",
            content=HealthStatusContent(status=HealthStatus.HEALTHY, details={"test": "data"}),
        )

        # Serialize to JSON
        json_str = original.model_dump_json()

        # Deserialize from JSON using the specific response type
        restored = HealthResponseType.model_validate_json(json_str)

        assert restored.success == original.success
        assert restored.message == original.message
        # Content should never be None in this test
        assert restored.content is not None
        assert restored.content.status == original.content.status  # type: ignore
        assert restored.content.details == original.content.details  # type: ignore

    def test_dict_roundtrip(self) -> None:
        """Test dict serialization and deserialization roundtrip."""
        original: GlobalResponse[WelcomeContent] = GlobalResponse(
            success=True,
            message="Test message",
            content=WelcomeContent(message="Welcome", version="1.0.0", docs="/docs", health="/health"),
        )

        # Serialize to dict
        data_dict = original.model_dump()

        # Deserialize from dict using the specific response type
        restored = WelcomeResponseType.model_validate(data_dict)

        assert restored.success == original.success
        assert restored.message == original.message
        # Content should never be None in this test
        assert restored.content is not None
        assert restored.content.message == original.content.message  # type: ignore
        assert restored.content.version == original.content.version  # type: ignore

    def test_exclude_none_values(self) -> None:
        """Test serialization with None values excluded."""
        response: GlobalResponse[None] = GlobalResponse(success=True, message="Test", content=None)

        # Test with exclude_none
        data = response.model_dump(exclude_none=True)

        assert "content" not in data
        assert "success" in data
        assert "message" in data
        assert "timestamp" in data

    def test_serialize_only_specific_fields(self) -> None:
        """Test serializing only specific fields."""
        response: GlobalResponse[dict[str, str]] = GlobalResponse(success=True, message="Test", content={"data": "test"})

        # Test with include parameter
        data = response.model_dump(include={"success", "message"})

        assert "success" in data
        assert "message" in data
        assert "content" not in data
        assert "timestamp" not in data

    def test_exclude_specific_fields(self) -> None:
        """Test excluding specific fields from serialization."""
        response: GlobalResponse[dict[str, str]] = GlobalResponse(success=True, message="Test", content={"data": "test"})

        # Test with exclude parameter
        data = response.model_dump(exclude={"timestamp"})

        assert "success" in data
        assert "message" in data
        assert "content" in data
        assert "timestamp" not in data
