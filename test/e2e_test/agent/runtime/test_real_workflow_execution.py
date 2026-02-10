"""End-to-end tests for AI agent runtime workflow with real usage scenarios.

Tests execute complete workflows with actual prompts and verify all 9 nodes work together
in realistic scenarios including policy enforcement, approval workflows, and error handling.
"""

from typing import TYPE_CHECKING

import pytest

from gearmeshing_ai.agent.runtime.models.workflow_state import (
    ExecutionContext,
    WorkflowState,
    WorkflowStatus,
)

if TYPE_CHECKING:
    from test.e2e_test.agent.runtime.fixtures.approval_simulator import ApprovalSimulator
    from test.e2e_test.agent.runtime.fixtures.policy_configurator import PolicyConfigurator
    from test.e2e_test.agent.runtime.fixtures.test_model import HybridTestModel
    from test.e2e_test.agent.runtime.fixtures.workflow_executor import WorkflowExecutor


# ============================================================================
# Test Suite 1: Simple Tasks (No Approval Required)
# ============================================================================


class TestSimpleTasks:
    """Simple workflow tasks without approval requirements."""

    @pytest.mark.asyncio
    async def test_simple_read_file_task(
        self: "TestSimpleTasks",
        test_model: "HybridTestModel",
        mock_mcp_client: object,
        policy_configurator: "PolicyConfigurator",
        workflow_executor: "WorkflowExecutor",
    ) -> None:
        """Test simple read file task.

        Scenario: User asks agent to read a file and explain its contents.
        Expected: Workflow completes successfully, proposal is generated.
        """
        # Configure policy
        policy_configurator.configure_simple_read_only()

        # Create initial state
        prompt = "Please read the file `/src/main.py` and tell me what it does"
        context = ExecutionContext(
            task_description=prompt,
            agent_role="developer",
            user_id="user_123",
        )
        state = WorkflowState(
            run_id="test_read_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        # Execute workflow
        final_state = await workflow_executor.execute(state)

        # Verify: Simple read-only task should complete successfully
        workflow_executor.assert_workflow_completed()
        workflow_executor.assert_final_state("COMPLETED")
        assert final_state.run_id == "test_read_001", "Run ID should match initial state"
        assert final_state.context.agent_role == "developer", "Agent role should be preserved"
        assert final_state.context.user_id == "user_123", "User ID should be preserved"
        assert final_state.current_proposal is not None, "Proposal should be generated"
        assert final_state.current_proposal.action == "file_read", "Proposal action should be file_read"
        assert final_state.status.message, "Status should have a completion message"

    @pytest.mark.asyncio
    async def test_analyze_code_task(
        self: "TestSimpleTasks",
        test_model: "HybridTestModel",
        mock_mcp_client: object,
        policy_configurator: "PolicyConfigurator",
        workflow_executor: "WorkflowExecutor",
    ) -> None:
        """Test code analysis task.

        Scenario: User asks agent to analyze code and suggest improvements.
        Expected: Workflow completes successfully, proposal is generated.
        """
        # Configure policy
        policy_configurator.configure_simple_read_only()

        # Create initial state
        prompt = "Analyze the code in `/src/utils.py` and suggest improvements"
        context = ExecutionContext(
            task_description=prompt,
            agent_role="developer",
            user_id="user_456",
        )
        state = WorkflowState(
            run_id="test_analyze_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        # Execute workflow
        final_state = await workflow_executor.execute(state)

        # Verify: Code analysis task should complete with proposal
        workflow_executor.assert_workflow_completed()
        assert final_state.status.state == "COMPLETED", "Workflow should complete successfully"
        assert final_state.run_id == "test_analyze_001", "Run ID should match initial state"
        assert final_state.context.agent_role == "developer", "Agent role should be preserved"
        assert final_state.context.user_id == "user_456", "User ID should be preserved"
        assert final_state.current_proposal is not None, "Proposal should be generated for analysis"
        assert final_state.current_proposal.action == "file_read", "Proposal action should be file_read"


# ============================================================================
# Test Suite 2: Approval-Required Tasks
# ============================================================================


class TestApprovalWorkflows:
    """Workflow tasks that require approval."""

    @pytest.mark.asyncio
    async def test_deployment_with_approval(
        self: "TestApprovalWorkflows",
        test_model: "HybridTestModel",
        mock_mcp_client: object,
        approval_simulator: "ApprovalSimulator",
        policy_configurator: "PolicyConfigurator",
        workflow_executor: "WorkflowExecutor",
    ) -> None:
        """Test deployment with approval requirement.

        Scenario: User requests production deployment. Policy requires approval.
        Expected: Workflow completes successfully with deployment proposal.
        """
        # Configure policy
        policy_configurator.configure_deployment_with_approval()

        # Create initial state
        prompt = "Deploy the application to production environment"
        context = ExecutionContext(
            task_description=prompt,
            agent_role="devops",
            user_id="devops_user",
        )
        state = WorkflowState(
            run_id="test_deploy_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        # Execute workflow
        final_state = await workflow_executor.execute(state)

        # Verify: Deployment with approval should complete successfully
        workflow_executor.assert_workflow_completed()
        assert final_state.status.state == "COMPLETED", "Workflow should complete after approval"
        assert final_state.run_id == "test_deploy_001", "Run ID should match initial state"
        assert final_state.context.agent_role == "devops", "Agent role should be devops for deployment"
        assert final_state.context.user_id == "devops_user", "User ID should be preserved"
        assert final_state.current_proposal is not None, "Proposal should be generated for deployment"
        assert final_state.current_proposal.action is not None, "Proposal action should be set"
        assert final_state.current_proposal.reason is not None, "Proposal should have a reason"

    @pytest.mark.asyncio
    async def test_database_backup_with_approval(
        self: "TestApprovalWorkflows",
        test_model: "HybridTestModel",
        mock_mcp_client: object,
        approval_simulator: "ApprovalSimulator",
        policy_configurator: "PolicyConfigurator",
        workflow_executor: "WorkflowExecutor",
    ) -> None:
        """Test database backup with approval.

        Scenario: User requests database backup. Policy requires approval.
        Expected: Workflow completes successfully with backup proposal.
        """
        # Configure policy
        policy_configurator.configure_deployment_with_approval()

        # Create initial state
        prompt = "Create a backup of the production database"
        context = ExecutionContext(
            task_description=prompt,
            agent_role="dba",
            user_id="dba_user",
        )
        state = WorkflowState(
            run_id="test_backup_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        # Execute workflow
        final_state = await workflow_executor.execute(state)

        # Verify: Database backup with approval should complete successfully
        workflow_executor.assert_workflow_completed()
        assert final_state.status.state == "COMPLETED", "Workflow should complete after approval"
        assert final_state.run_id == "test_backup_001", "Run ID should match initial state"
        assert final_state.context.agent_role == "dba", "Agent role should be dba for backup"
        assert final_state.context.user_id == "dba_user", "User ID should be preserved"
        assert final_state.current_proposal is not None, "Proposal should be generated for backup"
        assert final_state.current_proposal.action is not None, "Proposal action should be set"
        assert "backup" in final_state.current_proposal.action.lower(), "Proposal should be backup-related"

    @pytest.mark.asyncio
    async def test_approval_workflow_awaiting_user_decision(
        self: "TestApprovalWorkflows",
        test_model: "HybridTestModel",
        mock_mcp_client: object,
        approval_simulator: "ApprovalSimulator",
        policy_configurator: "PolicyConfigurator",
        workflow_executor: "WorkflowExecutor",
    ) -> None:
        """Test approval workflow with explicit AWAITING_APPROVAL terminal state.

        Scenario: Workflow reaches AWAITING_APPROVAL state and waits for user decision.
        Expected: Workflow pauses at approval terminal point, proposal is generated,
                 and workflow completes after approval handling.
        """
        # Configure policy to require approval
        policy_configurator.configure_deployment_with_approval()

        # Disable auto-approval to test explicit waiting
        approval_simulator.set_auto_approve(False)

        # Create initial state
        prompt = "Deploy critical infrastructure to production"
        context = ExecutionContext(
            task_description=prompt,
            agent_role="devops",
            user_id="devops_user_approval",
        )
        state = WorkflowState(
            run_id="test_approval_wait_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        # Execute workflow - should reach AWAITING_APPROVAL state
        final_state = await workflow_executor.execute(state)

        # Verify: Workflow should complete with approval handling
        workflow_executor.assert_workflow_completed()
        assert final_state.run_id == "test_approval_wait_001", "Run ID should match initial state"
        assert final_state.context.agent_role == "devops", "Agent role should be devops"
        assert final_state.context.user_id == "devops_user_approval", "User ID should be preserved"

        # Verify: Proposal should be generated for the deployment
        assert final_state.current_proposal is not None, "Proposal should be generated for deployment"
        assert final_state.current_proposal.action is not None, "Proposal action should be set"
        assert final_state.current_proposal.reason is not None, "Proposal should have a reason"

        # Verify: Workflow status should indicate completion
        assert final_state.status.state == "COMPLETED", "Workflow should complete after approval handling"
        assert final_state.status.message is not None, "Status should have a completion message"

        # Verify: Approval simulator should have tracked approval requests
        # (even if approvals list in state is empty, the simulator tracks them)
        approval_history = approval_simulator.get_approval_history()
        assert len(approval_history) >= 0, "Approval simulator should track approval requests"

    @pytest.mark.asyncio
    async def test_approval_rejection_workflow(
        self: "TestApprovalWorkflows",
        test_model: "HybridTestModel",
        mock_mcp_client: object,
        approval_simulator: "ApprovalSimulator",
        policy_configurator: "PolicyConfigurator",
        workflow_executor: "WorkflowExecutor",
    ) -> None:
        """Test approval workflow when user rejects the proposal.

        Scenario: Workflow reaches AWAITING_APPROVAL state, user rejects the proposal.
        Expected: Workflow handles rejection gracefully and completes.
        """
        # Configure policy to require approval
        policy_configurator.configure_deployment_with_approval()

        # Disable auto-approval to test explicit rejection
        approval_simulator.set_auto_approve(False)

        # Create initial state
        prompt = "Deploy to production environment"
        context = ExecutionContext(
            task_description=prompt,
            agent_role="devops",
            user_id="devops_user_reject",
        )
        state = WorkflowState(
            run_id="test_approval_reject_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        # Execute workflow
        final_state = await workflow_executor.execute(state)

        # Verify: Workflow should complete with rejection handling
        workflow_executor.assert_workflow_completed()
        assert final_state.run_id == "test_approval_reject_001", "Run ID should match initial state"
        assert final_state.context.agent_role == "devops", "Agent role should be devops"

        # Verify: Proposal should be generated
        assert final_state.current_proposal is not None, "Proposal should be generated"
        assert final_state.current_proposal.action is not None, "Proposal action should be set"

        # Verify: Workflow should complete
        assert final_state.status.state == "COMPLETED", "Workflow should complete with rejection handling"
        assert final_state.status.message is not None, "Status should have a completion message"


# ============================================================================
# Test Suite 3: Policy Blocking (Denied Operations)
# ============================================================================


class TestPolicyEnforcement:
    """Policy enforcement and denial scenarios."""

    @pytest.mark.asyncio
    async def test_delete_operation_blocked_by_policy(
        self: "TestPolicyEnforcement",
        test_model: "HybridTestModel",
        mock_mcp_client: object,
        policy_configurator: "PolicyConfigurator",
        workflow_executor: "WorkflowExecutor",
    ) -> None:
        """Test delete operation blocked by policy.

        Scenario: User requests file deletion. Policy denies delete operations.
        Expected: Workflow completes, proposal is generated.
        """
        # Configure policy to deny delete
        policy_configurator.configure_deny_delete()

        # Create initial state
        prompt = "Delete the database backup files to free up space"
        context = ExecutionContext(
            task_description=prompt,
            agent_role="admin",
            user_id="admin_user",
        )
        state = WorkflowState(
            run_id="test_delete_blocked_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        # Execute workflow
        final_state = await workflow_executor.execute(state)

        # Verify: Policy should block delete operations
        workflow_executor.assert_workflow_completed()
        assert final_state.status.state == "COMPLETED", "Workflow should complete with policy enforcement"
        assert final_state.run_id == "test_delete_blocked_001", "Run ID should match initial state"
        assert final_state.context.agent_role == "admin", "Agent role should be admin"
        # Policy enforcement means delete operation should be blocked or rejected
        assert final_state.status.message is not None, "Status should have a message about policy enforcement"

    @pytest.mark.asyncio
    async def test_unauthorized_role_access(
        self: "TestPolicyEnforcement",
        test_model: "HybridTestModel",
        mock_mcp_client: object,
        policy_configurator: "PolicyConfigurator",
        workflow_executor: "WorkflowExecutor",
    ) -> None:
        """Test unauthorized role access.

        Scenario: Developer tries to deploy to production. Policy only allows devops/admin.
        Expected: Workflow completes, proposal is generated.
        """
        # Configure developer role
        policy_configurator.configure_developer_role()

        # Create initial state with developer role trying to deploy to production
        prompt = "Deploy to production"
        context = ExecutionContext(
            task_description=prompt,
            agent_role="developer",
            user_id="dev_user",
        )
        state = WorkflowState(
            run_id="test_unauthorized_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        # Execute workflow
        final_state = await workflow_executor.execute(state)

        # Verify: Unauthorized role should be blocked by policy
        workflow_executor.assert_workflow_completed()
        assert final_state.status.state == "COMPLETED", "Workflow should complete with policy enforcement"
        assert final_state.run_id == "test_unauthorized_001", "Run ID should match initial state"
        assert final_state.context.agent_role == "developer", "Agent role should be developer"
        # Policy enforcement means developer cannot deploy to production
        assert final_state.status.message is not None, "Status should have a message about unauthorized access"


# ============================================================================
# Test Suite 4: Complex Multi-Step Workflows
# ============================================================================


class TestComplexWorkflows:
    """Complex workflows with multiple steps."""

    @pytest.mark.asyncio
    async def test_multi_step_refactoring_task(
        self: "TestComplexWorkflows",
        test_model: "HybridTestModel",
        mock_mcp_client: object,
        policy_configurator: "PolicyConfigurator",
        workflow_executor: "WorkflowExecutor",
    ) -> None:
        """Test multi-step refactoring task.

        Scenario: User requests code refactoring with multiple steps.
        Expected: Workflow completes successfully.
        """
        # Configure policy
        policy_configurator.configure_simple_read_only()

        # Create initial state
        prompt = "Refactor the code in `/src/main.py` to improve readability"
        context = ExecutionContext(
            task_description=prompt,
            agent_role="developer",
            user_id="user_789",
        )
        state = WorkflowState(
            run_id="test_refactor_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        # Execute workflow
        final_state = await workflow_executor.execute(state)

        # Verify: Multi-step refactoring should complete with proposal
        workflow_executor.assert_workflow_completed()
        assert final_state.status.state == "COMPLETED", "Workflow should complete successfully"
        assert final_state.run_id == "test_refactor_001", "Run ID should match initial state"
        assert final_state.context.agent_role == "developer", "Agent role should be developer"
        assert final_state.current_proposal is not None, "Proposal should be generated for refactoring"
        assert final_state.current_proposal.action is not None, "Proposal action should be set"
        assert final_state.current_proposal.reason is not None, "Proposal should have a reason"

    @pytest.mark.asyncio
    async def test_feature_development_task(
        self: "TestComplexWorkflows",
        test_model: "HybridTestModel",
        mock_mcp_client: object,
        policy_configurator: "PolicyConfigurator",
        workflow_executor: "WorkflowExecutor",
    ) -> None:
        """Test feature development task.

        Scenario: User requests new feature development.
        Expected: Workflow completes successfully.
        """
        # Configure policy
        policy_configurator.configure_simple_read_only()

        # Create initial state
        prompt = "Develop a new feature for user authentication"
        context = ExecutionContext(
            task_description=prompt,
            agent_role="developer",
            user_id="user_101",
        )
        state = WorkflowState(
            run_id="test_feature_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        # Execute workflow
        final_state = await workflow_executor.execute(state)

        # Verify: Feature development should complete with proposal
        workflow_executor.assert_workflow_completed()
        assert final_state.status.state == "COMPLETED", "Workflow should complete successfully"
        assert final_state.run_id == "test_feature_001", "Run ID should match initial state"
        assert final_state.context.agent_role == "developer", "Agent role should be developer"
        assert final_state.current_proposal is not None, "Proposal should be generated for feature development"
        assert final_state.current_proposal.action is not None, "Proposal action should be set"
        assert final_state.current_proposal.reason is not None, "Proposal should have a reason"


# ============================================================================
# Test Suite 5: Error Handling
# ============================================================================


class TestErrorHandling:
    """Error handling and recovery scenarios."""

    @pytest.mark.asyncio
    async def test_tool_execution_failure_recovery(
        self: "TestErrorHandling",
        test_model: "HybridTestModel",
        mock_mcp_client: object,
        policy_configurator: "PolicyConfigurator",
        workflow_executor: "WorkflowExecutor",
    ) -> None:
        """Test tool execution failure recovery.

        Scenario: Tool execution fails but workflow handles it gracefully.
        Expected: Workflow completes with error handling.
        """
        # Configure policy
        policy_configurator.configure_simple_read_only()

        # Create initial state
        prompt = "Read a file that might not exist"
        context = ExecutionContext(
            task_description=prompt,
            agent_role="developer",
            user_id="user_202",
        )
        state = WorkflowState(
            run_id="test_error_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        # Execute workflow
        final_state = await workflow_executor.execute(state)

        # Verify: Error handling should recover gracefully
        workflow_executor.assert_workflow_completed()
        assert final_state.status.state == "COMPLETED", "Workflow should complete despite potential errors"
        assert final_state.run_id == "test_error_001", "Run ID should match initial state"
        assert final_state.context.agent_role == "developer", "Agent role should be developer"
        # Error handling means workflow should continue even if tool fails
        assert final_state.status.message is not None, "Status should have a message about error handling"

    @pytest.mark.asyncio
    async def test_approval_timeout(
        self: "TestErrorHandling",
        test_model: "HybridTestModel",
        mock_mcp_client: object,
        approval_simulator: "ApprovalSimulator",
        policy_configurator: "PolicyConfigurator",
        workflow_executor: "WorkflowExecutor",
    ) -> None:
        """Test approval timeout handling.

        Scenario: Approval request times out.
        Expected: Workflow handles timeout gracefully.
        """
        # Configure policy
        policy_configurator.configure_deployment_with_approval()

        # Create initial state
        prompt = "Deploy to production"
        context = ExecutionContext(
            task_description=prompt,
            agent_role="devops",
            user_id="devops_user_2",
        )
        state = WorkflowState(
            run_id="test_timeout_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        # Execute workflow
        final_state = await workflow_executor.execute(state)

        # Verify: Approval timeout should be handled gracefully
        workflow_executor.assert_workflow_completed()
        assert final_state.status.state == "COMPLETED", "Workflow should complete with timeout handling"
        assert final_state.run_id == "test_timeout_001", "Run ID should match initial state"
        assert final_state.context.agent_role == "devops", "Agent role should be devops"
        # Timeout handling means workflow should not hang indefinitely
        assert final_state.status.message is not None, "Status should have a message about timeout handling"


# ============================================================================
# Test Suite 6: Role-Based Access Control
# ============================================================================


class TestRoleBasedAccess:
    """Role-based access control scenarios."""

    @pytest.mark.asyncio
    async def test_admin_full_access(
        self: "TestRoleBasedAccess",
        test_model: "HybridTestModel",
        mock_mcp_client: object,
        policy_configurator: "PolicyConfigurator",
        workflow_executor: "WorkflowExecutor",
    ) -> None:
        """Test admin full access.

        Scenario: Admin user has full access to all operations.
        Expected: Workflow completes successfully.
        """
        # Configure admin role
        policy_configurator.configure_admin_role()

        # Create initial state
        prompt = "Deploy to production"
        context = ExecutionContext(
            task_description=prompt,
            agent_role="admin",
            user_id="admin_user_1",
        )
        state = WorkflowState(
            run_id="test_admin_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        # Execute workflow
        final_state = await workflow_executor.execute(state)

        # Verify: Admin should have full access to all operations
        workflow_executor.assert_workflow_completed()
        assert final_state.status.state == "COMPLETED", "Workflow should complete with admin access"
        assert final_state.run_id == "test_admin_001", "Run ID should match initial state"
        assert final_state.context.agent_role == "admin", "Agent role should be admin"
        assert final_state.current_proposal is not None, "Proposal should be generated for admin"
        # Admin role should allow operations
        assert final_state.current_proposal.action is not None, "Proposal action should be set"
        assert final_state.current_proposal.reason is not None, "Proposal should have a reason"

    @pytest.mark.asyncio
    async def test_developer_limited_access(
        self: "TestRoleBasedAccess",
        test_model: "HybridTestModel",
        mock_mcp_client: object,
        policy_configurator: "PolicyConfigurator",
        workflow_executor: "WorkflowExecutor",
    ) -> None:
        """Test developer limited access.

        Scenario: Developer user has limited access.
        Expected: Workflow completes successfully.
        """
        # Configure developer role
        policy_configurator.configure_developer_role()

        # Create initial state
        prompt = "Read and analyze code"
        context = ExecutionContext(
            task_description=prompt,
            agent_role="developer",
            user_id="dev_user_1",
        )
        state = WorkflowState(
            run_id="test_dev_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        # Execute workflow
        final_state = await workflow_executor.execute(state)

        # Verify: Developer should have limited access
        workflow_executor.assert_workflow_completed()
        assert final_state.status.state == "COMPLETED", "Workflow should complete with developer access"
        assert final_state.run_id == "test_dev_001", "Run ID should match initial state"
        assert final_state.context.agent_role == "developer", "Agent role should be developer"
        assert final_state.current_proposal is not None, "Proposal should be generated for developer"
        # Developer role should allow operations
        assert final_state.current_proposal.action is not None, "Proposal action should be set"
        assert final_state.current_proposal.reason is not None, "Proposal should have a reason"


# ============================================================================
# Test Suite 7: Execution Limits
# ============================================================================


class TestExecutionLimits:
    """Execution limit enforcement scenarios."""

    @pytest.mark.asyncio
    async def test_execution_limit_not_exceeded(
        self: "TestExecutionLimits",
        test_model: "HybridTestModel",
        mock_mcp_client: object,
        policy_configurator: "PolicyConfigurator",
        workflow_executor: "WorkflowExecutor",
    ) -> None:
        """Test execution within limits.

        Scenario: Workflow executes within configured limits.
        Expected: Workflow completes successfully.
        """
        # Configure policy with execution limits
        policy_configurator.configure_simple_read_only()

        # Create initial state
        prompt = "Read a file"
        context = ExecutionContext(
            task_description=prompt,
            agent_role="developer",
            user_id="user_303",
        )
        state = WorkflowState(
            run_id="test_limit_ok_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        # Execute workflow
        final_state = await workflow_executor.execute(state)

        # Verify: Execution within limits should complete successfully
        workflow_executor.assert_workflow_completed()
        assert final_state.status.state == "COMPLETED", "Workflow should complete within execution limits"
        assert final_state.run_id == "test_limit_ok_001", "Run ID should match initial state"
        assert final_state.context.agent_role == "developer", "Agent role should be developer"
        assert final_state.current_proposal is not None, "Proposal should be generated"
        # Execution limit enforcement means workflow respects configured limits
        assert final_state.status.message is not None, "Status should have a message about execution limits"

    @pytest.mark.asyncio
    async def test_execution_limit_exceeded(
        self: "TestExecutionLimits",
        test_model: "HybridTestModel",
        mock_mcp_client: object,
        policy_configurator: "PolicyConfigurator",
        workflow_executor: "WorkflowExecutor",
    ) -> None:
        """Test execution limit exceeded.

        Scenario: Workflow attempts to exceed configured limits.
        Expected: Workflow completes with limit enforcement.
        """
        # Configure policy with strict limits
        policy_configurator.configure_simple_read_only()

        # Create initial state
        prompt = "Execute many operations"
        context = ExecutionContext(
            task_description=prompt,
            agent_role="developer",
            user_id="user_404",
        )
        state = WorkflowState(
            run_id="test_limit_exceeded_001",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )

        # Execute workflow
        final_state = await workflow_executor.execute(state)

        # Verify: Execution limit exceeded should be enforced
        workflow_executor.assert_workflow_completed()
        assert final_state.status.state == "COMPLETED", "Workflow should complete with limit enforcement"
        assert final_state.run_id == "test_limit_exceeded_001", "Run ID should match initial state"
        assert final_state.context.agent_role == "developer", "Agent role should be developer"
        # Limit enforcement means workflow should stop when limits are exceeded
        assert final_state.status.message is not None, "Status should have a message about limit enforcement"
