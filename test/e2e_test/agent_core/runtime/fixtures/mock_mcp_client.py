"""MockMCPClient fixture for E2E tests - simulates MCP tool execution."""

import asyncio
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from gearmeshing_ai.agent_core.models.actions import ActionProposal


class ToolMetadata(BaseModel):
    """Simple tool metadata model."""

    name: str
    description: str
    input_schema: dict[str, Any]


class MockMCPClient:
    """Mock MCP client for testing tool execution."""

    def __init__(self):
        """Initialize mock MCP client."""
        self.tools = {
            "file_read": self._file_read,
            "file_write": self._file_write,
            "run_command": self._run_command,
            "deploy": self._deploy,
            "deploy_staging": self._deploy_staging,
            "deploy_production": self._deploy_production,
            "run_tests": self._run_tests,
            "delete_file": self._delete_file,
            "backup_database": self._backup_database,
        }
        self.call_history: list[dict[str, Any]] = []
        self.error_on_tool: dict[str, Exception] = {}
        self.response_delay = 0.0

    async def execute_proposed_tool(self, proposal: ActionProposal) -> dict:
        """Execute tool and return result."""
        tool_name = proposal.action

        # Check if tool should error
        if tool_name in self.error_on_tool:
            error = self.error_on_tool[tool_name]
            del self.error_on_tool[tool_name]
            raise error

        # Record call
        self.call_history.append(
            {
                "tool": tool_name,
                "parameters": proposal.parameters,
                "timestamp": datetime.now(),
            }
        )

        # Simulate delay
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)

        # Execute tool
        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")

        return await tool(**proposal.parameters)

    async def _file_read(self, path: str) -> dict:
        """Simulate file read."""
        return {
            "status": "success",
            "path": path,
            "content": f"Mock content of {path}",
            "size": 1024,
        }

    async def _file_write(self, path: str, content: str) -> dict:
        """Simulate file write."""
        return {
            "status": "success",
            "path": path,
            "bytes_written": len(content),
        }

    async def _run_command(self, command: str) -> dict:
        """Simulate command execution."""
        return {
            "status": "success",
            "command": command,
            "stdout": f"Output of: {command}",
            "stderr": "",
            "return_code": 0,
        }

    async def _deploy(self, environment: str) -> dict:
        """Simulate deployment."""
        return {
            "status": "success",
            "environment": environment,
            "deployment_id": "deploy_123",
            "timestamp": datetime.now().isoformat(),
        }

    async def _deploy_staging(self, environment: str = "staging") -> dict:
        """Simulate staging deployment."""
        return {
            "status": "success",
            "environment": "staging",
            "deployment_id": "deploy_staging_123",
            "timestamp": datetime.now().isoformat(),
        }

    async def _deploy_production(self, environment: str = "production") -> dict:
        """Simulate production deployment."""
        return {
            "status": "success",
            "environment": "production",
            "deployment_id": "deploy_prod_123",
            "timestamp": datetime.now().isoformat(),
        }

    async def _run_tests(self) -> dict:
        """Simulate test execution."""
        return {
            "status": "success",
            "tests_passed": 42,
            "tests_failed": 0,
            "coverage": 95.5,
        }

    async def _delete_file(self, path: str) -> dict:
        """Simulate file deletion."""
        return {
            "status": "success",
            "path": path,
            "deleted": True,
        }

    async def _backup_database(self, database: str) -> dict:
        """Simulate database backup."""
        return {
            "status": "success",
            "database": database,
            "backup_id": "backup_123",
            "size_mb": 512,
            "timestamp": datetime.now().isoformat(),
        }

    async def discover_tools_for_agent(self, agent_role: str) -> list[ToolMetadata]:
        """Discover available tools for agent role."""
        # Return all available tools as ToolMetadata
        tools = [
            ToolMetadata(
                name="file_read",
                description="Read file contents",
                input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
            ),
            ToolMetadata(
                name="file_write",
                description="Write to file",
                input_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                },
            ),
            ToolMetadata(
                name="run_command",
                description="Run shell command",
                input_schema={"type": "object", "properties": {"command": {"type": "string"}}},
            ),
            ToolMetadata(
                name="deploy",
                description="Deploy application",
                input_schema={"type": "object", "properties": {"environment": {"type": "string"}}},
            ),
            ToolMetadata(
                name="deploy_staging",
                description="Deploy to staging",
                input_schema={"type": "object", "properties": {"environment": {"type": "string"}}},
            ),
            ToolMetadata(
                name="deploy_production",
                description="Deploy to production",
                input_schema={"type": "object", "properties": {"environment": {"type": "string"}}},
            ),
            ToolMetadata(
                name="run_tests",
                description="Run test suite",
                input_schema={"type": "object", "properties": {}},
            ),
            ToolMetadata(
                name="delete_file",
                description="Delete file",
                input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
            ),
            ToolMetadata(
                name="backup_database",
                description="Backup database",
                input_schema={"type": "object", "properties": {"database": {"type": "string"}}},
            ),
        ]
        return tools

    def set_tool_error(self, tool_name: str, error: Exception) -> None:
        """Configure tool to raise error on next call."""
        self.error_on_tool[tool_name] = error

    def set_response_delay(self, delay: float) -> None:
        """Set delay before tool response."""
        self.response_delay = delay

    def get_call_history(self, tool_name: str | None = None) -> list[dict[str, Any]]:
        """Get call history for tool."""
        if tool_name:
            return [c for c in self.call_history if c["tool"] == tool_name]
        return self.call_history

    def clear_call_history(self) -> None:
        """Clear call history."""
        self.call_history = []

    def assert_tool_called(self, tool_name: str, times: int = 1) -> None:
        """Assert tool was called specific number of times."""
        calls = self.get_call_history(tool_name)
        assert len(calls) == times, f"Expected {tool_name} called {times} times, got {len(calls)}"

    def assert_tool_called_with(self, tool_name: str, **parameters) -> None:
        """Assert tool was called with specific parameters."""
        calls = self.get_call_history(tool_name)
        for call in calls:
            if call["parameters"] == parameters:
                return
        raise AssertionError(f"{tool_name} not called with {parameters}")

    def assert_tool_not_called(self, tool_name: str) -> None:
        """Assert tool was not called."""
        calls = self.get_call_history(tool_name)
        assert len(calls) == 0, f"Expected {tool_name} not called, but was called {len(calls)} times"
