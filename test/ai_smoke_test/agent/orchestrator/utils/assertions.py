from __future__ import annotations

from typing import Any, Optional

import pytest

from gearmeshing_ai.agent.orchestrator.models import WorkflowResult, WorkflowStatus


class WorkflowAssertions:
    """Custom assertion helpers for workflow testing."""
    
    @staticmethod
    def assert_workflow_success(result: WorkflowResult) -> None:
        """Assert that workflow completed successfully.
        
        Args:
            result: Workflow result to check
            
        Raises:
            AssertionError: If workflow did not succeed
        """
        assert result.status == WorkflowStatus.SUCCESS, \
            f"Expected workflow to succeed, but got status: {result.status}"
        assert result.output is not None, \
            "Successful workflow should have output"
        assert result.run_id is not None, \
            "Workflow should have an ID"
    
    @staticmethod
    def assert_workflow_failure(result: WorkflowResult, expected_error: Optional[str] = None) -> None:
        """Assert that workflow failed as expected.
        
        Args:
            result: Workflow result to check
            expected_error: Optional expected error message
            
        Raises:
            AssertionError: If workflow did not fail as expected
        """
        assert result.status == WorkflowStatus.FAILED, \
            f"Expected workflow to fail, but got status: {result.status}"
        assert result.error is not None, \
            "Failed workflow should have error message"
        
        if expected_error:
            assert expected_error.lower() in result.error.lower(), \
                f"Expected error '{expected_error}' not found in actual error: {result.error}"
    
    @staticmethod
    def assert_workflow_awaiting_approval(result: WorkflowResult) -> None:
        """Assert that workflow is awaiting approval.
        
        Args:
            result: Workflow result to check
            
        Raises:
            AssertionError: If workflow is not awaiting approval
        """
        assert result.status == WorkflowStatus.AWAITING_APPROVAL, \
            f"Expected workflow to await approval, but got status: {result.status}"
        assert result.approval_request is not None, \
            "Workflow awaiting approval should have approval request"
        assert result.run_id is not None, \
            "Workflow should have an ID"
    
    @staticmethod
    def assert_workflow_cancelled(result: WorkflowResult) -> None:
        """Assert that workflow was cancelled.
        
        Args:
            result: Workflow result to check
            
        Raises:
            AssertionError: If workflow was not cancelled
        """
        assert result.status == WorkflowStatus.CANCELLED, \
            f"Expected workflow to be cancelled, but got status: {result.status}"
        assert result.error is not None, \
            "Cancelled workflow should have error message"
        assert "cancelled" in result.error.lower(), \
            f"Error message should mention cancellation: {result.error}"
    
    @staticmethod
    def assert_files_created(result: WorkflowResult, expected_files: list[str]) -> None:
        """Assert that specific files were created by workflow.
        
        Args:
            result: Workflow result to check
            expected_files: List of expected file names
            
        Raises:
            AssertionError: If expected files are not found
        """
        assert result.output is not None, "Workflow should have output"
        created_files = result.output.get("files_created", [])
        
        for expected_file in expected_files:
            assert expected_file in created_files, \
                f"Expected file '{expected_file}' not found in created files: {created_files}"
    
    @staticmethod
    def assert_workflow_output_contains(result: WorkflowResult, expected_content: str) -> None:
        """Assert that workflow output contains specific content.
        
        Args:
            result: Workflow result to check
            expected_content: Content expected to be in output
            
        Raises:
            AssertionError: If expected content is not found
        """
        assert result.output is not None, "Workflow should have output"
        
        # Convert output to string and check content
        output_str = str(result.output)
        assert expected_content in output_str, \
            f"Expected content '{expected_content}' not found in output: {output_str}"
    
    @staticmethod
    def assert_workflow_execution_history(result: WorkflowResult, min_nodes: int = 2) -> None:
        """Assert that workflow has execution history with minimum nodes.
        
        Args:
            result: Workflow result to check
            min_nodes: Minimum number of execution nodes expected
            
        Raises:
            AssertionError: If execution history is insufficient
        """
        if not hasattr(result, 'execution_history') or not result.execution_history:
            # Skip assertion if execution history is not available
            print("Warning: Execution history not available, skipping history assertion")
            return
        
        history = result.execution_history
        assert len(history) >= min_nodes, \
            f"Expected at least {min_nodes} execution nodes, got {len(history)}"
    
    @staticmethod
    def assert_approval_request_structure(approval_request: Any) -> None:
        """Assert that approval request has proper structure.
        
        Args:
            approval_request: Approval request object
            
        Raises:
            AssertionError: If approval request structure is invalid
        """
        assert approval_request is not None, "Approval request should not be None"
        assert hasattr(approval_request, 'description'), \
            "Approval request should have description"
        assert hasattr(approval_request, 'run_id'), \
            "Approval request should have run_id"
        assert len(approval_request.description.strip()) > 0, \
            "Approval request description should not be empty"
    
    @staticmethod
    def assert_workflow_timeout(result: WorkflowResult, max_duration_seconds: float) -> None:
        """Assert that workflow completed within time limit.
        
        Args:
            result: Workflow result to check
            max_duration_seconds: Maximum allowed duration in seconds
            
        Raises:
            AssertionError: If workflow exceeded time limit
        """
        if not hasattr(result, 'duration_seconds') or result.duration_seconds is None:
            print("Warning: Duration information not available, skipping timeout assertion")
            return
        
        assert result.duration_seconds <= max_duration_seconds, \
            f"Workflow duration {result.duration_seconds}s exceeded limit {max_duration_seconds}s"
    
    @staticmethod
    def assert_workflow_cost(result: WorkflowResult, max_cost: float) -> None:
        """Assert that workflow cost is within limit.
        
        Args:
            result: Workflow result to check
            max_cost: Maximum allowed cost
            
        Raises:
            AssertionError: If workflow exceeded cost limit
        """
        if not hasattr(result, 'cost') or result.cost is None:
            print("Warning: Cost information not available, skipping cost assertion")
            return
        
        assert result.cost <= max_cost, \
            f"Workflow cost ${result.cost:.4f} exceeded limit ${max_cost:.4f}"
    
    @staticmethod
    def assert_mcp_tools_used(result: WorkflowResult, min_tools: int = 1) -> None:
        """Assert that workflow used MCP tools.
        
        Args:
            result: Workflow result to check
            min_tools: Minimum number of MCP tools expected
            
        Raises:
            AssertionError: If insufficient MCP tools were used
        """
        assert result.output is not None, "Workflow should have output"
        
        mcp_tools = result.output.get("mcp_tools_used", [])
        assert len(mcp_tools) >= min_tools, \
            f"Expected at least {min_tools} MCP tools, got {len(mcp_tools)}"
    
    @staticmethod
    def assert_workflow_state_consistency(
        result1: WorkflowResult,
        result2: WorkflowResult
    ) -> None:
        """Assert that two workflow results are consistent.
        
        Args:
            result1: First workflow result
            result2: Second workflow result
            
        Raises:
            AssertionError: If results are inconsistent
        """
        assert result1.run_id == result2.run_id, \
            f"Workflow IDs should match: {result1.run_id} vs {result2.run_id}"
        assert result1.status == result2.status, \
            f"Workflow statuses should match: {result1.status} vs {result2.status}"


@pytest.fixture
def workflow_assertions() -> WorkflowAssertions:
    """Provide workflow assertions helper for smoke tests."""
    return WorkflowAssertions()
