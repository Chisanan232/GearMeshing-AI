"""Unit tests for metaclass-based auto-registration of checking points."""

import pytest

from gearmeshing_ai.scheduler.checking_points.base import (
    CheckingPoint,
    CheckingPointMeta,
    CheckingPointType,
    ClickUpCheckingPoint,
    CustomCheckingPoint,
    EmailCheckingPoint,
    SlackCheckingPoint,
    get_all_checking_point_classes,
    get_checking_point_class,
    get_checking_point_classes_by_filter,
    get_checking_point_classes_by_type,
    get_checking_point_count,
    get_registry_summary,
    is_checking_point_registered,
)
from gearmeshing_ai.scheduler.checking_points.clickup.overdue_tasks import OverdueTaskCheckingPoint
from gearmeshing_ai.scheduler.checking_points.clickup.urgent_tasks import UrgentTaskCheckingPoint
from gearmeshing_ai.scheduler.checking_points.custom.email_alerts import EmailAlertCheckingPoint
from gearmeshing_ai.scheduler.checking_points.slack.help_requests import HelpRequestCheckingPoint
from gearmeshing_ai.scheduler.models.checking_point import CheckResult
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData


class TestMetaclassAutoRegistration:
    """Test metaclass auto-registration mechanism."""

    def test_metaclass_is_abcmeta_subclass(self):
        """Test that CheckingPointMeta is a subclass of ABCMeta."""
        from abc import ABCMeta

        assert issubclass(CheckingPointMeta, ABCMeta)

    def test_checking_point_uses_metaclass(self):
        """Test that CheckingPoint uses CheckingPointMeta as metaclass."""
        assert type(CheckingPoint) is CheckingPointMeta

    def test_concrete_checking_point_inherits_metaclass(self):
        """Test that concrete checking point classes inherit the metaclass."""
        assert type(UrgentTaskCheckingPoint) is CheckingPointMeta
        assert type(HelpRequestCheckingPoint) is CheckingPointMeta
        assert type(EmailAlertCheckingPoint) is CheckingPointMeta

    def test_new_checking_point_auto_registers(self):
        """Test that a new checking point class auto-registers on creation."""

        # Create a new checking point class
        class TestAutoRegisterCP(CheckingPoint):
            name = "test_auto_register_cp"
            type = CheckingPointType.CUSTOM_CP
            description = "Test auto-registration"

            async def fetch_data(self, **kwargs):
                return []

            async def evaluate(self, data: MonitoringData) -> CheckResult:
                return CheckResult(should_act=False, reason="test", confidence=0.5)

        # Verify it's registered
        assert is_checking_point_registered("test_auto_register_cp")
        assert get_checking_point_class("test_auto_register_cp") == TestAutoRegisterCP

    def test_abstract_class_not_registered(self):
        """Test that abstract checking point classes are not registered."""
        # The base CheckingPoint class should not be registered
        # because it has abstract methods
        all_classes = get_all_checking_point_classes()
        assert CheckingPoint not in all_classes.values()

    def test_base_service_classes_not_registered(self):
        """Test that base service classes (ClickUp, Slack, Email) are not registered."""
        all_classes = get_all_checking_point_classes()
        # These are abstract base classes, not concrete implementations
        assert ClickUpCheckingPoint not in all_classes.values()
        assert SlackCheckingPoint not in all_classes.values()
        assert EmailCheckingPoint not in all_classes.values()
        assert CustomCheckingPoint not in all_classes.values()

    def test_concrete_checking_points_are_registered(self):
        """Test that all concrete checking point implementations are registered."""
        all_classes = get_all_checking_point_classes()

        # ClickUp checking points (registered by their 'name' attribute)
        assert "clickup_urgent_task_cp" in all_classes
        assert "clickup_overdue_task_cp" in all_classes

        # Slack checking points
        assert "slack_help_request_cp" in all_classes

    def test_registered_classes_are_correct_types(self):
        """Test that registered classes are the correct types."""
        all_classes = get_all_checking_point_classes()

        assert all_classes["clickup_urgent_task_cp"] is UrgentTaskCheckingPoint
        assert all_classes["slack_help_request_cp"] is HelpRequestCheckingPoint


class TestRegistryUtilityFunctions:
    """Test registry utility functions."""

    def test_get_checking_point_class_by_name(self):
        """Test retrieving a checking point class by name."""
        cp_class = get_checking_point_class("clickup_urgent_task_cp")
        assert cp_class is UrgentTaskCheckingPoint
        assert cp_class.name == "clickup_urgent_task_cp"

    def test_get_checking_point_class_not_found(self):
        """Test that getting non-existent checking point raises error."""
        with pytest.raises(ValueError, match="not found in registry"):
            get_checking_point_class("NonExistentCP")

    def test_get_all_checking_point_classes(self):
        """Test getting all registered checking point classes."""
        all_classes = get_all_checking_point_classes()

        assert isinstance(all_classes, dict)
        assert len(all_classes) > 0
        # Should contain at least the concrete implementations
        assert "clickup_urgent_task_cp" in all_classes
        assert "slack_help_request_cp" in all_classes

    def test_get_checking_point_classes_by_filter_name(self):
        """Test filtering checking points by name."""
        urgent_cps = get_checking_point_classes_by_filter(name_contains="urgent")
        assert len(urgent_cps) > 0
        assert "clickup_urgent_task_cp" in urgent_cps

    def test_get_checking_point_classes_by_filter_type(self):
        """Test filtering checking points by type."""
        clickup_cps = get_checking_point_classes_by_filter(type_contains="clickup")
        assert len(clickup_cps) > 0
        # Should contain ClickUp checking points
        assert any("urgent" in name or "overdue" in name or "assignment" in name for name in clickup_cps.keys())

    def test_get_checking_point_classes_by_filter_priority(self):
        """Test filtering checking points by priority."""
        high_priority_cps = get_checking_point_classes_by_filter(priority_min=7)
        assert isinstance(high_priority_cps, dict)
        # All returned classes should have priority >= 7
        for cp_class in high_priority_cps.values():
            assert cp_class.priority >= 7

    def test_get_checking_point_classes_by_filter_enabled(self):
        """Test filtering checking points by enabled status."""
        enabled_cps = get_checking_point_classes_by_filter(enabled=True)
        assert isinstance(enabled_cps, dict)
        # All returned classes should be enabled
        for cp_class in enabled_cps.values():
            assert cp_class.enabled is True

    def test_get_checking_point_classes_by_filter_multiple_criteria(self):
        """Test filtering with multiple criteria."""
        filtered = get_checking_point_classes_by_filter(type_contains="clickup", priority_min=5, enabled=True)
        assert isinstance(filtered, dict)
        # All results should match all criteria
        for cp_class in filtered.values():
            assert "clickup" in cp_class.type.value.lower()
            assert cp_class.priority >= 5
            assert cp_class.enabled is True

    def test_get_checking_point_classes_by_type_string(self):
        """Test getting checking points by type (string)."""
        clickup_urgent_cps = get_checking_point_classes_by_type("clickup_urgent_task_cp")
        assert len(clickup_urgent_cps) > 0
        assert "clickup_urgent_task_cp" in clickup_urgent_cps

    def test_get_checking_point_classes_by_type_enum(self):
        """Test getting checking points by type (enum)."""
        slack_help_cps = get_checking_point_classes_by_type(CheckingPointType.SLACK_HELP_REQUEST_CP)
        assert len(slack_help_cps) > 0
        assert "slack_help_request_cp" in slack_help_cps

    def test_get_checking_point_count(self):
        """Test getting total count of registered checking points."""
        count = get_checking_point_count()
        assert isinstance(count, int)
        assert count > 0
        # Should have at least the concrete implementations
        assert count >= 3

    def test_is_checking_point_registered_true(self):
        """Test checking if a registered checking point exists."""
        assert is_checking_point_registered("clickup_urgent_task_cp") is True
        assert is_checking_point_registered("slack_help_request_cp") is True
        assert is_checking_point_registered("clickup_overdue_task_cp") is True

    def test_is_checking_point_registered_false(self):
        """Test checking if an unregistered checking point exists."""
        assert is_checking_point_registered("NonExistentCP") is False
        assert is_checking_point_registered("FakeCP") is False

    def test_get_registry_summary(self):
        """Test getting registry summary."""
        summary = get_registry_summary()

        assert isinstance(summary, dict)
        assert "total_checking_points" in summary
        assert "type_counts" in summary
        assert "checking_points" in summary

        # Verify structure
        assert isinstance(summary["total_checking_points"], int)
        assert isinstance(summary["type_counts"], dict)
        assert isinstance(summary["checking_points"], dict)

        # Verify content
        assert summary["total_checking_points"] > 0
        assert len(summary["type_counts"]) > 0
        assert len(summary["checking_points"]) > 0

    def test_registry_summary_checking_point_details(self):
        """Test that registry summary includes correct checking point details."""
        summary = get_registry_summary()
        checking_points = summary["checking_points"]

        # Verify a known checking point is in the summary
        assert "clickup_urgent_task_cp" in checking_points

        urgent_cp_info = checking_points["clickup_urgent_task_cp"]
        assert urgent_cp_info["name"] == "clickup_urgent_task_cp"
        assert "clickup" in urgent_cp_info["type"].lower()
        assert "description" in urgent_cp_info
        assert "version" in urgent_cp_info
        assert "priority" in urgent_cp_info
        assert "enabled" in urgent_cp_info


class TestRegistryWithConcreteCheckingPoints:
    """Test registry with actual concrete checking point classes."""

    def test_urgent_task_checking_point_registered(self):
        """Test that UrgentTaskCheckingPoint is registered."""
        assert is_checking_point_registered("clickup_urgent_task_cp")
        cp_class = get_checking_point_class("clickup_urgent_task_cp")
        assert cp_class is UrgentTaskCheckingPoint
        assert cp_class.type == CheckingPointType.CLICKUP_URGENT_TASK_CP

    def test_overdue_task_checking_point_registered(self):
        """Test that OverdueTaskCheckingPoint is registered."""
        assert is_checking_point_registered("clickup_overdue_task_cp")
        cp_class = get_checking_point_class("clickup_overdue_task_cp")
        assert cp_class is OverdueTaskCheckingPoint
        assert cp_class.type == CheckingPointType.CLICKUP_OVERDUE_TASK_CP

    def test_help_request_checking_point_registered(self):
        """Test that HelpRequestCheckingPoint is registered."""
        assert is_checking_point_registered("slack_help_request_cp")
        cp_class = get_checking_point_class("slack_help_request_cp")
        assert cp_class is HelpRequestCheckingPoint
        assert cp_class.type == CheckingPointType.SLACK_HELP_REQUEST_CP

    def test_all_clickup_checking_points_registered(self):
        """Test that all ClickUp checking points are registered."""
        clickup_cps = get_checking_point_classes_by_type(CheckingPointType.CLICKUP_URGENT_TASK_CP)
        assert len(clickup_cps) > 0

        clickup_overdue = get_checking_point_classes_by_type(CheckingPointType.CLICKUP_OVERDUE_TASK_CP)
        assert len(clickup_overdue) > 0

    def test_all_slack_checking_points_registered(self):
        """Test that all Slack checking points are registered."""
        slack_help = get_checking_point_classes_by_type(CheckingPointType.SLACK_HELP_REQUEST_CP)
        assert len(slack_help) > 0

    def test_instantiate_registered_checking_point(self):
        """Test that registered checking points can be instantiated."""
        cp_class = get_checking_point_class("clickup_urgent_task_cp")
        cp_instance = cp_class()

        assert isinstance(cp_instance, CheckingPoint)
        assert isinstance(cp_instance, ClickUpCheckingPoint)
        assert cp_instance.name == "clickup_urgent_task_cp"

    def test_instantiate_with_config(self):
        """Test that registered checking points can be instantiated with config."""
        cp_class = get_checking_point_class("slack_help_request_cp")
        config = {"enabled": False, "priority": 8}
        cp_instance = cp_class(config=config)

        assert cp_instance.enabled is False
        assert cp_instance.priority == 8


class TestRegistryIntegration:
    """Integration tests for registry consistency and immutability."""

    def test_registry_consistency(self):
        """Test that registry is consistent across multiple calls."""
        count1 = get_checking_point_count()
        all_classes1 = get_all_checking_point_classes()

        count2 = get_checking_point_count()
        all_classes2 = get_all_checking_point_classes()

        # Registry should be consistent
        assert count1 == count2
        assert len(all_classes1) == len(all_classes2)
        assert all_classes1.keys() == all_classes2.keys()

    def test_registry_immutability(self):
        """Test that returned registry copy doesn't affect original."""
        all_classes = get_all_checking_point_classes()
        original_count = len(all_classes)

        # Modify the returned copy
        all_classes["FakeCP"] = None

        # Original registry should be unchanged
        all_classes_again = get_all_checking_point_classes()
        assert len(all_classes_again) == original_count
        assert "FakeCP" not in all_classes_again

    def test_instantiate_and_verify_type(self):
        """Test that instantiated checking points are correct types."""
        cp_class = get_checking_point_class("clickup_urgent_task_cp")
        cp_instance = cp_class()

        assert isinstance(cp_instance, CheckingPoint)
        assert isinstance(cp_instance, ClickUpCheckingPoint)
        assert cp_instance.name == "clickup_urgent_task_cp"
        assert hasattr(cp_instance, "fetch_data")
        assert hasattr(cp_instance, "evaluate")

    def test_instantiate_slack_checking_point(self):
        """Test that Slack checking points can be instantiated."""
        cp_class = get_checking_point_class("slack_help_request_cp")
        cp_instance = cp_class()

        assert isinstance(cp_instance, CheckingPoint)
        assert isinstance(cp_instance, SlackCheckingPoint)
        assert cp_instance.name == "slack_help_request_cp"
        assert hasattr(cp_instance, "fetch_data")
        assert hasattr(cp_instance, "evaluate")
