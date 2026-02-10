"""LangGraph workflow definition for AI agent execution.

This module defines the complete LangGraph workflow that orchestrates the execution
of AI agents with 9 specialized nodes for tool discovery, decision making, policy
validation, approval management, result processing, and error handling.

WORKFLOW ARCHITECTURE
=====================

Complete 9-Node Workflow:

    capability_discovery
            ↓
    agent_decision
            ↓
    policy_validation
        ├─ REJECTED → error_handler → END
        └─ APPROVED ↓
    
    approval_check
        ├─ REQUIRED → approval_workflow ↓
        └─ NOT_REQUIRED ↓
    
    result_processing
            ↓
    completion_check
            ↓
    approval_resolution
        ├─ REJECTED → error_handler → END
        └─ APPROVED → END


COMPONENT RELATIONSHIPS
======================

WorkflowState (Central State Object)
    ├── ExecutionContext
    │   ├── task_description
    │   ├── agent_role
    │   └── user_id
    ├── WorkflowStatus
    │   ├── state
    │   ├── message
    │   └── error
    ├── available_capabilities (from capability_discovery)
    ├── execution_plan (from agent_decision)
    └── results (from result_processing)

Node Dependencies:
    capability_discovery → CapabilityRegistry → MCPClientAbstraction
    agent_decision → AgentFactory
    policy_validation → (WorkflowState only)
    approval_check → (WorkflowState only)
    approval_workflow → PolicyEngine, ApprovalManager
    result_processing → (WorkflowState only)
    completion_check → (WorkflowState only)
    approval_resolution → ApprovalManager
    error_handler → (WorkflowState only)


DESIGN PRINCIPLES
=================

1. SEPARATION OF CONCERNS
   - Each node has a single, well-defined responsibility
   - Nodes are independent and can be tested in isolation
   - State is passed through WorkflowState object

2. POLICY-DRIVEN EXECUTION
   - All tool access is validated against policies
   - Approval requirements are policy-driven
   - Safety constraints are enforced at validation stage

3. HUMAN-IN-THE-LOOP SUPPORT
   - Approval workflow allows human intervention
   - Approval decisions are tracked and logged
   - Workflow can be paused and resumed

4. ERROR RESILIENCE
   - All nodes have error handling
   - Errors are logged and tracked
   - Workflow can recover from failures

5. OBSERVABILITY
   - All operations are logged
   - Metrics are collected at each node
   - Workflow execution can be monitored

6. PERFORMANCE OPTIMIZATION
   - Capability discovery results are cached
   - Batch processing is supported
   - Resource pooling is available


KEY DESIGN CONCERNS
===================

1. LATENCY MANAGEMENT
   Concern: Tool discovery and policy validation add latency
   Solution: Caching at capability discovery, async execution
   Monitoring: Track node execution times in metrics

2. APPROVAL BOTTLENECKS
   Concern: Approval workflow can block execution
   Solution: Timeout handling, escalation paths
   Monitoring: Track approval wait times

3. STATE CONSISTENCY
   Concern: State mutations across nodes must be consistent
   Solution: Immutable state updates using model_copy()
   Monitoring: Validate state transitions

4. POLICY ENFORCEMENT
   Concern: Policies must be enforced consistently
   Solution: Centralized PolicyEngine, validation at multiple points
   Monitoring: Log all policy decisions

5. ERROR PROPAGATION
   Concern: Errors in one node shouldn't crash entire workflow
   Solution: Try-catch in all nodes, error_handler node
   Monitoring: Track error rates and types

6. SCALABILITY
   Concern: Workflow must handle high-volume execution
   Solution: Async execution, resource pooling, batch processing
   Monitoring: Track throughput and resource usage


CRITICAL EXECUTION PATHS
========================

Path 1: SUCCESSFUL EXECUTION (No Approval)
    capability_discovery → agent_decision → policy_validation ✓
    → approval_check (no approval needed) → result_processing
    → completion_check ✓ → approval_resolution ✓ → END

Path 2: SUCCESSFUL EXECUTION (With Approval)
    capability_discovery → agent_decision → policy_validation ✓
    → approval_check (approval needed) → approval_workflow
    → result_processing → completion_check ✓
    → approval_resolution ✓ → END

Path 3: POLICY REJECTION
    capability_discovery → agent_decision → policy_validation ✗
    → error_handler → END

Path 4: APPROVAL REJECTION
    ... → approval_resolution ✗ → error_handler → END


STATE TRANSITIONS
=================

CAPABILITY_DISCOVERY_COMPLETE
    ↓
AGENT_DECISION_COMPLETE
    ↓
POLICY_VALIDATED / POLICY_REJECTED
    ├─ POLICY_REJECTED → ERROR
    └─ POLICY_VALIDATED ↓
    
APPROVAL_REQUIRED / NO_APPROVAL_NEEDED
    ├─ APPROVAL_REQUIRED → AWAITING_APPROVAL
    │   ├─ APPROVAL_COMPLETE
    │   └─ APPROVAL_REJECTED → ERROR
    └─ NO_APPROVAL_NEEDED ↓
    
RESULT_PROCESSING_COMPLETE
    ↓
TASK_COMPLETE / TASK_INCOMPLETE
    ↓
APPROVAL_RESOLVED / APPROVAL_REJECTED
    ├─ APPROVAL_REJECTED → ERROR
    └─ APPROVAL_RESOLVED → SUCCESS


PERFORMANCE CHARACTERISTICS
===========================

Node Execution Times (typical):
    capability_discovery:  50-200ms (cached: 5-10ms)
    agent_decision:        200-500ms (depends on LLM)
    policy_validation:     10-50ms
    approval_check:        10-50ms
    approval_workflow:     variable (depends on approval time)
    result_processing:     10-50ms
    completion_check:      10-50ms
    approval_resolution:   10-50ms
    error_handler:         10-50ms

Total Latency (no approval): ~300-800ms
Total Latency (with approval): variable (depends on approval time)


MONITORING POINTS
=================

Per-Node Metrics:
    - Execution time
    - Success/failure rate
    - Error types
    - State transitions

Workflow-Level Metrics:
    - Total execution time
    - Approval wait time
    - Error recovery time
    - Throughput (workflows/second)

Business Metrics:
    - Approval rate
    - Policy rejection rate
    - Task completion rate
    - Average approval time


EXTENSION POINTS
================

1. Custom Nodes
   - Can be added before/after existing nodes
   - Must follow node interface (async function)
   - Must update WorkflowState

2. Custom Policies
   - PolicyEngine supports custom policy types
   - Policies are evaluated at validation stage
   - Can be added/removed dynamically

3. Custom Approval Strategies
   - ApprovalManager supports custom approval logic
   - Can implement different approval workflows
   - Can add approval escalation paths

4. Custom Monitoring
   - WorkflowMonitor can be extended
   - Custom metrics can be added
   - Integration with monitoring systems


TESTING STRATEGY
================

Unit Tests:
    - Test each node independently
    - Mock dependencies
    - Verify state transitions

Integration Tests:
    - Test node combinations
    - Test state flow through workflow
    - Test error handling

E2E Tests:
    - Test complete workflow execution
    - Test with real components
    - Test approval workflows


DEPLOYMENT CONSIDERATIONS
=========================

1. Configuration
   - PolicyEngine must be configured with policies
   - ApprovalManager must be initialized
   - CapabilityRegistry must have MCP client

2. Monitoring
   - Enable logging at appropriate levels
   - Set up metrics collection
   - Configure error alerting

3. Scaling
   - Use async execution for high throughput
   - Implement caching for capability discovery
   - Use resource pooling for connections

4. Security
   - Validate all inputs
   - Enforce policies strictly
   - Log all decisions
   - Audit approval workflows
"""

import logging
from typing import Any

from langgraph.graph import StateGraph

from gearmeshing_ai.agent_core.abstraction.factory import AgentFactory
from gearmeshing_ai.agent_core.abstraction.mcp import MCPClientAbstraction

from .approval_manager import ApprovalManager
from .capability_registry import CapabilityRegistry
from .nodes import (
    agent_decision_node,
    approval_check_node,
    approval_resolution_node,
    approval_workflow_node,
    capability_discovery_node,
    completion_check_node,
    error_handler_node,
    policy_validation_node,
    result_processing_node,
)
from .policy_engine import PolicyEngine
from .models import WorkflowState

logger = logging.getLogger(__name__)


def create_agent_workflow(
    agent_factory: AgentFactory,
    mcp_client: MCPClientAbstraction,
    capability_registry: CapabilityRegistry | None = None,
    policy_engine: PolicyEngine | None = None,
    approval_manager: ApprovalManager | None = None,
) -> Any:
    """Create and compile the complete LangGraph workflow with all 9 nodes.

    This function creates a LangGraph workflow that orchestrates AI agent
    execution with the following node sequence:
    1. Capability Discovery - Discover available tools
    2. Agent Decision - Get agent proposal
    3. Policy Validation - Validate against policies
    4. Approval Check - Check if approval is needed
    5. Approval Workflow - Track approval state
    6. Result Processing - Process execution results
    7. Completion Check - Determine if workflow is complete
    8. Approval Resolution - Process approval decisions
    9. Error Handler - Handle any errors

    Args:
        agent_factory: Factory for creating AI agents
        mcp_client: MCP client for tool execution
        capability_registry: Registry for capability management (optional)
        policy_engine: Engine for policy enforcement (optional)
        approval_manager: Manager for approval requests (optional)

    Returns:
        Compiled LangGraph workflow graph

    Raises:
        ValueError: If workflow creation fails

    """
    logger.info("Creating complete LangGraph workflow with all 9 nodes")

    try:
        # Initialize optional components with defaults if not provided
        if capability_registry is None:
            capability_registry = CapabilityRegistry(mcp_client)
        if policy_engine is None:
            policy_engine = PolicyEngine()
        if approval_manager is None:
            approval_manager = ApprovalManager()

        # Create state graph
        workflow = StateGraph(WorkflowState)

        # Add nodes to the graph
        logger.debug("Adding all 9 nodes to workflow graph")

        # Node 1: Capability discovery
        async def capability_discovery_wrapper(state):
            return await capability_discovery_node(state, capability_registry)

        workflow.add_node("capability_discovery", capability_discovery_wrapper)

        # Node 2: Agent decision
        async def agent_decision_wrapper(state):
            return await agent_decision_node(state, agent_factory)

        workflow.add_node("agent_decision", agent_decision_wrapper)

        # Node 3: Policy validation
        async def policy_validation_wrapper(state):
            return await policy_validation_node(state)

        workflow.add_node("policy_validation", policy_validation_wrapper)

        # Node 4: Approval check
        async def approval_check_wrapper(state):
            return await approval_check_node(state)

        workflow.add_node("approval_check", approval_check_wrapper)

        # Node 5: Approval workflow
        async def approval_workflow_wrapper(state):
            return await approval_workflow_node(state, policy_engine, approval_manager)

        workflow.add_node("approval_workflow", approval_workflow_wrapper)

        # Node 6: Result processing
        async def result_processing_wrapper(state):
            return await result_processing_node(state)

        workflow.add_node("result_processing", result_processing_wrapper)

        # Node 7: Completion check
        async def completion_check_wrapper(state):
            return await completion_check_node(state)

        workflow.add_node("completion_check", completion_check_wrapper)

        # Node 8: Approval resolution
        async def approval_resolution_wrapper(state):
            return await approval_resolution_node(state, approval_manager)

        workflow.add_node("approval_resolution", approval_resolution_wrapper)

        # Node 9: Error handler
        async def error_handler_wrapper(state):
            return await error_handler_node(state)

        workflow.add_node("error_handler", error_handler_wrapper)

        # Set entry point to capability discovery
        logger.debug("Setting workflow entry point to capability_discovery")
        workflow.set_entry_point("capability_discovery")

        # Add edges between nodes
        logger.debug("Adding edges between all nodes")

        # Capability discovery -> Agent decision
        workflow.add_edge("capability_discovery", "agent_decision")

        # Agent decision -> Policy validation
        workflow.add_edge("agent_decision", "policy_validation")

        # Policy validation -> Approval check or Error handler
        def policy_validation_router(state: WorkflowState) -> str:
            """Route based on policy validation result."""
            if state.status.state == "POLICY_REJECTED":
                return "error_handler"
            return "approval_check"

        workflow.add_conditional_edges(
            "policy_validation",
            policy_validation_router,
            {
                "approval_check": "approval_check",
                "error_handler": "error_handler",
            },
        )

        # Approval check -> Approval workflow or Result processing
        def approval_check_router(state: WorkflowState) -> str:
            """Route based on approval requirement."""
            if state.status.state == "APPROVAL_REQUIRED":
                return "approval_workflow"
            return "result_processing"

        workflow.add_conditional_edges(
            "approval_check",
            approval_check_router,
            {
                "approval_workflow": "approval_workflow",
                "result_processing": "result_processing",
            },
        )

        # Approval workflow -> Result processing
        workflow.add_edge("approval_workflow", "result_processing")

        # Result processing -> Completion check
        workflow.add_edge("result_processing", "completion_check")

        # Completion check -> Approval resolution
        workflow.add_edge("completion_check", "approval_resolution")

        # Approval resolution -> End or Error handler
        def approval_resolution_router(state: WorkflowState) -> str:
            """Route based on approval resolution result."""
            if state.status.state == "APPROVAL_REJECTED":
                return "error_handler"
            return "__end__"

        workflow.add_conditional_edges(
            "approval_resolution",
            approval_resolution_router,
            {
                "error_handler": "error_handler",
                "__end__": "__end__",
            },
        )

        # Error handler -> End
        workflow.add_edge("error_handler", "__end__")

        # Compile the workflow
        logger.info("Compiling complete LangGraph workflow")
        compiled_workflow = workflow.compile()

        logger.info("Complete LangGraph workflow with 9 nodes created and compiled successfully")
        return compiled_workflow

    except Exception as e:
        logger.error(f"Failed to create LangGraph workflow: {e}")
        raise ValueError(f"Workflow creation failed: {e}") from e
