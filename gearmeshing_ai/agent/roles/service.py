"""Role service for managing role lifecycle and integration with AgentFactory.

This module provides the RoleService class, which serves as the high-level API
for role management and integration with the agent system.

## Design Overview

The RoleService provides a unified, high-level interface for:
- Loading roles from configuration files
- Registering roles with AgentFactory
- Validating and selecting roles
- Getting role information
- Filtering roles by domain or authority

```
RoleService (High-Level API)
├── agent_factory: AgentFactory (optional)
├── registry: RoleRegistry
├── loader: RoleLoader
├── selector: RoleSelector
├── load_and_register_roles(config_path): Load and register with factory
├── register_role(role): Register single role
├── get_role(role_name): Get role definition
├── validate_role(role_name): Validate role exists
├── list_available_roles(): List all roles
├── suggest_role(task_description): Suggest role
├── get_role_for_task(task, preferred_role): Get role with fallback
├── get_role_info(role_name): Get role information
├── get_roles_by_domain(domain): Filter by domain
├── get_roles_by_authority(authority): Filter by authority
└── print_available_roles(): Print formatted list
```

## Architecture

The RoleService acts as a facade that coordinates between:
1. **RoleLoader**: Loads roles from YAML/dict
2. **RoleRegistry**: Stores and retrieves roles
3. **RoleSelector**: Validates and suggests roles
4. **AgentFactory**: Registers roles for agent creation

## Usage Examples

### Basic Usage

```python
from gearmeshing_ai.agent.roles.service import RoleService, get_global_role_service
from gearmeshing_ai.agent.abstraction.factory import AgentFactory

# Create factory
factory = AgentFactory(adapter=adapter)

# Create service
service = RoleService(agent_factory=factory)

# Load and register roles
roles = service.load_and_register_roles(
    "gearmeshing_ai/agent/roles/config/default_roles_config.yaml"
)

# List available roles
available = service.list_available_roles()
print(f"Available roles: {available}")
```

### Role Suggestion and Selection

```python
# Suggest role for task
role = service.suggest_role("Design the system architecture")
# Returns: "dev_lead"

# Get role with preferred fallback
role = service.get_role_for_task(
    task_description="Implement authentication",
    preferred_role=None  # Will auto-suggest
)
# Returns: "dev"

# Get role information
info = service.get_role_info("dev_lead")
print(f"Role: {info['role']}")
print(f"Description: {info['description']}")
print(f"Model: {info['model_name']}")
```

### Filtering and Querying

```python
# Get roles by domain
dev_roles = service.get_roles_by_domain("software_development")

# Get roles by decision authority
approval_roles = service.get_roles_by_authority("code_approval")

# Print all roles
service.print_available_roles()
```

### Custom Role Registration

```python
from gearmeshing_ai.agent.roles.models.role_definition import RoleDefinition, RoleMetadata

# Create custom role
metadata = RoleMetadata(
    domain="custom_domain",
    decision_authority="custom_authority",
    temperature=0.5,
)

role = RoleDefinition(
    role="custom_role",
    description="Custom Role",
    model_provider="openai",
    model_name="gpt-4",
    customized_model_name="custom-gpt4",
    system_prompt="Custom prompt...",
    tools=["tool1", "tool2"],
    metadata=metadata,
)

# Register with service
service.register_role(role)
```

### Global Service Singleton

```python
from gearmeshing_ai.agent.roles.service import get_global_role_service

# Get global service instance
service = get_global_role_service(factory)

# Use service
service.load_and_register_roles("config.yaml")
roles = service.list_available_roles()
```

## Integration with Workflows

```python
from gearmeshing_ai.agent.runtime.nodes.agent_decision import agent_decision_node

# Load roles with service
service = get_global_role_service(factory)
service.load_and_register_roles("config.yaml")

# Use in workflow
result = await agent_decision_node(
    state=workflow_state,
    agent_factory=factory,
    auto_select_role=True  # Auto-select based on task
)
```

## Integration with REST API

```python
from fastapi import FastAPI
from gearmeshing_ai.agent.roles.service import get_global_role_service

app = FastAPI()

@app.get("/api/roles")
async def list_roles():
    service = get_global_role_service()
    return {"roles": service.list_available_roles()}

@app.get("/api/roles/{role_name}")
async def get_role(role_name: str):
    service = get_global_role_service()
    return service.get_role_info(role_name)

@app.post("/api/workflows")
async def create_workflow(task: str, role: Optional[str] = None):
    service = get_global_role_service()
    
    # Auto-select if not specified
    if not role:
        role = service.suggest_role(task)
    
    if not role:
        return {"error": "Could not determine role"}
    
    # Create workflow with role
    # ...
```

## Design Principles

1. **Unified Interface**: Single API for all role operations
2. **Flexibility**: Optional AgentFactory integration
3. **Composition**: Coordinates between registry, loader, and selector
4. **Singleton Pattern**: Global instance for easy access
5. **Error Handling**: Clear error messages and logging
6. **Extensibility**: Easy to extend with new operations
7. **Integration**: Seamless integration with agent system

## Key Features

- **Load and Register**: Load roles from YAML and register with factory
- **Validation**: Validate roles before use
- **Suggestion**: Suggest roles based on task description
- **Filtering**: Filter roles by domain or authority
- **Information**: Get detailed role information
- **Logging**: Comprehensive logging for debugging
- **Error Handling**: Clear error messages for issues
"""

import logging
from typing import Optional

from gearmeshing_ai.agent.abstraction.factory import AgentFactory

from .loader import RoleLoader, get_global_loader
from .models.role_definition import RoleDefinition
from .registry import RoleRegistry, get_global_registry
from .selector import RoleSelector

logger = logging.getLogger(__name__)


class RoleService:
    """High-level service for role management and integration.

    Provides unified API for:
    - Loading roles from configuration
    - Registering roles with AgentFactory
    - Selecting appropriate roles
    - Validating roles
    """

    def __init__(
        self,
        agent_factory: Optional[AgentFactory] = None,
        registry: Optional[RoleRegistry] = None,
        loader: Optional[RoleLoader] = None,
    ) -> None:
        """Initialize role service.

        Args:
            agent_factory: AgentFactory instance for registering roles
            registry: RoleRegistry instance (uses global if not provided)
            loader: RoleLoader instance (uses global if not provided)
        """
        self.agent_factory = agent_factory
        self.registry = registry or get_global_registry()
        self.loader = loader or get_global_loader()
        self.selector = RoleSelector(self.registry)

    def load_and_register_roles(self, config_path: str) -> list[RoleDefinition]:
        """Load roles from configuration and register with factory.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            List of loaded and registered RoleDefinition instances

        Raises:
            FileNotFoundError: If config file not found
            ValueError: If configuration invalid
        """
        logger.info(f"Loading and registering roles from: {config_path}")

        # Load roles from file
        roles = self.loader.load_from_file(config_path)

        # Register with factory if available
        if self.agent_factory:
            for role in roles:
                agent_settings = role.to_agent_settings()
                self.agent_factory.register_agent_settings(agent_settings)
                logger.debug(f"Registered role '{role.role}' with AgentFactory")

        logger.info(f"Successfully loaded and registered {len(roles)} roles")
        return roles

    def register_role(self, role: RoleDefinition) -> None:
        """Register a single role.

        Args:
            role: RoleDefinition instance to register
        """
        # Register with registry
        self.registry.register(role)

        # Register with factory if available
        if self.agent_factory:
            agent_settings = role.to_agent_settings()
            self.agent_factory.register_agent_settings(agent_settings)
            logger.debug(f"Registered role '{role.role}' with AgentFactory")

    def get_role(self, role_name: str) -> RoleDefinition:
        """Get a role definition.

        Args:
            role_name: Name of the role

        Returns:
            RoleDefinition instance

        Raises:
            ValueError: If role not found
        """
        return self.registry.get_or_raise(role_name)

    def validate_role(self, role_name: str) -> bool:
        """Check if a role exists.

        Args:
            role_name: Name of the role

        Returns:
            True if role exists, False otherwise
        """
        return self.selector.validate_role(role_name)

    def list_available_roles(self) -> list[str]:
        """Get list of all available roles.

        Returns:
            List of role names
        """
        return self.selector.list_available_roles()

    def get_role_info(self, role_name: str) -> dict:
        """Get detailed information about a role.

        Args:
            role_name: Name of the role

        Returns:
            Dictionary with role information

        Raises:
            ValueError: If role not found
        """
        return self.selector.get_role_info(role_name)

    def suggest_role(self, task_description: str) -> Optional[str]:
        """Suggest a role based on task description.

        Args:
            task_description: Description of the task

        Returns:
            Suggested role name or None
        """
        return self.selector.suggest_role(task_description)

    def get_role_for_task(
        self, task_description: str, preferred_role: Optional[str] = None
    ) -> str:
        """Get role for a task with optional preference.

        Args:
            task_description: Description of the task
            preferred_role: Preferred role name (optional)

        Returns:
            Role name to use

        Raises:
            ValueError: If no valid role found
        """
        return self.selector.get_role_for_task(task_description, preferred_role)

    def get_roles_by_domain(self, domain: str) -> list[str]:
        """Get all roles in a specific domain.

        Args:
            domain: Domain name

        Returns:
            List of role names in the domain
        """
        return self.selector.get_roles_by_domain(domain)

    def get_roles_by_authority(self, authority: str) -> list[str]:
        """Get all roles with specific decision authority.

        Args:
            authority: Decision authority type

        Returns:
            List of role names with that authority
        """
        return self.selector.get_roles_by_authority(authority)

    def print_available_roles(self) -> None:
        """Print all available roles with descriptions."""
        self.selector.print_available_roles()


# Global singleton instance
_global_service: Optional[RoleService] = None


def get_global_role_service(agent_factory: Optional[AgentFactory] = None) -> RoleService:
    """Get or create the global role service singleton.

    Args:
        agent_factory: AgentFactory instance (optional, used on first creation)

    Returns:
        Global RoleService instance
    """
    global _global_service
    if _global_service is None:
        _global_service = RoleService(agent_factory=agent_factory)
    return _global_service
