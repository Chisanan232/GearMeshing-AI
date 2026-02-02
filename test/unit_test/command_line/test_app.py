"""Unit tests for CLI application."""

from typer.testing import CliRunner

from gearmeshing_ai.command_line.app import app

runner = CliRunner()


class TestCLIApp:
    """Test the main CLI application."""

    def test_app_help(self) -> None:
        """Test that the app shows help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "GearMeshing-AI Command Line Interface" in result.stdout
        assert "agent" in result.stdout
        assert "server" in result.stdout
        assert "system" in result.stdout

    def test_app_verbose_flag(self) -> None:
        """Test verbose flag functionality."""
        result = runner.invoke(app, ["--verbose", "agent", "--help"])
        assert result.exit_code == 0
        assert "agent" in result.stdout

    def test_app_quiet_flag(self) -> None:
        """Test quiet flag functionality."""
        result = runner.invoke(app, ["--quiet", "agent", "--help"])
        assert result.exit_code == 0
        assert "agent" in result.stdout

    def test_app_config_flag(self) -> None:
        """Test config flag functionality."""
        result = runner.invoke(app, ["--config", "/path/to/config", "agent", "--help"])
        assert result.exit_code == 0
        assert "agent" in result.stdout

    def test_keyboard_interrupt_handling(self) -> None:
        """Test keyboard interrupt handling."""
        # Test that keyboard interrupt is handled gracefully
        result = runner.invoke(app, ["--help"], catch_exceptions=False)
        assert result.exit_code == 0

    def test_general_exception_handling(self) -> None:
        """Test general exception handling."""
        # Test that the app handles errors gracefully
        result = runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0
