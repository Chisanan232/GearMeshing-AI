"""Main CLI application entry point."""

import typer
from typing import Optional

from .subcmd import agent, server, system
from gearmeshing_ai.core.utils.logging_config import get_logger, setup_cli_logging

logger = get_logger(__name__)

# Create the main Typer app
app = typer.Typer(
    name="gearmeshing-ai",
    help="🤖 GearMeshing-AI Command Line Interface - Enterprise AI Agent Management",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=False,
)

# Add subcommands
app.add_typer(agent.app, name="agent", help="Manage AI agents and workflows")
app.add_typer(server.app, name="server", help="Server management and operations")
app.add_typer(system.app, name="system", help="System utilities and diagnostics")


@app.callback()
def main(
    verbose: Optional[bool] = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    quiet: Optional[bool] = typer.Option(
        False, "--quiet", "-q", help="Suppress non-error output"
    ),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to configuration file"
    ),
) -> None:
    """GearMeshing-AI CLI - Enterprise AI Agent Management System.
    
    This command line interface provides comprehensive tools for managing
    AI agents, workflows, server operations, and system diagnostics.
    
    Use --help with any command to see detailed usage information.
    """
    # Configure logging based on verbosity
    setup_cli_logging(verbose=verbose, quiet=quiet)
    
    logger.info(f"GearMeshing-AI CLI initialized (verbose={verbose}, quiet={quiet})")
    
    if config:
        logger.info(f"Using config file: {config}")


def main_entry() -> None:
    """Entry point for the CLI application."""
    try:
        app()
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"CLI error: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    main_entry()
