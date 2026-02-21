"""End-to-end tests for scheduler configuration."""

import pytest
from pathlib import Path

from gearmeshing_ai.scheduler.config.settings import SchedulerSettings


class TestConfigE2E:
    """End-to-end tests for scheduler configuration."""

    def test_complete_scheduler_configuration_workflow(self):
        """Test complete scheduler configuration workflow."""
        # Create production configuration
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
            log_file_dir=Path("/var/log/scheduler"),
            database_pool_size=10,
            redis_max_connections=20,
            enable_authentication=True
        )
        
        # Verify complete configuration
        assert settings.name == "production-scheduler"
        assert settings.environment == "production"
        assert settings.temporal_worker_count == 4
        assert settings.monitoring_max_concurrent_checks == 20
        assert settings.api_host == "0.0.0.0"
        assert settings.log_format == "json"
        assert settings.enable_authentication is True

    def test_development_vs_production_configuration(self):
        """Test development vs production configuration differences."""
        # Development configuration
        dev_config = SchedulerSettings(
            environment="development",
            debug=True,
            log_level="DEBUG",
            temporal_worker_count=1,
            monitoring_interval_seconds=60,
            enable_authentication=False
        )
        
        # Production configuration
        prod_config = SchedulerSettings(
            environment="production",
            debug=False,
            log_level="WARNING",
            temporal_worker_count=4,
            monitoring_interval_seconds=300,
            enable_authentication=True
        )
        
        # Verify differences
        assert dev_config.debug is True
        assert prod_config.debug is False
        assert dev_config.log_level == "DEBUG"
        assert prod_config.log_level == "WARNING"
        assert dev_config.temporal_worker_count == 1
        assert prod_config.temporal_worker_count == 4

    def test_scheduler_configuration_with_external_services(self):
        """Test scheduler configuration with external services."""
        settings = SchedulerSettings(
            temporal_host="temporal.example.com",
            temporal_port=7233,
            api_host="api.example.com",
            api_port=8080,
            database_pool_size=20,
            redis_max_connections=30,
            mcp_gateway_url="https://mcp-gateway.example.com",
            clickup_api_token=None,  # Would be set from env
            slack_bot_token=None,  # Would be set from env
            openai_api_key=None  # Would be set from env
        )
        
        # Verify external service configuration
        assert settings.temporal_host == "temporal.example.com"
        assert settings.api_host == "api.example.com"
        assert settings.database_pool_size == 20
        assert settings.redis_max_connections == 30
        assert settings.mcp_gateway_url == "https://mcp-gateway.example.com"

    def test_scheduler_configuration_with_monitoring(self):
        """Test scheduler configuration with comprehensive monitoring."""
        settings = SchedulerSettings(
            monitoring_enabled=True,
            monitoring_interval_seconds=300,
            monitoring_max_concurrent_checks=20,
            monitoring_check_timeout_seconds=60,
            enable_metrics=True,
            metrics_port=9090,
            enable_health_checks=True,
            health_check_interval_seconds=30,
            log_level="INFO",
            log_format="json",
            enable_file_logging=True,
            log_file_dir=Path("/var/log/scheduler")
        )
        
        # Verify monitoring configuration
        assert settings.monitoring_enabled is True
        assert settings.monitoring_interval_seconds == 300
        assert settings.enable_metrics is True
        assert settings.enable_health_checks is True
        assert settings.log_format == "json"

    def test_scheduler_configuration_scalability(self):
        """Test scheduler configuration for scalability."""
        # Small deployment
        small_config = SchedulerSettings(
            temporal_worker_count=1,
            monitoring_max_concurrent_checks=5,
            database_pool_size=5,
            redis_max_connections=10
        )
        
        # Large deployment
        large_config = SchedulerSettings(
            temporal_worker_count=10,
            monitoring_max_concurrent_checks=100,
            database_pool_size=50,
            redis_max_connections=100
        )
        
        # Verify scalability differences
        assert small_config.temporal_worker_count < large_config.temporal_worker_count
        assert small_config.monitoring_max_concurrent_checks < large_config.monitoring_max_concurrent_checks
        assert small_config.database_pool_size < large_config.database_pool_size

    def test_scheduler_configuration_logging_strategies(self):
        """Test different logging strategies."""
        # Console-only logging
        console_config = SchedulerSettings(
            log_level="INFO",
            log_format="simple",
            enable_file_logging=False
        )
        
        # File-based logging
        file_config = SchedulerSettings(
            log_level="DEBUG",
            log_format="json",
            enable_file_logging=True,
            log_file_dir=Path("/var/log/scheduler")
        )
        
        # Verify logging strategies
        assert console_config.enable_file_logging is False
        assert file_config.enable_file_logging is True
        assert file_config.log_file_dir == Path("/var/log/scheduler")

    def test_scheduler_configuration_temporal_settings(self):
        """Test Temporal-specific configuration."""
        settings = SchedulerSettings(
            temporal_host="temporal.example.com",
            temporal_port=7233,
            temporal_namespace="production",
            temporal_task_queue="prod-tasks",
            temporal_worker_count=4
        )
        
        # Verify Temporal configuration
        assert settings.temporal_host == "temporal.example.com"
        assert settings.temporal_port == 7233
        assert settings.temporal_namespace == "production"
        assert settings.temporal_task_queue == "prod-tasks"
        assert settings.temporal_worker_count == 4

    def test_scheduler_configuration_api_settings(self):
        """Test API-specific configuration."""
        settings = SchedulerSettings(
            api_host="0.0.0.0",
            api_port=8080,
            enable_api=True,
            enable_metrics=True,
            metrics_port=9090,
            enable_authentication=True
        )
        
        # Verify API configuration
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8080
        assert settings.enable_api is True
        assert settings.metrics_port == 9090
        assert settings.enable_authentication is True

    def test_scheduler_configuration_persistence(self):
        """Test scheduler configuration persistence."""
        # Create configuration
        settings = SchedulerSettings(
            name="persistent-scheduler",
            environment="production",
            temporal_host="temporal.example.com",
            config_file=Path("/etc/scheduler/config.yaml")
        )
        
        # Verify configuration can be retrieved
        assert settings.name == "persistent-scheduler"
        assert settings.config_file == Path("/etc/scheduler/config.yaml")

    def test_scheduler_configuration_validation_and_defaults(self):
        """Test configuration validation and defaults."""
        # Minimal configuration
        minimal_config = SchedulerSettings()
        
        # Verify defaults are applied
        assert minimal_config.name == "gearmeshing-scheduler"
        assert minimal_config.environment == "development"
        assert minimal_config.temporal_host == "localhost"
        assert minimal_config.monitoring_enabled is True
        assert minimal_config.enable_api is True

    def test_scheduler_configuration_for_different_deployment_scenarios(self):
        """Test configuration for different deployment scenarios."""
        # Local development
        local_config = SchedulerSettings(
            environment="development",
            temporal_host="localhost",
            api_host="localhost",
            api_port=8000,
            debug=True
        )
        
        # Docker deployment
        docker_config = SchedulerSettings(
            environment="staging",
            temporal_host="temporal",
            api_host="0.0.0.0",
            api_port=8080,
            debug=False
        )
        
        # Kubernetes deployment
        k8s_config = SchedulerSettings(
            environment="production",
            temporal_host="temporal.scheduler.svc.cluster.local",
            api_host="0.0.0.0",
            api_port=8080,
            temporal_worker_count=4,
            enable_metrics=True,
            enable_health_checks=True
        )
        
        # Verify deployment-specific configurations
        assert local_config.temporal_host == "localhost"
        assert docker_config.temporal_host == "temporal"
        assert k8s_config.temporal_host == "temporal.scheduler.svc.cluster.local"
