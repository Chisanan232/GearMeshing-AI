"""
Configuration and fixtures for abstraction smoke tests.

This module provides common fixtures and configuration for running
smoke tests that call real AI models.
"""

import os
from pathlib import Path

from typing import Any, Generator

import pytest

# Import test settings
from test.settings import test_settings


def pytest_configure(config: Any) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "ai_test: mark test as requiring real AI model calls")
    config.addinivalue_line("markers", "slow_test: mark test as slow (requires more time)")
    config.addinivalue_line("markers", "openai: mark test as requiring OpenAI API key")
    config.addinivalue_line("markers", "anthropic: mark test as requiring Anthropic API key")
    config.addinivalue_line("markers", "google: mark test as requiring Google API key")


def pytest_collection_modifyitems(config: Any, items: Any) -> None:
    """Modify test collection to add skip markers based on availability."""

    # Skip AI tests if disabled
    if not test_settings.run_ai_tests:
        skip_ai = pytest.mark.skip(reason="AI tests disabled")
        for item in items:
            if "ai_test" in item.keywords:
                item.add_marker(skip_ai)

    # Skip slow tests if disabled
    if not test_settings.run_slow_tests:
        skip_slow = pytest.mark.skip(reason="Slow tests disabled")
        for item in items:
            if "slow_test" in item.keywords:
                item.add_marker(skip_slow)

    # Skip provider-specific tests if API keys not available
    for item in items:
        if "openai" in item.keywords and not test_settings.has_provider("openai"):
            item.add_marker(pytest.mark.skip(reason="OpenAI API key not available"))

        if "anthropic" in item.keywords and not test_settings.has_provider("anthropic"):
            item.add_marker(pytest.mark.skip(reason="Anthropic API key not available"))

        if "google" in item.keywords and not test_settings.has_provider("google"):
            item.add_marker(pytest.mark.skip(reason="Google API key not available"))


@pytest.fixture(scope="session")  # type: ignore[untyped-decorator]
def test_settings_fixture() -> Any:
    """Provide test settings as a fixture."""
    return test_settings


@pytest.fixture(scope="session")  # type: ignore[untyped-decorator]
def available_providers() -> list[str]:
    """Get list of available AI providers."""
    return test_settings.get_available_providers()


@pytest.fixture(scope="session")  # type: ignore[untyped-decorator]
def has_openai() -> bool:
    """Check if OpenAI API key is available."""
    return test_settings.has_provider("openai")


@pytest.fixture(scope="session")  # type: ignore[untyped-decorator]
def has_anthropic() -> bool:
    """Check if Anthropic API key is available."""
    return test_settings.has_provider("anthropic")


@pytest.fixture(scope="session")  # type: ignore[untyped-decorator]
def has_google() -> bool:
    """Check if Google API key is available."""
    return test_settings.has_provider("google")


@pytest.fixture(scope="session")  # type: ignore[untyped-decorator]
def env_file_path() -> Path:
    """Get path to test environment file."""
    return Path(__file__).parent.parent.parent / ".env"


@pytest.fixture(autouse=True)  # type: ignore[untyped-decorator]
def setup_test_environment() -> Generator[None, None, None]:
    """Setup test environment before each test."""
    # Store original environment
    original_env = {}
    sensitive_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "LANGSMITH_TRACING", "LANGSMITH_API_KEY"]

    for key in sensitive_keys:
        if key in os.environ:
            original_env[key] = os.environ[key]

    yield

    # Restore original environment
    for key in sensitive_keys:
        if key in os.environ:
            del os.environ[key]

    for key, value in original_env.items():
        os.environ[key] = value
