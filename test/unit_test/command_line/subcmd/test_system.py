"""Unit tests for system commands."""

from unittest.mock import patch

from typer.testing import CliRunner

from gearmeshing_ai.command_line.subcmd.system import app

runner = CliRunner()


class TestSystemCommands:
    """Test system utility commands."""

    def test_system_info(self) -> None:
        """Test system info command."""
        with patch("gearmeshing_ai.command_line.subcmd.system.logger") as mock_logger:
            result = runner.invoke(app, ["info"])
            assert result.exit_code == 0
            assert "System Information:" in result.stdout
            mock_logger.info.assert_called_with("Displaying system information")

    def test_system_check(self) -> None:
        """Test system check command."""
        with patch("gearmeshing_ai.command_line.subcmd.system.logger") as mock_logger:
            result = runner.invoke(app, ["check"])
            assert result.exit_code == 0
            assert "System Health Checks:" in result.stdout
            mock_logger.info.assert_called_with("Running system health checks")

    def test_system_config_show_only(self) -> None:
        """Test system config command with show only."""
        with patch("gearmeshing_ai.command_line.subcmd.system.logger") as mock_logger:
            result = runner.invoke(app, ["config"])
            assert result.exit_code == 0
            assert "Current Configuration:" in result.stdout
            assert "Configuration display functionality to be implemented" in result.stdout
            mock_logger.info.assert_called_with("Managing configuration (show: True, validate: False)")

    def test_system_config_validate_only(self) -> None:
        """Test system config command with validate only."""
        with patch("gearmeshing_ai.command_line.subcmd.system.logger") as mock_logger:
            result = runner.invoke(app, ["config", "--validate", "--no-show"])
            assert result.exit_code == 0
            assert "Configuration Validation:" in result.stdout
            assert "Configuration validation functionality to be implemented" in result.stdout
            mock_logger.info.assert_called_with("Managing configuration (show: False, validate: True)")

    def test_system_config_both(self) -> None:
        """Test system config command with both show and validate."""
        with patch("gearmeshing_ai.command_line.subcmd.system.logger") as mock_logger:
            result = runner.invoke(app, ["config", "--validate"])
            assert result.exit_code == 0
            assert "Current Configuration:" in result.stdout
            assert "Configuration Validation:" in result.stdout
            mock_logger.info.assert_called_with("Managing configuration (show: True, validate: True)")

    def test_system_config_with_file(self) -> None:
        """Test system config command with config file."""
        with patch("gearmeshing_ai.command_line.subcmd.system.logger") as mock_logger:
            result = runner.invoke(app, ["config", "--config", "/path/to/config.yaml"])
            assert result.exit_code == 0
            assert "Current Configuration:" in result.stdout
            mock_logger.info.assert_called_with("Managing configuration (show: True, validate: False)")

    def test_system_logs_default(self) -> None:
        """Test system logs command with default parameters."""
        with patch("gearmeshing_ai.command_line.subcmd.system.logger") as mock_logger:
            result = runner.invoke(app, ["logs"])
            assert result.exit_code == 0
            assert "System Logs:" in result.stdout
            assert "Component: all" in result.stdout
            assert "Follow: False" in result.stdout
            assert "Lines: 50" in result.stdout
            assert "Level: INFO" in result.stdout
            mock_logger.info.assert_called_with("Viewing system logs (component: None, follow: False)")

    def test_system_logs_custom(self) -> None:
        """Test system logs command with custom parameters."""
        with patch("gearmeshing_ai.command_line.subcmd.system.logger") as mock_logger:
            result = runner.invoke(
                app, ["logs", "--component", "server", "--follow", "--lines", "100", "--level", "DEBUG"]
            )
            assert result.exit_code == 0
            assert "Component: server" in result.stdout
            assert "Follow: True" in result.stdout
            assert "Lines: 100" in result.stdout
            assert "Level: DEBUG" in result.stdout
            mock_logger.info.assert_called_with("Viewing system logs (component: server, follow: True)")

    def test_system_cleanup_dry_run(self) -> None:
        """Test system cleanup command with dry run."""
        with patch("gearmeshing_ai.command_line.subcmd.system.logger") as mock_logger:
            result = runner.invoke(app, ["cleanup", "--dry-run"])
            assert result.exit_code == 0
            assert "System Cleanup:" in result.stdout
            assert "Dry run: True" in result.stdout
            assert "Force: False" in result.stdout
            mock_logger.info.assert_called_with("Running cleanup (dry_run: True, force: False)")

    def test_system_cleanup_force(self) -> None:
        """Test system cleanup command with force flag."""
        with patch("gearmeshing_ai.command_line.subcmd.system.logger") as mock_logger:
            result = runner.invoke(app, ["cleanup", "--force"])
            assert result.exit_code == 0
            assert "System Cleanup:" in result.stdout
            assert "Dry run: False" in result.stdout
            assert "Force: True" in result.stdout
            mock_logger.info.assert_called_with("Running cleanup (dry_run: False, force: True)")

    def test_system_cleanup_with_confirmation(self) -> None:
        """Test system cleanup command with confirmation."""
        with (
            patch("gearmeshing_ai.command_line.subcmd.system.logger") as mock_logger,
            patch("typer.confirm", return_value=True),
        ):
            result = runner.invoke(app, ["cleanup"])
            assert result.exit_code == 0
            assert "System Cleanup:" in result.stdout
            assert "Dry run: False" in result.stdout
            assert "Force: False" in result.stdout
            mock_logger.info.assert_called_with("Running cleanup (dry_run: False, force: False)")

    def test_system_cleanup_cancelled(self) -> None:
        """Test system cleanup command when cancelled."""
        with patch("typer.confirm", return_value=False):
            result = runner.invoke(app, ["cleanup"], catch_exceptions=False)
            assert result.exit_code == 0
            assert "Operation cancelled" in result.stdout

    def test_system_monitor(self) -> None:
        """Test system monitor command."""
        with patch("gearmeshing_ai.command_line.subcmd.system.logger") as mock_logger:
            result = runner.invoke(app, ["monitor"])
            assert result.exit_code == 0
            assert "System Monitor:" in result.stdout
            mock_logger.info.assert_called_with("Starting system monitor")

    def test_system_version(self) -> None:
        """Test system version command."""
        with patch("gearmeshing_ai.command_line.subcmd.system.logger") as mock_logger:
            result = runner.invoke(app, ["version"])
            assert result.exit_code == 0
            assert "GearMeshing-AI Version:" in result.stdout
            mock_logger.info.assert_called_with("Displaying version information")
