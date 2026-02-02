"""Unit tests for agent commands."""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch

from gearmeshing_ai.command_line.subcmd.agent import app

runner = CliRunner()


class TestAgentCommands:
    """Test agent management commands."""

    def test_agent_list_default(self) -> None:
        """Test agent list command with default parameters."""
        with patch("gearmeshing_ai.command_line.subcmd.agent.logger") as mock_logger:
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            assert "Agent List:" in result.stdout
            assert "Status filter: all" in result.stdout
            assert "Limit: 10" in result.stdout
            mock_logger.info.assert_called_with("Listing agents with status filter: None, limit: 10")

    def test_agent_list_with_filters(self) -> None:
        """Test agent list command with filters."""
        with patch("gearmeshing_ai.command_line.subcmd.agent.logger") as mock_logger:
            result = runner.invoke(app, ["list", "--status", "running", "--limit", "5"])
            assert result.exit_code == 0
            assert "Status filter: running" in result.stdout
            assert "Limit: 5" in result.stdout
            mock_logger.info.assert_called_with("Listing agents with status filter: running, limit: 5")

    def test_agent_create_minimal(self) -> None:
        """Test agent create command with minimal parameters."""
        with patch("gearmeshing_ai.command_line.subcmd.agent.logger") as mock_logger:
            result = runner.invoke(app, ["create", "test-agent"])
            assert result.exit_code == 0
            assert "Creating agent: test-agent" in result.stdout
            assert "Model: gpt-4" in result.stdout
            assert "Description: No description" in result.stdout
            mock_logger.info.assert_called_with("Creating agent: test-agent with model: gpt-4")

    def test_agent_create_full(self) -> None:
        """Test agent create command with all parameters."""
        with patch("gearmeshing_ai.command_line.subcmd.agent.logger") as mock_logger:
            result = runner.invoke(app, [
                "create", "test-agent",
                "--model", "gpt-3.5-turbo",
                "--description", "Test agent for unit testing",
                "--config", "/path/to/config.yaml"
            ])
            assert result.exit_code == 0
            assert "Creating agent: test-agent" in result.stdout
            assert "Model: gpt-3.5-turbo" in result.stdout
            assert "Description: Test agent for unit testing" in result.stdout
            assert "Config file: /path/to/config.yaml" in result.stdout
            mock_logger.info.assert_called_with("Creating agent: test-agent with model: gpt-3.5-turbo")

    def test_agent_run_with_input(self) -> None:
        """Test agent run command with input text."""
        with patch("gearmeshing_ai.command_line.subcmd.agent.logger") as mock_logger:
            result = runner.invoke(app, ["run", "test-agent", "--input", "Hello, world!"])
            assert result.exit_code == 0
            assert "Running agent: test-agent" in result.stdout
            assert "Input: Hello, world!" in result.stdout
            mock_logger.info.assert_called_with("Running agent: test-agent")

    def test_agent_run_with_file(self) -> None:
        """Test agent run command with input file."""
        with patch("gearmeshing_ai.command_line.subcmd.agent.logger") as mock_logger:
            result = runner.invoke(app, ["run", "test-agent", "--file", "/path/to/input.txt"])
            assert result.exit_code == 0
            assert "Running agent: test-agent" in result.stdout
            assert "Input file: /path/to/input.txt" in result.stdout
            mock_logger.info.assert_called_with("Running agent: test-agent")

    def test_agent_run_interactive(self) -> None:
        """Test agent run command in interactive mode."""
        with patch("gearmeshing_ai.command_line.subcmd.agent.logger") as mock_logger:
            result = runner.invoke(app, ["run", "test-agent", "--interactive"])
            assert result.exit_code == 0
            assert "Running agent: test-agent" in result.stdout
            assert "Mode: Interactive" in result.stdout
            mock_logger.info.assert_called_with("Running agent: test-agent")

    def test_agent_run_no_input(self) -> None:
        """Test agent run command with no input (defaults to interactive)."""
        with patch("gearmeshing_ai.command_line.subcmd.agent.logger") as mock_logger:
            result = runner.invoke(app, ["run", "test-agent"])
            assert result.exit_code == 0
            assert "Running agent: test-agent" in result.stdout
            assert "No input provided, using interactive mode" in result.stdout
            mock_logger.info.assert_called_with("Running agent: test-agent")

    def test_agent_stop_default(self) -> None:
        """Test agent stop command."""
        with patch("gearmeshing_ai.command_line.subcmd.agent.logger") as mock_logger:
            result = runner.invoke(app, ["stop", "test-agent"])
            assert result.exit_code == 0
            assert "Stopping agent: test-agent" in result.stdout
            assert "Force: False" in result.stdout
            mock_logger.info.assert_called_with("Stopping agent: test-agent (force: False)")

    def test_agent_stop_force(self) -> None:
        """Test agent stop command with force flag."""
        with patch("gearmeshing_ai.command_line.subcmd.agent.logger") as mock_logger:
            result = runner.invoke(app, ["stop", "test-agent", "--force"])
            assert result.exit_code == 0
            assert "Stopping agent: test-agent" in result.stdout
            assert "Force: True" in result.stdout
            mock_logger.info.assert_called_with("Stopping agent: test-agent (force: True)")

    def test_agent_status_default(self) -> None:
        """Test agent status command."""
        with patch("gearmeshing_ai.command_line.subcmd.agent.logger") as mock_logger:
            result = runner.invoke(app, ["status", "test-agent"])
            assert result.exit_code == 0
            assert "Agent Status: test-agent" in result.stdout
            assert "Detailed: False" in result.stdout
            mock_logger.info.assert_called_with("Getting status for agent: test-agent")

    def test_agent_status_detailed(self) -> None:
        """Test agent status command with detailed flag."""
        with patch("gearmeshing_ai.command_line.subcmd.agent.logger") as mock_logger:
            result = runner.invoke(app, ["status", "test-agent", "--detailed"])
            assert result.exit_code == 0
            assert "Agent Status: test-agent" in result.stdout
            assert "Detailed: True" in result.stdout
            mock_logger.info.assert_called_with("Getting status for agent: test-agent")

    def test_agent_delete_with_confirmation(self) -> None:
        """Test agent delete command with confirmation."""
        with patch("gearmeshing_ai.command_line.subcmd.agent.logger") as mock_logger:
            with patch("typer.confirm", return_value=True):
                result = runner.invoke(app, ["delete", "test-agent"])
                assert result.exit_code == 0
                assert "Deleting agent: test-agent" in result.stdout
                mock_logger.info.assert_called_with("Deleting agent: test-agent")

    def test_agent_delete_cancelled(self) -> None:
        """Test agent delete command when cancelled."""
        with patch("typer.confirm", return_value=False):
            result = runner.invoke(app, ["delete", "test-agent"])
            assert result.exit_code == 0
            assert "Operation cancelled" in result.stdout

    def test_agent_delete_force(self) -> None:
        """Test agent delete command with force flag."""
        with patch("gearmeshing_ai.command_line.subcmd.agent.logger") as mock_logger:
            result = runner.invoke(app, ["delete", "test-agent", "--confirm"])
            assert result.exit_code == 0
            assert "Deleting agent: test-agent" in result.stdout
            mock_logger.info.assert_called_with("Deleting agent: test-agent")
