"""
Real-world usage tests for MCP client configuration.

Tests cover configuration creation, validation, merging, and loading from various sources.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from gearmeshing_ai.agent_core.mcp.client.config import (
    MCPClientConfig, RetryConfig, TransportConfig, MonitoringConfig
)


class TestRetryConfig:
    """Test RetryConfig functionality."""
    
    def test_retry_config_defaults(self):
        """Test default retry configuration."""
        config = RetryConfig()
        
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.backoff_factor == 2.0
        assert config.jitter is True
    
    def test_retry_config_custom_values(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=60.0,
            backoff_factor=3.0,
            jitter=False
        )
        
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 60.0
        assert config.backoff_factor == 3.0
        assert config.jitter is False
    
    def test_get_delay_calculation(self):
        """Test delay calculation with exponential backoff."""
        config = RetryConfig(
            base_delay=1.0,
            backoff_factor=2.0,
            jitter=False
        )
        
        # Verify exponential backoff: delay = base_delay * (backoff_factor ** attempt)
        assert config.get_delay(0) == 1.0  # 1.0 * 2^0 = 1.0
        assert config.get_delay(1) == 2.0  # 1.0 * 2^1 = 2.0
        assert config.get_delay(2) == 4.0  # 1.0 * 2^2 = 4.0
    
    def test_get_delay_respects_max_delay(self):
        """Test that delay respects max_delay limit."""
        config = RetryConfig(
            base_delay=1.0,
            backoff_factor=2.0,
            max_delay=5.0,
            jitter=False
        )
        
        # Delay should be capped at max_delay
        assert config.get_delay(10) == 5.0


class TestTransportConfig:
    """Test TransportConfig functionality."""
    
    def test_transport_config_defaults(self):
        """Test default transport configuration."""
        config = TransportConfig()
        
        assert config.connection_timeout == 30.0
        assert config.read_timeout == 60.0
        assert config.write_timeout == 60.0
    
    def test_transport_config_custom_values(self):
        """Test custom transport configuration."""
        config = TransportConfig(
            connection_timeout=45.0,
            read_timeout=90.0,
            write_timeout=90.0
        )
        
        assert config.connection_timeout == 45.0
        assert config.read_timeout == 90.0
        assert config.write_timeout == 90.0


class TestMonitoringConfig:
    """Test MonitoringConfig functionality."""
    
    def test_monitoring_config_defaults(self):
        """Test default monitoring configuration."""
        config = MonitoringConfig()
        
        assert config.enable_metrics is True
        assert config.enable_health_checking is True
        assert config.metrics_interval == 30.0
        assert config.health_check_interval == 60.0


class TestMCPClientConfig:
    """Test MCPClientConfig functionality."""
    
    def test_mcp_client_config_defaults(self):
        """Test default MCP client configuration."""
        config = MCPClientConfig()
        
        assert config.timeout == 30.0
        assert config.max_concurrent_requests == 10
        assert config.monitoring.enable_health_checking is True
        assert isinstance(config.retry_policy, RetryConfig)
    
    def test_mcp_client_config_custom_values(self):
        """Test custom MCP client configuration."""
        retry_config = RetryConfig(max_retries=5)
        config = MCPClientConfig(
            timeout=60.0,
            max_concurrent_requests=20,
            retry_policy=retry_config
        )
        
        assert config.timeout == 60.0
        assert config.max_concurrent_requests == 20
        assert config.retry_policy.max_retries == 5
    
    def test_mcp_client_config_from_dict(self):
        """Test creating config from dictionary."""
        config_dict = {
            "timeout": 45.0,
            "max_concurrent_requests": 15,
            "retry_policy": {
                "max_retries": 4,
                "base_delay": 1.5
            }
        }
        
        config = MCPClientConfig(**config_dict)
        
        assert config.timeout == 45.0
        assert config.max_concurrent_requests == 15
        assert config.retry_policy.max_retries == 4
    
    def test_mcp_client_config_from_env(self):
        """Test creating config from environment variables."""
        with patch.dict('os.environ', {
            'MCP_CLIENT_TIMEOUT': '60',
            'MCP_CLIENT_MAX_CONCURRENT_REQUESTS': '20'
        }):
            config = MCPClientConfig.from_env()
            
            assert config.timeout == 60.0
            assert config.max_concurrent_requests == 20
    
    def test_mcp_client_config_to_dict(self):
        """Test converting config to dictionary."""
        config = MCPClientConfig(timeout=45.0)
        config_dict = config.model_dump()
        
        assert config_dict['timeout'] == 45.0
        assert 'retry_policy' in config_dict
    
    def test_mcp_client_config_from_file(self):
        """Test loading config from file."""
        config_dict = {
            "timeout": 50.0,
            "max_concurrent_requests": 25
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_dict, f)
            temp_path = f.name
        
        try:
            config = MCPClientConfig.from_file(temp_path)
            assert config.timeout == 50.0
            assert config.max_concurrent_requests == 25
        finally:
            Path(temp_path).unlink()
    
    def test_mcp_client_config_merge(self):
        """Test merging configurations."""
        config1 = MCPClientConfig(timeout=30.0)
        config2 = MCPClientConfig(timeout=60.0, max_concurrent_requests=20)
        
        merged = config1.merge_with(config2)
        
        # config2 should override config1
        assert merged.timeout == 60.0
        assert merged.max_concurrent_requests == 20
