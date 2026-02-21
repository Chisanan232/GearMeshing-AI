"""Unit tests for scheduler settings."""

import pytest
from pathlib import Path
from unittest.mock import patch

from gearmeshing_ai.scheduler.config.settings import SchedulerSettings


class TestSchedulerSettings:
    """Test SchedulerSettings class."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = SchedulerSettings()
        assert settings.name == "gearmeshing-scheduler"
        assert settings.environment == "development"
        assert settings.debug is False
        assert settings.temporal_host == "localhost"
        assert settings.temporal_port == 7233
        assert settings.temporal_namespace == "default"
        assert settings.temporal_task_queue == "scheduler-tasks"

    def test_monitoring_settings(self):
        """Test monitoring configuration settings."""
        settings = SchedulerSettings()
        assert settings.monitoring_enabled is True
        assert settings.monitoring_interval_seconds == 300
        assert settings.monitoring_max_concurrent_checks == 10
        assert settings.monitoring_check_timeout_seconds == 60

    def test_api_settings(self):
        """Test API configuration settings."""
        settings = SchedulerSettings()
        assert settings.api_host == "localhost"
        assert settings.api_port == 8080
        assert settings.enable_api is True

    def test_metrics_settings(self):
        """Test metrics configuration settings."""
        settings = SchedulerSettings()
        assert settings.enable_metrics is True
        assert settings.metrics_port == 9090

    def test_health_check_settings(self):
        """Test health check configuration settings."""
        settings = SchedulerSettings()
        assert settings.enable_health_checks is True
        assert settings.health_check_interval_seconds == 30

    def test_logging_settings(self):
        """Test logging configuration settings."""
        settings = SchedulerSettings()
        assert settings.log_level == "INFO"
        assert settings.log_format == "detailed"
        assert settings.enable_file_logging is True

    def test_database_settings(self):
        """Test database configuration settings."""
        settings = SchedulerSettings()
        assert settings.database_pool_size == 5

    def test_redis_settings(self):
        """Test Redis configuration settings."""
        settings = SchedulerSettings()
        assert settings.redis_max_connections == 10

    def test_temporal_worker_count_validation(self):
        """Test temporal_worker_count validation."""
        # Valid values
        settings = SchedulerSettings(temporal_worker_count=1)
        assert settings.temporal_worker_count == 1
        
        settings = SchedulerSettings(temporal_worker_count=10)
        assert settings.temporal_worker_count == 10

    def test_monitoring_interval_validation(self):
        """Test monitoring_interval_seconds validation."""
        # Valid value
        settings = SchedulerSettings(monitoring_interval_seconds=60)
        assert settings.monitoring_interval_seconds == 60

    def test_monitoring_max_concurrent_checks_validation(self):
        """Test monitoring_max_concurrent_checks validation."""
        # Valid value
        settings = SchedulerSettings(monitoring_max_concurrent_checks=5)
        assert settings.monitoring_max_concurrent_checks == 5

    def test_custom_settings(self):
        """Test creating settings with custom values."""
        settings = SchedulerSettings(
            name="custom-scheduler",
            environment="production",
            debug=True,
            temporal_host="temporal.example.com",
            temporal_port=7234,
            monitoring_interval_seconds=600
        )
        
        assert settings.name == "custom-scheduler"
        assert settings.environment == "production"
        assert settings.debug is True
        assert settings.temporal_host == "temporal.example.com"
        assert settings.temporal_port == 7234
        assert settings.monitoring_interval_seconds == 600

    def test_secret_fields_are_secret_str(self):
        """Test that secret fields are SecretStr type."""
        settings = SchedulerSettings()
        # Secret fields should be optional and None by default
        assert settings.secret_key is None
        assert settings.database_url is None
        assert settings.redis_url is None

    def test_authentication_settings(self):
        """Test authentication configuration."""
        settings = SchedulerSettings()
        assert settings.enable_authentication is False

    def test_mcp_gateway_settings(self):
        """Test MCP Gateway configuration."""
        settings = SchedulerSettings()
        assert settings.mcp_gateway_url is None
        assert settings.mcp_gateway_token is None

    def test_external_service_settings(self):
        """Test external service configuration."""
        settings = SchedulerSettings()
        assert settings.clickup_api_token is None
        assert settings.slack_bot_token is None
        assert settings.slack_user_token is None

    def test_ai_provider_settings(self):
        """Test AI provider configuration."""
        settings = SchedulerSettings()
        assert settings.openai_api_key is None
        assert settings.anthropic_api_key is None
        assert settings.google_api_key is None

    def test_config_file_setting(self):
        """Test config file setting."""
        settings = SchedulerSettings()
        assert settings.config_file is None
        
        # Test with custom config file
        settings = SchedulerSettings(config_file=Path("/path/to/config.yaml"))
        assert settings.config_file == Path("/path/to/config.yaml")

    def test_log_file_dir_setting(self):
        """Test log file directory setting."""
        settings = SchedulerSettings()
        assert settings.log_file_dir is None
        
        # Test with custom log file dir
        settings = SchedulerSettings(log_file_dir=Path("/var/log/scheduler"))
        assert settings.log_file_dir == Path("/var/log/scheduler")

    def test_get_scheduler_config(self):
        """Test get_scheduler_config method."""
        settings = SchedulerSettings()
        # Method should exist and be callable
        assert callable(settings.get_scheduler_config)
