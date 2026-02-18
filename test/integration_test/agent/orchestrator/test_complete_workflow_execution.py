"""Integration tests for complete AI agent workflow execution with mocked AI models.

These tests run the entire workflow end-to-end but mock AI model calls to:
1. Test complete workflow orchestration without AI API dependencies
2. Verify WorkflowState validation and transitions work correctly
3. Ensure orchestrator service properly handles workflow lifecycle
4. Test LangGraph state management and node execution flow
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from gearmeshing_ai.agent.orchestrator.service import OrchestratorService
from gearmeshing_ai.agent.orchestrator.models import WorkflowResult, WorkflowStatus
from gearmeshing_ai.agent.runtime.models import (
    ExecutionContext,
    WorkflowState,
    WorkflowStatus as RuntimeWorkflowStatus,
)
from gearmeshing_ai.agent.runtime.capability_registry import CapabilityRegistry
from gearmeshing_ai.agent.models.actions import ActionProposal, MCPToolCatalog, MCPToolInfo


class MockAIModel:
    """Mock AI model that returns predictable responses for testing."""
    
    def __init__(self, response_content: str = "Mock AI response"):
        self.response_content = response_content
    
    async def ainvoke(self, messages: list[HumanMessage], **kwargs: Any) -> AIMessage:
        """Mock async invocation that returns a predictable AI response."""
        return AIMessage(content=self.response_content)
    
    def invoke(self, messages: list[HumanMessage], **kwargs: Any) -> AIMessage:
        """Mock sync invocation that returns a predictable AI response."""
        return AIMessage(content=self.response_content)


class MockMCPClient:
    """Mock MCP client for testing workflow execution."""
    
    def __init__(self):
        self.available_tools = MCPToolCatalog(
            tools=[
                MCPToolInfo(
                    name="file_write",
                    description="Write content to a file",
                    mcp_server="test_server",
                    parameters={"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}
                ),
                MCPToolInfo(
                    name="file_read", 
                    description="Read content from a file",
                    mcp_server="test_server",
                    parameters={"type": "object", "properties": {"path": {"type": "string"}}}
                )
            ]
        )
    
    async def list_tools(self) -> MCPToolCatalog:
        """Return mock tools catalog."""
        return self.available_tools
    
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Mock tool execution."""
        if name == "file_write":
            return {"success": True, "message": f"File written to {arguments.get('path')}"}
        elif name == "file_read":
            return {"content": "Mock file content"}
        else:
            return {"error": f"Unknown tool: {name}"}


class TestCompleteWorkflowExecution:
    """Test complete workflow execution with mocked AI models."""
    
    @pytest.fixture
    def mock_ai_model(self) -> MockAIModel:
        """Provide a mock AI model for testing."""
        return MockAIModel("Create a simple Python script that prints 'Hello, World!'")
    
    @pytest.fixture
    def mock_mcp_client(self) -> MockMCPClient:
        """Provide a mock MCP client for testing."""
        return MockMCPClient()
    
    @pytest.fixture
    def orchestrator_service(self) -> OrchestratorService:
        """Provide orchestrator service for testing."""
        return OrchestratorService()
    
    async def test_complete_workflow_execution_with_mocked_ai(
        self,
        orchestrator_service: OrchestratorService,
        mock_ai_model: MockAIModel,
        mock_mcp_client: MockMCPClient,
    ) -> None:
        """Test complete workflow execution from start to finish with mocked AI."""
        
        # Mock all the dependencies that would normally require real services
        with patch('gearmeshing_ai.agent.abstraction.factory.AgentFactory') as mock_factory, \
             patch('gearmeshing_ai.agent.abstraction.mcp.MCPClientAbstraction') as mock_mcp_abstraction, \
             patch('gearmeshing_ai.agent.runtime.CapabilityRegistry') as mock_registry, \
             patch('gearmeshing_ai.agent.runtime.PolicyEngine') as mock_policy_engine, \
             patch('gearmeshing_ai.agent.runtime.ApprovalManager') as mock_approval_manager:
            
            # Configure mocks to return our mock objects
            mock_agent_factory_instance = AsyncMock()
            mock_agent_factory_instance.create_agent.return_value = mock_ai_model
            mock_factory.return_value = mock_agent_factory_instance
            
            mock_mcp_abstraction_instance = AsyncMock()
            mock_mcp_abstraction_instance.list_tools.return_value = mock_mcp_client.available_tools
            mock_mcp_abstraction.return_value = mock_mcp_abstraction_instance
            
            mock_registry_instance = AsyncMock()
            mock_registry_instance.get_capabilities.return_value = mock_mcp_client.available_tools
            mock_registry.return_value = mock_registry_instance
            
            mock_policy_engine_instance = AsyncMock()
            mock_policy_engine_instance.validate_policy.return_value = {"approved": True}
            mock_policy_engine.return_value = mock_policy_engine_instance
            
            mock_approval_manager_instance = AsyncMock()
            mock_approval_manager_instance.check_approval_required.return_value = False
            mock_approval_manager.return_value = mock_approval_manager_instance
            
            # Run the complete workflow
            result = await orchestrator_service.run_workflow(
                task_description="Create a Python script that prints 'Hello, World!'",
                agent_role="dev",
                user_id="test_user",
                timeout_seconds=60
            )
            
            # Verify workflow completed successfully
            assert result.status == WorkflowStatus.SUCCESS
            assert result.run_id is not None
            assert result.error is None
            assert result.output is not None
            assert result.duration_seconds > 0
            
            # Verify workflow was called with proper parameters
            mock_factory.assert_called_once()
            mock_mcp_abstraction.assert_called_once()
            mock_registry.assert_called_once()
            mock_policy_engine.assert_called_once()
            mock_approval_manager.assert_called_once()
    
    async def test_workflow_state_validation_with_complete_execution(
        self,
        orchestrator_service: OrchestratorService,
        mock_ai_model: MockAIModel,
        mock_mcp_client: MockMCPClient,
    ) -> None:
        """Test that WorkflowState validation works correctly during complete execution."""
        
        with patch('gearmeshing_ai.agent.abstraction.factory.AgentFactory') as mock_factory, \
             patch('gearmeshing_ai.agent.abstraction.mcp.MCPClientAbstraction') as mock_mcp_abstraction, \
             patch('gearmeshing_ai.agent.runtime.CapabilityRegistry') as mock_registry, \
             patch('gearmeshing_ai.agent.runtime.PolicyEngine') as mock_policy_engine, \
             patch('gearmeshing_ai.agent.runtime.ApprovalManager') as mock_approval_manager:
            
            # Configure mocks
            mock_agent_factory_instance = AsyncMock()
            mock_agent_factory_instance.create_agent.return_value = mock_ai_model
            mock_factory.return_value = mock_agent_factory_instance
            
            mock_mcp_abstraction_instance = AsyncMock()
            mock_mcp_abstraction_instance.list_tools.return_value = mock_mcp_client.available_tools
            mock_mcp_abstraction.return_value = mock_mcp_abstraction_instance
            
            mock_registry_instance = AsyncMock()
            mock_registry_instance.get_capabilities.return_value = mock_mcp_client.available_tools
            mock_registry.return_value = mock_registry_instance
            
            mock_policy_engine_instance = AsyncMock()
            mock_policy_engine_instance.validate_policy.return_value = {"approved": True}
            mock_policy_engine.return_value = mock_policy_engine_instance
            
            mock_approval_manager_instance = AsyncMock()
            mock_approval_manager_instance.check_approval_required.return_value = False
            mock_approval_manager.return_value = mock_approval_manager_instance
            
            # Run workflow
            result = await orchestrator_service.run_workflow(
                task_description="Test task for state validation",
                agent_role="dev",
                user_id="test_user",
                timeout_seconds=60
            )
            
            # Verify the WorkflowState was properly created and validated
            assert result.status == WorkflowStatus.SUCCESS
            
            # Check that we can retrieve the state (this validates the state structure)
            status = await orchestrator_service.get_status(result.run_id)
            assert status["run_id"] == result.run_id
            assert status["state"] in ["success", "completed", "SUCCESS"]  # Different possible final states
    
    async def test_workflow_with_approval_required(
        self,
        orchestrator_service: OrchestratorService,
        mock_ai_model: MockAIModel,
        mock_mcp_client: MockMCPClient,
    ) -> None:
        """Test workflow that requires approval with mocked AI."""
        
        with patch('gearmeshing_ai.agent.abstraction.factory.AgentFactory') as mock_factory, \
             patch('gearmeshing_ai.agent.abstraction.mcp.MCPClientAbstraction') as mock_mcp_abstraction, \
             patch('gearmeshing_ai.agent.runtime.CapabilityRegistry') as mock_registry, \
             patch('gearmeshing_ai.agent.runtime.PolicyEngine') as mock_policy_engine, \
             patch('gearmeshing_ai.agent.runtime.ApprovalManager') as mock_approval_manager:
            
            # Configure mocks - this time approval is required
            mock_agent_factory_instance = AsyncMock()
            mock_agent_factory_instance.create_agent.return_value = mock_ai_model
            mock_factory.return_value = mock_agent_factory_instance
            
            mock_mcp_abstraction_instance = AsyncMock()
            mock_mcp_abstraction_instance.list_tools.return_value = mock_mcp_client.available_tools
            mock_mcp_abstraction.return_value = mock_mcp_abstraction_instance
            
            mock_registry_instance = AsyncMock()
            mock_registry_instance.get_capabilities.return_value = mock_mcp_client.available_tools
            mock_registry.return_value = mock_registry_instance
            
            mock_policy_engine_instance = AsyncMock()
            mock_policy_engine_instance.validate_policy.return_value = {"approved": True}
            mock_policy_engine.return_value = mock_policy_engine_instance
            
            mock_approval_manager_instance = AsyncMock()
            mock_approval_manager_instance.check_approval_required.return_value = True  # Approval required
            mock_approval_manager_instance.create_approval_request.return_value = {
                "approval_id": str(uuid4()),
                "operation": "file_write",
                "risk_level": "medium",
                "description": "Write to file system"
            }
            mock_approval_manager.return_value = mock_approval_manager_instance
            
            # Run workflow - should pause for approval
            result = await orchestrator_service.run_workflow(
                task_description="Task that requires approval",
                agent_role="dev", 
                user_id="test_user",
                timeout_seconds=60
            )
            
            # Verify workflow is awaiting approval
            assert result.status == WorkflowStatus.AWAITING_APPROVAL
            assert result.approval_request is not None
            assert result.run_id is not None
    
    async def test_approval_workflow_completion(
        self,
        orchestrator_service: OrchestratorService,
        mock_ai_model: MockAIModel,
        mock_mcp_client: MockMCPClient,
    ) -> None:
        """Test complete approval workflow: run -> approve -> complete."""
        
        # First, create a workflow that awaits approval
        with patch('gearmeshing_ai.agent.abstraction.factory.AgentFactory') as mock_factory, \
             patch('gearmeshing_ai.agent.abstraction.mcp.MCPClientAbstraction') as mock_mcp_abstraction, \
             patch('gearmeshing_ai.agent.runtime.CapabilityRegistry') as mock_registry, \
             patch('gearmeshing_ai.agent.runtime.PolicyEngine') as mock_policy_engine, \
             patch('gearmeshing_ai.agent.runtime.ApprovalManager') as mock_approval_manager:
            
            # Configure mocks for initial run
            mock_agent_factory_instance = AsyncMock()
            mock_agent_factory_instance.create_agent.return_value = mock_ai_model
            mock_factory.return_value = mock_agent_factory_instance
            
            mock_mcp_abstraction_instance = AsyncMock()
            mock_mcp_abstraction_instance.list_tools.return_value = mock_mcp_client.available_tools
            mock_mcp_abstraction.return_value = mock_mcp_abstraction_instance
            
            mock_registry_instance = AsyncMock()
            mock_registry_instance.get_capabilities.return_value = mock_mcp_client.available_tools
            mock_registry.return_value = mock_registry_instance
            
            mock_policy_engine_instance = AsyncMock()
            mock_policy_engine_instance.validate_policy.return_value = {"approved": True}
            mock_policy_engine.return_value = mock_policy_engine_instance
            
            mock_approval_manager_instance = AsyncMock()
            mock_approval_manager_instance.check_approval_required.return_value = True
            mock_approval_manager_instance.create_approval_request.return_value = {
                "approval_id": str(uuid4()),
                "operation": "file_write",
                "risk_level": "medium", 
                "description": "Write to file system"
            }
            mock_approval_manager.return_value = mock_approval_manager_instance
            
            # Run initial workflow
            initial_result = await orchestrator_service.run_workflow(
                task_description="Task requiring approval",
                agent_role="dev",
                user_id="test_user",
                timeout_seconds=60
            )
            
            assert initial_result.status == WorkflowStatus.AWAITING_APPROVAL
            run_id = initial_result.run_id
            
            # Now configure mocks for approval completion
            mock_approval_manager_instance.check_approval_required.return_value = False  # No longer required
            mock_approval_manager_instance.resolve_approval.return_value = {"approved": True}
            
            # Approve the workflow
            approval_result = await orchestrator_service.approve_workflow(
                run_id=run_id,
                approver_id="test_approver",
                reason="Test approval"
            )
            
            # Verify workflow completed after approval
            assert approval_result.status == WorkflowStatus.SUCCESS
            assert approval_result.run_id == run_id
            assert approval_result.error is None
    
    async def test_workflow_error_handling_with_mocked_ai(
        self,
        orchestrator_service: OrchestratorService,
    ) -> None:
        """Test workflow error handling when AI model fails."""
        
        # Create a mock AI model that raises an exception
        failing_ai_model = AsyncMock()
        failing_ai_model.create_agent.side_effect = Exception("AI model failure")
        
        with patch('gearmeshing_ai.agent.abstraction.factory.AgentFactory') as mock_factory, \
             patch('gearmeshing_ai.agent.abstraction.mcp.MCPClientAbstraction') as mock_mcp_abstraction, \
             patch('gearmeshing_ai.agent.runtime.CapabilityRegistry') as mock_registry, \
             patch('gearmeshing_ai.agent.runtime.PolicyEngine') as mock_policy_engine, \
             patch('gearmeshing_ai.agent.runtime.ApprovalManager') as mock_approval_manager:
            
            # Configure mocks to simulate failure
            mock_factory.return_value = failing_ai_model
            mock_mcp_abstraction.return_value = AsyncMock()
            mock_registry.return_value = AsyncMock()
            mock_policy_engine.return_value = AsyncMock()
            mock_approval_manager.return_value = AsyncMock()
            
            # Run workflow - should handle error gracefully
            result = await orchestrator_service.run_workflow(
                task_description="Task that will fail",
                agent_role="dev",
                user_id="test_user",
                timeout_seconds=60
            )
            
            # Verify error was handled properly
            assert result.status == WorkflowStatus.FAILED
            assert result.error is not None
            assert "AI model failure" in result.error or "Workflow execution failed" in result.error
    
    async def test_workflow_state_consistency_across_operations(
        self,
        orchestrator_service: OrchestratorService,
        mock_ai_model: MockAIModel,
        mock_mcp_client: MockMCPClient,
    ) -> None:
        """Test that WorkflowState remains consistent across different operations."""
        
        with patch('gearmeshing_ai.agent.abstraction.factory.AgentFactory') as mock_factory, \
             patch('gearmeshing_ai.agent.abstraction.mcp.MCPClientAbstraction') as mock_mcp_abstraction, \
             patch('gearmeshing_ai.agent.runtime.CapabilityRegistry') as mock_registry, \
             patch('gearmeshing_ai.agent.runtime.PolicyEngine') as mock_policy_engine, \
             patch('gearmeshing_ai.agent.runtime.ApprovalManager') as mock_approval_manager:
            
            # Configure mocks
            mock_agent_factory_instance = AsyncMock()
            mock_agent_factory_instance.create_agent.return_value = mock_ai_model
            mock_factory.return_value = mock_agent_factory_instance
            
            mock_mcp_abstraction_instance = AsyncMock()
            mock_mcp_abstraction_instance.list_tools.return_value = mock_mcp_client.available_tools
            mock_mcp_abstraction.return_value = mock_mcp_abstraction_instance
            
            mock_registry_instance = AsyncMock()
            mock_registry_instance.get_capabilities.return_value = mock_mcp_client.available_tools
            mock_registry.return_value = mock_registry_instance
            
            mock_policy_engine_instance = AsyncMock()
            mock_policy_engine_instance.validate_policy.return_value = {"approved": True}
            mock_policy_engine.return_value = mock_policy_engine_instance
            
            mock_approval_manager_instance = AsyncMock()
            mock_approval_manager_instance.check_approval_required.return_value = False
            mock_approval_manager.return_value = mock_approval_manager_instance
            
            # Run workflow
            result = await orchestrator_service.run_workflow(
                task_description="Consistency test task",
                agent_role="dev",
                user_id="test_user",
                timeout_seconds=60
            )
            
            # Get status multiple times and verify consistency
            status1 = await orchestrator_service.get_status(result.run_id)
            await asyncio.sleep(0.01)  # Small delay
            status2 = await orchestrator_service.get_status(result.run_id)
            
            # Status should be consistent across calls
            assert status1["run_id"] == status2["run_id"] == result.run_id
            assert status1["state"] == status2["state"]
            
            # Verify final state structure is valid
            assert "run_id" in status1
            assert "state" in status1
            assert isinstance(status1.get("created_at"), (datetime, type(None)))
            assert isinstance(status1.get("updated_at"), (datetime, type(None)))


class TestWorkflowStateValidation:
    """Specific tests for WorkflowState validation during workflow execution."""
    
    async def test_workflow_state_missing_status_field_error(self) -> None:
        """Test that WorkflowState validation catches missing status field."""
        
        orchestrator_service = OrchestratorService()
        
        # Mock create_agent_workflow to return an invalid state (missing status)
        with patch('gearmeshing_ai.agent.orchestrator.service.create_agent_workflow') as mock_create_workflow:
            # Create a mock workflow that returns invalid state
            mock_workflow = AsyncMock()
            mock_workflow.ainvoke.return_value = {
                "run_id": str(uuid4()),
                "context": {
                    "task_description": "Test task",
                    "agent_role": "dev", 
                    "user_id": "test_user",
                    "metadata": {}
                }
                # Missing 'status' field - this should cause validation error
            }
            mock_create_workflow.return_value = mock_workflow
            
            # Run workflow - should fail due to missing status field
            result = await orchestrator_service.run_workflow(
                task_description="Test task",
                agent_role="dev",
                user_id="test_user",
                timeout_seconds=60
            )
            
            # Verify the validation error was caught and handled
            assert result.status == WorkflowStatus.FAILED
            assert result.error is not None
            assert "validation error" in result.error.lower() or "field required" in result.error.lower()
    
    async def test_workflow_state_invalid_context_structure(self) -> None:
        """Test that WorkflowState validation catches invalid context structure."""
        
        orchestrator_service = OrchestratorService()
        
        with patch('gearmeshing_ai.agent.orchestrator.service.create_agent_workflow') as mock_create_workflow:
            # Create a mock workflow that returns state with invalid context
            mock_workflow = AsyncMock()
            mock_workflow.ainvoke.return_value = {
                "run_id": str(uuid4()),
                "status": {
                    "state": "completed",
                    "message": "Task completed"
                },
                "context": {
                    # Missing required fields: task_description, agent_role, user_id
                    "metadata": {}
                }
            }
            mock_create_workflow.return_value = mock_workflow
            
            # Run workflow - should fail due to invalid context
            result = await orchestrator_service.run_workflow(
                task_description="Test task",
                agent_role="dev",
                user_id="test_user",
                timeout_seconds=60
            )
            
            # Verify the validation error was caught
            assert result.status == WorkflowStatus.FAILED
            assert result.error is not None
    
    async def test_workflow_state_correct_validation(self) -> None:
        """Test that WorkflowState validation passes with correct structure."""
        
        orchestrator_service = OrchestratorService()
        
        with patch('gearmeshing_ai.agent.orchestrator.service.create_agent_workflow') as mock_create_workflow:
            # Create a mock workflow that returns properly structured state
            mock_workflow = AsyncMock()
            mock_workflow.ainvoke.return_value = WorkflowState(
                run_id=str(uuid4()),
                status=RuntimeWorkflowStatus(
                    state="completed",
                    message="Task completed successfully"
                ),
                context=ExecutionContext(
                    task_description="Test task",
                    agent_role="dev",
                    user_id="test_user"
                ),
                current_proposal=ActionProposal(
                    action="file_write",
                    parameters={"path": "test.py", "content": "print('Hello')"},
                    reason="Create test file"
                )
            )
            mock_create_workflow.return_value = mock_workflow
            
            # Run workflow - should succeed with proper validation
            result = await orchestrator_service.run_workflow(
                task_description="Test task",
                agent_role="dev",
                user_id="test_user",
                timeout_seconds=60
            )
            
            # Verify success with valid state
            assert result.status == WorkflowStatus.SUCCESS
            assert result.error is None
            assert result.output is not None
