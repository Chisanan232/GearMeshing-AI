"""
MCP (Model Context Protocol) client package.

This package provides a comprehensive set of tools for interacting with MCP servers
using different transport protocols (SSE, HTTP, stdio) with advanced features like
connection pooling, health monitoring, and failover capabilities.

Key Components:
- MCPClient: Main client class for MCP server interactions
- EasyMCPClient: Convenience wrapper with static methods
- AsyncMCPClient: Fully async client for high-performance scenarios
- Transport classes: SSETransport, HTTPTransport, StdioTransport
- Factory classes: MCPClientFactory, EasyMCPClientFactory
- Utility functions: Health checks, server discovery, load balancing
- Monitoring: ClientMetrics, HealthChecker, PerformanceTracker
- Pooling: ConnectionPool, ServerPool
- Configuration: MCPClientConfig, TransportConfig, RetryConfig

Usage Examples:
    # Easy usage with static methods
    tools = await EasyMCPClient.list_tools_sse("http://localhost:8082/sse/sse")
    result = await EasyMCPClient.call_tool_sse("http://localhost:8082/sse/sse", "tool_name", {"arg": "value"})
    
    # Factory pattern
    factory = MCPClientFactory()
    client = await factory.create_sse_client("http://localhost:8082/sse/sse")
    tools = await client.list_tools()
    
    # Advanced usage with sessions
    async with EasyMCPClient.sse_client("http://localhost:8082/sse/sse") as session:
        await session.initialize()
        tools = await session.list_tools()
        result = await session.call_tool("tool_name", {"arg": "value"})

Note: This package now re-exports from the new gearmeshing_ai.agent_core.mcp.client subpackage
which provides enhanced functionality with better architecture, monitoring, and error handling.
"""

# Re-export everything from the new client package
from .client import (
    # Core clients
    MCPClient,
    EasyMCPClient,
    AsyncMCPClient,
    
    # Transports
    BaseTransport,
    SSETransport,
    HTTPTransport,
    StdioTransport,
    
    # Factory
    MCPClientFactory,
    EasyMCPClientFactory,
    
    # Configuration
    MCPClientConfig,
    TransportConfig,
    RetryConfig,
    
    # Pooling
    ServerPool,
    ConnectionPool,
    
    # Monitoring
    ClientMetrics,
    HealthChecker,
    
    # Exceptions
    MCPClientError,
    ConnectionError,
    TimeoutError,
    ServerError,
)

# Version
__version__ = "1.0.0"

# Public API - re-export everything from client package
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
    
    # Factory classes
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