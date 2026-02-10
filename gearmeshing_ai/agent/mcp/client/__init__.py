"""MCP Client Package - Core client implementations for Model Context Protocol servers.

This package provides comprehensive client implementations for interacting with MCP servers
using different transport protocols (SSE, HTTP, stdio) with advanced features like
connection pooling, health monitoring, and failover capabilities.

Architecture Overview:
---------------------

The MCP client package follows a layered architecture:

1. **Transport Layer** - Handles different communication protocols
   - SSETransport: Server-Sent Events for real-time communication
   - HTTPTransport: Standard HTTP requests/responses
   - StdioTransport: Local process communication

2. **Client Layer** - High-level client interfaces
   - MCPClient: Main client with transport abstraction
   - EasyMCPClient: Convenience wrapper with static methods
   - AsyncMCPClient: Fully async client for high-performance scenarios

3. **Utility Layer** - Supporting functionality
   - Connection pooling and management
   - Health monitoring and failover
   - Configuration management
   - Error handling and retry logic

Key Features:
------------

✅ **Multiple Transport Support**: SSE, HTTP, and stdio transports
✅ **Connection Management**: Automatic connection pooling and reuse
✅ **Health Monitoring**: Built-in health checks and server readiness detection
✅ **Failover Support**: Automatic failover to backup servers
✅ **Configuration-Driven**: Create clients from configuration files
✅ **Type Safety**: Full type hints and Pydantic validation
✅ **Async Support**: Full async/await support throughout
✅ **Error Handling**: Comprehensive error handling and retry logic
✅ **Monitoring**: Built-in metrics and logging support
✅ **Testing**: Comprehensive test utilities and mocks

Usage Patterns:
--------------

# Basic usage with static methods
tools = await EasyMCPClient.list_tools_sse("http://localhost:8082/sse/sse")
result = await EasyMCPClient.call_tool_sse("http://localhost:8082/sse/sse", "tool_name", {"arg": "value"})

# Factory pattern for flexible client creation
factory = MCPClientFactory()
client = factory.create_sse_client("http://localhost:8082/sse/sse")
tools = await client.list_tools()

# Advanced usage with sessions
async with EasyMCPClient.sse_client("http://localhost:8082/sse/sse") as session:
    await session.initialize()
    tools = await session.list_tools()
    result = await session.call_tool("tool_name", {"arg": "value"})

# Server pool for load balancing
pool = ServerPool(server_configs)
result = await pool.execute_tool_call("clickup", "get_tasks", {})

Design Principles:
-----------------

1. **Simplicity**: Easy-to-use APIs with sensible defaults
2. **Flexibility**: Multiple usage patterns for different scenarios
3. **Reliability**: Built-in error handling and retry logic
4. **Performance**: Connection pooling and async support
5. **Testability**: Comprehensive test utilities and mocks
6. **Extensibility**: Easy to add new transports and features
7. **Type Safety**: Full type hints and validation
8. **Monitoring**: Built-in metrics and logging support

Thread Safety:
--------------

All client implementations are thread-safe and can be safely used in concurrent
environments. Connection pooling is handled automatically to ensure efficient
resource utilization.

Error Handling:
--------------

The package provides comprehensive error handling:

- Connection errors are automatically retried with exponential backoff
- Server errors are properly categorized and handled
- Timeout errors are configurable and handled gracefully
- All errors include detailed context for debugging

Performance Considerations:
--------------------------

- Connection pooling reduces connection overhead
- Async support enables high concurrency
- Efficient serialization/deserialization
- Minimal memory footprint for large-scale deployments
- Configurable timeouts and retry policies

Security:
--------

- Secure credential handling with SecretStr
- TLS support for encrypted communication
- Input validation and sanitization
- Protection against common security vulnerabilities

Extensibility:
------------

The package is designed to be easily extensible:

- New transports can be added by extending BaseTransport
- Custom error handling policies can be implemented
- Monitoring and metrics can be customized
- Configuration sources can be extended

"""

from .config import (
    MCPClientConfig,
    RetryConfig,
    TransportConfig,
)
from .core import (
    AsyncMCPClient,
    EasyMCPClient,
    MCPClient,
)
from .exceptions import (
    ConnectionError,
    MCPClientError,
    ServerError,
    TimeoutError,
)
from .factory import (
    EasyMCPClientFactory,
    MCPClientFactory,
)
from .monitoring import (
    ClientMetrics,
    HealthChecker,
)
from .pool import (
    ConnectionPool,
    ServerPool,
)
from .transports import (
    BaseTransport,
    HTTPTransport,
    SSETransport,
    StdioTransport,
)

__version__ = "1.0.0"
__author__ = "GearMeshing AI Team"

# Public API
__all__ = [
    # Core clients
    "MCPClient",
    "EasyMCPClient",
    "AsyncMCPClient",
    # Transports
    "BaseTransport",
    "SSETransport",
    "HTTPTransport",
    "StdioTransport",
    # Factory
    "MCPClientFactory",
    "EasyMCPClientFactory",
    # Configuration
    "MCPClientConfig",
    "TransportConfig",
    "RetryConfig",
    # Pooling
    "ServerPool",
    "ConnectionPool",
    # Monitoring
    "ClientMetrics",
    "HealthChecker",
    # Exceptions
    "MCPClientError",
    "ConnectionError",
    "TimeoutError",
    "ServerError",
]


# Version compatibility check
def _check_compatibility():
    """Check for version compatibility with dependencies."""
    import sys
    import warnings

    if sys.version_info < (3, 8):
        raise RuntimeError("MCP Client requires Python 3.8 or higher")

    # Check for required dependencies
    try:
        import httpx
        import mcp
        import pydantic
    except ImportError as e:
        raise ImportError(f"Required dependency missing: {e}")


_check_compatibility()
