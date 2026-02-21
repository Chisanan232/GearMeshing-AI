"""Configuration loader utilities.

This module provides utilities for loading scheduler configuration from various
sources, including YAML files, environment variables, and command-line arguments.
"""

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from gearmeshing_ai.scheduler.config.settings import SchedulerSettings
from gearmeshing_ai.scheduler.models.config import MonitorConfig, SchedulerConfig


class ConfigurationLoader:
    """Loader for scheduler configuration from various sources.

    This class handles loading configuration from YAML files, environment
    variables, and command-line arguments with proper validation and merging.
    """

    def __init__(self) -> None:
        """Initialize the configuration loader."""
        pass

    def load_from_file(self, file_path: str | Path) -> SchedulerConfig:
        """Load scheduler configuration from a YAML file.

        Args:
            file_path: Path to the configuration file

        Returns:
            Loaded scheduler configuration

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid

        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            return self._parse_scheduler_config(data)

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format in {file_path}: {e!s}")
        except Exception as e:
            raise ValueError(f"Error reading file {file_path}: {e!s}")

    def load_from_dict(self, config_dict: dict[str, Any]) -> SchedulerConfig:
        """Load scheduler configuration from a dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            Loaded scheduler configuration

        Raises:
            ValueError: If configuration is invalid

        """
        return self._parse_scheduler_config(config_dict)

    def load_monitoring_config_from_file(self, file_path: str | Path) -> MonitorConfig:
        """Load monitoring configuration from a YAML file.

        Args:
            file_path: Path to the monitoring configuration file

        Returns:
            Loaded monitoring configuration

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid

        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Monitoring configuration file not found: {file_path}")

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            return self._parse_monitoring_config(data)

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format in {file_path}: {e!s}")
        except Exception as e:
            raise ValueError(f"Error reading file {file_path}: {e!s}")

    def load_monitoring_config_from_dict(self, config_dict: dict[str, Any]) -> MonitorConfig:
        """Load monitoring configuration from a dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            Loaded monitoring configuration

        Raises:
            ValueError: If configuration is invalid

        """
        return self._parse_monitoring_config(config_dict)

    def load_scheduler_settings(self) -> SchedulerSettings:
        """Load scheduler settings from environment variables.

        Returns:
            Scheduler settings instance

        """
        return SchedulerSettings()

    def merge_configs(self, base_config: dict[str, Any], override_config: dict[str, Any]) -> dict[str, Any]:
        """Merge two configuration dictionaries.

        Args:
            base_config: Base configuration
            override_config: Override configuration

        Returns:
            Merged configuration

        """
        merged = base_config.copy()

        def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
            """Deep merge two dictionaries."""
            result = base.copy()

            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value

            return result

        return deep_merge(merged, override_config)

    def validate_config_file(self, file_path: str | Path) -> list[str]:
        """Validate a configuration file without loading it.

        Args:
            file_path: Path to the configuration file

        Returns:
            List of validation errors

        """
        errors = []

        try:
            self.load_from_file(file_path)
        except ValidationError as e:
            errors.extend([f"Validation error: {e!s}"])
        except Exception as e:
            errors.append(f"File validation error: {e!s}")

        return errors

    def generate_sample_config(self) -> SchedulerConfig:
        """Generate a sample configuration.

        Returns:
            Sample scheduler configuration

        """
        return SchedulerConfig(
            name="sample-scheduler",
            description="Sample scheduler configuration",
        )

    def generate_sample_monitoring_config(self) -> MonitorConfig:
        """Generate a sample monitoring configuration.

        Returns:
            Sample monitoring configuration

        """
        return MonitorConfig(
            name="sample-monitoring",
            description="Sample monitoring configuration",
            interval_seconds=300,
            enabled=True,
            checking_points=[
                {
                    "type": "clickup_urgent_task_cp",
                    "enabled": True,
                    "config": {
                        "urgent_keywords": ["urgent", "critical", "emergency"],
                        "priority_levels": ["urgent", "high"],
                        "due_date_threshold_hours": 24,
                    },
                },
                {
                    "type": "clickup_overdue_task_cp",
                    "enabled": True,
                    "config": {
                        "overdue_threshold_days": 1,
                        "critical_threshold_days": 7,
                    },
                },
                {
                    "type": "slack_help_request_cp",
                    "enabled": True,
                    "config": {
                        "channels": ["#general", "#support"],
                    },
                },
            ],
        )

    def export_config_to_yaml(self, config: SchedulerConfig | MonitorConfig, file_path: str | Path) -> None:
        """Export configuration to a YAML file.

        Args:
            config: Configuration to export
            file_path: Path to save the YAML file

        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        config_dict = config.model_dump(exclude_none=True, by_alias=True)

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

    def export_config_to_json(self, config: SchedulerConfig | MonitorConfig, file_path: str | Path) -> None:
        """Export configuration to a JSON file.

        Args:
            config: Configuration to export
            file_path: Path to save the JSON file

        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        config_dict = config.model_dump(exclude_none=True, by_alias=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)

    def _parse_scheduler_config(self, data: dict[str, Any]) -> SchedulerConfig:
        """Parse scheduler configuration from dictionary.

        Args:
            data: Configuration data

        Returns:
            SchedulerConfig instance

        Raises:
            ValueError: If configuration is invalid

        """
        try:
            return SchedulerConfig(**data)
        except ValidationError as e:
            raise ValueError(f"Invalid scheduler configuration: {e!s}")
        except Exception as e:
            raise ValueError(f"Error parsing scheduler configuration: {e!s}")

    def _parse_monitoring_config(self, data: dict[str, Any]) -> MonitorConfig:
        """Parse monitoring configuration from dictionary.

        Args:
            data: Configuration data

        Returns:
            MonitorConfig instance

        Raises:
            ValueError: If configuration is invalid

        """
        try:
            return MonitorConfig(**data)
        except ValidationError as e:
            raise ValueError(f"Invalid monitoring configuration: {e!s}")
        except Exception as e:
            raise ValueError(f"Error parsing monitoring configuration: {e!s}")

    def get_config_summary(self, config: SchedulerConfig | MonitorConfig) -> dict[str, Any]:
        """Get a summary of a configuration.

        Args:
            config: Configuration to summarize

        Returns:
            Configuration summary

        """
        if isinstance(config, SchedulerConfig):
            return {
                "type": "scheduler",
                "name": config.name,
                "description": config.description,
                "environment": config.environment,
                "debug": config.debug,
                "temporal": {
                    "host": config.temporal.host,
                    "port": config.temporal.port,
                    "namespace": config.temporal.namespace,
                    "task_queue": config.temporal.task_queue,
                    "worker_count": config.temporal.worker_count,
                },
                "monitoring": {
                    "enabled": config.monitoring.enabled,
                    "interval_seconds": config.monitoring.interval_seconds,
                    "max_concurrent_checks": config.monitoring.max_concurrent_checks,
                },
                "api": {
                    "enabled": config.enable_api,
                    "host": config.api_host,
                    "port": config.api_port,
                },
                "metrics": {
                    "enabled": config.enable_metrics,
                    "port": config.metrics_port,
                },
            }
        if isinstance(config, MonitorConfig):
            return {
                "type": "monitoring",
                "name": config.name,
                "description": config.description,
                "interval_seconds": config.interval_seconds,
                "enabled": config.enabled,
                "checking_points_count": len(config.checking_points),
                "enabled_checking_points": len(config.get_enabled_checking_points()),
                "max_concurrent_evaluations": config.max_concurrent_evaluations,
                "evaluation_timeout_seconds": config.evaluation_timeout_seconds,
                "data_sources_count": len(config.data_sources),
            }
        raise ValueError(f"Unknown configuration type: {type(config)}")

    def find_config_files(self, search_dir: str | Path, pattern: str = "*.yaml") -> list[Path]:
        """Find configuration files in a directory.

        Args:
            search_dir: Directory to search
            pattern: File pattern to match

        Returns:
            List of found configuration files

        """
        path = Path(search_dir)

        if not path.exists() or not path.is_dir():
            return []

        return list(path.glob(pattern))

    def load_all_configs_from_dir(self, search_dir: str | Path) -> dict[str, SchedulerConfig | MonitorConfig]:
        """Load all configuration files from a directory.

        Args:
            search_dir: Directory to search

        Returns:
            Dictionary mapping file names to loaded configurations

        """
        configs = {}
        config_files = self.find_config_files(search_dir)

        for config_file in config_files:
            try:
                # Try to load as scheduler config first
                if "scheduler" in config_file.name.lower():
                    config = self.load_from_file(config_file)
                else:
                    config = self.load_monitoring_config_from_file(config_file)

                configs[config_file.name] = config

            except Exception as e:
                # Skip files that can't be loaded
                continue

        return configs
