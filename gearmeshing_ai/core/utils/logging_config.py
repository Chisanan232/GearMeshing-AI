"""Simple logging configuration for CLI."""

import logging

_logging_configured = False


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name."""
    return logging.getLogger(name)


def setup_cli_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Set up CLI logging configuration."""
    global _logging_configured

    # Only configure logging once
    if _logging_configured:
        return

    level = logging.INFO
    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.ERROR

    # Get root logger and configure it
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add new handler
    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    _logging_configured = True
