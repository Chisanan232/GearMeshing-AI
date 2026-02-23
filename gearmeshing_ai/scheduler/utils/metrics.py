"""Metrics collection for the scheduler system.

This module provides metrics collection and reporting functionality for monitoring
scheduler performance and activity.
"""

import asyncio
from collections import defaultdict, deque
from datetime import datetime
from typing import Any

from gearmeshing_ai.scheduler.config.settings import get_scheduler_settings


class SchedulerMetrics:
    """Scheduler metrics data structure."""

    def __init__(self):
        """Initialize scheduler metrics."""
        self.workflow_metrics = WorkflowMetrics()
        self.checking_point_metrics = CheckingPointMetrics()
        self.ai_workflow_metrics = AIWorkflowMetrics()
        self.system_metrics = SystemMetrics()
        self.performance_metrics = PerformanceMetrics()


class WorkflowMetrics:
    """Workflow execution metrics."""

    def __init__(self):
        """Initialize workflow metrics."""
        self.total_workflows = 0
        self.successful_workflows = 0
        self.failed_workflows = 0
        self.active_workflows = 0
        self.workflow_durations = deque(maxlen=1000)  # Keep last 1000 durations
        self.workflow_types = defaultdict(int)
        self.workflow_errors = defaultdict(int)
        self.last_workflow_time = None

    def record_workflow_start(self, workflow_type: str):
        """Record workflow start."""
        self.total_workflows += 1
        self.active_workflows += 1
        self.workflow_types[workflow_type] += 1
        self.last_workflow_time = datetime.utcnow()

    def record_workflow_success(self, workflow_type: str, duration_ms: float):
        """Record successful workflow completion."""
        self.successful_workflows += 1
        self.active_workflows = max(0, self.active_workflows - 1)
        self.workflow_durations.append(duration_ms)

    def record_workflow_failure(self, workflow_type: str, error_type: str, duration_ms: float):
        """Record workflow failure."""
        self.failed_workflows += 1
        self.active_workflows = max(0, self.active_workflows - 1)
        self.workflow_durations.append(duration_ms)
        self.workflow_errors[error_type] += 1

    def get_success_rate(self) -> float:
        """Get workflow success rate."""
        if self.total_workflows == 0:
            return 0.0
        return (self.successful_workflows / self.total_workflows) * 100

    def get_average_duration(self) -> float:
        """Get average workflow duration."""
        if not self.workflow_durations:
            return 0.0
        return sum(self.workflow_durations) / len(self.workflow_durations)

    def get_summary(self) -> dict[str, Any]:
        """Get workflow metrics summary."""
        return {
            "total_workflows": self.total_workflows,
            "successful_workflows": self.successful_workflows,
            "failed_workflows": self.failed_workflows,
            "active_workflows": self.active_workflows,
            "success_rate": self.get_success_rate(),
            "average_duration_ms": self.get_average_duration(),
            "workflow_types": dict(self.workflow_types),
            "workflow_errors": dict(self.workflow_errors),
            "last_workflow_time": self.last_workflow_time.isoformat() if self.last_workflow_time else None,
        }


class CheckingPointMetrics:
    """Checking point evaluation metrics."""

    def __init__(self):
        """Initialize checking point metrics."""
        self.total_evaluations = 0
        self.matching_evaluations = 0
        self.non_matching_evaluations = 0
        self.error_evaluations = 0
        self.checking_point_types = defaultdict(int)
        self.evaluation_durations = deque(maxlen=1000)
        self.action_counts = defaultdict(int)
        self.last_evaluation_time = None

    def record_evaluation_start(self, checking_point_type: str):
        """Record checking point evaluation start."""
        self.total_evaluations += 1
        self.checking_point_types[checking_point_type] += 1
        self.last_evaluation_time = datetime.utcnow()

    def record_evaluation_match(self, checking_point_type: str, duration_ms: float, actions_count: int = 0):
        """Record matching evaluation."""
        self.matching_evaluations += 1
        self.evaluation_durations.append(duration_ms)
        self.action_counts["total"] += actions_count

    def record_evaluation_no_match(self, checking_point_type: str, duration_ms: float):
        """Record non-matching evaluation."""
        self.non_matching_evaluations += 1
        self.evaluation_durations.append(duration_ms)

    def record_evaluation_error(self, checking_point_type: str, duration_ms: float):
        """Record evaluation error."""
        self.error_evaluations += 1
        self.evaluation_durations.append(duration_ms)

    def get_match_rate(self) -> float:
        """Get evaluation match rate."""
        if self.total_evaluations == 0:
            return 0.0
        return (self.matching_evaluations / self.total_evaluations) * 100

    def get_average_duration(self) -> float:
        """Get average evaluation duration."""
        if not self.evaluation_durations:
            return 0.0
        return sum(self.evaluation_durations) / len(self.evaluation_durations)

    def get_summary(self) -> dict[str, Any]:
        """Get checking point metrics summary."""
        return {
            "total_evaluations": self.total_evaluations,
            "matching_evaluations": self.matching_evaluations,
            "non_matching_evaluations": self.non_matching_evaluations,
            "error_evaluations": self.error_evaluations,
            "match_rate": self.get_match_rate(),
            "average_duration_ms": self.get_average_duration(),
            "checking_point_types": dict(self.checking_point_types),
            "action_counts": dict(self.action_counts),
            "last_evaluation_time": self.last_evaluation_time.isoformat() if self.last_evaluation_time else None,
        }


class AIWorkflowMetrics:
    """AI workflow execution metrics."""

    def __init__(self):
        """Initialize AI workflow metrics."""
        self.total_ai_workflows = 0
        self.successful_ai_workflows = 0
        self.failed_ai_workflows = 0
        self.ai_workflow_durations = deque(maxlen=1000)
        self.ai_workflow_types = defaultdict(int)
        self.ai_provider_usage = defaultdict(int)
        self.token_usage = defaultdict(int)
        self.cost_tracking = defaultdict(float)
        self.last_ai_workflow_time = None

    def record_ai_workflow_start(self, workflow_type: str, provider: str):
        """Record AI workflow start."""
        self.total_ai_workflows += 1
        self.ai_workflow_types[workflow_type] += 1
        self.ai_provider_usage[provider] += 1
        self.last_ai_workflow_time = datetime.utcnow()

    def record_ai_workflow_success(
        self, workflow_type: str, duration_ms: float, tokens_used: int = 0, cost: float = 0.0
    ):
        """Record successful AI workflow."""
        self.successful_ai_workflows += 1
        self.ai_workflow_durations.append(duration_ms)
        self.token_usage["total"] += tokens_used
        self.cost_tracking["total"] += cost

    def record_ai_workflow_failure(self, workflow_type: str, duration_ms: float):
        """Record failed AI workflow."""
        self.failed_ai_workflows += 1
        self.ai_workflow_durations.append(duration_ms)

    def get_success_rate(self) -> float:
        """Get AI workflow success rate."""
        if self.total_ai_workflows == 0:
            return 0.0
        return (self.successful_ai_workflows / self.total_ai_workflows) * 100

    def get_average_duration(self) -> float:
        """Get average AI workflow duration."""
        if not self.ai_workflow_durations:
            return 0.0
        return sum(self.ai_workflow_durations) / len(self.ai_workflow_durations)

    def get_summary(self) -> dict[str, Any]:
        """Get AI workflow metrics summary."""
        return {
            "total_ai_workflows": self.total_ai_workflows,
            "successful_ai_workflows": self.successful_ai_workflows,
            "failed_ai_workflows": self.failed_ai_workflows,
            "success_rate": self.get_success_rate(),
            "average_duration_ms": self.get_average_duration(),
            "ai_workflow_types": dict(self.ai_workflow_types),
            "ai_provider_usage": dict(self.ai_provider_usage),
            "token_usage": dict(self.token_usage),
            "cost_tracking": dict(self.cost_tracking),
            "last_ai_workflow_time": self.last_ai_workflow_time.isoformat() if self.last_ai_workflow_time else None,
        }


class SystemMetrics:
    """System resource metrics."""

    def __init__(self):
        """Initialize system metrics."""
        self.start_time = datetime.utcnow()
        self.uptime_seconds = 0
        self.memory_usage_mb = 0
        self.cpu_usage_percent = 0
        self.disk_usage_gb = 0
        self.network_io_bytes = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.warning_counts = defaultdict(int)

    def update_system_metrics(self):
        """Update system metrics."""
        self.uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()

        # TODO: Implement actual system metrics collection
        # For now, use placeholder values
        try:
            import psutil

            process = psutil.Process()

            # Memory usage
            memory_info = process.memory_info()
            self.memory_usage_mb = memory_info.rss / 1024 / 1024

            # CPU usage
            self.cpu_usage_percent = process.cpu_percent()

            # Disk usage
            disk_usage = psutil.disk_usage("/")
            self.disk_usage_gb = disk_usage.used / 1024 / 1024 / 1024

            # Network I/O
            net_io = psutil.net_io_counters()
            self.network_io_bytes["bytes_sent"] = net_io.bytes_sent
            self.network_io_bytes["bytes_recv"] = net_io.bytes_recv

        except ImportError:
            # psutil not available, use placeholder values
            pass
        except Exception:
            # Error collecting system metrics
            pass

    def record_error(self, error_type: str):
        """Record system error."""
        self.error_counts[error_type] += 1

    def record_warning(self, warning_type: str):
        """Record system warning."""
        self.warning_counts[warning_type] += 1

    def get_summary(self) -> dict[str, Any]:
        """Get system metrics summary."""
        self.update_system_metrics()

        return {
            "uptime_seconds": self.uptime_seconds,
            "start_time": self.start_time.isoformat(),
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "disk_usage_gb": self.disk_usage_gb,
            "network_io_bytes": dict(self.network_io_bytes),
            "error_counts": dict(self.error_counts),
            "warning_counts": dict(self.warning_counts),
        }


class PerformanceMetrics:
    """Performance metrics."""

    def __init__(self):
        """Initialize performance metrics."""
        self.request_counts = defaultdict(int)
        self.response_times = deque(maxlen=1000)
        self.error_rates = defaultdict(float)
        self.throughput_per_minute = deque(maxlen=60)  # Last 60 minutes
        self.last_request_time = None

    def record_request(self, endpoint: str, response_time_ms: float, success: bool = True):
        """Record API request."""
        self.request_counts[endpoint] += 1
        self.response_times.append(response_time_ms)
        self.last_request_time = datetime.utcnow()

        # Update error rate
        if not success:
            current_error_rate = self.error_rates.get(endpoint, 0.0)
            total_requests = self.request_counts[endpoint]
            if total_requests > 0:
                # Simple moving average for error rate
                self.error_rates[endpoint] = (current_error_rate * (total_requests - 1) + 1.0) / total_requests

    def get_average_response_time(self) -> float:
        """Get average response time."""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)

    def get_throughput(self) -> float:
        """Get current throughput (requests per second)."""
        # TODO: Implement proper throughput calculation
        # For now, return requests per minute
        if len(self.throughput_per_minute) == 0:
            return 0.0
        return sum(self.throughput_per_minute) / len(self.throughput_per_minute)

    def get_summary(self) -> dict[str, Any]:
        """Get performance metrics summary."""
        return {
            "request_counts": dict(self.request_counts),
            "average_response_time_ms": self.get_average_response_time(),
            "error_rates": dict(self.error_rates),
            "throughput_per_second": self.get_throughput(),
            "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
        }


class MetricsCollector:
    """Main metrics collector for the scheduler."""

    def __init__(self):
        """Initialize the metrics collector."""
        self.settings = get_scheduler_settings()
        self.metrics = SchedulerMetrics()
        self.collection_interval = 60  # Collect metrics every 60 seconds
        self._collection_task = None
        self._running = False

    async def start_collection(self):
        """Start metrics collection."""
        if self._running:
            return

        self._running = True
        self._collection_task = asyncio.create_task(self._collect_metrics_loop())

    async def stop_collection(self):
        """Stop metrics collection."""
        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass

    async def _collect_metrics_loop(self):
        """Main metrics collection loop."""
        while self._running:
            try:
                # Update system metrics
                self.metrics.system_metrics.update_system_metrics()

                # Calculate throughput for current minute
                # TODO: Implement proper throughput calculation

                await asyncio.sleep(self.collection_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue collection
                self.metrics.system_metrics.record_error("metrics_collection_error")
                await asyncio.sleep(self.collection_interval)

    def get_all_metrics(self) -> dict[str, Any]:
        """Get all collected metrics."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "collection_interval": self.collection_interval,
            "workflow_metrics": self.metrics.workflow_metrics.get_summary(),
            "checking_point_metrics": self.metrics.checking_point_metrics.get_summary(),
            "ai_workflow_metrics": self.metrics.ai_workflow_metrics.get_summary(),
            "system_metrics": self.metrics.system_metrics.get_summary(),
            "performance_metrics": self.metrics.performance_metrics.get_summary(),
        }

    def get_workflow_metrics(self) -> dict[str, Any]:
        """Get workflow metrics."""
        return self.metrics.workflow_metrics.get_summary()

    def get_checking_point_metrics(self) -> dict[str, Any]:
        """Get checking point metrics."""
        return self.metrics.checking_point_metrics.get_summary()

    def get_ai_workflow_metrics(self) -> dict[str, Any]:
        """Get AI workflow metrics."""
        return self.metrics.ai_workflow_metrics.get_summary()

    def get_system_metrics(self) -> dict[str, Any]:
        """Get system metrics."""
        self.metrics.system_metrics.update_system_metrics()
        return self.metrics.system_metrics.get_summary()

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get performance metrics."""
        return self.metrics.performance_metrics.get_summary()

    def reset_metrics(self):
        """Reset all metrics."""
        self.metrics = SchedulerMetrics()

    def record_workflow_start(self, workflow_type: str):
        """Record workflow start."""
        self.metrics.workflow_metrics.record_workflow_start(workflow_type)

    def record_workflow_success(self, workflow_type: str, duration_ms: float):
        """Record workflow success."""
        self.metrics.workflow_metrics.record_workflow_success(workflow_type, duration_ms)

    def record_workflow_failure(self, workflow_type: str, error_type: str, duration_ms: float):
        """Record workflow failure."""
        self.metrics.workflow_metrics.record_workflow_failure(workflow_type, error_type, duration_ms)
        self.metrics.system_metrics.record_error(f"workflow_failure_{error_type}")

    def record_evaluation_start(self, checking_point_type: str):
        """Record checking point evaluation start."""
        self.metrics.checking_point_metrics.record_evaluation_start(checking_point_type)

    def record_evaluation_match(self, checking_point_type: str, duration_ms: float, actions_count: int = 0):
        """Record matching evaluation."""
        self.metrics.checking_point_metrics.record_evaluation_match(checking_point_type, duration_ms, actions_count)

    def record_evaluation_no_match(self, checking_point_type: str, duration_ms: float):
        """Record non-matching evaluation."""
        self.metrics.checking_point_metrics.record_evaluation_no_match(checking_point_type, duration_ms)

    def record_evaluation_error(self, checking_point_type: str, duration_ms: float):
        """Record evaluation error."""
        self.metrics.checking_point_metrics.record_evaluation_error(checking_point_type, duration_ms)
        self.metrics.system_metrics.record_error(f"evaluation_error_{checking_point_type}")

    def record_ai_workflow_start(self, workflow_type: str, provider: str):
        """Record AI workflow start."""
        self.metrics.ai_workflow_metrics.record_ai_workflow_start(workflow_type, provider)

    def record_ai_workflow_success(
        self, workflow_type: str, duration_ms: float, tokens_used: int = 0, cost: float = 0.0
    ):
        """Record successful AI workflow."""
        self.metrics.ai_workflow_metrics.record_ai_workflow_success(workflow_type, duration_ms, tokens_used, cost)

    def record_ai_workflow_failure(self, workflow_type: str, duration_ms: float):
        """Record failed AI workflow."""
        self.metrics.ai_workflow_metrics.record_ai_workflow_failure(workflow_type, duration_ms)
        self.metrics.system_metrics.record_error(f"ai_workflow_failure_{workflow_type}")

    def record_api_request(self, endpoint: str, response_time_ms: float, success: bool = True):
        """Record API request."""
        self.metrics.performance_metrics.record_request(endpoint, response_time_ms, success)

        if not success:
            self.metrics.system_metrics.record_error(f"api_error_{endpoint}")


# Global metrics collector instance
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
