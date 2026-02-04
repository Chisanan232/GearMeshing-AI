"""I/O models package for GearMeshing-AI project.

This package contains reusable Pydantic models for request and response
data structures used across the entire project, along with utility functions
for working with these models.
"""

from .common import (
    ApiInfoContent,
    ApiInfoResponseType,
    BaseResponseModel,
    ClientInfoContent,
    ClientInfoResponseType,
    ErrorContent,
    ErrorResponseType,
    # Global response models
    GlobalResponse,
    # Type aliases for common response types
    GlobalResponseType,
    HealthResponseType,
    # Status enums for type safety
    HealthStatus,
    # Content models for different scenarios
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
from .utils import (
    create_api_info_response,
    create_error_response,
    # Global response utility functions
    create_global_response,
    create_health_response,
    create_liveness_response,
    create_readiness_response,
    create_simple_health_response,
    create_success_response,
    create_welcome_response,
    # General utility functions
    get_client_info,
    sanitize_path,
)

__all__ = [
    "ApiInfoContent",
    "ApiInfoResponseType",
    "BaseResponseModel",
    "ClientInfoContent",
    "ClientInfoResponseType",
    "ErrorContent",
    "ErrorResponseType",
    "GlobalResponse",
    "GlobalResponseType",
    "HealthResponseType",
    "HealthStatus",
    "HealthStatusContent",
    "LivenessContent",
    "LivenessResponseType",
    "LivenessStatus",
    "ReadinessContent",
    "ReadinessResponseType",
    "ReadinessStatus",
    "SimpleHealthContent",
    "SimpleHealthResponseType",
    "SimpleHealthStatus",
    "WelcomeContent",
    "WelcomeResponseType",
    "create_api_info_response",
    "create_error_response",
    "create_global_response",
    "create_health_response",
    "create_liveness_response",
    "create_readiness_response",
    "create_simple_health_response",
    "create_success_response",
    "create_welcome_response",
    "get_client_info",
    "sanitize_path",
]
