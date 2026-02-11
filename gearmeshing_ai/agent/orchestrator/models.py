"""
Data models for the orchestrator module.

Defines all data structures used for workflow execution, approval management,
state persistence, and event callbacks.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4


class WorkflowStatus(str, Enum):
    """Status of a workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ApprovalDecision(str, Enum):
    """User decision on an approval request."""
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class WorkflowEventType(str, Enum):
    """Types of workflow events."""
    WORKFLOW_STARTED = "workflow_started"
    CAPABILITY_DISCOVERY_STARTED = "capability_discovery_started"
    CAPABILITY_DISCOVERY_COMPLETED = "capability_discovery_completed"
    AGENT_DECISION_STARTED = "agent_decision_started"
    AGENT_DECISION_COMPLETED = "agent_decision_completed"
    POLICY_VALIDATION_STARTED = "policy_validation_started"
    POLICY_VALIDATION_COMPLETED = "policy_validation_completed"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_TIMEOUT = "approval_timeout"
    RESULT_PROCESSING_STARTED = "result_processing_started"
    RESULT_PROCESSING_COMPLETED = "result_processing_completed"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_CANCELLED = "workflow_cancelled"


@dataclass
class ApprovalRequest:
    """Request for user approval of a risky operation."""
    run_id: str
    operation: str
    risk_level: str
    description: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    timeout_seconds: int = 3600
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalDecisionRecord:
    """Record of a user's approval decision."""
    approval_id: str
    run_id: str
    decision: ApprovalDecision
    approver_id: str
    decided_at: datetime = field(default_factory=datetime.utcnow)
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowEvent:
    """Event emitted during workflow execution."""
    event_type: WorkflowEventType
    run_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    payload: Dict[str, Any] = field(default_factory=dict)
    approval_request: Optional[ApprovalRequest] = None


@dataclass
class WorkflowResult:
    """Result of a workflow execution."""
    run_id: str
    status: WorkflowStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    approval_request: Optional[ApprovalRequest] = None
    events: List[WorkflowEvent] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None


@dataclass
class WorkflowCheckpoint:
    """Checkpoint for workflow state persistence."""
    run_id: str
    checkpoint_id: str = field(default_factory=lambda: str(uuid4()))
    state: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowCallbacks:
    """Callbacks for workflow events."""
    on_workflow_started: Optional[Callable[[str], None]] = None
    on_approval_required: Optional[Callable[[ApprovalRequest], None]] = None
    on_approval_approved: Optional[Callable[[str, str], None]] = None
    on_approval_rejected: Optional[Callable[[str, str], None]] = None
    on_approval_timeout: Optional[Callable[[str], None]] = None
    on_workflow_completed: Optional[Callable[[WorkflowResult], None]] = None
    on_workflow_failed: Optional[Callable[[WorkflowResult], None]] = None
    on_event: Optional[Callable[[WorkflowEvent], None]] = None


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator."""
    default_timeout_seconds: int = 300
    default_approval_timeout_seconds: int = 3600
    persistence_backend: str = "database"
    enable_event_logging: bool = True
    max_retries: int = 3
    retry_delay_seconds: int = 5
    metadata: Dict[str, Any] = field(default_factory=dict)
