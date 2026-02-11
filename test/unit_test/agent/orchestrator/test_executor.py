"""Unit tests for the workflow executor."""

from __future__ import annotations

import asyncio

import pytest

from gearmeshing_ai.agent.orchestrator.executor import WorkflowExecutor


class TestWorkflowExecutor:
    """Test suite for WorkflowExecutor."""

    @pytest.fixture
    def executor(self):
        """Create a workflow executor for testing."""
        return WorkflowExecutor(
            max_retries=3,
            retry_delay_seconds=0.1,
            timeout_seconds=5,
        )

    @pytest.mark.asyncio
    async def test_execute_step_success(self, executor):
        """Test successful step execution."""
        async def sample_step():
            await asyncio.sleep(0.01)
            return {"result": "success"}

        result = await executor.execute_step(
            step_name="test_step",
            step_func=sample_step,
        )

        assert result["status"] == "success"
        assert result["step"] == "test_step"
        assert result["attempts"] == 1

    @pytest.mark.asyncio
    async def test_execute_step_timeout(self, executor):
        """Test step execution timeout."""
        async def slow_step():
            await asyncio.sleep(10)

        result = await executor.execute_step(
            step_name="slow_step",
            step_func=slow_step,
            timeout_seconds=0.1,
        )

        assert result["status"] == "failed"
        assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_step_with_retry(self, executor):
        """Test step execution with retry."""
        call_count = 0

        async def flaky_step():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary error")
            return {"result": "success"}

        result = await executor.execute_step(
            step_name="flaky_step",
            step_func=flaky_step,
        )

        assert result["status"] == "success"
        assert result["attempts"] == 2

    @pytest.mark.asyncio
    async def test_execute_step_max_retries_exceeded(self, executor):
        """Test step execution with max retries exceeded."""
        async def always_fails():
            raise ValueError("Always fails")

        result = await executor.execute_step(
            step_name="failing_step",
            step_func=always_fails,
        )

        assert result["status"] == "failed"
        assert result["attempts"] == 3

    @pytest.mark.asyncio
    async def test_execute_capability_success(self, executor):
        """Test successful capability execution."""
        async def sample_capability():
            await asyncio.sleep(0.01)
            return {"data": "capability_result"}

        result = await executor.execute_capability(
            capability_name="test_capability",
            capability_func=sample_capability,
        )

        assert result["status"] == "success"
        assert result["capability"] == "test_capability"

    @pytest.mark.asyncio
    async def test_execute_capability_timeout(self, executor):
        """Test capability execution timeout."""
        async def slow_capability():
            await asyncio.sleep(10)

        result = await executor.execute_capability(
            capability_name="slow_capability",
            capability_func=slow_capability,
            timeout_seconds=0.1,
        )

        assert result["status"] == "timeout"
        assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_capability_error(self, executor):
        """Test capability execution error."""
        async def failing_capability():
            raise RuntimeError("Capability failed")

        result = await executor.execute_capability(
            capability_name="failing_capability",
            capability_func=failing_capability,
        )

        assert result["status"] == "error"
        assert "failed" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_parallel_success(self, executor):
        """Test successful parallel execution."""
        async def task_1():
            await asyncio.sleep(0.01)
            return "result_1"

        async def task_2():
            await asyncio.sleep(0.01)
            return "result_2"

        async def task_3():
            await asyncio.sleep(0.01)
            return "result_3"

        result = await executor.execute_parallel(
            tasks={
                "task_1": task_1(),
                "task_2": task_2(),
                "task_3": task_3(),
            },
        )

        assert result["status"] == "success"
        assert len(result["results"]) == 3
        assert result["results"]["task_1"] == "result_1"

    @pytest.mark.asyncio
    async def test_execute_parallel_timeout(self, executor):
        """Test parallel execution timeout."""
        async def slow_task():
            await asyncio.sleep(10)

        result = await executor.execute_parallel(
            tasks={
                "slow_task": slow_task(),
            },
            timeout_seconds=0.1,
        )

        assert result["status"] == "timeout"

    @pytest.mark.asyncio
    async def test_execute_parallel_with_exception(self, executor):
        """Test parallel execution with exception."""
        async def failing_task():
            raise ValueError("Task failed")

        async def success_task():
            return "success"

        result = await executor.execute_parallel(
            tasks={
                "failing_task": failing_task(),
                "success_task": success_task(),
            },
        )

        assert result["status"] == "success"
        assert isinstance(result["results"]["failing_task"], ValueError)
        assert result["results"]["success_task"] == "success"
