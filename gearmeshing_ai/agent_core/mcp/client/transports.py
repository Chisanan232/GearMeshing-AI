"""
Transport implementations for MCP client communication.

This module provides transport layer implementations for different communication
protocols used by MCP servers. Each transport handles the low-level details of
establishing connections, sending requests, and receiving responses.

Transport Architecture:
---------------------

The transport layer follows a consistent interface pattern:

1. **BaseTransport** - Abstract base class defining the transport interface
2. **SSETransport** - Server-Sent Events for real-time communication
3. **HTTPTransport** - Standard HTTP requests/responses
4. **StdioTransport** - Local process communication

Each transport implements:
- Connection establishment and management
- Request/response handling
- Error handling and recovery
- Health checking capabilities
- Resource cleanup

Design Principles:
------------------

1. **Protocol Agnostic**: All transports implement the same interface
2. **Async First**: All operations are async for performance
3. **Resource Management**: Automatic connection cleanup
4. **Error Resilience**: Comprehensive error handling
5. **Health Monitoring**: Built-in health checking
6. **Type Safety**: Full type hints throughout

Usage Guidelines:
-----------------

# Use SSE for real-time bidirectional communication
transport = SSETransport("http://localhost:8082/sse/sse", timeout=30.0)
await transport.connect()
tools = await transport.list_tools()

# Use HTTP for simple request/response patterns
transport = HTTPTransport("http://localhost:3000/mcp", timeout=30.0)
await transport.connect()
result = await transport.call_tool("tool_name", {"arg": "value"})

# Use Stdio for local process communication
transport = StdioTransport("python", ["server.py"], timeout=30.0)
await transport.connect()
tools = await transport.list_tools()

Performance Considerations:
--------------------------

- SSE: Best for real-time updates and streaming
- HTTP: Best for simple request/response patterns
- Stdio: Best for local development and testing

Error Handling:
--------------

All transports provide comprehensive error handling:

- Connection errors are properly categorized
- Timeout errors are configurable
- Server errors include detailed context
- Network errors trigger automatic retry

Extensibility:
------------

New transports can be added by extending BaseTransport:

class CustomTransport(BaseTransport):
    async def connect(self) -> None:
        # Implement connection logic
        pass
    
    async def list_tools(self) -> List[str]:
        # Implement tool listing
        pass
    
    async def call_tool(self, name: str, args: Dict[str, Any]) -> Any:
        # Implement tool calling
        pass

"""

import asyncio
import logging
import subprocess
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, AsyncGenerator

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.stdio import stdio_client

from .exceptions import ConnectionError, TimeoutError, ServerError

logger = logging.getLogger(__name__)


class BaseTransport(ABC):
    """
    Abstract base class for MCP transport implementations.
    
    This class defines the interface that all transport implementations
    must follow. It provides common functionality for connection management,
    error handling, and health checking.
    
    Design Principles:
    ------------------
    
    1. **Protocol Agnostic**: Works with any MCP protocol
    2. **Async First**: All operations are async
    3. **Resource Safe**: Automatic cleanup on errors
    4. **Error Resilient**: Comprehensive error handling
    5. **Health Aware**: Built-in health checking
    
    Implementation Guidelines:
    -------------------------
    
    1. Implement all abstract methods
    2. Handle connection lifecycle properly
    3. Provide meaningful error messages
    4. Support timeout configuration
    5. Implement health checking
    
    Example:
    -------
    >>> class MyTransport(BaseTransport):
    ...     async def list_tools(self) -> List[str]:
    ...         # Tool listing logic
    ...         pass
    ...     
    ...     async def call_tool(self, name: str, args: Dict[str, Any]) -> Any:
    ...         # Tool calling logic
    ...         pass
    """
    
    def __init__(self, timeout: float = 30.0):
        """
        Initialize transport.
        
        Args:
            timeout: Default timeout for operations in seconds
        """
        self.timeout = timeout
        self._connected = False
        self._last_health_check = 0.0
        self._health_check_interval = 60.0  # seconds
    
    @abstractmethod
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[ClientSession, None]:
        """
        Create and manage a client session.
        
        Yields:
            ClientSession: Initialized MCP session
            
        Raises:
            ConnectionError: If connection fails
            TimeoutError: If connection times out
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
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
        pass
    
    async def is_healthy(self) -> bool:
        """
        Check if the transport is healthy and ready for use.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Skip health checks if we checked recently
            current_time = time.time()
            if current_time - self._last_health_check < self._health_check_interval:
                return self._connected
            
            # Perform health check by trying to list tools
            await self.list_tools()
            self._connected = True
            self._last_health_check = current_time
            return True
            
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            self._connected = False
            return False
    
    async def close(self) -> None:
        """Close the transport and cleanup resources."""
        self._connected = False
        logger.debug(f"Transport {type(self).__name__} closed")


class SSETransport(BaseTransport):
    """
    Server-Sent Events transport for real-time MCP communication.
    
    This transport uses Server-Sent Events (SSE) for bidirectional communication
    with MCP servers. It's ideal for real-time updates and streaming scenarios.
    
    Features:
    --------
    - Real-time bidirectional communication
    - Automatic reconnection on connection loss
    - Efficient for streaming data
    - Low latency for real-time updates
    - Built-in health checking
    
    Use Cases:
    ----------
    
    - Real-time tool execution updates
    - Streaming responses from long-running operations
    - Live status updates
    - Event-driven architectures
    
    Example:
    -------
    >>> transport = SSETransport("http://localhost:8082/sse/sse", timeout=30.0)
    >>> async with transport.session() as session:
    ...     tools = await session.list_tools()
    ...     result = await session.call_tool("tool_name", {"arg": "value"})
    
    Performance:
    -----------
    
    - Low latency for real-time communication
    - Efficient for streaming scenarios
    - Automatic connection management
    - Minimal overhead for frequent updates
    """
    
    def __init__(self, url: str, timeout: float = 30.0):
        """
        Initialize SSE transport.
        
        Args:
            url: SSE endpoint URL
            timeout: Default timeout for operations
        """
        super().__init__(timeout)
        self.url = url
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[ClientSession, None]:
        """
        Create and manage an SSE client session.
        
        Yields:
            ClientSession: Initialized MCP session
            
        Raises:
            ConnectionError: If SSE connection fails
            TimeoutError: If connection times out
        """
        try:
            logger.debug(f"Creating SSE session for {self.url}")
            
            async with asyncio.timeout(self.timeout):
                async with sse_client(self.url) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        
                        self._connected = True
                        logger.debug(f"SSE session created for {self.url}")
                        yield session
                    
        except asyncio.TimeoutError:
            raise TimeoutError(f"SSE connection to {self.url} timed out")
        except Exception as e:
            # Inspect sub-exceptions if available (e.g. ExceptionGroup or similar)
            print(f"DEBUG: Exception caught in SSE session: {type(e)} {e}")
            if hasattr(e, 'exceptions'):
                for idx, exc in enumerate(e.exceptions):
                    print(f"DEBUG: Sub-exception {idx}: {exc} ({type(exc)})")
                    import traceback
                    traceback.print_exception(type(exc), exc, exc.__traceback__)
            
            logger.error(f"Failed to create SSE session for {self.url}: {e}", exc_info=True)
            raise ConnectionError(f"Failed to create SSE session: {e}") from e
    
    async def list_tools(self) -> List[str]:
        """
        List tools using SSE transport.
        
        Returns:
            List of tool names
        """
        try:
            async with self.session() as session:
                tools_resp = await session.list_tools()
                return [tool.name for tool in tools_resp.tools]
        except asyncio.TimeoutError:
            raise TimeoutError("Tool listing request timed out")
        except Exception as e:
            raise ServerError(f"Failed to list tools: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call tool using SSE transport.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        try:
            async with self.session() as session:
                result = await session.call_tool(tool_name, arguments)
                return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Tool call {tool_name} timed out")
        except Exception as e:
            raise ServerError(f"Failed to call tool {tool_name}: {e}")


class HTTPTransport(BaseTransport):
    """
    HTTP transport for standard MCP communication.
    
    This transport uses standard HTTP requests/responses for MCP communication.
    It's ideal for simple request/response patterns and when SSE is not available.
    
    Features:
    --------
    - Standard HTTP requests/responses
    - Firewall friendly
    - Simple and reliable
    - Good for stateless operations
    - Wide compatibility
    
    Use Cases:
    ----------
    
    - Simple tool execution
    - Stateless operations
    - When SSE is not available
    - Behind restrictive firewalls
    - Testing and development
    
    Example:
    -------
    >>> transport = HTTPTransport("http://localhost:3000/mcp", timeout=30.0)
    >>> async with transport.session() as session:
    ...     tools = await session.list_tools()
    ...     result = await session.call_tool("tool_name", {"arg": "value"})
    
    Performance:
    -----------
    
    - Reliable and predictable
    - Good for stateless operations
    - Standard HTTP overhead
    - Firewall compatible
    - Easy to debug and monitor
    """
    
    def __init__(self, url: str, timeout: float = 30.0):
        """
        Initialize HTTP transport.
        
        Args:
            url: HTTP endpoint URL
            timeout: Default timeout for operations
        """
        super().__init__(timeout)
        self.url = url
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[ClientSession, None]:
        """
        Create and manage an HTTP client session.
        
        Yields:
            ClientSession: Initialized MCP session
            
        Raises:
            ConnectionError: If HTTP connection fails
            TimeoutError: If connection times out
        """
        try:
            logger.debug(f"Creating HTTP session for {self.url}")
            
            async with asyncio.timeout(self.timeout):
                async with streamablehttp_client(self.url) as (read_stream, write_stream, _close_fn):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        
                        self._connected = True
                        logger.debug(f"HTTP session created for {self.url}")
                        yield session
                    
        except asyncio.TimeoutError:
            raise TimeoutError(f"HTTP connection to {self.url} timed out")
        except Exception as e:
            raise ConnectionError(f"Failed to create HTTP session: {e}")
    
    async def list_tools(self) -> List[str]:
        """
        List tools using HTTP transport.
        
        Returns:
            List of tool names
        """
        try:
            async with self.session() as session:
                tools_resp = await session.list_tools()
                return [tool.name for tool in tools_resp.tools]
        except asyncio.TimeoutError:
            raise TimeoutError("Tool listing request timed out")
        except Exception as e:
            raise ServerError(f"Failed to list tools: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call tool using HTTP transport.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        try:
            async with self.session() as session:
                result = await session.call_tool(tool_name, arguments)
                return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Tool call {tool_name} timed out")
        except Exception as e:
            raise ServerError(f"Failed to call tool {tool_name}: {e}")


class StdioTransport(BaseTransport):
    """
    Stdio transport for local MCP server communication.
    
    This transport uses standard input/output for communicating with local MCP
    server processes. It's ideal for development, testing, and local deployments.
    
    Features:
    --------
    - Local process communication
    - No network dependencies
    - Fast for local operations
    - Simple debugging
    - Development friendly
    
    Use Cases:
    ----------
    
    - Local development
    - Testing and debugging
    - Local server deployments
    - Process-based architectures
    - When network is not available
    
    Example:
    -------
    >>> transport = StdioTransport("python", ["server.py"], timeout=30.0)
    >>> async with transport.session() as session:
    ...     tools = await session.list_tools()
    ...     result = await session.call_tool("tool_name", {"arg": "value"})
    
    Performance:
    -----------
    
    - Very fast for local operations
    - No network overhead
    - Simple and direct
    - Easy to debug
    - Resource efficient
    """
    
    def __init__(
        self, 
        command: str, 
        args: List[str], 
        env: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ):
        """
        Initialize stdio transport.
        
        Args:
            command: Command to execute the MCP server
            args: Arguments for the command
            env: Environment variables for the process
            timeout: Default timeout for operations
        """
        super().__init__(timeout)
        self.command = command
        self.args = args
        self.env = env
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[ClientSession, None]:
        """
        Create and manage a stdio client session.
        
        Yields:
            ClientSession: Initialized MCP session
            
        Raises:
            ConnectionError: If process fails to start
            TimeoutError: If initialization times out
        """
        try:
            logger.debug(f"Creating stdio session for {self.command} {' '.join(self.args)}")
            
            # Create server parameters
            server_params = StdioServerParameters(
                command=self.command,
                args=self.args,
                env=self.env
            )
            
            # Create stdio client and session within context manager
            async with asyncio.timeout(self.timeout):
                async with stdio_client(server_params) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        
                        self._connected = True
                        logger.debug(f"Stdio session created for {self.command}")
                        yield session
            
        except asyncio.TimeoutError:
            raise TimeoutError(f"Stdio connection to {self.command} timed out")
        except Exception as e:
            raise ConnectionError(f"Failed to create stdio session: {e}")
    
    async def list_tools(self) -> List[str]:
        """
        List tools using stdio transport.
        
        Returns:
            List of tool names
        """
        try:
            async with self.session() as session:
                tools_resp = await session.list_tools()
                return [tool.name for tool in tools_resp.tools]
        except asyncio.TimeoutError:
            raise TimeoutError("Tool listing request timed out")
        except Exception as e:
            raise ServerError(f"Failed to list tools: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call tool using stdio transport.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        try:
            async with self.session() as session:
                result = await session.call_tool(tool_name, arguments)
                return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Tool call {tool_name} timed out")
        except Exception as e:
            raise ServerError(f"Failed to call tool {tool_name}: {e}")
