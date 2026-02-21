"""
Scheduler settings and configuration management.

This module provides the main settings class for the scheduler system,
with support for environment variables and configuration validation.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

from gearmeshing_ai.scheduler.models.config import SchedulerConfig


class SchedulerSettings(BaseSettings):
    """Main settings class for the scheduler system.
    
    This class provides configuration management for the scheduler system,
    with support for environment variables and validation.
    """
    
    model_config = {
        "extra": "ignore",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }
    
    # Basic configuration
    name: str = Field(default="gearmeshing-scheduler", description="Scheduler instance name")
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # Temporal configuration
    temporal_host: str = Field(default="localhost", description="Temporal server host")
    temporal_port: int = Field(default=7233, description="Temporal server port")
    temporal_namespace: str = Field(default="default", description="Temporal namespace")
    temporal_task_queue: str = Field(default="scheduler-tasks", description="Temporal task queue name")
    temporal_worker_count: int = Field(default=1, ge=1, le=10, description="Number of worker processes")
    
    # Monitoring configuration
    monitoring_enabled: bool = Field(default=True, description="Whether monitoring is enabled")
    monitoring_interval_seconds: int = Field(default=300, ge=10, description="Monitoring interval in seconds")
    monitoring_max_concurrent_checks: int = Field(default=10, ge=1, description="Maximum concurrent checking point evaluations")
    monitoring_check_timeout_seconds: int = Field(default=60, ge=5, description="Timeout for individual checking point evaluations")
    
    # Configuration file
    config_file: Optional[Path] = Field(None, description="Path to scheduler configuration file")
    
    # Security configuration
    secret_key: Optional[SecretStr] = Field(None, description="Secret key for authentication and encryption")
    enable_authentication: bool = Field(default=False, description="Enable authentication for API endpoints")
    
    # API configuration
    api_host: str = Field(default="localhost", description="API server host")
    api_port: int = Field(default=8080, description="API server port")
    enable_api: bool = Field(default=True, description="Enable API server")
    
    # Metrics configuration
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(default=9090, description="Metrics server port")
    
    # Health check configuration
    enable_health_checks: bool = Field(default=True, description="Enable health checks")
    health_check_interval_seconds: int = Field(default=30, ge=10, description="Health check interval in seconds")
    
    # Logging configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="detailed", description="Log format: simple, detailed, json")
    enable_file_logging: bool = Field(default=True, description="Enable file logging")
    log_file_dir: Optional[Path] = Field(None, description="Directory for log files")
    
    # Database configuration
    database_url: Optional[SecretStr] = Field(None, description="Database connection URL")
    database_pool_size: int = Field(default=5, ge=1, description="Database connection pool size")
    
    # Redis configuration
    redis_url: Optional[SecretStr] = Field(None, description="Redis connection URL")
    redis_max_connections: int = Field(default=10, ge=1, description="Maximum Redis connections")
    
    # MCP Gateway configuration
    mcp_gateway_url: Optional[str] = Field(None, description="MCP Gateway URL")
    mcp_gateway_token: Optional[SecretStr] = Field(None, description="MCP Gateway authentication token")
    
    # External service configuration
    clickup_api_token: Optional[SecretStr] = Field(None, description="ClickUp API token")
    slack_bot_token: Optional[SecretStr] = Field(None, description="Slack bot token")
    slack_user_token: Optional[SecretStr] = Field(None, description="Slack user token")
    
    # AI provider configuration
    openai_api_key: Optional[SecretStr] = Field(None, description="OpenAI API key")
    anthropic_api_key: Optional[SecretStr] = Field(None, description="Anthropic API key")
    google_api_key: Optional[SecretStr] = Field(None, description="Google AI API key")
    
    def get_scheduler_config(self) -> SchedulerConfig:
        """Get the scheduler configuration model.
        
        Returns:
            SchedulerConfig instance
        """
        from gearmeshing_ai.scheduler.models.config import (
            SchedulerTemporalConfig,
            SchedulerMonitoringConfig,
            SchedulerLoggingConfig,
        )
        
        # Create temporal configuration
        temporal_config = SchedulerTemporalConfig(
            host=self.temporal_host,
            port=self.temporal_port,
            namespace=self.temporal_namespace,
            task_queue=self.temporal_task_queue,
            worker_count=self.temporal_worker_count,
        )
        
        # Create monitoring configuration
        monitoring_config = SchedulerMonitoringConfig(
            enabled=self.monitoring_enabled,
            interval_seconds=self.monitoring_interval_seconds,
            max_concurrent_checks=self.monitoring_max_concurrent_checks,
            check_timeout_seconds=self.monitoring_check_timeout_seconds,
        )
        
        # Create logging configuration
        logging_config = SchedulerLoggingConfig(
            level=self.log_level,
            format=self.log_format,
            enable_file_logging=self.enable_file_logging,
            log_file_dir=self.log_file_dir,
        )
        
        # Create main scheduler configuration
        scheduler_config = SchedulerConfig(
            name=self.name,
            environment=self.environment,
            debug=self.debug,
            temporal=temporal_config,
            monitoring=monitoring_config,
            logging=logging_config,
            secret_key=self.secret_key.get_secret_value() if self.secret_key else None,
            enable_authentication=self.enable_authentication,
            api_host=self.api_host,
            api_port=self.api_port,
            enable_api=self.enable_api,
            enable_metrics=self.enable_metrics,
            metrics_port=self.metrics_port,
            enable_health_checks=self.enable_health_checks,
            health_check_interval_seconds=self.health_check_interval_seconds,
        )
        
        return scheduler_config
    
    def get_database_url(self) -> Optional[str]:
        """Get the database URL.
        
        Returns:
            Database URL or None if not configured
        """
        return self.database_url.get_secret_value() if self.database_url else None
    
    def get_redis_url(self) -> Optional[str]:
        """Get the Redis URL.
        
        Returns:
            Redis URL or None if not configured
        """
        return self.redis_url.get_secret_value() if self.redis_url else None
    
    def get_mcp_gateway_token(self) -> Optional[str]:
        """Get the MCP Gateway token.
        
        Returns:
            MCP Gateway token or None if not configured
        """
        return self.mcp_gateway_token.get_secret_value() if self.mcp_gateway_token else None
    
    def get_clickup_api_token(self) -> Optional[str]:
        """Get the ClickUp API token.
        
        Returns:
            ClickUp API token or None if not configured
        """
        return self.clickup_api_token.get_secret_value() if self.clickup_api_token else None
    
    def get_slack_bot_token(self) -> Optional[str]:
        """Get the Slack bot token.
        
        Returns:
            Slack bot token or None if not configured
        """
        return self.slack_bot_token.get_secret_value() if self.slack_bot_token else None
    
    def get_slack_user_token(self) -> Optional[str]:
        """Get the Slack user token.
        
        Returns:
            Slack user token or None if not configured
        """
        return self.slack_user_token.get_secret_value() if self.slack_user_token else None
    
    def get_openai_api_key(self) -> Optional[str]:
        """Get the OpenAI API key.
        
        Returns:
            OpenAI API key or None if not configured
        """
        return self.openai_api_key.get_secret_value() if self.openai_api_key else None
    
    def get_anthropic_api_key(self) -> Optional[str]:
        """Get the Anthropic API key.
        
        Returns:
            Anthropic API key or None if not configured
        """
        return self.anthropic_api_key.get_secret_value() if self.anthropic_api_key else None
    
    def get_google_api_key(self) -> Optional[str]:
        """Get the Google AI API key.
        
        Returns:
            Google AI API key or None if not configured
        """
        return self.google_api_key.get_secret_value() if self.google_api_key else None
    
    def has_database_config(self) -> bool:
        """Check if database configuration is available.
        
        Returns:
            True if database URL is configured
        """
        return self.database_url is not None
    
    def has_redis_config(self) -> bool:
        """Check if Redis configuration is available.
        
        Returns:
            True if Redis URL is configured
        """
        return self.redis_url is not None
    
    def has_mcp_gateway_config(self) -> bool:
        """Check if MCP Gateway configuration is available.
        
        Returns:
            True if MCP Gateway URL is configured
        """
        return self.mcp_gateway_url is not None
    
    def has_ai_provider_config(self) -> bool:
        """Check if any AI provider configuration is available.
        
        Returns:
            True if any AI provider key is configured
        """
        return any([
            self.openai_api_key,
            self.anthropic_api_key,
            self.google_api_key,
        ])
    
    def get_ai_providers(self) -> Dict[str, bool]:
        """Get available AI providers.
        
        Returns:
            Dictionary mapping provider names to availability
        """
        return {
            "openai": self.openai_api_key is not None,
            "anthropic": self.anthropic_api_key is not None,
            "google": self.google_api_key is not None,
        }
    
    def get_external_services(self) -> Dict[str, bool]:
        """Get available external services.
        
        Returns:
            Dictionary mapping service names to availability
        """
        return {
            "clickup": self.clickup_api_token is not None,
            "slack": self.slack_bot_token is not None or self.slack_user_token is not None,
            "mcp_gateway": self.mcp_gateway_url is not None,
        }
    
    def validate_configuration(self) -> List[str]:
        """Validate the configuration.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate environment
        valid_environments = ["development", "staging", "production", "test"]
        if self.environment.lower() not in valid_environments:
            errors.append(f"Environment must be one of: {valid_environments}")
        
        # Validate ports
        if not (1 <= self.temporal_port <= 65535):
            errors.append("Temporal port must be between 1 and 65535")
        
        if not (1 <= self.api_port <= 65535):
            errors.append("API port must be between 1 and 65535")
        
        if not (1 <= self.metrics_port <= 65535):
            errors.append("Metrics port must be between 1 and 65535")
        
        # Validate intervals
        if self.monitoring_interval_seconds < 10:
            errors.append("Monitoring interval must be at least 10 seconds")
        
        if self.health_check_interval_seconds < 10:
            errors.append("Health check interval must be at least 10 seconds")
        
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            errors.append(f"Log level must be one of: {valid_log_levels}")
        
        # Validate log format
        valid_log_formats = ["simple", "detailed", "json"]
        if self.log_format.lower() not in valid_log_formats:
            errors.append(f"Log format must be one of: {valid_log_formats}")
        
        # Validate worker count
        if not (1 <= self.temporal_worker_count <= 10):
            errors.append("Temporal worker count must be between 1 and 10")
        
        return errors
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the configuration.
        
        Returns:
            Configuration summary
        """
        return {
            "name": self.name,
            "environment": self.environment,
            "debug": self.debug,
            "temporal": {
                "host": self.temporal_host,
                "port": self.temporal_port,
                "namespace": self.temporal_namespace,
                "task_queue": self.temporal_task_queue,
                "worker_count": self.temporal_worker_count,
            },
            "monitoring": {
                "enabled": self.monitoring_enabled,
                "interval_seconds": self.monitoring_interval_seconds,
                "max_concurrent_checks": self.monitoring_max_concurrent_checks,
            },
            "api": {
                "enabled": self.enable_api,
                "host": self.api_host,
                "port": self.api_port,
            },
            "metrics": {
                "enabled": self.enable_metrics,
                "port": self.metrics_port,
            },
            "services": {
                "database": self.has_database_config(),
                "redis": self.has_redis_config(),
                "mcp_gateway": self.has_mcp_gateway_config(),
            },
            "ai_providers": self.get_ai_providers(),
            "external_services": self.get_external_services(),
        }


# Global settings instance
_scheduler_settings_instance: Optional[SchedulerSettings] = None


def get_scheduler_settings() -> SchedulerSettings:
    """Get the global scheduler settings instance.
    
    Returns:
        SchedulerSettings instance
    """
    global _scheduler_settings_instance
    
    if _scheduler_settings_instance is None:
        _scheduler_settings_instance = SchedulerSettings()
        
        # Validate configuration
        errors = _scheduler_settings_instance.validate_configuration()
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    return _scheduler_settings_instance


# Create global instance
scheduler_settings = get_scheduler_settings()
