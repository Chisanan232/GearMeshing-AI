"""Unit tests for Capability Registry.

Tests cover capability discovery, filtering, caching, and context-aware selection.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from gearmeshing_ai.agent.abstraction.mcp import MCPClientAbstraction
from gearmeshing_ai.agent.models.actions import MCPToolCatalog, MCPToolInfo
from gearmeshing_ai.agent.runtime.capability_registry import CapabilityRegistry
from gearmeshing_ai.agent.runtime.models.workflow_state import (
    ExecutionContext,
    WorkflowState,
    WorkflowStatus,
)


@pytest.fixture
def mock_mcp_client() -> MagicMock:
    """Create a mock MCP client."""
    return MagicMock(spec=MCPClientAbstraction)


@pytest.fixture
def sample_tool_catalog() -> MCPToolCatalog:
    """Create a sample tool catalog."""
    tools = [
        MCPToolInfo(
            name="run_tests",
            description="Run unit tests",
            mcp_server="test_server",
            parameters={"test_type": {"type": "string"}},
        ),
        MCPToolInfo(
            name="deploy",
            description="Deploy application",
            mcp_server="deploy_server",
            parameters={"environment": {"type": "string"}},
        ),
        MCPToolInfo(
            name="read_file",
            description="Read file content",
            mcp_server="file_server",
            parameters={"path": {"type": "string"}},
        ),
    ]
    return MCPToolCatalog(tools=tools)


@pytest.fixture
def execution_context() -> ExecutionContext:
    """Create a sample execution context."""
    return ExecutionContext(
        task_description="Run tests",
        agent_role="developer",
        user_id="user_123",
    )


@pytest.fixture
def workflow_state(execution_context: ExecutionContext) -> WorkflowState:
    """Create a sample workflow state."""
    return WorkflowState(
        run_id="run_123",
        status=WorkflowStatus(state="PENDING"),
        context=execution_context,
    )


class TestCapabilityRegistry:
    """Tests for CapabilityRegistry."""

    def test_capability_registry_initialization(
        self,
        mock_mcp_client: MagicMock,
    ) -> None:
        """Test CapabilityRegistry initialization."""
        registry = CapabilityRegistry(mock_mcp_client)

        assert registry.mcp_client is mock_mcp_client
        assert registry._catalog_cache is None
        assert len(registry._filtered_capabilities) == 0

    @pytest.mark.asyncio
    async def test_discover_capabilities(
        self,
        mock_mcp_client: MagicMock,
        sample_tool_catalog: MCPToolCatalog,
    ) -> None:
        """Test capability discovery."""
        mock_mcp_client.discover_tools_for_agent = AsyncMock(return_value=sample_tool_catalog)
        registry = CapabilityRegistry(mock_mcp_client)

        catalog = await registry.discover_capabilities()

        assert catalog is not None
        assert len(catalog.tools) == 3
        assert catalog.tools[0].name == "run_tests"

    @pytest.mark.asyncio
    async def test_discover_capabilities_caching(
        self,
        mock_mcp_client: MagicMock,
        sample_tool_catalog: MCPToolCatalog,
    ) -> None:
        """Test that discovered capabilities are cached."""
        mock_mcp_client.discover_tools_for_agent = AsyncMock(return_value=sample_tool_catalog)
        registry = CapabilityRegistry(mock_mcp_client)

        # First discovery
        catalog1 = await registry.discover_capabilities()
        assert len(catalog1.tools) == 3

        # Second discovery should use cache
        catalog2 = await registry.get_all_capabilities()
        assert catalog2 is catalog1

        # Verify discover was called only once
        assert mock_mcp_client.discover_tools_for_agent.call_count == 1

    @pytest.mark.asyncio
    async def test_get_all_capabilities_uses_cache(
        self,
        mock_mcp_client: MagicMock,
        sample_tool_catalog: MCPToolCatalog,
    ) -> None:
        """Test that get_all_capabilities uses cached catalog."""
        mock_mcp_client.discover_tools_for_agent = AsyncMock(return_value=sample_tool_catalog)
        registry = CapabilityRegistry(mock_mcp_client)

        # Populate cache
        await registry.discover_capabilities()

        # Get all should use cache
        catalog = await registry.get_all_capabilities()

        assert catalog is not None
        assert len(catalog.tools) == 3

    @pytest.mark.asyncio
    async def test_filter_capabilities(
        self,
        mock_mcp_client: MagicMock,
        sample_tool_catalog: MCPToolCatalog,
        execution_context: ExecutionContext,
    ) -> None:
        """Test capability filtering."""
        mock_mcp_client.discover_tools_for_agent = AsyncMock(return_value=sample_tool_catalog)
        registry = CapabilityRegistry(mock_mcp_client)

        filtered = await registry.filter_capabilities(execution_context)

        assert filtered is not None
        assert len(filtered) == 3

    @pytest.mark.asyncio
    async def test_filter_capabilities_with_custom_filter(
        self,
        mock_mcp_client: MagicMock,
        sample_tool_catalog: MCPToolCatalog,
        execution_context: ExecutionContext,
    ) -> None:
        """Test capability filtering with custom filter."""
        mock_mcp_client.discover_tools_for_agent = AsyncMock(return_value=sample_tool_catalog)
        registry = CapabilityRegistry(mock_mcp_client)

        custom_filter = {"excluded_tools": ["deploy"]}
        filtered = await registry.filter_capabilities(execution_context, custom_filter)

        assert len(filtered) == 2
        assert all(tool.name != "deploy" for tool in filtered)

    @pytest.mark.asyncio
    async def test_filter_capabilities_with_tags(
        self,
        mock_mcp_client: MagicMock,
        execution_context: ExecutionContext,
    ) -> None:
        """Test capability filtering with required tags."""
        # Create tools with tags
        tools = [
            MCPToolInfo(
                name="run_tests",
                description="Run unit tests",
                mcp_server="test_server",
                parameters={"test_type": {"type": "string"}},
            ),
            MCPToolInfo(
                name="deploy",
                description="Deploy application",
                mcp_server="deploy_server",
                parameters={"environment": {"type": "string"}},
            ),
        ]
        catalog = MCPToolCatalog(tools=tools)
        mock_mcp_client.discover_tools_for_agent = AsyncMock(return_value=catalog)
        registry = CapabilityRegistry(mock_mcp_client)

        # Without tags in tools, all tools should be returned
        custom_filter = {"required_tags": ["testing"]}
        filtered = await registry.filter_capabilities(execution_context, custom_filter)

        # Since tools don't have tags, they won't match the required_tags filter
        assert len(filtered) == 0

    @pytest.mark.asyncio
    async def test_update_workflow_state(
        self,
        mock_mcp_client: MagicMock,
        sample_tool_catalog: MCPToolCatalog,
        workflow_state: WorkflowState,
    ) -> None:
        """Test updating workflow state with capabilities."""
        mock_mcp_client.discover_tools_for_agent = AsyncMock(return_value=sample_tool_catalog)
        registry = CapabilityRegistry(mock_mcp_client)

        updated_state = await registry.update_workflow_state(workflow_state)

        assert updated_state.available_capabilities is not None
        assert len(updated_state.available_capabilities.tools) == 3

    @pytest.mark.asyncio
    async def test_update_workflow_state_preserves_other_fields(
        self,
        mock_mcp_client: MagicMock,
        sample_tool_catalog: MCPToolCatalog,
        workflow_state: WorkflowState,
    ) -> None:
        """Test that updating workflow state preserves other fields."""
        mock_mcp_client.discover_tools_for_agent = AsyncMock(return_value=sample_tool_catalog)
        registry = CapabilityRegistry(mock_mcp_client)

        updated_state = await registry.update_workflow_state(workflow_state)

        assert updated_state.run_id == workflow_state.run_id
        assert updated_state.context == workflow_state.context
        assert updated_state.status == workflow_state.status

    def test_clear_cache(
        self,
        mock_mcp_client: MagicMock,
        sample_tool_catalog: MCPToolCatalog,
    ) -> None:
        """Test clearing the capability cache."""
        registry = CapabilityRegistry(mock_mcp_client)
        registry._catalog_cache = sample_tool_catalog
        registry._filtered_capabilities["developer"] = sample_tool_catalog.tools

        registry.clear_cache()

        assert registry._catalog_cache is None
        assert len(registry._filtered_capabilities) == 0

    def test_get_capability_by_name(
        self,
        mock_mcp_client: MagicMock,
        sample_tool_catalog: MCPToolCatalog,
    ) -> None:
        """Test getting a capability by name."""
        registry = CapabilityRegistry(mock_mcp_client)
        registry._catalog_cache = sample_tool_catalog

        tool = registry.get_capability_by_name("run_tests")

        assert tool is not None
        assert tool.name == "run_tests"
        assert tool.description == "Run unit tests"

    def test_get_capability_by_name_not_found(
        self,
        mock_mcp_client: MagicMock,
        sample_tool_catalog: MCPToolCatalog,
    ) -> None:
        """Test getting a non-existent capability by name."""
        registry = CapabilityRegistry(mock_mcp_client)
        registry._catalog_cache = sample_tool_catalog

        tool = registry.get_capability_by_name("nonexistent")

        assert tool is None

    def test_get_capability_by_name_without_cache(
        self,
        mock_mcp_client: MagicMock,
    ) -> None:
        """Test getting a capability by name without cached catalog."""
        registry = CapabilityRegistry(mock_mcp_client)

        tool = registry.get_capability_by_name("run_tests")

        assert tool is None

    @pytest.mark.asyncio
    async def test_discover_capabilities_error_handling(
        self,
        mock_mcp_client: MagicMock,
    ) -> None:
        """Test error handling in capability discovery."""
        mock_mcp_client.discover_tools_for_agent = AsyncMock(side_effect=RuntimeError("Discovery failed"))
        registry = CapabilityRegistry(mock_mcp_client)

        with pytest.raises(RuntimeError):
            await registry.discover_capabilities()

    @pytest.mark.asyncio
    async def test_filter_capabilities_error_handling(
        self,
        mock_mcp_client: MagicMock,
        execution_context: ExecutionContext,
    ) -> None:
        """Test error handling in capability filtering."""
        mock_mcp_client.discover_tools_for_agent = AsyncMock(side_effect=RuntimeError("Discovery failed"))
        registry = CapabilityRegistry(mock_mcp_client)

        filtered = await registry.filter_capabilities(execution_context)

        assert filtered == []

    @pytest.mark.asyncio
    async def test_update_workflow_state_error_handling(
        self,
        mock_mcp_client: MagicMock,
        workflow_state: WorkflowState,
    ) -> None:
        """Test error handling in workflow state update."""
        mock_mcp_client.discover_tools_for_agent = AsyncMock(side_effect=RuntimeError("Discovery failed"))
        registry = CapabilityRegistry(mock_mcp_client)

        updated_state = await registry.update_workflow_state(workflow_state)

        # Should return original state on error (with empty catalog from filter_capabilities)
        # The filter_capabilities returns empty list on error, which creates empty catalog
        assert updated_state.run_id == workflow_state.run_id
