"""
Real-world usage tests for MCP client factory functionality.

These tests focus on practical factory usage patterns for creating
MCP clients with various configurations and transport types.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from gearmeshing_ai.agent_core.mcp.client.factory import (
    MCPClientFactory, EasyMCPClientFactory, TransportFactory
)
from gearmeshing_ai.agent_core.mcp.client.config import MCPClientConfig, RetryConfig
from gearmeshing_ai.agent_core.mcp.client.core import MCPClient, EasyMCPClient, AsyncMCPClient
from gearmeshing_ai.agent_core.mcp.client.transports import SSETransport, HTTPTransport, StdioTransport
from gearmeshing_ai.agent_core.mcp.client.exceptions import ConfigurationError


class TestMCPClientFactoryBasic:
    """Test basic MCPClientFactory usage."""
    
    def test_factory_initialization_with_defaults(self):
        """Test creating a factory with default configuration."""
        factory = MCPClientFactory()
        
        assert factory.default_config is not None
        assert isinstance(factory.default_config, MCPClientConfig)
    
    def test_factory_initialization_with_custom_config(self):
        """Test creating a factory with custom default configuration."""
        config = MCPClientConfig(timeout=60.0)
        factory = MCPClientFactory(config)
        
        assert factory.default_config.timeout == 60.0
    
    def test_create_client_from_config(self):
        """Test creating a client from configuration."""
        config = MCPClientConfig(timeout=30.0)
        factory = MCPClientFactory()
        
        client = factory.create_client_from_config(config)
        
        assert isinstance(client, MCPClient)
        assert client.config.timeout == 30.0
    
    def test_create_async_client_from_config(self):
        """Test creating an async client from configuration."""
        config = MCPClientConfig(timeout=30.0)
        factory = MCPClientFactory()
        
        client = factory.create_async_client_from_config(config)
        
        assert isinstance(client, AsyncMCPClient)
        assert client.config.timeout == 30.0


class TestMCPClientFactoryFromDict:
    """Test factory creation from dictionary configurations."""
    
    def test_create_client_from_dict(self):
        """Test creating a client from configuration dictionary."""
        config_dict = {
            "timeout": 45.0,
            "retry_policy": {
                "max_retries": 3,
                "base_delay": 1.0,
                "max_delay": 30.0
            }
        }
        factory = MCPClientFactory()
        
        client = factory.create_client_from_dict(config_dict)
        
        assert isinstance(client, MCPClient)
        assert client.config.timeout == 45.0
        assert client.config.retry_policy.max_retries == 3
    
    def test_create_client_from_dict_invalid(self):
        """Test that invalid configuration dict raises error."""
        config_dict = {
            "timeout": -1.0  # Invalid: negative timeout
        }
        factory = MCPClientFactory()
        
        with pytest.raises(ConfigurationError):
            factory.create_client_from_dict(config_dict)


class TestMCPClientFactoryFromEnvironment:
    """Test factory creation from environment variables."""
    
    def test_create_client_from_env(self):
        """Test creating a client from environment variables."""
        with patch.dict('os.environ', {
            'MCP_CLIENT_TIMEOUT': '60',
            'MCP_CLIENT_MAX_RETRIES': '5'
        }):
            factory = MCPClientFactory()
            client = factory.create_client_from_env()
            
            assert isinstance(client, MCPClient)


class TestMCPClientFactoryFromFile:
    """Test factory creation from configuration files."""
    
    def test_create_client_from_file_json(self):
        """Test creating a client from JSON configuration file."""
        config_dict = {
            "timeout": 50.0,
            "retry_policy": {
                "max_retries": 4,
                "base_delay": 1.5
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_dict, f)
            temp_path = f.name
        
        try:
            factory = MCPClientFactory()
            client = factory.create_client_from_file(temp_path)
            
            assert isinstance(client, MCPClient)
            assert client.config.timeout == 50.0
        finally:
            Path(temp_path).unlink()
    
    def test_create_client_from_file_nonexistent(self):
        """Test error when configuration file doesn't exist."""
        factory = MCPClientFactory()
        
        with pytest.raises(ConfigurationError):
            factory.create_client_from_file("/nonexistent/path/config.json")


class TestMCPClientFactoryTransportCreation:
    """Test transport creation through factory."""
    
    @pytest.mark.asyncio
    async def test_create_sse_client(self):
        """Test creating SSE client through factory."""
        factory = MCPClientFactory()
        
        client = await factory.create_sse_client("http://localhost:8082/sse/sse")
        
        assert isinstance(client, MCPClient)
        assert isinstance(client._transport, SSETransport)
    
    @pytest.mark.asyncio
    async def test_create_http_client(self):
        """Test creating HTTP client through factory."""
        factory = MCPClientFactory()
        
        client = await factory.create_http_client("http://localhost:3000/mcp")
        
        assert isinstance(client, MCPClient)
        assert isinstance(client._transport, HTTPTransport)
    
    @pytest.mark.asyncio
    async def test_create_stdio_client(self):
        """Test creating stdio client through factory."""
        factory = MCPClientFactory()
        
        client = await factory.create_stdio_client("python", ["server.py"])
        
        assert isinstance(client, MCPClient)
        assert isinstance(client._transport, StdioTransport)


class TestMCPClientFactoryAutoConnect:
    """Test factory auto-connect functionality."""
    
    @pytest.mark.asyncio
    async def test_sse_client_auto_connect(self):
        """Test SSE client with auto-connect."""
        factory = MCPClientFactory()
        
        with patch('gearmeshing_ai.agent_core.mcp.client.core.SSETransport') as mock_transport_class:
            mock_transport = AsyncMock()
            mock_transport.session = AsyncMock()
            mock_transport_class.return_value = mock_transport
            
            client = await factory.create_sse_client(
                "http://localhost:8082/sse/sse",
                auto_connect=True
            )
            
            assert isinstance(client, MCPClient)


class TestEasyMCPClientFactory:
    """Test EasyMCPClientFactory convenience methods."""
    
    def test_factory_initialization(self):
        """Test EasyMCPClientFactory initialization."""
        factory = EasyMCPClientFactory()
        
        assert factory is not None
    
    def test_create_sse_client(self):
        """Test creating SSE client through EasyMCPClientFactory."""
        factory = EasyMCPClientFactory()
        
        client = factory.create_sse_client("http://localhost:8082/sse/sse")
        
        # EasyMCPClientFactory returns the EasyMCPClient class
        assert client is EasyMCPClient
    
    def test_create_http_client(self):
        """Test creating HTTP client through EasyMCPClientFactory."""
        factory = EasyMCPClientFactory()
        
        client = factory.create_http_client("http://localhost:3000/mcp")
        
        assert client is EasyMCPClient
    
    def test_create_stdio_client(self):
        """Test creating stdio client through EasyMCPClientFactory."""
        factory = EasyMCPClientFactory()
        
        client = factory.create_stdio_client("python", ["server.py"])
        
        assert client is EasyMCPClient


class TestTransportFactory:
    """Test TransportFactory for direct transport creation."""
    
    def test_factory_initialization(self):
        """Test TransportFactory initialization."""
        factory = TransportFactory()
        
        assert factory is not None
    
    def test_create_sse_transport(self):
        """Test creating SSE transport."""
        factory = TransportFactory()
        
        transport = factory.create_sse_transport("http://localhost:8082/sse/sse")
        
        assert isinstance(transport, SSETransport)
        assert transport.url == "http://localhost:8082/sse/sse"
    
    def test_create_http_transport(self):
        """Test creating HTTP transport."""
        factory = TransportFactory()
        
        transport = factory.create_http_transport("http://localhost:3000/mcp")
        
        assert isinstance(transport, HTTPTransport)
        assert transport.url == "http://localhost:3000/mcp"
    
    def test_create_stdio_transport(self):
        """Test creating stdio transport."""
        factory = TransportFactory()
        
        transport = factory.create_stdio_transport("python", ["server.py"])
        
        assert isinstance(transport, StdioTransport)
        assert transport.command == "python"
        assert transport.args == ["server.py"]


class TestFactoryConfigurationMerging:
    """Test configuration merging in factory."""
    
    def test_factory_merges_default_config(self):
        """Test that factory merges default config with provided config."""
        default_config = MCPClientConfig(timeout=30.0)
        factory = MCPClientFactory(default_config)
        
        custom_config = MCPClientConfig(timeout=60.0)
        client = factory.create_client_from_config(custom_config)
        
        # Custom config should override default
        assert client.config.timeout == 60.0


class TestFactoryErrorHandling:
    """Test factory error handling."""
    
    def test_create_client_from_invalid_config(self):
        """Test error when creating client from invalid config."""
        factory = MCPClientFactory()
        
        # Create invalid config (negative timeout)
        with pytest.raises(Exception):
            config = MCPClientConfig(timeout=-1.0)
    
    def test_create_transport_invalid_type(self):
        """Test error when creating transport with invalid type."""
        factory = TransportFactory()
        
        with pytest.raises(ConfigurationError):
            factory.create_transport_from_dict({
                "type": "invalid",
                "url": "http://localhost:8082/sse/sse"
            })
