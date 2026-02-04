"""Health check router for the GearMeshing-AI REST API.

This module provides FastAPI router endpoints for health checking
using Pythonic FastAPI decorators with dependency injection.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from gearmeshing_ai.core.models.io import (
    HealthResponseType,
    HealthStatus,
    LivenessResponseType,
    LivenessStatus,
    ReadinessResponseType,
    ReadinessStatus,
    SimpleHealthResponseType,
    SimpleHealthStatus,
    create_error_response,
    create_health_response,
    create_liveness_response,
    create_readiness_response,
    create_simple_health_response,
)

from ..dependencies import get_health_service
from ..service.health import HealthCheckService

# Global router instance following FastAPI best practices
router = APIRouter(prefix="/health", tags=["health"])


@router.get(  # type: ignore
    "/",
    summary="Comprehensive health check",
    description="Check health of all system components",
    response_model=HealthResponseType,
)
async def health_check(service: HealthCheckService = Depends(get_health_service)) -> HealthResponseType:
    """Perform comprehensive health check.

    This endpoint checks all registered health checkers
    and returns detailed status information using the global response structure.

    Args:
        service: Health check service (injected via dependency injection)

    Returns:
        HealthResponseType: Detailed health status with global structure

    Raises:
        HTTPException: If health check fails

    """
    try:
        health_result = service.check_all_health()

        # Return appropriate response based on overall health
        if health_result["status"] == "healthy":
            return create_health_response(
                status=HealthStatus.HEALTHY,
                checkers=health_result["checkers"],
                details={"timestamp": health_result["timestamp"]},
            )
        if health_result["status"] == "degraded":
            # Degraded but still functional
            return create_health_response(
                status=HealthStatus.DEGRADED,
                checkers=health_result["checkers"],
                details={"timestamp": health_result["timestamp"]},
            )
        # Unhealthy - return 503
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=create_error_response(
                message="Service is unhealthy", status_code=status.HTTP_503_SERVICE_UNAVAILABLE, details=health_result
            ).model_dump(),
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Handle unexpected exceptions with consistent error response
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=create_error_response(
                message=f"Health check failed: {e!s}", status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            ).model_dump(),
        )


@router.get(  # type: ignore
    "/simple",
    summary="Simple health check",
    description="Basic health check for load balancers",
    response_model=SimpleHealthResponseType,
)
async def simple_health_check(service: HealthCheckService = Depends(get_health_service)) -> SimpleHealthResponseType:
    """Perform simple health check.

    This endpoint provides a minimal health check suitable
    for load balancers and monitoring systems using the global response structure.

    Args:
        service: Health check service (injected via dependency injection)

    Returns:
        SimpleHealthResponseType: Simple health status with global structure

    Raises:
        HTTPException: If health check fails

    """
    try:
        # Quick check - just verify the service can run
        result = service.check_all_health()

        if result["status"] == "healthy":
            return create_simple_health_response(status=SimpleHealthStatus.OK)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=create_error_response(
                message="Service is not healthy", status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            ).model_dump(),
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Handle unexpected exceptions with consistent error response
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=create_error_response(
                message=f"Health check failed: {e!s}", status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            ).model_dump(),
        )


@router.get(  # type: ignore
    "/ready",
    summary="Readiness check",
    description="Check if application is ready to serve traffic",
    response_model=ReadinessResponseType,
)
async def readiness_check(service: HealthCheckService = Depends(get_health_service)) -> ReadinessResponseType:
    """Check if application is ready to serve traffic.

    This endpoint checks if all critical components are ready
    to accept requests. It's used by Kubernetes and other
    orchestration systems using the global response structure.

    Args:
        service: Health check service (injected via dependency injection)

    Returns:
        ReadinessResponseType: Readiness status with global structure

    Raises:
        HTTPException: If application is not ready

    """
    try:
        health_result = service.check_all_health()

        # Consider application ready if not unhealthy
        if health_result["status"] != "unhealthy":
            return create_readiness_response(status=ReadinessStatus.READY)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=create_error_response(
                message="Application is not ready",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                details={"reason": "Some components are unhealthy"},
            ).model_dump(),
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Handle unexpected exceptions with consistent error response
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=create_error_response(
                message=f"Readiness check failed: {e!s}", status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            ).model_dump(),
        )


@router.get(  # type: ignore
    "/live", summary="Liveness check", description="Check if application is alive", response_model=LivenessResponseType
)
async def liveness_check() -> LivenessResponseType:
    """Check if application is alive.

    This endpoint provides a basic liveness check to determine
    if the application process is running and responsive
    using the global response structure.

    Returns:
        LivenessResponseType: Liveness status with global structure

    """
    # Liveness check should be very simple - just check if we can respond
    return create_liveness_response(status=LivenessStatus.ALIVE)


def get_health_router() -> APIRouter:
    """Get the health router instance.

    This function returns the global router instance for consistency
    with other routers in the application.

    Returns:
        APIRouter: Health check router instance

    """
    return router
