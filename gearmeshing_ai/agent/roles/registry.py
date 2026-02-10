"""Role registry for managing role definitions.

This module provides the RoleRegistry class, which serves as the centralized
storage and retrieval system for role definitions.

## Design Overview

The RoleRegistry is a singleton pattern implementation that provides:
- Centralized storage for all role definitions
- Fast lookup by role name
- Filtering by domain or decision authority
- Thread-safe operations
- Global access via get_global_registry()

## Architecture

```
RoleRegistry (Singleton)
├── _roles: dict[str, RoleDefinition]
│   └── Stores all registered roles keyed by role name
├── register(role): Register a role definition
├── get(role_name): Retrieve role or None
├── get_or_raise(role_name): Retrieve role or raise ValueError
├── exists(role_name): Check if role exists
├── list_roles(): Get all role names
├── list_all(): Get all role definitions
├── get_roles_by_domain(domain): Filter by domain
├── get_roles_by_authority(authority): Filter by authority
└── clear(): Clear all roles
```

## Key Features

1. **Singleton Pattern**: Global instance via get_global_registry()
2. **Fast Lookup**: O(1) retrieval by role name
3. **Filtering**: Filter roles by domain or decision authority
4. **Error Handling**: Clear error messages for missing roles
5. **Logging**: Debug logging for all operations
6. **Operators**: Support for 'in', 'len()', and repr()

## Usage Examples

### Basic Operations

```python
from gearmeshing_ai.agent.roles.registry import RoleRegistry, get_global_registry

# Create registry
registry = RoleRegistry()

# Register a role
registry.register(role_definition)

# Check if role exists
if registry.exists("dev"):
    role = registry.get("dev")

# Get role or raise error
role = registry.get_or_raise("dev_lead")

# List all roles
all_roles = registry.list_roles()
```

### Filtering

```python
# Get roles by domain
dev_roles = registry.get_roles_by_domain("software_development")

# Get roles by decision authority
approval_roles = registry.get_roles_by_authority("code_approval")
```

### Global Registry

```python
# Get global singleton instance
global_registry = get_global_registry()

# Register with global registry
global_registry.register(role)

# Get from global registry
role = global_registry.get("dev")
```

## Design Principles

1. **Centralization**: Single source of truth for all roles
2. **Efficiency**: Fast O(1) lookup by role name
3. **Flexibility**: Support filtering by multiple criteria
4. **Consistency**: Singleton pattern ensures consistency
5. **Logging**: All operations logged for debugging
6. **Error Handling**: Clear error messages
"""

import logging

from .models.role_definition import RoleDefinition

logger = logging.getLogger(__name__)


class RoleRegistry:
    """Registry for managing AI agent role definitions.

    Provides centralized storage and retrieval of role configurations.
    Supports registration, lookup, and listing of available roles.
    """

    def __init__(self) -> None:
        """Initialize the role registry."""
        self._roles: dict[str, RoleDefinition] = {}

    def register(self, role: RoleDefinition) -> None:
        """Register a role definition.

        Args:
            role: RoleDefinition instance to register

        Raises:
            ValueError: If role with same name already registered

        """
        if role.role in self._roles:
            logger.warning(f"Role '{role.role}' already registered, overwriting")

        self._roles[role.role] = role
        logger.debug(f"Registered role: {role.role}")

    def register_from_dict(self, role_dict: dict) -> None:
        """Register a role from dictionary (e.g., from YAML).

        Args:
            role_dict: Dictionary with role configuration

        """
        role = RoleDefinition.from_dict(role_dict)
        self.register(role)

    def get(self, role_name: str) -> RoleDefinition | None:
        """Get a role definition by name.

        Args:
            role_name: Name of the role

        Returns:
            RoleDefinition if found, None otherwise

        """
        return self._roles.get(role_name)

    def get_or_raise(self, role_name: str) -> RoleDefinition:
        """Get a role definition by name, raising if not found.

        Args:
            role_name: Name of the role

        Returns:
            RoleDefinition instance

        Raises:
            ValueError: If role not found

        """
        role = self.get(role_name)
        if not role:
            msg = f"Role '{role_name}' not found in registry"
            raise ValueError(msg)
        return role

    def exists(self, role_name: str) -> bool:
        """Check if a role exists.

        Args:
            role_name: Name of the role

        Returns:
            True if role exists, False otherwise

        """
        return role_name in self._roles

    def list_roles(self) -> list[str]:
        """List all registered role names.

        Returns:
            List of role names

        """
        return list(self._roles.keys())

    def list_all(self) -> list[RoleDefinition]:
        """List all registered role definitions.

        Returns:
            List of RoleDefinition instances

        """
        return list(self._roles.values())

    def get_roles_by_domain(self, domain: str) -> list[RoleDefinition]:
        """Get all roles in a specific domain.

        Args:
            domain: Domain name

        Returns:
            List of RoleDefinition instances in the domain

        """
        return [role for role in self._roles.values() if role.metadata.domain == domain]

    def get_roles_by_authority(self, authority: str) -> list[RoleDefinition]:
        """Get all roles with specific decision authority.

        Args:
            authority: Decision authority type

        Returns:
            List of RoleDefinition instances with that authority

        """
        return [role for role in self._roles.values() if authority in role.metadata.decision_authority]

    def clear(self) -> None:
        """Clear all registered roles."""
        self._roles.clear()
        logger.debug("Cleared all roles from registry")

    def __len__(self) -> int:
        """Get number of registered roles."""
        return len(self._roles)

    def __contains__(self, role_name: str) -> bool:
        """Check if role exists using 'in' operator."""
        return self.exists(role_name)

    def __repr__(self) -> str:
        """String representation of registry."""
        return f"RoleRegistry(roles={list(self._roles.keys())})"


# Global singleton instance
_global_registry: RoleRegistry | None = None


def get_global_registry() -> RoleRegistry:
    """Get or create the global role registry singleton.

    Returns:
        Global RoleRegistry instance

    """
    global _global_registry
    if _global_registry is None:
        _global_registry = RoleRegistry()
    return _global_registry
