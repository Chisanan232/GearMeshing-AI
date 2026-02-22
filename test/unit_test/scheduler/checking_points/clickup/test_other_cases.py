"""Unit tests for ClickUp checking points."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from gearmeshing_ai.scheduler.checking_points.base import CheckingPoint, CheckingPointType
from gearmeshing_ai.scheduler.models.checking_point import CheckResult, CheckResultType
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType


class TestClickUpCheckingPointIntegration:
    """Integration tests for ClickUp checking points."""

    @pytest.mark.asyncio
    async def test_multiple_checking_points_evaluation(self):
        """Test evaluating with multiple checking points."""
        urgent_cp = Mock()
        urgent_cp.name = "urgent_task_cp"
        overdue_cp = Mock()
        overdue_cp.name = "overdue_task_cp"
        
        data = MonitoringData(
            id="task_critical",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_critical",
                "priority": "urgent",
                "due_date": "2024-01-01",
                "status": "open"
            }
        )
        
        with patch.object(urgent_cp, 'evaluate', new_callable=AsyncMock) as mock_urgent:
            with patch.object(overdue_cp, 'evaluate', new_callable=AsyncMock) as mock_overdue:
                mock_urgent.return_value = CheckResult(
                    checking_point_name="urgent_task_cp",
                    checking_point_type="clickup_urgent_task_cp",
                    result_type=CheckResultType.MATCH,
                    should_act=True,
                    confidence=0.95
                )
                mock_overdue.return_value = CheckResult(
                    checking_point_name="overdue_task_cp",
                    checking_point_type="clickup_overdue_task_cp",
                    result_type=CheckResultType.MATCH,
                    should_act=True,
                    confidence=0.98
                )
                
                result_urgent = await urgent_cp.evaluate(data)
                result_overdue = await overdue_cp.evaluate(data)
                
                assert result_urgent.should_act is True
                assert result_overdue.should_act is True

    @pytest.mark.asyncio
    async def test_checking_point_with_empty_data(self):
        """Test checking point with empty data."""
        cp = Mock()
        cp.name = "urgent_task_cp"
        
        data = MonitoringData(
            id="empty_task",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={}
        )
        
        with patch.object(cp, 'evaluate', new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="urgent_task_cp",
                checking_point_type="clickup_urgent_task_cp",
                result_type=CheckResultType.NO_MATCH,
                should_act=False,
                reason="Missing required fields",
                confidence=0.5
            )
            
            result = await cp.evaluate(data)
            assert result.should_act is False

    @pytest.mark.asyncio
    async def test_checking_point_confidence_levels(self):
        """Test checking point with different confidence levels."""
        cp = Mock()
        cp.name = "urgent_task_cp"
        
        confidence_levels = [0.5, 0.7, 0.85, 0.95, 0.99]
        
        for confidence in confidence_levels:
            data = MonitoringData(
                id=f"task_conf_{confidence}",
                type=MonitoringDataType.CLICKUP_TASK,
                source="clickup",
                data={"priority": "urgent"}
            )
            
            with patch.object(cp, 'evaluate', new_callable=AsyncMock) as mock_eval:
                mock_eval.return_value = CheckResult(
                    checking_point_name="urgent_task_cp",
                    checking_point_type="clickup_urgent_task_cp",
                    result_type=CheckResultType.MATCH,
                    should_act=True,
                    confidence=confidence
                )
                
                result = await cp.evaluate(data)
                assert result.confidence == confidence
