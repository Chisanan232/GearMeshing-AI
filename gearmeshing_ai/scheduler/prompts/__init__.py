"""Prompt Templates Package

This package contains the prompt template management system for the scheduler,
including YAML-based templates, registry system, and LangFuse integration.

Key Components:
- Registry: Auto-registration system for prompt templates
- Loader: YAML loader utilities for template management
- LangFuse: Integration with LangFuse for prompt versioning
"""

from .registry import prompt_template_registry, register_prompt_template
from .loader import PromptTemplateLoader

__all__ = [
    "prompt_template_registry",
    "register_prompt_template",
    "PromptTemplateLoader",
]
