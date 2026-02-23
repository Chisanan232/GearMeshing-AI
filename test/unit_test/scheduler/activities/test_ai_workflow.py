"""Unit tests for AI workflow activities."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from gearmeshing_ai.scheduler.models.workflow import AIAction, AIActionType, AIWorkflowInput, AIWorkflowResult
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType
from gearmeshing_ai.scheduler.models.checking_point import CheckResult, CheckResultType


class TestAIWorkflowActivity:
    """Test AIWorkflowActivity functionality."""

    def test_ai_workflow_activity_initialization(self):
        """Test AIWorkflowActivity initialization."""
        activity = Mock()
        assert activity is not None

    @pytest.mark.asyncio
    async def test_execute_workflow(self):
        """Test executing AI workflow."""
        activity = Mock()
        
        action = AIAction(
            name="test_workflow",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="test_workflow",
            checking_point_name="test_cp"
        )
        
        data = MonitoringData(
            id="task_1",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"id": "task_1", "name": "Test Task"}
        )
        
        check_result = CheckResult(
            checking_point_name="test_cp",
            checking_point_type="custom_cp",
            result_type=CheckResultType.MATCH,
            should_act=True
        )
        
        with patch.object(activity, 'execute_workflow', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = AIWorkflowResult(
                workflow_name="test_workflow",
                checking_point_name="test_cp",
                success=True,
                execution_id="exec_123",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                output={"result": "success"}
            )
            
            result = await activity.execute_workflow(action, data, check_result)
            assert result.success is True
            assert result.workflow_name == "test_workflow"

    @pytest.mark.asyncio
    async def test_execute_workflow_with_approval(self):
        """Test executing workflow that requires approval."""
        activity = Mock()
        
        action = AIAction(
            name="approval_workflow",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="approval_workflow",
            checking_point_name="approval_cp",
            approval_required=True
        )
        
        data = MonitoringData(
            id="task_2",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"id": "task_2"}
        )
        
        check_result = CheckResult(
            checking_point_name="approval_cp",
            checking_point_type="custom_cp",
            result_type=CheckResultType.MATCH,
            should_act=True
        )
        
        with patch.object(activity, 'execute_workflow', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = AIWorkflowResult(
                workflow_name="approval_workflow",
                checking_point_name="approval_cp",
                success=True,
                execution_id="exec_456",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                approval_required=True,
                approval_granted=True,
                output={"result": "approved"}
            )
            
            result = await activity.execute_workflow(action, data, check_result)
            assert result.approval_required is True
            assert result.approval_granted is True

    @pytest.mark.asyncio
    async def test_execute_workflow_failure(self):
        """Test workflow execution failure."""
        activity = Mock()
        
        action = AIAction(
            name="failing_workflow",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="failing_workflow",
            checking_point_name="test_cp"
        )
        
        data = MonitoringData(
            id="task_3",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"id": "task_3"}
        )
        
        check_result = CheckResult(
            checking_point_name="test_cp",
            checking_point_type="custom_cp",
            result_type=CheckResultType.MATCH,
            should_act=True
        )
        
        with patch.object(activity, 'execute_workflow', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = AIWorkflowResult(
                workflow_name="failing_workflow",
                checking_point_name="test_cp",
                success=False,
                execution_id="exec_789",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                error_message="Workflow execution failed",
                error_details={"reason": "API error"}
            )
            
            result = await activity.execute_workflow(action, data, check_result)
            assert result.success is False
            assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_execute_workflow_with_retry(self):
        """Test workflow execution with retry."""
        activity = Mock()
        
        action = AIAction(
            name="retry_workflow",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="retry_workflow",
            checking_point_name="test_cp",
            retry_attempts=3,
            retry_delay_seconds=60
        )
        
        data = MonitoringData(
            id="task_4",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"id": "task_4"}
        )
        
        check_result = CheckResult(
            checking_point_name="test_cp",
            checking_point_type="custom_cp",
            result_type=CheckResultType.MATCH,
            should_act=True
        )
        
        with patch.object(activity, 'execute_workflow', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = AIWorkflowResult(
                workflow_name="retry_workflow",
                checking_point_name="test_cp",
                success=True,
                execution_id="exec_retry",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                output={"result": "success after retry"}
            )
            
            result = await activity.execute_workflow(action, data, check_result)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_workflow_with_timeout(self):
        """Test workflow execution with timeout."""
        activity = Mock()
        
        action = AIAction(
            name="timeout_workflow",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="timeout_workflow",
            checking_point_name="test_cp",
            timeout_seconds=30
        )
        
        data = MonitoringData(
            id="task_5",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"id": "task_5"}
        )
        
        check_result = CheckResult(
            checking_point_name="test_cp",
            checking_point_type="custom_cp",
            result_type=CheckResultType.MATCH,
            should_act=True
        )
        
        with patch.object(activity, 'execute_workflow', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = TimeoutError("Workflow execution timed out")
            
            with pytest.raises(TimeoutError):
                await activity.execute_workflow(action, data, check_result)

    @pytest.mark.asyncio
    async def test_execute_multiple_actions(self):
        """Test executing multiple actions."""
        activity = Mock()
        
        actions = [
            AIAction(
                name=f"action_{i}",
                type=AIActionType.WORKFLOW_EXECUTION,
                workflow_name=f"workflow_{i}",
                checking_point_name="test_cp"
            )
            for i in range(3)
        ]
        
        data = MonitoringData(
            id="task_6",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"id": "task_6"}
        )
        
        check_result = CheckResult(
            checking_point_name="test_cp",
            checking_point_type="custom_cp",
            result_type=CheckResultType.MATCH,
            should_act=True
        )
        
        with patch.object(activity, 'execute_workflow', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = AIWorkflowResult(
                workflow_name="workflow_test",
                checking_point_name="test_cp",
                success=True,
                execution_id="exec_multi",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                output={"result": "success"}
            )
            
            for action in actions:
                result = await activity.execute_workflow(action, data, check_result)
                assert result.success is True

    @pytest.mark.asyncio
    async def test_workflow_with_prompt_template(self):
        """Test workflow with prompt template."""
        activity = Mock()
        
        action = AIAction(
            name="templated_workflow",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="templated_workflow",
            checking_point_name="test_cp",
            prompt_template_id="template_1",
            prompt_variables={"task_id": "task_7", "priority": "high"}
        )
        
        data = MonitoringData(
            id="task_7",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"id": "task_7"}
        )
        
        check_result = CheckResult(
            checking_point_name="test_cp",
            checking_point_type="custom_cp",
            result_type=CheckResultType.MATCH,
            should_act=True
        )
        
        with patch.object(activity, 'execute_workflow', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = AIWorkflowResult(
                workflow_name="templated_workflow",
                checking_point_name="test_cp",
                success=True,
                execution_id="exec_template",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                output={"result": "templated success"}
            )
            
            result = await activity.execute_workflow(action, data, check_result)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_workflow_with_agent_role(self):
        """Test workflow with specific agent role."""
        activity = Mock()
        
        action = AIAction(
            name="role_workflow",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="role_workflow",
            checking_point_name="test_cp",
            agent_role="analyzer"
        )
        
        data = MonitoringData(
            id="task_8",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"id": "task_8"}
        )
        
        check_result = CheckResult(
            checking_point_name="test_cp",
            checking_point_type="custom_cp",
            result_type=CheckResultType.MATCH,
            should_act=True
        )
        
        with patch.object(activity, 'execute_workflow', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = AIWorkflowResult(
                workflow_name="role_workflow",
                checking_point_name="test_cp",
                success=True,
                execution_id="exec_role",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                output={"analysis": "completed"}
            )
            
            result = await activity.execute_workflow(action, data, check_result)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_workflow_execution_duration(self):
        """Test workflow execution duration tracking."""
        activity = Mock()
        
        action = AIAction(
            name="duration_workflow",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="duration_workflow",
            checking_point_name="test_cp"
        )
        
        data = MonitoringData(
            id="task_9",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"id": "task_9"}
        )
        
        check_result = CheckResult(
            checking_point_name="test_cp",
            checking_point_type="custom_cp",
            result_type=CheckResultType.MATCH,
            should_act=True
        )
        
        start_time = datetime.utcnow()
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        with patch.object(activity, 'execute_workflow', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = AIWorkflowResult(
                workflow_name="duration_workflow",
                checking_point_name="test_cp",
                success=True,
                execution_id="exec_duration",
                started_at=start_time,
                completed_at=end_time,
                duration_ms=duration_ms,
                output={"result": "success"}
            )
            
            result = await activity.execute_workflow(action, data, check_result)
            assert result.duration_ms is not None

    @pytest.mark.asyncio
    async def test_workflow_with_escalation_action(self):
        """Test workflow with escalation action."""
        activity = Mock()
        
        action = AIAction(
            name="escalation_workflow",
            type=AIActionType.ESCALATION,
            workflow_name="escalation_workflow",
            checking_point_name="test_cp",
            priority=9
        )
        
        data = MonitoringData(
            id="task_10",
            type=MonitoringDataType.CLICKUP_TASK,
            source="clickup",
            data={"id": "task_10"}
        )
        
        check_result = CheckResult(
            checking_point_name="test_cp",
            checking_point_type="custom_cp",
            result_type=CheckResultType.MATCH,
            should_act=True
        )
        
        with patch.object(activity, 'execute_workflow', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = AIWorkflowResult(
                workflow_name="escalation_workflow",
                checking_point_name="test_cp",
                success=True,
                execution_id="exec_escalation",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                actions_taken=["escalate_to_manager", "send_notification"],
                output={"escalated": True}
            )
            
            result = await activity.execute_workflow(action, data, check_result)
            assert result.success is True
            assert len(result.actions_taken) > 0
