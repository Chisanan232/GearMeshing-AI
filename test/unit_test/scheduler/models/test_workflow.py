"""Unit tests for workflow models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from gearmeshing_ai.scheduler.models.workflow import (
    AIAction,
    AIActionType,
)


class TestAIActionType:
    """Test AIActionType enum."""

    def test_all_enum_values(self):
        """Test that all enum values are defined."""
        assert AIActionType.WORKFLOW_EXECUTION.value == "workflow_execution"
        assert AIActionType.TASK_ASSIGNMENT.value == "task_assignment"
        assert AIActionType.NOTIFICATION.value == "notification"
        assert AIActionType.DATA_PROCESSING.value == "data_processing"
        assert AIActionType.ESCALATION.value == "escalation"
        assert AIActionType.CUSTOM_ACTION.value == "custom_action"

    def test_get_all_values(self):
        """Test get_all_values method."""
        values = AIActionType.get_all_values()
        assert len(values) == 6
        assert "workflow_execution" in values


class TestAIAction:
    """Test AIAction model."""

    def test_create_basic_action(self):
        """Test creating a basic AI action."""
        action = AIAction(
            name="test_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="test_workflow",
            checking_point_name="test_cp"
        )
        assert action.name == "test_action"
        assert action.type == AIActionType.WORKFLOW_EXECUTION
        assert action.workflow_name == "test_workflow"
        assert action.checking_point_name == "test_cp"

    def test_default_timeout(self):
        """Test default timeout value."""
        action = AIAction(
            name="test_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="test_workflow",
            checking_point_name="test_cp"
        )
        assert action.timeout_seconds == 600

    def test_custom_timeout(self):
        """Test custom timeout value."""
        action = AIAction(
            name="test_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="test_workflow",
            checking_point_name="test_cp",
            timeout_seconds=1200
        )
        assert action.timeout_seconds == 1200

    def test_timeout_validation_positive(self):
        """Test that timeout must be positive."""
        with pytest.raises(ValidationError):
            AIAction(
                name="test_action",
                type=AIActionType.WORKFLOW_EXECUTION,
                workflow_name="test_workflow",
                checking_point_name="test_cp",
                timeout_seconds=0
            )

    def test_empty_name_validation(self):
        """Test that empty name is rejected."""
        with pytest.raises(ValidationError):
            AIAction(
                name="",
                type=AIActionType.WORKFLOW_EXECUTION,
                workflow_name="test_workflow",
                checking_point_name="test_cp"
            )

    def test_empty_workflow_name_validation(self):
        """Test that empty workflow name is rejected."""
        with pytest.raises(ValidationError):
            AIAction(
                name="test_action",
                type=AIActionType.WORKFLOW_EXECUTION,
                workflow_name="",
                checking_point_name="test_cp"
            )

    def test_default_retry_attempts(self):
        """Test default retry attempts."""
        action = AIAction(
            name="test_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="test_workflow",
            checking_point_name="test_cp"
        )
        assert action.retry_attempts == 3

    def test_default_retry_delay(self):
        """Test default retry delay."""
        action = AIAction(
            name="test_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="test_workflow",
            checking_point_name="test_cp"
        )
        assert action.retry_delay_seconds == 60

    def test_approval_not_required_by_default(self):
        """Test that approval is not required by default."""
        action = AIAction(
            name="test_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="test_workflow",
            checking_point_name="test_cp"
        )
        assert action.approval_required is False

    def test_approval_required(self):
        """Test setting approval required."""
        action = AIAction(
            name="test_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="test_workflow",
            checking_point_name="test_cp",
            approval_required=True
        )
        assert action.approval_required is True

    def test_default_approval_timeout(self):
        """Test default approval timeout."""
        action = AIAction(
            name="test_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="test_workflow",
            checking_point_name="test_cp"
        )
        assert action.approval_timeout_seconds == 3600

    def test_approval_timeout_validation(self):
        """Test that approval timeout must be at least 60 seconds."""
        with pytest.raises(ValidationError):
            AIAction(
                name="test_action",
                type=AIActionType.WORKFLOW_EXECUTION,
                workflow_name="test_workflow",
                checking_point_name="test_cp",
                approval_timeout_seconds=30
            )

    def test_default_priority(self):
        """Test default priority."""
        action = AIAction(
            name="test_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="test_workflow",
            checking_point_name="test_cp"
        )
        assert action.priority == 5

    def test_priority_validation_min(self):
        """Test that priority must be at least 1."""
        with pytest.raises(ValidationError):
            AIAction(
                name="test_action",
                type=AIActionType.WORKFLOW_EXECUTION,
                workflow_name="test_workflow",
                checking_point_name="test_cp",
                priority=0
            )

    def test_priority_validation_max(self):
        """Test that priority must be at most 10."""
        with pytest.raises(ValidationError):
            AIAction(
                name="test_action",
                type=AIActionType.WORKFLOW_EXECUTION,
                workflow_name="test_workflow",
                checking_point_name="test_cp",
                priority=11
            )

    def test_parameters_field(self):
        """Test parameters field."""
        action = AIAction(
            name="test_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="test_workflow",
            checking_point_name="test_cp",
            parameters={"key": "value"}
        )
        assert action.parameters["key"] == "value"

    def test_prompt_template_id(self):
        """Test prompt template ID."""
        action = AIAction(
            name="test_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="test_workflow",
            checking_point_name="test_cp",
            prompt_template_id="template_123"
        )
        assert action.prompt_template_id == "template_123"

    def test_agent_role(self):
        """Test agent role."""
        action = AIAction(
            name="test_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="test_workflow",
            checking_point_name="test_cp",
            agent_role="dev"
        )
        assert action.agent_role == "dev"

    def test_scheduled_at(self):
        """Test scheduled_at field."""
        now = datetime.utcnow()
        action = AIAction(
            name="test_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="test_workflow",
            checking_point_name="test_cp",
            scheduled_at=now
        )
        assert action.scheduled_at == now

    def test_execution_id(self):
        """Test execution ID."""
        action = AIAction(
            name="test_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="test_workflow",
            checking_point_name="test_cp",
            execution_id="exec_123"
        )
        assert action.execution_id == "exec_123"

    def test_parent_execution_id(self):
        """Test parent execution ID."""
        action = AIAction(
            name="test_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="test_workflow",
            checking_point_name="test_cp",
            parent_execution_id="parent_exec_123"
        )
        assert action.parent_execution_id == "parent_exec_123"

    def test_get_summary(self):
        """Test get_summary method."""
        action = AIAction(
            name="test_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="test_workflow",
            checking_point_name="test_cp"
        )
        summary = action.get_summary()
        assert summary["name"] == "test_action"
        assert summary["type"] == "workflow_execution"
        assert summary["workflow_name"] == "test_workflow"
        assert summary["checking_point_name"] == "test_cp"

    def test_prompt_variables(self):
        """Test prompt variables field."""
        action = AIAction(
            name="test_action",
            type=AIActionType.WORKFLOW_EXECUTION,
            workflow_name="test_workflow",
            checking_point_name="test_cp",
            prompt_variables={"var1": "value1", "var2": "value2"}
        )
        assert action.prompt_variables["var1"] == "value1"
        assert action.prompt_variables["var2"] == "value2"
