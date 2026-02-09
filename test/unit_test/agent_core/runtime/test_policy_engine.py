"""Unit tests for Policy Engine.

Tests cover tool policies, approval policies, safety policies, and policy enforcement.
"""

import pytest

from gearmeshing_ai.agent_core.models.actions import MCPToolInfo
from gearmeshing_ai.agent_core.runtime.policy_engine import (
    ApprovalPolicy,
    PolicyEngine,
    SafetyPolicy,
    ToolPolicy,
)
from gearmeshing_ai.agent_core.runtime.workflow_state import (
    ExecutionContext,
    WorkflowState,
    WorkflowStatus,
)


@pytest.fixture
def sample_tool() -> MCPToolInfo:
    """Create a sample tool."""
    return MCPToolInfo(
        name="run_tests",
        description="Run unit tests",
        mcp_server="test_server",
        parameters={"test_type": {"type": "string"}},
    )


@pytest.fixture
def write_tool() -> MCPToolInfo:
    """Create a write operation tool."""
    return MCPToolInfo(
        name="deploy_application",
        description="Deploy application",
        mcp_server="deploy_server",
        parameters={"environment": {"type": "string"}},
    )


@pytest.fixture
def execution_context() -> ExecutionContext:
    """Create a sample execution context."""
    return ExecutionContext(
        task_description="Run tests",
        agent_role="developer",
        user_id="user_123",
    )


@pytest.fixture
def workflow_state(execution_context: ExecutionContext) -> WorkflowState:
    """Create a sample workflow state."""
    return WorkflowState(
        run_id="run_123",
        status=WorkflowStatus(state="PENDING"),
        context=execution_context,
    )


class TestToolPolicy:
    """Tests for ToolPolicy."""

    def test_tool_policy_initialization(self) -> None:
        """Test ToolPolicy initialization."""
        policy = ToolPolicy(
            allowed_tools=["run_tests"],
            denied_tools=["delete_all"],
            read_only=False,
            max_executions=10,
        )

        assert policy.allowed_tools == ["run_tests"]
        assert policy.denied_tools == ["delete_all"]
        assert policy.read_only is False
        assert policy.max_executions == 10

    def test_tool_policy_allows_tool(self, sample_tool: MCPToolInfo) -> None:
        """Test that allowed tool is permitted."""
        policy = ToolPolicy(allowed_tools=["run_tests"])

        assert policy.is_tool_allowed(sample_tool) is True

    def test_tool_policy_denies_tool(self, sample_tool: MCPToolInfo) -> None:
        """Test that denied tool is blocked."""
        policy = ToolPolicy(denied_tools=["run_tests"])

        assert policy.is_tool_allowed(sample_tool) is False

    def test_tool_policy_read_only_blocks_write(self, write_tool: MCPToolInfo) -> None:
        """Test that read-only mode blocks write operations."""
        policy = ToolPolicy(read_only=True)

        assert policy.is_tool_allowed(write_tool) is False

    def test_tool_policy_read_only_allows_read(self, sample_tool: MCPToolInfo) -> None:
        """Test that read-only mode allows read operations."""
        policy = ToolPolicy(read_only=True)

        assert policy.is_tool_allowed(sample_tool) is True

    def test_tool_policy_execution_limit(self) -> None:
        """Test execution limit enforcement."""
        policy = ToolPolicy(max_executions=2)

        assert policy.can_execute() is True
        policy.record_execution()
        assert policy.can_execute() is True
        policy.record_execution()
        assert policy.can_execute() is False

    def test_tool_policy_no_allowed_list(self, sample_tool: MCPToolInfo) -> None:
        """Test that None allowed_tools allows all tools."""
        policy = ToolPolicy(allowed_tools=None)

        assert policy.is_tool_allowed(sample_tool) is True


class TestApprovalPolicy:
    """Tests for ApprovalPolicy."""

    def test_approval_policy_initialization(self) -> None:
        """Test ApprovalPolicy initialization."""
        policy = ApprovalPolicy(
            require_approval_for_all=True,
            high_risk_tools=["deploy"],
            approval_timeout=7200,
        )

        assert policy.require_approval_for_all is True
        assert policy.high_risk_tools == ["deploy"]
        assert policy.approval_timeout == 7200

    def test_approval_policy_requires_all(self, sample_tool: MCPToolInfo) -> None:
        """Test that all tools require approval when flag is set."""
        policy = ApprovalPolicy(require_approval_for_all=True)

        assert policy.requires_approval(sample_tool) is True

    def test_approval_policy_high_risk_tool(self) -> None:
        """Test that high-risk tools require approval."""
        policy = ApprovalPolicy(high_risk_tools=["deploy"])
        tool = MCPToolInfo(
            name="deploy",
            description="Deploy app",
            mcp_server="deploy_server",
            parameters={},
        )

        assert policy.requires_approval(tool) is True

    def test_approval_policy_normal_tool(self, sample_tool: MCPToolInfo) -> None:
        """Test that normal tools don't require approval."""
        policy = ApprovalPolicy(high_risk_tools=["deploy"])

        assert policy.requires_approval(sample_tool) is False


class TestSafetyPolicy:
    """Tests for SafetyPolicy."""

    def test_safety_policy_initialization(self) -> None:
        """Test SafetyPolicy initialization."""
        policy = SafetyPolicy(
            max_concurrent_executions=3,
            timeout_per_execution=600,
            allowed_roles=["developer", "admin"],
        )

        assert policy.max_concurrent_executions == 3
        assert policy.timeout_per_execution == 600
        assert policy.allowed_roles == ["developer", "admin"]

    def test_safety_policy_role_allowed(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        """Test that allowed role is permitted."""
        policy = SafetyPolicy(allowed_roles=["developer"])

        assert policy.is_role_allowed(execution_context) is True

    def test_safety_policy_role_denied(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        """Test that denied role is blocked."""
        policy = SafetyPolicy(allowed_roles=["admin"])

        assert policy.is_role_allowed(execution_context) is False

    def test_safety_policy_no_role_restrictions(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        """Test that empty allowed_roles allows all roles."""
        policy = SafetyPolicy(allowed_roles=[])

        assert policy.is_role_allowed(execution_context) is True

    def test_safety_policy_concurrent_limit(self) -> None:
        """Test concurrent execution limit."""
        policy = SafetyPolicy(max_concurrent_executions=2)

        assert policy.can_execute_concurrently() is True
        policy.start_execution()
        assert policy.can_execute_concurrently() is True
        policy.start_execution()
        assert policy.can_execute_concurrently() is False

    def test_safety_policy_execution_tracking(self) -> None:
        """Test execution start and end tracking."""
        policy = SafetyPolicy(max_concurrent_executions=2)

        policy.start_execution()
        policy.start_execution()
        assert policy.can_execute_concurrently() is False

        policy.end_execution()
        assert policy.can_execute_concurrently() is True

        policy.end_execution()
        assert policy.can_execute_concurrently() is True


class TestPolicyEngine:
    """Tests for PolicyEngine."""

    def test_policy_engine_initialization(self) -> None:
        """Test PolicyEngine initialization."""
        tool_policy = ToolPolicy()
        approval_policy = ApprovalPolicy()
        safety_policy = SafetyPolicy()

        engine = PolicyEngine(
            tool_policy=tool_policy,
            approval_policy=approval_policy,
            safety_policy=safety_policy,
        )

        assert engine.tool_policy is tool_policy
        assert engine.approval_policy is approval_policy
        assert engine.safety_policy is safety_policy

    def test_policy_engine_default_policies(self) -> None:
        """Test PolicyEngine with default policies."""
        engine = PolicyEngine()

        assert engine.tool_policy is not None
        assert engine.approval_policy is not None
        assert engine.safety_policy is not None

    def test_policy_engine_validate_tool_access_allowed(
        self,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test tool access validation when allowed."""
        engine = PolicyEngine()

        allowed, reason = engine.validate_tool_access(sample_tool, execution_context)

        assert allowed is True
        assert "allowed" in reason.lower()

    def test_policy_engine_validate_tool_access_denied(
        self,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test tool access validation when denied."""
        engine = PolicyEngine(
            tool_policy=ToolPolicy(denied_tools=["run_tests"])
        )

        allowed, reason = engine.validate_tool_access(sample_tool, execution_context)

        assert allowed is False
        assert "not allowed" in reason.lower()

    def test_policy_engine_requires_approval(self, sample_tool: MCPToolInfo) -> None:
        """Test approval requirement check."""
        engine = PolicyEngine(
            approval_policy=ApprovalPolicy(require_approval_for_all=True)
        )

        assert engine.requires_approval(sample_tool) is True

    def test_policy_engine_execution_tracking(self) -> None:
        """Test execution recording."""
        engine = PolicyEngine()

        engine.record_execution()
        assert engine.safety_policy._concurrent_count == 1

        engine.end_execution()
        assert engine.safety_policy._concurrent_count == 0

    def test_policy_engine_validate_workflow_state(
        self,
        workflow_state: WorkflowState,
    ) -> None:
        """Test workflow state validation."""
        engine = PolicyEngine()

        valid, reason = engine.validate_workflow_state(workflow_state)

        assert valid is True
        assert "valid" in reason.lower()

    def test_policy_engine_validate_workflow_state_denied_role(
        self,
        workflow_state: WorkflowState,
    ) -> None:
        """Test workflow state validation with denied role."""
        engine = PolicyEngine(
            safety_policy=SafetyPolicy(allowed_roles=["admin"])
        )

        valid, reason = engine.validate_workflow_state(workflow_state)

        assert valid is False
        assert "not allowed" in reason.lower()

    def test_policy_engine_combined_policies(
        self,
        sample_tool: MCPToolInfo,
        execution_context: ExecutionContext,
    ) -> None:
        """Test PolicyEngine with combined policies."""
        engine = PolicyEngine(
            tool_policy=ToolPolicy(allowed_tools=["run_tests"]),
            approval_policy=ApprovalPolicy(high_risk_tools=["deploy"]),
            safety_policy=SafetyPolicy(allowed_roles=["developer"]),
        )

        # Tool should be allowed
        allowed, _ = engine.validate_tool_access(sample_tool, execution_context)
        assert allowed is True

        # Tool should not require approval
        assert engine.requires_approval(sample_tool) is False

        # Workflow state should be valid
        state = WorkflowState(
            run_id="run_123",
            status=WorkflowStatus(state="PENDING"),
            context=execution_context,
        )
        valid, _ = engine.validate_workflow_state(state)
        assert valid is True
