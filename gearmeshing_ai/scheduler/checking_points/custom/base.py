from abc import ABC

from gearmeshing_ai.scheduler.checking_points.base import CheckingPoint


class CustomCheckingPoint(CheckingPoint, ABC):
    """Base class for custom checking points."""

    def _can_handle_data_type(self, data_type: str) -> bool:
        """Custom checking points can handle any data type by default."""
        return True
