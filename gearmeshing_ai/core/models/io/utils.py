"""Utility functions for I/O models.

This module provides utility functions that work with the I/O models,
creating a cohesive package for data handling and validation.
"""

from datetime import datetime
from typing import Any

from .common import (
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


def create_global_response(
    success: bool = True,
    message: str = "Operation completed",
    content: Any | None = None,
    timestamp: datetime | None = None,
) -> GlobalResponse:
    """Create a standardized global response.

    This utility function creates consistent responses using the
    global response structure for all API endpoints.

    Args:
        success: Whether the operation was successful
        message: Human-readable message
        content: Response content (varies by scenario)
        timestamp: Custom timestamp for the response

    Returns:
        GlobalResponse: Standardized global response

    """
    kwargs = {"success": success, "message": message, "content": content}
    if timestamp is not None:
        kwargs["timestamp"] = timestamp

    return GlobalResponse(**kwargs)


def create_success_response(message: str = "Operation successful", content: Any | None = None) -> GlobalResponse:
    """Create a standardized success response.

    This utility function creates consistent success responses
    using the global response structure.

    Args:
        message: Success message
        content: Response content

    Returns:
        GlobalResponse: Standardized success response

    """
    return GlobalResponse(success=True, message=message, content=content)


def create_error_response(
    message: str = "An error occurred",
    status_code: int = 500,
    details: dict[str, Any] | None = None,
    error_code: str | None = None,
    stack_trace: str | None = None,
) -> GlobalResponse:
    """Create a standardized error response.

    This utility function creates consistent error responses
    using the global response structure.

    Args:
        message: Error message
        status_code: HTTP status code
        details: Additional error details
        error_code: Machine-readable error code
        stack_trace: Stack trace (development only)

    Returns:
        GlobalResponse: Standardized error response

    """
    # Use status_code as error_code if not provided
    final_error_code = error_code or str(status_code)

    error_content = ErrorContent(error_code=final_error_code, details=details, stack_trace=stack_trace)

    return GlobalResponse(success=False, message=message, content=error_content)


def create_welcome_response(
    message: str = "Welcome to GearMeshing-AI API", version: str = "0.0.0", docs: str = "/docs", health: str = "/health"
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
    welcome_content = WelcomeContent(message=message, version=version, docs=docs, health=health)

    return GlobalResponse(success=True, message="Welcome to GearMeshing-AI API", content=welcome_content)


def create_api_info_response(
    name: str, version: str, description: str, endpoints: list, documentation: dict
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
        name=name, version=version, description=description, endpoints=endpoints, documentation=documentation
    )

    return GlobalResponse(success=True, message="API information retrieved successfully", content=api_info_content)


def create_health_response(
    status: HealthStatus, checkers: dict[str, Any] | None = None, details: dict[str, Any] | None = None
) -> GlobalResponse:
    """Create a standardized health check response.

    Args:
        status: Health status (HealthStatus enum)
        checkers: Individual checker results
        details: Additional health details

    Returns:
        GlobalResponse: Health check response with content

    """
    health_content = HealthStatusContent(status=status, checkers=checkers, details=details)

    message = "Service is healthy" if status == HealthStatus.HEALTHY else f"Service status: {status.value}"

    return GlobalResponse(success=status != HealthStatus.UNHEALTHY, message=message, content=health_content)


def create_simple_health_response(status: SimpleHealthStatus = SimpleHealthStatus.OK) -> GlobalResponse:
    """Create a standardized simple health response.

    Args:
        status: Simple health status (SimpleHealthStatus enum)

    Returns:
        GlobalResponse: Simple health response with content

    """
    simple_health_content = SimpleHealthContent(status=status)

    return GlobalResponse(
        success=status == SimpleHealthStatus.OK, message="Health check completed", content=simple_health_content
    )


def create_readiness_response(status: ReadinessStatus = ReadinessStatus.READY) -> GlobalResponse:
    """Create a standardized readiness response.

    Args:
        status: Readiness status (ReadinessStatus enum)

    Returns:
        GlobalResponse: Readiness response with content

    """
    readiness_content = ReadinessContent(status=status)

    return GlobalResponse(
        success=status == ReadinessStatus.READY, message="Readiness check completed", content=readiness_content
    )


def create_liveness_response(status: LivenessStatus = LivenessStatus.ALIVE) -> GlobalResponse:
    """Create a standardized liveness response.

    Args:
        status: Liveness status (LivenessStatus enum)

    Returns:
        GlobalResponse: Liveness response with content

    """
    liveness_content = LivenessContent(status=status)

    return GlobalResponse(success=True, message="Liveness check completed", content=liveness_content)


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
        client_ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        method=request.method,
        url=str(request.url),
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
    if not isinstance(path, str):
        raise TypeError(f"Path must be a string, got {type(path).__name__}")

    if path is None:
        raise TypeError("Path cannot be None")

    # Strip leading/trailing whitespace
    path = path.strip()

    # Remove query parameters and fragments
    path = path.split("?")[0].split("#")[0]

    # Strip leading/trailing slashes
    path = path.strip("/")

    # Normalize multiple slashes
    while "//" in path:
        path = path.replace("//", "/")

    # Return with leading slash
    return "/" + path if path else "/"
