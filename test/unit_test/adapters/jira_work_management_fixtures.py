"""Pure Jira payload fixtures for work-management adapter tests."""

from __future__ import annotations

from typing import Any


def jira_description(*criteria: str) -> dict[str, Any]:
    content: list[dict[str, Any]] = [
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "User Value"}],
        },
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "Deliver only the approved behavior."}],
        },
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Acceptance Criteria"}],
        },
    ]
    if criteria:
        content.append(
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {"type": "paragraph", "content": [{"type": "text", "text": criterion}]}
                        ],
                    }
                    for criterion in criteria
                ],
            }
        )
    return {"type": "doc", "version": 1, "content": content}


def jira_issue_payload(
    *,
    issue_type: str = "Story",
    criteria: tuple[str, ...] = ("The approved result is observable.",),
    repository_url: str | None = "https://github.com/example/gearmeshing-ai",
    labels: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "key": "GMAI-17",
        "fields": {
            "summary": "Load approved Jira work item",
            "description": jira_description(*criteria),
            "issuetype": {"name": issue_type},
            "labels": ["mvp-1", "spec-ready"] if labels is None else labels,
            "customfield_12345": repository_url,
        },
    }
