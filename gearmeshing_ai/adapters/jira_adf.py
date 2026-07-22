"""Small, bounded Atlassian Document Format readers used by the Jira adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final

_MAX_ADF_DEPTH: Final = 32


def _node_text(node: object, *, depth: int = 0) -> str:
    if depth > _MAX_ADF_DEPTH or not isinstance(node, Mapping):
        return ""
    node_type = node.get("type")
    if node_type == "text":
        value = node.get("text")
        return value if isinstance(value, str) else ""
    if node_type == "hardBreak":
        return "\n"
    content = node.get("content")
    if not isinstance(content, Sequence) or isinstance(content, (str, bytes)):
        return ""
    return "".join(_node_text(child, depth=depth + 1) for child in content)


def adf_to_text(document: object) -> str:
    """Return provider-neutral text without interpreting or extending its meaning."""
    if not isinstance(document, Mapping):
        return ""
    content = document.get("content")
    if not isinstance(content, Sequence) or isinstance(content, (str, bytes)):
        return ""
    blocks = (_node_text(block).strip() for block in content)
    return "\n\n".join(block for block in blocks if block)


def adf_section_items(document: object, heading: str) -> tuple[str, ...]:
    """Read list items or paragraphs below a named top-level ADF heading."""
    if not isinstance(document, Mapping):
        return ()
    content = document.get("content")
    if not isinstance(content, Sequence) or isinstance(content, (str, bytes)):
        return ()

    target = heading.casefold().strip()
    found = False
    heading_level = 6
    items: list[str] = []
    for block in content:
        if not isinstance(block, Mapping):
            continue
        if block.get("type") == "heading":
            attrs = block.get("attrs")
            level = attrs.get("level", 6) if isinstance(attrs, Mapping) else 6
            if found and isinstance(level, int) and level <= heading_level:
                break
            if _node_text(block).casefold().strip() == target:
                found = True
                heading_level = level if isinstance(level, int) else 6
            continue
        if not found:
            continue
        if block.get("type") in {"bulletList", "orderedList"}:
            children = block.get("content")
            if isinstance(children, Sequence) and not isinstance(children, (str, bytes)):
                items.extend(text for child in children if (text := _node_text(child).strip()))
        elif block.get("type") == "paragraph":
            if text := _node_text(block).strip():
                items.append(text)
    return tuple(items)
