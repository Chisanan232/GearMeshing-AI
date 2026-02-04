"""Common I/O data models for the GearMeshing-AI project.

This module contains reusable Pydantic models for request and response
data structures used across the entire project, providing validation,
serialization, and clear documentation.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_serializer

T = TypeVar("T")


# Status enums for type safety and maintainability
class HealthStatus(str, Enum):
    """Health status enumeration for comprehensive health checks."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"

    def __str__(self) -> str:
        return self.value


class SimpleHealthStatus(str, Enum):
    """Simple health status enumeration for basic health checks."""

    OK = "ok"
    ERROR = "error"

    def __str__(self) -> str:
        return self.value


class ReadinessStatus(str, Enum):
    """Readiness status enumeration for readiness probes."""

    READY = "ready"
    NOT_READY = "not_ready"

    def __str__(self) -> str:
        return self.value


class LivenessStatus(str, Enum):
    """Liveness status enumeration for liveness probes."""

    ALIVE = "alive"

    def __str__(self) -> str:
        return self.value


class BaseResponseModel(BaseModel):
    """Base model for all API responses.

    Provides common fields and configuration for consistent responses.
    """

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Timestamp when the response was generated"
    )

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        """Serialize datetime to ISO format string."""
        return value.isoformat()


class GlobalResponse(BaseResponseModel, Generic[T]):
    """Global unified response model for all API endpoints.

    This model provides a consistent response structure across all scenarios
    while allowing flexibility for different content types.

    Structure:
    {
        "success": boolean,
        "message": string,
        "content": T,  # Varies by scenario
        "timestamp": datetime
    }

    Examples:
    - Success: {"success": true, "message": "Operation completed", "content": {...}}
    - Error: {"success": false, "message": "Error occurred", "content": {...}}
    - Health: {"success": true, "message": "Service healthy", "content": {...}}

    """

    success: bool = Field(description="Indicates if the operation was successful")
    message: str = Field(description="Human-readable message describing the result")
    content: T | None = Field(default=None, description="Response content - varies by scenario and endpoint")


# Health check specific content models
class HealthStatusContent(BaseModel):
    """Content model for health check responses."""

    model_config = ConfigDict(extra="forbid")

    status: HealthStatus = Field(description="Health status (healthy, unhealthy, degraded)")
    checkers: dict[str, Any] | None = Field(default=None, description="Individual health checker results")
    details: dict[str, Any] | None = Field(default=None, description="Additional health check details")


class SimpleHealthContent(BaseModel):
    """Content model for simple health check responses."""

    model_config = ConfigDict(extra="forbid")

    status: SimpleHealthStatus = Field(description="Simple health status (ok, error)")


class ReadinessContent(BaseModel):
    """Content model for readiness check responses."""

    model_config = ConfigDict(extra="forbid")

    status: ReadinessStatus = Field(description="Readiness status (ready, not ready)")


class LivenessContent(BaseModel):
    """Content model for liveness check responses."""

    model_config = ConfigDict(extra="forbid")

    status: LivenessStatus = Field(description="Liveness status (alive)")


# Information content models
class WelcomeContent(BaseModel):
    """Content model for welcome endpoint responses."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(description="Welcome message")
    version: str = Field(description="API version")
    docs: str = Field(description="Documentation URL")
    health: str = Field(description="Health check URL")


class ApiInfoContent(BaseModel):
    """Content model for API information responses."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="API name")
    version: str = Field(description="API version")
    description: str = Field(description="API description")
    endpoints: list[str] = Field(description="List of available endpoints")
    documentation: dict[str, str] = Field(description="Documentation URLs")


# Client information content model
class ClientInfoContent(BaseModel):
    """Content model for client information responses."""

    model_config = ConfigDict(extra="forbid")

    client_ip: str = Field(description="Client IP address")
    user_agent: str = Field(description="Client user agent string")
    method: str = Field(description="HTTP method used")
    url: str = Field(description="Full request URL")


# Error content models
class ErrorContent(BaseModel):
    """Content model for error responses."""

    model_config = ConfigDict(extra="forbid")

    error_code: str | None = Field(default=None, description="Machine-readable error code")
    details: dict[str, Any] | None = Field(default=None, description="Additional error details")
    stack_trace: str | None = Field(default=None, description="Stack trace (development only)")


# Type aliases for common response types
GlobalResponseType = GlobalResponse[T]
HealthResponseType = GlobalResponse[HealthStatusContent]
SimpleHealthResponseType = GlobalResponse[SimpleHealthContent]
ReadinessResponseType = GlobalResponse[ReadinessContent]
LivenessResponseType = GlobalResponse[LivenessContent]
WelcomeResponseType = GlobalResponse[WelcomeContent]
ApiInfoResponseType = GlobalResponse[ApiInfoContent]
ClientInfoResponseType = GlobalResponse[ClientInfoContent]
ErrorResponseType = GlobalResponse[ErrorContent]
