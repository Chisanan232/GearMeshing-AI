"""Configuration Management Package

This package contains the configuration management system for the scheduler,
including settings loading, validation, and environment variable handling.

Key Components:
- Settings: Application settings with environment variable support
- Loader: Configuration loading utilities
"""

from .settings import get_scheduler_settings, scheduler_settings

__all__ = [
    "get_scheduler_settings",
    "scheduler_settings",
]
