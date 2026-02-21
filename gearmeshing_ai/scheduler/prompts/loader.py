"""Prompt template loader utilities.

This module provides utilities for loading prompt templates from YAML files,
with support for validation and error handling.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PromptTemplate:
    """Prompt template data structure.

    This class represents a prompt template with its metadata, content,
    and configuration for use in AI workflows.
    """

    template_id: str
    name: str
    description: str
    version: str
    template: str
    variables_schema: dict[str, str]
    agent_role: str | None = None
    timeout_seconds: int = 600
    approval_timeout_seconds: int = 3600
    tags: list[str] = None
    author: str = "System"
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self):
        """Initialize default values for list fields."""
        if self.tags is None:
            self.tags = []


class PromptTemplateLoader:
    """Loader for prompt templates from YAML files.

    This class handles loading prompt templates from YAML files with proper
    validation and error handling.
    """

    def __init__(self) -> None:
        """Initialize the loader."""
        pass

    def load_from_yaml(self, file_path: str) -> list[PromptTemplate]:
        """Load prompt templates from a YAML file.

        Args:
            file_path: Path to the YAML file

        Returns:
            List of loaded prompt templates

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid

        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Prompt template file not found: {file_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        try:
            with open(path, encoding="utf-8") as f:
                yaml_content = f.read()

            return self.load_from_yaml_string(yaml_content)

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format in {file_path}: {e!s}")
        except Exception as e:
            raise ValueError(f"Error reading file {file_path}: {e!s}")

    def load_from_yaml_string(self, yaml_content: str) -> list[PromptTemplate]:
        """Load prompt templates from a YAML string.

        Args:
            yaml_content: YAML content as string

        Returns:
            List of loaded prompt templates

        Raises:
            ValueError: If YAML format is invalid

        """
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e!s}")

        if not isinstance(data, dict) or "prompt_templates" not in data:
            raise ValueError("YAML must contain 'prompt_templates' key with list of templates")

        templates_data = data["prompt_templates"]

        if not isinstance(templates_data, list):
            raise ValueError("'prompt_templates' must be a list")

        templates = []

        for i, template_data in enumerate(templates_data):
            try:
                template = self._parse_template_data(template_data)
                templates.append(template)
            except Exception as e:
                raise ValueError(f"Error parsing template at index {i}: {e!s}")

        return templates

    def _parse_template_data(self, template_data: dict[str, Any]) -> PromptTemplate:
        """Parse template data into a PromptTemplate object.

        Args:
            template_data: Template data dictionary

        Returns:
            PromptTemplate object

        Raises:
            ValueError: If template data is invalid

        """
        # Required fields
        required_fields = ["template_id", "name", "description", "version", "template"]
        for field in required_fields:
            if field not in template_data:
                raise ValueError(f"Missing required field: {field}")

        # Parse timestamps
        created_at = None
        updated_at = None

        if "created_at" in template_data:
            created_at = self._parse_datetime(template_data["created_at"])

        if "updated_at" in template_data:
            updated_at = self._parse_datetime(template_data["updated_at"])

        # Parse variables schema
        variables_schema = template_data.get("variables_schema", {})
        if not isinstance(variables_schema, dict):
            raise ValueError("variables_schema must be a dictionary")

        # Parse tags
        tags = template_data.get("tags", [])
        if not isinstance(tags, list):
            raise ValueError("tags must be a list")

        # Create template object
        template = PromptTemplate(
            template_id=template_data["template_id"],
            name=template_data["name"],
            description=template_data["description"],
            version=template_data["version"],
            template=template_data["template"],
            variables_schema=variables_schema,
            agent_role=template_data.get("agent_role"),
            timeout_seconds=template_data.get("timeout_seconds", 600),
            approval_timeout_seconds=template_data.get("approval_timeout_seconds", 3600),
            tags=tags,
            author=template_data.get("author", "System"),
            created_at=created_at,
            updated_at=updated_at,
        )

        return template

    def _parse_datetime(self, datetime_str: str) -> datetime:
        """Parse datetime string into datetime object.

        Args:
            datetime_str: Datetime string

        Returns:
            Datetime object

        Raises:
            ValueError: If datetime format is invalid

        """
        try:
            # Try ISO format first
            return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        except ValueError:
            # Try other common formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(datetime_str, fmt)
                except ValueError:
                    continue

            raise ValueError(f"Invalid datetime format: {datetime_str}")

    def validate_template_file(self, file_path: str) -> list[str]:
        """Validate a template file without loading it.

        Args:
            file_path: Path to the template file

        Returns:
            List of validation errors

        """
        errors = []

        try:
            templates = self.load_from_yaml(file_path)

            # Validate each template
            for template in templates:
                template_errors = self._validate_template(template)
                errors.extend([f"Template {template.template_id}: {error}" for error in template_errors])

        except Exception as e:
            errors.append(f"File validation error: {e!s}")

        return errors

    def _validate_template(self, template: PromptTemplate) -> list[str]:
        """Validate a single template.

        Args:
            template: Template to validate

        Returns:
            List of validation errors

        """
        errors = []

        # Validate template ID format
        if not template.template_id or not isinstance(template.template_id, str):
            errors.append("Template ID must be a non-empty string")
        elif not template.template_id.replace("_", "").replace("-", "").isalnum():
            errors.append("Template ID should contain only alphanumeric characters, hyphens, and underscores")

        # Validate name
        if not template.name or not isinstance(template.name, str):
            errors.append("Template name must be a non-empty string")

        # Validate description
        if not template.description or not isinstance(template.description, str):
            errors.append("Template description must be a non-empty string")

        # Validate version
        if not template.version or not isinstance(template.version, str):
            errors.append("Template version must be a non-empty string")

        # Validate template content
        if not template.template or not isinstance(template.template, str):
            errors.append("Template content must be a non-empty string")

        # Validate variables schema
        if not isinstance(template.variables_schema, dict):
            errors.append("Variables schema must be a dictionary")
        else:
            for var_name, var_type in template.variables_schema.items():
                if not isinstance(var_name, str) or not var_name:
                    errors.append(f"Variable name must be a non-empty string: {var_name}")

                valid_types = ["string", "number", "boolean", "array", "object"]
                if var_type not in valid_types:
                    errors.append(
                        f"Invalid variable type '{var_type}' for variable '{var_name}'. Valid types: {valid_types}"
                    )

        # Validate timeout
        if not isinstance(template.timeout_seconds, int) or template.timeout_seconds <= 0:
            errors.append("Timeout seconds must be a positive integer")

        # Validate approval timeout
        if not isinstance(template.approval_timeout_seconds, int) or template.approval_timeout_seconds <= 0:
            errors.append("Approval timeout seconds must be a positive integer")

        # Validate tags
        if not isinstance(template.tags, list):
            errors.append("Tags must be a list")
        else:
            for tag in template.tags:
                if not isinstance(tag, str) or not tag:
                    errors.append(f"Tag must be a non-empty string: {tag}")

        # Check for template variables in content
        template_vars = self._extract_template_variables(template.template)
        schema_vars = set(template.variables_schema.keys())

        # Check for variables in template that aren't in schema
        undefined_vars = template_vars - schema_vars
        if undefined_vars:
            errors.append(f"Template contains variables not defined in schema: {', '.join(undefined_vars)}")

        # Check for variables in schema that aren't used in template
        unused_vars = schema_vars - template_vars
        if unused_vars:
            errors.append(f"Schema defines variables not used in template: {', '.join(unused_vars)}")

        return errors

    def _extract_template_variables(self, template_content: str) -> set:
        """Extract variable names from template content.

        Args:
            template_content: Template content string

        Returns:
            Set of variable names found in template

        """
        import re

        # Find all {variable} patterns
        pattern = r"\{([^}]+)\}"
        matches = re.findall(pattern, template_content)

        return set(matches)

    def export_to_yaml(self, templates: list[PromptTemplate], file_path: str) -> None:
        """Export templates to a YAML file.

        Args:
            templates: List of templates to export
            file_path: Path to save the YAML file

        """
        data = {"prompt_templates": []}

        for template in templates:
            template_dict = {
                "template_id": template.template_id,
                "name": template.name,
                "description": template.description,
                "version": template.version,
                "template": template.template,
                "variables_schema": template.variables_schema,
                "agent_role": template.agent_role,
                "timeout_seconds": template.timeout_seconds,
                "approval_timeout_seconds": template.approval_timeout_seconds,
                "tags": template.tags,
                "author": template.author,
            }

            if template.created_at:
                template_dict["created_at"] = template.created_at.isoformat()

            if template.updated_at:
                template_dict["updated_at"] = template.updated_at.isoformat()

            data["prompt_templates"].append(template_dict)

        # Write to file
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
