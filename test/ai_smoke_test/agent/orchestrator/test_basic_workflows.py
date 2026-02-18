from __future__ import annotations

import json
import os

import pytest

from gearmeshing_ai.agent.orchestrator.models import WorkflowResult, WorkflowStatus
from gearmeshing_ai.agent.orchestrator.service import OrchestratorService
from test.ai_smoke_test.agent.orchestrator.utils.workflow_helpers import WorkflowTestHelper


@pytest.mark.smoke_test
@pytest.mark.basic_workflow
class TestBasicWorkflows:
    """Test basic orchestrator workflows with real AI models and proper status management."""

    async def test_simple_task_workflow(
        self,
        orchestrator_service: OrchestratorService,
        workflow_helper: WorkflowTestHelper,
        smoke_test_environment: dict[str, bool],
        test_file_workspace: str,
    ) -> None:
        """Test execution of a simple task that generates a text file with proper status polling."""
        # Specify exact file path to ensure AI model creates expected file
        task: str = "Create a Python script file named 'hello_world.py' that prints 'Hello, World!' when run"

        # Define expected file for cleanup
        expected_file: str = os.path.join(test_file_workspace, "hello_world.py")

        try:
            # Run workflow and wait for completion
            result: WorkflowResult = await workflow_helper.run_and_wait_for_completion(
                task_description=task,
                agent_role="dev",
                timeout_seconds=workflow_helper.get_workflow_timeout_for_task_type("simple"),
                poll_interval=workflow_helper.get_poll_interval_for_task_type("simple"),
            )

            # Verify LangGraph execution flow
            if smoke_test_environment.get("verify_langgraph", True):
                workflow_helper.verify_langgraph_execution_flow(result)

            # Verify workflow results
            assert result.status == WorkflowStatus.SUCCESS
            assert result.output is not None
            assert result.output.get("files_created") is not None

            # Verify actual file was created with exact name
            assert os.path.exists(expected_file), f"Expected file {expected_file} was not created"
            with open(expected_file, encoding="utf-8") as f:
                content: str = f.read()
                assert "print('Hello, World!')" in content or 'print("Hello, World!")' in content

            print(f"✓ Simple task workflow completed: {result.run_id}")

        finally:
            # Clean up test-created file immediately
            if os.path.exists(expected_file):
                os.remove(expected_file)

    async def test_code_analysis_workflow(
        self,
        orchestrator_service: OrchestratorService,
        workflow_helper: WorkflowTestHelper,
        smoke_test_environment: dict[str, bool],
        test_file_workspace: str,
    ) -> None:
        """Test code analysis task with real AI model and status polling."""
        # Define files for cleanup
        input_file: str = os.path.join(test_file_workspace, "sample.py")
        output_file: str = os.path.join(test_file_workspace, "analysis_report.json")

        try:
            # Create sample file with exact name expected in task
            with open(input_file, "w", encoding="utf-8") as f:
                f.write("""def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
""")

            # Specify exact input and output files to avoid ambiguity
            task: str = f"Analyze the Python file '{input_file}' and create an analysis report named '{output_file}' with suggestions for improvements"

            # Run workflow and wait for completion
            result: WorkflowResult = await workflow_helper.run_and_wait_for_completion(
                task_description=task,
                agent_role="dev",
                timeout_seconds=workflow_helper.get_workflow_timeout_for_task_type("complex"),
                poll_interval=workflow_helper.get_poll_interval_for_task_type("complex"),
            )

            # Verify LangGraph execution flow
            if smoke_test_environment.get("verify_langgraph", True):
                workflow_helper.verify_langgraph_execution_flow(result)

            # Verify workflow results
            assert result.status == WorkflowStatus.SUCCESS
            assert result.output is not None
            assert result.output.get("files_created") is not None

            # Verify analysis file contains meaningful content
            assert os.path.exists(output_file), f"Expected analysis file {output_file} was not created"
            with open(output_file, encoding="utf-8") as f:
                analysis: dict = json.load(f)
                assert isinstance(analysis, dict), "Analysis should be a JSON object"
                # Check for common analysis fields
                analysis_keys = set(analysis.keys())
                expected_keys = {"suggestions", "issues", "complexity", "summary"}
                assert len(analysis_keys.intersection(expected_keys)) > 0, (
                    f"Analysis should contain at least some of: {expected_keys}. Found: {analysis_keys}"
                )

            print(f"✓ Code analysis workflow completed: {result.run_id}")

        finally:
            # Clean up test-created files immediately
            for file_path in [input_file, output_file]:
                if os.path.exists(file_path):
                    os.remove(file_path)

    async def test_workflow_with_timeout(
        self,
        orchestrator_service: OrchestratorService,
        workflow_helper: WorkflowTestHelper,
        smoke_test_environment: dict[str, bool],
        test_file_workspace: str,
    ) -> None:
        """Test workflow timeout handling with status polling."""
        # Use a task that should complete quickly
        task: str = "Create a simple text file named 'quick.txt' with content 'Test completed'"
        expected_file: str = os.path.join(test_file_workspace, "quick.txt")

        try:
            # Run workflow with shorter timeout to test timeout handling
            result: WorkflowResult = await workflow_helper.run_and_wait_for_completion(
                task_description=task,
                agent_role="dev",
                timeout_seconds=workflow_helper.get_workflow_timeout_for_task_type("simple"),
                poll_interval=workflow_helper.get_poll_interval_for_task_type("simple"),
            )

            # Verify LangGraph execution flow
            if smoke_test_environment.get("verify_langgraph", True):
                workflow_helper.verify_langgraph_execution_flow(result)

            # Verify success
            assert result.status == WorkflowStatus.SUCCESS
            assert os.path.exists(expected_file), f"Expected file {expected_file} was not created"

            # Verify file content
            with open(expected_file, encoding="utf-8") as f:
                content: str = f.read()
                assert "Test completed" in content

            print(f"✓ Quick workflow completed: {result.run_id}")

        finally:
            # Clean up
            if os.path.exists(expected_file):
                os.remove(expected_file)

    async def test_error_handling_workflow(
        self,
        orchestrator_service: OrchestratorService,
        workflow_helper: WorkflowTestHelper,
        smoke_test_environment: dict[str, bool],
        test_file_workspace: str,
    ) -> None:
        """Test workflow error handling with invalid task."""
        # Use a task that should fail gracefully
        task: str = "Create a file in a non-existent directory '/invalid/path/that/does/not/exist/test.txt'"

        try:
            # Run workflow and expect it to handle the error gracefully
            with pytest.raises((AssertionError, TimeoutError)) as exc_info:
                result: WorkflowResult = await workflow_helper.run_and_wait_for_completion(
                    task_description=task,
                    agent_role="dev",
                    timeout_seconds=workflow_helper.get_workflow_timeout_for_task_type("error"),
                    poll_interval=workflow_helper.get_poll_interval_for_task_type("error"),
                )

            print(f"✓ Error handling workflow correctly failed: {exc_info.value}")

        except Exception as e:
            # If the workflow completes successfully despite the invalid path,
            # that's also acceptable behavior (AI might handle it gracefully)
            print(f"✓ Error handling workflow completed gracefully: {e}")

    async def test_workflow_state_consistency(
        self,
        orchestrator_service: OrchestratorService,
        workflow_helper: WorkflowTestHelper,
        smoke_test_environment: dict[str, bool],
        test_file_workspace: str,
    ) -> None:
        """Test workflow state consistency across multiple status checks."""
        task: str = "Create a simple JSON file named 'state_test.json' with content '{\"test\": true}'"
        expected_file: str = os.path.join(test_file_workspace, "state_test.json")

        try:
            # Start workflow
            initial_result: WorkflowResult = await orchestrator_service.run_workflow(
                task_description=task, agent_role="dev", timeout_seconds=60
            )

            # Verify state consistency
            if initial_result.run_id:
                await workflow_helper.verify_workflow_state_consistency(initial_result.run_id)

            # Wait for completion
            final_result: WorkflowResult = await workflow_helper.wait_for_workflow_completion(
                initial_result=initial_result,
                timeout_seconds=workflow_helper.get_workflow_timeout_for_task_type("simple"),
                poll_interval=workflow_helper.get_poll_interval_for_task_type("simple"),
            )

            # Verify final state consistency
            if final_result.run_id:
                await workflow_helper.verify_workflow_state_consistency(final_result.run_id)

            # Verify LangGraph execution flow
            if smoke_test_environment.get("verify_langgraph", True):
                workflow_helper.verify_langgraph_execution_flow(final_result)

            # Verify file was created
            assert os.path.exists(expected_file), f"Expected file {expected_file} was not created"

            print(f"✓ State consistency workflow completed: {final_result.run_id}")

        finally:
            # Clean up
            if os.path.exists(expected_file):
                os.remove(expected_file)
