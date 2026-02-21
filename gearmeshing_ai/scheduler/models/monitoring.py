"""
Monitoring data models for the scheduler system.

This module contains models for representing monitoring data from external systems,
including ClickUp tasks, Slack messages, and other data sources.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, field_validator

from .base import BaseSchedulerModel


class MonitoringDataType(str, Enum):
    """Types of monitoring data that can be processed by the system."""
    
    CLICKUP_TASK = "clickup_task"
    SLACK_MESSAGE = "slack_message"
    EMAIL_ALERT = "email_alert"
    WEBHOOK_EVENT = "webhook_event"
    CUSTOM_DATA = "custom_data"
    
    @classmethod
    def get_all_values(cls) -> List[str]:
        """Get all enum values as strings."""
        return [member.value for member in cls]


class MonitoringData(BaseSchedulerModel):
    """Represents a piece of monitoring data from an external system.
    
    This model encapsulates data from various sources (ClickUp, Slack, etc.)
    in a consistent format that can be processed by checking points.
    """
    
    # Core identification
    id: str = Field(..., description="Unique identifier for this data item")
    type: MonitoringDataType = Field(..., description="Type of monitoring data")
    source: str = Field(..., description="Source system where this data originated")
    
    # Data content
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Raw data from the source system"
    )
    
    # Metadata
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when this data was captured"
    )
    
    processed_at: Optional[datetime] = Field(
        None,
        description="Timestamp when this data was processed by checking points"
    )
    
    # Processing state
    processing_status: str = Field(
        default="pending",
        description="Processing status: pending, processing, completed, failed"
    )
    
    processing_errors: List[str] = Field(
        default_factory=list,
        description="List of processing errors, if any"
    )
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about this data item"
    )
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate that ID is not empty."""
        if not v or not v.strip():
            raise ValueError("ID cannot be empty")
        return v.strip()
    
    @field_validator('source')
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Validate that source is not empty."""
        if not v or not v.strip():
            raise ValueError("Source cannot be empty")
        return v.strip()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of this monitoring data item.
        
        Returns:
            Dictionary containing key information about this data item
        """
        summary = super().get_summary()
        # type is already a string due to use_enum_values config
        type_value = self.type if isinstance(self.type, str) else self.type.value
        summary.update({
            "id": self.id,
            "type": type_value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "processing_status": self.processing_status,
            "data_keys": list(self.data.keys()),
            "has_errors": len(self.processing_errors) > 0,
        })
        return summary
    
    def get_data_field(self, field_path: str, default: Any = None) -> Any:
        """Get a nested field from the data dictionary using dot notation.
        
        Args:
            field_path: Dot-separated path to the field (e.g., "task.name")
            default: Default value if field is not found
            
        Returns:
            Field value or default
        """
        keys = field_path.split('.')
        value = self.data
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set_data_field(self, field_path: str, value: Any) -> None:
        """Set a nested field in the data dictionary using dot notation.
        
        Args:
            field_path: Dot-separated path to the field (e.g., "task.name")
            value: Value to set
        """
        keys = field_path.split('.')
        data = self.data
        
        # Navigate to the parent of the target field
        for key in keys[:-1]:
            if key not in data:
                data[key] = {}
            data = data[key]
        
        # Set the target field
        data[keys[-1]] = value
    
    def mark_processed(self, status: str = "completed") -> None:
        """Mark this data item as processed.
        
        Args:
            status: Processing status to set
        """
        self.processed_at = datetime.utcnow()
        self.processing_status = status
    
    def add_error(self, error: str) -> None:
        """Add a processing error to this data item.
        
        Args:
            error: Error message to add
        """
        self.processing_errors.append(error)
        if self.processing_status == "pending":
            self.processing_status = "failed"
    
    def is_clickup_task(self) -> bool:
        """Check if this is a ClickUp task."""
        return self.type == MonitoringDataType.CLICKUP_TASK
    
    def is_slack_message(self) -> bool:
        """Check if this is a Slack message."""
        return self.type == MonitoringDataType.SLACK_MESSAGE
    
    def is_email_alert(self) -> bool:
        """Check if this is an email alert."""
        return self.type == MonitoringDataType.EMAIL_ALERT
    
    def get_task_id(self) -> Optional[str]:
        """Get the task ID if this is a task-related data item."""
        if self.is_clickup_task():
            return self.get_data_field("id")
        return self.get_data_field("task_id")
    
    def get_user_id(self) -> Optional[str]:
        """Get the user ID if this is a user-related data item."""
        if self.is_slack_message():
            return self.get_data_field("user")
        return self.get_data_field("user_id")
