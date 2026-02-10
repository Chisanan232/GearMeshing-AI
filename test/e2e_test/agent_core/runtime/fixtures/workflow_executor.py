"""WorkflowExecutor fixture for E2E tests - executes and tracks workflow."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from gearmeshing_ai.agent_core.runtime.models import WorkflowState


class WorkflowExecutor:
    """Execute and track workflow execution."""

    def __init__(self, workflow, approval_manager):
        """Initialize workflow executor."""
        self.workflow = workflow
        self.approval_manager = approval_manager
        self.execution_history: List[Dict[str, Any]] = []

    async def execute(self, initial_state: WorkflowState) -> WorkflowState:
        """Execute workflow and return final state."""
        try:
            # Execute workflow
            result = await self.workflow.ainvoke(initial_state)

            # Convert dict result to WorkflowState if needed
            if isinstance(result, dict):
                final_state = WorkflowState(**result)
            else:
                final_state = result

            # Track execution
            self.execution_history.append(
                {
                    "initial_state": initial_state,
                    "final_state": final_state,
                    "timestamp": datetime.now(),
                    "success": True,
                }
            )

            return final_state
        except Exception as e:
            # Track failed execution
            self.execution_history.append(
                {
                    "initial_state": initial_state,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "timestamp": datetime.now(),
                    "success": False,
                }
            )
            raise

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get execution history."""
        return self.execution_history

    def get_final_state(self) -> WorkflowState:
        """Get final state from last execution."""
        if not self.execution_history:
            raise RuntimeError("No executions recorded")

        last = self.execution_history[-1]
        if "final_state" in last:
            return last["final_state"]
        else:
            raise RuntimeError(f"Last execution failed: {last['error']}")

    def get_last_error(self) -> Optional[str]:
        """Get error from last execution."""
        if not self.execution_history:
            return None

        last = self.execution_history[-1]
        return last.get("error")

    def clear_history(self) -> None:
        """Clear execution history."""
        self.execution_history = []

    def assert_workflow_completed(self) -> None:
        """Assert workflow completed successfully."""
        if not self.execution_history:
            raise AssertionError("Workflow not executed")

        last = self.execution_history[-1]
        if not last["success"]:
            raise AssertionError(f"Workflow failed: {last['error']}")

    def assert_workflow_failed(self, error_type: Optional[type] = None) -> None:
        """Assert workflow failed."""
        if not self.execution_history:
            raise AssertionError("Workflow not executed")

        last = self.execution_history[-1]
        if last["success"]:
            raise AssertionError("Workflow did not fail")

        if error_type:
            error_str = last["error"]
            if error_type.__name__ not in error_str:
                raise AssertionError(
                    f"Expected {error_type.__name__}, got {error_str}"
                )

    def assert_final_state(self, state: str) -> None:
        """Assert final workflow state."""
        final_state = self.get_final_state()
        assert final_state.status.state == state, (
            f"Expected state {state}, got {final_state.status.state}"
        )

    def assert_execution_count(self, count: int) -> None:
        """Assert number of executions."""
        assert len(self.execution_history) == count, (
            f"Expected {count} executions, got {len(self.execution_history)}"
        )
