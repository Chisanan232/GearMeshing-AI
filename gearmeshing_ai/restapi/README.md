# GearMeshing-AI REST API

This package provides the REST API implementation for the GearMeshing-AI platform, following duck typing principles for clean, maintainable, and extensible code.

## Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **Health Checking**: Comprehensive health check endpoints for monitoring
- **Duck Typing**: Clean, maintainable code following Python duck typing principles
- **Docker Support**: Ready for containerization with proper startup scripts
- **CORS Support**: Configured for cross-origin requests
- **Auto Documentation**: Automatic API documentation with Swagger/ReDoc

## Quick Start

### Running the Web Server

```bash
# Using the Docker script (recommended)
SERVICE_TYPE=web ./scripts/docker/run-server.sh

# Or directly with uvicorn
uvicorn gearmeshing_ai.restapi.main:app --host 0.0.0.0 --port 8000 --reload
```

### Using Docker

```bash
# Build the image
docker build -t gearmeshing-ai .

# Run the container
docker run -p 8000:8000 -e SERVICE_TYPE=web gearmeshing-ai
```

## API Endpoints

### Health Check Endpoints

- **`GET /`** - Welcome message and basic info
- **`GET /info`** - Detailed API information
- **`GET /health`** - Comprehensive health check of all components
- **`GET /health/simple`** - Simple health check for load balancers
- **`GET /health/ready`** - Readiness probe for Kubernetes
- **`GET /health/live`** - Liveness probe for Kubernetes

### Documentation

- **`/docs`** - Interactive Swagger UI
- **`/redoc`** - ReDoc documentation

## Architecture

The application follows duck typing principles with clear separation of concerns:

### Core Components

- **`main.py`** - FastAPI application factory and configuration
- **`service/health.py`** - Health checking business logic and services
- **`internal/utils.py`** - Internal utilities and helpers
- **`routers/health.py`** - Health check API endpoints

### Architecture Layers

The application follows a clean layered architecture:

1. **`service/`** - Business logic layer
   - Contains core business logic and services
   - Follows duck typing principles for extensibility
   - Manages domain-specific operations

2. **`routers/`** - API layer
   - FastAPI routers and endpoints
   - HTTP request/response handling
   - API documentation and validation

3. **`internal/`** - Utilities layer
   - Internal helpers and utilities
   - Common functions used across the application
   - Support functions for the API layer

### Duck Typing Design

The codebase uses duck typing principles:

1. **Protocol-based interfaces** - Any class that implements the expected interface works
2. **Factory patterns** - Easy to extend and configure
3. **Template method pattern** - Consistent behavior with customizable logic
4. **Dependency injection** - Loose coupling between components

### Health Checking System

The health checking system demonstrates duck typing:

```python
# Any class with check_health() method can be a health checker
class HealthChecker(Protocol):
    def check_health(self) -> HealthStatus: ...

# Custom health checkers can be easily added
class CustomHealthChecker:
    def check_health(self) -> HealthStatus:
        # Custom logic here
        pass
```

## Configuration

### Environment Variables

- **`SERVICE_TYPE`** - Service type to run (`web`, `mcp`, `webhook`, `integrated`)
- **`HOST`** - Host to bind to (default: `0.0.0.0`)
- **`PORT`** - Port to bind to (default: `8000`)
- **`LOG_LEVEL`** - Logging level (default: `info`)
- **`RELOAD`** - Enable auto-reload (default: `false`)

### Docker Configuration

The application is configured for Docker with:

- Multi-stage builds for optimization
- Non-root user for security
- Proper signal handling
- Health check support

## Development

### Adding New Endpoints

1. Create a new router in `routers/` directory
2. Follow duck typing principles for clean design
3. Register the router in `main.py`

```python
# Example new router
# routers/custom.py
from fastapi import APIRouter

class CustomRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/custom", tags=["custom"])
        self._setup_routes()
    
    def _setup_routes(self):
        self.router.add_api_route("/", self.custom_endpoint, methods=["GET"])
    
    async def custom_endpoint(self):
        return {"message": "Custom endpoint"}

def create_custom_router():
    return CustomRouter().router
```

### Adding Health Checkers

```python
# Create custom health checker
class DatabaseHealthChecker(BaseHealthChecker):
    def __init__(self, db_connection):
        super().__init__("database")
        self.db = db_connection
    
    def _do_check_health(self) -> HealthStatus:
        # Check database connectivity
        return HealthStatus(
            status="healthy",
            message="Database is connected",
            timestamp=datetime.utcnow()
        )

# Register with service
service = HealthCheckService()
service.register_checker(DatabaseHealthChecker(db_connection))
```

## Testing

The application includes comprehensive testing:

```bash
# Run the built-in tests
python test_web_app.py

# Test with curl
curl http://localhost:8000/health
curl http://localhost:8000/info
```

## Production Considerations

- **Security**: Configure CORS appropriately for production
- **Monitoring**: Use health check endpoints for monitoring
- **Logging**: Configure structured logging for production
- **Scaling**: The application is stateless and ready for horizontal scaling

## Dependencies

See `pyproject.toml` for the full list of dependencies:

- **fastapi** - Web framework
- **uvicorn** - ASGI server
- **pydantic** - Data validation
- **sse-starlette** - Server-sent events support

## License

MIT License - see LICENSE file for details.
