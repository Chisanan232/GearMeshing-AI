"""Prompt template registry system.

This module provides the registry system for managing prompt templates,
allowing templates to be registered, retrieved, and used throughout the
scheduler system.
"""

from typing import Any

from .loader import PromptTemplate, PromptTemplateLoader


class PromptTemplateRegistry:
    """Registry for managing prompt templates.

    This registry provides a centralized location for storing and retrieving
    prompt templates, with support for loading from YAML files and runtime
    registration.
    """

    def __init__(self) -> None:
        """Initialize the registry."""
        self._templates: dict[str, PromptTemplate] = {}
        self._loader = PromptTemplateLoader()
        self._initialized = False

    def register(self, template: PromptTemplate) -> None:
        """Register a prompt template.

        Args:
            template: Prompt template to register

        Raises:
            ValueError: If template ID is already registered

        """
        if template.template_id in self._templates:
            raise ValueError(f"Prompt template '{template.template_id}' is already registered")

        self._templates[template.template_id] = template

    def unregister(self, template_id: str) -> None:
        """Unregister a prompt template.

        Args:
            template_id: ID of the template to unregister

        Raises:
            KeyError: If template is not registered

        """
        if template_id not in self._templates:
            raise KeyError(f"Prompt template '{template_id}' is not registered")

        del self._templates[template_id]

    def get(self, template_id: str) -> PromptTemplate | None:
        """Get a prompt template by ID.

        Args:
            template_id: ID of the template

        Returns:
            Prompt template or None if not found

        """
        return self._templates.get(template_id)

    def get_all(self) -> dict[str, PromptTemplate]:
        """Get all registered prompt templates.

        Returns:
            Dictionary mapping template IDs to templates

        """
        return self._templates.copy()

    def get_by_tags(self, tags: list[str]) -> dict[str, PromptTemplate]:
        """Get prompt templates by tags.

        Args:
            tags: Tags to filter by

        Returns:
            Dictionary of templates with matching tags

        """
        matching_templates = {}

        for template_id, template in self._templates.items():
            if any(tag in template.tags for tag in tags):
                matching_templates[template_id] = template

        return matching_templates

    def get_by_agent_role(self, agent_role: str) -> dict[str, PromptTemplate]:
        """Get prompt templates by agent role.

        Args:
            agent_role: Agent role to filter by

        Returns:
            Dictionary of templates for the specified agent role

        """
        matching_templates = {}

        for template_id, template in self._templates.items():
            if template.agent_role == agent_role:
                matching_templates[template_id] = template

        return matching_templates

    def load_from_yaml(self, file_path: str) -> int:
        """Load prompt templates from a YAML file.

        Args:
            file_path: Path to the YAML file

        Returns:
            Number of templates loaded

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid

        """
        templates = self._loader.load_from_yaml(file_path)

        loaded_count = 0
        for template in templates:
            try:
                self.register(template)
                loaded_count += 1
            except ValueError:
                # Skip templates with duplicate IDs
                continue

        return loaded_count

    def load_from_yaml_string(self, yaml_content: str) -> int:
        """Load prompt templates from a YAML string.

        Args:
            yaml_content: YAML content as string

        Returns:
            Number of templates loaded

        """
        templates = self._loader.load_from_yaml_string(yaml_content)

        loaded_count = 0
        for template in templates:
            try:
                self.register(template)
                loaded_count += 1
            except ValueError:
                # Skip templates with duplicate IDs
                continue

        return loaded_count

    def render_template(self, template_id: str, variables: dict[str, Any]) -> str:
        """Render a template by ID with variables.

        Args:
            template_id: ID of the template to render
            variables: Variables to substitute

        Returns:
            Rendered template

        Raises:
            KeyError: If template is not found
            ValueError: If variables are invalid

        """
        template = self.get(template_id)
        if not template:
            raise KeyError(f"Prompt template '{template_id}' not found")

        return template.render(variables)

    def validate_template_variables(self, template_id: str, variables: dict[str, Any]) -> list[str]:
        """Validate variables for a template.

        Args:
            template_id: ID of the template
            variables: Variables to validate

        Returns:
            List of validation errors

        Raises:
            KeyError: If template is not found

        """
        template = self.get(template_id)
        if not template:
            raise KeyError(f"Prompt template '{template_id}' not found")

        return template.validate_variables(variables)

    def search(self, query: str) -> dict[str, PromptTemplate]:
        """Search for templates by name, description, or tags.

        Args:
            query: Search query

        Returns:
            Dictionary of matching templates

        """
        query_lower = query.lower()
        matching_templates = {}

        for template_id, template in self._templates.items():
            # Search in name
            if query_lower in template.name.lower():
                matching_templates[template_id] = template
                continue

            # Search in description
            if query_lower in template.description.lower():
                matching_templates[template_id] = template
                continue

            # Search in tags
            if any(query_lower in tag.lower() for tag in template.tags):
                matching_templates[template_id] = template
                continue

        return matching_templates

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the registry.

        Returns:
            Dictionary containing registry summary

        """
        agent_roles = {}
        tag_counts = {}

        for template in self._templates.values():
            # Count agent roles
            if template.agent_role:
                agent_roles[template.agent_role] = agent_roles.get(template.agent_role, 0) + 1

            # Count tags
            for tag in template.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "total_templates": len(self._templates),
            "agent_roles": agent_roles,
            "tag_counts": tag_counts,
            "templates": {template_id: template.get_summary() for template_id, template in self._templates.items()},
        }

    def initialize(self, yaml_file_paths: list[str] | None = None) -> None:
        """Initialize the registry with default templates.

        Args:
            yaml_file_paths: Optional list of YAML files to load

        """
        if self._initialized:
            return

        # Load default templates from the checking point prompts file
        default_prompts_path = "/Users/bryant/Bryant-Developments/GearMeshing-AI/gearmeshing-ai/.ai_prompts/2026.2.18/checking_point_prompts.yaml"

        try:
            self.load_from_yaml(default_prompts_path)
        except (FileNotFoundError, ValueError):
            # Continue without default templates if file not found
            pass

        # Load additional YAML files if provided
        if yaml_file_paths:
            for file_path in yaml_file_paths:
                try:
                    self.load_from_yaml(file_path)
                except (FileNotFoundError, ValueError):
                    # Skip files that can't be loaded
                    continue

        self._initialized = True


# Global registry instance
prompt_template_registry = PromptTemplateRegistry()


def register_prompt_template(template: PromptTemplate) -> PromptTemplate:
    """Decorator for registering prompt templates.

    Args:
        template: Prompt template to register

    Returns:
        The same template (for decorator usage)

    """
    prompt_template_registry.register(template)
    return template


def get_prompt_template(template_id: str) -> PromptTemplate | None:
    """Get a prompt template by ID.

    Args:
        template_id: ID of the template

    Returns:
        Prompt template or None if not found

    """
    return prompt_template_registry.get(template_id)


def render_prompt_template(template_id: str, variables: dict[str, Any]) -> str:
    """Render a prompt template by ID with variables.

    Args:
        template_id: ID of the template to render
        variables: Variables to substitute

    Returns:
        Rendered template

    """
    return prompt_template_registry.render_template(template_id, variables)


def initialize_prompt_registry(yaml_file_paths: list[str] | None = None) -> None:
    """Initialize the global prompt template registry.

    Args:
        yaml_file_paths: Optional list of YAML files to load

    """
    prompt_template_registry.initialize(yaml_file_paths)
