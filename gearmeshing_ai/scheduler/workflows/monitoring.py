"""Smart monitoring workflow for the scheduler system.

This module contains the main Temporal workflow that continuously monitors
external systems and processes data through checking points.
"""

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import workflow

from gearmeshing_ai.scheduler.activities.action_execute import execute_action
from gearmeshing_ai.scheduler.activities.ai_workflow import execute_ai_workflow

# Import activities (these will be implemented in the activities module)
from gearmeshing_ai.scheduler.activities.data_fetch import fetch_monitoring_data
from gearmeshing_ai.scheduler.checking_points.registry import checking_point_registry
from gearmeshing_ai.scheduler.models.config import MonitorConfig
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData
from gearmeshing_ai.scheduler.models.workflow import AIWorkflowInput, AIWorkflowResult
from gearmeshing_ai.scheduler.workflows.base import BaseWorkflow


@workflow.defn(name="SmartMonitoringWorkflow")
class SmartMonitoringWorkflow(BaseWorkflow):
    """Smart monitoring workflow that continuously checks external systems.

    This workflow runs continuously, fetching data from external systems,
    processing it through checking points, and taking appropriate actions.
    """

    @workflow.run
    async def run(self, monitor_config: MonitorConfig) -> None:
        """Run the smart monitoring workflow.

        Args:
            monitor_config: Configuration for the monitoring workflow

        """
        self.log_workflow_start(
            "SmartMonitoringWorkflow",
            config_name=monitor_config.name,
            interval_seconds=monitor_config.interval_seconds,
        )

        try:
            # Initialize checking point instances from global registry
            checking_points = checking_point_registry.get_all_instances()
            enabled_checking_points = {name: cp for name, cp in checking_points.items() if cp.enabled}

            self.logger.info(
                f"Initialized {len(enabled_checking_points)} checking points",
                extra={
                    "total_checking_points": len(checking_points),
                    "enabled_checking_points": len(enabled_checking_points),
                    "checking_point_names": list(enabled_checking_points.keys()),
                },
            )

            # Main monitoring loop
            while True:
                try:
                    # Fetch data from external systems
                    data_items = await self.execute_activity_with_retry(
                        fetch_monitoring_data,
                        monitor_config,
                        timeout=timedelta(minutes=5),
                    )

                    self.logger.info(
                        f"Fetched {len(data_items)} data items",
                        extra={
                            "data_items_count": len(data_items),
                            "data_types": [item.type.value for item in data_items],
                        },
                    )

                    # Process each data item through all checking points
                    for data_item in data_items:
                        await self.process_data_item_with_checking_points(data_item, enabled_checking_points)

                    # Wait for next monitoring cycle using Temporal durable timer
                    await asyncio.sleep(monitor_config.interval_seconds)

                except Exception as e:
                    self.log_workflow_error(
                        "SmartMonitoringWorkflow",
                        e,
                        cycle_error=True,
                    )

                    # Wait before retrying the cycle
                    await asyncio.sleep(min(60, monitor_config.interval_seconds // 4))

        except Exception as e:
            self.log_workflow_error(
                "SmartMonitoringWorkflow",
                e,
                fatal_error=True,
            )
            raise
        finally:
            self.log_workflow_complete("SmartMonitoringWorkflow")

    async def process_data_item_with_checking_points(
        self, data_item: MonitoringData, checking_points: dict[str, Any]
    ) -> None:
        """Process a single data item through all checking points.

        Args:
            data_item: Monitoring data to process
            checking_points: Dictionary of checking point instances

        """
        self.logger.debug(
            f"Processing data item {data_item.id}",
            extra={
                "data_item_id": data_item.id,
                "data_item_type": data_item.type.value,
                "data_source": data_item.source,
            },
        )

        # Check each checking point
        for checking_point_name, checking_point in checking_points.items():
            try:
                # Only run checking points that are relevant for this data type
                if not checking_point.can_handle(data_item):
                    continue

                self.logger.debug(
                    f"Evaluating checking point {checking_point_name} for data item {data_item.id}",
                    extra={
                        "checking_point_name": checking_point_name,
                        "checking_point_type": checking_point.type.value,
                        "data_item_id": data_item.id,
                    },
                )

                # Evaluate the checking point
                check_result = await self.execute_activity_with_retry(
                    evaluate_checking_point,
                    checking_point,
                    data_item,
                    timeout=timedelta(seconds=30),
                )

                self.logger.info(
                    f"Checking point {checking_point_name} result: {check_result.result_type.value}",
                    extra={
                        "checking_point_name": checking_point_name,
                        "data_item_id": data_item.id,
                        "result_type": check_result.result_type.value,
                        "should_act": check_result.should_act,
                        "confidence": check_result.confidence,
                    },
                )

                # If checking point matches, trigger actions
                if check_result.should_act:
                    # Get immediate actions
                    immediate_actions = checking_point.get_actions(data_item, check_result)

                    # Execute immediate actions
                    for action in immediate_actions:
                        await self.execute_action_with_retry(
                            execute_action,
                            action,
                            timeout=timedelta(minutes=10),
                            retry_policy=self.create_retry_policy(
                                maximum_attempts=3,
                                initial_interval=timedelta(seconds=1),
                            ),
                        )

                        self.logger.info(
                            f"Executed immediate action for checking point {checking_point_name}",
                            extra={
                                "checking_point_name": checking_point_name,
                                "data_item_id": data_item.id,
                                "action_type": action.get("type", "unknown"),
                            },
                        )

                    # Get AI workflow actions
                    ai_actions = checking_point.get_after_process(data_item, check_result)

                    # Execute AI workflows if any
                    for ai_action in ai_actions:
                        await self.execute_child_workflow_with_timeout(
                            AIWorkflowExecutor.run,
                            AIWorkflowInput(
                                ai_action=ai_action,
                                data_item=data_item,
                                check_result=check_result,
                            ),
                            timeout=ai_action.get_execution_timeout(),
                        )

                        self.logger.info(
                            f"Executed AI workflow for checking point {checking_point_name}",
                            extra={
                                "checking_point_name": checking_point_name,
                                "data_item_id": data_item.id,
                                "ai_workflow": ai_action.workflow_name,
                                "ai_action": ai_action.name,
                            },
                        )

                    # Optional: Stop processing further checking points for this data item
                    if checking_point.stop_on_match:
                        self.logger.debug(
                            f"Stopping further checking point processing for data item {data_item.id} "
                            f"due to stop_on_match in {checking_point_name}",
                            extra={
                                "data_item_id": data_item.id,
                                "stopping_checking_point": checking_point_name,
                            },
                        )
                        break

            except Exception as e:
                self.log_workflow_error(
                    "SmartMonitoringWorkflow",
                    e,
                    checking_point_name=checking_point_name,
                    data_item_id=data_item.id,
                )

                # Continue with other checking points even if one fails
                continue


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
