"""Utility functions for I/O models.

This module provides utility functions that work with the I/O models,
creating a cohesive package for data handling and validation.
"""

from typing import Any, Dict, Optional

from .common import (
    GlobalResponse, 
    ErrorContent,
    WelcomeContent,
    ApiInfoContent,
    HealthStatusContent,
    SimpleHealthContent,
    ReadinessContent,
    LivenessContent,
    ClientInfoContent,
    HealthStatus,
    SimpleHealthStatus,
    ReadinessStatus,
    LivenessStatus
)


def create_global_response(
    success: bool, 
    message: str, 
    content: Optional[Any] = None
) -> GlobalResponse:
    """Create a standardized global response.
    
    This utility function creates consistent responses using the
    global response structure for all API endpoints.
    
    Args:
        success: Whether the operation was successful
        message: Human-readable message
        content: Response content (varies by scenario)
        
    Returns:
        GlobalResponse: Standardized global response
    """
    return GlobalResponse(
        success=success,
        message=message,
        content=content
    )


def create_success_response(content: Any, message: str = "Success") -> GlobalResponse:
    """Create a standardized success response.
    
    This utility function creates consistent success responses
    using the global response structure.
    
    Args:
        content: Response content
        message: Success message
        
    Returns:
        GlobalResponse: Standardized success response
    """
    return GlobalResponse(
        success=True,
        message=message,
        content=content
    )


def create_error_response(
    message: str, 
    status_code: int = 500, 
    details: Optional[Dict[str, Any]] = None,
    error_code: Optional[str] = None
) -> GlobalResponse:
    """Create a standardized error response.
    
    This utility function creates consistent error responses
    using the global response structure.
    
    Args:
        message: Error message
        status_code: HTTP status code
        details: Additional error details
        error_code: Machine-readable error code
        
    Returns:
        GlobalResponse: Standardized error response
    """
    error_content = ErrorContent(
        error_code=error_code,
        details=details
    )
    
    return GlobalResponse(
        success=False,
        message=message,
        content=error_content
    )


def create_welcome_response(
    message: str,
    version: str,
    docs: str,
    health: str
) -> GlobalResponse:
    """Create a standardized welcome response.
    
    Args:
        message: Welcome message
        version: API version
        docs: Documentation URL
        health: Health check URL
        
    Returns:
        GlobalResponse: Welcome response with content
    """
    welcome_content = WelcomeContent(
        message=message,
        version=version,
        docs=docs,
        health=health
    )
    
    return GlobalResponse(
        success=True,
        message="Welcome to GearMeshing-AI API",
        content=welcome_content
    )


def create_api_info_response(
    name: str,
    version: str,
    description: str,
    endpoints: list,
    documentation: dict
) -> GlobalResponse:
    """Create a standardized API info response.
    
    Args:
        name: API name
        version: API version
        description: API description
        endpoints: List of available endpoints
        documentation: Documentation URLs
        
    Returns:
        GlobalResponse: API info response with content
    """
    api_info_content = ApiInfoContent(
        name=name,
        version=version,
        description=description,
        endpoints=endpoints,
        documentation=documentation
    )
    
    return GlobalResponse(
        success=True,
        message="API information retrieved successfully",
        content=api_info_content
    )


def create_health_response(
    status: HealthStatus,
    checkers: Optional[Dict[str, Any]] = None,
    details: Optional[Dict[str, Any]] = None
) -> GlobalResponse:
    """Create a standardized health check response.
    
    Args:
        status: Health status (HealthStatus enum)
        checkers: Individual checker results
        details: Additional health details
        
    Returns:
        GlobalResponse: Health check response with content
    """
    health_content = HealthStatusContent(
        status=status,
        checkers=checkers,
        details=details
    )
    
    message = "Service is healthy" if status == HealthStatus.HEALTHY else f"Service status: {status.value}"
    
    return GlobalResponse(
        success=status != HealthStatus.UNHEALTHY,
        message=message,
        content=health_content
    )


def create_simple_health_response(status: SimpleHealthStatus) -> GlobalResponse:
    """Create a standardized simple health response.
    
    Args:
        status: Simple health status (SimpleHealthStatus enum)
        
    Returns:
        GlobalResponse: Simple health response with content
    """
    simple_health_content = SimpleHealthContent(status=status)
    
    return GlobalResponse(
        success=status == SimpleHealthStatus.OK,
        message="Health check completed",
        content=simple_health_content
    )


def create_readiness_response(status: ReadinessStatus) -> GlobalResponse:
    """Create a standardized readiness response.
    
    Args:
        status: Readiness status (ReadinessStatus enum)
        
    Returns:
        GlobalResponse: Readiness response with content
    """
    readiness_content = ReadinessContent(status=status)
    
    return GlobalResponse(
        success=status == ReadinessStatus.READY,
        message="Readiness check completed",
        content=readiness_content
    )


def create_liveness_response(status: LivenessStatus = LivenessStatus.ALIVE) -> GlobalResponse:
    """Create a standardized liveness response.
    
    Args:
        status: Liveness status (LivenessStatus enum)
        
    Returns:
        GlobalResponse: Liveness response with content
    """
    liveness_content = LivenessContent(status=status)
    
    return GlobalResponse(
        success=True,
        message="Liveness check completed",
        content=liveness_content
    )


def get_client_info(request) -> ClientInfoContent:
    """Extract client information from request.
    
    This utility function extracts relevant client information
    for logging and debugging purposes using the common I/O models.
    
    Args:
        request: FastAPI request object
        
    Returns:
        ClientInfoContent: Client information
    """
    return ClientInfoContent(
        client_ip=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", "unknown"),
        method=request.method,
        url=str(request.url)
    )


def sanitize_path(path: str) -> str:
    """Sanitize and normalize a path string.
    
    This utility function ensures paths are properly formatted
    and safe for internal use.
    
    Args:
        path: Path string to sanitize
        
    Returns:
        Sanitized path string
    """
    # Remove leading/trailing slashes and normalize
    return path.strip("/").replace("//", "/")


