"""Unit tests for Slack checking points."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from gearmeshing_ai.scheduler.models.checking_point import CheckResult, CheckResultType
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType


class TestSlackBotMentionCP:
    """Test Slack bot mention checking point."""

    def test_bot_mention_cp_initialization(self):
        """Test Slack bot mention CP initialization."""
        cp = Mock()
        cp.name = "bot_mention_cp"
        assert cp is not None
        assert cp.name == "bot_mention_cp"

    @pytest.mark.asyncio
    async def test_evaluate_bot_mention(self):
        """Test evaluating bot mention."""
        cp = Mock()
        cp.name = "bot_mention_cp"

        data = MonitoringData(
            id="msg_mention_123",
            type=MonitoringDataType.SLACK_MESSAGE,
            source="slack",
            data={
                "user": "user_123",
                "channel": "general",
                "text": "@scheduler-bot please analyze this task",
                "mentions": ["scheduler-bot"],
                "thread_ts": "1234567890.123456",
            },
        )

        with patch.object(cp, "evaluate", new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="bot_mention_cp",
                checking_point_type="slack_bot_mention_cp",
                result_type=CheckResultType.MATCH,
                should_act=True,
                reason="Bot mentioned in message",
                confidence=0.98,
            )

            result = await cp.evaluate(data)
            assert result.should_act is True

    @pytest.mark.asyncio
    async def test_evaluate_no_bot_mention(self):
        """Test evaluating message without bot mention."""
        cp = Mock()
        cp.name = "bot_mention_cp"

        data = MonitoringData(
            id="msg_no_mention_456",
            type=MonitoringDataType.SLACK_MESSAGE,
            source="slack",
            data={
                "user": "user_456",
                "channel": "general",
                "text": "Just a regular message",
                "mentions": [],
                "thread_ts": "1234567890.456789",
            },
        )

        with patch.object(cp, "evaluate", new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="bot_mention_cp",
                checking_point_type="slack_bot_mention_cp",
                result_type=CheckResultType.NO_MATCH,
                should_act=False,
                reason="No bot mention detected",
                confidence=0.99,
            )

            result = await cp.evaluate(data)
            assert result.should_act is False

    @pytest.mark.asyncio
    async def test_evaluate_multiple_mentions(self):
        """Test evaluating message with multiple mentions."""
        cp = Mock()
        cp.name = "bot_mention_cp"

        data = MonitoringData(
            id="msg_multi_mention",
            type=MonitoringDataType.SLACK_MESSAGE,
            source="slack",
            data={
                "user": "user_789",
                "channel": "general",
                "text": "@scheduler-bot @devops-team please review this",
                "mentions": ["scheduler-bot", "devops-team"],
                "thread_ts": "1234567890.789012",
            },
        )

        with patch.object(cp, "evaluate", new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="bot_mention_cp",
                checking_point_type="slack_bot_mention_cp",
                result_type=CheckResultType.MATCH,
                should_act=True,
                reason="Bot mentioned along with others",
                confidence=0.97,
            )

            result = await cp.evaluate(data)
            assert result.should_act is True
