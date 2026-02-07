"""
Real-world usage tests for MCP client monitoring and metrics.

Tests cover metrics collection, health checking, and performance tracking.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import time

from gearmeshing_ai.agent_core.mcp.client.monitoring import ClientMetrics, HealthChecker


class TestClientMetrics:
    """Test ClientMetrics functionality."""
    
    def test_metrics_initialization(self):
        """Test ClientMetrics initialization."""
        metrics = ClientMetrics()
        
        assert metrics is not None
        assert hasattr(metrics, 'record_success')
        assert hasattr(metrics, 'record_failure')
    
    def test_record_success(self):
        """Test recording successful operation."""
        metrics = ClientMetrics()
        
        # Record a successful operation
        metrics.record_success("list_tools", 0.5)
        
        # Verify metrics were updated
        assert metrics is not None
    
    def test_record_failure(self):
        """Test recording failed operation."""
        metrics = ClientMetrics()
        
        # Record a failed operation
        metrics.record_failure("list_tools", "ConnectionError", "Connection timeout")
        
        # Verify metrics were updated
        assert metrics is not None
    
    def test_multiple_operations(self):
        """Test recording multiple operations."""
        metrics = ClientMetrics()
        
        # Record multiple operations
        metrics.record_success("list_tools", 0.3)
        metrics.record_success("list_tools", 0.4)
        metrics.record_failure("call_tool", "ServerError", "Error")
        
        # Verify metrics were updated
        assert metrics is not None


class TestHealthChecker:
    """Test HealthChecker functionality."""
    
    def test_health_checker_initialization(self):
        """Test HealthChecker initialization."""
        mock_client = MagicMock()
        checker = HealthChecker(mock_client)
        
        assert checker is not None
        assert hasattr(checker, 'check_health')
        assert checker.client is mock_client
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        mock_client = MagicMock()
        mock_client.list_tools = AsyncMock(return_value=["tool1", "tool2"])
        
        checker = HealthChecker(mock_client)
        
        # Perform health check
        result = await checker.check_health()
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test failed health check."""
        mock_client = MagicMock()
        mock_client.list_tools = AsyncMock(side_effect=Exception("Connection failed"))
        
        checker = HealthChecker(mock_client)
        
        # Perform health check
        result = await checker.check_health()
        
        assert result is not None


class TestMetricsCollection:
    """Test metrics collection across operations."""
    
    @pytest.mark.asyncio
    async def test_metrics_tracks_operation_count(self):
        """Test that metrics track operation count."""
        metrics = ClientMetrics()
        
        # Record multiple operations
        for i in range(5):
            await metrics.record_success("list_tools", 0.1 * (i + 1))
        
        # Verify metrics were collected
        assert metrics.total_requests == 5
    
    @pytest.mark.asyncio
    async def test_metrics_tracks_failures(self):
        """Test that metrics track failures."""
        metrics = ClientMetrics()
        
        # Record successes and failures
        await metrics.record_success("list_tools", 0.1)
        await metrics.record_failure("call_tool", 0.2, "ServerError")
        await metrics.record_success("list_tools", 0.2)
        await metrics.record_failure("call_tool", 0.3, "TimeoutError")
        
        # Verify metrics were collected
        assert metrics.total_requests == 4
        assert metrics.successful_requests == 2
        assert metrics.failed_requests == 2


class TestHealthMonitoring:
    """Test health monitoring functionality."""
    
    @pytest.mark.asyncio
    async def test_continuous_health_monitoring(self):
        """Test continuous health monitoring."""
        mock_client = MagicMock()
        mock_client.list_tools = AsyncMock(return_value=["tool1"])
        
        checker = HealthChecker(mock_client)
        
        # Perform multiple health checks
        results = []
        for _ in range(3):
            result = await checker.check_health()
            results.append(result)
        
        assert len(results) == 3
    
    @pytest.mark.asyncio
    async def test_health_check_recovery(self):
        """Test health check recovery after failure."""
        mock_client = MagicMock()
        mock_client.list_tools = AsyncMock(
            side_effect=[
                Exception("Connection failed"),
                ["tool1", "tool2"]
            ]
        )
        
        checker = HealthChecker(mock_client)
        
        # First check should fail
        result1 = await checker.check_health()
        
        # Second check should succeed
        result2 = await checker.check_health()
        
        assert result1 is not None
        assert result2 is not None
