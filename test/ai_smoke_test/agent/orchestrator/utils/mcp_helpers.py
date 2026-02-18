from __future__ import annotations

from typing import Any

import pytest

from gearmeshing_ai.agent.mcp.gateway import GatewayApiClient


class MCPTestHelper:
    """Helper class for MCP integration testing."""

    def __init__(self, mcp_gateway_client: GatewayApiClient):
        self.mcp_gateway_client = mcp_gateway_client

    async def create_test_task(self, title: str, description: str = "", priority: str = "medium") -> str | None:
        """Create a test ClickUp task.

        Note: GatewayApiClient only lists tools, doesn't execute them.
        This method is a placeholder for future MCP client integration.

        Args:
            title: Task title
            description: Task description
            priority: Task priority (low, medium, high)

        Returns:
            Task ID if successful, None otherwise
        """
        # Note: This would need to be implemented with actual MCP client
        # GatewayApiClient only provides tool listing, not execution
        print(f"Would create test task: {title}")
        return "mock_task_id"

    async def delete_test_task(self, task_id: str) -> bool:
        """Delete a test ClickUp task.

        Note: GatewayApiClient only lists tools, doesn't execute them.
        This method is a placeholder for future MCP client integration.

        Args:
            task_id: ID of the task to delete

        Returns:
            True if successful, False otherwise
        """
        # Note: This would need to be implemented with actual MCP client
        print(f"Would delete test task: {task_id}")
        return True

    async def get_task_details(self, task_id: str) -> dict[str, Any] | None:
        """Get details of a ClickUp task.

        Note: GatewayApiClient only lists tools, doesn't execute them.
        This method is a placeholder for future MCP client integration.

        Args:
            task_id: ID of the task

        Returns:
            Task details if successful, None otherwise
        """
        # Note: This would need to be implemented with actual MCP client
        print(f"Would get task details: {task_id}")
        return {"id": task_id, "name": "Mock Task", "status": "open"}

    async def send_test_message(self, channel: str, message: str) -> str | None:
        """Send a test Slack message.

        Note: GatewayApiClient only lists tools, doesn't execute them.
        This method is a placeholder for future MCP client integration.

        Args:
            channel: Slack channel
            message: Message content

        Returns:
            Message ID if successful, None otherwise
        """
        # Note: This would need to be implemented with actual MCP client
        print(f"Would send message to {channel}: {message}")
        return "mock_message_id"

    async def delete_test_message(self, message_id: str) -> bool:
        """Delete a test Slack message.

        Note: GatewayApiClient only lists tools, doesn't execute them.
        This method is a placeholder for future MCP client integration.

        Args:
            message_id: ID of the message to delete

        Returns:
            True if successful, False otherwise
        """
        # Note: This would need to be implemented with actual MCP client
        print(f"Would delete message: {message_id}")
        return True

    async def get_message_details(self, message_id: str) -> dict[str, Any] | None:
        """Get details of a Slack message.

        Note: GatewayApiClient only lists tools, doesn't execute them.
        This method is a placeholder for future MCP client integration.

        Args:
            message_id: ID of the message

        Returns:
            Message details if successful, None otherwise
        """
        # Note: This would need to be implemented with actual MCP client
        print(f"Would get message details: {message_id}")
        return {"id": message_id, "text": "Mock message", "channel": "mock_channel"}

    async def list_available_tools(self) -> list[str]:
        """List available MCP tools.

        Returns:
            List of tool names
        """
        try:
            # Use the correct GatewayApiClient API
            tools_response = self.mcp_gateway_client.admin.tools.list(limit=50)
            return [tool.name for tool in tools_response.items]
        except Exception as e:
            print(f"Warning: Failed to list MCP tools: {e}")
            return []

    async def test_mcp_connectivity(self) -> bool:
        """Test basic MCP connectivity.

        Returns:
            True if MCP gateway is responsive, False otherwise
        """
        try:
            # Try a simple operation to test connectivity
            tools = await self.list_available_tools()
            return len(tools) > 0
        except Exception as e:
            print(f"Warning: MCP connectivity test failed: {e}")
            return False

    async def cleanup_test_resources(self, **resource_ids: str) -> None:
        """Clean up test resources by type.

        Args:
            **resource_ids: Dictionary of resource IDs by type
                (e.g., task_id="123", message_id="456")
        """
        for resource_type, resource_id in resource_ids.items():
            if resource_type == "task_id" and resource_id:
                await self.delete_test_task(resource_id)
            elif resource_type == "message_id" and resource_id:
                await self.delete_test_message(resource_id)
            else:
                print(f"Warning: Unknown resource type {resource_type}")

    def verify_task_structure(self, task_details: dict[str, Any]) -> bool:
        """Verify that task details have expected structure.

        Args:
            task_details: Task details dictionary

        Returns:
            True if structure is valid, False otherwise
        """
        required_fields = ["id", "title", "status", "priority"]
        return all(field in task_details for field in required_fields)

    def verify_message_structure(self, message_details: dict[str, Any]) -> bool:
        """Verify that message details have expected structure.

        Args:
            message_details: Message details dictionary

        Returns:
            True if structure is valid, False otherwise
        """
        required_fields = ["id", "text", "channel", "timestamp"]
        return all(field in message_details for field in required_fields)


@pytest.fixture
def mcp_helper(mcp_gateway_client: GatewayApiClient) -> MCPTestHelper:
    """Provide MCP test helper for smoke tests."""
    return MCPTestHelper(mcp_gateway_client)
