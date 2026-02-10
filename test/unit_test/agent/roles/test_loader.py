"""Unit tests for roles package loader.

Tests for RoleLoader including:
- Loading roles from YAML files
- Loading roles from dictionaries
- Error handling for invalid configurations
- Role registration with registry
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from gearmeshing_ai.agent.roles.loader import RoleLoader, load_default_roles
from gearmeshing_ai.agent.roles.registry import RoleRegistry


@pytest.fixture
def temp_yaml_file():
    """Create a temporary YAML file with role configuration."""
    config = {
        "roles": {
            "dev": {
                "description": "Developer",
                "model_settings": {
                    "customized_name": "dev-gpt4",
                    "provider": "openai",
                    "model": "gpt-4",
                },
                "system_prompt": "You are a developer...",
                "tools": ["read_file", "write_file"],
                "metadata": {
                    "domain": "software_development",
                    "decision_authority": "implementation",
                    "temperature": 0.4,
                    "max_tokens": 3072,
                },
            },
            "qa": {
                "description": "QA Engineer",
                "model_settings": {
                    "customized_name": "qa-gpt4",
                    "provider": "openai",
                    "model": "gpt-4",
                },
                "system_prompt": "You are a QA engineer...",
                "tools": ["read_file", "write_file"],
                "metadata": {
                    "domain": "quality_assurance",
                    "decision_authority": "quality_assessment",
                    "temperature": 0.4,
                },
            },
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink()


@pytest.fixture
def registry():
    """Create a fresh registry for each test."""
    return RoleRegistry()


@pytest.fixture
def loader(registry):
    """Create a loader with fresh registry."""
    return RoleLoader(registry)


class TestRoleLoader:
    """Test RoleLoader functionality."""

    def test_load_from_file(self, loader, temp_yaml_file):
        """Test loading roles from YAML file."""
        roles = loader.load_from_file(temp_yaml_file)

        assert len(roles) == 2
        assert any(r.role == "dev" for r in roles)
        assert any(r.role == "qa" for r in roles)

    def test_load_from_file_registers_with_registry(self, loader, temp_yaml_file):
        """Test that loaded roles are registered with registry."""
        loader.load_from_file(temp_yaml_file)

        assert loader.registry.exists("dev")
        assert loader.registry.exists("qa")
        assert len(loader.registry) == 2

    def test_load_from_file_nonexistent(self, loader):
        """Test loading from non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            loader.load_from_file("/nonexistent/path/config.yaml")

    def test_load_from_file_invalid_yaml(self, loader):
        """Test loading invalid YAML raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Failed to parse YAML"):
                loader.load_from_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_from_file_missing_roles_key(self, loader):
        """Test loading YAML without 'roles' key raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"other_key": {}}, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="must contain 'roles' key"):
                loader.load_from_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_from_file_empty_roles(self, loader):
        """Test loading YAML with empty roles."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"roles": {}}, f)
            temp_path = f.name

        try:
            roles = loader.load_from_file(temp_path)
            assert len(roles) == 0
        finally:
            Path(temp_path).unlink()

    def test_load_single_role(self, loader, temp_yaml_file):
        """Test loading a single role from file."""
        role = loader.load_single_role(temp_yaml_file, "dev")

        assert role.role == "dev"
        assert role.description == "Developer"
        assert loader.registry.exists("dev")

    def test_load_single_role_nonexistent(self, loader, temp_yaml_file):
        """Test loading non-existent role raises error."""
        with pytest.raises(ValueError, match="Role 'nonexistent' not found"):
            loader.load_single_role(temp_yaml_file, "nonexistent")

    def test_load_from_dict(self, loader):
        """Test loading roles from dictionary."""
        config = {
            "roles": {
                "dev": {
                    "description": "Developer",
                    "model_settings": {
                        "customized_name": "dev-gpt4",
                        "provider": "openai",
                        "model": "gpt-4",
                    },
                    "system_prompt": "You are a developer...",
                    "metadata": {
                        "domain": "software_development",
                        "decision_authority": "implementation",
                    },
                },
            }
        }

        roles = loader.load_from_dict(config)

        assert len(roles) == 1
        assert roles[0].role == "dev"
        assert loader.registry.exists("dev")

    def test_load_from_dict_registers_with_registry(self, loader):
        """Test that roles from dict are registered."""
        config = {
            "roles": {
                "test_role": {
                    "description": "Test Role",
                    "model_settings": {
                        "customized_name": "test-gpt4",
                        "provider": "openai",
                        "model": "gpt-4",
                    },
                    "system_prompt": "Test prompt",
                    "metadata": {
                        "domain": "test",
                        "decision_authority": "test",
                    },
                },
            }
        }

        loader.load_from_dict(config)

        assert loader.registry.exists("test_role")

    def test_load_from_dict_missing_roles_key(self, loader):
        """Test loading dict without 'roles' key raises error."""
        with pytest.raises(ValueError, match="must contain 'roles' key"):
            loader.load_from_dict({"other_key": {}})

    def test_load_from_dict_invalid_role_config(self, loader):
        """Test loading dict with invalid role config raises error."""
        config = {
            "roles": {
                "invalid_role": {
                    "description": "Invalid",
                    # Missing required fields
                }
            }
        }

        with pytest.raises(ValueError, match="Failed to load role"):
            loader.load_from_dict(config)

    def test_load_multiple_roles_from_dict(self, loader):
        """Test loading multiple roles from dict."""
        config = {
            "roles": {
                "role1": {
                    "description": "Role 1",
                    "model_settings": {
                        "customized_name": "role1-gpt4",
                        "provider": "openai",
                        "model": "gpt-4",
                    },
                    "system_prompt": "Prompt 1",
                    "metadata": {
                        "domain": "domain1",
                        "decision_authority": "auth1",
                    },
                },
                "role2": {
                    "description": "Role 2",
                    "model_settings": {
                        "customized_name": "role2-gpt4",
                        "provider": "openai",
                        "model": "gpt-4",
                    },
                    "system_prompt": "Prompt 2",
                    "metadata": {
                        "domain": "domain2",
                        "decision_authority": "auth2",
                    },
                },
            }
        }

        roles = loader.load_from_dict(config)

        assert len(roles) == 2
        assert loader.registry.exists("role1")
        assert loader.registry.exists("role2")

    def test_load_from_dict_with_tools(self, loader):
        """Test loading role with tools from dict."""
        config = {
            "roles": {
                "dev": {
                    "description": "Developer",
                    "model_settings": {
                        "customized_name": "dev-gpt4",
                        "provider": "openai",
                        "model": "gpt-4",
                    },
                    "system_prompt": "You are a developer...",
                    "tools": ["read_file", "write_file", "run_command"],
                    "metadata": {
                        "domain": "software_development",
                        "decision_authority": "implementation",
                    },
                },
            }
        }

        roles = loader.load_from_dict(config)

        assert len(roles[0].tools) == 3
        assert "run_command" in roles[0].tools

    def test_load_from_dict_without_tools(self, loader):
        """Test loading role without tools defaults to empty list."""
        config = {
            "roles": {
                "marketing": {
                    "description": "Marketing Manager",
                    "model_settings": {
                        "customized_name": "marketing-gpt4",
                        "provider": "openai",
                        "model": "gpt-4",
                    },
                    "system_prompt": "You are a marketing manager...",
                    "metadata": {
                        "domain": "product_marketing",
                        "decision_authority": "positioning",
                    },
                },
            }
        }

        roles = loader.load_from_dict(config)

        assert roles[0].tools == []

    def test_load_from_dict_role_name_inference(self, loader):
        """Test that role name is inferred from dict key if not in config."""
        config = {
            "roles": {
                "inferred_role": {
                    "description": "Role with inferred name",
                    "model_settings": {
                        "customized_name": "inferred-gpt4",
                        "provider": "openai",
                        "model": "gpt-4",
                    },
                    "system_prompt": "Prompt",
                    "metadata": {
                        "domain": "test",
                        "decision_authority": "test",
                    },
                    # No 'role' field - should be inferred from key
                }
            }
        }

        roles = loader.load_from_dict(config)

        assert roles[0].role == "inferred_role"


class TestLoadDefaultRoles:
    """Test the load_default_roles function."""

    def test_load_default_roles_from_package(self):
        """Test loading default roles from package."""
        roles = load_default_roles()

        assert len(roles) == 6
        role_names = [r.role for r in roles]
        assert "marketing" in role_names
        assert "planner" in role_names
        assert "dev_lead" in role_names
        assert "dev" in role_names
        assert "qa" in role_names
        assert "sre" in role_names

    def test_load_default_roles_from_custom_path(self, temp_yaml_file):
        """Test loading default roles from custom path."""
        roles = load_default_roles(temp_yaml_file)

        assert len(roles) == 2
        role_names = [r.role for r in roles]
        assert "dev" in role_names
        assert "qa" in role_names


class TestRoleLoaderEdgeCases:
    """Test edge cases for RoleLoader."""

    def test_load_role_with_special_characters(self, loader):
        """Test loading role with special characters."""
        config = {
            "roles": {
                "dev-lead-v2.0": {
                    "description": "Developer v2.0",
                    "model_settings": {
                        "customized_name": "dev-lead-v2.0-gpt4",
                        "provider": "openai",
                        "model": "gpt-4",
                    },
                    "system_prompt": "Prompt",
                    "metadata": {
                        "domain": "test",
                        "decision_authority": "test",
                    },
                },
            }
        }

        roles = loader.load_from_dict(config)

        assert roles[0].role == "dev-lead-v2.0"

    def test_load_role_with_long_system_prompt(self, loader):
        """Test loading role with very long system prompt."""
        long_prompt = "This is a very long system prompt. " * 100

        config = {
            "roles": {
                "verbose_role": {
                    "description": "Verbose Role",
                    "model_settings": {
                        "customized_name": "verbose-gpt4",
                        "provider": "openai",
                        "model": "gpt-4",
                    },
                    "system_prompt": long_prompt,
                    "metadata": {
                        "domain": "test",
                        "decision_authority": "test",
                    },
                },
            }
        }

        roles = loader.load_from_dict(config)

        assert len(roles[0].system_prompt) > 1000

    def test_load_role_with_many_tools(self, loader):
        """Test loading role with many tools."""
        tools = [f"tool_{i}" for i in range(20)]

        config = {
            "roles": {
                "tool_heavy_role": {
                    "description": "Tool Heavy Role",
                    "model_settings": {
                        "customized_name": "tool-heavy-gpt4",
                        "provider": "openai",
                        "model": "gpt-4",
                    },
                    "system_prompt": "Prompt",
                    "tools": tools,
                    "metadata": {
                        "domain": "test",
                        "decision_authority": "test",
                    },
                },
            }
        }

        roles = loader.load_from_dict(config)

        assert len(roles[0].tools) == 20
