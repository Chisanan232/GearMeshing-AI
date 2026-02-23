"""Unit tests for ClickUp checking points."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from gearmeshing_ai.scheduler.models.checking_point import CheckResult, CheckResultType
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType


class TestClickUpSmartAssignmentCP:
    """Test ClickUp smart assignment checking point."""

    def test_smart_assignment_cp_initialization(self):
        """Test ClickUp smart assignment CP initialization."""
        cp = Mock()
        cp.name = "clickup_smart_assignment_cp"
        cp.priority_thresholds = ["high", "urgent"]
        cp.ignore_statuses = ["done", "completed", "closed"]

        assert cp is not None
        assert cp.name == "clickup_smart_assignment_cp"
        assert "high" in cp.priority_thresholds
        assert "urgent" in cp.priority_thresholds

    @pytest.mark.asyncio
    async def test_evaluate_unassigned_urgent_task(self):
        """Test evaluating unassigned urgent task."""
        cp = Mock()
        cp.name = "clickup_smart_assignment_cp"

        # Create task that's 48 hours old (unassigned)
        created_date = (datetime.utcnow() - timedelta(hours=48)).isoformat() + "Z"

        data = MonitoringData(
            id="task_unassigned_urgent",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_unassigned_urgent",
                "name": "Urgent API Fix",
                "description": "Fix critical API endpoint",
                "priority": "urgent",
                "status": {"status": "open"},
                "tags": [],
                "date_created": created_date,
                "assignees": {},
            },
        )

        with patch.object(cp, "evaluate", new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="clickup_smart_assignment_cp",
                checking_point_type="clickup_smart_assignment_cp",
                result_type=CheckResultType.MATCH,
                should_act=True,
                reason="Unassigned urgent task needs assignment",
                confidence=0.85,
                context={
                    "hours_unassigned": 48.0,
                    "task_priority": "urgent",
                    "task_categories": ["backend", "api"],
                    "confidence_factors": ["Urgent priority", "Very old (48 hours)"],
                    "available_team_members": 4,
                },
            )

            result = await cp.evaluate(data)
            assert result.should_act is True
            assert result.confidence >= 0.8
            assert result.context["hours_unassigned"] == 48.0

    @pytest.mark.asyncio
    async def test_evaluate_already_assigned_task(self):
        """Test evaluating already assigned task."""
        cp = Mock()
        cp.name = "clickup_smart_assignment_cp"

        data = MonitoringData(
            id="task_assigned",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_assigned",
                "name": "Already Assigned Task",
                "priority": "urgent",
                "status": {"status": "open"},
                "tags": [],
                "assignees": {"user_1": "John Doe"},
            },
        )

        with patch.object(cp, "evaluate", new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="clickup_smart_assignment_cp",
                checking_point_type="clickup_smart_assignment_cp",
                result_type=CheckResultType.NO_MATCH,
                should_act=False,
                reason="Task is already assigned",
                confidence=1.0,
            )

            result = await cp.evaluate(data)
            assert result.should_act is False
            assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_evaluate_completed_task(self):
        """Test evaluating completed task."""
        cp = Mock()
        cp.name = "clickup_smart_assignment_cp"

        data = MonitoringData(
            id="task_completed",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_completed",
                "name": "Completed Task",
                "priority": "urgent",
                "status": {"status": "completed"},
                "tags": [],
                "assignees": {},
            },
        )

        with patch.object(cp, "evaluate", new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="clickup_smart_assignment_cp",
                checking_point_type="clickup_smart_assignment_cp",
                result_type=CheckResultType.NO_MATCH,
                should_act=False,
                reason="Task status 'completed' is ignored",
                confidence=1.0,
            )

            result = await cp.evaluate(data)
            assert result.should_act is False

    @pytest.mark.asyncio
    async def test_evaluate_low_priority_task(self):
        """Test evaluating low priority task."""
        cp = Mock()
        cp.name = "clickup_smart_assignment_cp"

        created_date = (datetime.utcnow() - timedelta(hours=48)).isoformat() + "Z"

        data = MonitoringData(
            id="task_low_priority",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_low_priority",
                "name": "Low Priority Task",
                "priority": "low",
                "status": {"status": "open"},
                "tags": [],
                "date_created": created_date,
                "assignees": {},
            },
        )

        with patch.object(cp, "evaluate", new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="clickup_smart_assignment_cp",
                checking_point_type="clickup_smart_assignment_cp",
                result_type=CheckResultType.NO_MATCH,
                should_act=False,
                reason="Task priority 'low' is below threshold",
                confidence=1.0,
            )

            result = await cp.evaluate(data)
            assert result.should_act is False

    @pytest.mark.asyncio
    async def test_evaluate_task_with_excluded_tags(self):
        """Test evaluating task with excluded tags."""
        cp = Mock()
        cp.name = "clickup_smart_assignment_cp"

        created_date = (datetime.utcnow() - timedelta(hours=48)).isoformat() + "Z"

        data = MonitoringData(
            id="task_blocked",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_blocked",
                "name": "Blocked Task",
                "priority": "urgent",
                "status": {"status": "open"},
                "tags": ["blocked", "waiting"],
                "date_created": created_date,
                "assignees": {},
            },
        )

        with patch.object(cp, "evaluate", new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="clickup_smart_assignment_cp",
                checking_point_type="clickup_smart_assignment_cp",
                result_type=CheckResultType.NO_MATCH,
                should_act=False,
                reason="Task has excluded tags: blocked, waiting",
                confidence=1.0,
            )

            result = await cp.evaluate(data)
            assert result.should_act is False

    @pytest.mark.asyncio
    async def test_evaluate_task_too_new(self):
        """Test evaluating task that's too new to assign."""
        cp = Mock()
        cp.name = "clickup_smart_assignment_cp"

        # Create task that's only 12 hours old
        created_date = (datetime.utcnow() - timedelta(hours=12)).isoformat() + "Z"

        data = MonitoringData(
            id="task_new",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_new",
                "name": "New Task",
                "priority": "urgent",
                "status": {"status": "open"},
                "tags": [],
                "date_created": created_date,
                "assignees": {},
            },
        )

        with patch.object(cp, "evaluate", new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="clickup_smart_assignment_cp",
                checking_point_type="clickup_smart_assignment_cp",
                result_type=CheckResultType.NO_MATCH,
                should_act=False,
                reason="Task is only 12.0 hours old (threshold: 24)",
                confidence=1.0,
            )

            result = await cp.evaluate(data)
            assert result.should_act is False

    @pytest.mark.asyncio
    async def test_evaluate_task_with_required_tags(self):
        """Test evaluating task with required tags."""
        cp = Mock()
        cp.name = "clickup_smart_assignment_cp"

        created_date = (datetime.utcnow() - timedelta(hours=48)).isoformat() + "Z"

        # Task missing required tag
        data = MonitoringData(
            id="task_missing_tag",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_missing_tag",
                "name": "Task Missing Tag",
                "priority": "urgent",
                "status": {"status": "open"},
                "tags": ["bug"],
                "date_created": created_date,
                "assignees": {},
            },
        )

        with patch.object(cp, "evaluate", new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="clickup_smart_assignment_cp",
                checking_point_type="clickup_smart_assignment_cp",
                result_type=CheckResultType.NO_MATCH,
                should_act=False,
                reason="Missing required tags: critical",
                confidence=1.0,
            )

            result = await cp.evaluate(data)
            assert result.should_act is False

    @pytest.mark.asyncio
    async def test_evaluate_high_priority_task(self):
        """Test evaluating high priority unassigned task."""
        cp = Mock()
        cp.name = "clickup_smart_assignment_cp"

        created_date = (datetime.utcnow() - timedelta(hours=36)).isoformat() + "Z"

        data = MonitoringData(
            id="task_high_priority",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_high_priority",
                "name": "High Priority Database Migration",
                "description": "Migrate production database",
                "priority": "high",
                "status": {"status": "open"},
                "tags": ["database"],
                "date_created": created_date,
                "assignees": {},
            },
        )

        with patch.object(cp, "evaluate", new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="clickup_smart_assignment_cp",
                checking_point_type="clickup_smart_assignment_cp",
                result_type=CheckResultType.MATCH,
                should_act=True,
                reason="Unassigned high task (36.0 hours old) needs assignment",
                confidence=0.75,
                context={
                    "hours_unassigned": 36.0,
                    "task_priority": "high",
                    "task_categories": ["backend"],
                    "confidence_factors": ["High priority", "Old (36 hours)"],
                    "available_team_members": 4,
                },
            )

            result = await cp.evaluate(data)
            assert result.should_act is True
            assert result.confidence >= 0.7

    @pytest.mark.asyncio
    async def test_evaluate_task_with_multiple_categories(self):
        """Test evaluating task with multiple skill categories."""
        cp = Mock()
        cp.name = "clickup_smart_assignment_cp"

        created_date = (datetime.utcnow() - timedelta(hours=48)).isoformat() + "Z"

        data = MonitoringData(
            id="task_multi_category",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_multi_category",
                "name": "Full Stack Feature Implementation",
                "description": "Implement API endpoint and React UI component",
                "priority": "urgent",
                "status": {"status": "open"},
                "tags": ["feature"],
                "date_created": created_date,
                "assignees": {},
            },
        )

        with patch.object(cp, "evaluate", new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="clickup_smart_assignment_cp",
                checking_point_type="clickup_smart_assignment_cp",
                result_type=CheckResultType.MATCH,
                should_act=True,
                reason="Unassigned urgent task (48.0 hours old) needs assignment",
                confidence=0.85,
                context={
                    "hours_unassigned": 48.0,
                    "task_priority": "urgent",
                    "task_categories": ["backend", "frontend"],
                    "confidence_factors": ["Urgent priority", "Very old (48 hours)"],
                    "available_team_members": 4,
                },
            )

            result = await cp.evaluate(data)
            assert result.should_act is True
            assert len(result.context["task_categories"]) > 1

    @pytest.mark.asyncio
    async def test_evaluate_task_with_invalid_date(self):
        """Test evaluating task with invalid date format."""
        cp = Mock()
        cp.name = "clickup_smart_assignment_cp"

        data = MonitoringData(
            id="task_invalid_date",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_invalid_date",
                "name": "Task with Invalid Date",
                "priority": "urgent",
                "status": {"status": "open"},
                "tags": [],
                "date_created": "invalid-date-format",
                "assignees": {},
            },
        )

        with patch.object(cp, "evaluate", new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="clickup_smart_assignment_cp",
                checking_point_type="clickup_smart_assignment_cp",
                result_type=CheckResultType.NO_MATCH,
                should_act=False,
                reason="Task is only 0.0 hours old (threshold: 24)",
                confidence=1.0,
            )

            result = await cp.evaluate(data)
            assert result.should_act is False

    @pytest.mark.asyncio
    async def test_evaluate_task_with_exception(self):
        """Test evaluating task that raises exception."""
        cp = Mock()
        cp.name = "clickup_smart_assignment_cp"

        # Create data with missing required fields to trigger error handling
        data = MonitoringData(
            id="task_error",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={},  # Empty data dict
        )

        with patch.object(cp, "evaluate", new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="clickup_smart_assignment_cp",
                checking_point_type="clickup_smart_assignment_cp",
                result_type=CheckResultType.NO_MATCH,
                should_act=False,
                confidence=1.0,
                reason="Task is only 0.0 hours old (threshold: 24)",
            )

            result = await cp.evaluate(data)
            assert result.should_act is False

    @pytest.mark.asyncio
    async def test_get_actions_for_unassigned_task(self):
        """Test getting actions for unassigned task."""
        cp = Mock()
        cp.name = "clickup_smart_assignment_cp"
        cp.notify_team_lead = True

        data = MonitoringData(
            id="task_actions",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_actions",
                "name": "Task Needing Actions",
                "priority": "urgent",
                "status": {"status": "open"},
                "tags": [],
            },
        )

        check_result = CheckResult(
            checking_point_name="clickup_smart_assignment_cp",
            checking_point_type="clickup_smart_assignment_cp",
            result_type=CheckResultType.MATCH,
            should_act=True,
            confidence=0.85,
            context={"hours_unassigned": 48.0},
        )

        with patch.object(cp, "get_actions") as mock_actions:
            mock_actions.return_value = [
                {
                    "type": "status_update",
                    "name": "mark_needs_assignment",
                    "parameters": {
                        "system": "clickup",
                        "entity_id": "task_actions",
                        "add_tags": ["needs_assignment"],
                    },
                },
                {
                    "type": "notification",
                    "name": "notify_team_lead_assignment",
                    "parameters": {
                        "notification_type": "slack",
                        "recipient": "#team-leads",
                        "subject": "Unassigned Task: Task Needing Actions",
                    },
                },
            ]

            actions = cp.get_actions(data, check_result)
            assert len(actions) == 2
            assert actions[0]["type"] == "status_update"
            assert actions[1]["type"] == "notification"

    @pytest.mark.asyncio
    async def test_get_after_process_ai_action(self):
        """Test getting AI workflow action for smart assignment."""
        cp = Mock()
        cp.name = "clickup_smart_assignment_cp"
        cp.ai_workflow_enabled = True
        cp.auto_assign = False
        cp.team_members = [
            {"id": "dev_1", "name": "Senior Developer", "skills": ["backend"]},
            {"id": "dev_2", "name": "Frontend Developer", "skills": ["frontend"]},
        ]
        cp.assignment_rules = {"backend_tasks": ["dev_1"]}
        cp.default_assignee = "dev_1"

        data = MonitoringData(
            id="task_ai_action",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_ai_action",
                "name": "Task for AI Assignment",
                "priority": "urgent",
                "status": {"status": "open"},
                "tags": [],
            },
        )

        check_result = CheckResult(
            checking_point_name="clickup_smart_assignment_cp",
            checking_point_type="clickup_smart_assignment_cp",
            result_type=CheckResultType.MATCH,
            should_act=True,
            confidence=0.85,
            context={
                "hours_unassigned": 48.0,
                "task_categories": ["backend"],
            },
        )

        with patch.object(cp, "get_after_process") as mock_after:
            mock_after.return_value = [
                {
                    "type": "ai_workflow",
                    "parameters": {
                        "task_categories": ["backend"],
                        "hours_unassigned": 48.0,
                        "team_members": cp.team_members,
                        "assignment_rules": cp.assignment_rules,
                        "default_assignee": "dev_1",
                        "auto_assign": False,
                    },
                    "approval_required": True,
                }
            ]

            actions = cp.get_after_process(data, check_result)
            assert len(actions) == 1
            assert actions[0]["type"] == "ai_workflow"

    @pytest.mark.asyncio
    async def test_evaluate_very_old_task(self):
        """Test evaluating very old unassigned task."""
        cp = Mock()
        cp.name = "clickup_smart_assignment_cp"

        # Create task that's 72 hours old
        created_date = (datetime.utcnow() - timedelta(hours=72)).isoformat() + "Z"

        data = MonitoringData(
            id="task_very_old",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={
                "id": "task_very_old",
                "name": "Very Old Unassigned Task",
                "priority": "high",
                "status": {"status": "open"},
                "tags": [],
                "date_created": created_date,
                "assignees": {},
            },
        )

        with patch.object(cp, "evaluate", new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = CheckResult(
                checking_point_name="clickup_smart_assignment_cp",
                checking_point_type="clickup_smart_assignment_cp",
                result_type=CheckResultType.MATCH,
                should_act=True,
                reason="Unassigned high task (72.0 hours old) needs assignment",
                confidence=0.8,
                context={
                    "hours_unassigned": 72.0,
                    "task_priority": "high",
                    "task_categories": ["general"],
                    "confidence_factors": ["High priority", "Very old (72 hours)"],
                    "available_team_members": 4,
                },
            )

            result = await cp.evaluate(data)
            assert result.should_act is True
            assert result.context["hours_unassigned"] == 72.0
            assert result.confidence >= 0.8
