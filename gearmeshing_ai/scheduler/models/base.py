"""Base Pydantic models for the scheduler system.

This module provides the foundational base classes that all other scheduler models
inherit from, ensuring consistent configuration and behavior across the system.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BaseSchedulerModel(BaseModel):
    """Base model for all scheduler-related data structures.

    Provides common configuration and behavior for all scheduler models,
    including consistent serialization, validation, and documentation.
    """

    model_config = ConfigDict(
        # Use enum values instead of enum objects
        use_enum_values=True,
        # Validate assignment to ensure data integrity
        validate_assignment=True,
        # Extra fields are forbidden to catch configuration errors early
        extra="forbid",
        # Populate by name to make models more robust
        populate_by_name=True,
        # Use strict validation for better error messages
        strict=True,
    )

    created_at: datetime | None = Field(
        default_factory=datetime.utcnow, description="Timestamp when this model instance was created"
    )

    updated_at: datetime | None = Field(
        default_factory=datetime.utcnow, description="Timestamp when this model instance was last updated"
    )

    def model_dump_json(self, **kwargs: Any) -> str:
        """Override to provide consistent JSON serialization.

        Args:
            **kwargs: Additional arguments to pass to model_dump_json

        Returns:
            JSON string representation of the model

        """
        # Ensure consistent datetime formatting
        kwargs.setdefault("exclude_none", True)
        kwargs.setdefault("by_alias", True)
        return super().model_dump_json(**kwargs)

    def get_summary(self) -> dict[str, Any]:
        """Get a summary dictionary of the model for logging and debugging.

        Returns:
            Dictionary containing key model information

        """
        return {
            "model_type": self.__class__.__name__,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TimestampedModel(BaseSchedulerModel):
    """Model with automatic timestamp management.

    Automatically updates the updated_at field when the model is modified.
    """

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._original_data = self.model_dump(exclude_unset=True)

    def model_copy(self, **kwargs: Any) -> "TimestampedModel":
        """Create a copy with updated timestamps.

        Args:
            **kwargs: Additional arguments to pass to model_copy

        Returns:
            New instance with updated timestamps

        """
        copy = super().model_copy(**kwargs)
        copy.updated_at = datetime.utcnow()
        return copy

    def has_changed(self) -> bool:
        """Check if the model has been modified since creation.

        Returns:
            True if the model has been modified, False otherwise

        """
        current_data = self.model_dump(exclude_unset=True)
        return current_data != self._original_data
