"""
Configuration and fixtures for adapter smoke tests.

This module provides common fixtures and configuration for running
adapter smoke tests that call real AI models.
"""

import pytest


def pytest_configure(config: any) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "smoke: mark test as a smoke test")
    config.addinivalue_line("markers", "ai_test: mark test as requiring real AI model calls")
    config.addinivalue_line("markers", "openai: mark test as requiring OpenAI API key")
