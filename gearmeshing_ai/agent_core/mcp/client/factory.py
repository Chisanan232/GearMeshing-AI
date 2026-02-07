"""
Factory classes for creating MCP clients.

This module provides factory classes for creating MCP clients with different
configurations and transport types. The factory pattern enables flexible
client creation while maintaining consistency and validation.

Factory Architecture:
---------------------

The factory system follows these principles:

1. **Flexibility**: Create clients from various sources (config, env, files)
2. **Validation**: Ensure all clients are properly configured
3. **Consistency**: Standardized client creation patterns
4. **Extensibility**: Easy to add new client types and configurations
5. **Type Safety**: Full type hints and validation

Factory Types:
--------------

1. **MCPClientFactory** - Main factory for creating MCP clients
2. **EasyMCPClientFactory** - Factory for convenience clients
3. **TransportFactory** - Factory for creating transport instances

Usage Patterns:
---------------

# Create client from configuration
factory = MCPClientFactory()
config = MCPClientConfig(timeout=30.0)
client = factory.create_client_from_config(config)

# Create SSE client directly
client = factory.create_sse_client("http://localhost:8082/sse/sse")

# Create client from environment
client = factory.create_client_from_env()

# Create client from file
client = factory.create_client_from_file("config.json")

Design Benefits:
----------------

1. **Centralized Creation**: All client creation logic in one place
2. **Configuration Validation**: Ensure clients are properly configured
3. **Error Handling**: Consistent error handling across all creation methods
4. **Testing**: Easy to mock and test client creation
5. **Documentation**: Clear patterns for client creation

Extensibility:
------------

Add new factory methods for custom client types:

class CustomMCPClientFactory(MCPClientFactory):
    def create_custom_client(self, custom_config: CustomConfig) -> CustomClient:
        \"\"\"Create custom client with custom configuration.\"\"\"
        # Implementation
        pass

Examples:
---------

# Basic factory usage
factory = MCPClientFactory()
client = factory.create_sse_client("http://localhost:8082/sse/sse")

# Advanced factory with configuration
config = MCPClientConfig(
    timeout=60.0,
    retry_policy=RetryConfig(max_retries=5),
    monitoring=MonitoringConfig(enable_metrics=True)
)
client = factory.create_client_from_config(config)

# Environment-based creation
# Set MCP_CLIENT_TIMEOUT=30, MCP_CLIENT_MAX_RETRIES=3
client = factory.create_client_from_env()

# File-based creation
client = factory.create_client_from_file("client_config.json")

"""

import logging
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from .core import MCPClient, EasyMCPClient, AsyncMCPClient
from .transports import BaseTransport, SSETransport, HTTPTransport, StdioTransport
from .config import MCPClientConfig, TransportConfig
from .exceptions import ConfigurationError, ConnectionError

logger = logging.getLogger(__name__)


class MCPClientFactory:
    """
    Factory for creating MCP clients with various configurations.
    
    This factory provides methods for creating MCP clients from different
    sources including configuration objects, environment variables, and
    configuration files. It ensures proper validation and error handling.
    
    Features:
    --------
    - Multiple client creation methods
    - Configuration validation
    - Environment variable support
    - File-based configuration
    - Transport-specific creation
    - Error handling and logging
    
    Example:
    -------
    >>> factory = MCPClientFactory()
    >>> 
    >>> # Create from configuration
    >>> config = MCPClientConfig(timeout=30.0)
    >>> client = factory.create_client_from_config(config)
    >>> 
    >>> # Create SSE client directly
    >>> client = factory.create_sse_client("http://localhost:8082/sse/sse")
    >>> 
    >>> # Create from environment
    >>> client = factory.create_client_from_env()
    >>> 
    >>> # Create from file
    >>> client = factory.create_client_from_file("config.json")
    """
    
    def __init__(self, default_config: Optional[MCPClientConfig] = None):
        """
        Initialize MCP client factory.
        
        Args:
            default_config: Default configuration for all clients
        """
        self.default_config = default_config or MCPClientConfig()
        logger.debug("MCPClientFactory initialized")
    
    def create_client_from_config(self, config: MCPClientConfig) -> MCPClient:
        """
        Create MCP client from configuration.
        
        Args:
            config: Client configuration
            
        Returns:
            Configured MCP client
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            # Validate configuration
            warnings = config.validate()
            for warning in warnings:
                logger.warning(f"Configuration warning: {warning}")
            
            # Merge with default configuration
            merged_config = self.default_config.merge_with(config)
            
            # Create client
            client = MCPClient(merged_config)
            
            logger.debug(f"Created MCP client from config: {type(client).__name__}")
            return client
            
        except Exception as e:
            raise ConfigurationError(f"Failed to create client from config: {e}")
    
    def create_async_client_from_config(self, config: MCPClientConfig) -> AsyncMCPClient:
        """
        Create async MCP client from configuration.
        
        Args:
            config: Client configuration
            
        Returns:
            Configured AsyncMCPClient
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            # Validate configuration
            warnings = config.validate()
            for warning in warnings:
                logger.warning(f"Configuration warning: {warning}")
            
            # Merge with default configuration
            merged_config = self.default_config.merge_with(config)
            
            # Create async client
            client = AsyncMCPClient(merged_config)
            
            logger.debug(f"Created Async MCP client from config: {type(client).__name__}")
            return client
            
        except Exception as e:
            raise ConfigurationError(f"Failed to create async client from config: {e}")
    
    def create_client_from_env(self, prefix: str = "MCP_CLIENT_") -> MCPClient:
        """
        Create MCP client from environment variables.
        
        Args:
            prefix: Environment variable prefix
            
        Returns:
            Configured MCP client
            
        Raises:
            ConfigurationError: If environment configuration is invalid
        """
        try:
            config = MCPClientConfig.from_env(prefix)
            return self.create_client_from_config(config)
        except Exception as e:
            raise ConfigurationError(f"Failed to create client from environment: {e}")
    
    def create_client_from_file(self, file_path: Union[str, Path]) -> MCPClient:
        """
        Create MCP client from configuration file.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            Configured MCP client
            
        Raises:
            ConfigurationError: If file configuration is invalid
        """
        try:
            config = MCPClientConfig.from_file(file_path)
            return self.create_client_from_config(config)
        except Exception as e:
            raise ConfigurationError(f"Failed to create client from file: {e}")
    
    async def create_sse_client(
        self,
        url: str,
        config: Optional[MCPClientConfig] = None,
        auto_connect: bool = False
    ) -> MCPClient:
        """
        Create SSE-based MCP client.
        
        Args:
            url: SSE endpoint URL
            config: Optional client configuration
            auto_connect: Whether to auto-connect the client
            
        Returns:
            Configured SSE MCP client
            
        Raises:
            ConfigurationError: If configuration is invalid
            ConnectionError: If auto-connect fails
        """
        try:
            # Use provided config or default
            client_config = config or self.default_config
            
            # Create client
            client = MCPClient(client_config)
            
            # Create and set transport
            transport = SSETransport(url, client_config.timeout)
            client.set_transport(transport)
            
            # Auto-connect if requested
            if auto_connect:
                await client.connect(url, "sse")
            
            logger.debug(f"Created SSE client for {url}")
            return client
            
        except Exception as e:
            if isinstance(e, (ConfigurationError, ConnectionError)):
                raise
            raise ConfigurationError(f"Failed to create SSE client: {e}")
    
    async def create_http_client(
        self,
        url: str,
        config: Optional[MCPClientConfig] = None,
        auto_connect: bool = False
    ) -> MCPClient:
        """
        Create HTTP-based MCP client.
        
        Args:
            url: HTTP endpoint URL
            config: Optional client configuration
            auto_connect: Whether to auto-connect the client
            
        Returns:
            Configured HTTP MCP client
            
        Raises:
            ConfigurationError: If configuration is invalid
            ConnectionError: If auto-connect fails
        """
        try:
            # Use provided config or default
            client_config = config or self.default_config
            
            # Create client
            client = MCPClient(client_config)
            
            # Create and set transport
            transport = HTTPTransport(url, client_config.timeout)
            client.set_transport(transport)
            
            # Auto-connect if requested
            if auto_connect:
                await client.connect(url, "http")
            
            logger.debug(f"Created HTTP client for {url}")
            return client
            
        except Exception as e:
            if isinstance(e, (ConfigurationError, ConnectionError)):
                raise
            raise ConfigurationError(f"Failed to create HTTP client: {e}")
    
    async def create_stdio_client(
        self,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        config: Optional[MCPClientConfig] = None,
        auto_connect: bool = False
    ) -> MCPClient:
        """
        Create stdio-based MCP client.
        
        Args:
            command: Command to execute the MCP server
            args: Arguments for the command
            env: Environment variables for the process
            config: Optional client configuration
            auto_connect: Whether to auto-connect the client
            
        Returns:
            Configured stdio MCP client
            
        Raises:
            ConfigurationError: If configuration is invalid
            ConnectionError: If auto-connect fails
        """
        try:
            # Use provided config or default
            client_config = config or self.default_config
            
            # Create client
            client = MCPClient(client_config)
            
            # Create and set transport
            transport = StdioTransport(command, args, env, client_config.timeout)
            client.set_transport(transport)
            
            # Auto-connect if requested
            if auto_connect:
                await client.connect_stdio(command, args, env)
            
            logger.debug(f"Created stdio client for {command} {' '.join(args)}")
            return client
            
        except Exception as e:
            if isinstance(e, (ConfigurationError, ConnectionError)):
                raise
            raise ConfigurationError(f"Failed to create stdio client: {e}")
    
    def create_client_from_dict(self, config_dict: Dict[str, Any]) -> MCPClient:
        """
        Create MCP client from configuration dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            Configured MCP client
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            config = MCPClientConfig(**config_dict)
            return self.create_client_from_config(config)
        except Exception as e:
            raise ConfigurationError(f"Failed to create client from dict: {e}")
    
    def create_transport_from_config(
        self,
        transport_type: str,
        url_or_command: str,
        config: Optional[TransportConfig] = None,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None
    ) -> BaseTransport:
        """
        Create transport from configuration.
        
        Args:
            transport_type: Type of transport ("sse", "http", "stdio")
            url_or_command: URL for SSE/HTTP or command for stdio
            config: Optional transport configuration
            args: Arguments for stdio transport
            env: Environment variables for stdio transport
            
        Returns:
            Configured transport
            
        Raises:
            ConfigurationError: If transport configuration is invalid
        """
        try:
            transport_config = config or TransportConfig()
            
            if transport_type.lower() == "sse":
                return SSETransport(url_or_command, transport_config.connection_timeout)
            elif transport_type.lower() == "http":
                return HTTPTransport(url_or_command, transport_config.connection_timeout)
            elif transport_type.lower() == "stdio":
                if not args:
                    raise ConfigurationError("stdio transport requires args")
                return StdioTransport(url_or_command, args, env, transport_config.connection_timeout)
            else:
                raise ConfigurationError(f"Unsupported transport type: {transport_type}")
                
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(f"Failed to create transport: {e}")


class EasyMCPClientFactory:
    """
    Factory for creating EasyMCPClient instances.
    
    This factory provides convenience methods for creating EasyMCPClient
    instances with different transport types. It's designed for simple
    use cases where the full MCPClient functionality isn't needed.
    
    Features:
    --------
    - Simple client creation
    - Transport-specific methods
    - Minimal configuration
    - Convenience methods
    - Error handling
    
    Example:
    -------
    >>> factory = EasyMCPClientFactory()
    >>> 
    >>> # Create SSE client
    >>> client = factory.create_sse_client("http://localhost:8082/sse/sse")
    >>> 
    >>> # Create HTTP client
    >>> client = factory.create_http_client("http://localhost:3000/mcp")
    >>> 
    >>> # Create stdio client
    >>> client = factory.create_stdio_client("python", ["server.py"])
    """
    
    def __init__(self):
        """Initialize EasyMCPClient factory."""
        logger.debug("EasyMCPClientFactory initialized")
    
    def create_sse_client(self, url: str, timeout: float = 30.0) -> EasyMCPClient:
        """
        Create SSE-based EasyMCPClient.
        
        Args:
            url: SSE endpoint URL
            timeout: Connection timeout in seconds
            
        Returns:
            EasyMCPClient instance
        """
        # EasyMCPClient uses static methods, so we just return the class
        # The actual client creation happens when methods are called
        logger.debug(f"Created EasyMCP SSE client for {url}")
        return EasyMCPClient
    
    def create_http_client(self, url: str, timeout: float = 30.0) -> EasyMCPClient:
        """
        Create HTTP-based EasyMCPClient.
        
        Args:
            url: HTTP endpoint URL
            timeout: Connection timeout in seconds
            
        Returns:
            EasyMCPClient instance
        """
        logger.debug(f"Created EasyMCP HTTP client for {url}")
        return EasyMCPClient
    
    def create_stdio_client(
        self,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ) -> EasyMCPClient:
        """
        Create stdio-based EasyMCPClient.
        
        Args:
            command: Command to execute the MCP server
            args: Arguments for the command
            env: Environment variables for the process
            timeout: Connection timeout in seconds
            
        Returns:
            EasyMCPClient instance
        """
        logger.debug(f"Created EasyMCP stdio client for {command} {' '.join(args)}")
        return EasyMCPClient


class TransportFactory:
    """
    Factory for creating transport instances.
    
    This factory provides methods for creating different transport types
    with proper configuration and validation. It's useful when you need
    work with transports directly without creating a full client.
    
    Features:
    --------
    - Transport creation methods
    - Configuration validation
    - Type safety
    - Error handling
    - Extensibility
    
    Example:
    -------
    >>> factory = TransportFactory()
    >>> 
    >>> # Create SSE transport
    >>> transport = factory.create_sse_transport("http://localhost:8082/sse/sse")
    >>> 
    >>> # Create HTTP transport
    >>> transport = factory.create_http_transport("http://localhost:3000/mcp")
    >>> 
    >>> # Create stdio transport
    >>> transport = factory.create_stdio_transport("python", ["server.py"])
    """
    
    def __init__(self, default_config: Optional[TransportConfig] = None):
        """
        Initialize transport factory.
        
        Args:
            default_config: Default transport configuration
        """
        self.default_config = default_config or TransportConfig()
        logger.debug("TransportFactory initialized")
    
    def create_sse_transport(
        self,
        url: str,
        config: Optional[TransportConfig] = None
    ) -> SSETransport:
        """
        Create SSE transport.
        
        Args:
            url: SSE endpoint URL
            config: Optional transport configuration
            
        Returns:
            Configured SSE transport
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            transport_config = config or self.default_config
            transport = SSETransport(url, transport_config.connection_timeout)
            logger.debug(f"Created SSE transport for {url}")
            return transport
        except Exception as e:
            raise ConfigurationError(f"Failed to create SSE transport: {e}")
    
    def create_http_transport(
        self,
        url: str,
        config: Optional[TransportConfig] = None
    ) -> HTTPTransport:
        """
        Create HTTP transport.
        
        Args:
            url: HTTP endpoint URL
            config: Optional transport configuration
            
        Returns:
            Configured HTTP transport
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            transport_config = config or self.default_config
            transport = HTTPTransport(url, transport_config.connection_timeout)
            logger.debug(f"Created HTTP transport for {url}")
            return transport
        except Exception as e:
            raise ConfigurationError(f"Failed to create HTTP transport: {e}")
    
    def create_stdio_transport(
        self,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        config: Optional[TransportConfig] = None
    ) -> StdioTransport:
        """
        Create stdio transport.
        
        Args:
            command: Command to execute the MCP server
            args: Arguments for the command
            env: Environment variables for the process
            config: Optional transport configuration
            
        Returns:
            Configured stdio transport
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            transport_config = config or self.default_config
            transport = StdioTransport(command, args, env, transport_config.connection_timeout)
            logger.debug(f"Created stdio transport for {command} {' '.join(args)}")
            return transport
        except Exception as e:
            raise ConfigurationError(f"Failed to create stdio transport: {e}")
    
    def create_transport_from_dict(
        self,
        transport_dict: Dict[str, Any]
    ) -> BaseTransport:
        """
        Create transport from configuration dictionary.
        
        Args:
            transport_dict: Transport configuration dictionary
            
        Returns:
            Configured transport
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            transport_type = transport_dict.get("type")
            if not transport_type:
                raise ConfigurationError("Transport type is required")
            
            if transport_type.lower() == "sse":
                url = transport_dict.get("url")
                if not url:
                    raise ConfigurationError("SSE transport requires URL")
                return self.create_sse_transport(url, transport_dict.get("config"))
            
            elif transport_type.lower() == "http":
                url = transport_dict.get("url")
                if not url:
                    raise ConfigurationError("HTTP transport requires URL")
                return self.create_http_transport(url, transport_dict.get("config"))
            
            elif transport_type.lower() == "stdio":
                command = transport_dict.get("command")
                args = transport_dict.get("args", [])
                if not command:
                    raise ConfigurationError("stdio transport requires command")
                return self.create_stdio_transport(
                    command, 
                    args, 
                    transport_dict.get("env"),
                    transport_dict.get("config")
                )
            
            else:
                raise ConfigurationError(f"Unsupported transport type: {transport_type}")
                
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(f"Failed to create transport from dict: {e}")


# Convenience functions for quick client creation
def create_sse_client(url: str, timeout: float = 30.0) -> MCPClient:
    """
    Quick function to create an SSE MCP client.
    
    Args:
        url: SSE endpoint URL
        timeout: Connection timeout in seconds
        
    Returns:
        Configured SSE MCP client
    """
    factory = MCPClientFactory()
    return factory.create_sse_client(url, MCPClientConfig(timeout=timeout))


def create_http_client(url: str, timeout: float = 30.0) -> MCPClient:
    """
    Quick function to create an HTTP MCP client.
    
    Args:
        url: HTTP endpoint URL
        timeout: Connection timeout in seconds
        
    Returns:
        Configured HTTP MCP client
    """
    factory = MCPClientFactory()
    return factory.create_http_client(url, MCPClientConfig(timeout=timeout))


def create_stdio_client(
    command: str,
    args: List[str],
    env: Optional[Dict[str, str]] = None,
    timeout: float = 30.0
) -> MCPClient:
    """
    Quick function to create a stdio MCP client.
    
    Args:
        command: Command to execute the MCP server
        args: Arguments for the command
        env: Environment variables for the process
        timeout: Connection timeout in seconds
        
    Returns:
        Configured stdio MCP client
    """
    factory = MCPClientFactory()
    return factory.create_stdio_client(command, args, env, MCPClientConfig(timeout=timeout))
