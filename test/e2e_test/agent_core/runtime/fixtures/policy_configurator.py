"""PolicyConfigurator fixture for E2E tests - configures policies for different scenarios."""

from gearmeshing_ai.agent_core.runtime.policy_engine import PolicyEngine, ToolPolicy


class PolicyConfigurator:
    """Configure policies for testing."""

    def __init__(self):
        """Initialize policy configurator."""
        self.policy_engine = PolicyEngine()

    def configure_simple_read_only(self) -> PolicyEngine:
        """Configure for simple read-only task."""
        self.policy_engine.tool_policy = ToolPolicy(
            allowed_tools=["file_read"],
            denied_tools=[],
        )
        self.policy_engine.approval_policy.require_approval_for_all = False
        return self.policy_engine

    def configure_deployment_with_approval(self) -> PolicyEngine:
        """Configure for deployment with approval."""
        self.policy_engine.tool_policy = ToolPolicy(
            allowed_tools=["deploy", "deploy_production", "run_tests"],
            denied_tools=[],
        )
        self.policy_engine.approval_policy.require_approval_for_all = False
        self.policy_engine.approval_policy.high_risk_tools = ["deploy", "deploy_production"]
        self.policy_engine.approval_policy.approval_timeout = 3600
        return self.policy_engine

    def configure_deny_delete(self) -> PolicyEngine:
        """Configure to deny delete operations."""
        self.policy_engine.tool_policy = ToolPolicy(
            allowed_tools=["file_read", "file_write"],
            denied_tools=["delete_file"],
        )
        self.policy_engine.approval_policy.require_approval_for_all = False
        return self.policy_engine

    def configure_developer_role(self) -> PolicyEngine:
        """Configure for developer role."""
        self.policy_engine.tool_policy = ToolPolicy(
            allowed_tools=["file_read", "run_tests", "deploy_staging"],
            denied_tools=["deploy_production", "delete_file"],
        )
        self.policy_engine.approval_policy.require_approval_for_all = False
        return self.policy_engine

    def configure_admin_role(self) -> PolicyEngine:
        """Configure for admin role."""
        self.policy_engine.tool_policy = ToolPolicy(
            allowed_tools=None,  # All tools allowed
            denied_tools=[],
        )
        self.policy_engine.approval_policy.require_approval_for_all = False
        self.policy_engine.approval_policy.high_risk_tools = [
            "deploy",
            "deploy_production",
            "delete_file",
            "backup_database",
        ]
        return self.policy_engine

    def configure_execution_limit(self, limit: int) -> PolicyEngine:
        """Configure execution limit."""
        self.policy_engine.tool_policy = ToolPolicy(
            allowed_tools=None,
            denied_tools=[],
            max_executions=limit,
        )
        return self.policy_engine

    def configure_multi_step_workflow(self) -> PolicyEngine:
        """Configure for multi-step workflow."""
        self.policy_engine.tool_policy = ToolPolicy(
            allowed_tools=["file_read", "run_tests"],
            denied_tools=[],
        )
        self.policy_engine.approval_policy.require_approval_for_all = False
        return self.policy_engine

    def configure_with_high_risk_tools(self, tools: list) -> PolicyEngine:
        """Configure with specific high-risk tools."""
        self.policy_engine.approval_policy.high_risk_tools = tools
        self.policy_engine.approval_policy.require_approval_for_all = False
        return self.policy_engine

    def get_policy_engine(self) -> PolicyEngine:
        """Get configured policy engine."""
        return self.policy_engine

    def reset(self) -> None:
        """Reset to default policy."""
        self.policy_engine = PolicyEngine()
