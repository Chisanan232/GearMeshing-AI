"""Unit tests for checking point registry."""

import pytest
from unittest.mock import Mock

from gearmeshing_ai.scheduler.checking_points.registry import (
    CheckingPointRegistry,
    register_checking_point,
    get_checking_point,
    get_all_checking_points,
    get_checking_points_by_type,
)
from gearmeshing_ai.scheduler.checking_points.base import CheckingPoint, CheckingPointType
from gearmeshing_ai.scheduler.models.monitoring import MonitoringData, MonitoringDataType
from gearmeshing_ai.scheduler.models.checking_point import CheckResult


class MockCheckingPoint(CheckingPoint):
    """Mock checking point for testing."""
    name = "mock_cp"
    type = CheckingPointType.CUSTOM_CP
    
    async def evaluate(self, data: MonitoringData) -> CheckResult:
        return CheckResult(should_act=True, reason="test", confidence=0.9)


class AnotherMockCP(CheckingPoint):
    """Another mock checking point for testing."""
    name = "another_mock_cp"
    type = CheckingPointType.CLICKUP_URGENT_TASK_CP
    
    async def evaluate(self, data: MonitoringData) -> CheckResult:
        return CheckResult(should_act=False, reason="no match", confidence=0.1)


class TestCheckingPointRegistry:
    """Test CheckingPointRegistry class."""

    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = CheckingPointRegistry()
        assert len(registry.get_all_classes()) == 0
        assert len(registry.get_all_instances()) == 0

    def test_register_checking_point(self):
        """Test registering a checking point."""
        registry = CheckingPointRegistry()
        registry.register(MockCheckingPoint)
        
        assert "mock_cp" in registry.get_all_classes()
        assert registry.get_class("mock_cp") == MockCheckingPoint

    def test_register_duplicate_raises_error(self):
        """Test that registering duplicate checking point raises error."""
        registry = CheckingPointRegistry()
        registry.register(MockCheckingPoint)
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register(MockCheckingPoint)

    def test_register_non_class_raises_error(self):
        """Test that registering non-class raises error."""
        registry = CheckingPointRegistry()
        
        with pytest.raises(ValueError, match="must be a class"):
            registry.register("not a class")

    def test_register_non_checking_point_raises_error(self):
        """Test that registering non-CheckingPoint class raises error."""
        registry = CheckingPointRegistry()
        
        class NotACheckingPoint:
            pass
        
        with pytest.raises(ValueError, match="must inherit from CheckingPoint"):
            registry.register(NotACheckingPoint)

    def test_register_without_name_raises_error(self):
        """Test that registering checking point without name raises error."""
        registry = CheckingPointRegistry()
        
        class NoNameCP(CheckingPoint):
            type = CheckingPointType.CUSTOM_CP
            async def evaluate(self, data):
                pass
        
        with pytest.raises(ValueError, match="must have a 'name' attribute"):
            registry.register(NoNameCP)

    def test_unregister_checking_point(self):
        """Test unregistering a checking point."""
        registry = CheckingPointRegistry()
        registry.register(MockCheckingPoint)
        
        assert "mock_cp" in registry.get_all_classes()
        registry.unregister("mock_cp")
        assert "mock_cp" not in registry.get_all_classes()

    def test_unregister_nonexistent_raises_error(self):
        """Test that unregistering nonexistent checking point raises error."""
        registry = CheckingPointRegistry()
        
        with pytest.raises(KeyError):
            registry.unregister("nonexistent")

    def test_get_instance(self):
        """Test getting a checking point instance."""
        registry = CheckingPointRegistry()
        registry.register(MockCheckingPoint)
        
        instance = registry.get_instance("mock_cp")
        assert instance is not None
        assert isinstance(instance, MockCheckingPoint)

    def test_get_instance_with_config(self):
        """Test getting a checking point instance with config."""
        registry = CheckingPointRegistry()
        registry.register(MockCheckingPoint)
        
        config = {"enabled": False, "priority": 8}
        instance = registry.get_instance("mock_cp", config)
        assert instance is not None
        assert instance.enabled is False
        assert instance.priority == 8

    def test_get_instance_caches_without_config(self):
        """Test that instances are cached when no config provided."""
        registry = CheckingPointRegistry()
        registry.register(MockCheckingPoint)
        
        instance1 = registry.get_instance("mock_cp")
        instance2 = registry.get_instance("mock_cp")
        assert instance1 is instance2

    def test_get_instance_nonexistent_returns_none(self):
        """Test that getting nonexistent instance returns None."""
        registry = CheckingPointRegistry()
        
        instance = registry.get_instance("nonexistent")
        assert instance is None

    def test_get_all_classes(self):
        """Test getting all registered classes."""
        registry = CheckingPointRegistry()
        registry.register(MockCheckingPoint)
        registry.register(AnotherMockCP)
        
        classes = registry.get_all_classes()
        assert len(classes) == 2
        assert "mock_cp" in classes
        assert "another_mock_cp" in classes

    def test_get_all_instances(self):
        """Test getting all instances."""
        registry = CheckingPointRegistry()
        registry.register(MockCheckingPoint)
        registry.register(AnotherMockCP)
        
        instances = registry.get_all_instances()
        assert len(instances) == 2
        assert "mock_cp" in instances
        assert "another_mock_cp" in instances

    def test_get_by_type(self):
        """Test getting checking points by type."""
        registry = CheckingPointRegistry()
        registry.register(MockCheckingPoint)
        registry.register(AnotherMockCP)
        
        custom_cps = registry.get_by_type(CheckingPointType.CUSTOM_CP)
        assert "mock_cp" in custom_cps
        
        clickup_cps = registry.get_by_type(CheckingPointType.CLICKUP_URGENT_TASK_CP)
        assert "another_mock_cp" in clickup_cps

    def test_get_enabled_instances(self):
        """Test getting only enabled instances."""
        registry = CheckingPointRegistry()
        registry.register(MockCheckingPoint)
        registry.register(AnotherMockCP)
        
        configs = {
            "mock_cp": {"enabled": True},
            "another_mock_cp": {"enabled": False}
        }
        
        enabled = registry.get_enabled_instances(configs)
        assert "mock_cp" in enabled
        assert "another_mock_cp" not in enabled

    def test_validate_all(self):
        """Test validating all checking points."""
        registry = CheckingPointRegistry()
        registry.register(MockCheckingPoint)
        
        errors = registry.validate_all()
        assert len(errors) == 0

    def test_get_summary(self):
        """Test getting registry summary."""
        registry = CheckingPointRegistry()
        registry.register(MockCheckingPoint)
        registry.register(AnotherMockCP)
        
        summary = registry.get_summary()
        assert summary["total_checking_points"] == 2
        assert "checking_points" in summary
        assert "mock_cp" in summary["checking_points"]

    def test_initialize_without_auto_discover(self):
        """Test initializing registry without auto-discovery."""
        registry = CheckingPointRegistry()
        registry.initialize()
        assert registry._initialized is True

    def test_initialize_idempotent(self):
        """Test that initialize is idempotent."""
        registry = CheckingPointRegistry()
        registry.initialize()
        registry.initialize()  # Should not raise
        assert registry._initialized is True


class TestRegisterDecorator:
    """Test register_checking_point decorator."""

    def test_decorator_registers_class(self):
        """Test that decorator registers the class."""
        @register_checking_point
        class DecoratedCP(CheckingPoint):
            name = "decorated_cp"
            type = CheckingPointType.CUSTOM_CP
            
            async def evaluate(self, data):
                pass
        
        # The decorator should have registered it in the global registry
        assert DecoratedCP.name == "decorated_cp"

    def test_decorator_returns_class(self):
        """Test that decorator returns the class unchanged."""
        @register_checking_point
        class DecoratedCP2(CheckingPoint):
            name = "decorated_cp_2"
            type = CheckingPointType.CUSTOM_CP
            
            async def evaluate(self, data):
                from gearmeshing_ai.scheduler.models.checking_point import CheckResult, CheckResultType
                return CheckResult(
                    checking_point_name="decorated_cp_2",
                    checking_point_type="custom_cp",
                    result_type=CheckResultType.NO_MATCH,
                    should_act=False
                )
        
        assert issubclass(DecoratedCP2, CheckingPoint)


class TestRegistryHelperFunctions:
    """Test registry helper functions."""

    def test_get_checking_point_function(self):
        """Test get_checking_point helper function."""
        registry = CheckingPointRegistry()
        registry.register(MockCheckingPoint)
        
        # Note: These functions use the global registry
        # We're testing the function signatures here
        assert callable(get_checking_point)

    def test_get_all_checking_points_function(self):
        """Test get_all_checking_points helper function."""
        assert callable(get_all_checking_points)

    def test_get_checking_points_by_type_function(self):
        """Test get_checking_points_by_type helper function."""
        assert callable(get_checking_points_by_type)
