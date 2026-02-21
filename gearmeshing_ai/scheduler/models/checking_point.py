"""
Checking point result models for the scheduler system.

This module contains models for representing the results of checking point
evaluations, including decisions, actions, and metadata.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from .base import BaseSchedulerModel


class CheckResultType(str, Enum):
    """Types of checking point results."""
    
    MATCH = "match"
    NO_MATCH = "no_match"
    ERROR = "error"
    SKIP = "skip"
    
    @classmethod
    def get_all_values(cls) -> List[str]:
        """Get all enum values as strings."""
        return [member.value for member in cls]


class CheckResult(BaseSchedulerModel):
    """Represents the result of evaluating a checking point against monitoring data.
    
    This model encapsulates the outcome of a checking point evaluation, including
    whether the checking point matched, what actions should be taken, and any
    relevant metadata about the evaluation.
    """
    
    # Core result information
    checking_point_name: str = Field(..., description="Name of the checking point that produced this result")
    checking_point_type: str = Field(..., description="Type of the checking point")
    result_type: CheckResultType = Field(..., description="Type of result")
    
    # Decision information
    should_act: bool = Field(
        default=False,
        description="Whether actions should be taken based on this result"
    )
    
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence level of this result (0.0 to 1.0)"
    )
    
    # Reasoning and context
    reason: str = Field(
        default="",
        description="Human-readable explanation of why this result was produced"
    )
    
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context about the evaluation"
    )
    
    # Evaluation metadata
    evaluation_time: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when this evaluation was performed"
    )
    
    evaluation_duration_ms: Optional[int] = Field(
        None,
        description="Duration of the evaluation in milliseconds"
    )
    
    # Error information
    error_message: Optional[str] = Field(
        None,
        description="Error message if evaluation failed"
    )
    
    # Action information
    suggested_actions: List[str] = Field(
        default_factory=list,
        description="List of suggested action names"
    )
    
    action_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for suggested actions"
    )
    
    # Data processing information
    data_processed: bool = Field(
        default=False,
        description="Whether the data was successfully processed"
    )
    
    processing_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of data processing performed"
    )
    
    @field_validator('checking_point_name')
    @classmethod
    def validate_checking_point_name(cls, v: str) -> str:
        """Validate that checking point name is not empty."""
        if not v or not v.strip():
            raise ValueError("Checking point name cannot be empty")
        return v.strip()
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Validate confidence is within valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v
    
    def is_match(self) -> bool:
        """Check if this result represents a match."""
        return self.result_type == CheckResultType.MATCH
    
    def is_no_match(self) -> bool:
        """Check if this result represents no match."""
        return self.result_type == CheckResultType.NO_MATCH
    
    def is_error(self) -> bool:
        """Check if this result represents an error."""
        return self.result_type == CheckResultType.ERROR
    
    def is_skip(self) -> bool:
        """Check if this result represents a skip."""
        return self.result_type == CheckResultType.SKIP
    
    def has_actions(self) -> bool:
        """Check if this result has suggested actions."""
        return len(self.suggested_actions) > 0
    
    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if this result has high confidence.
        
        Args:
            threshold: Confidence threshold (default: 0.8)
            
        Returns:
            True if confidence is above threshold
        """
        return self.confidence >= threshold
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of this check result.
        
        Returns:
            Dictionary containing key information about this result
        """
        summary = super().get_summary()
        summary.update({
            "checking_point_name": self.checking_point_name,
            "checking_point_type": self.checking_point_type,
            "result_type": self.result_type.value,
            "should_act": self.should_act,
            "confidence": self.confidence,
            "has_actions": self.has_actions(),
            "action_count": len(self.suggested_actions),
            "is_error": self.is_error(),
            "evaluation_time": self.evaluation_time.isoformat(),
            "evaluation_duration_ms": self.evaluation_duration_ms,
        })
        return summary
    
    def add_action(self, action_name: str, **parameters: Any) -> None:
        """Add a suggested action to this result.
        
        Args:
            action_name: Name of the action
            **parameters: Parameters for the action
        """
        if action_name not in self.suggested_actions:
            self.suggested_actions.append(action_name)
        
        if parameters:
            self.action_parameters[action_name] = parameters
    
    def set_error(self, error_message: str) -> None:
        """Set this result as an error.
        
        Args:
            error_message: Error message
        """
        self.result_type = CheckResultType.ERROR
        self.error_message = error_message
        self.should_act = False
        self.confidence = 0.0
    
    def set_match(self, reason: str = "", confidence: float = 1.0) -> None:
        """Set this result as a match.
        
        Args:
            reason: Reason for the match
            confidence: Confidence level
        """
        self.result_type = CheckResultType.MATCH
        self.should_act = True
        self.reason = reason
        self.confidence = confidence
    
    def set_no_match(self, reason: str = "") -> None:
        """Set this result as no match.
        
        Args:
            reason: Reason for no match
        """
        self.result_type = CheckResultType.NO_MATCH
        self.should_act = False
        self.reason = reason
    
    def set_skip(self, reason: str = "") -> None:
        """Set this result as skipped.
        
        Args:
            reason: Reason for skipping
        """
        self.result_type = CheckResultType.SKIP
        self.should_act = False
        self.reason = reason
