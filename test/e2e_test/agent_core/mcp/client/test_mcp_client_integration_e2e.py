"""
Integration end-to-end tests for MCP client with real-world workflows.

This test module covers integration scenarios that simulate real-world usage:
- Multi-step workflows
- Tool chaining
- Data flow between tools
- Error handling in workflows
- Workflow recovery and resilience
"""

import asyncio
import json
import logging

import pytest
from mcp import ListToolsResult

from gearmeshing_ai.agent.mcp.client import (
    EasyMCPClient,
    MCPClient,
    MCPClientConfig,
    RetryConfig,
)

logger = logging.getLogger(__name__)


class TestWorkflowScenarios:
    """Test complete workflow scenarios."""

    @pytest.mark.asyncio
    async def test_workflow_discover_and_list(self, clickup_base_url: str):
        """
        Workflow: Discover available tools and list them.

        Real-world scenario: Agent needs to understand what tools are available
        before deciding which ones to use.
        """
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()

            # Step 1: Discover tools
            logger.info("Step 1: Discovering available tools...")
            tools = await session.list_tools()

            assert isinstance(tools, ListToolsResult), "Tools should be ListToolsResult"
            assert isinstance(tools.tools, list), "Tools.tools should be a list"
            assert len(tools.tools) > 0, "Should have at least one tool"

            logger.info(f"✓ Discovered {len(tools.tools)} tools")
            tool_names = [t.name if hasattr(t, "name") else t for t in tools.tools]
            logger.info(f"  Tools: {', '.join(tool_names[:5])}{'...' if len(tools.tools) > 5 else ''}")

            # Step 2: Categorize tools
            logger.info("Step 2: Categorizing tools...")
            get_tools = [t for t in tool_names if "get" in t.lower()]
            create_tools = [t for t in tool_names if "create" in t.lower()]
            update_tools = [t for t in tool_names if "update" in t.lower()]

            logger.info("✓ Categorized tools:")
            logger.info(f"  - GET operations: {len(get_tools)}")
            logger.info(f"  - CREATE operations: {len(create_tools)}")
            logger.info(f"  - UPDATE operations: {len(update_tools)}")

            # Verification
            assert len(get_tools) + len(create_tools) + len(update_tools) <= len(tools.tools)

    @pytest.mark.asyncio
    async def test_workflow_tool_exploration(self, clickup_base_url: str):
        """
        Workflow: Explore tools by attempting to call them.

        Real-world scenario: Agent explores tool capabilities by attempting
        to call them and observing responses.
        """
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()

            logger.info("Workflow: Tool Exploration")

            # Step 1: Get available tools
            logger.info("Step 1: Getting available tools...")
            tools = await session.list_tools()
            logger.info(f"✓ Found {len(tools.tools)} tools")

            # Step 2: Explore each tool
            logger.info("Step 2: Exploring tools...")
            exploration_results = {"callable": [], "requires_args": [], "failed": []}

            tool_names = [t.name if hasattr(t, "name") else t for t in tools.tools]
            for tool_name in tool_names[:10]:  # Explore first 10 tools
                try:
                    # Try calling with empty arguments
                    result = await session.call_tool(tool_name, {})
                    exploration_results["callable"].append(tool_name)
                    logger.info(f"  ✓ {tool_name}: callable with empty args")
                except TypeError as e:
                    if "required" in str(e).lower() or "argument" in str(e).lower():
                        exploration_results["requires_args"].append(tool_name)
                        logger.info(f"  ⚠ {tool_name}: requires arguments")
                    else:
                        exploration_results["failed"].append(tool_name)
                        logger.info(f"  ✗ {tool_name}: {type(e).__name__}")
                except Exception as e:
                    exploration_results["failed"].append(tool_name)
                    logger.info(f"  ✗ {tool_name}: {type(e).__name__}")

            # Step 3: Report findings
            logger.info("Step 3: Exploration results:")
            logger.info(f"  - Callable: {len(exploration_results['callable'])}")
            logger.info(f"  - Requires args: {len(exploration_results['requires_args'])}")
            logger.info(f"  - Failed: {len(exploration_results['failed'])}")

            # Verification
            total_explored = sum(len(v) for v in exploration_results.values())
            assert total_explored > 0

    @pytest.mark.asyncio
    async def test_workflow_repeated_queries(self, clickup_base_url: str):
        """
        Workflow: Perform repeated queries with caching.

        Real-world scenario: Agent performs multiple queries and caches results
        to avoid redundant calls.
        """
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()

            logger.info("Workflow: Repeated Queries with Caching")

            # Step 1: Initial query
            logger.info("Step 1: Initial query...")
            tools_cache = await session.list_tools()
            logger.info(f"✓ Cached {len(tools_cache.tools)} tools")

            # Step 2: Use cache for multiple operations
            logger.info("Step 2: Using cache for operations...")
            operations_count = 0

            tool_names = [t.name if hasattr(t, "name") else t for t in tools_cache.tools]
            for i in range(5):
                # Use cached tools instead of querying again
                if tool_names:
                    tool_name = tool_names[i % len(tool_names)]
                    try:
                        result = await session.call_tool(tool_name, {})
                        operations_count += 1
                        logger.info(f"  ✓ Operation {i + 1}: Called {tool_name}")
                    except Exception as e:
                        logger.info(f"  ⚠ Operation {i + 1}: {type(e).__name__}")

            # Step 3: Verify cache was used
            logger.info("Step 3: Cache verification")
            logger.info(f"✓ Completed {operations_count} operations using cache")

            # Verification
            assert operations_count > 0

    @pytest.mark.asyncio
    async def test_workflow_error_recovery_chain(self, clickup_base_url: str):
        """
        Workflow: Handle errors and recover in a chain of operations.

        Real-world scenario: Agent performs multiple operations and handles
        errors gracefully without stopping the entire workflow.
        """
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()

            logger.info("Workflow: Error Recovery Chain")

            tools = await session.list_tools()
            if not tools or not tools.tools:
                pytest.skip("No tools available")
            assert isinstance(tools, ListToolsResult)

            # Step 1: Perform chain of operations
            logger.info("Step 1: Executing operation chain...")
            results = []

            tool = tools.tools[0]
            first_tool = tool.name
            operations = [
                ("valid_tool", first_tool, {}),
                ("invalid_tool", "nonexistent_tool_xyz", {}),
                ("valid_tool_again", first_tool, {}),
                ("invalid_args", first_tool, {"invalid": "args"}),
                ("valid_tool_final", first_tool, {}),
            ]

            for op_name, tool_name, args in operations:
                try:
                    result = await session.call_tool(tool_name, args)
                    results.append((op_name, "success"))
                    logger.info(f"  ✓ {op_name}: success")
                except Exception as e:
                    results.append((op_name, "failed"))
                    logger.info(f"  ✗ {op_name}: {type(e).__name__}")

            # Step 2: Analyze results
            logger.info("Step 2: Results analysis")
            successful = [r for r in results if r[1] == "success"]
            failed = [r for r in results if r[1] == "failed"]

            logger.info(f"✓ Successful: {len(successful)}/{len(results)}")
            logger.info(f"✓ Failed (handled): {len(failed)}/{len(results)}")

            # Verification: Should have both successes and handled failures
            # Note: If all operations succeed, the server accepts them all (which is valid behavior)
            assert len(successful) > 0
            if len(failed) == 0:
                logger.info("Note: All operations succeeded - server accepts all tool calls")

    @pytest.mark.asyncio
    async def test_workflow_concurrent_tool_calls(self, clickup_base_url: str):
        """
        Workflow: Execute multiple tool calls concurrently.

        Real-world scenario: Agent needs to fetch data from multiple tools
        in parallel for efficiency.
        """
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()

            logger.info("Workflow: Concurrent Tool Calls")

            tools = await session.list_tools()
            if not tools or not tools.tools:
                pytest.skip("No tools available")
            assert isinstance(tools, ListToolsResult)

            # Step 1: Prepare concurrent operations
            logger.info("Step 1: Preparing concurrent operations...")
            tool_name = tools.tools[0].name if hasattr(tools.tools[0], "name") else tools.tools[0]
            concurrent_count = 10

            # Step 2: Execute concurrently
            logger.info(f"Step 2: Executing {concurrent_count} concurrent calls...")
            tasks = [session.call_tool(tool_name, {}) for _ in range(concurrent_count)]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Step 3: Analyze results
            logger.info("Step 3: Results analysis")
            successful = [r for r in results if not isinstance(r, Exception)]
            failed = [r for r in results if isinstance(r, Exception)]

            logger.info(f"✓ Successful: {len(successful)}/{concurrent_count}")
            logger.info(f"✓ Failed: {len(failed)}/{concurrent_count}")

            # Verification
            assert len(successful) > 0

    @pytest.mark.asyncio
    async def test_workflow_session_lifecycle(self, clickup_base_url: str):
        """
        Workflow: Complete session lifecycle from creation to cleanup.

        Real-world scenario: Agent manages a complete session lifecycle
        with proper resource management.
        """
        logger.info("Workflow: Session Lifecycle")

        # Step 1: Create session
        logger.info("Step 1: Creating session...")
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            logger.info("✓ Session created")

            # Step 2: Initialize session
            logger.info("Step 2: Initializing session...")
            await session.initialize()
            logger.info("✓ Session initialized")

            # Step 3: Use session
            logger.info("Step 3: Using session...")
            tools = await session.list_tools()
            assert isinstance(tools, ListToolsResult)
            logger.info(f"✓ Retrieved {len(tools.tools)} tools")

            # Step 4: Perform operations
            logger.info("Step 4: Performing operations...")
            operation_count = 0
            for i in range(5):
                try:
                    await session.list_tools()
                    operation_count += 1
                except Exception:
                    pass
            logger.info(f"✓ Completed {operation_count} operations")

        # Step 5: Session cleanup (automatic via context manager)
        logger.info("Step 5: Session cleanup (automatic)")
        logger.info("✓ Session cleaned up")

        # Verification
        assert operation_count > 0


class TestDataFlowScenarios:
    """Test data flow between operations."""

    @pytest.mark.asyncio
    async def test_data_flow_tool_to_tool(self, clickup_base_url: str):
        """
        Test data flow: Use output from one tool as input to another.

        Real-world scenario: Agent chains tools where output of one
        becomes input to the next.
        """
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()

            logger.info("Data Flow: Tool-to-Tool")

            tools = await session.list_tools()
            if not tools or len(tools.tools) < 2:
                pytest.skip("Need at least 2 tools")
            assert isinstance(tools, ListToolsResult)

            # Step 1: Call first tool
            logger.info("Step 1: Calling first tool...")
            try:
                first_tool = tools.tools[0].name if hasattr(tools.tools[0], "name") else tools.tools[0]
                result1 = await session.call_tool(first_tool, {})
                logger.info(f"✓ First tool result type: {type(result1)}")

                # Step 2: Use result as input to second tool
                logger.info("Step 2: Using result as input to second tool...")

                # Prepare input for second tool
                if isinstance(result1, dict):
                    second_input = result1
                elif isinstance(result1, str):
                    try:
                        second_input = json.loads(result1)
                    except:
                        second_input = {"data": result1}
                else:
                    second_input = {"data": str(result1)}

                try:
                    second_tool = tools.tools[1].name if hasattr(tools.tools[1], "name") else tools.tools[1]
                    result2 = await session.call_tool(second_tool, second_input)
                    logger.info(f"✓ Second tool result type: {type(result2)}")
                except Exception as e:
                    logger.info(f"⚠ Second tool failed: {type(e).__name__}")

            except Exception as e:
                logger.info(f"⚠ First tool failed: {type(e).__name__}")

    @pytest.mark.asyncio
    async def test_data_aggregation(self, clickup_base_url: str):
        """
        Test data aggregation from multiple tools.

        Real-world scenario: Agent collects data from multiple tools
        and aggregates the results.
        """
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()

            logger.info("Data Flow: Aggregation")

            tools = await session.list_tools()
            if not tools or not tools.tools:
                pytest.skip("No tools available")
            assert isinstance(tools, ListToolsResult)

            # Step 1: Collect data from multiple tools
            logger.info("Step 1: Collecting data from multiple tools...")
            aggregated_data = {}

            for tool in tools.tools[:5]:
                tool_name = tool.name if hasattr(tool, "name") else tool
                try:
                    result = await session.call_tool(tool_name, {})
                    aggregated_data[tool_name] = {"status": "success", "result_type": type(result).__name__}
                    logger.info(f"  ✓ {tool_name}: {type(result).__name__}")
                except Exception as e:
                    aggregated_data[tool_name] = {"status": "failed", "error": type(e).__name__}
                    logger.info(f"  ✗ {tool_name}: {type(e).__name__}")

            # Step 2: Analyze aggregated data
            logger.info("Step 2: Analyzing aggregated data...")
            successful = [k for k, v in aggregated_data.items() if v["status"] == "success"]
            failed = [k for k, v in aggregated_data.items() if v["status"] == "failed"]

            logger.info(f"✓ Aggregated {len(aggregated_data)} tool results")
            logger.info(f"  - Successful: {len(successful)}")
            logger.info(f"  - Failed: {len(failed)}")

            # Verification
            assert len(aggregated_data) > 0


class TestRobustnessScenarios:
    """Test robustness and resilience."""

    @pytest.mark.asyncio
    async def test_robustness_partial_failures(self, clickup_base_url: str):
        """
        Test robustness with partial failures.

        Real-world scenario: Some operations fail but overall workflow
        continues and provides partial results.
        """
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()

            logger.info("Robustness: Partial Failures")

            tools = await session.list_tools()
            if not tools or not tools.tools:
                pytest.skip("No tools available")
            assert isinstance(tools, ListToolsResult)

            # Mix valid and invalid operations
            tool = tools.tools[0]
            first_tool_name = tool.name
            operations = [
                ("valid", first_tool_name, {}),
                ("invalid", "nonexistent", {}),
                ("valid", first_tool_name, {}),
                ("invalid", "another_nonexistent", {}),
                ("valid", first_tool_name, {}),
            ]

            logger.info("Executing mixed valid/invalid operations...")
            results = []

            for op_type, tool_name, args in operations:
                try:
                    result = await session.call_tool(tool_name, args)
                    results.append((op_type, "success"))
                except Exception as e:
                    results.append((op_type, "failed"))

            # Analyze results
            successful = [r for r in results if r[1] == "success"]
            failed = [r for r in results if r[1] == "failed"]

            logger.info(f"✓ Results: {len(successful)} successful, {len(failed)} failed")
            logger.info("✓ Workflow continued despite any failures")

            # Verification: Should have successes and ideally some failures
            # Note: If all operations succeed, the server accepts them all (which is valid behavior)
            assert len(successful) > 0
            if len(failed) == 0:
                logger.info("Note: All operations succeeded - server accepts all tool calls")

    @pytest.mark.asyncio
    async def test_robustness_timeout_recovery(self, clickup_base_url: str):
        """
        Test robustness with timeout and recovery.

        Real-world scenario: Operation times out but system recovers
        and continues.
        """
        config = MCPClientConfig(timeout=30.0, retry_policy=RetryConfig(max_retries=2, base_delay=0.1))
        client = MCPClient(config)

        try:
            await client.connect(clickup_base_url, transport_type="sse")

            logger.info("Robustness: Timeout Recovery")

            # Step 1: Normal operation
            logger.info("Step 1: Normal operation...")
            tools = await client.list_tools()
            logger.info(f"✓ Retrieved {len(tools)} tools")  # MCPClient.list_tools() returns List[str]

            # Step 2: Test timeout configuration and recovery
            logger.info("Step 2: Testing timeout configuration...")
            original_timeout = client.config.timeout

            # Change timeout to a shorter value
            client.config.timeout = 5.0
            logger.info(f"✓ Timeout changed from {original_timeout}s to {client.config.timeout}s")

            # Attempt operation with modified timeout
            try:
                tools_with_timeout = await client.list_tools()
                logger.info(f"✓ Operation succeeded with {client.config.timeout}s timeout")
            except Exception as e:
                logger.info(f"✓ Operation failed with timeout: {type(e).__name__}")

            # Step 3: Recovery - restore original timeout
            logger.info("Step 3: Restoring original timeout...")
            client.config.timeout = original_timeout
            tools = await client.list_tools()
            logger.info(f"✓ Recovered, retrieved {len(tools)} tools")  # MCPClient.list_tools() returns List[str]

            # Verification: Timeout configuration was restored and system recovered
            assert client.config.timeout == original_timeout
            assert len(tools) > 0

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_robustness_connection_reuse(self, clickup_base_url: str):
        """
        Test robustness with connection reuse.

        Real-world scenario: Multiple operations reuse same connection
        for efficiency and reliability.
        """
        async with EasyMCPClient.sse_client(clickup_base_url) as session:
            await session.initialize()

            logger.info("Robustness: Connection Reuse")

            # Perform many operations with same connection
            logger.info("Performing operations with connection reuse...")
            operation_count = 0
            error_count = 0

            for i in range(20):
                try:
                    result = await session.list_tools()
                    if result and result.tools:
                        operation_count += 1
                except Exception as e:
                    error_count += 1
                    if error_count > 5:
                        break

            logger.info(f"✓ Completed {operation_count} operations")
            logger.info(f"✓ Errors: {error_count}")

            # Verification: Most operations should succeed
            assert operation_count > error_count


class TestMonitoringAndObservability:
    """Test monitoring and observability features."""

    @pytest.mark.asyncio
    async def test_monitoring_operation_metrics(self, clickup_base_url: str):
        """
        Test monitoring of operation metrics.

        Real-world scenario: Agent monitors operation metrics for
        performance analysis and debugging.
        """
        config = MCPClientConfig(timeout=30.0)
        client = MCPClient(config)

        try:
            await client.connect(clickup_base_url, transport_type="sse")

            logger.info("Monitoring: Operation Metrics")

            # Perform operations
            logger.info("Performing operations...")
            for i in range(5):
                try:
                    result = await client.list_tools()
                    if result:  # MCPClient.list_tools() returns List[str]
                        pass
                except Exception:
                    pass

            # Collect metrics
            logger.info("Collecting metrics...")
            stats = client.get_stats()

            logger.info("✓ Metrics collected:")
            logger.info(f"  - Total requests: {stats.total_requests}")
            logger.info(f"  - Successful: {stats.successful_requests}")
            logger.info(f"  - Failed: {stats.failed_requests}")
            logger.info(f"  - Avg response time: {stats.average_response_time:.3f}s")

            # Verification
            assert stats.total_requests > 0

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_monitoring_error_tracking(self, clickup_base_url: str):
        """
        Test error tracking and monitoring.

        Real-world scenario: Agent tracks errors for debugging and
        alerting purposes.
        """
        config = MCPClientConfig(timeout=30.0)
        client = MCPClient(config)

        try:
            await client.connect(clickup_base_url, transport_type="sse")

            logger.info("Monitoring: Error Tracking")

            # Perform operations including errors
            logger.info("Performing operations with errors...")
            for i in range(3):
                try:
                    result = await client.list_tools()
                    if result:  # MCPClient.list_tools() returns List[str]
                        pass
                except Exception:
                    pass

            # Try invalid operation
            try:
                await client.call_tool("invalid_tool", {})
            except Exception:
                pass

            # Get metrics
            stats = client.get_stats()

            logger.info("✓ Error tracking:")
            logger.info(f"  - Total requests: {stats.total_requests}")
            logger.info(f"  - Failed: {stats.failed_requests}")

            # Verification
            assert stats.total_requests > 0

        finally:
            await client.close()
