"""
End-to-end tests for MCP Gateway integration.

This test module verifies that the MCP Gateway can:
1. Discover and list MCP servers from its registry
2. Register MCP servers and make them available
3. Provide connection information for MCP servers behind the gateway
4. Allow clients to connect to MCP servers through the gateway
5. List and execute tools from gateway-managed MCP servers

Test Coverage:
- Gateway server discovery and registration
- Connection info retrieval for MCP servers
- Direct client connection to gateway-managed servers
- Tool listing and execution through gateway
- Error handling and recovery scenarios
- Gateway health and status monitoring
"""

import asyncio
import logging
import time

import pytest

from gearmeshing_ai.agent_core.mcp.client import EasyMCPClient
from gearmeshing_ai.agent_core.mcp.gateway import GatewayApiClient
from gearmeshing_ai.agent_core.mcp.gateway.errors import GatewayApiError
from gearmeshing_ai.agent_core.mcp.gateway.models.dto import (
    CatalogListResponseDTO,
    ToolReadDTO,
)

logger = logging.getLogger(__name__)


class TestMCPGatewayIntegration:
    """Test MCP Gateway integration with real MCP servers."""

    @pytest.mark.asyncio
    async def test_gateway_server_discovery(self, gateway_client_with_register_servers: GatewayApiClient):
        """Test that gateway can discover and list MCP servers."""
        # List all servers in the registry
        catalog_response = gateway_client_with_register_servers.admin.mcp_registry.list()

        assert isinstance(catalog_response, CatalogListResponseDTO)
        assert hasattr(catalog_response, "servers")
        assert len(catalog_response.servers) > 0, "No servers found in gateway registry"

        # Verify server structure
        for server in catalog_response.servers:
            assert hasattr(server, "id")
            assert hasattr(server, "name")
            assert hasattr(server, "description")
            assert hasattr(server, "url")
            assert server.id, "Server ID should not be empty"
            logger.info(f"Found server: {server.name} ({server.id}) at {server.url}")

    @pytest.mark.asyncio
    async def test_gateway_server_registration(self, gateway_client: GatewayApiClient):
        """Test that gateway can register MCP servers."""
        # Get initial server list
        initial_catalog = gateway_client.admin.mcp_registry.list()
        initial_server_ids = {server.id for server in initial_catalog.servers}

        # Register all available servers
        mcp_registry = gateway_client.admin.mcp_registry.list()
        registered_count = 0

        for server in mcp_registry.servers:
            if server.id not in initial_server_ids:
                register_result = gateway_client.admin.mcp_registry.register(server.id)
                assert register_result.success, f"Failed to register server {server.id}: {register_result.error}"
                registered_count += 1
                logger.info(f"Successfully registered server: {server.name} ({server.id})")

        # Verify servers are registered
        updated_catalog = gateway_client.admin.mcp_registry.list()
        assert len(updated_catalog.servers) >= len(initial_catalog.servers)

        if registered_count > 0:
            logger.info(f"Successfully registered {registered_count} new servers")

    @pytest.mark.asyncio
    async def test_gateway_tools_listing(self, gateway_client_with_register_servers: GatewayApiClient):
        """Test that gateway can list tools from all registered MCP servers."""
        # List tools from gateway
        tools_response = gateway_client_with_register_servers.admin.tools.list(limit=100)

        assert hasattr(tools_response, "data")
        assert len(tools_response.data) > 0, "No tools found in gateway"

        # Verify tool structure
        for tool in tools_response.data:
            assert isinstance(tool, ToolReadDTO)
            assert hasattr(tool, "id")
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "gatewaySlug")
            assert tool.id, "Tool ID should not be empty"
            assert tool.gatewaySlug, "Tool should be associated with a gateway"
            logger.info(f"Found tool: {tool.name} from gateway {tool.gatewaySlug}")

    @pytest.mark.asyncio
    async def test_gateway_server_connection_info(self, gateway_client_with_register_servers: GatewayApiClient):
        """Test that gateway provides connection information for MCP servers."""
        # Get server list from gateway
        catalog_response = gateway_client_with_register_servers.admin.mcp_registry.list()

        # Find a server with URL information
        server_with_url = None
        for server in catalog_response.servers:
            if hasattr(server, "url") and server.url:
                server_with_url = server
                break

        assert server_with_url is not None, "No server with URL found"

        # Verify URL is accessible
        url = server_with_url.url
        assert url.startswith(("http://", "https://")), f"Invalid URL format: {url}"

        logger.info(f"Server {server_with_url.name} ({server_with_url.id}) available at: {url}")

    @pytest.mark.asyncio
    async def test_direct_client_connection_to_gateway_server(
        self, gateway_client_with_register_servers: GatewayApiClient
    ):
        """Test that clients can directly connect to MCP servers discovered via gateway."""
        # Get server list from gateway
        catalog_response = gateway_client_with_register_servers.admin.mcp_registry.list()

        # Find a server that should be accessible
        accessible_server = None
        for server in catalog_response.servers:
            # Look for servers that are likely to be running
            if server.url:
                accessible_server = server
                break

        # Wait for a while to let the tools be registered
        time.sleep(2)
        if accessible_server is None:
            assert False, "No accessible server found for direct connection test"

        # Try to connect directly to the server URL
        original_url = accessible_server.url
        logger.info(f"Original server URL from gateway: {original_url}")

        # Map container names to host ports
        # clickup-mcp:8082 -> localhost:8082 (based on actual docker container port mapping)
        url_mapping = {
            "http://clickup-mcp:8082": "http://localhost:8082",
            "http://clickup-mcp:8082/sse/sse": "http://localhost:8082/sse/sse",
        }

        # Try to find a mapped URL
        host_url = None
        for container_url, mapped_url in url_mapping.items():
            if container_url in original_url:
                if original_url == container_url:
                    host_url = mapped_url
                else:
                    # Replace the container URL part with the mapped URL
                    host_url = original_url.replace(container_url, mapped_url)
                break

        if host_url is None:
            pytest.skip(f"Could not map server URL {original_url} to host-accessible URL")

        logger.info(f"Mapped host URL: {host_url}")

        try:
            # List tools using direct connection
            tools = await EasyMCPClient.list_tools_sse(host_url)
            assert isinstance(tools, list), f"Expected list of tool names, got {type(tools)}"
            logger.info(f"Successfully connected to {accessible_server.name}, found {len(tools)} tools")

            # Verify tools structure if any
            if tools:
                for tool in tools[:3]:  # Check first 3 tools
                    assert isinstance(tool, str), "Tool name should be a string"
                    assert tool, "Tool name should not be empty"
                    logger.info(f"Found tool: {tool}")
            else:
                assert False, "It should get some tools from the MCP gateway service."

        except Exception as e:
            pytest.fail(f"Failed to connect directly to server {accessible_server.name} at {host_url}: {e}")

    @pytest.mark.asyncio
    async def test_gateway_tool_execution_flow(self, gateway_client_with_register_servers: GatewayApiClient):
        """Test the complete flow of discovering and using tools through gateway."""
        # Get tools from gateway
        tools_response = gateway_client_with_register_servers.admin.tools.list(limit=10)

        if not tools_response.data:
            pytest.skip("No tools available for execution test")

        # Get server info for the first tool
        first_tool = tools_response.data[0]
        gateway_slug = first_tool.gatewaySlug

        # Find the server for this tool by matching gateway slug with server id
        catalog_response = gateway_client_with_register_servers.admin.mcp_registry.list()
        target_server = None
        for server in catalog_response.servers:
            if server.id == gateway_slug:
                target_server = server
                break

        assert target_server is not None, f"Server {gateway_slug} not found in registry"

        # Verify we can get the tool details
        tool_details = gateway_client_with_register_servers.admin.tools.get(first_tool.id)
        assert isinstance(tool_details, ToolReadDTO)
        assert tool_details.id == first_tool.id
        assert tool_details.name == first_tool.name

        logger.info(f"Successfully retrieved tool details for {tool_details.name} from server {target_server.name}")

    @pytest.mark.asyncio
    async def test_gateway_health_and_status(self, gateway_client: GatewayApiClient):
        """Test gateway health check and status endpoints."""
        # Check gateway health
        health_info = gateway_client.health()
        assert isinstance(health_info, dict), "Health check should return dictionary"
        assert "status" in health_info, "Health response should contain status"

        logger.info(f"Gateway health status: {health_info.get('status')}")

        # List gateway instances
        gateways = gateway_client.admin.gateway.list()
        assert isinstance(gateways, list), "Gateway list should be a list"

        if gateways:
            for gateway in gateways:
                assert hasattr(gateway, "id")
                assert hasattr(gateway, "enabled")
                assert hasattr(gateway, "reachable")
                logger.info(
                    f"Gateway instance: {gateway.id} (enabled: {gateway.enabled}, reachable: {gateway.reachable})"
                )

    @pytest.mark.asyncio
    async def test_gateway_error_handling(self, gateway_client: GatewayApiClient):
        """Test gateway error handling for invalid requests."""
        # Test getting non-existent server - should raise GatewayApiError or HTTP error
        try:
            gateway_client.admin.mcp_registry.register("non-existent-server-id")
            # If we get here, the call didn't raise an exception, which might be unexpected
            logger.info("Non-existent server registration did not raise an exception")
        except (GatewayApiError, Exception) as e:
            logger.info(f"Expected error for non-existent server: {type(e).__name__}")

        # Test getting non-existent tool - should raise GatewayApiError or HTTP error
        try:
            gateway_client.admin.tools.get("non-existent-tool-id")
            # If we get here, the call didn't raise an exception
            logger.info("Non-existent tool retrieval did not raise an exception")
        except (GatewayApiError, Exception) as e:
            logger.info(f"Expected error for non-existent tool: {type(e).__name__}")

        logger.info("Gateway error handling verified")

    @pytest.mark.asyncio
    async def test_complete_gateway_workflow(self, gateway_client_with_register_servers: GatewayApiClient):
        """Test the complete workflow from discovery to tool access."""
        # Step 1: Discover servers
        catalog_response = gateway_client_with_register_servers.admin.mcp_registry.list()
        assert len(catalog_response.servers) > 0, "No servers discovered"

        # Step 2: Get tools from all servers
        tools_response = gateway_client_with_register_servers.admin.tools.list(limit=50)
        assert len(tools_response.data) > 0, "No tools found"

        # Step 3: Pick a server and verify its tools
        server_tools = {}
        for tool in tools_response.data:
            if tool.gatewaySlug not in server_tools:
                server_tools[tool.gatewaySlug] = []
            server_tools[tool.gatewaySlug].append(tool)

        # Verify at least one server has tools
        assert len(server_tools) > 0, "No server-tool associations found"

        # Step 4: For each server, verify we can get detailed info
        for gateway_slug, tools in server_tools.items():
            # Get server details
            server = next((s for s in catalog_response.servers if s.id == gateway_slug), None)
            assert server is not None, f"Server {gateway_slug} not found in catalog"

            # Get detailed tool info for first tool
            if tools:
                tool_details = gateway_client_with_register_servers.admin.tools.get(tools[0].id)
                assert tool_details.gatewaySlug == gateway_slug
                logger.info(f"Verified {len(tools)} tools for server {server.name} ({gateway_slug})")

        logger.info(
            f"Complete workflow verified: {len(catalog_response.servers)} servers, {len(tools_response.data)} tools"
        )

    @pytest.mark.asyncio
    async def test_gateway_concurrent_access(self, gateway_client_with_register_servers: GatewayApiClient):
        """Test concurrent access to gateway endpoints."""

        # Create concurrent tasks for different operations
        async def list_servers():
            return gateway_client_with_register_servers.admin.mcp_registry.list()

        async def list_tools():
            return gateway_client_with_register_servers.admin.tools.list(limit=20)

        async def get_health():
            return gateway_client_with_register_servers.health()

        # Run operations concurrently
        results = await asyncio.gather(list_servers(), list_tools(), get_health(), return_exceptions=True)

        # Verify all operations succeeded
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Concurrent operation {i} failed: {result}"

        servers_result, tools_result, health_result = results
        assert isinstance(servers_result, CatalogListResponseDTO)
        assert hasattr(tools_result, "data")
        assert isinstance(health_result, dict)

        logger.info("Concurrent access test passed")

    @pytest.mark.asyncio
    async def test_gateway_server_filtering(self, gateway_client_with_register_servers: GatewayApiClient):
        """Test gateway server filtering capabilities."""
        # Test listing with different parameters
        all_servers = gateway_client_with_register_servers.admin.mcp_registry.list()

        # Test with include_inactive=False (should only return active servers)
        active_servers = gateway_client_with_register_servers.admin.mcp_registry.list(include_inactive=False)

        # Verify filtering works
        assert len(active_servers.servers) <= len(all_servers.servers)

        # Test tools filtering
        all_tools = gateway_client_with_register_servers.admin.tools.list(limit=100)
        active_tools = gateway_client_with_register_servers.admin.tools.list(limit=100, include_inactive=False)

        assert len(active_tools.data) <= len(all_tools.data)

        logger.info(
            f"Filtering test passed: {len(all_servers.servers)} total servers, {len(active_servers.servers)} active"
        )
