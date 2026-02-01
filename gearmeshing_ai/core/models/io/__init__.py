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
]