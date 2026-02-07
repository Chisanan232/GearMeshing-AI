"""
Real-world usage tests for MCP client transports.

Tests cover SSE, HTTP, and Stdio transport implementations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from gearmeshing_ai.agent_core.mcp.client.transports import (
    SSETransport, HTTPTransport, StdioTransport
)
from gearmeshing_ai.agent_core.mcp.client.exceptions import ConnectionError, TimeoutError


class TestSSETransport:
    """Test SSE transport functionality."""
    
    def test_sse_transport_initialization(self):
        """Test SSE transport initialization."""
        url = "http://localhost:8082/sse/sse"
        transport = SSETransport(url, timeout=30.0)
        
        assert transport.url == url
        assert transport.timeout == 30.0
        assert transport._connected is False
    
    def test_sse_transport_custom_timeout(self):
        """Test SSE transport with custom timeout."""
        transport = SSETransport("http://localhost:8082/sse/sse", timeout=60.0)
        
        assert transport.timeout == 60.0
    
    @pytest.mark.asyncio
    async def test_sse_transport_health_check(self):
        """Test SSE transport health checking."""
        transport = SSETransport("http://localhost:8082/sse/sse")
        
        # Mock list_tools to simulate health check
        transport.list_tools = AsyncMock(return_value=["tool1", "tool2"])
        
        is_healthy = await transport.is_healthy()
        
        assert is_healthy is True
        assert transport._connected is True
    
    @pytest.mark.asyncio
    async def test_sse_transport_close(self):
        """Test SSE transport cleanup."""
        transport = SSETransport("http://localhost:8082/sse/sse")
        transport._connected = True
        
        await transport.close()
        
        assert transport._connected is False


class TestHTTPTransport:
    """Test HTTP transport functionality."""
    
    def test_http_transport_initialization(self):
        """Test HTTP transport initialization."""
        url = "http://localhost:3000/mcp"
        transport = HTTPTransport(url, timeout=30.0)
        
        assert transport.url == url
        assert transport.timeout == 30.0
        assert transport._connected is False
    
    def test_http_transport_custom_timeout(self):
        """Test HTTP transport with custom timeout."""
        transport = HTTPTransport("http://localhost:3000/mcp", timeout=60.0)
        
        assert transport.timeout == 60.0
    
    @pytest.mark.asyncio
    async def test_http_transport_health_check(self):
        """Test HTTP transport health checking."""
        transport = HTTPTransport("http://localhost:3000/mcp")
        
        # Mock list_tools to simulate health check
        transport.list_tools = AsyncMock(return_value=["tool1", "tool2"])
        
        is_healthy = await transport.is_healthy()
        
        assert is_healthy is True
        assert transport._connected is True
    
    @pytest.mark.asyncio
    async def test_http_transport_close(self):
        """Test HTTP transport cleanup."""
        transport = HTTPTransport("http://localhost:3000/mcp")
        transport._connected = True
        
        await transport.close()
        
        assert transport._connected is False


class TestStdioTransport:
    """Test Stdio transport functionality."""
    
    def test_stdio_transport_initialization(self):
        """Test Stdio transport initialization."""
        command = "python"
        args = ["server.py"]
        transport = StdioTransport(command, args, timeout=30.0)
        
        assert transport.command == command
        assert transport.args == args
        assert transport.timeout == 30.0
        assert transport._connected is False
    
    def test_stdio_transport_with_env(self):
        """Test Stdio transport with environment variables."""
        env = {"VAR": "value"}
        transport = StdioTransport("python", ["server.py"], env=env, timeout=30.0)
        
        assert transport.env == env
    
    @pytest.mark.asyncio
    async def test_stdio_transport_health_check(self):
        """Test Stdio transport health checking."""
        transport = StdioTransport("python", ["server.py"])
        
        # Mock list_tools to simulate health check
        transport.list_tools = AsyncMock(return_value=["tool1", "tool2"])
        
        is_healthy = await transport.is_healthy()
        
        assert is_healthy is True
        assert transport._connected is True
    
    @pytest.mark.asyncio
    async def test_stdio_transport_close(self):
        """Test Stdio transport cleanup."""
        transport = StdioTransport("python", ["server.py"])
        transport._connected = True
        
        await transport.close()
        
        assert transport._connected is False


class TestTransportCommonBehavior:
    """Test common behavior across all transports."""
    
    @pytest.mark.asyncio
    async def test_transport_health_check_caching(self):
        """Test that health checks are cached."""
        transport = SSETransport("http://localhost:8082/sse/sse")
        transport.list_tools = AsyncMock(return_value=["tool1"])
        
        # First health check
        result1 = await transport.is_healthy()
        
        # Second health check (should use cache)
        result2 = await transport.is_healthy()
        
        assert result1 is True
        assert result2 is True
        # list_tools should only be called once due to caching
        assert transport.list_tools.call_count == 1
    
    @pytest.mark.asyncio
    async def test_transport_health_check_failure(self):
        """Test health check failure handling."""
        transport = SSETransport("http://localhost:8082/sse/sse")
        transport.list_tools = AsyncMock(side_effect=ConnectionError("Connection failed"))
        
        is_healthy = await transport.is_healthy()
        
        assert is_healthy is False
        assert transport._connected is False
