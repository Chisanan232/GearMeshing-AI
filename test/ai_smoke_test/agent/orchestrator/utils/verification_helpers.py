from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from gearmeshing_ai.agent.orchestrator.models import WorkflowResult, WorkflowStatus


class VerificationHelper:
    """Helper class for verifying workflow results and side effects."""

    @staticmethod
    def verify_file_creation(file_path: str, expected_content: str | None = None, encoding: str = "utf-8") -> bool:
        """Verify that a file was created with expected content.

        Args:
            file_path: Path to the file to verify
            expected_content: Optional content that should be in the file
            encoding: File encoding

        Returns:
            True if verification passes, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return False

            if expected_content is not None:
                with open(file_path, encoding=encoding) as f:
                    actual_content = f.read()
                    if expected_content not in actual_content:
                        print(f"Expected content not found in {file_path}")
                        print(f"Expected: {expected_content}")
                        print(f"Actual content: {actual_content}")
                        return False

            return True

        except Exception as e:
            print(f"Error verifying file {file_path}: {e}")
            return False

    @staticmethod
    def verify_json_file_structure(file_path: str, required_fields: list[str], encoding: str = "utf-8") -> bool:
        """Verify that a JSON file has required fields.

        Args:
            file_path: Path to the JSON file
            required_fields: List of required field names
            encoding: File encoding

        Returns:
            True if verification passes, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                print(f"JSON file not found: {file_path}")
                return False

            with open(file_path, encoding=encoding) as f:
                data = json.load(f)

            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                print(f"Missing required fields in {file_path}: {missing_fields}")
                return False

            return True

        except json.JSONDecodeError as e:
            print(f"Invalid JSON in {file_path}: {e}")
            return False
        except Exception as e:
            print(f"Error verifying JSON file {file_path}: {e}")
            return False

    @staticmethod
    def verify_workflow_result_structure(result: WorkflowResult) -> bool:
        """Verify that workflow result has proper structure.

        Args:
            result: Workflow result to verify

        Returns:
            True if structure is valid, False otherwise
        """
        try:
            # Check required attributes
            if not hasattr(result, "status"):
                print("Workflow result missing status attribute")
                return False

            if not hasattr(result, "run_id"):
                print("Workflow result missing run_id attribute")
                return False

            # Check status is valid
            valid_statuses = {status.value for status in WorkflowStatus}
            if result.status not in valid_statuses:
                print(f"Invalid workflow status: {result.status}")
                return False

            # Check run_id is not None for non-initial results
            if result.run_id is None and result.status != WorkflowStatus.IN_PROGRESS:
                print("Workflow ID should not be None for completed workflow")
                return False

            return True

        except Exception as e:
            print(f"Error verifying workflow result structure: {e}")
            return False

    @staticmethod
    def verify_langgraph_execution(result: WorkflowResult) -> bool:
        """Verify that LangGraph execution patterns are present.

        Args:
            result: Workflow result to verify

        Returns:
            True if LangGraph patterns are detected, False otherwise
        """
        try:
            if not hasattr(result, "execution_history") or not result.execution_history:
                print("Execution history not available for LangGraph verification")
                return True  # Skip verification if not available

            history = result.execution_history

            # Check for multiple execution nodes
            if len(history) < 2:
                print("Expected at least 2 execution nodes for LangGraph")
                return False

            # Check for expected node types
            node_types = set()
            for node in history:
                if isinstance(node, dict) and "node_type" in node:
                    node_types.add(node["node_type"])

            expected_types = {"planner", "executor", "verifier"}
            found_types = node_types.intersection(expected_types)

            if len(found_types) == 0:
                print(f"No expected LangGraph node types found. Found: {node_types}")
                return False

            print(f"Found LangGraph node types: {found_types}")
            return True

        except Exception as e:
            print(f"Error verifying LangGraph execution: {e}")
            return False

    @staticmethod
    def verify_mcp_integration(result: WorkflowResult) -> bool:
        """Verify that MCP integration was used in workflow.

        Args:
            result: Workflow result to verify

        Returns:
            True if MCP integration is detected, False otherwise
        """
        try:
            if not result.output:
                print("No output available for MCP verification")
                return False

            output = result.output

            # Check for MCP tool usage
            mcp_tools_used = output.get("mcp_tools_used", [])
            if len(mcp_tools_used) == 0:
                print("No MCP tools were used")
                return False

            # Check for MCP service interactions
            mcp_interactions = output.get("mcp_interactions", [])
            if len(mcp_interactions) == 0:
                print("No MCP interactions recorded")
                return False

            print(f"MCP integration verified: {len(mcp_tools_used)} tools, {len(mcp_interactions)} interactions")
            return True

        except Exception as e:
            print(f"Error verifying MCP integration: {e}")
            return False

    @staticmethod
    def verify_approval_workflow(result: WorkflowResult) -> bool:
        """Verify that approval workflow was handled correctly.

        Args:
            result: Workflow result to verify

        Returns:
            True if approval workflow is valid, False otherwise
        """
        try:
            if result.status == WorkflowStatus.AWAITING_APPROVAL:
                # Check approval request structure
                if not result.approval_request:
                    print("Approval workflow awaiting approval but no approval request found")
                    return False

                if not hasattr(result.approval_request, "description"):
                    print("Approval request missing description")
                    return False

                if not result.approval_request.description.strip():
                    print("Approval request description is empty")
                    return False

            elif result.status == WorkflowStatus.SUCCESS:
                # Check if approval was processed
                if hasattr(result, "approval_history") and result.approval_history:
                    print("Approval workflow completed with approval history")
                else:
                    print("Approval workflow completed (no approval history available)")

            return True

        except Exception as e:
            print(f"Error verifying approval workflow: {e}")
            return False

    @staticmethod
    def verify_cleanup_effectiveness(original_state: dict[str, Any], current_state: dict[str, Any]) -> bool:
        """Verify that cleanup was effective by comparing states.

        Args:
            original_state: State before cleanup
            current_state: State after cleanup

        Returns:
            True if cleanup was effective, False otherwise
        """
        try:
            # Check file cleanup
            original_files = set(original_state.get("files", []))
            current_files = set(current_state.get("files", []))

            remaining_files = original_files.intersection(current_files)
            if remaining_files:
                print(f"Cleanup incomplete: files still exist: {remaining_files}")
                return False

            # Check MCP resource cleanup
            original_resources = set(original_state.get("mcp_resources", []))
            current_resources = set(current_state.get("mcp_resources", []))

            remaining_resources = original_resources.intersection(current_resources)
            if remaining_resources:
                print(f"Cleanup incomplete: MCP resources still exist: {remaining_resources}")
                return False

            return True

        except Exception as e:
            print(f"Error verifying cleanup effectiveness: {e}")
            return False

    @staticmethod
    def capture_current_state(directory: str) -> dict[str, Any]:
        """Capture current state for cleanup verification.

        Args:
            directory: Directory to capture state from

        Returns:
            Dictionary representing current state
        """
        try:
            state = {"files": [], "mcp_resources": [], "timestamp": None}

            # Capture files
            dir_path = Path(directory)
            if dir_path.exists():
                for file_path in dir_path.rglob("*"):
                    if file_path.is_file():
                        state["files"].append(str(file_path))

            # Note: MCP resources would need to be captured via MCP client
            # This is a placeholder for future implementation

            return state

        except Exception as e:
            print(f"Error capturing current state: {e}")
            return {"files": [], "mcp_resources": [], "timestamp": None}

    @staticmethod
    def verify_workflow_performance(
        result: WorkflowResult, max_duration_seconds: float | None = None, max_cost: float | None = None
    ) -> bool:
        """Verify workflow performance metrics.

        Args:
            result: Workflow result to verify
            max_duration_seconds: Maximum allowed duration
            max_cost: Maximum allowed cost

        Returns:
            True if performance is acceptable, False otherwise
        """
        try:
            # Check duration
            if max_duration_seconds is not None:
                if hasattr(result, "duration_seconds") and result.duration_seconds:
                    if result.duration_seconds > max_duration_seconds:
                        print(f"Workflow exceeded duration limit: {result.duration_seconds}s > {max_duration_seconds}s")
                        return False

            # Check cost
            if max_cost is not None:
                if hasattr(result, "cost") and result.cost:
                    if result.cost > max_cost:
                        print(f"Workflow exceeded cost limit: ${result.cost:.4f} > ${max_cost:.4f}")
                        return False

            return True

        except Exception as e:
            print(f"Error verifying workflow performance: {e}")
            return False


@pytest.fixture
def verification_helper() -> VerificationHelper:
    """Provide verification helper for smoke tests."""
    return VerificationHelper()
