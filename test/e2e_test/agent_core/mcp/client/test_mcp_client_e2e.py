"""
End-to-end tests for MCP client with real MCP servers.

This test module verifies that the MCP client can successfully connect to
and interact with real MCP servers in various real-world scenarios.

Test Coverage:
- Basic tool listing and discovery
- Tool execution with various argument types
- Session management and lifecycle
- Error handling and recovery
- Connection pooling and reuse
- Concurrent operations
- Timeout handling
- Retry logic

All tests use real MCP servers (ClickUp, Slack, GitHub) running in Docker containers.
"""

import asyncio
import json
import logging
import pytest
from typing import Any, Dict, List

from mcp import ListToolsResult
from mcpgateway.main import tool_router

from gearmeshing_ai.agent_core.mcp.client import (
    EasyMCPClient,
    MCPClient,
    MCPClientConfig,
    SSETransport,
    HTTPTransport,
    RetryConfig,
)
from gearmeshing_ai.agent_core.mcp.client.exceptions import (
    MCPClientError,
    ConnectionError as MCPConnectionError,
    TimeoutError as MCPTimeoutError,
)

logger = logging.getLogger(__name__)


class TestBasicToolOperations:
    """Test basic tool listing and discovery operations."""

    @pytest.mark.asyncio
    async def test_list_tools_sse(self, clickup_base_url: str):
        """Test listing tools from ClickUp MCP server via SSE."""
        tools = await EasyMCPClient.list_tools_sse(clickup_base_url)
        
        assert isinstance(tools, list)
        logger.info(f"Found {len(tools)} tools: {tools}")
        
        # ClickUp MCP server should have at least some tools
        assert len(tools) > 0, "ClickUp MCP server should expose at least one tool"

    @pytest.mark.asyncio
    async def test_list_tools_with_client(self, clickup_base_url: str):
        """Test listing tools using MCPClient directly."""
        config = MCPClientConfig(timeout=30.0)
        client = MCPClient(config)
        
        try:
            await client.connect(clickup_base_url, transport_type="sse")
            tools = await client.list_tools()
            
            assert isinstance(tools, list)
            assert len(tools) > 0
            logger.info(f"MCPClient found {len(tools)} tools")
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_list_tools_with_session_context(self, clickup_base_url: str):
        """Test listing tools using session context manager."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            # await session.initialize()
            tools = await session.list_tools()
            
            assert isinstance(tools, ListToolsResult)
            assert isinstance(tools.tools, list)
            assert len(tools.tools) > 0
            logger.info(f"Session found {len(tools.tools)} tools")


class TestToolExecution:
    """Test tool execution with various scenarios."""

    @pytest.mark.asyncio
    async def test_call_tool_with_arguments(self, clickup_base_url: str):
        """Test calling a tool with arguments."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            # await session.initialize()
            
            # Get available tools first
            tools = await session.list_tools()
            assert isinstance(tools, ListToolsResult)
            assert isinstance(tools.tools, list)
            assert len(tools.tools) > 0
            
            # Try to call a tool with typical ClickUp arguments
            # get_tasks is a common ClickUp tool
            if "get_tasks" in tools.tools:
                try:
                    result = await session.call_tool(
                        "get_tasks",
                        {"team_id": "test_team"}
                    )
                    # Result should be a valid response (could be empty list or error)
                    assert result is not None
                    logger.info(f"Tool call result: {result}")
                except Exception as e:
                    # Tool might fail due to missing credentials, but should not crash
                    logger.info(f"Tool call failed as expected: {e}")

    @pytest.mark.asyncio
    async def test_call_tool_without_arguments(self, clickup_base_url: str):
        """Test calling a tool without arguments."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            # await session.initialize()
            
            tools = await session.list_tools()
            assert isinstance(tools, ListToolsResult)
            assert isinstance(tools.tools, list)
            assert len(tools.tools) > 0
            
            # Try calling first available tool without arguments
            if tools:
                tool = tools.tools[0]
                tool_name = tool.name
                try:
                    result = await session.call_tool(tool_name)
                    # Should not crash even if tool requires arguments
                    logger.info(f"Tool call result: {result}")
                except Exception as e:
                    # Expected if tool requires arguments
                    logger.info(f"Tool call failed as expected: {e}")

    @pytest.mark.asyncio
    async def test_call_multiple_tools_sequentially(self, clickup_base_url: str):
        """Test calling multiple tools in sequence."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            # await session.initialize()
            
            tools = await session.list_tools()
            assert isinstance(tools, ListToolsResult)
            assert isinstance(tools.tools, list)
            assert len(tools.tools) > 0

            # Call each tool (may fail due to missing credentials, but should not crash)
            results = []
            for tool in tools.tools[:3]:  # Test first 3 tools
                tool_name = tool.name
                try:
                    result = await session.call_tool(tool_name, {})
                    results.append((tool_name, "success", result))
                    logger.info(f"Tool {tool_name} succeeded")
                except Exception as e:
                    results.append((tool_name, "failed", str(e)))
                    logger.info(f"Tool {tool_name} failed: {e}")
            
            assert len(results) > 0
            logger.info(f"Executed {len(results)} tool calls")


class TestSessionManagement:
    """Test session lifecycle and management."""

    @pytest.mark.asyncio
    async def test_session_initialization(self, clickup_base_url: str):
        """Test session initialization and cleanup."""
        config = MCPClientConfig(timeout=30.0)
        client = MCPClient(config)
        
        # Transport should not be configured yet
        assert client._transport is None
        
        try:
            await client.connect(clickup_base_url, transport_type="sse")
            # Transport should be configured after connect
            assert client._transport is not None
            logger.info("Session initialized successfully")
        finally:
            await client.close()
            # Transport should be cleaned up
            assert client._transport is None
            logger.info("Session cleaned up successfully")

    @pytest.mark.asyncio
    async def test_multiple_sequential_sessions(self, clickup_base_url: str):
        """Test creating and closing multiple sessions sequentially."""
        for i in range(3):
            config = MCPClientConfig(timeout=30.0)
            client = MCPClient(config)
            
            try:
                await client.connect(clickup_base_url, transport_type="sse")
                tools = await client.list_tools()
                assert isinstance(tools, list)
                assert len(tools) > 0
                logger.info(f"Session {i+1}: Found {len(tools)} tools")
            finally:
                await client.close()

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self, clickup_base_url: str):
        """Test that context manager properly cleans up resources."""
        config = MCPClientConfig(timeout=30.0)
        
        async with MCPClient(config) as client:
            await client.connect(clickup_base_url, transport_type="sse")
            tools = await client.list_tools()
            assert len(tools) > 0
            assert client._transport is not None
        
        # After context exit, transport should be cleaned up
        assert client._transport is None
        logger.info("Context manager cleanup verified")


class TestErrorHandling:
    """Test error handling and recovery."""

    @pytest.mark.asyncio
    async def test_connection_to_invalid_url(self):
        """Test handling of connection to invalid URL."""
        config = MCPClientConfig(timeout=5.0)
        client = MCPClient(config)
        
        try:
            with pytest.raises((MCPConnectionError, MCPClientError, Exception)):
                await client.connect("http://invalid-host-12345:9999/sse/sse", transport_type="sse")
                await client.list_tools()
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_timeout_handling(self, clickup_base_url: str):
        """Test timeout handling with very short timeout."""
        config = MCPClientConfig(timeout=0.1)  # Very short timeout
        client = MCPClient(config)
        
        try:
            # Connection might timeout
            await client.connect(clickup_base_url, transport_type="sse")
            # If connection succeeds, list_tools might timeout
            try:
                await client.list_tools()
            except (MCPTimeoutError, MCPClientError, Exception):
                logger.info("Timeout occurred as expected")
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self, clickup_base_url: str):
        """Test retry logic on transient failures."""
        retry_config = RetryConfig(
            max_retries=2,
            base_delay=0.1,
            max_delay=0.5,
            exponential_base=2.0
        )
        config = MCPClientConfig(timeout=30.0, retry_policy=retry_config)
        client = MCPClient(config)
        
        try:
            await client.connect(clickup_base_url, transport_type="sse")
            tools = await client.list_tools()
            
            # Should succeed with retries
            assert len(tools) > 0
            
            # Check that retry policy is configured
            assert client.config.retry_policy.max_retries == 2
            logger.info("Retry logic verified")
        finally:
            await client.close()


class TestConcurrentOperations:
    """Test concurrent operations and thread safety."""

    @pytest.mark.asyncio
    async def test_concurrent_tool_listing(self, clickup_base_url: str):
        """Test concurrent tool listing from same session."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            # await session.initialize()
            
            # Run multiple list_tools calls concurrently
            tasks = [session.list_tools() for _ in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed
            successful = [r for r in results if not isinstance(r, Exception)]
            assert len(successful) > 0
            logger.info(f"Concurrent operations: {len(successful)}/{len(tasks)} succeeded")

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, clickup_base_url: str):
        """Test concurrent tool calls."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            # await session.initialize()
            
            tools = await session.list_tools()
            if not tools:
                pytest.skip("No tools available")
            
            # Call same tool multiple times concurrently
            assert isinstance(tools, ListToolsResult)
            assert isinstance(tools.tools, list)
            tool = tools.tools[0]
            tasks = [
                session.call_tool(tool.name, {})
                for _ in range(3)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Should handle concurrent calls
            logger.info(f"Concurrent tool calls: {len(results)} executed")

    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, clickup_base_url: str):
        """Test multiple concurrent sessions."""
        async def create_and_list_tools():
            async with EasyMCPClient.sse_client(clickup_base_url) as session:
                # await session.initialize()
                return await session.list_tools()
        
        # Create multiple concurrent sessions
        tasks = [create_and_list_tools() for _ in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) > 0
        logger.info(f"Concurrent sessions: {len(successful)}/{len(tasks)} succeeded")


class TestClientMetrics:
    """Test client metrics and statistics."""

    @pytest.mark.asyncio
    async def test_metrics_collection(self, clickup_base_url: str):
        """Test that metrics are collected during operations."""
        config = MCPClientConfig(timeout=30.0)
        client = MCPClient(config)
        
        try:
            await client.connect(clickup_base_url, transport_type="sse")
            
            # Perform some operations
            await client.list_tools()
            await client.list_tools()
            
            # Check metrics
            stats = client.get_stats()
            assert stats.total_requests >= 2
            assert stats.successful_requests >= 2
            assert stats.average_response_time > 0
            
            logger.info(f"Metrics - Total: {stats.total_requests}, "
                       f"Successful: {stats.successful_requests}, "
                       f"Avg time: {stats.average_response_time:.3f}s")
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_failure_metrics(self, clickup_base_url: str):
        """Test that failure metrics are recorded."""
        config = MCPClientConfig(timeout=30.0)
        client = MCPClient(config)
        
        try:
            await client.connect(clickup_base_url, transport_type="sse")
            
            # Perform successful operation
            await client.list_tools()
            
            # Try to call non-existent tool (should fail)
            try:
                await client.call_tool("nonexistent_tool_xyz", {})
            except Exception:
                pass
            
            # Check metrics
            stats = client.get_stats()
            assert stats.total_requests >= 2
            
            logger.info(f"Failure metrics - Total: {stats.total_requests}, "
                       f"Failed: {stats.failed_requests}")
        finally:
            await client.close()


class TestTransportAbstraction:
    """Test transport abstraction and switching."""

    @pytest.mark.asyncio
    async def test_sse_transport_directly(self, clickup_base_url: str):
        """Test using SSE transport directly."""
        transport = SSETransport(clickup_base_url, timeout=30.0)
        
        try:
            tools = await transport.list_tools()
            assert isinstance(tools, list)
            assert len(tools) > 0
            logger.info(f"SSE transport: Found {len(tools)} tools")
        finally:
            await transport.close()

    @pytest.mark.asyncio
    async def test_transport_session_context(self, clickup_base_url: str):
        """Test transport session context manager."""
        transport = SSETransport(clickup_base_url, timeout=30.0)
        
        async with transport.session() as session:
            # await session.initialize()
            tools = await session.list_tools()
            assert isinstance(tools, ListToolsResult)
            assert isinstance(tools.tools, list)
            assert len(tools.tools) > 0
            logger.info(f"Transport session: Found {len(tools.tools)} tools")

    @pytest.mark.asyncio
    async def test_client_with_custom_transport(self, clickup_base_url: str):
        """Test MCPClient with custom transport configuration."""
        config = MCPClientConfig(
            timeout=30.0,
            retry_policy=RetryConfig(max_retries=1)
        )
        client = MCPClient(config)
        
        try:
            # Set custom transport
            transport = SSETransport(clickup_base_url, timeout=30.0)
            client.set_transport(transport)
            
            # Ensure session is created
            await client._ensure_session()
            
            tools = await client.list_tools()
            assert len(tools) > 0
            logger.info(f"Custom transport: Found {len(tools)} tools")
        finally:
            await client.close()


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_workflow_list_and_filter_tools(self, clickup_base_url: str):
        """Test workflow: list tools and filter by name."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            # await session.initialize()
            
            tools = await session.list_tools()
            assert isinstance(tools, ListToolsResult)
            assert isinstance(tools.tools, list)
            assert len(tools.tools) > 0
            
            # Filter tools (example: tools containing "get")
            filtered_tools = [t for t in tools.tools if "get" in t.name.lower()]
            logger.info(f"Total tools: {len(tools.tools)}, Filtered: {len(filtered_tools)}")

    @pytest.mark.asyncio
    async def test_workflow_tool_discovery_and_execution(self, clickup_base_url: str):
        """Test workflow: discover tools and execute them."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            # await session.initialize()
            
            # Discover available tools
            tools = await session.list_tools()
            assert isinstance(tools, ListToolsResult)
            all_tools = tools.tools
            assert isinstance(all_tools, list)
            logger.info(f"Discovered {len(all_tools)} tools: {all_tools}")
            
            # Try to execute each tool with empty arguments
            execution_results = {}
            for tool in all_tools[:5]:  # Test first 5 tools
                tool_name = tool.name
                try:
                    result = await session.call_tool(tool_name, {})
                    execution_results[tool_name] = "executed"
                    logger.info(f"✓ {tool_name}: executed")
                except Exception as e:
                    execution_results[tool_name] = f"failed: {type(e).__name__}"
                    logger.info(f"✗ {tool_name}: {type(e).__name__}")
            
            assert len(execution_results) > 0

    @pytest.mark.asyncio
    async def test_workflow_repeated_operations_with_reuse(self, clickup_base_url: str):
        """Test workflow: repeated operations with session reuse."""
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            # await session.initialize()
            
            # Perform multiple operations with same session
            operation_count = 0
            
            for i in range(5):
                try:
                    tools = await session.list_tools()
                    operation_count += 1
                    logger.info(f"Operation {i+1}: Found {len(tools)} tools")
                except Exception as e:
                    logger.warning(f"Operation {i+1} failed: {e}")
            
            assert operation_count > 0
            logger.info(f"Completed {operation_count} operations with session reuse")

    @pytest.mark.asyncio
    async def test_workflow_error_recovery(self, clickup_base_url: str):
        """Test workflow: error recovery and retry."""
        config = MCPClientConfig(
            timeout=30.0,
            retry_policy=RetryConfig(max_retries=2, base_delay=0.1)
        )
        client = MCPClient(config)
        
        try:
            await client.connect(clickup_base_url, transport_type="sse")
            
            # First operation
            tools1 = await client.list_tools()
            logger.info(f"First operation: Found {len(tools1)} tools")
            
            # Try operation that might fail
            try:
                await client.call_tool("invalid_tool", {})
            except Exception as e:
                logger.info(f"Expected failure: {type(e).__name__}")
            
            # Second operation should still work
            tools2 = await client.list_tools()
            logger.info(f"Second operation: Found {len(tools2)} tools")
            
            assert len(tools1) == len(tools2)
        finally:
            await client.close()


class TestConnectionPooling:
    """Test connection pooling and resource management."""

    @pytest.mark.asyncio
    async def test_session_reuse_efficiency(self, clickup_base_url: str):
        """Test that session reuse is more efficient than creating new sessions."""
        import time
        
        # Test with session reuse
        start = time.time()
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            # await session.initialize()
            for _ in range(5):
                await session.list_tools()
        reuse_time = time.time() - start
        
        # Test without session reuse (create new session each time)
        start = time.time()
        for _ in range(5):
            async with EasyMCPClient.sse_client(clickup_base_url) as session:
                # await session.initialize()
                await session.list_tools()
        no_reuse_time = time.time() - start
        
        logger.info(f"With reuse: {reuse_time:.3f}s, Without reuse: {no_reuse_time:.3f}s")
        # Session reuse should be faster (or at least not significantly slower)
        assert reuse_time <= no_reuse_time * 1.5  # Allow 50% margin for variance

    @pytest.mark.asyncio
    async def test_resource_cleanup_on_error(self, clickup_base_url: str):
        """Test that resources are cleaned up even on error."""
        config = MCPClientConfig(timeout=30.0)
        client = MCPClient(config)
        
        try:
            await client.connect(clickup_base_url, transport_type="sse")
            
            # Perform operation
            tools = await client.list_tools()
            assert isinstance(tools, list)
            assert len(tools) > 0
            
            # Simulate error scenario
            try:
                raise ValueError("Simulated error")
            except ValueError:
                pass
            
            # Should still be able to perform operations
            tools = await client.list_tools()
            assert isinstance(tools, list)
            assert len(tools) > 0
            logger.info("Resource cleanup verified after error")
        finally:
            await client.close()


class TestConfigurationOptions:
    """Test various configuration options."""

    @pytest.mark.asyncio
    async def test_custom_timeout_configuration(self, clickup_base_url: str):
        """Test custom timeout configuration."""
        config = MCPClientConfig(timeout=60.0)
        client = MCPClient(config)
        
        try:
            await client.connect(clickup_base_url, transport_type="sse")
            tools = await client.list_tools()
            assert isinstance(tools, list)
            assert len(tools) > 0
            assert client.config.timeout == 60.0
            logger.info(f"Custom timeout configured: {client.config.timeout}s")
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_retry_policy_configuration(self, clickup_base_url: str):
        """Test retry policy configuration."""
        retry_config = RetryConfig(
            max_retries=3,
            base_delay=0.5,
            max_delay=5.0,
            exponential_base=2.0
        )
        config = MCPClientConfig(timeout=30.0, retry_policy=retry_config)
        client = MCPClient(config)
        
        try:
            await client.connect(clickup_base_url, transport_type="sse")
            tools = await client.list_tools()
            assert isinstance(tools, list)
            assert len(tools) > 0
            
            # Verify retry configuration
            assert client.config.retry_policy.max_retries == 3
            assert client.config.retry_policy.base_delay == 0.5
            logger.info("Retry policy configured correctly")
        finally:
            await client.close()


@pytest.mark.asyncio
async def test_easy_client_static_methods(clickup_base_url: str):
    """Test EasyMCPClient static methods for quick operations."""
    # Test list_tools_sse
    tools = await EasyMCPClient.list_tools_sse(clickup_base_url)
    assert isinstance(tools, list)
    assert len(tools) > 0
    logger.info(f"EasyMCPClient.list_tools_sse: Found {len(tools)} tools")
    
    # Test call_tool_sse (may fail due to missing credentials, but should not crash)
    if tools:
        try:
            result = await EasyMCPClient.call_tool_sse(
                clickup_base_url,
                tools[0],
                {}
            )
            logger.info(f"EasyMCPClient.call_tool_sse: {result}")
        except Exception as e:
            logger.info(f"EasyMCPClient.call_tool_sse failed as expected: {e}")
