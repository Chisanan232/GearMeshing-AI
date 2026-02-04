"""End-to-end tests for GearMeshing-AI CLI.

This module contains comprehensive end-to-end tests that verify
complete CLI workflows and real-world usage scenarios.
"""

import re
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from gearmeshing_ai.command_line.app import app, main_entry


def strip_ansi_codes(text: str) -> str:
    """Strip ANSI escape codes from text.

    This is necessary for CI environments where terminal detection
    causes Typer/Click to include color codes in help output.
    """
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


class TestCLIBasicWorkflows:
    """End-to-end tests for basic CLI workflows."""

    def setup_method(self) -> None:
        """Setup test runner for each test."""
        self.runner = CliRunner()

    def test_cli_help_discovery_workflow(self) -> None:
        """Test complete help discovery workflow for new users."""
        # 1. User discovers the main CLI help
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        clean_stdout = strip_ansi_codes(result.stdout)
        assert "GearMeshing-AI Command Line Interface" in clean_stdout
        assert "agent" in clean_stdout
        assert "server" in clean_stdout
        assert "system" in clean_stdout

        # 2. User discovers agent subcommand help
        result = self.runner.invoke(app, ["agent", "--help"])
        assert result.exit_code == 0
        clean_stdout = strip_ansi_codes(result.stdout)
        assert "list" in clean_stdout
        assert "create" in clean_stdout
        assert "run" in clean_stdout
        assert "stop" in clean_stdout
        assert "status" in clean_stdout
        assert "delete" in clean_stdout

        # 3. User discovers specific command help
        result = self.runner.invoke(app, ["agent", "list", "--help"])
        assert result.exit_code == 0
        clean_stdout = strip_ansi_codes(result.stdout)
        assert "--status" in clean_stdout
        assert "--limit" in clean_stdout

    def test_cli_agent_workflow(self) -> None:
        """Test complete agent management workflow."""
        # 1. List agents
        result = self.runner.invoke(app, ["agent", "list"])
        assert result.exit_code == 0
        assert "Agent List" in result.stdout

        # 2. List agents with filters
        result = self.runner.invoke(app, ["agent", "list", "--status", "active", "--limit", "5"])
        assert result.exit_code == 0
        assert "Agent List" in result.stdout

        # 3. Get agent status
        result = self.runner.invoke(app, ["agent", "status", "test-agent"])
        assert result.exit_code == 0
        assert "Agent Status" in result.stdout

        # 4. Get detailed agent status
        result = self.runner.invoke(app, ["agent", "status", "test-agent", "--detailed"])
        assert result.exit_code == 0
        assert "Agent Status" in result.stdout
        assert "Detailed: True" in result.stdout

    def test_cli_agent_creation_workflow(self) -> None:
        """Test agent creation workflow with various options."""
        # 1. Create agent with minimal parameters
        result = self.runner.invoke(app, ["agent", "create", "test-agent"])
        assert result.exit_code == 0
        assert "Creating agent" in result.stdout
        assert "test-agent" in result.stdout

        # 2. Create agent with full parameters
        result = self.runner.invoke(
            app,
            [
                "agent",
                "create",
                "advanced-agent",
                "--model",
                "gpt-4",
                "--description",
                "Test agent",
                "--config",
                "/path/to/config.yml",
            ],
        )
        assert result.exit_code == 0
        assert "Creating agent" in result.stdout
        assert "advanced-agent" in result.stdout
        assert "gpt-4" in result.stdout

    def test_cli_agent_execution_workflow(self) -> None:
        """Test agent execution workflow with different input modes."""
        # 1. Run agent with text input
        result = self.runner.invoke(app, ["agent", "run", "test-agent", "--input", "Hello agent"])
        assert result.exit_code == 0
        assert "Running agent" in result.stdout

        # 2. Run agent with file input
        result = self.runner.invoke(app, ["agent", "run", "test-agent", "--file", "/path/to/input.txt"])
        assert result.exit_code == 0
        assert "Running agent" in result.stdout

        # 3. Run agent in interactive mode
        result = self.runner.invoke(app, ["agent", "run", "test-agent", "--interactive"])
        assert result.exit_code == 0
        assert "Running agent" in result.stdout
        assert "Interactive" in result.stdout

    def test_cli_agent_stop_workflow(self) -> None:
        """Test agent stop workflow."""
        # 1. Stop agent gracefully
        result = self.runner.invoke(app, ["agent", "stop", "test-agent"])
        assert result.exit_code == 0
        assert "Stopping agent" in result.stdout

        # 2. Force stop agent
        result = self.runner.invoke(app, ["agent", "stop", "test-agent", "--force"])
        assert result.exit_code == 0
        assert "Stopping agent" in result.stdout
        assert "Force: True" in result.stdout

    def test_cli_agent_deletion_workflow(self) -> None:
        """Test agent deletion workflow with confirmation."""
        # 1. Delete agent with confirmation (user confirms)
        result = self.runner.invoke(app, ["agent", "delete", "test-agent"], input="y\n")
        assert result.exit_code == 0
        assert "Deleting agent" in result.stdout

        # 2. Delete agent with confirmation (user cancels)
        result = self.runner.invoke(app, ["agent", "delete", "test-agent"], input="n\n")
        assert result.exit_code == 0
        assert "Operation cancelled" in result.stdout

        # 3. Delete agent with force flag (skip confirmation)
        result = self.runner.invoke(app, ["agent", "delete", "test-agent", "--confirm"])
        assert result.exit_code == 0
        assert "Deleting agent" in result.stdout


class TestCLIServerWorkflows:
    """End-to-end tests for server management workflows."""

    def setup_method(self) -> None:
        """Setup test runner for each test."""
        self.runner = CliRunner()

    def test_cli_server_help_discovery(self) -> None:
        """Test server subcommand help discovery."""
        result = self.runner.invoke(app, ["server", "--help"])
        assert result.exit_code == 0
        clean_stdout = strip_ansi_codes(result.stdout)
        assert "start" in clean_stdout
        assert "stop" in clean_stdout
        assert "status" in clean_stdout
        assert "restart" in clean_stdout
        assert "logs" in clean_stdout
        assert "health" in clean_stdout

    def test_cli_server_startup_workflow(self) -> None:
        """Test server startup workflow with various configurations."""
        # 1. Start server with default settings
        result = self.runner.invoke(app, ["server", "start"])
        assert result.exit_code == 0
        assert "GearMeshing-AI server" in result.stdout

        # 2. Start server with custom host and port (explicitly testing all interfaces binding)
        result = self.runner.invoke(app, ["server", "start", "--host", "0.0.0.0", "--port", "9000"])  # noqa: S104
        assert result.exit_code == 0
        assert "GearMeshing-AI server" in result.stdout

        # 3. Start server with workers
        result = self.runner.invoke(app, ["server", "start", "--workers", "4"])
        assert result.exit_code == 0
        assert "GearMeshing-AI server" in result.stdout

        # 4. Start server with reload enabled
        result = self.runner.invoke(app, ["server", "start", "--reload"])
        assert result.exit_code == 0
        assert "GearMeshing-AI server" in result.stdout

    def test_cli_server_management_workflow(self) -> None:
        """Test server management workflow."""
        # 1. Check server status
        result = self.runner.invoke(app, ["server", "status"])
        assert result.exit_code == 0
        assert "Server Status" in result.stdout

        # 2. Stop server
        result = self.runner.invoke(app, ["server", "stop"])
        assert result.exit_code == 0
        assert "GearMeshing-AI server" in result.stdout

        # 3. Stop server with force flag
        result = self.runner.invoke(app, ["server", "stop", "--force"])
        assert result.exit_code == 0
        assert "GearMeshing-AI server" in result.stdout

    def test_cli_server_restart_workflow(self) -> None:
        """Test server restart workflow."""
        # 1. Restart server gracefully (default)
        result = self.runner.invoke(app, ["server", "restart"])
        assert result.exit_code == 0
        assert "GearMeshing-AI server" in result.stdout

        # 2. Restart server without graceful flag
        result = self.runner.invoke(app, ["server", "restart", "--no-graceful"])
        assert result.exit_code == 0
        assert "GearMeshing-AI server" in result.stdout

    def test_cli_server_logs_workflow(self) -> None:
        """Test server logs viewing workflow."""
        # 1. View server logs
        result = self.runner.invoke(app, ["server", "logs"])
        assert result.exit_code == 0
        assert "Server Logs" in result.stdout

        # 2. View server logs with follow flag
        result = self.runner.invoke(app, ["server", "logs", "--follow"])
        assert result.exit_code == 0
        assert "Server Logs" in result.stdout

        # 3. View server logs with custom line count
        result = self.runner.invoke(app, ["server", "logs", "--lines", "50"])
        assert result.exit_code == 0
        assert "Server Logs" in result.stdout

    def test_cli_server_health_check_workflow(self) -> None:
        """Test server health check workflow."""
        # 1. Check server health
        result = self.runner.invoke(app, ["server", "health"])
        assert result.exit_code == 0
        assert "Server Health" in result.stdout


class TestCLISystemWorkflows:
    """End-to-end tests for system utility workflows."""

    def setup_method(self) -> None:
        """Setup test runner for each test."""
        self.runner = CliRunner()

    def test_cli_system_help_discovery(self) -> None:
        """Test system subcommand help discovery."""
        result = self.runner.invoke(app, ["system", "--help"])
        assert result.exit_code == 0
        clean_stdout = strip_ansi_codes(result.stdout)
        assert "info" in clean_stdout
        assert "check" in clean_stdout
        assert "config" in clean_stdout
        assert "logs" in clean_stdout
        assert "cleanup" in clean_stdout
        assert "monitor" in clean_stdout
        assert "version" in clean_stdout

    def test_cli_system_info_workflow(self) -> None:
        """Test system information workflow."""
        result = self.runner.invoke(app, ["system", "info"])
        assert result.exit_code == 0
        assert "System Information" in result.stdout

    def test_cli_system_check_workflow(self) -> None:
        """Test system health check workflow."""
        result = self.runner.invoke(app, ["system", "check"])
        assert result.exit_code == 0
        assert "Health Checks" in result.stdout

    def test_cli_system_config_workflow(self) -> None:
        """Test system configuration workflow."""
        # 1. Show configuration
        result = self.runner.invoke(app, ["system", "config", "--show"])
        assert result.exit_code == 0
        assert "Configuration" in result.stdout

        # 2. Validate configuration
        result = self.runner.invoke(app, ["system", "config", "--validate"])
        assert result.exit_code == 0
        assert "Configuration" in result.stdout

    def test_cli_system_logs_workflow(self) -> None:
        """Test system logs viewing workflow."""
        # 1. View system logs
        result = self.runner.invoke(app, ["system", "logs"])
        assert result.exit_code == 0
        assert "System Logs" in result.stdout

        # 2. View system logs with follow flag
        result = self.runner.invoke(app, ["system", "logs", "--follow"])
        assert result.exit_code == 0
        assert "System Logs" in result.stdout

        # 3. View system logs with custom line count
        result = self.runner.invoke(app, ["system", "logs", "--lines", "100"])
        assert result.exit_code == 0
        assert "System Logs" in result.stdout

    def test_cli_system_cleanup_workflow(self) -> None:
        """Test system cleanup workflow."""
        # 1. Cleanup with dry-run
        result = self.runner.invoke(app, ["system", "cleanup", "--dry-run"])
        assert result.exit_code == 0
        assert "System Cleanup" in result.stdout

        # 2. Cleanup with force flag
        result = self.runner.invoke(app, ["system", "cleanup", "--force"])
        assert result.exit_code == 0
        assert "System Cleanup" in result.stdout

        # 3. Cleanup with confirmation (user confirms)
        result = self.runner.invoke(app, ["system", "cleanup"], input="y\n")
        assert result.exit_code == 0
        assert "System Cleanup" in result.stdout

        # 4. Cleanup with confirmation (user cancels)
        result = self.runner.invoke(app, ["system", "cleanup"], input="n\n")
        assert result.exit_code == 0
        assert "Operation cancelled" in result.stdout

    def test_cli_system_monitor_workflow(self) -> None:
        """Test system monitoring workflow."""
        result = self.runner.invoke(app, ["system", "monitor"])
        assert result.exit_code == 0
        assert "System Monitor" in result.stdout

    def test_cli_system_version_workflow(self) -> None:
        """Test system version workflow."""
        result = self.runner.invoke(app, ["system", "version"])
        assert result.exit_code == 0
        assert "Version" in result.stdout


class TestCLIGlobalOptionsWorkflows:
    """End-to-end tests for global options workflows."""

    def setup_method(self) -> None:
        """Setup test runner for each test."""
        self.runner = CliRunner()

    def test_cli_verbose_flag_workflow(self) -> None:
        """Test verbose flag workflow across different commands."""
        # 1. Agent list with verbose
        result = self.runner.invoke(app, ["--verbose", "agent", "list"])
        assert result.exit_code == 0
        assert "Agent List" in result.stdout

        # 2. Server status with verbose
        result = self.runner.invoke(app, ["--verbose", "server", "status"])
        assert result.exit_code == 0
        assert "Server Status" in result.stdout

        # 3. System info with verbose
        result = self.runner.invoke(app, ["--verbose", "system", "info"])
        assert result.exit_code == 0
        assert "System Information" in result.stdout

    def test_cli_quiet_flag_workflow(self) -> None:
        """Test quiet flag workflow across different commands."""
        # 1. Agent list with quiet
        result = self.runner.invoke(app, ["--quiet", "agent", "list"])
        assert result.exit_code == 0
        assert "Agent List" in result.stdout

        # 2. Server status with quiet
        result = self.runner.invoke(app, ["--quiet", "server", "status"])
        assert result.exit_code == 0
        assert "Server Status" in result.stdout

    def test_cli_config_flag_workflow(self) -> None:
        """Test config flag workflow."""
        # 1. Agent list with config
        result = self.runner.invoke(app, ["--config", "/path/to/config.yml", "agent", "list"])
        assert result.exit_code == 0
        assert "Agent List" in result.stdout

        # 2. Server start with config
        result = self.runner.invoke(app, ["--config", "/path/to/config.yml", "server", "start"])
        assert result.exit_code == 0
        assert "GearMeshing-AI server" in result.stdout

    def test_cli_combined_global_options_workflow(self) -> None:
        """Test combined global options workflow."""
        result = self.runner.invoke(
            app,
            [
                "--verbose",
                "--config",
                "/path/to/config.yml",
                "agent",
                "list",
                "--limit",
                "20",
            ],
        )
        assert result.exit_code == 0
        assert "Agent List" in result.stdout


class TestCLIErrorHandlingWorkflows:
    """End-to-end tests for error handling workflows."""

    def setup_method(self) -> None:
        """Setup test runner for each test."""
        self.runner = CliRunner()

    def test_cli_invalid_command_workflow(self) -> None:
        """Test invalid command error handling."""
        result = self.runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0

    def test_cli_invalid_subcommand_workflow(self) -> None:
        """Test invalid subcommand error handling."""
        result = self.runner.invoke(app, ["agent", "invalid-subcommand"])
        assert result.exit_code != 0

    def test_cli_missing_required_argument_workflow(self) -> None:
        """Test missing required argument error handling."""
        result = self.runner.invoke(app, ["agent", "create"])
        assert result.exit_code != 0

    def test_cli_invalid_option_type_workflow(self) -> None:
        """Test invalid option type error handling."""
        result = self.runner.invoke(app, ["server", "start", "--port", "invalid"])
        assert result.exit_code != 0

    def test_cli_invalid_option_workflow(self) -> None:
        """Test invalid option error handling."""
        result = self.runner.invoke(app, ["agent", "list", "--invalid-option", "value"])
        assert result.exit_code != 0


class TestCLIEntryPointWorkflow:
    """End-to-end tests for CLI entry point."""

    def test_main_entry_function_workflow(self) -> None:
        """Test main_entry function workflow."""
        with patch("gearmeshing_ai.command_line.app.app") as mock_app:
            main_entry()
            mock_app.assert_called_once()

    def test_main_entry_keyboard_interrupt_workflow(self) -> None:
        """Test main_entry handles keyboard interrupt."""
        with patch("gearmeshing_ai.command_line.app.app") as mock_app:
            mock_app.side_effect = KeyboardInterrupt()
            with pytest.raises(typer.Exit):  # typer.Exit raises Exception
                main_entry()

    def test_main_entry_exception_workflow(self) -> None:
        """Test main_entry handles exceptions."""
        with patch("gearmeshing_ai.command_line.app.app") as mock_app:
            mock_app.side_effect = Exception("Test error")
            with pytest.raises(typer.Exit):  # typer.Exit raises Exception
                main_entry()


class TestCLIRealWorldScenarios:
    """End-to-end tests for real-world usage scenarios."""

    def setup_method(self) -> None:
        """Setup test runner for each test."""
        self.runner = CliRunner()

    def test_cli_developer_onboarding_scenario(self) -> None:
        """Test typical developer onboarding scenario."""
        # 1. Developer discovers CLI
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0

        # 2. Developer explores agent management
        result = self.runner.invoke(app, ["agent", "--help"])
        assert result.exit_code == 0

        # 3. Developer lists existing agents
        result = self.runner.invoke(app, ["agent", "list"])
        assert result.exit_code == 0

        # 4. Developer creates a new agent
        result = self.runner.invoke(
            app,
            [
                "agent",
                "create",
                "my-first-agent",
                "--model",
                "gpt-4",
                "--description",
                "My first AI agent",
            ],
        )
        assert result.exit_code == 0

        # 5. Developer checks agent status
        result = self.runner.invoke(app, ["agent", "status", "my-first-agent"])
        assert result.exit_code == 0

    def test_cli_devops_scenario(self) -> None:
        """Test typical DevOps scenario."""
        # 1. DevOps engineer checks system health
        result = self.runner.invoke(app, ["system", "check"])
        assert result.exit_code == 0

        # 2. DevOps engineer starts server (explicitly testing all interfaces binding for production)
        result = self.runner.invoke(app, ["server", "start", "--host", "0.0.0.0", "--port", "8000"])  # noqa: S104
        assert result.exit_code == 0

        # 3. DevOps engineer checks server status
        result = self.runner.invoke(app, ["server", "status"])
        assert result.exit_code == 0

        # 4. DevOps engineer views server health
        result = self.runner.invoke(app, ["server", "health"])
        assert result.exit_code == 0

        # 5. DevOps engineer views system logs
        result = self.runner.invoke(app, ["system", "logs", "--lines", "50"])
        assert result.exit_code == 0

    def test_cli_production_monitoring_scenario(self) -> None:
        """Test typical production monitoring scenario."""
        # 1. Monitor checks system information
        result = self.runner.invoke(app, ["system", "info"])
        assert result.exit_code == 0

        # 2. Monitor checks system health
        result = self.runner.invoke(app, ["system", "check"])
        assert result.exit_code == 0

        # 3. Monitor views system logs with verbose
        result = self.runner.invoke(app, ["--verbose", "system", "logs"])
        assert result.exit_code == 0

        # 4. Monitor checks server health
        result = self.runner.invoke(app, ["server", "health"])
        assert result.exit_code == 0

        # 5. Monitor lists active agents
        result = self.runner.invoke(app, ["agent", "list", "--status", "active"])
        assert result.exit_code == 0
