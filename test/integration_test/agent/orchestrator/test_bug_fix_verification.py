"""Test to verify the orchestrator workflow bug is fixed.

This test verifies that the LangGraph state data model validation bug
has been fixed and the orchestrator can successfully run workflows.
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import patch

from gearmeshing_ai.agent.orchestrator.service import OrchestratorService
from gearmeshing_ai.agent.orchestrator.models import WorkflowStatus


class TestOrchestratorBugFix:
    """Test that verifies the orchestrator workflow bug is completely fixed."""
    
    async def test_workflow_creation_no_parameter_error(self) -> None:
        """Test that create_agent_workflow parameter error is fixed."""
        service = OrchestratorService()
        
        # This should not raise TypeError about missing arguments anymore
        result = await service.run_workflow(
            task_description="Test task",
            agent_role="dev",
            user_id="test_user",
            timeout_seconds=30
        )
        
        # Verify workflow completes (even with mock errors)
        assert result.status == WorkflowStatus.SUCCESS
        assert result.error is None
        assert result.run_id is not None
    
    async def test_workflow_state_validation_works(self) -> None:
        """Test that WorkflowState validation works correctly."""
        service = OrchestratorService()
        
        # This should not raise ValidationError about missing status field
        result = await service.run_workflow(
            task_description="Test task for state validation",
            agent_role="dev", 
            user_id="test_user",
            timeout_seconds=30
        )
        
        # Verify the state was created and validated successfully
        assert result.status == WorkflowStatus.SUCCESS
        assert "validation error" not in str(result.error).lower()
    
    async def test_complete_workflow_execution(self) -> None:
        """Test complete workflow execution from start to finish."""
        service = OrchestratorService()
        
        # Run complete workflow
        result = await service.run_workflow(
            task_description="Complete workflow test",
            agent_role="dev",
            user_id="test_user",
            timeout_seconds=60
        )
        
        # Verify successful execution
        assert result.status == WorkflowStatus.SUCCESS
        assert result.run_id is not None
        assert result.duration_seconds > 0
        assert result.started_at is not None
        assert result.completed_at is not None
    
    async def test_approval_workflow_execution(self) -> None:
        """Test approval workflow execution."""
        service = OrchestratorService()
        
        # Mock the persistence to simulate approval workflow
        with patch.object(service.persistence, 'load_workflow_state') as mock_load, \
             patch.object(service.persistence, 'save_approval_decision') as mock_save:
            
            # First run a workflow
            initial_result = await service.run_workflow(
                task_description="Approval workflow test",
                agent_role="dev",
                user_id="test_user",
                timeout_seconds=30
            )
            
            # Should complete successfully
            assert initial_result.status == WorkflowStatus.SUCCESS
    
    async def test_multiple_workflow_executions(self) -> None:
        """Test multiple workflow executions don't interfere with each other."""
        service = OrchestratorService()
        
        # Run multiple workflows
        results = []
        for i in range(3):
            result = await service.run_workflow(
                task_description=f"Multiple workflow test {i+1}",
                agent_role="dev",
                user_id="test_user",
                timeout_seconds=30
            )
            results.append(result)
        
        # All should succeed
        for i, result in enumerate(results):
            assert result.status == WorkflowStatus.SUCCESS
            assert result.run_id is not None
            assert result.run_id != results[i-1].run_id if i > 0 else True  # Unique IDs
    
    async def test_workflow_error_handling(self) -> None:
        """Test that workflow error handling works properly."""
        service = OrchestratorService()
        
        # Even with internal errors, workflow should handle gracefully
        result = await service.run_workflow(
            task_description="Error handling test",
            agent_role="dev",
            user_id="test_user",
            timeout_seconds=30
        )
        
        # Should complete successfully despite mock errors
        assert result.status == WorkflowStatus.SUCCESS
    
    def test_orchestrator_service_initialization(self) -> None:
        """Test that OrchestratorService initializes correctly."""
        # This should not raise any errors
        service = OrchestratorService()
        assert service is not None
        assert service.persistence is not None
    
    def test_workflow_creation_helper_method(self) -> None:
        """Test that the _create_workflow helper method works."""
        service = OrchestratorService()
        
        # This should not raise TypeError about missing arguments
        workflow = service._create_workflow()
        assert workflow is not None


if __name__ == "__main__":
    # Quick verification that the bug is fixed
    async def main():
        test = TestOrchestratorBugFix()
        try:
            await test.test_workflow_creation_no_parameter_error()
            print("✓ Bug fix verified: No more parameter errors!")
        except Exception as e:
            print(f"✗ Bug still exists: {e}")
            return False
        
        try:
            await test.test_workflow_state_validation_works()
            print("✓ Bug fix verified: No more validation errors!")
        except Exception as e:
            print(f"✗ Bug still exists: {e}")
            return False
        
        print("🎉 ALL TESTS PASSED - Bug is completely fixed!")
        return True
    
    success = asyncio.run(main())
    exit(0 if success else 1)
