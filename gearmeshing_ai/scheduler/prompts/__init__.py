"""Prompt Templates Package

This package contains the prompt template management system for the scheduler,
including YAML-based templates, registry system, and LangFuse integration.

Key Components:
- Registry: Auto-registration system for prompt templates
- Loader: YAML loader utilities for template management
- LangFuse: Integration with LangFuse for prompt versioning
"""

from .loader import PromptTemplateLoader
from .registry import prompt_template_registry, register_prompt_template

__all__ = [
    "PromptTemplateLoader",
    "prompt_template_registry",
    "register_prompt_template",
]
