"""Slack checking points package.

This package contains checking point implementations for Slack events and messages.

Note: Checking points are automatically registered via the CheckingPointMeta metaclass
when they are imported. No manual registration is needed.
"""

from .bot_mentions import BotMentionCheckingPoint

__all__ = [
    "BotMentionCheckingPoint",
]
