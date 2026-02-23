"""Custom checking points package.

This package contains custom checking point implementations for various
monitoring scenarios and business logic.

Note: Checking points are automatically registered via the CheckingPointMeta metaclass
when they are imported. No manual registration is needed.
"""

from .email_alerts import EmailAlertCheckingPoint

__all__ = [
    "EmailAlertCheckingPoint",
]
