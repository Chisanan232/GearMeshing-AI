"""Fixtures for command line tests."""

import logging
from collections.abc import Generator

import pytest


@pytest.fixture(autouse=True)  # type: ignore[untyped-decorator]
def reset_logging() -> Generator[None, None, None]:
    """Reset logging configuration between tests."""
    # Reset the logging configured flag
    import gearmeshing_ai.core.utils.logging_config as logging_config

    logging_config._logging_configured = False

    # Clear all handlers from root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    yield

    # Cleanup after test
    logging_config._logging_configured = False
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
