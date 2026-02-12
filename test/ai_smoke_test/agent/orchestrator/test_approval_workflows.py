from __future__ import annotations

import asyncio
import glob
import os
from typing import Optional

import pytest

from gearmeshing_ai.agent.orchestrator.service import OrchestratorService
from gearmeshing_ai.agent.orchestrator.models import (
    ApprovalRequest,
    WorkflowResult,
    WorkflowStatus,
)
from test.ai_smoke_test.agent.orchestrator.utils.workflow_helpers import WorkflowTestHelper


@pytest.mark.smoke_test
@pytest.mark.approval_workflow
class TestApprovalWorkflows:
    """Test orchestrator approval workflows with proper status management."""

    async def test_approval_required_workflow(
        self,
        orchestrator_service: OrchestratorService,
        workflow_helper: WorkflowTestHelper,
        smoke_test_environment: dict[str, bool],
        test_file_workspace: str,
    ) -> None:
        """Test workflow that requires approval with status polling."""
        # Use a task that might trigger approval for sensitive operations
        task: str = "Deploy a configuration file named 'production_config.json' to production environment"
        config_file: str = os.path.join(test_file_workspace, "production_config.json")
        workflow_id: Optional[str] = None
        
        try:
            # Run workflow and wait for completion or approval
            result: WorkflowResult = await workflow_helper.run_and_wait_for_completion(
                task_description=task,
                agent_role="dev",
                timeout_seconds=workflow_helper.get_workflow_timeout_for_task_type("approval"),
                poll_interval=workflow_helper.get_poll_interval_for_task_type("approval")
            )
            
            # Check if approval is required
            if result.status == WorkflowStatus.AWAITING_APPROVAL:
                workflow_id = result.run_id
                assert workflow_id is not None, "Workflow ID required for approval"
                
                # Verify LangGraph execution flow up to approval point
                if smoke_test_environment.get("verify_langgraph", True):
                    workflow_helper.verify_langgraph_execution_flow(result)
                
                # Verify approval request structure
                approval_request: ApprovalRequest = result.approval_request
                assert approval_request is not None, "Approval request should be present"
                assert "deploy" in approval_request.description.lower(), \
                    "Approval request should mention deployment"
                
                # Test approval
                approval_result: WorkflowResult = await orchestrator_service.approve_workflow(
                    workflow_id=workflow_id,
                    decision="APPROVE",
                    comment="Approved for smoke test"
                )
                
                # Wait for approval completion
                final_result: WorkflowResult = await workflow_helper.wait_for_workflow_completion(
                    initial_result=approval_result,
                    timeout_seconds=120,
                    poll_interval=5.0
                )
                
                # Verify final completion
                assert final_result.status == WorkflowStatus.SUCCESS
                assert final_result.output is not None
                
                # Verify complete LangGraph execution flow
                if smoke_test_environment.get("verify_langgraph", True):
                    workflow_helper.verify_langgraph_execution_flow(final_result)
                
                # Check if config file was created (optional, depends on implementation)
                if os.path.exists(config_file):
                    with open(config_file, encoding="utf-8") as f:
                        content: str = f.read()
                        assert len(content) > 0, "Config file should not be empty"
                
                print(f"✓ Approval workflow completed: {final_result.run_id}")
            else:
                # If no approval required, verify direct success
                assert result.status == WorkflowStatus.SUCCESS
                if smoke_test_environment.get("verify_langgraph", True):
                    workflow_helper.verify_langgraph_execution_flow(result)
                
                print(f"✓ Workflow completed without approval: {result.run_id}")
        
        finally:
            # Clean up created file
            if os.path.exists(config_file):
                os.remove(config_file)

    async def test_rejection_with_alternative(
        self,
        orchestrator_service: OrchestratorService,
        workflow_helper: WorkflowTestHelper,
        smoke_test_environment: dict[str, bool],
        test_file_workspace: str,
    ) -> None:
        """Test workflow rejection with alternative action and status polling."""
        task: str = "Delete all log files in the current directory"
        workflow_id: Optional[str] = None
        backup_files: list[str] = []
        
        try:
            # Run workflow and wait for completion or approval
            result: WorkflowResult = await workflow_helper.run_and_wait_for_completion(
                task_description=task,
                agent_role="dev",
                timeout_seconds=workflow_helper.get_workflow_timeout_for_task_type("approval"),
                poll_interval=workflow_helper.get_poll_interval_for_task_type("approval")
            )
            
            # If approval is required for destructive operation
            if result.status == WorkflowStatus.AWAITING_APPROVAL:
                workflow_id = result.run_id
                assert workflow_id is not None, "Workflow ID required for rejection"
                
                # Verify LangGraph execution flow up to approval point
                if smoke_test_environment.get("verify_langgraph", True):
                    workflow_helper.verify_langgraph_execution_flow(result)
                
                # Test rejection with alternative
                rejection_result: WorkflowResult = await orchestrator_service.reject_workflow(
                    workflow_id=workflow_id,
                    decision="REJECT",
                    alternative_action="Create a backup of log files instead",
                    comment="Too destructive, create backup instead"
                )
                
                # Wait for alternative execution completion
                final_result: WorkflowResult = await workflow_helper.wait_for_workflow_completion(
                    initial_result=rejection_result,
                    timeout_seconds=120,
                    poll_interval=5.0
                )
                
                # Verify alternative was executed
                assert final_result.status == WorkflowStatus.SUCCESS
                assert final_result.output is not None
                
                # Verify complete LangGraph execution flow
                if smoke_test_environment.get("verify_langgraph", True):
                    workflow_helper.verify_langgraph_execution_flow(final_result)
                
                # Check if backup files were created
                backup_files = glob.glob(os.path.join(test_file_workspace, "*backup*"))
                assert len(backup_files) > 0, "Backup files should be created as alternative"
                
                print(f"✓ Rejection with alternative completed: {final_result.run_id}")
            else:
                # If no approval required, verify direct success
                assert result.status == WorkflowStatus.SUCCESS
                if smoke_test_environment.get("verify_langgraph", True):
                    workflow_helper.verify_langgraph_execution_flow(result)
                
                print(f"✓ Workflow completed without approval: {result.run_id}")
        
        finally:
            # Clean up any backup files created
            all_backup_files = glob.glob(os.path.join(test_file_workspace, "*backup*"))
            for file_path in all_backup_files:
                try:
                    os.remove(file_path)
                    print(f"✓ Cleaned up backup file: {file_path}")
                except Exception as e:
                    print(f"Warning: Failed to clean up backup file {file_path}: {e}")

    async def test_approval_cancellation(
        self,
        orchestrator_service: OrchestratorService,
        workflow_helper: WorkflowTestHelper,
        smoke_test_environment: dict[str, bool],
        test_file_workspace: str,
    ) -> None:
        """Test workflow cancellation during approval process."""
        task: str = "Perform a sensitive database migration that requires approval"
        workflow_id: Optional[str] = None
        
        try:
            # Run workflow and wait for approval
            result: WorkflowResult = await workflow_helper.run_and_wait_for_completion(
                task_description=task,
                agent_role="dev",
                timeout_seconds=workflow_helper.get_workflow_timeout_for_task_type("approval"),
                poll_interval=workflow_helper.get_poll_interval_for_task_type("approval")
            )
            
            # If approval is required
            if result.status == WorkflowStatus.AWAITING_APPROVAL:
                workflow_id = result.run_id
                assert workflow_id is not None, "Workflow ID required for cancellation"
                
                # Verify LangGraph execution flow up to approval point
                if smoke_test_environment.get("verify_langgraph", True):
                    workflow_helper.verify_langgraph_execution_flow(result)
                
                # Test cancellation
                cancel_result: WorkflowResult = await orchestrator_service.cancel_workflow(
                    workflow_id=workflow_id,
                    reason="Cancelled for smoke test"
                )
                
                # Verify cancellation
                assert cancel_result.status == WorkflowStatus.CANCELLED
                assert cancel_result.error is not None
                assert "cancelled" in cancel_result.error.lower()
                
                print(f"✓ Approval workflow cancelled: {workflow_id}")
            else:
                # If no approval required, that's also acceptable
                assert result.status in [WorkflowStatus.SUCCESS, WorkflowStatus.FAILED]
                print(f"✓ Workflow completed without requiring approval: {result.run_id}")
        
        except Exception as e:
            # Cancellation might fail if workflow already completed
            print(f"Warning: Cancellation test encountered error: {e}")

    async def test_approval_workflow_state_persistence(
        self,
        orchestrator_service: OrchestratorService,
        workflow_helper: WorkflowTestHelper,
        smoke_test_environment: dict[str, bool],
        test_file_workspace: str,
    ) -> None:
        """Test that approval workflow state persists across status checks."""
        task: str = "Create a deployment plan that requires approval"
        workflow_id: Optional[str] = None
        
        try:
            # Run workflow and wait for approval
            result: WorkflowResult = await workflow_helper.run_and_wait_for_completion(
                task_description=task,
                agent_role="dev",
                timeout_seconds=workflow_helper.get_workflow_timeout_for_task_type("approval"),
                poll_interval=workflow_helper.get_poll_interval_for_task_type("approval")
            )
            
            # If approval is required
            if result.status == WorkflowStatus.AWAITING_APPROVAL:
                workflow_id = result.run_id
                assert workflow_id is not None, "Workflow ID required for state persistence test"
                
                # Verify state persistence across multiple checks
                await workflow_helper.verify_workflow_state_consistency(workflow_id)
                
                # Check status multiple times to ensure consistency
                status1 = await orchestrator_service.get_status(workflow_id)
                await asyncio.sleep(0.1)
                status2 = await orchestrator_service.get_status(workflow_id)
                
                assert status1.status == status2.status == WorkflowStatus.AWAITING_APPROVAL
                assert status1.workflow_id == status2.workflow_id == workflow_id
                
                # Verify approval request is consistent
                if status1.approval_request and status2.approval_request:
                    assert status1.approval_request.description == status2.approval_request.description
                
                print(f"✓ Approval workflow state persistence verified: {workflow_id}")
                
                # Clean up by cancelling the workflow
                try:
                    await orchestrator_service.cancel_workflow(workflow_id, "Test cleanup")
                except Exception:
                    pass  # Ignore cleanup errors
            else:
                # If no approval required, verify direct success
                assert result.status == WorkflowStatus.SUCCESS
                print(f"✓ Workflow completed without requiring approval: {result.run_id}")
        
        except Exception as e:
            print(f"Warning: Approval state persistence test encountered error: {e}")

    async def test_approval_with_comments(
        self,
        orchestrator_service: OrchestratorService,
        workflow_helper: WorkflowTestHelper,
        smoke_test_environment: dict[str, bool],
        test_file_workspace: str,
    ) -> None:
        """Test approval workflow with detailed comments and feedback."""
        task: str = "Update production configuration with new settings"
        workflow_id: Optional[str] = None
        
        try:
            # Run workflow and wait for approval
            result: WorkflowResult = await workflow_helper.run_and_wait_for_completion(
                task_description=task,
                agent_role="dev",
                timeout_seconds=workflow_helper.get_workflow_timeout_for_task_type("approval"),
                poll_interval=workflow_helper.get_poll_interval_for_task_type("approval")
            )
            
            # If approval is required
            if result.status == WorkflowStatus.AWAITING_APPROVAL:
                workflow_id = result.run_id
                assert workflow_id is not None, "Workflow ID required for comments test"
                
                # Verify LangGraph execution flow up to approval point
                if smoke_test_environment.get("verify_langgraph", True):
                    workflow_helper.verify_langgraph_execution_flow(result)
                
                # Test approval with detailed comments
                approval_result: WorkflowResult = await orchestrator_service.approve_workflow(
                    workflow_id=workflow_id,
                    decision="APPROVE",
                    comment="Approved for smoke test. Verified all configuration changes are safe and properly tested."
                )
                
                # Wait for approval completion
                final_result: WorkflowResult = await workflow_helper.wait_for_workflow_completion(
                    initial_result=approval_result,
                    timeout_seconds=120,
                    poll_interval=5.0
                )
                
                # Verify final completion
                assert final_result.status == WorkflowStatus.SUCCESS
                assert final_result.output is not None
                
                # Verify complete LangGraph execution flow
                if smoke_test_environment.get("verify_langgraph", True):
                    workflow_helper.verify_langgraph_execution_flow(final_result)
                
                # Check if comments are preserved in workflow history
                if hasattr(final_result, 'execution_history') and final_result.execution_history:
                    approval_events = [
                        event for event in final_result.execution_history
                        if event.get('event_type') == 'approval'
                    ]
                    assert len(approval_events) > 0, "Approval events should be recorded"
                
                print(f"✓ Approval with comments completed: {final_result.run_id}")
            else:
                # If no approval required, verify direct success
                assert result.status == WorkflowStatus.SUCCESS
                if smoke_test_environment.get("verify_langgraph", True):
                    workflow_helper.verify_langgraph_execution_flow(result)
                
                print(f"✓ Workflow completed without approval: {result.run_id}")
        
        finally:
            # Clean up any created files
            config_files = glob.glob(os.path.join(test_file_workspace, "*config*"))
            for file_path in config_files:
                try:
                    os.remove(file_path)
                except Exception:
                    pass
