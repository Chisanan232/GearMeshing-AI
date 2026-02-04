"""Test configuration and fixtures for CLI integration tests."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture  # type: ignore[misc]
def temp_config_file() -> Path:
    """Create a temporary configuration file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""
# Test configuration
server:
  host: "127.0.0.1"
  port: 9000

agents:
  default_model: "gpt-4"
  timeout: 30

logging:
  level: "DEBUG"
  format: "detailed"
""")
        return Path(f.name)


@pytest.fixture  # type: ignore[misc]
def mock_agent_service() -> Mock:
    """Mock agent service for testing."""
    mock = Mock()
    mock.list_agents.return_value = []
    mock.create_agent.return_value = {"id": "test-agent", "status": "created"}
    mock.get_agent_status.return_value = {"id": "test-agent", "status": "running"}
    mock.run_agent.return_value = {"id": "test-agent", "result": "success"}
    mock.stop_agent.return_value = {"id": "test-agent", "status": "stopped"}
    mock.delete_agent.return_value = {"id": "test-agent", "status": "deleted"}
    return mock


@pytest.fixture  # type: ignore[misc]
def mock_server_service() -> Mock:
    """Mock server service for testing."""
    mock = Mock()
    mock.start_server.return_value = {"status": "started", "port": 8000}
    mock.stop_server.return_value = {"status": "stopped"}
    mock.get_server_status.return_value = {"status": "running", "uptime": "5m"}
    mock.restart_server.return_value = {"status": "restarted"}
    mock.get_health.return_value = {"status": "healthy", "checks": []}
    return mock


@pytest.fixture  # type: ignore[misc]
def mock_system_service() -> Mock:
    """Mock system service for testing."""
    mock = Mock()
    mock.get_system_info.return_value = {"version": "1.0.0", "platform": "linux"}
    mock.run_health_checks.return_value = {"status": "healthy", "checks": []}
    mock.get_config.return_value = {"server": {"port": 8000}}
    mock.validate_config.return_value = {"valid": True, "errors": []}
    mock.cleanup_resources.return_value = {"cleaned": 10, "errors": []}
    mock.monitor_system.return_value = {"cpu": "50%", "memory": "60%"}
    return mock
