"""Unit tests for agent decision node role selection mechanism.

Tests cover:
- Role validation with RoleSelector
- Auto-role selection based on task description
- Role-based agent creation
- Error handling for invalid/missing roles
- Integration with RoleSelector and RoleRegistry
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from gearmeshing_ai.agent.abstraction.factory import AgentFactory
from gearmeshing_ai.agent.models.actions import ActionProposal
from gearmeshing_ai.agent.roles.models.role_definition import RoleDefinition, RoleMetadata
from gearmeshing_ai.agent.roles.registry import RoleRegistry
from gearmeshing_ai.agent.roles.selector import RoleSelector
from gearmeshing_ai.agent.runtime.models.workflow_state import (
    ExecutionContext,
    WorkflowState,
    WorkflowStatus,
)
from gearmeshing_ai.agent.runtime.nodes.agent_decision import agent_decision_node

from ..conftest import merge_state_update


@pytest.fixture
def multi_role_registry():
    """Create a registry with multiple roles for testing."""
    registry = RoleRegistry()
    
    roles_data = {
        "dev": {
            "description": "Software Developer",
            "domain": "software_development",
            "authority": "implementation",
        },
        "qa": {
            "description": "QA Engineer",
            "domain": "quality_assurance",
            "authority": "quality_assessment",
        },
        "sre": {
            "description": "SRE Engineer",
            "domain": "infrastructure",
            "authority": "deployment",
        },
        "dev_lead": {
            "description": "Tech Lead",
            "domain": "technical_leadership",
            "authority": "architecture",
        },
    }
    
    for role_name, role_info in roles_data.items():
        metadata = RoleMetadata(
            domain=role_info["domain"],
            decision_authority=role_info["authority"],
        )
        
        role = RoleDefinition(
            role=role_name,
            description=role_info["description"],
            model_provider="openai",
            model_name="gpt-4",
            customized_model_name=f"{role_name}-gpt4",
            system_prompt=f"You are a {role_name}...",
            metadata=metadata,
        )
        
        registry.register(role)
    
    return registry


@pytest.fixture
def multi_role_selector(multi_role_registry):
    """Create a role selector with multiple roles."""
    return RoleSelector(multi_role_registry)


class TestRoleValidation:
    """Test role validation in agent decision node."""

    @pytest.mark.asyncio
    async def test_valid_role_validation(
        self,
        multi_role_selector: RoleSelector,
    ) -> None:
        """Test validation of a valid role."""
        # Create workflow state with valid role
        context = ExecutionContext(
            task_description="Implement new feature",
            agent_role="dev",
            user_id="user_123",
        )
        state = WorkflowState(
            run_id="run_123",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )
        
        # Setup mock factory
        mock_factory = MagicMock(spec=AgentFactory)
        mock_agent = MagicMock()
        mock_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)
        mock_factory.adapter = MagicMock()
        
        proposal = ActionProposal(
            action="code_implementation",
            reason="Feature requested",
        )
        mock_factory.adapter.run = AsyncMock(return_value=proposal)
        
        # Execute node with role selector
        result = await agent_decision_node(
            state,
            mock_factory,
            role_selector=multi_role_selector,
        )
        
        # Verify
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "PROPOSAL_OBTAINED"
        assert updated_state.current_proposal is not None
        mock_factory.get_or_create_agent.assert_called_once_with("dev")

    @pytest.mark.asyncio
    async def test_invalid_role_raises_error(
        self,
        multi_role_selector: RoleSelector,
    ) -> None:
        """Test that invalid role raises ValueError."""
        # Create workflow state with invalid role
        context = ExecutionContext(
            task_description="Some task",
            agent_role="invalid_role",
            user_id="user_123",
        )
        state = WorkflowState(
            run_id="run_123",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )
        
        # Setup mock factory
        mock_factory = MagicMock(spec=AgentFactory)
        
        # Execute node
        result = await agent_decision_node(
            state,
            mock_factory,
            role_selector=multi_role_selector,
        )
        
        # Verify error
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "FAILED"
        assert "Invalid agent role" in updated_state.status.error
        assert updated_state.status.error is not None

    @pytest.mark.asyncio
    async def test_missing_role_without_auto_select(
        self,
        multi_role_selector: RoleSelector,
    ) -> None:
        """Test that missing role without auto-select raises error."""
        # Create workflow state with no role
        context = ExecutionContext(
            task_description="Some task",
            agent_role="",  # Empty role
            user_id="user_123",
        )
        state = WorkflowState(
            run_id="run_123",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )
        
        # Setup mock factory
        mock_factory = MagicMock(spec=AgentFactory)
        
        # Execute node without auto-select
        result = await agent_decision_node(
            state,
            mock_factory,
            role_selector=multi_role_selector,
            auto_select_role=False,
        )
        
        # Verify error
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "FAILED"
        assert "No agent role specified" in updated_state.status.error


class TestAutoRoleSelection:
    """Test automatic role selection based on task description."""

    @pytest.mark.asyncio
    async def test_auto_select_with_matching_keywords(
        self,
        multi_role_selector: RoleSelector,
    ) -> None:
        """Test auto-selecting role when task has matching keywords."""
        # Create workflow state with task that contains "test" keyword (matches qa)
        context = ExecutionContext(
            task_description="Create test cases and verify functionality",
            agent_role="",  # Empty role
            user_id="user_123",
        )
        state = WorkflowState(
            run_id="run_123",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )
        
        # Setup mock factory
        mock_factory = MagicMock(spec=AgentFactory)
        mock_agent = MagicMock()
        mock_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)
        mock_factory.adapter = MagicMock()
        
        proposal = ActionProposal(
            action="test_creation",
            reason="Testing required",
        )
        mock_factory.adapter.run = AsyncMock(return_value=proposal)
        
        # Execute node with auto-select enabled
        result = await agent_decision_node(
            state,
            mock_factory,
            role_selector=multi_role_selector,
            auto_select_role=True,
        )
        
        # Verify
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "PROPOSAL_OBTAINED"
        # Should auto-select qa role since "test" is a qa keyword
        assert updated_state.context.agent_role == "qa"
        mock_factory.get_or_create_agent.assert_called_once_with("qa")

    @pytest.mark.asyncio
    async def test_auto_select_updates_context_role(
        self,
        multi_role_selector: RoleSelector,
    ) -> None:
        """Test that auto-selected role is stored in context."""
        # Create workflow state with task that contains "implement" keyword (matches dev)
        context = ExecutionContext(
            task_description="Implement the authentication feature",
            agent_role="",  # Empty role
            user_id="user_123",
        )
        state = WorkflowState(
            run_id="run_123",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )
        
        # Setup mock factory
        mock_factory = MagicMock(spec=AgentFactory)
        mock_agent = MagicMock()
        mock_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)
        mock_factory.adapter = MagicMock()
        
        proposal = ActionProposal(
            action="code_implementation",
            reason="Feature requested",
        )
        mock_factory.adapter.run = AsyncMock(return_value=proposal)
        
        # Execute node with auto-select enabled
        result = await agent_decision_node(
            state,
            mock_factory,
            role_selector=multi_role_selector,
            auto_select_role=True,
        )
        
        # Verify
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "PROPOSAL_OBTAINED"
        # Should auto-select dev role since "code" is a dev keyword
        assert updated_state.context.agent_role == "dev"

    @pytest.mark.asyncio
    async def test_auto_select_with_deploy_keyword(
        self,
        multi_role_selector: RoleSelector,
    ) -> None:
        """Test auto-selecting role with deploy keyword."""
        # Create workflow state with task that contains "deploy" keyword (matches devops)
        context = ExecutionContext(
            task_description="Deploy the application to production",
            agent_role="",  # Empty role
            user_id="user_123",
        )
        state = WorkflowState(
            run_id="run_123",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )
        
        # Setup mock factory
        mock_factory = MagicMock(spec=AgentFactory)
        mock_agent = MagicMock()
        mock_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)
        mock_factory.adapter = MagicMock()
        
        proposal = ActionProposal(
            action="deployment",
            reason="Release ready",
        )
        mock_factory.adapter.run = AsyncMock(return_value=proposal)
        
        # Execute node with auto-select enabled
        result = await agent_decision_node(
            state,
            mock_factory,
            role_selector=multi_role_selector,
            auto_select_role=True,
        )
        
        # Verify
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "PROPOSAL_OBTAINED"
        # Should auto-select sre role since "deploy" is a sre keyword
        assert updated_state.context.agent_role == "sre"

    @pytest.mark.asyncio
    async def test_auto_select_fails_with_no_matching_role(
        self,
        multi_role_selector: RoleSelector,
    ) -> None:
        """Test auto-select fails when no role matches task."""
        # Create workflow state with task that doesn't match any role
        context = ExecutionContext(
            task_description="xyz abc def ghi jkl mno pqr stu vwx",
            agent_role="",  # Empty role
            user_id="user_123",
        )
        state = WorkflowState(
            run_id="run_123",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )
        
        # Setup mock factory
        mock_factory = MagicMock(spec=AgentFactory)
        
        # Execute node with auto-select enabled
        result = await agent_decision_node(
            state,
            mock_factory,
            role_selector=multi_role_selector,
            auto_select_role=True,
        )
        
        # Verify error
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "FAILED"
        assert "Could not auto-select role" in updated_state.status.error


class TestRoleBasedAgentCreation:
    """Test agent creation with different roles."""

    @pytest.mark.asyncio
    async def test_agent_creation_with_developer_role(
        self,
        multi_role_selector: RoleSelector,
    ) -> None:
        """Test agent creation with developer role."""
        context = ExecutionContext(
            task_description="Fix bug in authentication",
            agent_role="dev",
            user_id="user_123",
        )
        state = WorkflowState(
            run_id="run_123",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )
        
        # Setup mock factory
        mock_factory = MagicMock(spec=AgentFactory)
        mock_agent = MagicMock()
        mock_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)
        mock_factory.adapter = MagicMock()
        
        proposal = ActionProposal(
            action="bug_fix",
            reason="Bug reported",
        )
        mock_factory.adapter.run = AsyncMock(return_value=proposal)
        
        # Execute node
        result = await agent_decision_node(
            state,
            mock_factory,
            role_selector=multi_role_selector,
        )
        
        # Verify agent was created with correct role
        mock_factory.get_or_create_agent.assert_called_once_with("dev")
        
        # Verify adapter was called with agent and task
        mock_factory.adapter.run.assert_called_once()
        call_args = mock_factory.adapter.run.call_args
        assert call_args[0][0] == mock_agent
        assert call_args[0][1] == "Fix bug in authentication"

    @pytest.mark.asyncio
    async def test_agent_creation_with_qa_role(
        self,
        multi_role_selector: RoleSelector,
    ) -> None:
        """Test agent creation with QA role."""
        context = ExecutionContext(
            task_description="Test the new feature",
            agent_role="qa",
            user_id="user_123",
        )
        state = WorkflowState(
            run_id="run_123",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )
        
        # Setup mock factory
        mock_factory = MagicMock(spec=AgentFactory)
        mock_agent = MagicMock()
        mock_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)
        mock_factory.adapter = MagicMock()
        
        proposal = ActionProposal(
            action="test_execution",
            reason="Testing needed",
        )
        mock_factory.adapter.run = AsyncMock(return_value=proposal)
        
        # Execute node
        result = await agent_decision_node(
            state,
            mock_factory,
            role_selector=multi_role_selector,
        )
        
        # Verify agent was created with QA role
        mock_factory.get_or_create_agent.assert_called_once_with("qa")

    @pytest.mark.asyncio
    async def test_agent_creation_with_devops_role(
        self,
        multi_role_selector: RoleSelector,
    ) -> None:
        """Test agent creation with DevOps role."""
        context = ExecutionContext(
            task_description="Deploy to production",
            agent_role="sre",
            user_id="user_123",
        )
        state = WorkflowState(
            run_id="run_123",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )
        
        # Setup mock factory
        mock_factory = MagicMock(spec=AgentFactory)
        mock_agent = MagicMock()
        mock_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)
        mock_factory.adapter = MagicMock()
        
        proposal = ActionProposal(
            action="deployment",
            reason="Release ready",
        )
        mock_factory.adapter.run = AsyncMock(return_value=proposal)
        
        # Execute node
        result = await agent_decision_node(
            state,
            mock_factory,
            role_selector=multi_role_selector,
        )
        
        # Verify agent was created with SRE role
        mock_factory.get_or_create_agent.assert_called_once_with("sre")


class TestRoleSelectionErrorHandling:
    """Test error handling in role selection."""

    @pytest.mark.asyncio
    async def test_role_selector_not_provided_uses_global(
        self,
    ) -> None:
        """Test that node uses global registry when role_selector not provided."""
        context = ExecutionContext(
            task_description="Some task",
            agent_role="dev",
            user_id="user_123",
        )
        state = WorkflowState(
            run_id="run_123",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )
        
        # Setup mock factory
        mock_factory = MagicMock(spec=AgentFactory)
        mock_agent = MagicMock()
        mock_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)
        mock_factory.adapter = MagicMock()
        
        proposal = ActionProposal(
            action="test_action",
            reason="Test reason",
        )
        mock_factory.adapter.run = AsyncMock(return_value=proposal)
        
        # Execute node without role_selector (will use global registry)
        # This should fail because global registry is empty
        result = await agent_decision_node(
            state,
            mock_factory,
            role_selector=None,
            auto_select_role=False,
        )
        
        # Verify error
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "FAILED"

    @pytest.mark.asyncio
    async def test_role_validation_with_empty_registry(
        self,
    ) -> None:
        """Test role validation with empty registry."""
        # Create empty registry and selector
        empty_registry = RoleRegistry()
        empty_selector = RoleSelector(empty_registry)
        
        context = ExecutionContext(
            task_description="Some task",
            agent_role="dev",
            user_id="user_123",
        )
        state = WorkflowState(
            run_id="run_123",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )
        
        # Setup mock factory
        mock_factory = MagicMock(spec=AgentFactory)
        
        # Execute node
        result = await agent_decision_node(
            state,
            mock_factory,
            role_selector=empty_selector,
        )
        
        # Verify error
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "FAILED"
        assert "Invalid agent role" in updated_state.status.error

    @pytest.mark.asyncio
    async def test_auto_select_with_empty_registry(
        self,
    ) -> None:
        """Test auto-select with empty registry."""
        # Create empty registry and selector
        empty_registry = RoleRegistry()
        empty_selector = RoleSelector(empty_registry)
        
        context = ExecutionContext(
            task_description="Implement new feature",
            agent_role="",
            user_id="user_123",
        )
        state = WorkflowState(
            run_id="run_123",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )
        
        # Setup mock factory
        mock_factory = MagicMock(spec=AgentFactory)
        
        # Execute node with auto-select
        result = await agent_decision_node(
            state,
            mock_factory,
            role_selector=empty_selector,
            auto_select_role=True,
        )
        
        # Verify error
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "FAILED"
        assert "Could not auto-select role" in updated_state.status.error


class TestRoleSelectionIntegration:
    """Integration tests for role selection with proposal generation."""

    @pytest.mark.asyncio
    async def test_role_selection_affects_proposal(
        self,
        multi_role_selector: RoleSelector,
    ) -> None:
        """Test that selected role is included in status message."""
        context = ExecutionContext(
            task_description="Implement feature",
            agent_role="dev",
            user_id="user_123",
        )
        state = WorkflowState(
            run_id="run_123",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )
        
        # Setup mock factory
        mock_factory = MagicMock(spec=AgentFactory)
        mock_agent = MagicMock()
        mock_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)
        mock_factory.adapter = MagicMock()
        
        proposal = ActionProposal(
            action="implementation",
            reason="Feature requested",
        )
        mock_factory.adapter.run = AsyncMock(return_value=proposal)
        
        # Execute node
        result = await agent_decision_node(
            state,
            mock_factory,
            role_selector=multi_role_selector,
        )
        
        # Verify role is in status message
        updated_state = merge_state_update(state, result)
        assert "dev" in updated_state.status.message
        assert "role: dev" in updated_state.status.message

    @pytest.mark.asyncio
    async def test_auto_selected_role_in_context(
        self,
        multi_role_selector: RoleSelector,
    ) -> None:
        """Test that auto-selected role is stored in context."""
        context = ExecutionContext(
            task_description="Create test cases",
            agent_role="",
            user_id="user_123",
        )
        state = WorkflowState(
            run_id="run_123",
            status=WorkflowStatus(state="PENDING"),
            context=context,
        )
        
        # Setup mock factory
        mock_factory = MagicMock(spec=AgentFactory)
        mock_agent = MagicMock()
        mock_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)
        mock_factory.adapter = MagicMock()
        
        proposal = ActionProposal(
            action="test_creation",
            reason="Testing needed",
        )
        mock_factory.adapter.run = AsyncMock(return_value=proposal)
        
        # Execute node with auto-select
        result = await agent_decision_node(
            state,
            mock_factory,
            role_selector=multi_role_selector,
            auto_select_role=True,
        )
        
        # Verify role is stored in context
        updated_state = merge_state_update(state, result)
        assert updated_state.context.agent_role == "qa"

    @pytest.mark.asyncio
    async def test_multiple_roles_different_proposals(
        self,
        multi_role_selector: RoleSelector,
    ) -> None:
        """Test that different roles can generate different proposals."""
        # Test with dev role
        dev_context = ExecutionContext(
            task_description="Implement feature",
            agent_role="dev",
            user_id="user_123",
        )
        dev_state = WorkflowState(
            run_id="run_dev",
            status=WorkflowStatus(state="PENDING"),
            context=dev_context,
        )
        
        # Setup mock factory for developer
        dev_factory = MagicMock(spec=AgentFactory)
        dev_agent = MagicMock()
        dev_factory.get_or_create_agent = AsyncMock(return_value=dev_agent)
        dev_factory.adapter = MagicMock()
        
        dev_proposal = ActionProposal(
            action="code_implementation",
            reason="Feature requested",
        )
        dev_factory.adapter.run = AsyncMock(return_value=dev_proposal)
        
        # Execute for developer
        dev_result = await agent_decision_node(
            dev_state,
            dev_factory,
            role_selector=multi_role_selector,
        )
        
        dev_updated = merge_state_update(dev_state, dev_result)
        assert dev_updated.current_proposal.action == "code_implementation"
        
        # Test with QA role
        qa_context = ExecutionContext(
            task_description="Test feature",
            agent_role="qa",
            user_id="user_123",
        )
        qa_state = WorkflowState(
            run_id="run_qa",
            status=WorkflowStatus(state="PENDING"),
            context=qa_context,
        )
        
        # Setup mock factory for QA
        qa_factory = MagicMock(spec=AgentFactory)
        qa_agent = MagicMock()
        qa_factory.get_or_create_agent = AsyncMock(return_value=qa_agent)
        qa_factory.adapter = MagicMock()
        
        qa_proposal = ActionProposal(
            action="test_execution",
            reason="Testing needed",
        )
        qa_factory.adapter.run = AsyncMock(return_value=qa_proposal)
        
        # Execute for QA
        qa_result = await agent_decision_node(
            qa_state,
            qa_factory,
            role_selector=multi_role_selector,
        )
        
        qa_updated = merge_state_update(qa_state, qa_result)
        assert qa_updated.current_proposal.action == "test_execution"
