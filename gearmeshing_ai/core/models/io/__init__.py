"""I/O models package for GearMeshing-AI project.

This package contains reusable Pydantic models for request and response
data structures used across the entire project, along with utility functions
for working with these models.
"""

from .common import (
    # Global response models
    GlobalResponse,
    BaseResponseModel,
    
    # Status enums for type safety
    HealthStatus,
    SimpleHealthStatus,
    ReadinessStatus,
    LivenessStatus,
    
    # Content models for different scenarios
    HealthStatusContent,
    SimpleHealthContent,
    ReadinessContent,
    LivenessContent,
    WelcomeContent,
    ApiInfoContent,
    ClientInfoContent,
    ErrorContent,
    
    # Type aliases for common response types
    GlobalResponseType,
    HealthResponseType,
    SimpleHealthResponseType,
    ReadinessResponseType,
    LivenessResponseType,
    WelcomeResponseType,
    ApiInfoResponseType,
    ClientInfoResponseType,
    ErrorResponseType,
)

from .utils import (
    # Global response utility functions
    create_global_response,
    create_success_response,
    create_error_response,
    create_welcome_response,
    create_api_info_response,
    create_health_response,
    create_simple_health_response,
    create_readiness_response,
    create_liveness_response,

    # General utility functions
    get_client_info,
    sanitize_path,
)

__all__ = [
    # Global response models
    "GlobalResponse",
    "BaseResponseModel",
    
    # Status enums for type safety
    "HealthStatus",
    "SimpleHealthStatus",
    "ReadinessStatus",
    "LivenessStatus",
    
    # Content models
    "HealthStatusContent",
    "SimpleHealthContent",
    "ReadinessContent",
    "LivenessContent",
    "WelcomeContent",
    "ApiInfoContent",
    "ClientInfoContent",
    "ErrorContent",
    
    # Type aliases
    "GlobalResponseType",
    "HealthResponseType",
    "SimpleHealthResponseType",
    "ReadinessResponseType",
    "LivenessResponseType",
    "WelcomeResponseType",
    "ApiInfoResponseType",
    "ClientInfoResponseType",
    "ErrorResponseType",

    # Global response utility functions
    "create_global_response",
    "create_success_response",
    "create_error_response",
    "create_welcome_response",
    "create_api_info_response",
    "create_health_response",
    "create_simple_health_response",
    "create_readiness_response",
    "create_liveness_response",

    # General utility functions
    "get_client_info",
    "sanitize_path",
]