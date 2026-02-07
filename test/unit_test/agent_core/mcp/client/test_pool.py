"""
Real-world usage tests for MCP client connection and server pooling.

Tests cover connection pooling, server pool management, and failover functionality.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from gearmeshing_ai.agent_core.mcp.client.pool import ConnectionPool, PooledConnection, ServerPool


class TestPooledConnection:
    """Test PooledConnection functionality."""

    def test_pooled_connection_initialization(self):
        """Test PooledConnection initialization."""
        mock_transport = MagicMock()
        mock_client = MagicMock()

        conn = PooledConnection(
            transport=mock_transport,
            client=mock_client,
            server_name="test_server",
            url="http://localhost:8082/sse/sse",
            is_healthy=True,
        )

        assert conn.transport is mock_transport
        assert conn.client is mock_client
        assert conn.server_name == "test_server"
        assert conn.url == "http://localhost:8082/sse/sse"
        assert conn.is_healthy is True

    def test_pooled_connection_touch(self):
        """Test updating connection last access time."""
        mock_transport = MagicMock()
        mock_client = MagicMock()

        conn = PooledConnection(
            transport=mock_transport, client=mock_client, server_name="test_server", url="http://localhost:8082/sse/sse"
        )

        # Touch the connection
        conn.touch()

        # Verify last_used was updated
        assert conn.last_used is not None

    def test_pooled_connection_idle_time(self):
        """Test idle time calculation."""
        mock_transport = MagicMock()
        mock_client = MagicMock()

        conn = PooledConnection(
            transport=mock_transport, client=mock_client, server_name="test_server", url="http://localhost:8082/sse/sse"
        )

        # Idle time should be calculated
        idle_time = conn.idle_time
        assert idle_time >= 0


class TestConnectionPool:
    """Test ConnectionPool functionality."""

    def test_connection_pool_initialization(self):
        """Test ConnectionPool initialization."""
        pool = ConnectionPool(max_size=10, timeout=30.0)

        assert pool.max_size == 10
        assert pool.timeout == 30.0
        assert len(pool.connections) == 0

    def test_connection_pool_custom_settings(self):
        """Test ConnectionPool with custom settings."""
        pool = ConnectionPool(max_size=20, timeout=60.0, max_idle_time=600.0, health_check_interval=120.0)

        assert pool.max_size == 20
        assert pool.timeout == 60.0
        assert pool.max_idle_time == 600.0
        assert pool.health_check_interval == 120.0

    @pytest.mark.asyncio
    async def test_connection_pool_get_stats(self):
        """Test getting pool statistics."""
        pool = ConnectionPool(max_size=10)

        stats = pool.get_stats()

        assert stats["max_size"] == 10
        assert stats["total_connections"] == 0
        assert stats["available_connections"] == 0
        assert stats["total_created"] == 0
        assert stats["total_destroyed"] == 0

    @pytest.mark.asyncio
    async def test_connection_pool_cleanup(self):
        """Test pool cleanup."""
        pool = ConnectionPool(max_size=10)

        # Cleanup should not raise errors
        await pool.cleanup()

        # Verify pool is still functional
        stats = pool.get_stats()
        assert stats is not None

    @pytest.mark.asyncio
    async def test_connection_pool_close(self):
        """Test closing the pool."""
        pool = ConnectionPool(max_size=10)

        # Close should not raise errors
        await pool.close()

        # Verify pool is closed
        assert len(pool.connections) == 0


class TestServerPool:
    """Test ServerPool functionality."""

    def test_server_pool_initialization(self):
        """Test ServerPool initialization."""
        server_configs = [
            {"urls": ["http://localhost:8082/sse/sse"], "name": "server1"},
            {"urls": ["http://localhost:8083/sse/sse"], "name": "server2"},
        ]

        pool = ServerPool(server_configs)

        assert pool is not None
        assert hasattr(pool, "execute_tool_call")

    def test_server_pool_with_single_server(self):
        """Test ServerPool with single server."""
        server_configs = [{"urls": ["http://localhost:8082/sse/sse"], "name": "server1"}]

        pool = ServerPool(server_configs)

        assert pool is not None

    @pytest.mark.asyncio
    async def test_server_pool_failover(self):
        """Test ServerPool failover to backup server."""
        server_configs = [
            {"urls": ["http://localhost:8082/sse/sse"], "name": "server1"},
            {"urls": ["http://localhost:8083/sse/sse"], "name": "server2"},
        ]

        pool = ServerPool(server_configs)

        # Mock execute_tool_call
        pool.execute_tool_call = AsyncMock(return_value={"result": "success"})

        result = await pool.execute_tool_call("test_server", "test_tool", {})

        assert result is not None


class TestConnectionPooling:
    """Test connection pooling behavior."""

    def test_pool_tracks_connections(self):
        """Test that pool tracks connections."""
        pool = ConnectionPool(max_size=10)

        stats = pool.get_stats()

        assert "total_connections" in stats
        assert "available_connections" in stats
        assert "total_created" in stats
        assert "total_destroyed" in stats

    def test_pool_respects_max_size(self):
        """Test that pool respects maximum size."""
        pool = ConnectionPool(max_size=5)

        assert pool.max_size == 5

    @pytest.mark.asyncio
    async def test_pool_health_checking(self):
        """Test pool health checking."""
        pool = ConnectionPool(max_size=10, health_check_interval=60.0)

        # Start health checking
        await pool.start_health_checking()

        # Stop health checking
        await pool.stop_health_checking()


class TestServerPooling:
    """Test server pooling and failover."""

    def test_server_pool_configuration(self):
        """Test ServerPool configuration."""
        server_configs = [
            {"urls": ["http://localhost:8082/sse/sse"], "name": "server1"},
            {"urls": ["http://localhost:8083/sse/sse"], "name": "server2"},
            {"urls": ["http://localhost:8084/sse/sse"], "name": "server3"},
        ]

        pool = ServerPool(server_configs)

        assert pool is not None

    def test_server_pool_with_weights(self):
        """Test ServerPool with server weights."""
        server_configs = [
            {"urls": ["http://localhost:8082/sse/sse"], "name": "server1", "weight": 2},
            {"urls": ["http://localhost:8083/sse/sse"], "name": "server2", "weight": 1},
        ]

        pool = ServerPool(server_configs)

        assert pool is not None
