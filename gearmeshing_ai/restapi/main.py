"""Main FastAPI application for GearMeshing-AI REST API.

This module creates and configures the FastAPI application following
duck typing principles for clean, maintainable, and extensible code.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gearmeshing_ai.core.models.io import (
    ApiInfoResponseType,
    WelcomeResponseType,
    create_api_info_response,
    create_welcome_response,
)

from .routers.health import get_health_router


class ApplicationFactory:
    """Factory for creating FastAPI applications.

    This class follows duck typing principles and provides a clean
    way to create and configure FastAPI applications with different
    configurations and dependencies.
    """

    def __init__(self) -> None:
        """Initialize the application factory."""
        self._app: FastAPI | None = None

    def create_app(self, title: str = "GearMeshing-AI API", **kwargs: Any) -> FastAPI:
        """Create and configure FastAPI application.

        This method creates a FastAPI application with standard
        configuration and middleware setup.

        Args:
            title: Application title
            **kwargs: Additional FastAPI configuration options

        Returns:
            FastAPI: Configured FastAPI application

        """
        # Create FastAPI app with lifecycle management
        app = FastAPI(
            title=title,
            description="Enterprise AI agents development platform API",
            version="0.0.0",
            lifespan=self._create_lifespan(),
            **kwargs,
        )

        # Configure middleware
        self._setup_middleware(app)

        # Setup routers
        self._setup_routers(app)

        self._app = app
        return app

    def _setup_middleware(self, app: FastAPI) -> None:
        """Setup application middleware.

        This method configures all necessary middleware for the
        FastAPI application following duck typing principles.

        Args:
            app: FastAPI application instance

        """
        # Setup CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routers(self, app: FastAPI) -> None:
        """Setup application routers.

        This method registers all API routers with the FastAPI
        application. The router setup follows duck typing principles
        making it easy to add new routers.

        Args:
            app: FastAPI application instance

        """
        # Include health check router
        health_router = get_health_router()
        app.include_router(health_router)

        # Add main endpoints
        self._setup_main_endpoints(app)

        # Add other routers here as they are created
        # app.include_router(other_router)

    def _setup_main_endpoints(self, app: FastAPI) -> None:
        """Setup main application endpoints.

        Args:
            app: FastAPI application instance

        """

        @app.get("/", response_model=WelcomeResponseType)  # type: ignore
        async def root() -> WelcomeResponseType:
            """Root endpoint for the API.

            This endpoint provides basic information about the API
            and serves as a welcome page using the global response structure.

            Returns:
                WelcomeResponseType: API welcome information with global structure

            """
            return create_welcome_response(
                message="Welcome to GearMeshing-AI API", version="0.0.0", docs="/docs", health="/health"
            )

        @app.get("/info", response_model=ApiInfoResponseType)  # type: ignore
        async def info() -> ApiInfoResponseType:
            """Information endpoint for the API.

            This endpoint provides detailed information about the API
            including available endpoints and features using the global response structure.

            Returns:
                ApiInfoResponseType: Detailed API information with global structure

            """
            return create_api_info_response(
                name="GearMeshing-AI API",
                version="0.0.0",
                description="Enterprise AI agents development platform API",
                endpoints=["/", "/info", "/health", "/health/simple", "/health/ready", "/health/live"],
                documentation={"swagger": "/docs", "redoc": "/redoc"},
            )

    def _create_lifespan(self) -> Any:
        """Create application lifespan context manager.

        This method creates a lifespan context manager that handles
        application startup and shutdown events.

        Returns:
            Lifespan context manager

        """

        @asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
            """Handle application startup and shutdown.

            This context manager manages the application lifecycle,
            including startup initialization and cleanup.

            Args:
                app: FastAPI application instance

            Yields:
                None: Control is yielded to the application

            """
            # Startup logic
            print("🚀 GearMeshing-AI API is starting up...")

            try:
                # Initialize application components here
                # For example: database connections, external services, etc.

                print("✅ GearMeshing-AI API startup completed successfully")

                # Yield control to the application
                yield

            except Exception as e:
                print(f"❌ GearMeshing-AI API startup failed: {e}")
                raise

            finally:
                # Shutdown logic
                print("🔄 GearMeshing-AI API is shutting down...")

                try:
                    # Cleanup resources here
                    # For example: close database connections, cleanup services, etc.

                    print("✅ GearMeshing-AI API shutdown completed")

                except Exception as e:
                    print(f"❌ GearMeshing-AI API shutdown failed: {e}")

        return lifespan


# Global application factory instance
_app_factory = ApplicationFactory()


def create_application(**kwargs: Any) -> FastAPI:
    """Create and return a FastAPI application.

    This factory function provides a simple interface for creating
    FastAPI applications with default configuration.

    Args:
        **kwargs: Additional FastAPI configuration options

    Returns:
        FastAPI: Configured FastAPI application

    """
    return _app_factory.create_app(**kwargs)


# Create the main application instance
app = create_application()


# Note: Run the application using uvicorn command:
# uvicorn gearmeshing_ai.restapi.main:app --host 0.0.0.0 --port 8000 --reload
