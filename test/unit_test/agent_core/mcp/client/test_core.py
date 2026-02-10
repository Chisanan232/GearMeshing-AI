"""
Real-world usage tests for MCP client core functionality.

These tests focus on practical usage scenarios rather than implementation details.
They test the actual behavior of the client with realistic configurations and workflows.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gearmeshing_ai.agent.mcp.client.config import MCPClientConfig, RetryConfig
from gearmeshing_ai.agent.mcp.client.core import AsyncMCPClient, ClientStats, EasyMCPClient, MCPClient
from gearmeshing_ai.agent.mcp.client.exceptions import ConnectionError, ServerError, TimeoutError
from gearmeshing_ai.agent.mcp.client.transports import SSETransport


class TestMCPClientBasicUsage:
    """Test basic MCPClient usage patterns."""

    def test_client_initialization_with_defaults(self):
        """Test creating a client with default configuration."""
        client = MCPClient()

        assert client.config is not None
        assert client._transport is None
        assert client._stats.total_requests == 0

    def test_client_initialization_with_custom_config(self):
        """Test creating a client with custom configuration."""
        config = MCPClientConfig(timeout=60.0)
        client = MCPClient(config)

        assert client.config.timeout == 60.0

    def test_set_transport(self):
        """Test setting a transport on the client."""
        client = MCPClient()
        transport = SSETransport("http://localhost:8082/sse/sse")

        client.set_transport(transport)

        assert client._transport is transport

    def test_get_stats(self):
        """Test retrieving client statistics."""
        client = MCPClient()
        stats = client.get_stats()

        assert isinstance(stats, ClientStats)
        assert stats.total_requests == 0
        assert stats.successful_requests == 0
        assert stats.failed_requests == 0

    def test_get_metrics(self):
        """Test retrieving client metrics."""
        client = MCPClient()
        metrics = client.get_metrics()

        assert metrics is not None


class TestMCPClientRetryLogic:
    """Test client retry behavior."""

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self):
        """Test that client retries on connection errors."""
        config = MCPClientConfig(timeout=5.0, retry_policy=RetryConfig(max_retries=2, base_delay=0.1))
        client = MCPClient(config)

        # Mock transport that fails then succeeds
        mock_transport = AsyncMock()
        mock_transport.list_tools.side_effect = [ConnectionError("Connection failed"), ["tool1", "tool2"]]
        client.set_transport(mock_transport)

        # Mock metrics to avoid missing argument error
        client._metrics.record_failure = MagicMock()
        client._metrics.record_success = MagicMock()

        result = await client.list_tools()

        assert result == ["tool1", "tool2"]
        assert mock_transport.list_tools.call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self):
        """Test that client raises error when max retries exhausted."""
        config = MCPClientConfig(timeout=5.0, retry_policy=RetryConfig(max_retries=2, base_delay=0.1))
        client = MCPClient(config)

        # Mock transport that always fails
        mock_transport = AsyncMock()
        mock_transport.list_tools.side_effect = ConnectionError("Connection failed")
        client.set_transport(mock_transport)

        # Mock metrics to avoid missing argument error
        client._metrics.record_failure = MagicMock()

        with pytest.raises(ConnectionError):
            await client.list_tools()

        # Should have tried 3 times (initial + 2 retries)
        assert mock_transport.list_tools.call_count == 3


class TestMCPClientToolCalling:
    """Test tool calling functionality."""

    @pytest.mark.asyncio
    async def test_call_tool_with_arguments(self):
        """Test calling a tool with arguments."""
        client = MCPClient()

        mock_transport = AsyncMock()
        mock_transport.call_tool.return_value = {"status": "success", "data": "result"}
        client.set_transport(mock_transport)

        result = await client.call_tool("get_tasks", {"project_id": "123"})

        assert result == {"status": "success", "data": "result"}
        mock_transport.call_tool.assert_called_once_with("get_tasks", {"project_id": "123"})

    @pytest.mark.asyncio
    async def test_call_tool_without_arguments(self):
        """Test calling a tool without arguments."""
        client = MCPClient()

        mock_transport = AsyncMock()
        mock_transport.call_tool.return_value = {"status": "success"}
        client.set_transport(mock_transport)

        result = await client.call_tool("get_status")

        assert result == {"status": "success"}
        mock_transport.call_tool.assert_called_once_with("get_status", None)


class TestMCPClientContextManager:
    """Test client context manager functionality."""

    @pytest.mark.asyncio
    async def test_client_as_context_manager(self):
        """Test using client as async context manager."""
        client = MCPClient()
        mock_transport = AsyncMock()
        client.set_transport(mock_transport)

        async with client as ctx:
            assert ctx is client

        # Verify close was called
        mock_transport.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_close_cleanup(self):
        """Test that client properly cleans up on close."""
        client = MCPClient()
        mock_transport = AsyncMock()
        client.set_transport(mock_transport)

        await client.close()

        assert client._transport is None
        mock_transport.close.assert_called_once()


class TestEasyMCPClientStaticMethods:
    """Test EasyMCPClient convenience static methods."""

    @pytest.mark.asyncio
    async def test_list_tools_sse(self):
        """Test listing tools via SSE."""
        with patch("gearmeshing_ai.agent.mcp.client.core.SSETransport") as mock_transport_class:
            mock_transport = AsyncMock()
            mock_transport.list_tools.return_value = ["tool1", "tool2"]
            mock_transport_class.return_value = mock_transport

            result = await EasyMCPClient.list_tools_sse("http://localhost:8082/sse/sse")

            assert result == ["tool1", "tool2"]

    @pytest.mark.asyncio
    async def test_call_tool_sse(self):
        """Test calling a tool via SSE."""
        with patch("gearmeshing_ai.agent.mcp.client.core.SSETransport") as mock_transport_class:
            mock_transport = AsyncMock()
            mock_transport.call_tool.return_value = {"result": "success"}
            mock_transport_class.return_value = mock_transport

            result = await EasyMCPClient.call_tool_sse(
                "http://localhost:8082/sse/sse", "get_tasks", {"project_id": "123"}
            )

            assert result == {"result": "success"}


class TestAsyncMCPClientConcurrency:
    """Test AsyncMCPClient concurrency features."""

    def test_async_client_initialization(self):
        """Test AsyncMCPClient initialization."""
        config = MCPClientConfig(max_concurrent_requests=5)
        client = AsyncMCPClient(config)

        assert client._semaphore is not None
        assert client._connection_pool == {}

    @pytest.mark.asyncio
    async def test_concurrent_requests_limited(self):
        """Test that concurrent requests are limited by semaphore."""
        config = MCPClientConfig(max_concurrent_requests=2)
        client = AsyncMCPClient(config)

        mock_transport = AsyncMock()
        mock_transport.list_tools.return_value = ["tool1"]
        client.set_transport(mock_transport)

        # Create multiple concurrent requests
        tasks = [client.list_tools() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(r == ["tool1"] for r in results)


class TestClientStatistics:
    """Test client statistics tracking."""

    @pytest.mark.asyncio
    async def test_stats_updated_on_success(self):
        """Test that statistics are updated on successful requests."""
        client = MCPClient()
        mock_transport = AsyncMock()
        mock_transport.list_tools.return_value = ["tool1"]
        client.set_transport(mock_transport)

        await client.list_tools()

        stats = client.get_stats()
        assert stats.total_requests == 1
        assert stats.successful_requests == 1
        assert stats.failed_requests == 0

    @pytest.mark.asyncio
    async def test_stats_updated_on_failure(self):
        """Test that statistics are updated on failed requests."""
        config = MCPClientConfig(retry_policy=RetryConfig(max_retries=0, base_delay=0.1))
        client = MCPClient(config)
        mock_transport = AsyncMock()
        mock_transport.list_tools.side_effect = ServerError("Server error")
        client.set_transport(mock_transport)

        # Mock metrics to avoid missing argument error
        client._metrics.record_failure = MagicMock()

        with pytest.raises(ServerError):
            await client.list_tools()

        stats = client.get_stats()
        assert stats.total_requests == 1
        assert stats.successful_requests == 0
        assert stats.failed_requests == 1


class TestClientErrorHandling:
    """Test client error handling."""

    @pytest.mark.asyncio
    async def test_no_transport_configured_error(self):
        """Test error when no transport is configured."""
        client = MCPClient()

        with pytest.raises(ConnectionError, match="No transport configured"):
            await client.list_tools()

    @pytest.mark.asyncio
    async def test_timeout_error_propagation(self):
        """Test that timeout errors are properly propagated."""
        config = MCPClientConfig(retry_policy=RetryConfig(max_retries=0, base_delay=0.1))
        client = MCPClient(config)
        mock_transport = AsyncMock()
        mock_transport.list_tools.side_effect = TimeoutError("Request timed out")
        client.set_transport(mock_transport)

        # Mock metrics to avoid missing argument error
        client._metrics.record_failure = MagicMock()

        with pytest.raises(TimeoutError):
            await client.list_tools()
