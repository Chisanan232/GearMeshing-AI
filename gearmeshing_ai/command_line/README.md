# CLI Usage and Extension Guide

## How to Use the CLI

### Basic Invocation

```bash
# From Python code
from gearmeshing_ai.command_line import main
main()

# Or directly via entry point (once installed)
gearmeshing-ai --help
```

### Global Options

All commands support these global flags:

```bash
gearmeshing-ai --verbose agent list          # Enable debug logging
gearmeshing-ai --quiet agent list            # Suppress non-error output
gearmeshing-ai --config /path/to/config.yml agent list  # Use config file
```

### Available Command Groups

**Agent Management:**
```bash
gearmeshing-ai agent list [--status STATUS] [--limit N]
gearmeshing-ai agent create NAME [--model MODEL] [--description DESC] [--config FILE]
gearmeshing-ai agent run AGENT_ID [--input TEXT] [--file FILE] [--interactive]
gearmeshing-ai agent stop AGENT_ID [--force]
gearmeshing-ai agent status AGENT_ID [--detailed]
gearmeshing-ai agent delete AGENT_ID [--confirm]
```

**Server Management:**
```bash
gearmeshing-ai server start [--host HOST] [--port PORT] [--workers N] [--reload]
gearmeshing-ai server stop [--graceful]
gearmeshing-ai server status
gearmeshing-ai server restart [--graceful] [--force]
gearmeshing-ai server logs [--follow] [--lines N]
gearmeshing-ai server health [--level LEVEL]
```

**System Utilities:**
```bash
gearmeshing-ai system info
gearmeshing-ai system check
gearmeshing-ai system config [--show] [--validate] [--file FILE]
gearmeshing-ai system logs [--follow] [--lines N]
gearmeshing-ai system cleanup [--dry-run] [--force]
gearmeshing-ai system monitor
gearmeshing-ai system version
```

---

## How to Extend the CLI

### 1. Add a New Command to Existing Group

Edit the relevant command file (e.g., [gearmeshing_ai/command_line/commands/agent.py](cci:7://file:///Users/bryant/Bryant-Developments/GearMeshing-AI/gearmeshing-ai/gearmeshing_ai/command_line/commands/agent.py:0:0-0:0)):

```python
@app.command()
def my_command(
    param1: str = typer.Argument(..., help="Required parameter"),
    param2: Optional[str] = typer.Option(None, "--option", "-o", help="Optional flag"),
) -> None:
    """Description of what this command does."""
    logger.info(f"Running my_command with param1={param1}, param2={param2}")
    
    # TODO: Implement actual functionality
    typer.echo(f"✅ Command executed: {param1}")
```

### 2. Add a New Command Group (Subcommand)

Create a new file in `gearmeshing_ai/command_line/commands/`:

```python
# gearmeshing_ai/command_line/commands/workflow.py
"""Workflow management commands."""

import typer
from gearmeshing_ai.core.utils.logging_config import get_logger

logger = get_logger(__name__)

app = typer.Typer(
    name="workflow",
    help="🔄 Manage AI workflows and pipelines",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

@app.command()
def create(name: str = typer.Argument(..., help="Workflow name")) -> None:
    """Create a new workflow."""
    logger.info(f"Creating workflow: {name}")
    typer.echo(f"🔄 Workflow created: {name}")
```

Then register it in [gearmeshing_ai/command_line/app.py](cci:7://file:///Users/bryant/Bryant-Developments/GearMeshing-AI/gearmeshing-ai/gearmeshing_ai/command_line/app.py:0:0-0:0):

```python
from .commands import agent, server, system, workflow

app.add_typer(workflow.app, name="workflow", help="Manage workflows")
```

### 3. Add Tests for New Commands

Create tests in `test/unit_test/command_line/test_workflow.py`:

```python
from typer.testing import CliRunner
from gearmeshing_ai.command_line.app import app
from unittest.mock import patch

runner = CliRunner()

class TestWorkflowCommands:
    def test_workflow_create(self) -> None:
        """Test workflow creation."""
        with patch("gearmeshing_ai.command_line.commands.workflow.logger") as mock_logger:
            result = runner.invoke(app, ["workflow", "create", "my-workflow"])
            assert result.exit_code == 0
            assert "Workflow created" in result.stdout
            mock_logger.info.assert_called_with("Creating workflow: my-workflow")
```

---

## Important Considerations

### 1. **Logging Configuration**
- Use [get_logger(__name__)](cci:1://file:///Users/bryant/Bryant-Developments/GearMeshing-AI/gearmeshing-ai/gearmeshing_ai/core/utils/logging_config.py:8:0-10:34) to get a logger for your module
- The [setup_cli_logging()](cci:1://file:///Users/bryant/Bryant-Developments/GearMeshing-AI/gearmeshing-ai/gearmeshing_ai/core/utils/logging_config.py:13:0-45:30) function is called automatically via the callback
- **Important:** Tests reset logging between runs via the [conftest.py](cci:7://file:///Users/bryant/Bryant-Developments/GearMeshing-AI/gearmeshing-ai/test/unit_test/command_line/conftest.py:0:0-0:0) fixture to avoid file handle issues

### 2. **Test Isolation**
- The [test/unit_test/command_line/conftest.py](cci:7://file:///Users/bryant/Bryant-Developments/GearMeshing-AI/gearmeshing-ai/test/unit_test/command_line/conftest.py:0:0-0:0) fixture automatically resets logging state
- This prevents "I/O operation on closed file" errors when running multiple tests
- **Don't disable this fixture** - it's essential for test stability

### 3. **Typer Type Validation**
- Typer automatically validates parameter types (e.g., `int` for `--port`)
- Invalid types will cause exit code 2 (not 0)
- Empty strings are accepted for arguments unless you add custom validation

### 4. **Command Naming**
- Use lowercase with hyphens for command names (Typer converts underscores to hyphens)
- Keep command names concise and descriptive
- Use consistent naming across related commands

### 5. **Error Handling**
- Use `typer.Exit(code)` to exit with a specific code
- Use `typer.confirm()` for user confirmations (automatically mocked in tests)
- Log errors before exiting for debugging

### 6. **Documentation**
- Add docstrings to all commands and parameters
- Use `help=` parameter for clear option descriptions
- The `--help` flag automatically generates documentation

### 7. **Placeholder Implementation Pattern**
Current commands use this pattern:
```python
# TODO: Implement actual functionality
typer.echo("✅ Command executed")
```
Replace the TODO with actual implementation when ready.

### 8. **Import Paths**
- Use relative imports for commands: `from .commands import agent`
- Use absolute imports for utilities: `from gearmeshing_ai.core.utils.logging_config import get_logger`
- This maintains proper module structure and testability

### 9. **Global Options**
- Global options (verbose, quiet, config) are handled in the [main()](cci:1://file:///Users/bryant/Bryant-Developments/GearMeshing-AI/gearmeshing-ai/gearmeshing_ai/command_line/app.py:25:0-50:51) callback
- They're available to all subcommands automatically
- Add new global options to the [main()](cci:1://file:///Users/bryant/Bryant-Developments/GearMeshing-AI/gearmeshing-ai/gearmeshing_ai/command_line/app.py:25:0-50:51) function signature

### 10. **Entry Point**
- The [main_entry()](cci:1://file:///Users/bryant/Bryant-Developments/GearMeshing-AI/gearmeshing-ai/gearmeshing_ai/command_line/app.py:53:0-62:27) function handles exceptions and keyboard interrupts
- It's used by the package entry point in [pyproject.toml](cci:7://file:///Users/bryant/Bryant-Developments/GearMeshing-AI/gearmeshing-ai/pyproject.toml:0:0-0:0)
- Don't modify this unless you have a specific reason

---

## Quick Reference: File Structure

```
gearmeshing_ai/command_line/
├── __init__.py              # Package exports
├── app.py                   # Main app, global options, subcommand registration
└── commands/
    ├── __init__.py
    ├── agent.py             # Agent management commands
    ├── server.py            # Server management commands
    └── system.py            # System utility commands

test/unit_test/command_line/
├── conftest.py              # Logging reset fixture (IMPORTANT)
├── test_app.py              # Tests for global app behavior
├── test_agent.py            # Tests for agent commands
├── test_server.py           # Tests for server commands
└── test_system.py           # Tests for system commands

test/integration_test/command_line/
└── test_cli_integration.py  # Integration tests for CLI workflows
```
