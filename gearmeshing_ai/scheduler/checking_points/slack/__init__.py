"""Slack checking points package.

This package contains checking point implementations for Slack events and messages.
"""

from .bot_mentions import BotMentionCheckingPoint

__all__ = [
    "BotMentionCheckingPoint",
]
