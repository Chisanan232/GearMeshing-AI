"""Role loader for loading role definitions from YAML configuration.

This module provides the RoleLoader class for loading role definitions from
YAML files or dictionaries and automatically registering them with a registry.

## Design Overview

The RoleLoader handles all aspects of loading role configurations:
- Load roles from YAML files
- Load roles from dictionaries (programmatic)
- Automatic registration with RoleRegistry
- Comprehensive error handling
- Support for partial loading (single role)

## Architecture

```
RoleLoader
├── registry: RoleRegistry
├── load_from_file(config_path): Load all roles from YAML file
├── load_single_role(config_path, role_name): Load specific role
├── load_from_dict(config): Load roles from dictionary
└── Global Functions:
    └── load_default_roles(config_path): Load default roles from package
```

## YAML Configuration Format

```yaml
roles:
  dev:
    description: "Senior Software Developer"
    model_settings:
      customized_name: "dev-gpt4"
      provider: "openai"
      model: "gpt-4"
    system_prompt: |
      You are a senior software developer...

      Your expertise includes:
      - Full-stack development
      - Software design patterns
      - Testing and debugging

      Your responsibilities:
      1. Implement features
      2. Write clean code
      3. Write unit tests
    tools:
      - read_file
      - write_file
      - run_command
    metadata:
      domain: "software_development"
      decision_authority: "implementation"
      temperature: 0.4
      max_tokens: 3072
      cost_priority: "medium"
```

## Usage Examples

### Load from YAML File

```python
from gearmeshing_ai.agent.roles.loader import RoleLoader

loader = RoleLoader()

# Load all roles from file
roles = loader.load_from_file("path/to/config.yaml")

# Load single role
role = loader.load_single_role("path/to/config.yaml", "dev_lead")
```

### Load from Dictionary

```python
config = {
    "roles": {
        "dev": {
            "description": "Developer",
            "model_settings": {...},
            "system_prompt": "...",
            "metadata": {...},
        },
    }
}

roles = loader.load_from_dict(config)
```

### Load Default Roles

```python
from gearmeshing_ai.agent.roles.loader import load_default_roles

# Load from package default location
roles = load_default_roles()

# Load from custom path
roles = load_default_roles("path/to/custom_config.yaml")
```

### With Custom Registry

```python
from gearmeshing_ai.agent.roles.registry import RoleRegistry
from gearmeshing_ai.agent.roles.loader import RoleLoader

# Create custom registry
registry = RoleRegistry()

# Create loader with custom registry
loader = RoleLoader(registry)

# Load roles
roles = loader.load_from_file("config.yaml")

# Roles are automatically registered with custom registry
assert registry.exists("dev")
```

## Error Handling

The loader provides comprehensive error handling:

```python
# FileNotFoundError: Config file not found
try:
    loader.load_from_file("/nonexistent/config.yaml")
except FileNotFoundError as e:
    print(f"Config file not found: {e}")

# ValueError: Invalid YAML or missing required fields
try:
    loader.load_from_file("invalid.yaml")
except ValueError as e:
    print(f"Invalid configuration: {e}")

# ValueError: Missing 'roles' key
try:
    loader.load_from_dict({"other_key": {}})
except ValueError as e:
    print(f"Missing roles key: {e}")
```

## Design Principles

1. **Flexibility**: Support both YAML files and dictionaries
2. **Automation**: Automatic registration with registry
3. **Validation**: Comprehensive validation of configurations
4. **Error Handling**: Clear error messages for debugging
5. **Logging**: Debug logging for all operations
6. **Extensibility**: Easy to add support for other formats
7. **Robustness**: Handle edge cases and malformed input
"""

import logging
from pathlib import Path

import yaml

from .models.role_definition import RoleDefinition
from .registry import RoleRegistry, get_global_registry

logger = logging.getLogger(__name__)


class RoleLoader:
    """Loader for role definitions from YAML configuration files.

    Supports loading single roles or all roles from a YAML file.
    Automatically registers loaded roles with a registry.
    """

    def __init__(self, registry: RoleRegistry | None = None) -> None:
        """Initialize role loader.

        Args:
            registry: RoleRegistry instance (uses global if not provided)

        """
        self.registry = registry or get_global_registry()

    def load_from_file(self, config_path: str | Path) -> list[RoleDefinition]:
        """Load all roles from a YAML configuration file.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            List of loaded RoleDefinition instances

        Raises:
            FileNotFoundError: If config file not found
            ValueError: If YAML parsing fails or roles invalid

        """
        config_path = Path(config_path)

        if not config_path.exists():
            msg = f"Configuration file not found: {config_path}"
            raise FileNotFoundError(msg)

        logger.info(f"Loading roles from: {config_path}")

        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            msg = f"Failed to parse YAML configuration: {e}"
            raise ValueError(msg) from e

        if not config or "roles" not in config:
            msg = "Configuration file must contain 'roles' key"
            raise ValueError(msg)

        roles = []
        for role_name, role_config in config["roles"].items():
            try:
                # Add role name to config if not present
                if "role" not in role_config:
                    role_config["role"] = role_name

                role = RoleDefinition.from_dict(role_config)
                self.registry.register(role)
                roles.append(role)
                logger.debug(f"Loaded role: {role_name}")
            except Exception as e:
                logger.error(f"Failed to load role '{role_name}': {e}")
                raise ValueError(f"Failed to load role '{role_name}': {e}") from e

        logger.info(f"Successfully loaded {len(roles)} roles")
        return roles

    def load_from_dict(self, config: dict) -> list[RoleDefinition]:
        """Load roles from a dictionary configuration.

        Args:
            config: Dictionary with 'roles' key containing role configurations

        Returns:
            List of loaded RoleDefinition instances

        Raises:
            ValueError: If configuration invalid

        """
        if not config or "roles" not in config:
            msg = "Configuration must contain 'roles' key"
            raise ValueError(msg)

        roles = []
        for role_name, role_config in config["roles"].items():
            try:
                # Add role name to config if not present
                if "role" not in role_config:
                    role_config["role"] = role_name

                role = RoleDefinition.from_dict(role_config)
                self.registry.register(role)
                roles.append(role)
                logger.debug(f"Loaded role: {role_name}")
            except Exception as e:
                logger.error(f"Failed to load role '{role_name}': {e}")
                raise ValueError(f"Failed to load role '{role_name}': {e}") from e

        logger.info(f"Successfully loaded {len(roles)} roles from dictionary")
        return roles

    def load_single_role(self, config_path: str | Path, role_name: str) -> RoleDefinition:
        """Load a single role from YAML configuration file.

        Args:
            config_path: Path to YAML configuration file
            role_name: Name of the role to load

        Returns:
            Loaded RoleDefinition instance

        Raises:
            FileNotFoundError: If config file not found
            ValueError: If role not found or invalid

        """
        config_path = Path(config_path)

        if not config_path.exists():
            msg = f"Configuration file not found: {config_path}"
            raise FileNotFoundError(msg)

        with open(config_path) as f:
            config = yaml.safe_load(f)

        if not config or "roles" not in config:
            msg = "Configuration file must contain 'roles' key"
            raise ValueError(msg)

        if role_name not in config["roles"]:
            msg = f"Role '{role_name}' not found in configuration"
            raise ValueError(msg)

        role_config = config["roles"][role_name]
        if "role" not in role_config:
            role_config["role"] = role_name

        role = RoleDefinition.from_dict(role_config)
        self.registry.register(role)
        logger.info(f"Loaded single role: {role_name}")

        return role


# Global singleton instance
_global_loader: RoleLoader | None = None


def get_global_loader() -> RoleLoader:
    """Get or create the global role loader singleton.

    Returns:
        Global RoleLoader instance

    """
    global _global_loader
    if _global_loader is None:
        _global_loader = RoleLoader()
    return _global_loader


def load_default_roles(config_path: str | Path | None = None) -> list[RoleDefinition]:
    """Load default roles from configuration file.

    If config_path not provided, looks for default_roles_config.yaml
    in the roles package directory.

    Args:
        config_path: Path to configuration file (optional)

    Returns:
        List of loaded RoleDefinition instances

    """
    if config_path is None:
        # Use default location in roles package
        config_path = Path(__file__).parent / "config" / "default_roles_config.yaml"

    loader = get_global_loader()
    return loader.load_from_file(config_path)
