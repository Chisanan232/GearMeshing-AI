"""
AI workflow activities for the scheduler system.

This module contains activities for executing AI-powered workflows through
the orchestrator service.
"""

from datetime import datetime
from typing import Any, Dict

from temporalio import activity

from gearmeshing_ai.scheduler.models.workflow import AIAction
from gearmeshing_ai.scheduler.activities.base import BaseActivity


class AIWorkflowActivity(BaseActivity):
    """Activity for executing AI-powered workflows through the orchestrator service."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.name = "ai_workflow_activity"
        self.description = "Execute AI-powered workflows through orchestrator"
        self.version = "1.0.0"
        self.timeout_seconds = 600
    
    async def execute_ai_workflow(
        self,
        ai_action: AIAction,
        data_item: Dict[str, Any],
        check_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an AI workflow through the orchestrator service.
        
        This method executes AI-powered workflows by calling the orchestrator
        service with the appropriate parameters and context.
        
        Args:
            ai_action: AI action to execute
            data_item: Monitoring data that triggered the action
            check_result: Checking point evaluation result
            
        Returns:
            AI workflow execution result
        """
        self.log_activity_start(
            "execute_ai_workflow",
            workflow_name=ai_action.workflow_name,
            checking_point_name=ai_action.checking_point_name,
            action_name=ai_action.name,
        )
        
        start_time = datetime.utcnow()
        
        try:
            # Get orchestrator service
            orchestrator_service = self._get_orchestrator_service()
            
            # Prepare workflow input
            workflow_input = {
                "ai_action": ai_action.dict(),
                "data_item": data_item,
                "check_result": check_result,
            }
            
            # Execute workflow through orchestrator
            result = await orchestrator_service.run_workflow(
                workflow_name=ai_action.workflow_name,
                input_data=workflow_input,
                timeout_seconds=ai_action.timeout_seconds,
            )
            
            execution_time = self.measure_execution_time(start_time)
            
            self.log_activity_complete(
                "execute_ai_workflow",
                workflow_name=ai_action.workflow_name,
                checking_point_name=ai_action.checking_point_name,
                success=result.get("success", False),
                execution_time_ms=int(execution_time.total_seconds() * 1000),
            )
            
            return result
            
        except Exception as e:
            self.log_activity_error(
                "execute_ai_workflow",
                e,
                workflow_name=ai_action.workflow_name,
                checking_point_name=ai_action.checking_point_name,
            )
            
            return {
                "success": False,
                "error": str(e),
                "workflow_name": ai_action.workflow_name,
                "checking_point_name": ai_action.checking_point_name,
            }
    
    def _get_orchestrator_service(self):
        """Get orchestrator service instance."""
        # Mock implementation - in real implementation, this would get the actual service
        return MockOrchestratorService()
    
    def _create_workflow_result(self, success: bool, workflow_name: str, result: Any = None, error: str = None) -> Dict[str, Any]:
        """Create a workflow result dictionary.
        
        Args:
            success: Whether the workflow was successful
            workflow_name: Name of the workflow
            result: Workflow result data
            error: Error message if workflow failed
            
        Returns:
            Workflow result dictionary
        """
        return {
            "success": success,
            "workflow_name": workflow_name,
            "result": result,
            "error": error,
            "execution_time": 1.5,
        }
    
    async def execute_workflow(self, input_data) -> Any:
        """Execute workflow with the input format expected by tests.
        
        This method adapts the test-expected input format to the actual
        execute_ai_workflow method.
        
        Args:
            input_data: AIWorkflowInput object or dictionary with workflow parameters
            
        Returns:
            Workflow execution result
        """
        # Handle both AIWorkflowInput object and dictionary
        if hasattr(input_data, 'workflow_name'):
            # It's an AIWorkflowInput object
            ai_action = input_data.ai_action
            data_item = input_data.data_item
            check_result = input_data.check_result
        else:
            # It's a dictionary
            ai_action = AIAction(
                name=input_data.get("workflow_name", "test_workflow"),
                type=AIActionType.WORKFLOW_EXECUTION,
                workflow_name=input_data.get("workflow_name", "test_workflow"),
                checking_point_name=input_data.get("checking_point_name", "test_cp"),
                prompt_template_id=input_data.get("prompt_template_id"),
                agent_role=input_data.get("agent_role"),
                timeout_seconds=input_data.get("timeout_seconds", 300),
            )
            data_item = input_data.get("input_data", {})
            check_result = {}
        
        # Call the actual execute_ai_workflow method
        result = await self.execute_ai_workflow(
            ai_action=ai_action,
            data_item=data_item,
            check_result=check_result
        )
        
        return result


class MockOrchestratorService:
    """Mock orchestrator service for testing."""
    
    async def run_workflow(
        self,
        workflow_name: str,
        input_data: Dict[str, Any],
        timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """Mock workflow execution."""
        return {
            "success": True,
            "workflow_name": workflow_name,
            "result": f"Mock result for {workflow_name}",
            "execution_time": 1.5,
        }


# Keep the original activity functions for Temporal workflow compatibility
@activity.defn
async def execute_ai_workflow(
    ai_action: AIAction,
    data_item: Dict[str, Any],
    check_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute an AI workflow through the orchestrator service."""
    activity_instance = AIWorkflowActivity()
    return await activity_instance.execute_ai_workflow(ai_action, data_item, check_result)


def get_orchestrator_service():
    """Get the orchestrator service instance.
    
    Returns:
        Orchestrator service instance
    """
    # This would import and return the actual orchestrator service
    # For now, return a mock service
    return MockOrchestratorService()


class MockOrchestratorService:
    """Mock orchestrator service for testing and development.
    
    This mock service simulates the behavior of the real orchestrator service
    for development and testing purposes.
    """
    
    async def run_ai_workflow(self, workflow_input: Dict[str, Any]) -> Dict[str, Any]:
        """Run an AI workflow.
        
        Args:
            workflow_input: Workflow input parameters
            
        Returns:
            Workflow execution result
        """
        workflow_name = workflow_input.get("workflow_name", "unknown")
        agent_role = workflow_input.get("agent_role", "dev")
        prompt_template_id = workflow_input.get("prompt_template_id")
        
        # Simulate AI workflow execution
        await activity.sleep(2)  # Simulate processing time
        
        # Mock different workflow behaviors based on workflow name
        if "triage" in workflow_name.lower():
            result = await mock_triage_workflow(workflow_input)
        elif "escalation" in workflow_name.lower():
            result = await mock_escalation_workflow(workflow_input)
        elif "assignment" in workflow_name.lower():
            result = await mock_assignment_workflow(workflow_input)
        elif "analysis" in workflow_name.lower():
            result = await mock_analysis_workflow(workflow_input)
        else:
            result = await mock_generic_workflow(workflow_input)
        
        return result


async def mock_triage_workflow(workflow_input: Dict[str, Any]) -> Dict[str, Any]:
    """Mock triage workflow execution.
    
    Args:
        workflow_input: Workflow input parameters
        
    Returns:
        Mock workflow result
    """
    data_item = workflow_input.get("context", {}).get("data_item", {})
    task_name = data_item.get("name", "Unknown Task")
    task_priority = data_item.get("priority", "normal")
    
    return {
        "success": True,
        "workflow_name": "clickup_urgent_task_triage",
        "actions_taken": [
            "analyzed_task_urgency",
            "recommended_assignment",
            "added_comment",
        ],
        "output": {
            "analysis": f"Task '{task_name}' with priority '{task_priority}' requires immediate attention",
            "recommendation": "Assign to senior developer and create follow-up tasks",
            "estimated_effort": "4 hours",
            "risk_level": "medium",
        },
        "metadata": {
            "agent_role": "dev",
            "processing_time": "2.1s",
            "confidence": 0.85,
        }
    }


async def mock_escalation_workflow(workflow_input: Dict[str, Any]) -> Dict[str, Any]:
    """Mock escalation workflow execution.
    
    Args:
        workflow_input: Workflow input parameters
        
    Returns:
        Mock workflow result
    """
    data_item = workflow_input.get("context", {}).get("data_item", {})
    days_overdue = data_item.get("days_overdue", 1)
    task_name = data_item.get("name", "Unknown Task")
    
    return {
        "success": True,
        "workflow_name": "clickup_overdue_task_escalation",
        "actions_taken": [
            "analyzed_overdue_reasons",
            "created_incident_ticket",
            "notified_management",
        ],
        "output": {
            "analysis": f"Task '{task_name}' is {days_overdue} days overdue",
            "impact_assessment": "Medium impact on project timeline",
            "escalation_level": "Team Lead" if days_overdue <= 3 else "Management",
            "recommended_actions": [
                "Reassign to experienced team member",
                "Break down into smaller subtasks",
                "Adjust timeline expectations",
            ],
        },
        "metadata": {
            "agent_role": "sre",
            "processing_time": "3.2s",
            "confidence": 0.92,
        }
    }


async def mock_assignment_workflow(workflow_input: Dict[str, Any]) -> Dict[str, Any]:
    """Mock assignment workflow execution.
    
    Args:
        workflow_input: Workflow input parameters
        
    Returns:
        Mock workflow result
    """
    data_item = workflow_input.get("context", {}).get("data_item", {})
    task_name = data_item.get("name", "Unknown Task")
    assignment_rules = workflow_input.get("parameters", {}).get("assignment_rules", {})
    
    return {
        "success": True,
        "workflow_name": "clickup_smart_assignment",
        "actions_taken": [
            "analyzed_task_requirements",
            "evaluated_team_workload",
            "made_assignment_recommendation",
        ],
        "output": {
            "analysis": f"Task '{task_name}' requires backend development skills",
            "recommended_assignee": "senior_backend_dev",
            "assignment_reasoning": "Has relevant experience and current availability",
            "confidence_score": 0.88,
            "alternative_assignees": ["backend_dev_2", "tech_lead"],
        },
        "metadata": {
            "agent_role": "dev",
            "processing_time": "1.8s",
            "confidence": 0.88,
        }
    }


async def mock_analysis_workflow(workflow_input: Dict[str, Any]) -> Dict[str, Any]:
    """Mock analysis workflow execution.
    
    Args:
        workflow_input: Workflow input parameters
        
    Returns:
        Mock workflow result
    """
    data_item = workflow_input.get("context", {}).get("data_item", {})
    message_text = data_item.get("message_text", "")
    user_name = data_item.get("user_name", "Unknown User")
    
    return {
        "success": True,
        "workflow_name": "slack_help_request_analysis",
        "actions_taken": [
            "analyzed_request_type",
            "categorized_urgency",
            "provided_response",
        ],
        "output": {
            "analysis": f"Help request from {user_name}: '{message_text[:50]}...'",
            "request_category": "technical_support",
            "urgency_level": "medium",
            "suggested_response": "I'll help you with that issue. Let me check the documentation...",
            "needs_escalation": False,
        },
        "metadata": {
            "agent_role": "qa",
            "processing_time": "1.5s",
            "confidence": 0.79,
        }
    }


async def mock_generic_workflow(workflow_input: Dict[str, Any]) -> Dict[str, Any]:
    """Mock generic workflow execution.
    
    Args:
        workflow_input: Workflow input parameters
        
    Returns:
        Mock workflow result
    """
    workflow_name = workflow_input.get("workflow_name", "unknown")
    agent_role = workflow_input.get("agent_role", "dev")
    
    return {
        "success": True,
        "workflow_name": workflow_name,
        "actions_taken": [
            "processed_request",
            "generated_response",
        ],
        "output": {
            "analysis": f"Generic AI workflow execution for {workflow_name}",
            "result": "Workflow completed successfully",
            "recommendations": ["Continue monitoring", "Review results"],
        },
        "metadata": {
            "agent_role": agent_role,
            "processing_time": "2.0s",
            "confidence": 0.75,
        }
    }
