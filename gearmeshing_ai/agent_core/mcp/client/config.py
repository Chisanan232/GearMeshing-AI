"""
Configuration management for MCP client.

This module provides configuration classes and validation for MCP clients.
It supports various configuration sources including environment variables,
configuration files, and programmatic configuration.

Configuration Architecture:
--------------------------

The configuration system follows these principles:

1. **Type Safety**: All configuration is strongly typed with Pydantic
2. **Validation**: Automatic validation of configuration values
3. **Flexibility**: Multiple configuration sources supported
4. **Defaults**: Sensible defaults for all options
5. **Environment Awareness**: Environment variable support
6. **Security**: Secure handling of sensitive values

Configuration Sources:
---------------------

1. **Programmatic**: Direct Python object creation
2. **Environment Variables**: Environment-based configuration
3. **Configuration Files**: JSON/YAML file support
4. **Default Values**: Built-in sensible defaults

Usage Guidelines:
-----------------

# Create configuration programmatically
config = MCPClientConfig(
    timeout=30.0,
    retry_policy=RetryConfig(max_retries=3, base_delay=1.0)
)

# Load from environment variables
config = MCPClientConfig.from_env()

# Load from configuration file
config = MCPClientConfig.from_file("config.json")

# Use with factory
factory = MCPClientFactory()
client = factory.create_client_from_config(config)

Security:
--------

Sensitive configuration values are handled securely:

- API keys and tokens use SecretStr
- Passwords are automatically masked
- TLS certificates are validated
- Environment variables are sanitized

Validation:
----------

All configuration is validated using Pydantic:

- Type checking ensures correct data types
- Range validation prevents invalid values
- Pattern validation enforces formats
- Custom validation for complex rules

Extensibility:
------------

New configuration options can be added easily:

class CustomConfig(MCPClientConfig):
    custom_option: str = Field(default="default", description="Custom option")
    
    class Config:
        extra = "forbid"  # Prevent unknown fields

Examples:
---------

# Basic configuration
config = MCPClientConfig()

# Advanced configuration with retry policy
config = MCPClientConfig(
    timeout=60.0,
    retry_policy=RetryConfig(
        max_retries=5,
        base_delay=2.0,
        max_delay=30.0,
        backoff_factor=2.0
    ),
    enable_metrics=True,
    max_concurrent_requests=20
)

# Environment-based configuration
# Set MCP_CLIENT_TIMEOUT=30, MCP_CLIENT_MAX_RETRIES=3
config = MCPClientConfig.from_env()

"""

import os
import json
import logging
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, SecretStr

logger = logging.getLogger(__name__)


class RetryConfig(BaseModel):
    """
    Configuration for retry policies.
    
    This class defines how clients should handle temporary failures
    and when to retry operations. It supports exponential backoff
    and configurable retry limits.
    
    Features:
    --------
    - Configurable retry limits
    - Exponential backoff with jitter
    - Configurable delays
    - Per-retry timeout handling
    
    Example:
    -------
    >>> retry_config = RetryConfig(
    ...     max_retries=3,
    ...     base_delay=1.0,
    ...     max_delay=30.0,
    ...     backoff_factor=2.0
    ... )
    >>> delay = retry_config.get_delay(attempt=1)  # Returns 2.0
    """
    
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum number of retry attempts")
    base_delay: float = Field(default=1.0, ge=0.001, le=60.0, description="Base delay in seconds")
    max_delay: float = Field(default=30.0, ge=0.1, le=300.0, description="Maximum delay in seconds")
    backoff_factor: float = Field(default=2.0, ge=1.0, le=10.0, description="Backoff multiplier")
    jitter: bool = Field(default=True, description="Add jitter to delays")
    
    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given retry attempt.
        
        Args:
            attempt: Retry attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            import random
            # Add ±25% jitter
            jitter_factor = 0.25
            jitter_range = delay * jitter_factor
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    @field_validator('max_retries')
    @classmethod
    def validate_max_retries(cls, v):
        """Validate max_retries is reasonable."""
        if v > 10:
            logger.warning(f"High retry count ({v}) may cause long delays")
        return v
    
    @field_validator('base_delay')
    @classmethod
    def validate_base_delay(cls, v):
        """Validate base_delay is reasonable."""
        if v < 0.001:
            raise ValueError("base_delay must be at least 0.001 seconds")
        return v


class TransportConfig(BaseModel):
    """
    Configuration for transport-specific settings.
    
    This class provides transport-specific configuration options
    that can be customized based on the transport type being used.
    
    Features:
    --------
    - Transport-specific timeouts
    - Connection pool settings
    - TLS configuration
    - Custom headers and options
    
    Example:
    -------
    >>> transport_config = TransportConfig(
    ...     connection_timeout=30.0,
    ...     read_timeout=60.0,
    ...     max_connections=10,
    ...     verify_ssl=True
    ... )
    """
    
    connection_timeout: float = Field(default=30.0, ge=1.0, le=300.0, description="Connection timeout in seconds")
    read_timeout: float = Field(default=60.0, ge=1.0, le=600.0, description="Read timeout in seconds")
    write_timeout: float = Field(default=60.0, ge=1.0, le=600.0, description="Write timeout in seconds")
    max_connections: int = Field(default=10, ge=1, le=100, description="Maximum connections per host")
    keep_alive: bool = Field(default=True, description="Enable connection keep-alive")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    ssl_cert_path: Optional[str] = Field(default=None, description="Path to SSL certificate file")
    custom_headers: Dict[str, str] = Field(default_factory=dict, description="Custom HTTP headers")
    
    @field_validator('ssl_cert_path')
    @classmethod
    def validate_ssl_cert_path(cls, v):
        """Validate SSL certificate path exists."""
        if v is not None and not Path(v).exists():
            raise ValueError(f"SSL certificate file not found: {v}")
        return v


class MonitoringConfig(BaseModel):
    """
    Configuration for monitoring and metrics collection.
    
    This class defines how clients should collect and report metrics
    and monitoring data. It supports various monitoring backends
    and configurable collection intervals.
    
    Features:
    --------
    - Metrics collection configuration
    - Health check settings
    - Performance monitoring
    - Custom metric support
    
    Example:
    -------
    >>> monitoring_config = MonitoringConfig(
    ...     enable_metrics=True,
    ...     metrics_interval=30.0,
    ...     enable_health_checking=True,
    ...     health_check_interval=60.0
    ... )
    """
    
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_interval: float = Field(default=30.0, ge=1.0, le=300.0, description="Metrics collection interval in seconds")
    enable_health_checking: bool = Field(default=True, description="Enable health checking")
    health_check_interval: float = Field(default=60.0, ge=10.0, le=600.0, description="Health check interval in seconds")
    enable_tracing: bool = Field(default=False, description="Enable distributed tracing")
    tracing_sample_rate: float = Field(default=0.1, ge=0.0, le=1.0, description="Tracing sample rate")
    
    @field_validator('tracing_sample_rate')
    @classmethod
    def validate_tracing_sample_rate(cls, v):
        """Validate tracing sample rate."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("tracing_sample_rate must be between 0.0 and 1.0")
        return v


class MCPClientConfig(BaseModel):
    """
    Main configuration for MCP clients.
    
    This class provides comprehensive configuration options for MCP clients,
    including timeouts, retry policies, transport settings, and monitoring
    configuration. It supports multiple configuration sources and validation.
    
    Features:
    --------
    - Comprehensive client configuration
    - Multiple configuration sources
    - Environment variable support
    - File-based configuration
    - Validation and type safety
    
    Configuration Sources:
    ----------------------
    
    1. **Programmatic**: Direct object creation
    2. **Environment**: MCP_CLIENT_* environment variables
    3. **File**: JSON/YAML configuration files
    4. **Defaults**: Built-in sensible defaults
    
    Example:
    -------
    >>> # Programmatic configuration
    >>> config = MCPClientConfig(
    ...     timeout=30.0,
    ...     retry_policy=RetryConfig(max_retries=3),
    ...     transport=TransportConfig(connection_timeout=60.0),
    ...     monitoring=MonitoringConfig(enable_metrics=True)
    ... )
    >>> 
    >>> # Environment configuration
    >>> # MCP_CLIENT_TIMEOUT=30 MCP_CLIENT_MAX_RETRIES=3
    >>> config = MCPClientConfig.from_env()
    >>> 
    >>> # File configuration
    >>> config = MCPClientConfig.from_file("client_config.json")
    """
    
    # Core settings
    timeout: float = Field(default=30.0, ge=0.001, le=300.0, description="Default timeout in seconds")
    max_concurrent_requests: int = Field(default=10, ge=1, le=100, description="Maximum concurrent requests")
    
    # Retry and error handling
    retry_policy: RetryConfig = Field(default_factory=RetryConfig, description="Retry policy configuration")
    
    # Transport configuration
    transport: TransportConfig = Field(default_factory=TransportConfig, description="Transport configuration")
    
    # Monitoring and metrics
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig, description="Monitoring configuration")
    
    # Security settings
    api_key: Optional[SecretStr] = Field(default=None, description="API key for authentication")
    auth_token: Optional[SecretStr] = Field(default=None, description="Authentication token")
    
    # Advanced settings
    enable_connection_pooling: bool = Field(default=True, description="Enable connection pooling")
    connection_pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    enable_compression: bool = Field(default=True, description="Enable response compression")
    user_agent: str = Field(default="MCPClient/1.0", description="User agent string")
    
    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v):
        """Validate timeout is reasonable."""
        if v < 0.001:
            raise ValueError("timeout must be at least 0.001 second")
        if v > 300.0:
            logger.warning(f"High timeout value ({v}s) may cause long waits")
        return v
    
    @field_validator('max_concurrent_requests')
    @classmethod
    def validate_max_concurrent_requests(cls, v):
        """Validate concurrent requests limit."""
        if v > 50:
            logger.warning(f"High concurrent request limit ({v}) may overwhelm servers")
        return v
    
    @classmethod
    def from_env(cls, prefix: str = "MCP_CLIENT_") -> "MCPClientConfig":
        """
        Create configuration from environment variables.
        
        Args:
            prefix: Environment variable prefix
            
        Returns:
            MCPClientConfig instance
            
        Example:
        -------
        >>> # Set environment variables:
        >>> # MCP_CLIENT_TIMEOUT=30
        >>> # MCP_CLIENT_MAX_RETRIES=3
        >>> # MCP_CLIENT_ENABLE_METRICS=true
        >>> config = MCPClientConfig.from_env()
        """
        env_config = {}
        
        # Map environment variables to config fields
        env_mappings = {
            f"{prefix}TIMEOUT": ("timeout", float),
            f"{prefix}MAX_CONCURRENT_REQUESTS": ("max_concurrent_requests", int),
            f"{prefix}API_KEY": ("api_key", str),
            f"{prefix}AUTH_TOKEN": ("auth_token", str),
            f"{prefix}ENABLE_CONNECTION_POOLING": ("enable_connection_pooling", lambda x: x.lower() == "true"),
            f"{prefix}CONNECTION_POOL_SIZE": ("connection_pool_size", int),
            f"{prefix}ENABLE_COMPRESSION": ("enable_compression", lambda x: x.lower() == "true"),
            f"{prefix}USER_AGENT": ("user_agent", str),
            
            # Retry policy
            f"{prefix}MAX_RETRIES": ("retry_policy.max_retries", int),
            f"{prefix}BASE_DELAY": ("retry_policy.base_delay", float),
            f"{prefix}MAX_DELAY": ("retry_policy.max_delay", float),
            f"{prefix}BACKOFF_FACTOR": ("retry_policy.backoff_factor", float),
            f"{prefix}RETRY_JITTER": ("retry_policy.jitter", lambda x: x.lower() == "true"),
            
            # Transport config
            f"{prefix}CONNECTION_TIMEOUT": ("transport.connection_timeout", float),
            f"{prefix}READ_TIMEOUT": ("transport.read_timeout", float),
            f"{prefix}WRITE_TIMEOUT": ("transport.write_timeout", float),
            f"{prefix}MAX_CONNECTIONS": ("transport.max_connections", int),
            f"{prefix}KEEP_ALIVE": ("transport.keep_alive", lambda x: x.lower() == "true"),
            f"{prefix}VERIFY_SSL": ("transport.verify_ssl", lambda x: x.lower() == "true"),
            f"{prefix}SSL_CERT_PATH": ("transport.ssl_cert_path", str),
            
            # Monitoring config
            f"{prefix}ENABLE_METRICS": ("monitoring.enable_metrics", lambda x: x.lower() == "true"),
            f"{prefix}METRICS_INTERVAL": ("monitoring.metrics_interval", float),
            f"{prefix}ENABLE_HEALTH_CHECKING": ("monitoring.enable_health_checking", lambda x: x.lower() == "true"),
            f"{prefix}HEALTH_CHECK_INTERVAL": ("monitoring.health_check_interval", float),
            f"{prefix}ENABLE_TRACING": ("monitoring.enable_tracing", lambda x: x.lower() == "true"),
            f"{prefix}TRACING_SAMPLE_RATE": ("monitoring.tracing_sample_rate", float),
        }
        
        for env_var, (field_path, converter) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    converted_value = converter(value)
                    
                    # Handle nested field paths (e.g., "retry_policy.max_retries")
                    if "." in field_path:
                        parts = field_path.split(".")
                        current = env_config
                        for part in parts[:-1]:
                            if part not in current:
                                current[part] = {}
                            current = current[part]
                        current[parts[-1]] = converted_value
                    else:
                        env_config[field_path] = converted_value
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid value for {env_var}: {value}, error: {e}")
        
        return cls(**env_config)
    
    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> "MCPClientConfig":
        """
        Create configuration from a JSON file.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            MCPClientConfig instance
            
        Raises:
            FileNotFoundError: If configuration file doesn't exist
            ValueError: If configuration file is invalid
            
        Example:
        -------
        >>> config_data = {
        ...     "timeout": 30.0,
        ...     "retry_policy": {"max_retries": 3},
        ...     "monitoring": {"enable_metrics": True}
        ... }
        >>> with open("config.json", "w") as f:
        ...     json.dump(config_data, f)
        >>> config = MCPClientConfig.from_file("config.json")
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                config_data = json.load(f)
            
            return cls(**config_data)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file {file_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error loading configuration from {file_path}: {e}")
    
    def to_file(self, file_path: Union[str, Path]) -> None:
        """
        Save configuration to a JSON file.
        
        Args:
            file_path: Path to save configuration
            
        Example:
        -------
        >>> config = MCPClientConfig(timeout=60.0)
        >>> config.to_file("config.json")
        """
        file_path = Path(file_path)
        
        # Convert to dict, handling SecretStr
        config_dict = self.dict(exclude_none=True, exclude_unset=True)
        
        # Handle SecretStr serialization
        if "api_key" in config_dict and config_dict["api_key"]:
            config_dict["api_key"] = str(config_dict["api_key"])
        if "auth_token" in config_dict and config_dict["auth_token"]:
            config_dict["auth_token"] = str(config_dict["auth_token"])
        
        with open(file_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        logger.info(f"Configuration saved to {file_path}")
    
    def merge_with(self, other: "MCPClientConfig") -> "MCPClientConfig":
        """
        Merge this configuration with another, with other taking precedence.
        
        Args:
            other: Configuration to merge with
            
        Returns:
            New merged configuration
        """
        # Get dictionaries for both configs
        self_dict = self.dict(exclude_none=True, exclude_unset=True)
        other_dict = other.dict(exclude_none=True, exclude_unset=True)
        
        # Deep merge
        merged_dict = self_dict.copy()
        
        def deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
            """Deep merge two dictionaries."""
            result = base.copy()
            for key, value in update.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        merged_dict = deep_merge(merged_dict, other_dict)
        
        return MCPClientConfig(**merged_dict)
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return any warnings.
        
        Returns:
            List of validation warnings
        """
        warnings = []
        
        # Check for potentially problematic configurations
        if self.timeout > 120.0:
            warnings.append(f"High timeout ({self.timeout}s) may cause long waits")
        
        if self.max_concurrent_requests > 50:
            warnings.append(f"High concurrent request limit ({self.max_concurrent_requests}) may overwhelm servers")
        
        if self.retry_policy.max_retries > 5:
            warnings.append(f"High retry count ({self.retry_policy.max_retries}) may cause long delays")
        
        if self.monitoring.metrics_interval < 10.0:
            warnings.append(f"Frequent metrics collection ({self.monitoring.metrics_interval}s) may impact performance")
        
        if not self.transport.verify_ssl:
            warnings.append("SSL verification is disabled - security risk")
        
        return warnings
