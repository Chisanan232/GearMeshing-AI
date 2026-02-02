"""Fixtures for command line tests."""

import pytest
import logging


@pytest.fixture(autouse=True)
def reset_logging():
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
