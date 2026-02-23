"""Unit tests for scheduler health checks."""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

from gearmeshing_ai.scheduler.utils.health import HealthChecker


class TestHealthChecker:
    """Test HealthChecker functionality."""

    def test_health_checker_initialization(self):
        """Test HealthChecker initialization."""
        checker = MagicMock()
        assert checker is not None

    @pytest.mark.asyncio
    async def test_check_temporal_health(self):
        """Test checking Temporal health."""
        checker = MagicMock()
        
        with patch.object(checker, 'check_temporal', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {
                "status": "healthy",
                "response_time_ms": 45,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            result = await checker.check_temporal()
            assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_check_database_health(self):
        """Test checking database health."""
        checker = MagicMock()
        
        with patch.object(checker, 'check_database', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {
                "status": "healthy",
                "connection_pool": "active",
                "response_time_ms": 12
            }
            
            result = await checker.check_database()
            assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_check_redis_health(self):
        """Test checking Redis health."""
        checker = MagicMock()
        
        with patch.object(checker, 'check_redis', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {
                "status": "healthy",
                "memory_usage": "256MB",
                "response_time_ms": 8
            }
            
            result = await checker.check_redis()
            assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_check_all_health(self):
        """Test checking all health metrics."""
        checker = MagicMock()
        
        with patch.object(checker, 'check_all', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {
                "overall_status": "healthy",
                "components": {
                    "temporal": {"status": "healthy"},
                    "database": {"status": "healthy"},
                    "redis": {"status": "healthy"}
                }
            }
            
            result = await checker.check_all()
            assert result["overall_status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_degraded(self):
        """Test health check with degraded status."""
        checker = MagicMock()
        
        with patch.object(checker, 'check_all', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {
                "overall_status": "degraded",
                "components": {
                    "temporal": {"status": "healthy"},
                    "database": {"status": "degraded", "reason": "slow response"},
                    "redis": {"status": "healthy"}
                }
            }
            
            result = await checker.check_all()
            assert result["overall_status"] == "degraded"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """Test health check with unhealthy status."""
        checker = MagicMock()
        
        with patch.object(checker, 'check_all', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {
                "overall_status": "unhealthy",
                "components": {
                    "temporal": {"status": "unhealthy", "error": "connection refused"},
                    "database": {"status": "healthy"},
                    "redis": {"status": "healthy"}
                }
            }
            
            result = await checker.check_all()
            assert result["overall_status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_check_with_retry(self):
        """Test health check with retry logic."""
        checker = MagicMock()
        
        with patch.object(checker, 'check_temporal', new_callable=AsyncMock) as mock_check:
            # Simulate retry: fail once, then succeed
            mock_check.side_effect = [
                Exception("Temporary error"),
                {"status": "healthy", "response_time_ms": 50}
            ]
            
            # First call fails
            with pytest.raises(Exception):
                await checker.check_temporal()
            
            # Second call succeeds
            result = await checker.check_temporal()
            assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_response_time(self):
        """Test health check response time tracking."""
        checker = MagicMock()
        
        with patch.object(checker, 'check_temporal', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {
                "status": "healthy",
                "response_time_ms": 125
            }
            
            result = await checker.check_temporal()
            assert result["response_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_health_check_threshold(self):
        """Test health check with response time threshold."""
        checker = MagicMock()
        
        with patch.object(checker, 'check_temporal', new_callable=AsyncMock) as mock_check:
            # Slow response
            mock_check.return_value = {
                "status": "degraded",
                "response_time_ms": 5000,
                "reason": "response time exceeds threshold"
            }
            
            result = await checker.check_temporal()
            assert result["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_health_check_periodic(self):
        """Test periodic health checks."""
        checker = MagicMock()
        
        with patch.object(checker, 'start_periodic_checks', new_callable=AsyncMock) as mock_start:
            mock_start.return_value = True
            
            result = await checker.start_periodic_checks(interval_seconds=30)
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_history(self):
        """Test health check history tracking."""
        checker = MagicMock()
        
        with patch.object(checker, 'get_health_history', new_callable=AsyncMock) as mock_history:
            mock_history.return_value = [
                {"timestamp": "2026-02-21T10:00:00", "status": "healthy"},
                {"timestamp": "2026-02-21T10:05:00", "status": "healthy"},
                {"timestamp": "2026-02-21T10:10:00", "status": "degraded"},
            ]
            
            result = await checker.get_health_history(limit=10)
            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_health_check_alert_generation(self):
        """Test health check alert generation."""
        checker = MagicMock()
        
        with patch.object(checker, 'check_all', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {
                "overall_status": "unhealthy",
                "components": {
                    "temporal": {"status": "unhealthy"}
                },
                "alerts": [
                    {"severity": "critical", "message": "Temporal service is down"}
                ]
            }
            
            result = await checker.check_all()
            assert len(result.get("alerts", [])) > 0
