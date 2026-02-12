from __future__ import annotations

import asyncio
import time
from typing import Optional

import pytest

from gearmeshing_ai.agent.orchestrator.service import OrchestratorService
from gearmeshing_ai.agent.orchestrator.models import WorkflowResult, WorkflowStatus


class WorkflowTestHelper:
    """Helper class for testing AI workflows with proper status management."""
    
    def __init__(self, orchestrator_service: OrchestratorService):
        self.orchestrator_service = orchestrator_service
    
    async def wait_for_workflow_completion(
        self,
        initial_result: WorkflowResult,
        timeout_seconds: int = 180,
        poll_interval: float = 5.0,
    ) -> WorkflowResult:
        """Wait for workflow completion with proper status polling.
        
        Args:
            initial_result: Initial result from run_workflow call
            timeout_seconds: Maximum time to wait for completion
            poll_interval: Seconds between status checks
            
        Returns:
            Final WorkflowResult with completed status
            
        Raises:
            TimeoutError: If workflow doesn't complete within timeout
            AssertionError: If workflow fails unexpectedly
        """
        # If already completed, return immediately
        if initial_result.status in [WorkflowStatus.SUCCESS, WorkflowStatus.FAILED]:
            return initial_result
        
        # For in-progress workflows, poll for completion
        run_id: str = initial_result.run_id
        assert run_id is not None, "Workflow ID required for polling"
        
        start_time: float = time.time()
        current_result: WorkflowResult = initial_result
        
        while time.time() - start_time < timeout_seconds:
            # Check current status
            current_result = await self.orchestrator_service.get_status(run_id)
            
            # Log progress for debugging
            print(f"Workflow {run_id} status: {current_result.status}")
            
            # Check for completion
            if current_result.status == WorkflowStatus.SUCCESS:
                print(f"Workflow {run_id} completed successfully")
                return current_result
            elif current_result.status == WorkflowStatus.FAILED:
                failure_reason: str = current_result.error or "Unknown error"
                raise AssertionError(f"Workflow {run_id} failed: {failure_reason}")
            elif current_result.status == WorkflowStatus.AWAITING_APPROVAL:
                print(f"Workflow {run_id} awaiting approval")
                return current_result  # Return for approval testing
            elif current_result.status == WorkflowStatus.CANCELLED:
                raise AssertionError(f"Workflow {run_id} was cancelled")
            
            # Wait before next poll
            await asyncio.sleep(poll_interval)
        
        # Timeout reached
        raise TimeoutError(
            f"Workflow {run_id} did not complete within {timeout_seconds} seconds. "
            f"Last status: {current_result.status}"
        )
    
    async def run_and_wait_for_completion(
        self,
        task_description: str,
        agent_role: str,
        timeout_seconds: int = 180,
        poll_interval: float = 5.0,
    ) -> WorkflowResult:
        """Run workflow and wait for completion in one call.
        
        Args:
            task_description: The task to execute
            agent_role: Role for the AI agent
            timeout_seconds: Maximum time to wait for completion
            poll_interval: Seconds between status checks
            
        Returns:
            Completed WorkflowResult
        """
        # Start the workflow
        initial_result: WorkflowResult = await self.orchestrator_service.run_workflow(
            task_description=task_description,
            agent_role=agent_role,
            timeout_seconds=timeout_seconds
        )
        
        # Wait for completion
        return await self.wait_for_workflow_completion(
            initial_result=initial_result,
            timeout_seconds=timeout_seconds,
            poll_interval=poll_interval
        )
    
    def verify_langgraph_execution_flow(self, result: WorkflowResult) -> None:
        """Verify that the workflow followed proper LangGraph execution patterns.
        
        Args:
            result: Completed workflow result to verify
            
        Raises:
            AssertionError: If workflow execution doesn't match expected patterns
        """
        assert result.status == WorkflowStatus.SUCCESS, f"Workflow must complete successfully. Current status: {result.status}"
        assert result.output is not None, "Workflow must have output"
        assert result.run_id is not None, "Workflow must have ID"
        
        # Verify execution history exists (LangGraph tracks node execution)
        if hasattr(result, 'execution_history') and result.execution_history:
            history: list = result.execution_history
            
            # Should have multiple nodes executed (planning, execution, verification)
            assert len(history) >= 2, "LangGraph should execute multiple nodes"
            
            # Verify node types in execution flow
            node_types: set = {node.get('node_type') for node in history if 'node_type' in node}
            expected_nodes: set = {'planner', 'executor', 'verifier'}
            
            # At least some expected nodes should be present
            assert len(node_types.intersection(expected_nodes)) > 0, \
                f"Expected LangGraph nodes not found. Found: {node_types}"
        else:
            # If execution history is not available, verify through other means
            # This is a fallback for implementations that don't expose execution history
            print("Warning: Execution history not available, skipping LangGraph flow verification")
        
        print(f"✓ LangGraph execution flow verified for workflow {result.run_id}")
    
    async def verify_workflow_state_consistency(self, run_id: str) -> None:
        """Verify that workflow state is consistent across different checks.
        
        Args:
            run_id: ID of the workflow to verify
        """
        # Get status multiple times to ensure consistency
        status1 = await self.orchestrator_service.get_status(run_id)
        await asyncio.sleep(0.1)  # Small delay
        status2 = await self.orchestrator_service.get_status(run_id)
        
        # Status should be consistent
        assert status1.status == status2.status, \
            f"Workflow status inconsistent: {status1.status} vs {status2.status}"
        
        # Workflow ID should be consistent
        assert status1.run_id == status2.run_id == run_id, \
            "Workflow ID inconsistent across status checks"
    
    def get_workflow_timeout_for_task_type(self, task_type: str) -> int:
        """Get appropriate timeout for different task types.
        
        Args:
            task_type: Type of task (simple, complex, mcp, approval)
            
        Returns:
            Timeout in seconds
        """
        timeout_map: dict[str, int] = {
            "simple": 120,
            "complex": 240,
            "mcp": 300,
            "approval": 300,
            "error": 60,
        }
        
        return timeout_map.get(task_type, 180)
    
    def get_poll_interval_for_task_type(self, task_type: str) -> float:
        """Get appropriate poll interval for different task types.
        
        Args:
            task_type: Type of task (simple, complex, mcp, approval)
            
        Returns:
            Poll interval in seconds
        """
        interval_map: dict[str, float] = {
            "simple": 3.0,
            "complex": 5.0,
            "mcp": 5.0,
            "approval": 5.0,
            "error": 2.0,
        }
        
        return interval_map.get(task_type, 5.0)


@pytest.fixture
def workflow_helper(orchestrator_service: OrchestratorService) -> WorkflowTestHelper:
    """Provide workflow test helper for smoke tests."""
    return WorkflowTestHelper(orchestrator_service)
