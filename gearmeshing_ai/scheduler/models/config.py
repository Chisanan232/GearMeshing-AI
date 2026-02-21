"""Configuration models for the scheduler system.

This module contains models for scheduler configuration, monitoring configuration,
and other configuration-related data structures.
"""

from datetime import timedelta
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator

from .base import BaseSchedulerModel


class SchedulerTemporalConfig(BaseSchedulerModel):
    """Configuration for Temporal integration."""

    host: str = Field(default="localhost", description="Temporal server host")
    port: int = Field(default=7233, description="Temporal server port")
    namespace: str = Field(default="default", description="Temporal namespace")
    task_queue: str = Field(default="scheduler-tasks", description="Task queue name")

    # Worker configuration
    worker_count: int = Field(default=1, ge=1, le=10, description="Number of worker processes")

    worker_poll_timeout: timedelta = Field(default=timedelta(seconds=30), description="Worker poll timeout")

    # Client configuration
    client_timeout: timedelta = Field(default=timedelta(seconds=10), description="Client connection timeout")

    # Retry configuration
    max_retry_attempts: int = Field(default=3, ge=0, description="Maximum retry attempts for failed operations")

    retry_initial_interval: timedelta = Field(default=timedelta(seconds=1), description="Initial retry interval")

    retry_maximum_interval: timedelta = Field(default=timedelta(minutes=1), description="Maximum retry interval")


class SchedulerMonitoringConfig(BaseSchedulerModel):
    """Configuration for monitoring settings."""

    # General monitoring settings
    enabled: bool = Field(default=True, description="Whether monitoring is enabled")
    interval_seconds: int = Field(default=300, ge=10, description="Monitoring interval in seconds")

    # Data retention
    data_retention_days: int = Field(default=30, ge=1, description="Number of days to retain monitoring data")

    # Performance settings
    max_concurrent_checks: int = Field(
        default=10, ge=1, description="Maximum number of concurrent checking point evaluations"
    )

    check_timeout_seconds: int = Field(
        default=60, ge=5, description="Timeout for individual checking point evaluations"
    )

    # Error handling
    max_error_rate: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Maximum error rate before stopping monitoring"
    )

    error_cooldown_seconds: int = Field(default=300, ge=60, description="Cooldown period after high error rate")


class SchedulerLoggingConfig(BaseSchedulerModel):
    """Configuration for logging settings."""

    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(default="detailed", description="Log format: simple, detailed, json")

    # File logging
    enable_file_logging: bool = Field(default=True, description="Enable file logging")
    log_file_dir: Path | None = Field(None, description="Directory for log files (default: ./logs)")

    max_file_size_mb: int = Field(default=100, ge=1, description="Maximum log file size in MB")

    backup_count: int = Field(default=5, ge=1, description="Number of backup log files to keep")

    # Structured logging
    enable_structured_logging: bool = Field(default=True, description="Enable structured JSON logging")

    # Module-specific levels
    module_levels: dict[str, str] = Field(default_factory=dict, description="Module-specific logging levels")


class SchedulerConfig(BaseSchedulerModel):
    """Main configuration for the scheduler system."""

    # Basic configuration
    name: str = Field(default="gearmeshing-scheduler", description="Scheduler instance name")
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Temporal configuration
    temporal: SchedulerTemporalConfig = Field(
        default_factory=SchedulerTemporalConfig, description="Temporal integration configuration"
    )

    # Monitoring configuration
    monitoring: SchedulerMonitoringConfig = Field(
        default_factory=SchedulerMonitoringConfig, description="Monitoring configuration"
    )

    # Logging configuration
    logging: SchedulerLoggingConfig = Field(default_factory=SchedulerLoggingConfig, description="Logging configuration")

    # Security configuration
    secret_key: str | None = Field(None, description="Secret key for authentication and encryption")

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

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that scheduler name is not empty."""
        if not v or not v.strip():
            raise ValueError("Scheduler name cannot be empty")
        return v.strip()

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment name."""
        valid_environments = ["development", "staging", "production", "test"]
        if v.lower() not in valid_environments:
            raise ValueError(f"Environment must be one of: {valid_environments}")
        return v.lower()

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of this scheduler configuration.

        Returns:
            Dictionary containing key configuration information

        """
        return {
            "name": self.name,
            "environment": self.environment,
            "debug": self.debug,
            "temporal": {
                "host": self.temporal.host,
                "port": self.temporal.port,
                "namespace": self.temporal.namespace,
                "task_queue": self.temporal.task_queue,
                "worker_count": self.temporal.worker_count,
            },
            "monitoring": {
                "enabled": self.monitoring.enabled,
                "interval_seconds": self.monitoring.interval_seconds,
                "max_concurrent_checks": self.monitoring.max_concurrent_checks,
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
        }


class MonitorConfig(BaseSchedulerModel):
    """Configuration for a specific monitoring workflow.

    This model encapsulates the configuration for running a monitoring workflow,
    including which checking points to use and how often to run.
    """

    # Basic configuration
    name: str = Field(..., description="Name of this monitoring configuration")
    description: str = Field(default="", description="Description of what this monitoring configuration does")

    # Scheduling configuration
    interval_seconds: int = Field(default=300, ge=10, description="Monitoring interval in seconds")

    enabled: bool = Field(default=True, description="Whether this monitoring is enabled")

    # Checking points configuration
    checking_points: list[dict[str, Any]] = Field(
        default_factory=list, description="List of checking point configurations"
    )

    # Data source configuration
    data_sources: list[dict[str, Any]] = Field(default_factory=list, description="List of data source configurations")

    # Execution configuration
    max_concurrent_evaluations: int = Field(default=5, ge=1, description="Maximum number of concurrent evaluations")

    evaluation_timeout_seconds: int = Field(default=120, ge=30, description="Timeout for evaluation in seconds")

    # Error handling
    max_retry_attempts: int = Field(default=3, ge=0, description="Maximum retry attempts for failed evaluations")

    retry_delay_seconds: int = Field(default=60, ge=10, description="Delay between retry attempts in seconds")

    # Notification configuration
    notifications: dict[str, Any] = Field(default_factory=dict, description="Notification configuration")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that monitoring name is not empty."""
        if not v or not v.strip():
            raise ValueError("Monitoring name cannot be empty")
        return v.strip()

    def get_enabled_checking_points(self) -> list[dict[str, Any]]:
        """Get only enabled checking points.

        Returns:
            List of enabled checking point configurations

        """
        return [cp for cp in self.checking_points if cp.get("enabled", False)]

    def get_checking_points_by_type(self, cp_type: str) -> list[dict[str, Any]]:
        """Get checking points of a specific type.

        Args:
            cp_type: Type of checking points to get

        Returns:
            List of checking point configurations of the specified type

        """
        return [cp for cp in self.checking_points if cp.get("type") == cp_type and cp.get("enabled", False)]

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of this monitoring configuration.

        Returns:
            Dictionary containing key configuration information

        """
        return {
            "name": self.name,
            "description": self.description,
            "interval_seconds": self.interval_seconds,
            "enabled": self.enabled,
            "total_checking_points": len(self.checking_points),
            "enabled_checking_points": len(self.get_enabled_checking_points()),
            "data_sources_count": len(self.data_sources),
            "max_concurrent_evaluations": self.max_concurrent_evaluations,
        }
