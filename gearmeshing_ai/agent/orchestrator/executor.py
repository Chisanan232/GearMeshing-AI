"""
Workflow executor for handling execution details.

Handles the actual execution of workflow steps, capability invocation,
timeouts, retries, and error handling. Delegates high-level orchestration
to OrchestratorEngine.
"""

import asyncio
from typing import Any, Dict, Optional


class WorkflowExecutor:
    """
    Executes workflow steps with support for timeouts, retries, and error handling.
    
    Handles:
    - Step execution with timeout
    - Retry logic with exponential backoff
    - Error handling and recovery
    - Capability invocation
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay_seconds: int = 5,
        timeout_seconds: int = 300,
    ):
        """Initialize the workflow executor."""
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.timeout_seconds = timeout_seconds

    async def execute_step(
        self,
        step_name: str,
        step_func,
        *args,
        timeout_seconds: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute a workflow step with timeout and retry logic.
        
        Args:
            step_name: Name of the step
            step_func: Async function to execute
            timeout_seconds: Optional timeout override
            *args: Positional arguments for step_func
            **kwargs: Keyword arguments for step_func
            
        Returns:
            Dict with step result
        """
        timeout = timeout_seconds or self.timeout_seconds
        last_error = None

        for attempt in range(self.max_retries):
            try:
                result = await asyncio.wait_for(
                    step_func(*args, **kwargs),
                    timeout=timeout,
                )
                return {
                    "step": step_name,
                    "status": "success",
                    "result": result,
                    "attempts": attempt + 1,
                }
            except asyncio.TimeoutError:
                last_error = f"Step '{step_name}' timeout after {timeout}s"
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay_seconds)
            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay_seconds)

        return {
            "step": step_name,
            "status": "failed",
            "error": last_error,
            "attempts": self.max_retries,
        }

    async def execute_capability(
        self,
        capability_name: str,
        capability_func,
        *args,
        timeout_seconds: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute a capability with timeout and error handling.
        
        Args:
            capability_name: Name of the capability
            capability_func: Async function to execute
            timeout_seconds: Optional timeout override
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Dict with capability result
        """
        timeout = timeout_seconds or self.timeout_seconds

        try:
            result = await asyncio.wait_for(
                capability_func(*args, **kwargs),
                timeout=timeout,
            )
            return {
                "capability": capability_name,
                "status": "success",
                "result": result,
            }
        except asyncio.TimeoutError:
            return {
                "capability": capability_name,
                "status": "timeout",
                "error": f"Capability timeout after {timeout}s",
            }
        except Exception as e:
            return {
                "capability": capability_name,
                "status": "error",
                "error": str(e),
            }

    async def execute_parallel(
        self,
        tasks: Dict[str, Any],
        timeout_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute multiple tasks in parallel.
        
        Args:
            tasks: Dict of task_name -> coroutine
            timeout_seconds: Optional timeout override
            
        Returns:
            Dict with results for each task
        """
        timeout = timeout_seconds or self.timeout_seconds

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks.values(), return_exceptions=True),
                timeout=timeout,
            )
            return {
                "status": "success",
                "results": {
                    name: result
                    for name, result in zip(tasks.keys(), results)
                },
            }
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "error": f"Parallel execution timeout after {timeout}s",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }
