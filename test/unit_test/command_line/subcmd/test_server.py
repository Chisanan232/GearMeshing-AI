"""Unit tests for server commands."""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch

from gearmeshing_ai.command_line.commands.server import app

runner = CliRunner()


class TestServerCommands:
    """Test server management commands."""

    def test_server_start_default(self) -> None:
        """Test server start command with default parameters."""
        with patch("gearmeshing_ai.command_line.commands.server.logger") as mock_logger:
            result = runner.invoke(app, ["start"])
            assert result.exit_code == 0
            assert "Starting GearMeshing-AI server:" in result.stdout
            assert "Host: 0.0.0.0" in result.stdout
            assert "Port: 8000" in result.stdout
            assert "Workers: 1" in result.stdout
            assert "Reload: False" in result.stdout
            assert "Config: default" in result.stdout
            mock_logger.info.assert_called_with("Starting server on 0.0.0.0:8000 with 1 workers")

    def test_server_start_custom(self) -> None:
        """Test server start command with custom parameters."""
        with patch("gearmeshing_ai.command_line.commands.server.logger") as mock_logger:
            result = runner.invoke(app, [
                "start",
                "--host", "127.0.0.1",
                "--port", "9000",
                "--workers", "4",
                "--reload",
                "--config", "/path/to/config.yaml"
            ])
            assert result.exit_code == 0
            assert "Host: 127.0.0.1" in result.stdout
            assert "Port: 9000" in result.stdout
            assert "Workers: 4" in result.stdout
            assert "Reload: True" in result.stdout
            assert "Config: /path/to/config.yaml" in result.stdout
            mock_logger.info.assert_called_with("Starting server on 127.0.0.1:9000 with 4 workers")

    def test_server_stop_default(self) -> None:
        """Test server stop command."""
        with patch("gearmeshing_ai.command_line.commands.server.logger") as mock_logger:
            result = runner.invoke(app, ["stop"])
            assert result.exit_code == 0
            assert "Stopping GearMeshing-AI server" in result.stdout
            assert "Force: False" in result.stdout
            mock_logger.info.assert_called_with("Stopping server (force: False)")

    def test_server_stop_force(self) -> None:
        """Test server stop command with force flag."""
        with patch("gearmeshing_ai.command_line.commands.server.logger") as mock_logger:
            result = runner.invoke(app, ["stop", "--force"])
            assert result.exit_code == 0
            assert "Stopping GearMeshing-AI server" in result.stdout
            assert "Force: True" in result.stdout
            mock_logger.info.assert_called_with("Stopping server (force: True)")

    def test_server_status(self) -> None:
        """Test server status command."""
        with patch("gearmeshing_ai.command_line.commands.server.logger") as mock_logger:
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "Server Status:" in result.stdout
            mock_logger.info.assert_called_with("Getting server status")

    def test_server_restart_graceful(self) -> None:
        """Test server restart command with graceful flag."""
        with patch("gearmeshing_ai.command_line.commands.server.logger") as mock_logger:
            result = runner.invoke(app, ["restart", "--graceful"])
            assert result.exit_code == 0
            assert "Restarting GearMeshing-AI server" in result.stdout
            assert "Graceful: True" in result.stdout
            mock_logger.info.assert_called_with("Restarting server (graceful: True)")

    def test_server_restart_force(self) -> None:
        """Test server restart command without graceful flag."""
        with patch("gearmeshing_ai.command_line.commands.server.logger") as mock_logger:
            result = runner.invoke(app, ["restart", "--no-graceful"])
            assert result.exit_code == 0
            assert "Restarting GearMeshing-AI server" in result.stdout
            assert "Graceful: False" in result.stdout
            mock_logger.info.assert_called_with("Restarting server (graceful: False)")

    def test_server_logs_default(self) -> None:
        """Test server logs command with default parameters."""
        with patch("gearmeshing_ai.command_line.commands.server.logger") as mock_logger:
            result = runner.invoke(app, ["logs"])
            assert result.exit_code == 0
            assert "Server Logs:" in result.stdout
            assert "Follow: False" in result.stdout
            assert "Lines: 50" in result.stdout
            assert "Level: INFO" in result.stdout
            mock_logger.info.assert_called_with("Viewing logs (follow: False, lines: 50, level: INFO)")

    def test_server_logs_custom(self) -> None:
        """Test server logs command with custom parameters."""
        with patch("gearmeshing_ai.command_line.commands.server.logger") as mock_logger:
            result = runner.invoke(app, [
                "logs",
                "--follow",
                "--lines", "100",
                "--level", "DEBUG"
            ])
            assert result.exit_code == 0
            assert "Follow: True" in result.stdout
            assert "Lines: 100" in result.stdout
            assert "Level: DEBUG" in result.stdout
            mock_logger.info.assert_called_with("Viewing logs (follow: True, lines: 100, level: DEBUG)")

    def test_server_health(self) -> None:
        """Test server health command."""
        with patch("gearmeshing_ai.command_line.commands.server.logger") as mock_logger:
            result = runner.invoke(app, ["health"])
            assert result.exit_code == 0
            assert "Server Health:" in result.stdout
            mock_logger.info.assert_called_with("Checking server health")
