"""Monitoring and observability for runtime engine.

This module provides monitoring, tracing, and observability for the LangGraph
workflow execution, including metrics collection and LangSmith integration.
"""

import logging
import time
from datetime import datetime
from typing import Any, Callable

from gearmeshing_ai.agent.runtime.models import WorkflowState

logger = logging.getLogger(__name__)


class WorkflowMetrics:
    """Metrics collection for workflow execution.

    Attributes:
        run_id: Workflow run ID
        start_time: Workflow start time
        end_time: Workflow end time
        node_timings: Dictionary of node execution timings
        node_counts: Dictionary of node execution counts
        errors: List of errors encountered

    """

    def __init__(self, run_id: str) -> None:
        """Initialize WorkflowMetrics.

        Args:
            run_id: Workflow run ID

        """
        self.run_id = run_id
        self.start_time = datetime.utcnow()
        self.end_time: datetime | None = None
        self.node_timings: dict[str, list[float]] = {}
        self.node_counts: dict[str, int] = {}
        self.errors: list[dict[str, Any]] = []
        logger.debug(f"WorkflowMetrics initialized for run {run_id}")

    def record_node_execution(self, node_name: str, duration_seconds: float) -> None:
        """Record a node execution.

        Args:
            node_name: Name of the node
            duration_seconds: Execution duration in seconds

        """
        if node_name not in self.node_timings:
            self.node_timings[node_name] = []
            self.node_counts[node_name] = 0

        self.node_timings[node_name].append(duration_seconds)
        self.node_counts[node_name] += 1
        logger.debug(f"Recorded {node_name} execution: {duration_seconds:.3f}s")

    def record_error(self, node_name: str, error: Exception) -> None:
        """Record an error.

        Args:
            node_name: Name of the node where error occurred
            error: Exception that occurred

        """
        self.errors.append({
            "node": node_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.utcnow().isoformat(),
        })
        logger.warning(f"Error in {node_name}: {error}")

    def finalize(self) -> None:
        """Finalize metrics collection."""
        self.end_time = datetime.utcnow()
        logger.debug(f"Finalized metrics for run {self.run_id}")

    def get_total_duration(self) -> float:
        """Get total workflow duration in seconds.

        Returns:
            Total duration in seconds

        """
        if self.end_time is None:
            return (datetime.utcnow() - self.start_time).total_seconds()
        return (self.end_time - self.start_time).total_seconds()

    def get_node_average_time(self, node_name: str) -> float:
        """Get average execution time for a node.

        Args:
            node_name: Name of the node

        Returns:
            Average execution time in seconds

        """
        if node_name not in self.node_timings or not self.node_timings[node_name]:
            return 0.0

        timings = self.node_timings[node_name]
        return sum(timings) / len(timings)

    def get_node_total_time(self, node_name: str) -> float:
        """Get total execution time for a node.

        Args:
            node_name: Name of the node

        Returns:
            Total execution time in seconds

        """
        if node_name not in self.node_timings:
            return 0.0

        return sum(self.node_timings[node_name])

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary.

        Returns:
            Dictionary representation of metrics

        """
        return {
            "run_id": self.run_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration_seconds": self.get_total_duration(),
            "node_counts": self.node_counts,
            "node_average_times": {
                node: self.get_node_average_time(node)
                for node in self.node_timings.keys()
            },
            "node_total_times": {
                node: self.get_node_total_time(node)
                for node in self.node_timings.keys()
            },
            "error_count": len(self.errors),
            "errors": self.errors,
        }


class WorkflowMonitor:
    """Monitor for workflow execution.

    Provides timing, metrics collection, and observability for workflow execution.

    Attributes:
        metrics: Metrics collection for the workflow
        current_node: Currently executing node name

    """

    def __init__(self, run_id: str) -> None:
        """Initialize WorkflowMonitor.

        Args:
            run_id: Workflow run ID

        """
        self.metrics = WorkflowMetrics(run_id)
        self.current_node: str | None = None
        self.node_start_time: float | None = None
        logger.debug(f"WorkflowMonitor initialized for run {run_id}")

    def start_node(self, node_name: str) -> None:
        """Record the start of a node execution.

        Args:
            node_name: Name of the node

        """
        if self.current_node is not None:
            self.end_node()

        self.current_node = node_name
        self.node_start_time = time.time()
        logger.debug(f"Started node: {node_name}")

    def end_node(self) -> None:
        """Record the end of a node execution."""
        if self.current_node is None or self.node_start_time is None:
            return

        duration = time.time() - self.node_start_time
        self.metrics.record_node_execution(self.current_node, duration)
        logger.debug(f"Ended node: {self.current_node} ({duration:.3f}s)")

        self.current_node = None
        self.node_start_time = None

    def record_error(self, error: Exception) -> None:
        """Record an error.

        Args:
            error: Exception that occurred

        """
        node_name = self.current_node or "unknown"
        self.metrics.record_error(node_name, error)

    def finalize(self) -> WorkflowMetrics:
        """Finalize monitoring and return metrics.

        Returns:
            Collected metrics

        """
        self.end_node()
        self.metrics.finalize()
        logger.info(f"Workflow monitoring finalized: {self.metrics.to_dict()}")
        return self.metrics

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics.

        Returns:
            Dictionary representation of metrics

        """
        return self.metrics.to_dict()


def monitor_node_execution(node_name: str) -> Callable:
    """Decorator for monitoring node execution.

    Args:
        node_name: Name of the node being monitored

    Returns:
        Decorator function

    """

    def decorator(func: Callable) -> Callable:
        async def async_wrapper(
            state: WorkflowState,
            *args: Any,
            **kwargs: Any,
        ) -> dict[str, Any]:
            monitor = kwargs.pop("monitor", None)

            if monitor:
                monitor.start_node(node_name)

            try:
                result = await func(state, *args, **kwargs)
                return result
            except Exception as e:
                if monitor:
                    monitor.record_error(e)
                raise
            finally:
                if monitor:
                    monitor.end_node()

        def sync_wrapper(
            state: WorkflowState,
            *args: Any,
            **kwargs: Any,
        ) -> dict[str, Any]:
            monitor = kwargs.pop("monitor", None)

            if monitor:
                monitor.start_node(node_name)

            try:
                result = func(state, *args, **kwargs)
                return result
            except Exception as e:
                if monitor:
                    monitor.record_error(e)
                raise
            finally:
                if monitor:
                    monitor.end_node()

        # Return appropriate wrapper based on function type
        if hasattr(func, "__await__"):
            return async_wrapper
        return sync_wrapper

    return decorator


class ApprovalMetrics:
    """Metrics for approval tracking.

    Attributes:
        total_approvals: Total number of approvals
        approved_count: Number of approved requests
        rejected_count: Number of rejected requests
        pending_count: Number of pending requests
        average_approval_time: Average time to approval in seconds
        approval_times: List of approval times in seconds

    """

    def __init__(self) -> None:
        """Initialize ApprovalMetrics."""
        self.total_approvals = 0
        self.approved_count = 0
        self.rejected_count = 0
        self.pending_count = 0
        self.approval_times: list[float] = []
        logger.debug("ApprovalMetrics initialized")

    def record_approval(self, duration_seconds: float) -> None:
        """Record an approval.

        Args:
            duration_seconds: Time from request to approval in seconds

        """
        self.total_approvals += 1
        self.approved_count += 1
        self.approval_times.append(duration_seconds)
        logger.debug(f"Recorded approval: {duration_seconds:.1f}s")

    def record_rejection(self) -> None:
        """Record a rejection."""
        self.total_approvals += 1
        self.rejected_count += 1
        logger.debug("Recorded rejection")

    def record_pending(self) -> None:
        """Record a pending approval."""
        self.pending_count += 1
        logger.debug("Recorded pending approval")

    def get_average_approval_time(self) -> float:
        """Get average approval time.

        Returns:
            Average approval time in seconds

        """
        if not self.approval_times:
            return 0.0
        return sum(self.approval_times) / len(self.approval_times)

    def get_approval_rate(self) -> float:
        """Get approval rate (approved / total).

        Returns:
            Approval rate as percentage

        """
        if self.total_approvals == 0:
            return 0.0
        return (self.approved_count / self.total_approvals) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary.

        Returns:
            Dictionary representation of metrics

        """
        return {
            "total_approvals": self.total_approvals,
            "approved": self.approved_count,
            "rejected": self.rejected_count,
            "pending": self.pending_count,
            "approval_rate_percent": self.get_approval_rate(),
            "average_approval_time_seconds": self.get_average_approval_time(),
        }
