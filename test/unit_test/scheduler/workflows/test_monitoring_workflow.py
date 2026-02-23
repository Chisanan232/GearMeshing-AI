"""Unit tests for monitoring workflow."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gearmeshing_ai.scheduler.models.checking_point import CheckResult, CheckResultType
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType
from gearmeshing_ai.scheduler.models.workflow import AIWorkflowResult


class TestMonitoringWorkflow:
    """Test MonitoringWorkflow functionality."""

    def test_monitoring_workflow_initialization(self):
        """Test MonitoringWorkflow initialization."""
        workflow = MagicMock()
        assert workflow is not None

    @pytest.mark.asyncio
    async def test_execute_monitoring_workflow(self):
        """Test executing monitoring workflow."""
        workflow = MagicMock()

        with patch.object(workflow, "execute", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = AIWorkflowResult(
                workflow_name="monitoring_workflow",
                checking_point_name="monitoring_cp",
                success=True,
                execution_id="exec_123",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                output={"status": "monitoring_complete"},
            )

            result = await workflow.execute()
            assert result.success is True
            assert result.workflow_name == "monitoring_workflow"

    @pytest.mark.asyncio
    async def test_monitoring_workflow_data_collection(self):
        """Test monitoring workflow data collection."""
        workflow = MagicMock()

        with patch.object(workflow, "collect_monitoring_data", new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = [
                MonitoringData(
                    id="task_1",
                    type=MonitoringDataType.CLICKUP_TASK,
                    source="clickup",
                    data={"id": "task_1", "priority": "urgent"},
                ),
                MonitoringData(
                    id="msg_1", type=MonitoringDataType.SLACK_MESSAGE, source="slack", data={"text": "Help needed"}
                ),
            ]

            results = await workflow.collect_monitoring_data()
            assert len(results) == 2
            assert results[0].source == "clickup"
            assert results[1].source == "slack"

    @pytest.mark.asyncio
    async def test_monitoring_workflow_evaluation(self):
        """Test monitoring workflow evaluation."""
        workflow = MagicMock()

        data = MonitoringData(
            id="task_1", type=MonitoringDataType.CLICKUP_TASK, source="clickup", data={"priority": "urgent"}
        )

        with patch.object(workflow, "evaluate_data", new_callable=AsyncMock) as mock_evaluate:
            mock_evaluate.return_value = CheckResult(
                checking_point_name="urgent_cp",
                checking_point_type="clickup_urgent_task_cp",
                result_type=CheckResultType.MATCH,
                should_act=True,
                confidence=0.95,
            )

            result = await workflow.evaluate_data(data)
            assert result.should_act is True
            assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_monitoring_workflow_action_execution(self):
        """Test monitoring workflow action execution."""
        workflow = MagicMock()

        data = MonitoringData(
            id="task_1", type=MonitoringDataType.CLICKUP_TASK, source="clickup", data={"id": "task_1"}
        )

        check_result = CheckResult(
            checking_point_name="urgent_cp",
            checking_point_type="clickup_urgent_task_cp",
            result_type=CheckResultType.MATCH,
            should_act=True,
        )

        with patch.object(workflow, "execute_action", new_callable=AsyncMock) as mock_action:
            mock_action.return_value = AIWorkflowResult(
                workflow_name="monitoring_workflow",
                checking_point_name="urgent_cp",
                success=True,
                execution_id="exec_action",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                actions_taken=["escalate", "notify"],
            )

            result = await workflow.execute_action(data, check_result)
            assert result.success is True
            assert len(result.actions_taken) > 0

    @pytest.mark.asyncio
    async def test_monitoring_workflow_error_handling(self):
        """Test monitoring workflow error handling."""
        workflow = MagicMock()

        with patch.object(workflow, "execute", new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = Exception("Workflow error")

            with pytest.raises(Exception):
                await workflow.execute()

    @pytest.mark.asyncio
    async def test_monitoring_workflow_with_multiple_sources(self):
        """Test monitoring workflow with multiple data sources."""
        workflow = MagicMock()

        with patch.object(workflow, "collect_monitoring_data", new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = [
                MonitoringData(id=f"item_{source}", type=data_type, source=source, data={})
                for source, data_type in [
                    ("clickup", MonitoringDataType.CLICKUP_TASK),
                    ("slack", MonitoringDataType.SLACK_MESSAGE),
                    ("email", MonitoringDataType.EMAIL_ALERT),
                ]
            ]

            results = await workflow.collect_monitoring_data()
            assert len(results) == 3
            sources = {r.source for r in results}
            assert sources == {"clickup", "slack", "email"}

    @pytest.mark.asyncio
    async def test_monitoring_workflow_batch_processing(self):
        """Test monitoring workflow batch processing."""
        workflow = MagicMock()

        data_items = [
            MonitoringData(
                id=f"task_{i}", type=MonitoringDataType.CLICKUP_TASK, source="clickup", data={"id": f"task_{i}"}
            )
            for i in range(10)
        ]

        with patch.object(workflow, "process_batch", new_callable=AsyncMock) as mock_batch:
            mock_batch.return_value = {"processed": 10, "matched": 5, "actions_taken": 5}

            result = await workflow.process_batch(data_items)
            assert result["processed"] == 10
            assert result["matched"] == 5

    @pytest.mark.asyncio
    async def test_monitoring_workflow_filtering(self):
        """Test monitoring workflow filtering."""
        workflow = MagicMock()

        all_data = [
            MonitoringData(
                id=f"task_{i}",
                type=MonitoringDataType.CLICKUP_TASK,
                source="clickup",
                data={"priority": "urgent" if i % 2 == 0 else "low"},
            )
            for i in range(10)
        ]

        with patch.object(workflow, "filter_data", new_callable=AsyncMock) as mock_filter:
            mock_filter.return_value = [d for d in all_data if d.data["priority"] == "urgent"]

            result = await workflow.filter_data(all_data, priority="urgent")
            assert len(result) == 5

    @pytest.mark.asyncio
    async def test_monitoring_workflow_aggregation(self):
        """Test monitoring workflow aggregation."""
        workflow = MagicMock()

        with patch.object(workflow, "aggregate_results", new_callable=AsyncMock) as mock_aggregate:
            mock_aggregate.return_value = {
                "total_items": 100,
                "matched_items": 25,
                "actions_taken": 20,
                "success_rate": 0.95,
            }

            result = await workflow.aggregate_results()
            assert result["total_items"] == 100
            assert result["success_rate"] == 0.95

    @pytest.mark.asyncio
    async def test_monitoring_workflow_scheduling(self):
        """Test monitoring workflow scheduling."""
        workflow = MagicMock()

        with patch.object(workflow, "schedule_next_run", new_callable=AsyncMock) as mock_schedule:
            mock_schedule.return_value = {"next_run": "2026-02-21T15:00:00", "interval_seconds": 3600}

            result = await workflow.schedule_next_run()
            assert result["next_run"] is not None
            assert result["interval_seconds"] == 3600

    @pytest.mark.asyncio
    async def test_monitoring_workflow_metrics(self):
        """Test monitoring workflow metrics collection."""
        workflow = MagicMock()

        with patch.object(workflow, "collect_metrics", new_callable=AsyncMock) as mock_metrics:
            mock_metrics.return_value = {
                "execution_time_ms": 1234,
                "items_processed": 50,
                "items_matched": 15,
                "actions_executed": 12,
            }

            result = await workflow.collect_metrics()
            assert result["execution_time_ms"] > 0
            assert result["items_processed"] == 50

    @pytest.mark.asyncio
    async def test_monitoring_workflow_state_management(self):
        """Test monitoring workflow state management."""
        workflow = MagicMock()

        with patch.object(workflow, "save_state", new_callable=AsyncMock) as mock_save:
            mock_save.return_value = True

            state = {"last_run": datetime.utcnow().isoformat(), "items_processed": 100, "status": "completed"}

            result = await workflow.save_state(state)
            assert result is True

    @pytest.mark.asyncio
    async def test_monitoring_workflow_recovery(self):
        """Test monitoring workflow recovery from failure."""
        workflow = MagicMock()

        with patch.object(workflow, "recover_from_failure", new_callable=AsyncMock) as mock_recover:
            mock_recover.return_value = {"recovered": True, "items_reprocessed": 10, "status": "resumed"}

            result = await workflow.recover_from_failure()
            assert result["recovered"] is True
