"""Integration tests for scheduler configuration."""

import pytest
from pathlib import Path

from gearmeshing_ai.scheduler.config.settings import SchedulerSettings


class TestConfigIntegration:
    """Integration tests for scheduler configuration."""

    def test_scheduler_settings_with_all_components(self):
        """Test scheduler settings with all components configured."""
        settings = SchedulerSettings(
            name="production-scheduler",
            environment="production",
            debug=False,
            temporal_host="temporal.prod.example.com",
            temporal_port=7233,
            temporal_namespace="production",
            temporal_task_queue="prod-scheduler-tasks",
            temporal_worker_count=4,
            monitoring_enabled=True,
            monitoring_interval_seconds=300,
            monitoring_max_concurrent_checks=20,
            monitoring_check_timeout_seconds=60,
            api_host="0.0.0.0",
            api_port=8080,
            enable_api=True,
            enable_metrics=True,
            metrics_port=9090,
            enable_health_checks=True,
            health_check_interval_seconds=30,
            log_level="INFO",
            log_format="json",
            enable_file_logging=True,
            database_pool_size=10,
            redis_max_connections=20
        )
        
        # Verify all settings
        assert settings.name == "production-scheduler"
        assert settings.environment == "production"
        assert settings.temporal_worker_count == 4
        assert settings.monitoring_max_concurrent_checks == 20
        assert settings.log_format == "json"

    def test_scheduler_settings_defaults(self):
        """Test scheduler settings with default values."""
        settings = SchedulerSettings()
        
        # Verify defaults
        assert settings.name == "gearmeshing-scheduler"
        assert settings.environment == "development"
        assert settings.debug is False
        assert settings.temporal_host == "localhost"
        assert settings.monitoring_enabled is True
        assert settings.enable_api is True

    def test_scheduler_settings_environment_specific(self):
        """Test environment-specific settings."""
        # Development settings
        dev_settings = SchedulerSettings(
            environment="development",
            debug=True,
            log_level="DEBUG"
        )
        assert dev_settings.debug is True
        assert dev_settings.log_level == "DEBUG"
        
        # Production settings
        prod_settings = SchedulerSettings(
            environment="production",
            debug=False,
            log_level="WARNING"
        )
        assert prod_settings.debug is False
        assert prod_settings.log_level == "WARNING"

    def test_scheduler_settings_temporal_configuration(self):
        """Test Temporal-specific configuration."""
        settings = SchedulerSettings(
            temporal_host="temporal.example.com",
            temporal_port=7234,
            temporal_namespace="custom",
            temporal_task_queue="custom-queue",
            temporal_worker_count=5
        )
        
        assert settings.temporal_host == "temporal.example.com"
        assert settings.temporal_port == 7234
        assert settings.temporal_namespace == "custom"
        assert settings.temporal_task_queue == "custom-queue"
        assert settings.temporal_worker_count == 5

    def test_scheduler_settings_monitoring_configuration(self):
        """Test monitoring-specific configuration."""
        settings = SchedulerSettings(
            monitoring_enabled=True,
            monitoring_interval_seconds=600,
            monitoring_max_concurrent_checks=50,
            monitoring_check_timeout_seconds=120
        )
        
        assert settings.monitoring_enabled is True
        assert settings.monitoring_interval_seconds == 600
        assert settings.monitoring_max_concurrent_checks == 50
        assert settings.monitoring_check_timeout_seconds == 120

    def test_scheduler_settings_api_configuration(self):
        """Test API-specific configuration."""
        settings = SchedulerSettings(
            api_host="0.0.0.0",
            api_port=8000,
            enable_api=True,
            enable_metrics=True,
            metrics_port=9000
        )
        
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000
        assert settings.enable_api is True
        assert settings.metrics_port == 9000

    def test_scheduler_settings_logging_configuration(self):
        """Test logging-specific configuration."""
        settings = SchedulerSettings(
            log_level="DEBUG",
            log_format="json",
            enable_file_logging=True,
            log_file_dir=Path("/var/log/scheduler")
        )
        
        assert settings.log_level == "DEBUG"
        assert settings.log_format == "json"
        assert settings.enable_file_logging is True
        assert settings.log_file_dir == Path("/var/log/scheduler")

    def test_scheduler_settings_database_configuration(self):
        """Test database-specific configuration."""
        settings = SchedulerSettings(
            database_pool_size=20,
            redis_max_connections=30
        )
        
        assert settings.database_pool_size == 20
        assert settings.redis_max_connections == 30

    def test_scheduler_settings_validation(self):
        """Test scheduler settings validation."""
        # Valid settings
        valid_settings = SchedulerSettings(
            temporal_worker_count=5,
            monitoring_interval_seconds=300,
            monitoring_max_concurrent_checks=10
        )
        assert valid_settings.temporal_worker_count == 5
        
        # Settings with constraints
        settings = SchedulerSettings(
            temporal_worker_count=1,  # Minimum
            monitoring_interval_seconds=10  # Minimum
        )
        assert settings.temporal_worker_count == 1
        assert settings.monitoring_interval_seconds == 10

    def test_scheduler_settings_health_check_configuration(self):
        """Test health check configuration."""
        settings = SchedulerSettings(
            enable_health_checks=True,
            health_check_interval_seconds=60
        )
        
        assert settings.enable_health_checks is True
        assert settings.health_check_interval_seconds == 60

    def test_scheduler_settings_security_configuration(self):
        """Test security configuration."""
        settings = SchedulerSettings(
            enable_authentication=True
        )
        
        assert settings.enable_authentication is True

    def test_scheduler_settings_config_file(self):
        """Test config file setting."""
        settings = SchedulerSettings(
            config_file=Path("/etc/scheduler/config.yaml")
        )
        
        assert settings.config_file == Path("/etc/scheduler/config.yaml")

    def test_scheduler_settings_get_scheduler_config(self):
        """Test get_scheduler_config method."""
        settings = SchedulerSettings()
        
        # Method should be callable
        assert callable(settings.get_scheduler_config)
