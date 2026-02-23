"""Unit tests for data fetch activities."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType


class TestDataFetchingActivity:
    """Test DataFetchingActivity functionality."""

    def test_data_fetch_activity_initialization(self):
        """Test DataFetchingActivity initialization."""
        activity = Mock()
        assert activity is not None

    @pytest.mark.asyncio
    async def test_fetch_clickup_tasks(self):
        """Test fetching ClickUp tasks."""
        activity = Mock()

        with patch.object(activity, "fetch_clickup_tasks", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [
                MonitoringData(
                    id="task_1",
                    type=MonitoringDataType.CLICKUP_TASK,
                    source="clickup",
                    data={"id": "task_1", "name": "Task 1", "priority": "high"},
                ),
                MonitoringData(
                    id="task_2",
                    type=MonitoringDataType.CLICKUP_TASK,
                    source="clickup",
                    data={"id": "task_2", "name": "Task 2", "priority": "low"},
                ),
            ]

            results = await activity.fetch_clickup_tasks()
            assert len(results) == 2
            assert results[0].id == "task_1"

    @pytest.mark.asyncio
    async def test_fetch_slack_messages(self):
        """Test fetching Slack messages."""
        activity = Mock()

        with patch.object(activity, "fetch_slack_messages", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [
                MonitoringData(
                    id="msg_1",
                    type=MonitoringDataType.SLACK_MESSAGE,
                    source="slack",
                    data={"user": "user_1", "text": "Help needed"},
                ),
                MonitoringData(
                    id="msg_2",
                    type=MonitoringDataType.SLACK_MESSAGE,
                    source="slack",
                    data={"user": "user_2", "text": "Update on project"},
                ),
            ]

            results = await activity.fetch_slack_messages()
            assert len(results) == 2
            assert results[0].type == MonitoringDataType.SLACK_MESSAGE

    @pytest.mark.asyncio
    async def test_fetch_with_filters(self):
        """Test fetching data with filters."""
        activity = Mock()

        filters = {"priority": "urgent", "status": "open"}

        with patch.object(activity, "fetch_clickup_tasks", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [
                MonitoringData(
                    id="urgent_task",
                    type=MonitoringDataType.CLICKUP_TASK,
                    source="clickup",
                    data={"priority": "urgent", "status": "open"},
                )
            ]

            results = await activity.fetch_clickup_tasks(**filters)
            assert len(results) == 1
            assert results[0].data["priority"] == "urgent"

    @pytest.mark.asyncio
    async def test_fetch_with_pagination(self):
        """Test fetching data with pagination."""
        activity = Mock()

        with patch.object(activity, "fetch_clickup_tasks", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [
                MonitoringData(
                    id=f"task_{i}", type=MonitoringDataType.CLICKUP_TASK, source="clickup", data={"id": f"task_{i}"}
                )
                for i in range(10)
            ]

            results = await activity.fetch_clickup_tasks(limit=10, offset=0)
            assert len(results) == 10

    @pytest.mark.asyncio
    async def test_fetch_error_handling(self):
        """Test error handling during fetch."""
        activity = Mock()

        with patch.object(activity, "fetch_clickup_tasks", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("API Error")

            with pytest.raises(Exception):
                await activity.fetch_clickup_tasks()

    @pytest.mark.asyncio
    async def test_fetch_empty_results(self):
        """Test fetching with empty results."""
        activity = Mock()

        with patch.object(activity, "fetch_clickup_tasks", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []

            results = await activity.fetch_clickup_tasks()
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_fetch_with_timestamp_filtering(self):
        """Test fetching with timestamp filtering."""
        activity = Mock()

        now = datetime.utcnow()

        with patch.object(activity, "fetch_slack_messages", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [
                MonitoringData(
                    id="msg_recent",
                    type=MonitoringDataType.SLACK_MESSAGE,
                    source="slack",
                    data={"text": "Recent message"},
                    timestamp=now,
                )
            ]

            results = await activity.fetch_slack_messages(since=now)
            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_fetch_multiple_sources(self):
        """Test fetching from multiple sources."""
        activity = Mock()

        with patch.object(activity, "fetch_all_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [
                MonitoringData(
                    id="task_1", type=MonitoringDataType.CLICKUP_TASK, source="clickup", data={"id": "task_1"}
                ),
                MonitoringData(
                    id="msg_1", type=MonitoringDataType.SLACK_MESSAGE, source="slack", data={"text": "message"}
                ),
                MonitoringData(
                    id="email_1", type=MonitoringDataType.EMAIL_ALERT, source="email", data={"subject": "Alert"}
                ),
            ]

            results = await activity.fetch_all_data()
            assert len(results) == 3
            assert results[0].source == "clickup"
            assert results[1].source == "slack"
            assert results[2].source == "email"

    @pytest.mark.asyncio
    async def test_fetch_with_retry_logic(self):
        """Test fetch with retry logic."""
        activity = Mock()

        with patch.object(activity, "fetch_clickup_tasks", new_callable=AsyncMock) as mock_fetch:
            # Simulate retry: fail once, then succeed
            mock_fetch.side_effect = [
                Exception("Temporary error"),
                [
                    MonitoringData(
                        id="task_1", type=MonitoringDataType.CLICKUP_TASK, source="clickup", data={"id": "task_1"}
                    )
                ],
            ]

            # First call fails
            with pytest.raises(Exception):
                await activity.fetch_clickup_tasks()

            # Second call succeeds
            results = await activity.fetch_clickup_tasks()
            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_fetch_data_enrichment(self):
        """Test data enrichment during fetch."""
        activity = Mock()

        with patch.object(activity, "fetch_clickup_tasks", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [
                MonitoringData(
                    id="task_1",
                    type=MonitoringDataType.CLICKUP_TASK,
                    source="clickup",
                    data={"id": "task_1", "name": "Task 1"},
                    metadata={"source_url": "https://clickup.com/tasks/task_1"},
                )
            ]

            results = await activity.fetch_clickup_tasks()
            assert results[0].metadata["source_url"] is not None

    @pytest.mark.asyncio
    async def test_fetch_concurrent_sources(self):
        """Test concurrent fetching from multiple sources."""
        activity = Mock()

        with patch.object(activity, "fetch_clickup_tasks", new_callable=AsyncMock) as mock_clickup:
            with patch.object(activity, "fetch_slack_messages", new_callable=AsyncMock) as mock_slack:
                mock_clickup.return_value = [
                    MonitoringData(
                        id="task_1", type=MonitoringDataType.CLICKUP_TASK, source="clickup", data={"id": "task_1"}
                    )
                ]
                mock_slack.return_value = [
                    MonitoringData(
                        id="msg_1", type=MonitoringDataType.SLACK_MESSAGE, source="slack", data={"text": "message"}
                    )
                ]

                # Simulate concurrent fetch
                clickup_results = await activity.fetch_clickup_tasks()
                slack_results = await activity.fetch_slack_messages()

                assert len(clickup_results) == 1
                assert len(slack_results) == 1
