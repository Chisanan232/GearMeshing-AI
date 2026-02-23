"""
Data fetching activities for the scheduler system.

This module contains activities for fetching data from external systems
and evaluating checking points against monitoring data.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Union

from temporalio import activity

from gearmeshing_ai.scheduler.models.config import MonitorConfig
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType
from gearmeshing_ai.scheduler.models.checking_point import CheckResult, CheckResultType
from gearmeshing_ai.scheduler.checking_points.base import (
    CheckingPoint,
    get_checking_point_class,
    get_all_checking_point_classes,
)
from gearmeshing_ai.scheduler.activities.base import BaseActivity


class DataFetchingActivity(BaseActivity):
    """Activity for fetching monitoring data from external systems."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.name = "data_fetching_activity"
        self.description = "Fetches monitoring data from external sources"
        self.version = "1.0.0"
        self.timeout_seconds = 300
    
    async def fetch_data(self, config: MonitorConfig) -> List[MonitoringData]:
        """Fetch data using decentralized checking point data fetching.
        
        This method uses the new Bridge Pattern approach where each checking point
        is responsible for fetching its own relevant data using the parent's client
        and utility methods. This replaces the old centralized data fetching logic.
        
        Args:
            config: Monitoring configuration
            
        Returns:
            List of monitoring data items
        """
        self.log_activity_start("fetch_data", config_name=config.name)
        
        start_time = datetime.utcnow()
        data_items = []
        
        try:
            # Iterate through checking points and use their data fetching capabilities
            enabled_checking_points = config.get_enabled_checking_points()
            
            for checking_point_config in enabled_checking_points:
                cp_type = checking_point_config.get("type")
                cp_config = checking_point_config.get("config", {})
                
                try:
                    # Get checking point instance
                    checking_point = self._get_checking_point_instance(cp_type, cp_config)
                    
                    # Use checking point's decentralized data fetching capability
                    if hasattr(checking_point, 'fetch_data') and callable(getattr(checking_point, 'fetch_data')):
                        fetched_data = await checking_point.fetch_data(**cp_config)
                        data_items.extend(fetched_data)
                        
                        self.logger.debug(
                            f"Fetched {len(fetched_data)} items from {cp_type}",
                            extra={"checking_point_type": cp_type, "item_count": len(fetched_data)}
                        )
                except Exception as cp_error:
                    self.logger.warning(
                        f"Error fetching data from {cp_type}: {str(cp_error)}",
                        extra={"checking_point_type": cp_type, "error": str(cp_error)}
                    )
                    # Continue with other checking points even if one fails
                    continue
            
            execution_time = self.measure_execution_time(start_time)
            
            self.log_activity_complete(
                "fetch_data",
                data_items_count=len(data_items),
                execution_time_ms=int(execution_time.total_seconds() * 1000),
                data_types=list(set(item.type.value for item in data_items)),
            )
            
            return data_items
            
        except Exception as e:
            self.log_activity_error("fetch_data", e, config_name=config.name)
            raise
    
    def _get_checking_point_instance(self, cp_type: str, cp_config: Dict[str, Any]) -> CheckingPoint:
        """Get a checking point instance by name using the metaclass-based registry.
        
        This method instantiates the appropriate checking point class based on the name
        by looking it up in the global checking point registry. The registry is populated
        automatically via the CheckingPointMeta metaclass when checking point classes
        are defined and imported.
        
        Args:
            cp_type: Checking point name identifier
            cp_config: Configuration for the checking point
            
        Returns:
            Initialized checking point instance
            
        Raises:
            ValueError: If checking point name is not registered
        """
        # Get the checking point class from the metaclass-based registry
        cp_class = get_checking_point_class(cp_type)
        
        # Instantiate and return the checking point with its configuration
        return cp_class(config=cp_config)


# Keep the original activity functions for Temporal workflow compatibility
@activity.defn
async def fetch_monitoring_data(config: MonitorConfig) -> List[MonitoringData]:
    """Fetch data from all configured external systems."""
    activity_instance = DataFetchingActivity()
    return await activity_instance.fetch_data(config)


@activity.defn
async def evaluate_checking_point(
    checking_point: CheckingPoint, 
    data: MonitoringData
) -> CheckResult:
    """Evaluate a checking point against monitoring data.
    
    This activity evaluates a checking point against monitoring data,
    returning a check result indicating whether the checking point matched.
    
    Args:
        checking_point: Checking point to evaluate
        data: Monitoring data to evaluate against
        
    Returns:
        Check result
    """
    base = BaseActivity()
    base.log_activity_start(
        "evaluate_checking_point",
        checking_point_name=checking_point.name,
        checking_point_type=checking_point.type.value,
        data_item_id=data.id,
        data_item_type=data.type.value,
    )
    
    start_time = datetime.utcnow()
    
    try:
        # Check if the checking point can handle this data
        if not checking_point.can_handle(data):
            result = CheckResult(
                checking_point_name=checking_point.name,
                checking_point_type=checking_point.type.value,
                result_type=CheckResultType.SKIP,
                should_act=False,
                reason=f"Checking point cannot handle data type: {data.type.value}",
                confidence=0.0,
            )
        else:
            # Evaluate the checking point
            result = await checking_point.evaluate(data)
            
            # Ensure result has required fields
            if not hasattr(result, 'checking_point_name'):
                result.checking_point_name = checking_point.name
            if not hasattr(result, 'checking_point_type'):
                result.checking_point_type = checking_point.type.value
        
        # Set evaluation duration
        execution_time = base.measure_execution_time(start_time)
        result.evaluation_duration_ms = int(execution_time.total_seconds() * 1000)
        
        base.log_activity_complete(
            "evaluate_checking_point",
            checking_point_name=checking_point.name,
            data_item_id=data.id,
            result_type=result.result_type.value,
            should_act=result.should_act,
            confidence=result.confidence,
            execution_time_ms=result.evaluation_duration_ms,
        )
        
        return result
        
    except Exception as e:
        base.log_activity_error(
            "evaluate_checking_point",
            e,
            checking_point_name=checking_point.name,
            data_item_id=data.id,
        )
        
        # Return error result
        return CheckResult(
            checking_point_name=checking_point.name,
            checking_point_type=checking_point.type.value,
            result_type=CheckResultType.ERROR,
            should_act=False,
            confidence=0.0,
            error_message=str(e),
        )


