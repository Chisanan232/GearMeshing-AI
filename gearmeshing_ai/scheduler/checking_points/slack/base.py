from abc import ABC
from datetime import datetime
from typing import Any

from gearmeshing_ai.scheduler.checking_points.base import CheckingPoint
from gearmeshing_ai.scheduler.models.checking_point import CheckResult
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType


class SlackCheckingPoint(CheckingPoint, ABC):
    """Base class for Slack checking points with client initialization."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the Slack checking point.

        Args:
            config: Configuration dictionary

        """
        super().__init__(config)

        # Slack-specific configuration
        self.bot_token = self.config.get("bot_token")

        # Client will be initialized lazily through the property
        self._slack_client = None

    async def _get_client(self):
        """Get the initialized Slack client with lazy loading."""
        if self._slack_client is None:
            await self._setup_client()
        return self._slack_client

    async def _setup_client(self) -> None:
        """Setup Slack client using slack-mcp-server library."""
        from slack_mcp.client.manager import get_client_manager

        # Use the Slack MCP server client manager
        manager = get_client_manager()
        self._slack_client = manager.get_async_client(
            token=self.bot_token,
            use_retries=self.config.get("use_retries", True),
        )

    def _can_handle_data_type(self, data_type: str) -> bool:
        """Check if this checking point can handle Slack message data."""
        return data_type == "slack_message"

    async def get_channel_messages(
        self,
        channel: str,
        limit: int = 100,
        oldest: str | None = None,
    ) -> list[dict]:
        """Get messages from a Slack channel using MCP server client with proper data models.

        Args:
            channel: Slack channel ID or name
            limit: Maximum number of messages to retrieve
            oldest: Optional timestamp to get messages after

        Returns:
            List of message dictionaries

        """
        from slack_mcp.mcp.model.input import SlackReadChannelMessagesInput

        client = await self._get_client()  # Lazy initialization happens here

        # Build input with proper data model
        input_params = SlackReadChannelMessagesInput(
            channel=channel,
            limit=limit,
            oldest=oldest,
        )

        # Use Slack MCP server client's conversations_history method
        # This returns a structured SlackChannelMessagesResponse data model
        response = await client.conversations_history(
            channel=input_params.channel,
            limit=input_params.limit,
            oldest=input_params.oldest,
        )

        # Return messages from the structured response
        # SlackChannelMessagesResponse has typed fields: ok, messages, has_more, etc.
        if response.ok and response.messages:
            return response.messages
        return []

    def convert_to_monitoring_data(self, messages: list[dict]) -> list[MonitoringData]:
        """Convert Slack messages to MonitoringData objects.

        Args:
            messages: List of message dictionaries

        Returns:
            List of MonitoringData objects

        """
        data_items = []
        for message in messages:
            data_items.append(
                MonitoringData(
                    id=f"slack_{message.get('ts', '')}",
                    type=MonitoringDataType.SLACK_MESSAGE,
                    source="slack",
                    data=message,
                    timestamp=datetime.utcnow(),
                )
            )
        return data_items

    def _get_prompt_variables(self, data: MonitoringData, result: CheckResult) -> dict[str, Any]:
        """Get Slack-specific prompt variables."""
        variables = super()._get_prompt_variables(data, result)

        # Add Slack-specific variables
        message_data = data.data
        variables.update(
            {
                "user_name": message_data.get("user"),
                "channel": message_data.get("channel"),
                "message_text": message_data.get("text", ""),
                "thread_ts": message_data.get("thread_ts"),
                "timestamp": message_data.get("ts"),
                "mentions": message_data.get("mentions", []),
                "reactions": message_data.get("reactions", []),
            }
        )

        return variables
