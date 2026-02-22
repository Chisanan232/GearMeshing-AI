"""Checking Points Package

This package contains the checking point system that provides flexible, code-based
monitoring logic for external systems. Checking points are the core components that
evaluate monitoring data and determine what actions should be taken.

Key Components:
- Base Classes: Abstract base classes for checking point implementations
- Registry: Auto-registration system for checking points
- Implementations: Concrete checking point implementations for different systems
"""

from .base import CheckingPoint, CheckingPointType
from .registry import checking_point_registry, register_checking_point

# Import all checking point implementations to trigger registration
from .clickup import *
from .slack import *
from .custom import *

__all__ = [
    "CheckingPoint",
    "CheckingPointType",
    "checking_point_registry",
    "register_checking_point",
]
