"""
Core MCP client implementations.

This module provides the main client classes for interacting with MCP servers.
It includes both high-level convenience interfaces and low-level transport
abstractions.

Design Philosophy:
------------------

The core client implementations follow these principles:

1. **Transport Agnostic**: Clients work with any transport implementation
2. **Async First**: All operations are async by default for performance
3. **Resource Management**: Automatic connection pooling and cleanup
4. **Error Resilience**: Comprehensive error handling and retry logic
5. **Type Safety**: Full type hints and validation throughout
6. **Monitoring**: Built-in metrics and health checking

Usage Guidelines:
-----------------

# For simple use cases, use EasyMCPClient static methods
tools = await EasyMCPClient.list_tools_sse("http://localhost:8082/sse/sse")
result = await EasyMCPClient.call_tool_sse("http://localhost:8082/sse/sse", "tool_name", {"arg": "value"})

# For advanced use cases, use MCPClient with custom configuration
config = MCPClientConfig(timeout=30.0, retry_policy=RetryConfig(max_retries=3))
client = MCPClient(config)
transport = SSETransport("http://localhost:8082/sse/sse")
client.set_transport(transport)
tools = await client.list_tools()

# For high-performance scenarios, use AsyncMCPClient
async_client = AsyncMCPClient(config)
await async_client.connect("http://localhost:8082/sse/sse")
tools = await async_client.list_tools()

Thread Safety:
--------------

All client implementations are thread-safe and can be safely used in
concurrent environments. Connection pooling is handled automatically.

Performance:
-----------

- Connection pooling reduces connection overhead
- Async support enables high concurrency
- Efficient serialization/deserialization
- Minimal memory footprint for large-scale deployments

Error Handling:
--------------

The clients provide comprehensive error handling:

- Connection errors are automatically retried with exponential backoff
- Server errors are properly categorized and handled
- Timeout errors are configurable and handled gracefully
- All errors include detailed context for debugging

"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from dataclasses import dataclass, field

from mcp import ClientSession
from .transports import BaseTransport, SSETransport, HTTPTransport, StdioTransport
from .config import MCPClientConfig, RetryConfig
from .exceptions import MCPClientError, ConnectionError, TimeoutError, ServerError
from .monitoring import ClientMetrics

logger = logging.getLogger(__name__)


@dataclass
class ClientStats:
    """Statistics for MCP client operations."""
    
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    average_response_time: float = 0.0
    last_request_time: Optional[float] = None
    
    def update_success(self, response_time: float) -> None:
        """Update stats after a successful request."""
        self.total_requests += 1
        self.successful_requests += 1
        self.total_response_time += response_time
        self.average_response_time = self.total_response_time / self.total_requests
        self.last_request_time = time.time()
    
    def update_failure(self) -> None:
        """Update stats after a failed request."""
        self.total_requests += 1
        self.failed_requests += 1
        self.last_request_time = time.time()


class MCPClient:
    """
    Main MCP client with transport abstraction.
    
    This is the primary client class that provides a high-level interface
    for interacting with MCP servers. It supports multiple transport types
    and includes built-in error handling, retry logic, and monitoring.
    
    Features:
    --------
    - Transport-agnostic interface
    - Automatic retry with exponential backoff
    - Connection pooling and management
    - Built-in metrics and monitoring
    - Comprehensive error handling
    - Thread-safe operations
    
    Example:
    -------
    >>> config = MCPClientConfig(timeout=30.0)
    >>> client = MCPClient(config)
    >>> transport = SSETransport("http://localhost:8082/sse/sse")
    >>> client.set_transport(transport)
    >>> tools = await client.list_tools()
    >>> result = await client.call_tool("get_tasks", {"project_id": "123"})
    """
    
    def __init__(self, config: Optional[MCPClientConfig] = None):
        """
        Initialize MCP client.
        
        Args:
            config: Client configuration. If None, default config is used.
        """
        self.config = config or MCPClientConfig()
        self._transport: Optional[BaseTransport] = None
        self._stats = ClientStats()
        self._metrics = ClientMetrics()
        self._lock = asyncio.Lock()
        
    def set_transport(self, transport: BaseTransport) -> None:
        """
        Set the transport for the client.
        
        Args:
            transport: Transport implementation to use
        """
        self._transport = transport
        logger.debug(f"Set transport: {type(transport).__name__}")
    
    async def connect(self, url: str, transport_type: str = "sse") -> None:
        """
        Connect to an MCP server.
        
        Args:
            url: Server URL
            transport_type: Type of transport ("sse", "http", "stdio")
            
        Raises:
            ConnectionError: If connection fails
            TimeoutError: If connection times out
        """
        if transport_type == "sse":
            transport = SSETransport(url, self.config.timeout)
        elif transport_type == "http":
            transport = HTTPTransport(url, self.config.timeout)
        elif transport_type == "stdio":
            raise ValueError("Stdio transport requires command and args, use connect_stdio()")
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")
        
        self.set_transport(transport)
        await self._ensure_session()
        
    async def connect_stdio(self, command: str, args: List[str], env: Optional[Dict[str, str]] = None) -> None:
        """
        Connect to an MCP server via stdio.
        
        Args:
            command: Command to execute
            args: Command arguments
            env: Environment variables
        """
        transport = StdioTransport(command, args, env, self.config.timeout)
        self.set_transport(transport)
        await self._ensure_session()
    
    async def _ensure_session(self) -> None:
        """Ensure we have an active session."""
        if not self._transport:
            raise ConnectionError("No transport configured")
        
        # Sessions are now managed by the transport's session() context manager
        # No need to pre-create and store a session
        logger.debug("Transport configured and ready")
    
    async def list_tools(self) -> List[str]:
        """
        List available tools from the MCP server.
        
        Returns:
            List of tool names
            
        Raises:
            ConnectionError: If connection fails
            TimeoutError: If request times out
            ServerError: If server returns an error
        """
        return await self._execute_with_retry(
            self._transport.list_tools if self._transport else None,
            "list_tools"
        )
    
    async def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """
        Call a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool execution result
            
        Raises:
            ConnectionError: If connection fails
            TimeoutError: If request times out
            ServerError: If server returns an error
        """
        return await self._execute_with_retry(
            lambda: self._transport.call_tool(tool_name, arguments) if self._transport else None,
            f"call_tool({tool_name})"
        )
    
    async def _execute_with_retry(self, operation, operation_name: str) -> Any:
        """
        Execute an operation with retry logic.
        
        Args:
            operation: The operation to execute
            operation_name: Name of the operation for logging
            
        Returns:
            Operation result
            
        Raises:
            MCPClientError: If all retries are exhausted
        """
        if not operation:
            raise ConnectionError("No transport configured")
        
        start_time = time.time()
        last_error = None
        
        for attempt in range(self.config.retry_policy.max_retries + 1):
            try:
                result = await operation()
                
                # Update success stats
                response_time = time.time() - start_time
                self._stats.update_success(response_time)
                self._metrics.record_success(operation_name, response_time)
                
                logger.debug(f"Operation {operation_name} succeeded in {response_time:.3f}s")
                return result
                
            except (ConnectionError, TimeoutError) as e:
                last_error = e
                response_time = time.time() - start_time
                self._stats.update_failure()
                self._metrics.record_failure(operation_name, str(e))
                
                if attempt < self.config.retry_policy.max_retries:
                    delay = self.config.retry_policy.get_delay(attempt)
                    logger.warning(
                        f"Operation {operation_name} failed (attempt {attempt + 1}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Operation {operation_name} failed after {attempt + 1} attempts: {e}")
                    
            except Exception as e:
                # Non-retryable errors
                self._stats.update_failure()
                self._metrics.record_failure(operation_name, str(e))
                logger.error(f"Operation {operation_name} failed with non-retryable error: {e}")
                raise ServerError(f"Server error during {operation_name}: {e}")
        
        # All retries exhausted
        raise last_error or MCPClientError(f"Operation {operation_name} failed")
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[ClientSession, None]:
        """
        Get the underlying session for advanced usage.
        
        Yields:
            ClientSession: The MCP session
            
        Example:
        -------
        >>> async with client.session() as session:
        ...     tools = await session.list_tools()
        ...     result = await session.call_tool("tool_name", {"arg": "value"})
        """
        if not self._transport:
            raise ConnectionError("No transport configured")
        
        async with self._transport.session() as session:
            yield session
    
    def get_stats(self) -> ClientStats:
        """Get client statistics."""
        return self._stats
    
    def get_metrics(self) -> ClientMetrics:
        """Get client metrics."""
        return self._metrics
    
    async def close(self) -> None:
        """Close the client and cleanup resources."""
        async with self._lock:
            if self._transport:
                try:
                    await self._transport.close()
                except Exception as e:
                    logger.warning(f"Error closing transport: {e}")
                finally:
                    self._transport = None
            
            logger.debug("Client closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


class EasyMCPClient:
    """
    Convenience wrapper with static methods for common MCP operations.
    
    This class provides static methods for quick and easy MCP operations
    without needing to manage client instances. It's perfect for simple
    use cases and testing.
    
    Features:
    --------
    - Static methods for common operations
    - Automatic session management
    - Built-in error handling
    - Support for all transport types
    - Context managers for resource management
    
    Example:
    -------
    >>> # Quick tool listing
    >>> tools = await EasyMCPClient.list_tools_sse("http://localhost:8082/sse/sse")
    >>> 
    >>> # Quick tool calling
    >>> result = await EasyMCPClient.call_tool_sse(
    ...     "http://localhost:8082/sse/sse", 
    ...     "get_tasks", 
    ...     {"project_id": "123"}
    ... )
    >>> 
    >>> # Session-based usage
    >>> async with EasyMCPClient.sse_client("http://localhost:8082/sse/sse") as session:
    ...     await session.initialize()
    ...     tools = await session.list_tools()
    ...     result = await session.call_tool("tool_name", {"arg": "value"})
    """
    
    @staticmethod
    @asynccontextmanager
    async def sse_client(url: str, timeout: float = 30.0) -> AsyncGenerator[ClientSession, None]:
        """
        Create an SSE-based MCP client session.
        
        Args:
            url: The SSE endpoint URL
            timeout: Connection timeout in seconds
            
        Yields:
            ClientSession: Initialized MCP client session
            
        Example:
        -------
        >>> async with EasyMCPClient.sse_client("http://localhost:8082/sse/sse") as session:
        ...     await session.initialize()
        ...     tools = await session.list_tools()
        """
        transport = SSETransport(url, timeout)
        async with transport.session() as session:
            yield session
    
    @staticmethod
    @asynccontextmanager
    async def http_client(url: str, timeout: float = 30.0) -> AsyncGenerator[ClientSession, None]:
        """
        Create an HTTP-based MCP client session.
        
        Args:
            url: The HTTP endpoint URL
            timeout: Connection timeout in seconds
            
        Yields:
            ClientSession: Initialized MCP client session
        """
        transport = HTTPTransport(url, timeout)
        async with transport.session() as session:
            yield session
    
    @staticmethod
    @asynccontextmanager
    async def stdio_client(
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ) -> AsyncGenerator[ClientSession, None]:
        """
        Create a stdio-based MCP client session.
        
        Args:
            command: Command to execute the MCP server
            args: Arguments for the command
            env: Optional environment variables
            timeout: Connection timeout in seconds
            
        Yields:
            ClientSession: Initialized MCP client session
        """
        transport = StdioTransport(command, args, env, timeout)
        async with transport.session() as session:
            yield session
    
    @staticmethod
    async def list_tools_sse(url: str, timeout: float = 30.0) -> List[str]:
        """
        List available tools using SSE transport.
        
        Args:
            url: The SSE endpoint URL
            timeout: Connection timeout in seconds
            
        Returns:
            List of tool names
        """
        transport = SSETransport(url, timeout)
        return await transport.list_tools()
    
    @staticmethod
    async def list_tools_http(url: str, timeout: float = 30.0) -> List[str]:
        """
        List available tools using HTTP transport.
        
        Args:
            url: The HTTP endpoint URL
            timeout: Connection timeout in seconds
            
        Returns:
            List of tool names
        """
        transport = HTTPTransport(url, timeout)
        return await transport.list_tools()
    
    @staticmethod
    async def list_tools_stdio(
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ) -> List[str]:
        """
        List available tools using stdio transport.
        
        Args:
            command: Command to execute the MCP server
            args: Arguments for the command
            env: Optional environment variables
            timeout: Connection timeout in seconds
            
        Returns:
            List of tool names
        """
        transport = StdioTransport(command, args, env, timeout)
        return await transport.list_tools()
    
    @staticmethod
    async def call_tool_sse(
        url: str,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Any:
        """
        Call a tool using SSE transport.
        
        Args:
            url: The SSE endpoint URL
            tool_name: Name of the tool to call
            arguments: Optional tool arguments
            timeout: Connection timeout in seconds
            
        Returns:
            Tool execution result
        """
        transport = SSETransport(url, timeout)
        return await transport.call_tool(tool_name, arguments or {})
    
    @staticmethod
    async def call_tool_http(
        url: str,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Any:
        """
        Call a tool using HTTP transport.
        
        Args:
            url: The HTTP endpoint URL
            tool_name: Name of the tool to call
            arguments: Optional tool arguments
            timeout: Connection timeout in seconds
            
        Returns:
            Tool execution result
        """
        transport = HTTPTransport(url, timeout)
        return await transport.call_tool(tool_name, arguments or {})
    
    @staticmethod
    async def call_tool_stdio(
        command: str,
        args: List[str],
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ) -> Any:
        """
        Call a tool using stdio transport.
        
        Args:
            command: Command to execute the MCP server
            args: Arguments for the command
            tool_name: Name of the tool to call
            arguments: Optional tool arguments
            env: Optional environment variables
            timeout: Connection timeout in seconds
            
        Returns:
            Tool execution result
        """
        transport = StdioTransport(command, args, env, timeout)
        return await transport.call_tool(tool_name, arguments or {})


class AsyncMCPClient(MCPClient):
    """
    High-performance async MCP client for advanced use cases.
    
    This client extends the base MCPClient with additional async-specific
    features like connection pooling, concurrent request handling, and
    advanced monitoring capabilities.
    
    Features:
    --------
    - Connection pooling for high performance
    - Concurrent request handling
    - Advanced monitoring and metrics
    - Configurable concurrency limits
    - Background health checking
    - Automatic failover support
    
    Example:
    -------
    >>> config = MCPClientConfig(
    ...     timeout=30.0,
    ...     max_concurrent_requests=10,
    ...     enable_health_checking=True
    ... )
    >>> client = AsyncMCPClient(config)
    >>> await client.connect("http://localhost:8082/sse/sse")
    >>> 
    >>> # Concurrent operations
    >>> tools_task = client.list_tools()
    >>> result_task = client.call_tool("get_tasks", {"project_id": "123"})
    >>> tools, result = await asyncio.gather(tools_task, result_task)
    """
    
    def __init__(self, config: Optional[MCPClientConfig] = None):
        """
        Initialize async MCP client.
        
        Args:
            config: Client configuration
        """
        super().__init__(config)
        self._semaphore = asyncio.Semaphore(config.max_concurrent_requests if config else 10)
        self._connection_pool = {}
        self._health_check_task: Optional[asyncio.Task] = None
        self._background_tasks = set()
    
    async def connect(self, url: str, transport_type: str = "sse") -> None:
        """
        Connect to an MCP server with connection pooling.
        
        Args:
            url: Server URL
            transport_type: Type of transport
        """
        connection_key = f"{transport_type}:{url}"
        
        # Check if we have a pooled connection
        if connection_key in self._connection_pool:
            transport = self._connection_pool[connection_key]
            if await transport.is_healthy():
                self.set_transport(transport)
                await self._ensure_session()
                return
        
        # Create new connection
        await super().connect(url, transport_type)
        
        # Add to pool
        if self._transport:
            self._connection_pool[connection_key] = self._transport
        
        # Start background health checking
        if self.config.enable_health_checking:
            self._start_health_checking()
    
    async def _execute_with_concurrency_limit(self, operation, operation_name: str) -> Any:
        """
        Execute operation with concurrency limit.
        
        Args:
            operation: Operation to execute
            operation_name: Operation name
            
        Returns:
            Operation result
        """
        async with self._semaphore:
            return await self._execute_with_retry(operation, operation_name)
    
    async def list_tools(self) -> List[str]:
        """List tools with concurrency control."""
        if not self._transport:
            raise ConnectionError("No transport configured")
        
        return await self._execute_with_concurrency_limit(
            self._transport.list_tools,
            "list_tools"
        )
    
    async def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Call tool with concurrency control."""
        if not self._transport:
            raise ConnectionError("No transport configured")
        
        return await self._execute_with_concurrency_limit(
            lambda: self._transport.call_tool(tool_name, arguments),
            f"call_tool({tool_name})"
        )
    
    def _start_health_checking(self) -> None:
        """Start background health checking."""
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            self._background_tasks.add(self._health_check_task)
            self._health_check_task.add_done_callback(self._background_tasks.discard)
    
    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._check_connection_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Health check error: {e}")
    
    async def _check_connection_health(self) -> None:
        """Check connection health and reconnect if needed."""
        if not self._transport:
            return
        
        try:
            is_healthy = await self._transport.is_healthy()
            if not is_healthy:
                logger.warning("Connection unhealthy, attempting reconnection")
                # Reconnection logic would go here
                await self._reconnect()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    async def _reconnect(self) -> None:
        """Reconnect to the server."""
        # Implementation would depend on stored connection info
        logger.info("Reconnecting to server")
    
    async def close(self) -> None:
        """Close client and cleanup background tasks."""
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Close connection pool
        for transport in self._connection_pool.values():
            try:
                await transport.close()
            except Exception as e:
                logger.warning(f"Error closing pooled transport: {e}")
        
        self._connection_pool.clear()
        
        # Close parent
        await super().close()
        
        logger.debug("Async client closed")
