"""Role selection logic for automatic role suggestion.

This module provides the RoleSelector class for intelligent role selection,
validation, and suggestion based on task descriptions.

## Design Overview

The RoleSelector provides intelligent role selection capabilities:
- Validate role existence
- Suggest roles based on task description keywords
- Get detailed role information
- Filter roles by domain or decision authority
- Support for role-based workflow routing

## Architecture

```
RoleSelector
├── registry: RoleRegistry
├── validate_role(role_name): Check if role exists
├── suggest_role(task_description): Suggest role based on keywords
├── get_role_for_task(task, preferred_role): Get role with fallback
├── get_role_info(role_name): Get detailed role information
├── list_available_roles(): List all available roles
├── get_roles_by_domain(domain): Filter by domain
├── get_roles_by_authority(authority): Filter by authority
└── print_available_roles(): Print formatted role list
```

## Keyword-Based Suggestion

The selector uses keyword matching to suggest appropriate roles:

**Marketing Keywords:**
- market, positioning, customer, benefit, messaging, value proposition,
  go-to-market, competitive

**Planner Keywords:**
- plan, timeline, schedule, estimate, task, breakdown, milestone, roadmap

**Dev Lead Keywords:**
- architecture, design, review, code review, technical, system design, refactor

**Dev Keywords:**
- implement, code, fix, bug, feature, develop, build, coding

**QA Keywords:**
- test, quality, verify, quality assurance, test case, bug report, regression

**SRE Keywords:**
- deploy, infrastructure, monitor, incident, performance, reliability,
  scaling, production

## Usage Examples

### Role Validation

```python
from gearmeshing_ai.agent.roles.selector import RoleSelector

selector = RoleSelector()

# Validate role
if selector.validate_role("dev_lead"):
    print("Role exists")

# List available roles
roles = selector.list_available_roles()
```

### Role Suggestion

```python
# Suggest role based on task
role = selector.suggest_role("Design the system architecture")
# Returns: "dev_lead"

role = selector.suggest_role("Create comprehensive test cases")
# Returns: "qa"

role = selector.suggest_role("Implement authentication module")
# Returns: "dev"
```

### Role Selection with Fallback

```python
# Get role with preferred fallback
role = selector.get_role_for_task(
    task_description="Some task",
    preferred_role="dev_lead"
)
# Returns: "dev_lead" (preferred role)

# Get role with auto-suggestion fallback
role = selector.get_role_for_task(
    task_description="Create test cases",
    preferred_role=None
)
# Returns: "qa" (suggested based on keywords)
```

### Role Information

```python
# Get detailed role information
info = selector.get_role_info("dev_lead")
# Returns: {
#     "role": "dev_lead",
#     "description": "Senior Software Architect",
#     "model_provider": "openai",
#     "model_name": "gpt-4-turbo",
#     "tools": [...],
#     "domain": "technical_leadership",
#     "decision_authority": "architecture_and_code_approval",
#     ...
# }
```

### Filtering

```python
# Get roles by domain
dev_roles = selector.get_roles_by_domain("software_development")

# Get roles by decision authority
approval_roles = selector.get_roles_by_authority("code_approval")
```

## Design Principles

1. **Keyword-Based**: Simple but effective role suggestion
2. **Flexible**: Support for preferred roles with fallback
3. **Informative**: Detailed role information retrieval
4. **Filterable**: Filter roles by domain or authority
5. **Extensible**: Easy to add custom keywords
6. **Graceful**: Handle missing roles gracefully
7. **Logging**: Debug logging for suggestion process
"""

import logging

from .registry import RoleRegistry, get_global_registry

logger = logging.getLogger(__name__)


class RoleSelector:
    """Selector for choosing appropriate roles based on task context.

    Provides role suggestion based on task description keywords,
    role validation, and role information retrieval.
    """

    def __init__(self, registry: RoleRegistry | None = None) -> None:
        """Initialize role selector.

        Args:
            registry: RoleRegistry instance (uses global if not provided)

        """
        self.registry = registry or get_global_registry()

    def get_role_info(self, role_name: str) -> dict:
        """Get detailed information about a role.

        Args:
            role_name: Name of the role

        Returns:
            Dictionary with role information

        Raises:
            ValueError: If role not found

        """
        role = self.registry.get_or_raise(role_name)

        return {
            "role": role.role,
            "description": role.description,
            "model_provider": role.model_provider,
            "model_name": role.model_name,
            "tools": role.tools,
            "domain": role.metadata.domain,
            "decision_authority": role.metadata.decision_authority,
            "requires_approval": role.metadata.requires_approval,
            "temperature": role.metadata.temperature,
            "max_tokens": role.metadata.max_tokens,
        }

    def validate_role(self, role_name: str) -> bool:
        """Check if a role exists and is valid.

        Args:
            role_name: Name of the role

        Returns:
            True if role exists, False otherwise

        """
        return self.registry.exists(role_name)

    def list_available_roles(self) -> list[str]:
        """Get list of all available roles.

        Returns:
            List of role names

        """
        return self.registry.list_roles()

    def suggest_role(self, task_description: str) -> str | None:
        """Suggest a role based on task description keywords.

        Uses keyword matching to suggest appropriate role.
        Returns None if no suitable role found.

        Args:
            task_description: Description of the task

        Returns:
            Suggested role name or None

        """
        task_lower = task_description.lower()

        # Define keyword-to-role mappings
        role_keywords = {
            "marketing": [
                "market",
                "positioning",
                "customer",
                "benefit",
                "messaging",
                "value proposition",
                "go-to-market",
                "competitive",
            ],
            "planner": [
                "plan",
                "timeline",
                "schedule",
                "estimate",
                "task",
                "breakdown",
                "milestone",
                "roadmap",
            ],
            "dev_lead": [
                "architecture",
                "design",
                "review",
                "code review",
                "technical",
                "system design",
                "refactor",
            ],
            "dev": [
                "implement",
                "code",
                "fix",
                "bug",
                "feature",
                "develop",
                "build",
                "coding",
            ],
            "qa": [
                "test",
                "quality",
                "verify",
                "quality assurance",
                "test case",
                "bug report",
                "regression",
            ],
            "sre": [
                "deploy",
                "infrastructure",
                "monitor",
                "incident",
                "performance",
                "reliability",
                "scaling",
                "production",
            ],
        }

        # Score each role based on keyword matches
        scores = {}
        for role, keywords in role_keywords.items():
            if not self.registry.exists(role):
                continue

            score = sum(1 for keyword in keywords if keyword in task_lower)
            if score > 0:
                scores[role] = score

        # Return role with highest score
        if scores:
            suggested_role = max(scores, key=scores.get)
            logger.debug(f"Suggested role '{suggested_role}' for task: {task_description[:50]}...")
            return suggested_role

        logger.debug(f"No role suggestion found for task: {task_description[:50]}...")
        return None

    def get_role_for_task(self, task_description: str, preferred_role: str | None = None) -> str:
        """Get role for a task, with optional preference.

        If preferred_role is provided and valid, uses it.
        Otherwise, suggests role based on task description.

        Args:
            task_description: Description of the task
            preferred_role: Preferred role name (optional)

        Returns:
            Role name to use

        Raises:
            ValueError: If no valid role found

        """
        # Use preferred role if provided and valid
        if preferred_role:
            if self.validate_role(preferred_role):
                logger.debug(f"Using preferred role: {preferred_role}")
                return preferred_role

            logger.warning(f"Preferred role '{preferred_role}' not found, will suggest alternative")

        # Suggest role based on task
        suggested = self.suggest_role(task_description)
        if suggested:
            return suggested

        # No suggestion found
        msg = f"Could not determine appropriate role for task: {task_description[:50]}..."
        logger.error(msg)
        raise ValueError(msg)

    def get_roles_by_domain(self, domain: str) -> list[str]:
        """Get all roles in a specific domain.

        Args:
            domain: Domain name

        Returns:
            List of role names in the domain

        """
        roles = self.registry.get_roles_by_domain(domain)
        return [role.role for role in roles]

    def get_roles_by_authority(self, authority: str) -> list[str]:
        """Get all roles with specific decision authority.

        Args:
            authority: Decision authority type

        Returns:
            List of role names with that authority

        """
        roles = self.registry.get_roles_by_authority(authority)
        return [role.role for role in roles]

    def print_available_roles(self) -> None:
        """Print all available roles with descriptions."""
        roles = self.registry.list_all()

        if not roles:
            print("No roles registered")
            return

        print("\nAvailable Roles:")
        print("-" * 80)

        for role in roles:
            print(f"\n{role.role.upper()}")
            print(f"  Description: {role.description}")
            print(f"  Domain: {role.metadata.domain}")
            print(f"  Model: {role.model_name} ({role.model_provider})")
            print(f"  Tools: {', '.join(role.tools) if role.tools else 'None'}")
            print(f"  Authority: {role.metadata.decision_authority}")
            print(f"  Requires Approval: {role.metadata.requires_approval}")
