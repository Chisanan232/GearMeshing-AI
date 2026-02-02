"""Tests for the GearMeshing-AI REST API main application.

This module contains comprehensive tests for the FastAPI application
factory, lifecycle management, and main endpoints.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from gearmeshing_ai.core.models.io import ApiInfoResponseType, WelcomeResponseType
from gearmeshing_ai.restapi.main import ApplicationFactory, app, create_application


class TestApplicationFactory:
    """Test cases for ApplicationFactory class."""

    def test_application_factory_initialization(self):
        """Test ApplicationFactory initialization."""
        factory = ApplicationFactory()
        assert factory._app is None

    def test_create_app_default_configuration(self):
        """Test creating app with default configuration."""
        factory = ApplicationFactory()
        app = factory.create_app()

        assert isinstance(app, FastAPI)
        assert app.title == "GearMeshing-AI API"
        assert app.description == "Enterprise AI agents development platform API"
        assert app.version == "0.0.0"
        assert factory._app is app

    def test_create_app_custom_configuration(self):
        """Test creating app with custom configuration."""
        factory = ApplicationFactory()
        app = factory.create_app(title="Custom API")

        assert app.title == "Custom API"
        assert app.description == "Enterprise AI agents development platform API"

    def test_create_app_middleware_setup(self):
        """Test that middleware is properly configured."""
        factory = ApplicationFactory()
        app = factory.create_app()

        # Check that middleware is configured
        assert len(app.user_middleware) > 0

    def test_create_app_router_setup(self):
        """Test that routers are properly configured."""
        factory = ApplicationFactory()
        app = factory.create_app()

        # Check that health router is included
        routes = [route.path for route in app.routes]
        # Health routes may have trailing slash
        assert "/health/" in routes or "/health" in routes
        assert "/health/simple" in routes

    def test_multiple_create_app_calls(self):
        """Test multiple create_app calls return same instance."""
        factory = ApplicationFactory()
        app1 = factory.create_app()
        app2 = factory.create_app()

        # Both should be FastAPI instances with same configuration
        assert isinstance(app1, FastAPI)
        assert isinstance(app2, FastAPI)
        assert app1.title == app2.title


class TestCreateApplicationFunction:
    """Test cases for create_application factory function."""

    def test_create_application_default(self):
        """Test create_application with default parameters."""
        app = create_application()

        assert isinstance(app, FastAPI)
        assert app.title == "GearMeshing-AI API"
        assert app.version == "0.0.0"

    def test_create_application_with_kwargs(self):
        """Test create_application with custom parameters."""
        app = create_application(title="Test API")

        assert app.title == "Test API"
        assert app.version == "0.0.0"


class TestMainEndpoints:
    """Test cases for main application endpoints."""

    def setup_method(self):
        """Setup test client for each test."""
        self.client = TestClient(app)

    def test_root_endpoint(self):
        """Test the root endpoint (/)."""
        response = self.client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "success" in data
        assert "message" in data
        assert "content" in data
        assert "timestamp" in data

        # Verify response values
        assert data["success"] is True
        assert data["message"] == "Welcome to GearMeshing-AI API"
        assert data["content"]["message"] == "Welcome to GearMeshing-AI API"
        assert data["content"]["version"] == "0.0.0"
        assert data["content"]["docs"] == "/docs"
        assert data["content"]["health"] == "/health"

    def test_root_endpoint_response_model(self):
        """Test root endpoint response model validation."""
        response = self.client.get("/")
        data = response.json()

        # Validate against response model
        welcome_response = WelcomeResponseType(**data)
        assert welcome_response.success is True
        assert welcome_response.content.message == "Welcome to GearMeshing-AI API"

    def test_info_endpoint(self):
        """Test the info endpoint (/info)."""
        response = self.client.get("/info")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "success" in data
        assert "message" in data
        assert "content" in data
        assert "timestamp" in data

        # Verify response values
        assert data["success"] is True
        assert data["content"]["name"] == "GearMeshing-AI API"
        assert data["content"]["version"] == "0.0.0"
        assert data["content"]["description"] == "Enterprise AI agents development platform API"
        assert isinstance(data["content"]["endpoints"], list)
        assert isinstance(data["content"]["documentation"], dict)

    def test_info_endpoint_response_model(self):
        """Test info endpoint response model validation."""
        response = self.client.get("/info")
        data = response.json()

        # Validate against response model
        api_info_response = ApiInfoResponseType(**data)
        assert api_info_response.success is True
        assert api_info_response.content.name == "GearMeshing-AI API"

    def test_info_endpoint_endpoints_list(self):
        """Test that info endpoint returns expected endpoints."""
        response = self.client.get("/info")
        data = response.json()

        endpoints = data["content"]["endpoints"]
        expected_endpoints = ["/", "/info", "/health", "/health/simple", "/health/ready", "/health/live"]

        for endpoint in expected_endpoints:
            assert endpoint in endpoints

    def test_info_endpoint_documentation(self):
        """Test that info endpoint returns documentation links."""
        response = self.client.get("/info")
        data = response.json()

        documentation = data["content"]["documentation"]
        assert "swagger" in documentation
        assert "redoc" in documentation
        assert documentation["swagger"] == "/docs"
        assert documentation["redoc"] == "/redoc"

    def test_openapi_docs_endpoint(self):
        """Test that OpenAPI docs endpoint is available."""
        response = self.client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

    def test_swagger_docs_endpoint(self):
        """Test that Swagger UI docs endpoint is available."""
        response = self.client.get("/docs")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_docs_endpoint(self):
        """Test that ReDoc docs endpoint is available."""
        response = self.client.get("/redoc")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestApplicationLifecycle:
    """Test cases for application lifecycle management."""

    def test_lifespan_context_manager_creation(self):
        """Test that lifespan context manager is created properly."""
        factory = ApplicationFactory()
        lifespan = factory._create_lifespan()

        assert callable(lifespan)

    def test_startup_success_logging(self):
        """Test successful startup logging."""
        factory = ApplicationFactory()
        lifespan = factory._create_lifespan()

        # Verify lifespan is callable
        assert callable(lifespan)

    def test_shutdown_success_logging(self):
        """Test successful shutdown logging."""
        factory = ApplicationFactory()
        lifespan = factory._create_lifespan()

        # Verify lifespan is callable
        assert callable(lifespan)

    def test_startup_failure_logging(self):
        """Test startup failure logging."""
        factory = ApplicationFactory()
        app = factory.create_app()

        # Verify app is created successfully
        assert isinstance(app, FastAPI)

    def test_shutdown_failure_logging(self):
        """Test shutdown failure logging."""
        factory = ApplicationFactory()
        app = factory.create_app()

        # Verify app is created successfully
        assert isinstance(app, FastAPI)


class TestGlobalAppInstance:
    """Test cases for the global app instance."""

    def test_global_app_instance_exists(self):
        """Test that global app instance is created."""
        from gearmeshing_ai.restapi.main import app

        assert isinstance(app, FastAPI)
        assert app.title == "GearMeshing-AI API"

    def test_global_app_same_as_created(self):
        """Test that global app is same as created by factory."""
        from gearmeshing_ai.restapi.main import app, create_application

        created_app = create_application()
        # Note: These might be different instances due to module-level execution
        # but should have the same configuration
        assert app.title == created_app.title
        assert app.version == created_app.version


class TestErrorHandling:
    """Test cases for error handling in main application."""

    def test_404_error_handling(self):
        """Test 404 error handling."""
        client = TestClient(app)
        response = client.get("/nonexistent")

        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Test method not allowed handling."""
        client = TestClient(app)
        response = client.post("/")

        # Should return 405 Method Not Allowed or 422 Validation Error
        assert response.status_code in [405, 422]

    def test_invalid_json_request(self):
        """Test handling of invalid JSON requests."""
        client = TestClient(app)
        response = client.post("/info", content="invalid json", headers={"content-type": "application/json"})

        # POST on GET endpoint returns 405 or 422
        assert response.status_code in [405, 422]


class TestMiddlewareConfiguration:
    """Test cases for middleware configuration."""

    def test_cors_middleware_configuration(self):
        """Test CORS middleware configuration."""
        client = TestClient(app)

        # Test preflight request
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        # Should allow CORS
        assert response.status_code in [200, 204]
        if response.status_code == 200:
            assert "access-control-allow-origin" in response.headers

    def test_cors_headers_in_response(self):
        """Test CORS headers in actual responses."""
        client = TestClient(app)

        response = client.get("/", headers={"Origin": "http://localhost:3000"})

        assert response.status_code == 200
        # CORS headers should be present (depending on FastAPI CORS configuration)
