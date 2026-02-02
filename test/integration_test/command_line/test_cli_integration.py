"""Integration tests for CLI functionality."""

import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from gearmeshing_ai.command_line.app import app

runner = CliRunner()


class TestCLIIntegration:
    """Integration tests for the complete CLI system."""

    def test_cli_help_hierarchy(self) -> None:
        """Test that the CLI help hierarchy works correctly."""
        # Test main app help
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "agent" in result.stdout
        assert "server" in result.stdout
        assert "system" in result.stdout

        # Test agent subcommand help
        result = runner.invoke(app, ["agent", "--help"])
        assert result.exit_code == 0
        assert "list" in result.stdout
        assert "create" in result.stdout
        assert "run" in result.stdout
        assert "stop" in result.stdout
        assert "status" in result.stdout
        assert "delete" in result.stdout

        # Test server subcommand help
        result = runner.invoke(app, ["server", "--help"])
        assert result.exit_code == 0
        assert "start" in result.stdout
        assert "stop" in result.stdout
        assert "status" in result.stdout
        assert "restart" in result.stdout
        assert "logs" in result.stdout
        assert "health" in result.stdout

        # Test system subcommand help
        result = runner.invoke(app, ["system", "--help"])
        assert result.exit_code == 0
        assert "info" in result.stdout
        assert "check" in result.stdout
        assert "config" in result.stdout
        assert "logs" in result.stdout
        assert "cleanup" in result.stdout
        assert "monitor" in result.stdout
        assert "version" in result.stdout

    def test_cli_command_execution_flow(self) -> None:
        """Test that commands can be executed in sequence."""
        # Test that multiple commands can be called without errors
        commands = [
            ["agent", "list"],
            ["server", "status"],
            ["system", "info"],
        ]

        for cmd in commands:
            result = runner.invoke(app, cmd)
            assert result.exit_code == 0

    def test_cli_error_handling(self) -> None:
        """Test CLI error handling for invalid commands."""
        # Test invalid subcommand
        result = runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0

        # Test invalid option
        result = runner.invoke(app, ["--invalid-option"])
        assert result.exit_code != 0

        # Test missing required argument
        result = runner.invoke(app, ["agent", "create"])
        assert result.exit_code != 0

    def test_cli_flag_combinations(self) -> None:
        """Test various flag combinations."""
        # Test verbose with subcommands
        result = runner.invoke(app, ["--verbose", "agent", "list"])
        assert result.exit_code == 0

        # Test quiet with subcommands
        result = runner.invoke(app, ["--quiet", "server", "status"])
        assert result.exit_code == 0

        # Test config with subcommands
        result = runner.invoke(app, ["--config", "/tmp/test-config", "system", "info"])
        assert result.exit_code == 0

    def test_cli_file_operations(self) -> None:
        """Test CLI operations involving files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test agent create with config file
            config_file = temp_path / "test-config.yaml"
            config_file.write_text("test: config")

            result = runner.invoke(app, ["agent", "create", "test-agent", "--config", str(config_file)])
            assert result.exit_code == 0
            assert str(config_file) in result.stdout

            # Test agent run with input file
            input_file = temp_path / "input.txt"
            input_file.write_text("test input")

            result = runner.invoke(app, ["agent", "run", "test-agent", "--file", str(input_file)])
            assert result.exit_code == 0
            assert str(input_file) in result.stdout

    def test_cli_confirmation_prompts(self) -> None:
        """Test CLI confirmation prompts."""
        # Test agent delete without confirmation (should show prompt)
        result = runner.invoke(app, ["agent", "delete", "test-agent"], input="n\n")
        assert result.exit_code == 0
        assert "Operation cancelled" in result.stdout

        # Test agent delete with confirmation
        result = runner.invoke(app, ["agent", "delete", "test-agent"], input="y\n")
        assert result.exit_code == 0
        assert "Deleting agent: test-agent" in result.stdout

        # Test agent delete with force flag (no prompt)
        result = runner.invoke(app, ["agent", "delete", "test-agent", "--confirm"])
        assert result.exit_code == 0
        assert "Deleting agent: test-agent" in result.stdout

        # Test system cleanup without confirmation (should show prompt)
        result = runner.invoke(app, ["system", "cleanup"], input="n\n")
        assert result.exit_code == 0
        assert "Operation cancelled" in result.stdout

        # Test system cleanup with confirmation
        result = runner.invoke(app, ["system", "cleanup"], input="y\n")
        assert result.exit_code == 0
        assert "System Cleanup:" in result.stdout

    def test_cli_parameter_validation(self) -> None:
        """Test CLI parameter validation."""
        # Test invalid port number (Typer validates types automatically)
        result = runner.invoke(app, ["server", "start", "--port", "invalid"])
        assert result.exit_code != 0

        # Test negative limit (should work as validation is not implemented yet)
        result = runner.invoke(app, ["agent", "list", "--limit", "-1"])
        assert result.exit_code == 0

        # Test missing required argument (should fail)
        result = runner.invoke(app, ["agent", "create"])
        assert result.exit_code != 0


class TestCLIRealExecution:
    """Test CLI execution through subprocess for more realistic testing."""

    def test_cli_as_module(self) -> None:
        """Test running CLI as a Python module."""
        # This test requires the package to be installed
        # For now, we'll skip it as it's not essential for basic functionality
        pytest.skip("CLI module execution test requires package installation")

    def test_cli_entry_point(self) -> None:
        """Test CLI entry point functionality."""
        # Test that the main function can be imported and called
        from gearmeshing_ai.command_line import main

        # We can't actually call main() as it would start the CLI
        # But we can verify it's importable and the right type
        assert callable(main)
