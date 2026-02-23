from gearmeshing_ai.scheduler.checking_points.base import (
    CheckingPoint,
    CheckingPointType,
)
from gearmeshing_ai.scheduler.checking_points.custom.base import CustomCheckingPoint
from gearmeshing_ai.scheduler.models.checking_point import CheckResult
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType


class TestCustomCheckingPoint:
    """Test CustomCheckingPoint base class."""

    class ConcreteCustomCP(CustomCheckingPoint):
        """Concrete custom checking point for testing."""

        name = "custom_test"
        type = CheckingPointType.CUSTOM_CP

        async def fetch_data(self, **kwargs) -> list[MonitoringData]:
            """Fetch test custom data."""
            return [
                MonitoringData(
                    id="test_1",
                    type=MonitoringDataType.CUSTOM_DATA,
                    source="test",
                    data={"test": "data"},
                )
            ]

        async def evaluate(self, data: MonitoringData) -> CheckResult:
            return CheckResult(should_act=True, reason="test", confidence=0.9)

    def test_can_handle_any_data_type(self):
        """Test that custom checking point can handle any data type."""
        cp = self.ConcreteCustomCP()

        # Test with different data types
        for data_type in MonitoringDataType.get_all_values():
            data = MonitoringData(id="test_1", type=MonitoringDataType(data_type), source="test")
            assert cp._can_handle_data_type(data.type) is True
