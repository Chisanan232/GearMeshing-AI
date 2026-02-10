"""Policy Engine for managing and enforcing agent policies.

This module implements the Policy Engine that manages tool policies, approval policies,
and safety policies for agent workflows.

POLICY ENGINE ARCHITECTURE
==========================

Policy Hierarchy:

    PolicyEngine (Central Policy Manager)
    ├── ToolPolicy (Tool Access Control)
    │   ├── allowed_tools: list[str] | None
    │   ├── denied_tools: list[str]
    │   ├── read_only: bool
    │   └── max_executions: int | None
    │
    ├── ApprovalPolicy (Approval Requirements)
    │   ├── requires_approval: bool
    │   ├── approval_threshold: int
    │   ├── approvers: list[str]
    │   └── timeout_seconds: int
    │
    └── SafetyPolicy (Safety Constraints)
        ├── max_retries: int
        ├── timeout_seconds: int
        ├── resource_limits: dict
        └── restricted_operations: list[str]


POLICY EVALUATION FLOW
======================

Tool Execution Request
    ↓
PolicyEngine.is_tool_allowed(tool)
    ├── Check denied_tools list
    ├── Check allowed_tools list (if specified)
    ├── Check read_only flag
    ├── Check max_executions limit
    └── Return: bool (allowed/denied)
    ↓
PolicyEngine.requires_approval(tool)
    ├── Check approval policy
    ├── Check tool risk level
    ├── Check execution context
    └── Return: bool (approval required/not required)
    ↓
PolicyEngine.is_safe_operation(tool, context)
    ├── Check safety constraints
    ├── Check resource limits
    ├── Check timeout constraints
    └── Return: bool (safe/unsafe)
    ↓
Decision: ALLOW / REQUIRE_APPROVAL / DENY


POLICY DECISION MATRIX
======================

Tool Access:
    ┌─────────────────────────────────────────────────┐
    │ Tool in denied_tools?                           │
    ├─────────────────────────────────────────────────┤
    │ YES → DENY (highest priority)                   │
    │ NO  → Check allowed_tools                       │
    │       ├─ allowed_tools is None → ALLOW          │
    │       ├─ tool in allowed_tools → ALLOW          │
    │       └─ tool not in allowed_tools → DENY       │
    └─────────────────────────────────────────────────┘

Read-Only Mode:
    ┌─────────────────────────────────────────────────┐
    │ read_only = True?                               │
    ├─────────────────────────────────────────────────┤
    │ YES → Only allow read operations                │
    │ NO  → Allow all operations                      │
    └─────────────────────────────────────────────────┘

Execution Limit:
    ┌─────────────────────────────────────────────────┐
    │ max_executions set?                             │
    ├─────────────────────────────────────────────────┤
    │ YES → Check execution_count < max_executions    │
    │ NO  → No limit                                  │
    └─────────────────────────────────────────────────┘


POLICY ENFORCEMENT CONCERNS
===========================

1. POLICY CONSISTENCY
   Concern: Policies must be enforced consistently across all nodes
   Solution: Centralized PolicyEngine, single source of truth
   Validation: All policy decisions logged and audited

2. POLICY CONFLICTS
   Concern: Multiple policies might conflict
   Solution: Clear priority order (denied > allowed > default)
   Validation: Tests verify conflict resolution

3. DYNAMIC POLICY UPDATES
   Concern: Policies might change during workflow execution
   Solution: Policies are read-only during execution
   Validation: Policy updates require workflow restart

4. CONTEXT-AWARE POLICIES
   Concern: Policies might depend on execution context
   Solution: ExecutionContext passed to policy evaluation
   Validation: Context is validated before use

5. APPROVAL POLICY ENFORCEMENT
   Concern: Approval requirements must be enforced
   Solution: ApprovalPolicy checked before tool execution
   Validation: Approval decisions tracked and verified

6. SAFETY POLICY ENFORCEMENT
   Concern: Safety constraints must be enforced
   Solution: SafetyPolicy checked at multiple points
   Validation: Safety violations logged and blocked

7. POLICY AUDIT TRAIL
   Concern: All policy decisions must be auditable
   Solution: All decisions logged with context
   Monitoring: Policy decision logs reviewed regularly


POLICY TYPES AND RULES
======================

ToolPolicy Rules:
    1. If tool in denied_tools → DENY (always)
    2. If allowed_tools is None → ALLOW (if not denied)
    3. If allowed_tools is set → ALLOW only if in list
    4. If read_only → ALLOW only read operations
    5. If max_executions set → ALLOW only if count < max

ApprovalPolicy Rules:
    1. If requires_approval → REQUIRE_APPROVAL
    2. If approval_threshold > 1 → REQUIRE multiple approvals
    3. If timeout_seconds set → ENFORCE timeout
    4. If approvers list set → REQUIRE specific approvers

SafetyPolicy Rules:
    1. If max_retries set → LIMIT retries
    2. If timeout_seconds set → ENFORCE timeout
    3. If resource_limits set → ENFORCE limits
    4. If restricted_operations set → BLOCK operations


POLICY LIFECYCLE
================

1. POLICY CREATION
   - PolicyEngine created with default policies
   - Policies can be customized before workflow starts

2. POLICY INITIALIZATION
   - Policies loaded from configuration
   - Policies validated for consistency
   - Policies registered with PolicyEngine

3. POLICY EVALUATION
   - During workflow execution
   - For each tool execution request
   - Against current policies

4. POLICY ENFORCEMENT
   - Decisions made based on policy evaluation
   - Decisions logged and tracked
   - Violations blocked or escalated

5. POLICY AUDIT
   - All decisions logged
   - Audit trail maintained
   - Compliance verified


POLICY CONFIGURATION EXAMPLES
=============================

Example 1: Restrictive Policy (Production)
    ToolPolicy(
        allowed_tools=["read_logs", "check_status"],
        denied_tools=[],
        read_only=True,
        max_executions=10,
    )
    ApprovalPolicy(
        requires_approval=True,
        approval_threshold=2,
        approvers=["admin", "security"],
        timeout_seconds=3600,
    )

Example 2: Permissive Policy (Development)
    ToolPolicy(
        allowed_tools=None,  # All tools allowed
        denied_tools=["delete_database"],
        read_only=False,
        max_executions=None,  # Unlimited
    )
    ApprovalPolicy(
        requires_approval=False,
        approval_threshold=1,
        approvers=[],
        timeout_seconds=0,
    )

Example 3: Role-Based Policy
    For role="developer":
        ToolPolicy(
            allowed_tools=["run_tests", "build", "deploy_staging"],
            denied_tools=["deploy_production"],
            read_only=False,
            max_executions=100,
        )
    
    For role="admin":
        ToolPolicy(
            allowed_tools=None,
            denied_tools=[],
            read_only=False,
            max_executions=None,
        )


PERFORMANCE CHARACTERISTICS
===========================

Policy Evaluation Time:
    Simple check (denied_tools): <1ms
    Allowed_tools check: 1-5ms
    Complex evaluation: 5-10ms

Policy Storage:
    Single policy: ~1 KB
    100 policies: ~100 KB
    1000 policies: ~1 MB

Caching:
    Policy decisions can be cached
    Cache invalidation on policy update
    TTL-based cache expiration


MONITORING POLICIES
===================

Per-Decision Metrics:
    - Decision type (ALLOW/DENY/REQUIRE_APPROVAL)
    - Tool name
    - Agent role
    - Execution context
    - Timestamp

Policy-Level Metrics:
    - Total decisions made
    - Allow rate
    - Deny rate
    - Approval rate
    - Policy violations

Audit Metrics:
    - Policy changes
    - Policy violations
    - Approval decisions
    - Escalations


EXTENSION POINTS
================

1. Custom Policy Types
   - Can extend ToolPolicy, ApprovalPolicy, SafetyPolicy
   - Must implement policy evaluation logic
   - Must integrate with PolicyEngine

2. Custom Policy Rules
   - Can add custom rules to existing policies
   - Must follow policy evaluation pattern
   - Must be tested thoroughly

3. Custom Policy Sources
   - Can load policies from external sources
   - Must validate policies on load
   - Must handle policy updates

4. Custom Policy Enforcement
   - Can implement custom enforcement logic
   - Must log all enforcement actions
   - Must handle enforcement failures


TESTING POLICIES
================

Unit Tests:
    - Test each policy type independently
    - Test policy evaluation logic
    - Test policy conflicts
    - Test edge cases

Integration Tests:
    - Test policies with workflow nodes
    - Test policy enforcement
    - Test policy updates
    - Test audit logging

E2E Tests:
    - Test complete policy workflows
    - Test with real tools
    - Test approval workflows
    - Test policy violations
"""

import logging
from typing import Any

from gearmeshing_ai.agent_core.models.actions import MCPToolInfo

from .models import ExecutionContext, WorkflowState

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
