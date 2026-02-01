"""Common I/O data models for the GearMeshing-AI project.

This module contains reusable Pydantic models for request and response
data structures used across the entire project, providing validation,
serialization, and clear documentation.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


T = TypeVar('T')


# Status enums for type safety and maintainability
class HealthStatus(str, Enum):
    """Health status enumeration for comprehensive health checks."""
    
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class SimpleHealthStatus(str, Enum):
    """Simple health status enumeration for basic health checks."""
    
    OK = "ok"
    ERROR = "error"


class ReadinessStatus(str, Enum):
    """Readiness status enumeration for readiness probes."""
    
    READY = "ready"
    NOT_READY = "not_ready"


class LivenessStatus(str, Enum):
    """Liveness status enumeration for liveness probes."""
    
    ALIVE = "alive"


class BaseResponseModel(BaseModel):
    """Base model for all API responses.
    
    Provides common fields and configuration for consistent responses.
    """
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        },
        populate_by_name=True,
        str_strip_whitespace=True
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the response was generated"
    )


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
    
    success: bool = Field(
        description="Indicates if the operation was successful"
    )
    message: str = Field(
        description="Human-readable message describing the result"
    )
    content: Optional[T] = Field(
        default=None,
        description="Response content - varies by scenario and endpoint"
    )




# Health check specific content models
class HealthStatusContent(BaseModel):
    """Content model for health check responses."""
    
    status: HealthStatus = Field(
        description="Health status (healthy, unhealthy, degraded)"
    )
    checkers: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Individual health checker results"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional health check details"
    )


class SimpleHealthContent(BaseModel):
    """Content model for simple health check responses."""
    
    status: SimpleHealthStatus = Field(
        description="Simple health status (ok, error)"
    )


class ReadinessContent(BaseModel):
    """Content model for readiness check responses."""
    
    status: ReadinessStatus = Field(
        description="Readiness status (ready, not ready)"
    )


class LivenessContent(BaseModel):
    """Content model for liveness check responses."""
    
    status: LivenessStatus = Field(
        description="Liveness status (alive)"
    )


# Information content models
class WelcomeContent(BaseModel):
    """Content model for welcome endpoint responses."""
    
    message: str = Field(
        description="Welcome message"
    )
    version: str = Field(
        description="API version"
    )
    docs: str = Field(
        description="Documentation URL"
    )
    health: str = Field(
        description="Health check URL"
    )


class ApiInfoContent(BaseModel):
    """Content model for API information responses."""
    
    name: str = Field(
        description="API name"
    )
    version: str = Field(
        description="API version"
    )
    description: str = Field(
        description="API description"
    )
    endpoints: List[str] = Field(
        description="List of available endpoints"
    )
    documentation: Dict[str, str] = Field(
        description="Documentation URLs"
    )


# Client information content model
class ClientInfoContent(BaseModel):
    """Content model for client information responses."""
    
    client_ip: str = Field(
        description="Client IP address"
    )
    user_agent: str = Field(
        description="Client user agent string"
    )
    method: str = Field(
        description="HTTP method used"
    )
    url: str = Field(
        description="Full request URL"
    )




# Error content models
class ErrorContent(BaseModel):
    """Content model for error responses."""
    
    error_code: Optional[str] = Field(
        default=None,
        description="Machine-readable error code"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
    stack_trace: Optional[str] = Field(
        default=None,
        description="Stack trace (development only)"
    )


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


