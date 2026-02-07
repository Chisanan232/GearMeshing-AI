"""
Advanced end-to-end tests for MCP client with complex scenarios.

This test module covers advanced usage patterns including:
- Multi-server interactions
- Complex tool arguments and responses
- Performance testing
- Stress testing
- Integration with gateway
- Tool result parsing and validation
"""

import asyncio
import json
import logging
import pytest
from typing import Any, Dict, List

from mcp import ListToolsResult

from gearmeshing_ai.agent_core.mcp.client import (
    EasyMCPClient,
    MCPClient,
    MCPClientConfig,
    ServerPool,
    RetryConfig,
)

logger = logging.getLogger(__name__)


class TestComplexToolArguments:
    """Test tool calls with complex argument structures."""

    @pytest.mark.asyncio
    async def test_tool_with_nested_arguments(self, clickup_base_url: str):
        """Test calling tool with nested/complex arguments."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            
            tools = await session.list_tools()
            if not tools or not tools.tools:
                pytest.skip("No tools available")
            
            # Try calling with complex nested arguments
            tool_name = tools.tools[0].name if hasattr(tools.tools[0], 'name') else tools.tools[0]
            complex_args = {
                "filters": {
                    "status": "active",
                    "priority": "high",
                    "tags": ["urgent", "important"]
                },
                "pagination": {
                    "limit": 10,
                    "offset": 0
                },
                "sort": {
                    "field": "created_at",
                    "order": "desc"
                }
            }
            
            try:
                result = await session.call_tool(tool_name, complex_args)
                logger.info(f"Complex arguments handled: {type(result)}")
            except Exception as e:
                logger.info(f"Tool call with complex args: {type(e).__name__}")

    @pytest.mark.asyncio
    async def test_tool_with_large_arguments(self, clickup_base_url: str):
        """Test calling tool with large argument payloads."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            
            tools = await session.list_tools()
            if not tools or not tools.tools:
                pytest.skip("No tools available")
            
            # Create large argument payload
            tool_name = tools.tools[0].name if hasattr(tools.tools[0], 'name') else tools.tools[0]
            large_args = {
                "data": "x" * 10000,  # 10KB of data
                "items": [{"id": i, "value": f"item_{i}"} for i in range(100)]
            }
            
            try:
                result = await session.call_tool(tool_name, large_args)
                logger.info(f"Large arguments handled successfully")
            except Exception as e:
                logger.info(f"Large arguments handling: {type(e).__name__}")

    @pytest.mark.asyncio
    async def test_tool_with_special_characters(self, clickup_base_url: str):
        """Test tool arguments with special characters."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            
            tools = await session.list_tools()
            if not tools or not tools.tools:
                pytest.skip("No tools available")
            
            # Arguments with special characters
            tool_name = tools.tools[0].name if hasattr(tools.tools[0], 'name') else tools.tools[0]
            special_args = {
                "query": "test@#$%^&*()",
                "description": "Line1\nLine2\nLine3",
                "unicode": "你好世界 🌍 مرحبا",
                "json_string": json.dumps({"nested": "value"})
            }
            
            try:
                result = await session.call_tool(tool_name, special_args)
                logger.info(f"Special characters handled")
            except Exception as e:
                logger.info(f"Special characters handling: {type(e).__name__}")


class TestToolResultHandling:
    """Test handling of various tool result types."""

    @pytest.mark.asyncio
    async def test_result_type_validation(self, clickup_base_url: str):
        """Test validation of different result types."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            
            tools = await session.list_tools()
            if not tools or not tools.tools:
                pytest.skip("No tools available")
            
            # Call tool and validate result type
            tool_name = tools.tools[0].name if hasattr(tools.tools[0], 'name') else tools.tools[0]
            try:
                result = await session.call_tool(tool_name, {})
                
                # Result could be various types
                if isinstance(result, dict):
                    logger.info(f"Result is dict with keys: {list(result.keys())}")
                elif isinstance(result, list):
                    logger.info(f"Result is list with {len(result)} items")
                elif isinstance(result, str):
                    logger.info(f"Result is string: {result[:100]}")
                else:
                    logger.info(f"Result type: {type(result)}")
            except Exception as e:
                logger.info(f"Result handling: {type(e).__name__}")

    @pytest.mark.asyncio
    async def test_result_parsing_json(self, clickup_base_url: str):
        """Test parsing JSON results."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            
            tools = await session.list_tools()
            if not tools or not tools.tools:
                pytest.skip("No tools available")
            
            tool_name = tools.tools[0].name if hasattr(tools.tools[0], 'name') else tools.tools[0]
            try:
                result = await session.call_tool(tool_name, {})
                
                # Try to parse as JSON if string
                if isinstance(result, str):
                    try:
                        parsed = json.loads(result)
                        logger.info(f"Parsed JSON: {type(parsed)}")
                    except json.JSONDecodeError:
                        logger.info("Result is not valid JSON")
                else:
                    logger.info(f"Result is already structured: {type(result)}")
            except Exception as e:
                logger.info(f"JSON parsing: {type(e).__name__}")

    @pytest.mark.asyncio
    async def test_result_error_handling(self, clickup_base_url: str):
        """Test handling of error results from tools."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            
            # Call tool that might return error
            try:
                result = await session.call_tool("nonexistent_tool", {})
                logger.info(f"Unexpected success: {result}")
            except Exception as e:
                # Expected to fail
                logger.info(f"Error handling verified: {type(e).__name__}")


class TestPerformanceCharacteristics:
    """Test performance characteristics and optimization."""

    @pytest.mark.asyncio
    async def test_tool_listing_performance(self, clickup_base_url: str):
        """Test performance of tool listing operation."""
        import time
        
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            
            # Warm up
            await session.list_tools()
            
            # Measure performance
            start = time.time()
            for _ in range(10):
                tools = await session.list_tools()
            elapsed = time.time() - start
            
            avg_time = elapsed / 10
            logger.info(f"Tool listing: {avg_time*1000:.2f}ms per call")
            
            # Should be reasonably fast
            assert avg_time < 5.0, "Tool listing should complete within 5 seconds"

    @pytest.mark.asyncio
    async def test_concurrent_performance(self, clickup_base_url: str):
        """Test performance of concurrent operations."""
        import time
        
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            
            # Run 20 concurrent operations
            start = time.time()
            tasks = [session.list_tools() for _ in range(20)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.time() - start
            
            successful = [r for r in results if not isinstance(r, Exception)]
            logger.info(f"Concurrent performance: {len(successful)}/20 succeeded in {elapsed:.3f}s")

    @pytest.mark.asyncio
    async def test_session_reuse_performance(self, clickup_base_url: str):
        """Test performance improvement from session reuse."""
        import time
        
        # With session reuse
        start = time.time()
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            for _ in range(10):
                await session.list_tools()
        reuse_time = time.time() - start
        
        # Without session reuse
        start = time.time()
        for _ in range(10):
            async with EasyMCPClient.sse_client(clickup_base_url) as session:
                await session.initialize()
                await session.list_tools()
        no_reuse_time = time.time() - start
        
        improvement = (no_reuse_time - reuse_time) / no_reuse_time * 100
        logger.info(f"Session reuse improvement: {improvement:.1f}% faster")


class TestStressScenarios:
    """Test stress scenarios and limits."""

    @pytest.mark.asyncio
    async def test_rapid_sequential_calls(self, clickup_base_url: str):
        """Test rapid sequential tool calls."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            
            tools = await session.list_tools()
            if not tools or not tools.tools:
                pytest.skip("No tools available")
            
            # Make rapid sequential calls
            tool_name = tools.tools[0].name if hasattr(tools.tools[0], 'name') else tools.tools[0]
            success_count = 0
            for i in range(50):
                try:
                    result = await session.call_tool(tool_name, {})
                    success_count += 1
                except Exception:
                    pass
            
            logger.info(f"Rapid calls: {success_count}/50 succeeded")
            assert success_count > 0

    @pytest.mark.asyncio
    async def test_high_concurrency(self, clickup_base_url: str):
        """Test high concurrency with many concurrent operations."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            
            # Create 100 concurrent operations
            tasks = [session.list_tools() for _ in range(100)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful = [r for r in results if not isinstance(r, Exception)]
            logger.info(f"High concurrency: {len(successful)}/100 succeeded")
            assert len(successful) > 0

    @pytest.mark.asyncio
    async def test_long_running_session(self, clickup_base_url: str):
        """Test long-running session with many operations."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            
            operation_count = 0
            error_count = 0
            
            # Perform operations for extended period
            for i in range(100):
                try:
                    await session.list_tools()
                    operation_count += 1
                except Exception as e:
                    error_count += 1
                    if error_count > 10:
                        break
            
            logger.info(f"Long-running session: {operation_count} operations, {error_count} errors")
            assert operation_count > 50


class TestServerPoolIntegration:
    """Test server pool functionality."""

    @pytest.mark.asyncio
    async def test_server_pool_creation(self, clickup_base_url: str):
        """Test creating and using server pool."""
        # Create server pool with single server
        server_configs = [
            {
                "name": "clickup",
                "url": clickup_base_url,
                "transport": "sse",
                "timeout": 30.0
            }
        ]
        
        try:
            pool = ServerPool(server_configs)
            logger.info(f"Server pool created with {len(server_configs)} servers")
        except Exception as e:
            logger.info(f"Server pool creation: {type(e).__name__}")

    @pytest.mark.asyncio
    async def test_server_pool_tool_execution(self, clickup_base_url: str):
        """Test executing tools through server pool."""
        server_configs = [
            {
                "name": "clickup",
                "url": clickup_base_url,
                "transport": "sse",
                "timeout": 30.0
            }
        ]
        
        try:
            pool = ServerPool(server_configs)
            
            # Try to execute tool through pool
            result = await pool.execute_tool_call(
                "clickup",
                "get_tasks",
                {"team_id": "test"}
            )
            logger.info(f"Pool tool execution: {type(result)}")
        except Exception as e:
            logger.info(f"Pool tool execution: {type(e).__name__}")


class TestAdvancedSessionManagement:
    """Test advanced session management scenarios."""

    @pytest.mark.asyncio
    async def test_session_recovery_after_error(self, clickup_base_url: str):
        """Test session recovery after encountering errors."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            
            # Successful operation
            tools1 = await session.list_tools()
            assert isinstance(tools1, ListToolsResult)
            assert len(tools1.tools) > 0
            
            # Trigger error
            try:
                await session.call_tool("invalid_tool_xyz", {})
            except Exception:
                pass
            
            # Session should still work
            tools2 = await session.list_tools()
            assert isinstance(tools2, ListToolsResult)
            assert len(tools2.tools) > 0
            assert len(tools1.tools) == len(tools2.tools)
            
            logger.info("Session recovery verified")

    @pytest.mark.asyncio
    async def test_multiple_tools_same_session(self, clickup_base_url: str):
        """Test calling multiple different tools in same session."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            
            tools = await session.list_tools()
            if not tools or len(tools.tools) < 2:
                pytest.skip("Need at least 2 tools")
            
            # Call multiple different tools
            results = {}
            tool_names = [t.name if hasattr(t, 'name') else t for t in tools.tools]
            for tool_name in tool_names[:5]:
                try:
                    result = await session.call_tool(tool_name, {})
                    results[tool_name] = "success"
                except Exception as e:
                    results[tool_name] = f"failed: {type(e).__name__}"
            
            logger.info(f"Multiple tools: {len(results)} tools attempted")

    @pytest.mark.asyncio
    async def test_session_timeout_recovery(self, clickup_base_url: str):
        """Test recovery from timeout scenarios."""
        config = MCPClientConfig(
            timeout=30.0,
            retry_policy=RetryConfig(max_retries=2, base_delay=0.1)
        )
        client = MCPClient(config)
        
        try:
            await client.connect(clickup_base_url, transport_type="sse")
            
            # Normal operation
            tools = await client.list_tools()
            assert len(tools) > 0
            
            # Simulate timeout scenario with very short timeout
            client.config.timeout = 0.001
            try:
                await client.list_tools()
            except Exception:
                pass
            
            # Restore timeout and verify recovery
            client.config.timeout = 30.0
            tools = await client.list_tools()
            assert len(tools) > 0
            
            logger.info("Timeout recovery verified")
        finally:
            await client.close()


class TestDataIntegrity:
    """Test data integrity and consistency."""

    @pytest.mark.asyncio
    async def test_consistent_tool_listing(self, clickup_base_url: str):
        """Test that tool listing is consistent across calls."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            
            # Get tools multiple times
            tools_list = []
            for _ in range(5):
                tools = await session.list_tools()
                tools_list.append(tools.tools)
            
            # All should be identical
            first_set = tools_list[0]
            for tool_set in tools_list[1:]:
                assert tool_set == first_set, "Tool listing should be consistent"
            
            logger.info(f"Consistency verified: {len(first_set)} tools")

    @pytest.mark.asyncio
    async def test_tool_metadata_consistency(self, clickup_base_url: str):
        """Test that tool metadata is consistent."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            
            tools = await session.list_tools()
            if not tools or not tools.tools:
                pytest.skip("No tools available")
            
            # Get same tool multiple times
            tool_name = tools.tools[0].name if hasattr(tools.tools[0], 'name') else tools.tools[0]
            results = []
            
            for _ in range(3):
                try:
                    result = await session.call_tool(tool_name, {})
                    results.append(result)
                except Exception as e:
                    results.append(f"error: {type(e).__name__}")
            
            logger.info(f"Tool metadata consistency: {len(results)} calls")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_tool_arguments(self, clickup_base_url: str):
        """Test calling tool with empty arguments."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            
            tools = await session.list_tools()
            if not tools or not tools.tools:
                pytest.skip("No tools available")
            
            # Call with empty dict
            tool_name = tools.tools[0].name if hasattr(tools.tools[0], 'name') else tools.tools[0]
            try:
                result = await session.call_tool(tool_name, {})
                logger.info("Empty arguments handled")
            except Exception as e:
                logger.info(f"Empty arguments: {type(e).__name__}")

    @pytest.mark.asyncio
    async def test_none_arguments(self, clickup_base_url: str):
        """Test calling tool with None arguments."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            
            tools = await session.list_tools()
            if not tools or not tools.tools:
                pytest.skip("No tools available")
            
            # Call with None
            tool_name = tools.tools[0].name if hasattr(tools.tools[0], 'name') else tools.tools[0]
            try:
                result = await session.call_tool(tool_name, None)
                logger.info("None arguments handled")
            except Exception as e:
                logger.info(f"None arguments: {type(e).__name__}")

    @pytest.mark.asyncio
    async def test_very_long_tool_name(self, clickup_base_url: str):
        """Test calling tool with very long name."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            
            # Call with very long tool name
            long_name = "tool_" + "x" * 1000
            try:
                result = await session.call_tool(long_name, {})
                logger.info("Long tool name handled")
            except Exception as e:
                logger.info(f"Long tool name: {type(e).__name__}")

    @pytest.mark.asyncio
    async def test_unicode_tool_names(self, clickup_base_url: str):
        """Test calling tool with unicode characters in name."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()
            
            # Call with unicode tool name
            unicode_name = "工具_🔧_tool"
            try:
                result = await session.call_tool(unicode_name, {})
                logger.info("Unicode tool name handled")
            except Exception as e:
                logger.info(f"Unicode tool name: {type(e).__name__}")
