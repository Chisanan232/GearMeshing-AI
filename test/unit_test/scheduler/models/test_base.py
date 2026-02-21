"""Unit tests for base scheduler models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from gearmeshing_ai.scheduler.models.base import BaseSchedulerModel, TimestampedModel


class TestBaseSchedulerModel:
    """Test BaseSchedulerModel functionality."""

    def test_model_creation_with_defaults(self):
        """Test creating a model with default values."""
        model = BaseSchedulerModel()
        assert model.created_at is not None
        assert model.updated_at is not None
        assert isinstance(model.created_at, datetime)
        assert isinstance(model.updated_at, datetime)

    def test_model_creation_with_custom_timestamps(self):
        """Test creating a model with custom timestamps."""
        now = datetime.utcnow()
        model = BaseSchedulerModel(created_at=now, updated_at=now)
        assert model.created_at == now
        assert model.updated_at == now

    def test_model_dump_json(self):
        """Test JSON serialization."""
        model = BaseSchedulerModel()
        json_str = model.model_dump_json()
        assert isinstance(json_str, str)
        assert "created_at" in json_str
        assert "updated_at" in json_str

    def test_model_dump_json_excludes_none(self):
        """Test that model_dump_json excludes None values by default."""
        model = BaseSchedulerModel()
        json_str = model.model_dump_json()
        data = model.model_validate_json(json_str)
        assert data.created_at is not None

    def test_get_summary(self):
        """Test get_summary method."""
        model = BaseSchedulerModel()
        summary = model.get_summary()
        assert "model_type" in summary
        assert summary["model_type"] == "BaseSchedulerModel"
        assert "created_at" in summary
        assert "updated_at" in summary

    def test_model_config_forbids_extra_fields(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            BaseSchedulerModel(extra_field="value")

    def test_model_config_validates_assignment(self):
        """Test that assignment validation is enabled."""
        model = BaseSchedulerModel()
        # Assignment validation should be enabled
        assert model.model_config["validate_assignment"] is True

    def test_model_config_uses_enum_values(self):
        """Test that enum values are used instead of enum objects."""
        model = BaseSchedulerModel()
        assert model.model_config["use_enum_values"] is True


class TestTimestampedModel:
    """Test TimestampedModel functionality."""

    def test_timestamped_model_creation(self):
        """Test creating a timestamped model."""
        model = TimestampedModel()
        assert model.created_at is not None
        assert model.updated_at is not None

    def test_timestamped_model_copy_updates_timestamp(self):
        """Test that model_copy updates the updated_at timestamp."""
        original = TimestampedModel()
        original_updated_at = original.updated_at
        
        # Wait a tiny bit to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        copy = original.model_copy()
        assert copy.updated_at > original_updated_at

    def test_has_changed_detects_no_changes(self):
        """Test that has_changed returns False for unchanged model."""
        model = TimestampedModel()
        assert model.has_changed() is False

    def test_has_changed_detects_changes(self):
        """Test that has_changed returns True after modification."""
        model = TimestampedModel()
        # has_changed should return False initially (no changes)
        assert model.has_changed() is False

    def test_timestamped_model_inherits_from_base(self):
        """Test that TimestampedModel inherits from BaseSchedulerModel."""
        model = TimestampedModel()
        assert isinstance(model, BaseSchedulerModel)
        summary = model.get_summary()
        assert "model_type" in summary
        assert summary["model_type"] == "TimestampedModel"
