"""
AI workflow executor for the scheduler system.

This module contains the AI workflow executor that handles AI-powered
actions and decision making within the scheduler system.
"""

from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

from gearmeshing_ai.scheduler.models.workflow import AIWorkflowInput, AIWorkflowResult
from gearmeshing_ai.scheduler.workflows.base import BaseWorkflow

# Import activities
from gearmeshing_ai.scheduler.activities.ai_workflow import execute_ai_workflow


@workflow.defn(name="AIWorkflowExecutor")
class AIWorkflowExecutor(BaseWorkflow):
    """AI workflow executor for running AI-powered actions.
    
    This workflow executes AI actions through the orchestrator service,
    handling AI model interactions and decision making.
    """
    
    @workflow.run
    async def run(self, input: AIWorkflowInput) -> AIWorkflowResult:
        """Execute an AI workflow action.
        
        Args:
            input: AI workflow input containing action and context
            
        Returns:
            AI workflow result
        """
        self.log_workflow_start(
            "AIWorkflowExecutor",
            action_name=input.ai_action.name,
            workflow_name=input.ai_action.workflow_name,
            checking_point_name=input.ai_action.checking_point_name,
        )
        
        try:
            # Execute AI workflow via orchestrator service
            result = await self.execute_activity_with_retry(
                execute_ai_workflow,
                input.ai_action,
                input.data_item,
                input.check_result,
                timeout=input.ai_action.get_execution_timeout(),
            )
            
            # Create workflow result
            workflow_result = AIWorkflowResult(
                workflow_name=input.ai_action.workflow_name,
                checking_point_name=input.ai_action.checking_point_name,
                success=True,
                execution_id=self.get_workflow_info()["workflow_id"],
                started_at=workflow.now(),
                completed_at=workflow.now(),
                output=result,
                actions_taken=[input.ai_action.name],
                data_summary={
                    "data_item_id": input.data_item.get("id"),
                    "data_item_type": input.data_item.get("type"),
                    "check_result_type": input.check_result.get("result_type"),
                },
                approval_required=input.ai_action.approval_required,
                approval_granted=not input.ai_action.approval_required,  # Assume granted if not required
            )
            
            self.log_workflow_complete(
                "AIWorkflowExecutor",
                action_name=input.ai_action.name,
                success=True,
                output_keys=list(result.keys()) if isinstance(result, dict) else [],
            )
            
            return workflow_result
            
        except Exception as e:
            self.log_workflow_error(
                "AIWorkflowExecutor",
                e,
                action_name=input.ai_action.name,
                workflow_name=input.ai_action.workflow_name,
            )
            
            # Return failed result
            return AIWorkflowResult(
                workflow_name=input.ai_action.workflow_name,
                checking_point_name=input.ai_action.checking_point_name,
                success=False,
                execution_id=self.get_workflow_info()["workflow_id"],
                started_at=workflow.now(),
                error_message=str(e),
                error_details={
                    "error_type": type(e).__name__,
                    "action_name": input.ai_action.name,
                },
                data_summary={
                    "data_item_id": input.data_item.get("id"),
                    "data_item_type": input.data_item.get("type"),
                },
                approval_required=input.ai_action.approval_required,
                approval_granted=False,
            )
