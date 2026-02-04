# I/O Models Documentation

This package contains reusable Pydantic models for request and response data structures used across the entire GearMeshing-AI project, along with utility functions for working with these models.

## Purpose

The I/O models provide:

- **Validation**: Automatic data validation using Pydantic
- **Serialization**: Consistent JSON serialization/deserialization
- **Documentation**: Self-documenting data structures
- **Type Safety**: Strong typing for better IDE support
- **Reusability**: Common models used across the entire project
- **Utility Functions**: Helper functions for creating and working with models
- **Global Response Structure**: Unified response format for all API endpoints

## 🌟 Global Response Structure

The most important feature is the **unified global response structure** that provides consistency across all API endpoints:

### Structure
```json
{
  "success": boolean,
  "message": "string",
  "content": {},  // Varies by scenario
  "timestamp": "datetime"
}
```

### Examples
```json
// Success response
{
  "success": true,
  "message": "User created successfully",
  "content": {"user_id": 123, "name": "John Doe"},
  "timestamp": "2026-01-30T02:30:00Z"
}

// Error response
{
  "success": false,
  "message": "Validation failed",
  "content": {
    "error_code": "VALIDATION_ERROR",
    "details": {"field": "email", "error": "Invalid format"}
  },
  "timestamp": "2026-01-30T02:30:00Z"
}

// Health check response
{
  "success": true,
  "message": "Service is healthy",
  "content": {
    "status": "healthy",
    "checkers": {"database": {...}, "application": {...}}
  },
  "timestamp": "2026-01-30T02:30:00Z"
}
```

### Benefits
- **Consistency**: All endpoints have the same top-level structure
- **Flexibility**: Content varies by scenario while maintaining consistency
- **Easy Parsing**: Clients can handle all responses with a single structure
- **Type Safety**: Strong typing with Pydantic validation
- **Unified Error Handling**: Consistent error format across all endpoints

## Available Models

# Status Enums for Type Safety

The package provides enums for status fields to ensure type safety and maintainability:

#### `HealthStatus` - Comprehensive health check status
- `HEALTHY` - Service is fully operational
- `UNHEALTHY` - Service has critical issues
- `DEGRADED` - Service is operational but with issues

#### `SimpleHealthStatus` - Basic health check status
- `OK` - Service is responding correctly
- `ERROR` - Service has issues

#### `ReadinessStatus` - Readiness probe status
- `READY` - Application is ready to serve traffic
- `NOT_READY` - Application is not ready

#### `LivenessStatus` - Liveness probe status
- `ALIVE` - Application process is running

### Global Response Models

#### `GlobalResponse[T]`
**🌟 RECOMMENDED: Unified response model for all API endpoints**
```python
{
    "success": boolean,
    "message": "string",
    "content": T,  # Generic content type
    "timestamp": datetime
}
```

#### Content Models (for GlobalResponse)
- `HealthStatusContent` - Health check details
- `SimpleHealthContent` - Simple health status
- `ReadinessContent` - Readiness probe status
- `LivenessContent` - Liveness probe status
- `WelcomeContent` - Welcome message details
- `ApiInfoContent` - API information details
- `ClientInfoContent` - Client information
- `ErrorContent` - Error details

## Utility Functions

### Global Response Functions (Recommended)

#### `create_global_response(success, message, content=None)`
Create a standardized global response.

#### `create_success_response(content, message="Success")`
Create a success response using the global structure.

#### `create_error_response(message, status_code=500, details=None, error_code=None)`
Create an error response using the global structure.

#### Specific Response Creators
- `create_welcome_response(message, version, docs, health)`
- `create_api_info_response(name, version, description, endpoints, documentation)`
- `create_health_response(status, checkers=None, details=None)`
- `create_simple_health_response(status)`
- `create_readiness_response(status)`
- `create_liveness_response(status)`

### General Utility Functions

#### `get_client_info(request)`
Extract client information from FastAPI requests.

#### `sanitize_path(path)`
Sanitize and normalize path strings.

## Usage Examples

### Using Status Enums

```python
from gearmeshing_ai.core.models.io import (
    HealthStatus,
    SimpleHealthStatus,
    ReadinessStatus,
    LivenessStatus,
    create_health_response,
    create_simple_health_response
)

# Health check with enum
health = create_health_response(
    status=HealthStatus.HEALTHY,  # Type-safe enum value
    checkers={"database": {"status": "healthy"}}
)

# Simple health check
simple = create_simple_health_response(
    status=SimpleHealthStatus.OK  # Type-safe enum value
)

# Readiness check
ready = create_readiness_response(
    status=ReadinessStatus.READY  # Type-safe enum value
)

# Liveness check
alive = create_liveness_response(
    status=LivenessStatus.ALIVE  # Type-safe enum value
)
```

### Basic Usage with Global Response Structure

```python
from gearmeshing_ai.core.models.io import (
    create_success_response,
    create_error_response,
    create_health_response
)

# Success response
response = create_success_response(
    content={"user_id": 123, "name": "John"},
    message="User retrieved successfully"
)

# Error response
error = create_error_response(
    message="Validation failed",
    status_code=400,
    details={"field": "email", "error": "Invalid format"},
    error_code="VALIDATION_ERROR"
)

# Health response with enum
health = create_health_response(
    status=HealthStatus.HEALTHY,
    checkers={"database": {"status": "healthy"}, "application": {"status": "healthy"}}
)
```

### FastAPI Integration

```python
from fastapi import FastAPI
from gearmeshing_ai.core.models.io import (
    WelcomeResponseType,
    create_welcome_response
)

app = FastAPI()

@app.get("/", response_model=WelcomeResponseType)
async def root() -> WelcomeResponseType:
    return create_welcome_response(
        message="Welcome to GearMeshing-AI API",
        version="1.0.0",
        docs="/docs",
        health="/health"
    )
```

### Custom Content Types

```python
from gearmeshing_ai.core.models.io import GlobalResponse, BaseModel
from typing import Optional

class UserProfileContent(BaseModel):
    user_id: int
    name: str
    email: str

def get_user_profile(user_id: int) -> GlobalResponse[UserProfileContent]:
    # Your business logic here
    return create_success_response(
        content=UserProfileContent(
            user_id=user_id,
            name="John Doe",
            email="john@example.com"
        ),
        message="User profile retrieved successfully"
    )
```

## Migration Guide

### Using the Global Response Structure

The global response structure provides a consistent format across all endpoints:

```python
# Success
create_success_response(content=user_data, message="Success")

# Error
create_error_response(
    message="Error",
    status_code=500,
    details=error_details
)

# Health
create_health_response(status="healthy", checkers=checkers)
```

## Type Hints

The package provides type hints for better IDE support:

```python
from gearmeshing_ai.core.models.io import (
    GlobalResponseType,
    HealthResponseType,
    WelcomeResponseType
)

def process_data() -> GlobalResponseType[dict]:
    return create_success_response(data={"result": "success"})

def check_health() -> HealthResponseType:
    return create_health_response(status="healthy")
```

## Benefits

1. **🌟 Unified Structure**: All endpoints use the same response format
2. **Flexibility**: Content varies by scenario while maintaining consistency
3. **Validation**: Automatic data validation prevents invalid responses
4. **Documentation**: Models are self-documenting
5. **Type Safety**: Strong typing improves code quality
6. **Cohesion**: Related models and utilities are grouped together
7. **Testing**: Easy to test and validate data structures
8. **Client-Friendly**: Consistent structure makes client implementation easier

## Best Practices

1. **Always use GlobalResponse**: Use `GlobalResponse[T]` for all new endpoints
2. **Use utility functions**: Prefer `create_success_response()` over direct model instantiation
3. **Define content models**: Create specific content models for different scenarios
4. **Handle errors consistently**: Use `create_error_response()` for all error cases
5. **Keep content focused**: Each content model should have a single responsibility
6. **Document content fields**: Use Field descriptions for better documentation

## Extending Models

To add new content models:

1. Create the content model in `common.py`
2. Inherit from `BaseModel` for consistency
3. Add proper field descriptions and validation
4. Export in `__init__.py`
5. Create corresponding utility function in `utils.py`
6. Update documentation

Example:

```python
class CustomContent(BaseModel):
    """Custom content for specific use case."""

    custom_field: str = Field(description="Custom field description")
    optional_field: Optional[int] = Field(default=None, description="Optional field")

def create_custom_response(custom_field: str, optional_field: Optional[int] = None) -> GlobalResponse[CustomContent]:
    """Create a standardized custom response."""
    return create_success_response(
        content=CustomContent(
            custom_field=custom_field,
            optional_field=optional_field
        ),
        message="Custom operation completed"
    )
```

## Package Organization

```
core/models/io/
├── __init__.py          # Package exports
├── common.py            # Pydantic models (GlobalResponse + content models)
├── utils.py             # Utility functions for creating responses
└── README.md            # This documentation
```

This organization creates a cohesive package where:
- **GlobalResponse** provides the unified structure
- **Content models** define scenario-specific data
- **Utility functions** create standardized responses
- All related functionality is grouped together
- Import paths are clean and intuitive

## 🚀 Recommendation

For all new development:
1. **Use `GlobalResponse[T]`** as the response model
2. **Create content models** for specific scenarios
3. **Use utility functions** to create responses
4. **Maintain consistency** across all endpoints

This ensures your API follows the unified response structure and provides the best developer experience for API consumers.
