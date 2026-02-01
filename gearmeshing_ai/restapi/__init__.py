"""GearMeshing-AI REST API package.

This package provides the REST API implementation for the GearMeshing-AI
platform, following duck typing principles for clean, maintainable code.
"""

from .main import app, create_application

__all__ = ["app", "create_application"]
