"""
Exception classes for MCP client.

This module defines the exception hierarchy used by the MCP client package.
It provides specific exception types for different error scenarios and
includes detailed error information for debugging.

Exception Hierarchy:
-------------------

BaseException
└── MCPClientError
    ├── ConnectionError
    │   ├── TimeoutError
    │   ├── AuthenticationError
    │   └── NetworkError
    ├── ServerError
    │   ├── ToolNotFoundError
    │   ├── ToolExecutionError
    │   └── InvalidResponseError
    ├── ConfigurationError
    ├── ValidationError
    └── TransportError

Design Principles:
-----------------

1. **Specificity**: Each error type has a specific exception
2. **Context**: Exceptions include detailed context information
3. **Recoverability**: Distinguish between retryable and non-retryable errors
4. **Debugging**: Include sufficient information for debugging
5. **Consistency**: Consistent error handling patterns

Error Categories:
----------------

1. **Connection Errors**: Problems establishing or maintaining connections
2. **Server Errors**: Errors returned by the MCP server
3. **Configuration Errors**: Invalid or missing configuration
4. **Validation Errors**: Invalid input data or parameters
5. **Transport Errors**: Transport-specific errors

Usage Guidelines:
----------------

# Handle specific exceptions
try:
    await client.call_tool("tool_name", {"arg": "value"})
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    # Retry logic
except ServerError as e:
    logger.error(f"Server error: {e}")
    # Handle server error
except TimeoutError as e:
    logger.error(f"Request timed out: {e}")
    # Timeout handling

# Check error recoverability
if isinstance(error, ConnectionError) and error.is_retryable():
    # Retry the operation
    pass

# Get error context
error_details = {
    "operation": error.operation,
    "server_url": error.server_url,
    "retry_count": error.retry_count,
    "timestamp": error.timestamp
}

Error Attributes:
----------------

All exceptions include these common attributes:

- message: Human-readable error message
- operation: Operation that failed
- server_url: Server URL (if applicable)
- retry_count: Number of retries attempted
- timestamp: When the error occurred
- cause: Original exception (if any)
- context: Additional context information

Custom Exceptions:
-----------------

Create custom exceptions for specific scenarios:

class CustomError(MCPClientError):
    \"\"\"Custom error for specific scenario.\"\"\"
    
    def __init__(self, message: str, custom_field: str, **kwargs):
        super().__init__(message, **kwargs)
        self.custom_field = custom_field

"""

import time
from typing import Any, Dict, List, Optional, Union


class MCPClientError(Exception):
    """
    Base exception for all MCP client errors.
    
    This is the base class for all exceptions raised by the MCP client
    package. It provides common attributes and methods for error handling
    and debugging.
    
    Attributes:
    ----------
    message: Human-readable error message
    operation: Operation that failed (e.g., "list_tools", "call_tool")
    server_url: Server URL (if applicable)
    retry_count: Number of retries attempted
    timestamp: When the error occurred
    cause: Original exception that caused this error
    context: Additional context information
    
    Example:
    -------
    >>> try:
    ...     await client.call_tool("tool_name", {"arg": "value"})
    ... except MCPClientError as e:
    ...     print(f"Error in {e.operation}: {e.message}")
    ...     print(f"Server: {e.server_url}")
    ...     print(f"Retries: {e.retry_count}")
    """
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        server_url: Optional[str] = None,
        retry_count: int = 0,
        cause: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize MCP client error.
        
        Args:
            message: Human-readable error message
            operation: Operation that failed
            server_url: Server URL (if applicable)
            retry_count: Number of retries attempted
            cause: Original exception that caused this error
            context: Additional context information
            **kwargs: Additional keyword arguments
        """
        super().__init__(message)
        self.message = message
        self.operation = operation
        self.server_url = server_url
        self.retry_count = retry_count
        self.timestamp = time.time()
        self.cause = cause
        self.context = context or {}
        
        # Add any additional kwargs to context
        self.context.update(kwargs)
    
    def is_retryable(self) -> bool:
        """
        Check if this error is retryable.
        
        Returns:
            True if the error can be retried, False otherwise
        """
        # Base implementation - subclasses override
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error to dictionary for serialization.
        
        Returns:
            Dictionary representation of the error
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "operation": self.operation,
            "server_url": self.server_url,
            "retry_count": self.retry_count,
            "timestamp": self.timestamp,
            "is_retryable": self.is_retryable(),
            "context": self.context,
        }
    
    def __str__(self) -> str:
        """String representation of the error."""
        parts = [self.message]
        
        if self.operation:
            parts.append(f"operation: {self.operation}")
        
        if self.server_url:
            parts.append(f"server: {self.server_url}")
        
        if self.retry_count > 0:
            parts.append(f"retries: {self.retry_count}")
        
        return " | ".join(parts)


class ConnectionError(MCPClientError):
    """
    Exception for connection-related errors.
    
    This exception is raised when there are problems establishing or
    maintaining connections to MCP servers. It includes network errors,
    authentication errors, and timeout errors.
    
    Connection errors are typically retryable unless they're authentication
    or configuration issues.
    
    Attributes:
    ----------
    error_code: Specific error code from the underlying transport
    connection_state: State of the connection when error occurred
    
    Example:
    -------
    >>> try:
    ...     await client.connect("http://localhost:8082/sse/sse")
    ... except ConnectionError as e:
    ...     if e.is_retryable():
    ...         # Retry the connection
    ...         pass
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        connection_state: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize connection error.
        
        Args:
            message: Human-readable error message
            error_code: Specific error code from transport
            connection_state: State of connection when error occurred
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(message, **kwargs)
        self.error_code = error_code
        self.connection_state = connection_state
    
    def is_retryable(self) -> bool:
        """Check if connection error is retryable."""
        # Authentication and configuration errors are not retryable
        non_retryable_codes = ["AUTH_FAILED", "INVALID_CONFIG", "FORBIDDEN"]
        
        if self.error_code in non_retryable_codes:
            return False
        
        # Other connection errors are generally retryable
        return True


class TimeoutError(ConnectionError):
    """
    Exception for timeout errors.
    
    This exception is raised when operations timeout. Timeout errors
    are generally retryable, but the retry policy should consider
    increasing the timeout for subsequent attempts.
    
    Attributes:
    ----------
    timeout_duration: The timeout that was exceeded
    operation_duration: How long the operation actually took
    
    Example:
    -------
    >>> try:
    ...     await client.call_tool("slow_tool", {}, timeout=30.0)
    ... except TimeoutError as e:
    ...     print(f"Operation timed out after {e.timeout_duration}s")
    ...     # Consider increasing timeout for retry
    """
    
    def __init__(
        self,
        message: str,
        timeout_duration: Optional[float] = None,
        operation_duration: Optional[float] = None,
        **kwargs
    ):
        """
        Initialize timeout error.
        
        Args:
            message: Human-readable error message
            timeout_duration: The timeout that was exceeded
            operation_duration: How long the operation actually took
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(message, **kwargs)
        self.timeout_duration = timeout_duration
        self.operation_duration = operation_duration
    
    def is_retryable(self) -> bool:
        """Timeout errors are generally retryable."""
        return True


class AuthenticationError(ConnectionError):
    """
    Exception for authentication errors.
    
    This exception is raised when authentication fails. Authentication
    errors are not retryable without changing credentials.
    
    Attributes:
    ----------
    auth_method: Authentication method that failed
    auth_details: Additional authentication details (sanitized)
    
    Example:
    -------
    >>> try:
    ...     await client.connect("http://localhost:8082/sse/sse")
    ... except AuthenticationError as e:
    ...     print(f"Authentication failed using {e.auth_method}")
    ...     # Need to update credentials
    """
    
    def __init__(
        self,
        message: str,
        auth_method: Optional[str] = None,
        auth_details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize authentication error.
        
        Args:
            message: Human-readable error message
            auth_method: Authentication method that failed
            auth_details: Additional authentication details (sanitized)
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(message, **kwargs)
        self.auth_method = auth_method
        self.auth_details = auth_details or {}
    
    def is_retryable(self) -> bool:
        """Authentication errors are not retryable without credential changes."""
        return False


class ServerError(MCPClientError):
    """
    Exception for server-side errors.
    
    This exception is raised when the MCP server returns an error response.
    Server errors may or may not be retryable depending on the specific
    error type.
    
    Attributes:
    ----------
    error_code: Server error code
    error_details: Detailed error information from server
    http_status_code: HTTP status code (if applicable)
    
    Example:
    -------
    >>> try:
    ...     await client.call_tool("tool_name", {"arg": "value"})
    ... except ServerError as e:
    ...     print(f"Server error: {e.error_code}")
    ...     if e.is_retryable():
    ...         # Retry the operation
    ...         pass
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        http_status_code: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize server error.
        
        Args:
            message: Human-readable error message
            error_code: Server error code
            error_details: Detailed error information from server
            http_status_code: HTTP status code (if applicable)
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(message, **kwargs)
        self.error_code = error_code
        self.error_details = error_details or {}
        self.http_status_code = http_status_code
    
    def is_retryable(self) -> bool:
        """Check if server error is retryable."""
        # HTTP 5xx errors are generally retryable
        if self.http_status_code and 500 <= self.http_status_code < 600:
            return True
        
        # Specific retryable error codes
        retryable_codes = ["TEMPORARY_FAILURE", "SERVICE_UNAVAILABLE", "RATE_LIMITED"]
        if self.error_code in retryable_codes:
            return True
        
        # Other server errors are generally not retryable
        return False


class ToolNotFoundError(ServerError):
    """
    Exception for when a requested tool is not found.
    
    This exception is raised when the client tries to call a tool that
    doesn't exist on the server. Tool not found errors are not retryable.
    
    Attributes:
    ----------
    tool_name: Name of the tool that was not found
    available_tools: List of available tools (if provided)
    
    Example:
    -------
    >>> try:
    ...     await client.call_tool("nonexistent_tool", {})
    ... except ToolNotFoundError as e:
    ...     print(f"Tool '{e.tool_name}' not found")
    ...     print(f"Available tools: {e.available_tools}")
    """
    
    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        available_tools: Optional[List[str]] = None,
        **kwargs
    ):
        """
        Initialize tool not found error.
        
        Args:
            message: Human-readable error message
            tool_name: Name of the tool that was not found
            available_tools: List of available tools (if provided)
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(message, **kwargs)
        self.tool_name = tool_name
        self.available_tools = available_tools or []
    
    def is_retryable(self) -> bool:
        """Tool not found errors are not retryable."""
        return False


class ToolExecutionError(ServerError):
    """
    Exception for tool execution errors.
    
    This exception is raised when a tool exists but fails to execute
    successfully. Tool execution errors may be retryable depending on
    the specific error.
    
    Attributes:
    ----------
    tool_name: Name of the tool that failed
    execution_details: Details about the execution failure
    
    Example:
    -------
    >>> try:
    ...     await client.call_tool("tool_name", {"arg": "value"})
    ... except ToolExecutionError as e:
    ...     print(f"Tool '{e.tool_name}' execution failed")
    ...     if e.is_retryable():
    ...         # Retry the tool execution
    ...         pass
    """
    
    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        execution_details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize tool execution error.
        
        Args:
            message: Human-readable error message
            tool_name: Name of the tool that failed
            execution_details: Details about the execution failure
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(message, **kwargs)
        self.tool_name = tool_name
        self.execution_details = execution_details or {}
    
    def is_retryable(self) -> bool:
        """Check if tool execution error is retryable."""
        # Check for retryable execution error codes
        retryable_codes = ["TEMPORARY_FAILURE", "RESOURCE_BUSY", "TIMEOUT"]
        if self.error_code in retryable_codes:
            return True
        
        return super().is_retryable()


class ConfigurationError(MCPClientError):
    """
    Exception for configuration errors.
    
    This exception is raised when there are problems with the client
    configuration. Configuration errors are not retryable and must
    be fixed by changing the configuration.
    
    Attributes:
    ----------
    config_field: Configuration field that caused the error
    config_value: The problematic configuration value
    
    Example:
    -------
    >>> try:
    ...     config = MCPClientConfig(timeout=-1)  # Invalid timeout
    ... except ConfigurationError as e:
    ...     print(f"Configuration error in {e.config_field}: {e.message}")
    """
    
    def __init__(
        self,
        message: str,
        config_field: Optional[str] = None,
        config_value: Optional[Any] = None,
        **kwargs
    ):
        """
        Initialize configuration error.
        
        Args:
            message: Human-readable error message
            config_field: Configuration field that caused the error
            config_value: The problematic configuration value
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(message, **kwargs)
        self.config_field = config_field
        self.config_value = config_value
    
    def is_retryable(self) -> bool:
        """Configuration errors are not retryable."""
        return False


class ValidationError(MCPClientError):
    """
    Exception for validation errors.
    
    This exception is raised when input validation fails. Validation
    errors are not retryable and must be fixed by providing valid input.
    
    Attributes:
    ----------
    field: Field that failed validation
    field_value: The problematic field value
    validation_rule: Validation rule that was violated
    
    Example:
    -------
    >>> try:
    ...     await client.call_tool("tool_name", {"invalid_arg": "value"})
    ... except ValidationError as e:
    ...     print(f"Validation failed for field '{e.field}': {e.message}")
    """
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        field_value: Optional[Any] = None,
        validation_rule: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize validation error.
        
        Args:
            message: Human-readable error message
            field: Field that failed validation
            field_value: The problematic field value
            validation_rule: Validation rule that was violated
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(message, **kwargs)
        self.field = field
        self.field_value = field_value
        self.validation_rule = validation_rule
    
    def is_retryable(self) -> bool:
        """Validation errors are not retryable."""
        return False


class TransportError(MCPClientError):
    """
    Exception for transport-specific errors.
    
    This exception is raised when there are problems with the transport
    layer that don't fit into other categories. Transport errors may
    be retryable depending on the specific issue.
    
    Attributes:
    ----------
    transport_type: Type of transport that failed
    transport_details: Transport-specific error details
    
    Example:
    -------
    >>> try:
    ...     await client.connect("http://localhost:8082/sse/sse")
    ... except TransportError as e:
    ...     print(f"Transport error in {e.transport_type}: {e.message}")
    """
    
    def __init__(
        self,
        message: str,
        transport_type: Optional[str] = None,
        transport_details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize transport error.
        
        Args:
            message: Human-readable error message
            transport_type: Type of transport that failed
            transport_details: Transport-specific error details
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(message, **kwargs)
        self.transport_type = transport_type
        self.transport_details = transport_details or {}
    
    def is_retryable(self) -> bool:
        """Check if transport error is retryable."""
        # Most transport errors are retryable unless they're configuration issues
        # Note: TransportError doesn't have error_code attribute, so we check transport_details
        non_retryable_codes = ["INVALID_TRANSPORT_CONFIG", "UNSUPPORTED_TRANSPORT"]
        
        # Check if error code is in transport_details
        error_code = self.transport_details.get("error_code") if self.transport_details else None
        if error_code in non_retryable_codes:
            return False
        
        return True


# Utility functions for error handling
def is_retryable_error(error: Exception) -> bool:
    """
    Check if an error is retryable.
    
    Args:
        error: Exception to check
        
    Returns:
        True if the error is retryable, False otherwise
    """
    if isinstance(error, MCPClientError):
        return error.is_retryable()
    
    # Non-MCP errors are generally retryable if they're connection-related
    retryable_types = (ConnectionRefusedError, TimeoutError, OSError)
    return isinstance(error, retryable_types)


def get_error_context(error: Exception) -> Dict[str, Any]:
    """
    Get context information from an error.
    
    Args:
        error: Exception to extract context from
        
    Returns:
        Dictionary with error context information
    """
    if isinstance(error, MCPClientError):
        return error.to_dict()
    
    return {
        "error_type": type(error).__name__,
        "message": str(error),
        "is_retryable": is_retryable_error(error),
        "timestamp": time.time(),
    }
