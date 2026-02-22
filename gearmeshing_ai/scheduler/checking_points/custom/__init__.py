"""Custom checking points package.

This package contains custom checking point implementations for various
monitoring scenarios and business logic.
"""

from .email_alerts import EmailAlertCheckingPoint

__all__ = [
    "EmailAlertCheckingPoint",
]
