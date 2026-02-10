"""Unit tests for capability discovery node.

Tests cover capability discovery, filtering, and state updates.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from ..conftest import merge_state_update

from gearmeshing_ai.agent_core.models.actions import MCPToolCatalog, MCPToolInfo
from gearmeshing_ai.agent_core.runtime.capability_registry import CapabilityRegistry
from gearmeshing_ai.agent_core.runtime.nodes.capability_discovery import capability_discovery_node
from gearmeshing_ai.agent_core.runtime.models.workflow_state import (
    ExecutionContext,
    WorkflowState,
    WorkflowStatus,
)


@pytest.fixture
def mock_capability_registry() -> MagicMock:
    """Create a mock CapabilityRegistry."""
    return MagicMock(spec=CapabilityRegistry)


@pytest.fixture
def workflow_state_base() -> WorkflowState:
    """Create a base test workflow state."""
    context = ExecutionContext(
        task_description="Run tests",
        agent_role="developer",
        user_id="user_123",
    )
    return WorkflowState(
        run_id="run_123",
        status=WorkflowStatus(state="PENDING"),
        context=context,
    )


@pytest.fixture
def sample_tools() -> list[MCPToolInfo]:
    """Create sample tools."""
    return [
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


class TestCapabilityDiscoveryNode:
    """Tests for capability discovery node."""

    @pytest.mark.asyncio
    async def test_capability_discovery_node_success(
        self,
        workflow_state_base: WorkflowState,
        mock_capability_registry: MagicMock,
        sample_tools: list[MCPToolInfo],
    ) -> None:
        """Test capability discovery node with successful discovery."""
        # Setup mock
        updated_state = workflow_state_base.model_copy(
            update={
                "available_capabilities": MCPToolCatalog(tools=sample_tools),
                "status": WorkflowStatus(state="CAPABILITY_DISCOVERY_COMPLETE"),
            }
        )
        mock_capability_registry.update_workflow_state = AsyncMock(return_value=updated_state)

        result = await capability_discovery_node(workflow_state_base, mock_capability_registry)

        updated_state = merge_state_update(workflow_state_base, result)
        assert updated_state.status.state == "CAPABILITY_DISCOVERY_COMPLETE"
        assert updated_state.available_capabilities is not None
        assert len(updated_state.available_capabilities.tools) == 2

    @pytest.mark.asyncio
    async def test_capability_discovery_node_no_capabilities(
        self,
        workflow_state_base: WorkflowState,
        mock_capability_registry: MagicMock,
    ) -> None:
        """Test capability discovery node with no capabilities found."""
        # Setup mock to return state without capabilities
        updated_state = workflow_state_base.model_copy(
            update={
                "available_capabilities": None,
                "status": WorkflowStatus(state="CAPABILITY_DISCOVERY_COMPLETE"),
            }
        )
        mock_capability_registry.update_workflow_state = AsyncMock(return_value=updated_state)

        result = await capability_discovery_node(workflow_state_base, mock_capability_registry)

        updated_state = merge_state_update(workflow_state_base, result)
        assert updated_state.status.state == "CAPABILITY_DISCOVERY_COMPLETE"
        assert updated_state.available_capabilities is None

    @pytest.mark.asyncio
    async def test_capability_discovery_node_preserves_run_id(
        self,
        workflow_state_base: WorkflowState,
        mock_capability_registry: MagicMock,
        sample_tools: list[MCPToolInfo],
    ) -> None:
        """Test capability discovery node preserves run_id."""
        updated_state = workflow_state_base.model_copy(
            update={
                "available_capabilities": MCPToolCatalog(tools=sample_tools),
                "status": WorkflowStatus(state="CAPABILITY_DISCOVERY_COMPLETE"),
            }
        )
        mock_capability_registry.update_workflow_state = AsyncMock(return_value=updated_state)

        result = await capability_discovery_node(workflow_state_base, mock_capability_registry)

        updated_state = merge_state_update(workflow_state_base, result)
        assert updated_state.run_id == "run_123"

    @pytest.mark.asyncio
    async def test_capability_discovery_node_preserves_context(
        self,
        workflow_state_base: WorkflowState,
        mock_capability_registry: MagicMock,
        sample_tools: list[MCPToolInfo],
    ) -> None:
        """Test capability discovery node preserves context."""
        updated_state = workflow_state_base.model_copy(
            update={
                "available_capabilities": MCPToolCatalog(tools=sample_tools),
                "status": WorkflowStatus(state="CAPABILITY_DISCOVERY_COMPLETE"),
            }
        )
        mock_capability_registry.update_workflow_state = AsyncMock(return_value=updated_state)

        result = await capability_discovery_node(workflow_state_base, mock_capability_registry)

        updated_state = merge_state_update(workflow_state_base, result)
        assert updated_state.context.agent_role == "developer"
        assert updated_state.context.user_id == "user_123"

    @pytest.mark.asyncio
    async def test_capability_discovery_node_error_handling(
        self,
        workflow_state_base: WorkflowState,
        mock_capability_registry: MagicMock,
    ) -> None:
        """Test capability discovery node error handling."""
        # Setup mock to raise error
        mock_capability_registry.update_workflow_state = AsyncMock(
            side_effect=RuntimeError("Discovery failed")
        )

        result = await capability_discovery_node(workflow_state_base, mock_capability_registry)

        updated_state = merge_state_update(workflow_state_base, result)
        assert updated_state.status.state == "FAILED"
        assert updated_state.status.error is not None
        assert "Discovery failed" in updated_state.status.error

    @pytest.mark.asyncio
    async def test_capability_discovery_node_with_multiple_tools(
        self,
        workflow_state_base: WorkflowState,
        mock_capability_registry: MagicMock,
    ) -> None:
        """Test capability discovery node with multiple tools."""
        tools = [
            MCPToolInfo(
                name=f"tool_{i}",
                description=f"Tool {i}",
                mcp_server="test_server",
                parameters={"param": {"type": "string"}},
            )
            for i in range(10)
        ]
        updated_state = workflow_state_base.model_copy(
            update={
                "available_capabilities": MCPToolCatalog(tools=tools),
                "status": WorkflowStatus(state="CAPABILITY_DISCOVERY_COMPLETE"),
            }
        )
        mock_capability_registry.update_workflow_state = AsyncMock(return_value=updated_state)

        result = await capability_discovery_node(workflow_state_base, mock_capability_registry)

        updated_state = merge_state_update(workflow_state_base, result)
        assert updated_state.available_capabilities is not None
        assert len(updated_state.available_capabilities.tools) == 10

    @pytest.mark.asyncio
    async def test_capability_discovery_node_status_message(
        self,
        workflow_state_base: WorkflowState,
        mock_capability_registry: MagicMock,
        sample_tools: list[MCPToolInfo],
    ) -> None:
        """Test capability discovery node status message."""
        updated_state = workflow_state_base.model_copy(
            update={
                "available_capabilities": MCPToolCatalog(tools=sample_tools),
                "status": WorkflowStatus(
                    state="CAPABILITY_DISCOVERY_COMPLETE",
                    message="Discovered 2 capabilities",
                ),
            }
        )
        mock_capability_registry.update_workflow_state = AsyncMock(return_value=updated_state)

        result = await capability_discovery_node(workflow_state_base, mock_capability_registry)

        updated_state = merge_state_update(workflow_state_base, result)
        assert "capabilities" in updated_state.status.message.lower()
