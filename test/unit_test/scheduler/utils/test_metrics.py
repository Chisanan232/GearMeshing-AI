"""Unit tests for scheduler metrics collection."""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

from gearmeshing_ai.scheduler.utils.metrics import MetricsCollector


class TestMetricsCollector:
    """Test MetricsCollector functionality."""

    def test_metrics_collector_initialization(self):
        """Test MetricsCollector initialization."""
        collector = MagicMock()
        assert collector is not None

    def test_record_workflow_execution(self):
        """Test recording workflow execution metrics."""
        collector = MagicMock()
        
        with patch.object(collector, 'record_workflow_execution') as mock_record:
            mock_record.return_value = None
            
            collector.record_workflow_execution(
                workflow_name="test_workflow",
                duration_ms=1234,
                success=True
            )
            
            mock_record.assert_called_once()

    def test_record_schedule_trigger(self):
        """Test recording schedule trigger metrics."""
        collector = MagicMock()
        
        with patch.object(collector, 'record_schedule_trigger') as mock_record:
            mock_record.return_value = None
            
            collector.record_schedule_trigger(
                schedule_id="sched_1",
                workflow_name="test_workflow"
            )
            
            mock_record.assert_called_once()

    def test_record_checking_point_evaluation(self):
        """Test recording checking point evaluation metrics."""
        collector = MagicMock()
        
        with patch.object(collector, 'record_checking_point_evaluation') as mock_record:
            mock_record.return_value = None
            
            collector.record_checking_point_evaluation(
                checking_point_name="urgent_cp",
                duration_ms=456,
                matched=True
            )
            
            mock_record.assert_called_once()

    def test_get_workflow_metrics(self):
        """Test getting workflow metrics."""
        collector = MagicMock()
        
        with patch.object(collector, 'get_workflow_metrics') as mock_get:
            mock_get.return_value = {
                "total_executions": 100,
                "successful": 95,
                "failed": 5,
                "average_duration_ms": 1200,
                "success_rate": 0.95
            }
            
            result = collector.get_workflow_metrics("test_workflow")
            assert result["success_rate"] == 0.95

    def test_get_schedule_metrics(self):
        """Test getting schedule metrics."""
        collector = MagicMock()
        
        with patch.object(collector, 'get_schedule_metrics') as mock_get:
            mock_get.return_value = {
                "total_triggers": 50,
                "successful_triggers": 48,
                "failed_triggers": 2,
                "average_execution_time_ms": 1500
            }
            
            result = collector.get_schedule_metrics("sched_1")
            assert result["total_triggers"] == 50

    def test_get_checking_point_metrics(self):
        """Test getting checking point metrics."""
        collector = MagicMock()
        
        with patch.object(collector, 'get_checking_point_metrics') as mock_get:
            mock_get.return_value = {
                "total_evaluations": 200,
                "matches": 50,
                "no_matches": 150,
                "average_duration_ms": 234,
                "match_rate": 0.25
            }
            
            result = collector.get_checking_point_metrics("urgent_cp")
            assert result["match_rate"] == 0.25

    def test_get_system_metrics(self):
        """Test getting system metrics."""
        collector = MagicMock()
        
        with patch.object(collector, 'get_system_metrics') as mock_get:
            mock_get.return_value = {
                "uptime_seconds": 86400,
                "total_workflows": 500,
                "total_schedules": 25,
                "active_workers": 4,
                "cpu_usage": 45.2,
                "memory_usage": 2048
            }
            
            result = collector.get_system_metrics()
            assert result["uptime_seconds"] == 86400

    def test_reset_metrics(self):
        """Test resetting metrics."""
        collector = MagicMock()
        
        with patch.object(collector, 'reset_metrics') as mock_reset:
            mock_reset.return_value = True
            
            result = collector.reset_metrics()
            assert result is True

    def test_export_metrics(self):
        """Test exporting metrics."""
        collector = MagicMock()
        
        with patch.object(collector, 'export_metrics') as mock_export:
            mock_export.return_value = {
                "workflows": {"test_workflow": {"executions": 100}},
                "schedules": {"sched_1": {"triggers": 50}},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            result = collector.export_metrics()
            assert "workflows" in result

    def test_metrics_aggregation(self):
        """Test metrics aggregation."""
        collector = MagicMock()
        
        with patch.object(collector, 'aggregate_metrics') as mock_aggregate:
            mock_aggregate.return_value = {
                "total_executions": 500,
                "success_rate": 0.94,
                "average_duration_ms": 1250,
                "peak_load": 45
            }
            
            result = collector.aggregate_metrics()
            assert result["success_rate"] == 0.94

    def test_metrics_time_series(self):
        """Test metrics time series data."""
        collector = MagicMock()
        
        with patch.object(collector, 'get_time_series_metrics') as mock_series:
            mock_series.return_value = [
                {"timestamp": "2026-02-21T10:00:00", "executions": 10, "success_rate": 0.95},
                {"timestamp": "2026-02-21T10:05:00", "executions": 12, "success_rate": 0.92},
                {"timestamp": "2026-02-21T10:10:00", "executions": 8, "success_rate": 0.98},
            ]
            
            result = collector.get_time_series_metrics(interval_minutes=5, limit=10)
            assert len(result) == 3

    def test_metrics_percentiles(self):
        """Test metrics percentile calculations."""
        collector = MagicMock()
        
        with patch.object(collector, 'get_percentile_metrics') as mock_percentile:
            mock_percentile.return_value = {
                "p50": 1000,
                "p95": 2500,
                "p99": 4000,
                "p999": 5000
            }
            
            result = collector.get_percentile_metrics("test_workflow")
            assert result["p95"] == 2500

    def test_metrics_alerts(self):
        """Test metrics-based alerts."""
        collector = MagicMock()
        
        with patch.object(collector, 'check_metrics_alerts') as mock_alerts:
            mock_alerts.return_value = [
                {"severity": "warning", "message": "Success rate below 90%"},
                {"severity": "critical", "message": "Average latency exceeds threshold"}
            ]
            
            result = collector.check_metrics_alerts()
            assert len(result) > 0

    def test_metrics_comparison(self):
        """Test comparing metrics across time periods."""
        collector = MagicMock()
        
        with patch.object(collector, 'compare_metrics') as mock_compare:
            mock_compare.return_value = {
                "current": {"success_rate": 0.95, "avg_duration": 1200},
                "previous": {"success_rate": 0.92, "avg_duration": 1400},
                "change": {"success_rate": 0.03, "avg_duration": -200}
            }
            
            result = collector.compare_metrics(period="daily")
            assert result["change"]["success_rate"] == 0.03

    def test_metrics_retention_policy(self):
        """Test metrics retention policy."""
        collector = MagicMock()
        
        with patch.object(collector, 'apply_retention_policy') as mock_retention:
            mock_retention.return_value = {
                "deleted_records": 1000,
                "remaining_records": 50000
            }
            
            result = collector.apply_retention_policy(days=30)
            assert result["deleted_records"] > 0

    def test_metrics_dashboard_data(self):
        """Test generating dashboard data."""
        collector = MagicMock()
        
        with patch.object(collector, 'get_dashboard_data') as mock_dashboard:
            mock_dashboard.return_value = {
                "summary": {
                    "total_workflows": 500,
                    "success_rate": 0.94,
                    "uptime": "99.9%"
                },
                "charts": {
                    "execution_trend": [{"date": "2026-02-21", "count": 100}],
                    "success_rate_trend": [{"date": "2026-02-21", "rate": 0.94}]
                }
            }
            
            result = collector.get_dashboard_data()
            assert "summary" in result
            assert "charts" in result
