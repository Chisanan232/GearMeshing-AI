"""Main CLI application entry point."""

import typer

from gearmeshing_ai.core.utils.logging_config import get_logger, setup_cli_logging

from .subcmd import agent, server, system

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


@app.callback()  # type: ignore[misc]
def main(
    verbose: bool | None = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    quiet: bool | None = typer.Option(False, "--quiet", "-q", help="Suppress non-error output"),
    config: str | None = typer.Option(None, "--config", "-c", help="Path to configuration file"),
) -> None:
    """GearMeshing-AI CLI - Enterprise AI Agent Management System.

    This command line interface provides comprehensive tools for managing
    AI agents, workflows, server operations, and system diagnostics.

    Use --help with any command to see detailed usage information.
    """
    # Configure logging based on verbosity
    setup_cli_logging(verbose=verbose or False, quiet=quiet or False)

    logger.info(f"GearMeshing-AI CLI initialized (verbose={verbose}, quiet={quiet})")

    if config:
        logger.info(f"Using config file: {config}")


def main_entry() -> None:
    """Entry point for the CLI application."""
    try:
        app()
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        raise typer.Exit(1) from None
    except Exception as e:
        logger.error(f"CLI error: {e}")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    main_entry()
