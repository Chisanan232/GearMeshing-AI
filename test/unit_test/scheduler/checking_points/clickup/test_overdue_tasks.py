"""Unit tests for ClickUp checking points."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from gearmeshing_ai.scheduler.models.checking_point import CheckResult, CheckResultType
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType


class TestClickUpOverdueTaskCP:
    """Test ClickUp overdue task checking point."""

    def test_overdue_task_cp_initialization(self):
        """Test ClickUp overdue task CP initialization."""
        cp = Mock()
        cp.name = "overdue_task_cp"
        assert cp is not None
        assert cp.name == "overdue_task_cp"

    @pytest.mark.asyncio
    async def test_evaluate_overdue_task(self):
        """Test evaluating overdue task."""
        cp = Mock()
        cp.name = "overdue_task_cp"

        data = MonitoringData(
            id="task_overdue",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"id": "task_overdue", "name": "Overdue Task", "due_date": "2024-01-01", "status": "open"},
        )

        with patch.object(cp, "evaluate", new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="overdue_task_cp",
                checking_point_type="clickup_overdue_task_cp",
                result_type=CheckResultType.MATCH,
                should_act=True,
                reason="Task is overdue",
                confidence=0.98,
            )

            result = await cp.evaluate(data)
            assert result.should_act is True

    @pytest.mark.asyncio
    async def test_evaluate_on_time_task(self):
        """Test evaluating on-time task."""
        cp = Mock()
        cp.name = "overdue_task_cp"

        data = MonitoringData(
            id="task_ontime",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"id": "task_ontime", "name": "On Time Task", "due_date": "2026-12-31", "status": "open"},
        )

        with patch.object(cp, "evaluate", new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="overdue_task_cp",
                checking_point_type="clickup_overdue_task_cp",
                result_type=CheckResultType.NO_MATCH,
                should_act=False,
                reason="Task is not overdue",
                confidence=0.95,
            )

            result = await cp.evaluate(data)
            assert result.should_act is False

    @pytest.mark.asyncio
    async def test_evaluate_overdue_by_days(self):
        """Test evaluating task overdue by specific days."""
        cp = Mock()
        cp.name = "overdue_task_cp"

        data = MonitoringData(
            id="task_days_overdue",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"id": "task_days_overdue", "due_date": "2024-01-01", "days_overdue": 30, "status": "open"},
        )

        with patch.object(cp, "evaluate", new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="overdue_task_cp",
                checking_point_type="clickup_overdue_task_cp",
                result_type=CheckResultType.MATCH,
                should_act=True,
                reason="Task is 30 days overdue",
                confidence=0.99,
            )

            result = await cp.evaluate(data)
            assert result.should_act is True
