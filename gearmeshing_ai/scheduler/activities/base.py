"""
Base activity utilities for the scheduler system.

This module provides base classes and common functionality for all Temporal
activities in the scheduler system.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from temporalio import activity

from gearmeshing_ai.scheduler.models.config import MonitorConfig


class BaseActivity:
    """Base class for all scheduler activities.
    
    Provides common functionality and utilities for Temporal activities,
    including logging, error handling, and configuration management.
    """
    
    def __init__(self, config: Dict[str, Any] = None) -> None:
        """Initialize the base activity.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.logger = activity.logger
        self.name = "base_activity"
        self.description = "Base activity for all scheduler activities"
        self.version = "1.0.0"
        self.timeout_seconds = 300
    
    def validate_config(self, config: Dict[str, Any] = None) -> List[str]:
        """Validate the activity configuration.
        
        Args:
            config: Optional configuration dictionary to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Use provided config or self.config
        cfg = config if config is not None else self.config
        
        # Validate timeout_seconds from config
        timeout = cfg.get('timeout_seconds', self.timeout_seconds)
        if timeout < 0:
            errors.append("timeout_seconds must be positive")
        
        return errors
    
    def measure_execution_time(self, start_time: datetime) -> timedelta:
        """Measure execution time from start time.
        
        Args:
            start_time: Start time
            
        Returns:
            Execution time duration
        """
        return datetime.utcnow() - start_time
    
    def log_activity_start(self, activity_name: str, **context: Any) -> None:
        """Log activity start with context.
        
        Args:
            activity_name: Name of the activity
            **context: Additional context information
        """
        self.logger.info(
            f"Starting activity: {activity_name}",
            extra={
                "activity_name": activity_name,
                "activity_id": activity.info().activity_id,
                "workflow_id": activity.info().workflow_id,
                "run_id": activity.info().run_id,
                "attempt": activity.info().attempt,
                **context,
            }
        )
    
    def log_activity_complete(self, activity_name: str, **context: Any) -> None:
        """Log activity completion with context.
        
        Args:
            activity_name: Name of the activity
            **context: Additional context information
        """
        self.logger.info(
            f"Completed activity: {activity_name}",
            extra={
                "activity_name": activity_name,
                "activity_id": activity.info().activity_id,
                "workflow_id": activity.info().workflow_id,
                "run_id": activity.info().run_id,
                "attempt": activity.info().attempt,
                **context,
            }
        )
    
    def log_activity_error(self, activity_name: str, error: Exception, **context: Any) -> None:
        """Log activity error with context.
        
        Args:
            activity_name: Name of the activity
            error: Error that occurred
            **context: Additional context information
        """
        self.logger.error(
            f"Error in activity: {activity_name}: {str(error)}",
            extra={
                "activity_name": activity_name,
                "activity_id": activity.info().activity_id,
                "workflow_id": activity.info().workflow_id,
                "run_id": activity.info().run_id,
                "attempt": activity.info().attempt,
                "error_type": type(error).__name__,
                "error_message": str(error),
                **context,
            },
            exc_info=True,
        )
    
    def get_activity_info(self) -> Dict[str, Any]:
        """Get current activity information.
        
        Returns:
            Dictionary containing activity information
        """
        info = activity.info()
        return {
            "activity_id": info.activity_id,
            "activity_type": info.activity_type.name,
            "workflow_id": info.workflow_id,
            "run_id": info.run_id,
            "attempt": info.attempt,
            "heartbeat_timeout": info.heartbeat_timeout.total_seconds() if info.heartbeat_timeout else None,
            "start_to_close_timeout": info.start_to_close_timeout.total_seconds() if info.start_to_close_timeout else None,
        }
    
    def heartbeat(self, details: Optional[Dict[str, Any]] = None) -> None:
        """Send a heartbeat to indicate the activity is still running.
        
        Args:
            details: Optional heartbeat details
        """
        activity.heartbeat(details)
    
    def is_test_mode(self) -> bool:
        """Check if activity is running in test mode.
        
        Returns:
            True if running in test mode
        """
        # Check if test mode is indicated in activity info or environment
        info = activity.info()
        return (hasattr(info, 'test_mode') and info.test_mode) or \
               info.activity_type.name.startswith("test_")
    
    def get_config_value(self, config: MonitorConfig, key: str, default: Any = None) -> Any:
        """Get a configuration value with fallback to default.
        
        Args:
            config: Configuration object
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if hasattr(config, key):
            return getattr(config, key)
        return default
    
    def measure_execution_time(self, start_time: datetime) -> timedelta:
        """Measure execution time from start time.
        
        Args:
            start_time: Start time
            
        Returns:
            Execution duration
        """
        return datetime.utcnow() - start_time
    
    def create_error_response(
        self, 
        error: Exception, 
        activity_name: str,
        **context: Any
    ) -> Dict[str, Any]:
        """Create a standardized error response.
        
        Args:
            error: Error that occurred
            activity_name: Name of the activity
            **context: Additional context
            
        Returns:
            Error response dictionary
        """
        return {
            "success": False,
            "error": {
                "type": type(error).__name__,
                "message": str(error),
                "activity_name": activity_name,
                "activity_id": self.get_activity_info()["activity_id"],
                "timestamp": datetime.utcnow().isoformat(),
                "context": context,
            }
        }
    
    def create_success_response(
        self, 
        data: Any, 
        activity_name: str,
        **context: Any
    ) -> Dict[str, Any]:
        """Create a standardized success response.
        
        Args:
            data: Response data
            activity_name: Name of the activity
            **context: Additional context
            
        Returns:
            Success response dictionary
        """
        return {
            "success": True,
            "data": data,
            "activity_name": activity_name,
            "activity_id": self.get_activity_info()["activity_id"],
            "timestamp": datetime.utcnow().isoformat(),
            "context": context,
        }
