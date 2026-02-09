"""Policy Engine for managing and enforcing agent policies.

This module implements the Policy Engine that manages tool policies, approval policies,
and safety policies for agent workflows.
"""

import logging
from typing import Any

from gearmeshing_ai.agent_core.models.actions import MCPToolInfo

from .workflow_state import ExecutionContext, WorkflowState

logger = logging.getLogger(__name__)


class ToolPolicy:
    """Policy for controlling tool access and execution.

    Attributes:
        allowed_tools: List of allowed tool names (None = all allowed)
        denied_tools: List of denied tool names
        read_only: If True, only read operations allowed
        max_executions: Maximum number of tool executions allowed

    """

    def __init__(
        self,
        allowed_tools: list[str] | None = None,
        denied_tools: list[str] | None = None,
        read_only: bool = False,
        max_executions: int | None = None,
    ) -> None:
        """Initialize ToolPolicy.

        Args:
            allowed_tools: List of allowed tool names
            denied_tools: List of denied tool names
            read_only: If True, only read operations allowed
            max_executions: Maximum number of tool executions

        """
        self.allowed_tools = allowed_tools
        self.denied_tools = denied_tools or []
        self.read_only = read_only
        self.max_executions = max_executions
        self._execution_count = 0

    def is_tool_allowed(self, tool: MCPToolInfo) -> bool:
        """Check if a tool is allowed by this policy.

        Args:
            tool: Tool to check

        Returns:
            True if tool is allowed, False otherwise

        """
        # Check denied list first
        if tool.name in self.denied_tools:
            logger.debug(f"Tool {tool.name} is in denied list")
            return False

        # Check allowed list
        if self.allowed_tools is not None:
            if tool.name not in self.allowed_tools:
                logger.debug(f"Tool {tool.name} is not in allowed list")
                return False

        # Check read-only constraint
        if self.read_only:
            # Tools that modify state are not allowed in read-only mode
            if self._is_write_operation(tool):
                logger.debug(f"Tool {tool.name} is write operation in read-only mode")
                return False

        return True

    def can_execute(self) -> bool:
        """Check if another execution is allowed.

        Returns:
            True if execution is allowed, False otherwise

        """
        if self.max_executions is None:
            return True

        if self._execution_count >= self.max_executions:
            logger.warning(f"Max executions ({self.max_executions}) reached")
            return False

        return True

    def record_execution(self) -> None:
        """Record a tool execution."""
        self._execution_count += 1
        logger.debug(f"Recorded execution: {self._execution_count}/{self.max_executions}")

    def _is_write_operation(self, tool: MCPToolInfo) -> bool:
        """Check if a tool performs write operations.

        Args:
            tool: Tool to check

        Returns:
            True if tool performs write operations

        """
        # Simple heuristic: check tool name for write-like operations
        write_keywords = ["write", "delete", "remove", "update", "create", "deploy", "execute"]
        tool_name_lower = tool.name.lower()
        return any(keyword in tool_name_lower for keyword in write_keywords)


class ApprovalPolicy:
    """Policy for determining when approvals are required.

    Attributes:
        require_approval_for_all: If True, all actions require approval
        high_risk_tools: Tools that require approval
        approval_timeout: Timeout for approval in seconds

    """

    def __init__(
        self,
        require_approval_for_all: bool = False,
        high_risk_tools: list[str] | None = None,
        approval_timeout: int = 3600,
    ) -> None:
        """Initialize ApprovalPolicy.

        Args:
            require_approval_for_all: If True, all actions require approval
            high_risk_tools: Tools that require approval
            approval_timeout: Timeout for approval in seconds

        """
        self.require_approval_for_all = require_approval_for_all
        self.high_risk_tools = high_risk_tools or []
        self.approval_timeout = approval_timeout

    def requires_approval(self, tool: MCPToolInfo) -> bool:
        """Check if a tool requires approval.

        Args:
            tool: Tool to check

        Returns:
            True if approval is required, False otherwise

        """
        if self.require_approval_for_all:
            logger.debug("All actions require approval")
            return True

        if tool.name in self.high_risk_tools:
            logger.debug(f"Tool {tool.name} is high-risk and requires approval")
            return True

        return False


class SafetyPolicy:
    """Policy for safety constraints and limits.

    Attributes:
        max_concurrent_executions: Maximum concurrent tool executions
        timeout_per_execution: Timeout per execution in seconds
        allowed_roles: Roles allowed to execute tools

    """

    def __init__(
        self,
        max_concurrent_executions: int = 5,
        timeout_per_execution: int = 300,
        allowed_roles: list[str] | None = None,
    ) -> None:
        """Initialize SafetyPolicy.

        Args:
            max_concurrent_executions: Maximum concurrent executions
            timeout_per_execution: Timeout per execution in seconds
            allowed_roles: Roles allowed to execute tools

        """
        self.max_concurrent_executions = max_concurrent_executions
        self.timeout_per_execution = timeout_per_execution
        self.allowed_roles = allowed_roles or []
        self._concurrent_count = 0

    def is_role_allowed(self, context: ExecutionContext) -> bool:
        """Check if a role is allowed to execute tools.

        Args:
            context: Execution context

        Returns:
            True if role is allowed, False otherwise

        """
        if not self.allowed_roles:
            # No restrictions if allowed_roles is empty
            return True

        if context.agent_role in self.allowed_roles:
            logger.debug(f"Role {context.agent_role} is allowed")
            return True

        logger.warning(f"Role {context.agent_role} is not allowed")
        return False

    def can_execute_concurrently(self) -> bool:
        """Check if another concurrent execution is allowed.

        Returns:
            True if concurrent execution is allowed, False otherwise

        """
        if self._concurrent_count >= self.max_concurrent_executions:
            logger.warning(f"Max concurrent executions ({self.max_concurrent_executions}) reached")
            return False

        return True

    def start_execution(self) -> None:
        """Record the start of an execution."""
        self._concurrent_count += 1
        logger.debug(f"Started execution: {self._concurrent_count}/{self.max_concurrent_executions}")

    def end_execution(self) -> None:
        """Record the end of an execution."""
        if self._concurrent_count > 0:
            self._concurrent_count -= 1
            logger.debug(f"Ended execution: {self._concurrent_count}/{self.max_concurrent_executions}")


class PolicyEngine:
    """Main policy engine for managing and enforcing policies.

    Attributes:
        tool_policy: Tool access policy
        approval_policy: Approval requirement policy
        safety_policy: Safety constraints policy

    """

    def __init__(
        self,
        tool_policy: ToolPolicy | None = None,
        approval_policy: ApprovalPolicy | None = None,
        safety_policy: SafetyPolicy | None = None,
    ) -> None:
        """Initialize PolicyEngine.

        Args:
            tool_policy: Tool access policy
            approval_policy: Approval requirement policy
            safety_policy: Safety constraints policy

        """
        self.tool_policy = tool_policy or ToolPolicy()
        self.approval_policy = approval_policy or ApprovalPolicy()
        self.safety_policy = safety_policy or SafetyPolicy()
        logger.debug("PolicyEngine initialized")

    def validate_tool_access(
        self,
        tool: MCPToolInfo,
        context: ExecutionContext,
    ) -> tuple[bool, str]:
        """Validate if a tool can be accessed.

        Args:
            tool: Tool to validate
            context: Execution context

        Returns:
            Tuple of (allowed, reason)

        """
        logger.debug(f"Validating tool access: {tool.name} for role={context.agent_role}")

        # Check safety policy
        if not self.safety_policy.is_role_allowed(context):
            return False, f"Role {context.agent_role} is not allowed"

        # Check tool policy
        if not self.tool_policy.is_tool_allowed(tool):
            return False, f"Tool {tool.name} is not allowed"

        # Check execution limits
        if not self.tool_policy.can_execute():
            return False, "Maximum tool executions reached"

        if not self.safety_policy.can_execute_concurrently():
            return False, "Maximum concurrent executions reached"

        return True, "Tool access allowed"

    def requires_approval(self, tool: MCPToolInfo) -> bool:
        """Check if a tool requires approval.

        Args:
            tool: Tool to check

        Returns:
            True if approval is required, False otherwise

        """
        return self.approval_policy.requires_approval(tool)

    def record_execution(self) -> None:
        """Record a tool execution."""
        self.tool_policy.record_execution()
        self.safety_policy.start_execution()

    def end_execution(self) -> None:
        """Record the end of a tool execution."""
        self.safety_policy.end_execution()

    def validate_workflow_state(
        self,
        state: WorkflowState,
    ) -> tuple[bool, str]:
        """Validate workflow state against policies.

        Args:
            state: Workflow state to validate

        Returns:
            Tuple of (valid, reason)

        """
        logger.debug(f"Validating workflow state for run_id={state.run_id}")

        # Check role is allowed
        if not self.safety_policy.is_role_allowed(state.context):
            return False, f"Role {state.context.agent_role} is not allowed"

        return True, "Workflow state is valid"
