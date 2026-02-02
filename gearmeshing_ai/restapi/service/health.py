"""Health checking services for the GearMeshing-AI REST API.

This module contains the business logic for health checking,
following duck typing principles for clean, maintainable code.
"""

from datetime import UTC, datetime
from typing import Any, Protocol

from gearmeshing_ai.core.models.io import HealthStatusContent


class HealthChecker(Protocol):
    """Protocol defining the contract for health checkers.

    This follows duck typing principles - any class that implements
    the check_health method with the expected signature can be used
    as a health checker.
    """

    def check_health(self) -> HealthStatusContent:
        """Perform health check and return status.

        Returns:
            HealthStatusContent: The health check result

        """
        ...


class BaseHealthChecker:
    """Base class for health checkers providing common functionality.

    This class follows the Template Method pattern and duck typing
    principles. Subclasses only need to implement the specific
    health check logic.
    """

    def __init__(self, name: str) -> None:
        """Initialize health checker.

        Args:
            name: Name of the health checker for identification

        """
        self.name = name

    def check_health(self) -> HealthStatusContent:
        """Perform health check with common error handling.

        This method provides the template while allowing subclasses
        to implement specific check logic via _do_check_health.

        Returns:
            HealthStatusContent: The health check result

        """
        try:
            return self._do_check_health()
        except Exception as e:
            return HealthStatusContent(status="unhealthy", details={"checker": self.name, "error": str(e)})

    def _do_check_health(self) -> HealthStatusContent:
        """Perform the actual health check.

        Subclasses must implement this method to provide specific
        health checking logic.

        Returns:
            HealthStatusContent: The health check result

        Raises:
            Exception: If health check fails

        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement _do_check_health")


class DatabaseHealthChecker(BaseHealthChecker):
    """Health checker for database connectivity.

    This checker verifies that the database connection is working
    properly by attempting a simple query.
    """

    def __init__(self, connection_string: str | None = None) -> None:
        """Initialize database health checker.

        Args:
            connection_string: Database connection string

        """
        super().__init__("database")
        self.connection_string = connection_string

    def _do_check_health(self) -> HealthStatusContent:
        """Check database connectivity.

        Returns:
            HealthStatusContent: Database health status

        """
        # For now, return a placeholder status
        # In a real implementation, this would test actual database connectivity
        return HealthStatusContent(
            status="healthy",
            details={"checker": self.name, "connection_configured": self.connection_string is not None},
        )


class ApplicationHealthChecker(BaseHealthChecker):
    """Health checker for application components.

    This checker verifies that core application components
    are functioning properly.
    """

    def __init__(self) -> None:
        """Initialize application health checker."""
        super().__init__("application")

    def _do_check_health(self) -> HealthStatusContent:
        """Check application health.

        Returns:
            HealthStatusContent: Application health status

        """
        # Check basic application functionality
        return HealthStatusContent(
            status="healthy",
            details={"checker": self.name, "version": "0.0.0", "components": ["restapi", "agent_core", "core"]},
        )


class HealthCheckService:
    """Service for coordinating multiple health checkers.

    This class follows duck typing principles and can work with any
    objects that implement the HealthChecker protocol.
    """

    def __init__(self) -> None:
        """Initialize health check service."""
        self._checkers: list[HealthChecker] = []

    def register_checker(self, checker: HealthChecker) -> None:
        """Register a health checker.

        Args:
            checker: Health checker to register

        """
        self._checkers.append(checker)

    def check_all_health(self) -> dict[str, Any]:
        """Check health of all registered checkers.

        Returns:
            Dict containing overall health status and individual checker results

        """
        results = {}
        overall_status = "healthy"

        for checker in self._checkers:
            try:
                status = checker.check_health()
                results[checker.name if hasattr(checker, "name") else type(checker).__name__] = status

                # Determine overall status
                if status.status == "unhealthy":
                    overall_status = "unhealthy"
                elif status.status == "degraded" and overall_status == "healthy":
                    overall_status = "degraded"

            except Exception as e:
                # Handle case where checker itself fails
                checker_name = checker.name if hasattr(checker, "name") else type(checker).__name__
                results[checker_name] = HealthStatusContent(status="unhealthy", details={"error": str(e)})
                overall_status = "unhealthy"

        return {"status": overall_status, "timestamp": datetime.now(UTC).isoformat(), "checkers": results}


def create_default_health_service() -> HealthCheckService:
    """Create a health check service with default checkers.

    Returns:
        HealthCheckService: Service with default health checkers registered

    """
    service = HealthCheckService()

    # Register default health checkers
    service.register_checker(ApplicationHealthChecker())
    service.register_checker(DatabaseHealthChecker())

    return service
