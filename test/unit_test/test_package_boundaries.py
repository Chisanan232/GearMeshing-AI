"""Tests for the modular-monolith package boundaries."""

from importlib import import_module

import pytest


@pytest.mark.parametrize(
    "package_name",
    [
        "gearmeshing_ai.domain",
        "gearmeshing_ai.application",
        "gearmeshing_ai.application.ports",
        "gearmeshing_ai.adapters",
        "gearmeshing_ai.runtime",
        "gearmeshing_ai.interfaces",
    ],
)
def test_package_boundary_is_importable(package_name: str) -> None:
    """Each declared package boundary is importable after installation."""
    assert import_module(package_name).__name__ == package_name
