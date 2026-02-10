"""Unit tests for roles package registry.

Tests for RoleRegistry including:
- Role registration and retrieval
- Role listing and filtering
- Error handling
- Singleton pattern
"""

import pytest

from gearmeshing_ai.agent.roles.models.role_definition import RoleDefinition, RoleMetadata
from gearmeshing_ai.agent.roles.registry import RoleRegistry, get_global_registry


@pytest.fixture
def registry():
    """Create a fresh registry for each test."""
    return RoleRegistry()


@pytest.fixture
def sample_roles():
    """Create sample roles for testing."""
    metadata_dev = RoleMetadata(
        domain="software_development",
        decision_authority="implementation",
    )

    metadata_lead = RoleMetadata(
        domain="technical_leadership",
        decision_authority="architecture",
    )

    metadata_qa = RoleMetadata(
        domain="quality_assurance",
        decision_authority="quality_assessment",
    )

    return {
        "dev": RoleDefinition(
            role="dev",
            description="Developer",
            model_provider="openai",
            model_name="gpt-4",
            customized_model_name="dev-gpt4",
            system_prompt="You are a developer...",
            tools=["read_file", "write_file"],
            metadata=metadata_dev,
        ),
        "dev_lead": RoleDefinition(
            role="dev_lead",
            description="Tech Lead",
            model_provider="openai",
            model_name="gpt-4-turbo",
            customized_model_name="dev-lead-gpt4-turbo",
            system_prompt="You are a tech lead...",
            tools=["read_file", "write_file", "run_command"],
            metadata=metadata_lead,
        ),
        "qa": RoleDefinition(
            role="qa",
            description="QA Engineer",
            model_provider="openai",
            model_name="gpt-4",
            customized_model_name="qa-gpt4",
            system_prompt="You are a QA engineer...",
            tools=["read_file", "write_file"],
            metadata=metadata_qa,
        ),
    }


class TestRoleRegistry:
    """Test RoleRegistry functionality."""

    def test_register_single_role(self, registry, sample_roles):
        """Test registering a single role."""
        registry.register(sample_roles["dev"])

        assert registry.exists("dev")
        assert len(registry) == 1

    def test_register_multiple_roles(self, registry, sample_roles):
        """Test registering multiple roles."""
        for role in sample_roles.values():
            registry.register(role)

        assert len(registry) == 3
        assert registry.exists("dev")
        assert registry.exists("dev_lead")
        assert registry.exists("qa")

    def test_get_existing_role(self, registry, sample_roles):
        """Test retrieving an existing role."""
        registry.register(sample_roles["dev"])

        role = registry.get("dev")

        assert role is not None
        assert role.role == "dev"
        assert role.description == "Developer"

    def test_get_nonexistent_role(self, registry):
        """Test retrieving a non-existent role returns None."""
        role = registry.get("nonexistent")

        assert role is None

    def test_get_or_raise_existing_role(self, registry, sample_roles):
        """Test get_or_raise with existing role."""
        registry.register(sample_roles["dev"])

        role = registry.get_or_raise("dev")

        assert role.role == "dev"

    def test_get_or_raise_nonexistent_role(self, registry):
        """Test get_or_raise raises ValueError for non-existent role."""
        with pytest.raises(ValueError, match="Role 'nonexistent' not found"):
            registry.get_or_raise("nonexistent")

    def test_exists_check(self, registry, sample_roles):
        """Test exists method."""
        registry.register(sample_roles["dev"])

        assert registry.exists("dev") is True
        assert registry.exists("nonexistent") is False

    def test_list_roles(self, registry, sample_roles):
        """Test listing all role names."""
        for role in sample_roles.values():
            registry.register(role)

        roles = registry.list_roles()

        assert len(roles) == 3
        assert "dev" in roles
        assert "dev_lead" in roles
        assert "qa" in roles

    def test_list_all_roles(self, registry, sample_roles):
        """Test listing all role definitions."""
        for role in sample_roles.values():
            registry.register(role)

        all_roles = registry.list_all()

        assert len(all_roles) == 3
        assert all(isinstance(r, RoleDefinition) for r in all_roles)

    def test_get_roles_by_domain(self, registry, sample_roles):
        """Test filtering roles by domain."""
        for role in sample_roles.values():
            registry.register(role)

        dev_roles = registry.get_roles_by_domain("software_development")

        assert len(dev_roles) == 1
        assert dev_roles[0].role == "dev"

    def test_get_roles_by_domain_multiple(self, registry, sample_roles):
        """Test filtering when multiple roles in same domain."""
        # Add another dev role
        metadata = RoleMetadata(
            domain="software_development",
            decision_authority="implementation",
        )
        another_dev = RoleDefinition(
            role="dev_senior",
            description="Senior Developer",
            model_provider="openai",
            model_name="gpt-4-turbo",
            customized_model_name="dev-senior-gpt4-turbo",
            system_prompt="You are a senior developer...",
            metadata=metadata,
        )

        registry.register(sample_roles["dev"])
        registry.register(another_dev)
        registry.register(sample_roles["qa"])

        dev_roles = registry.get_roles_by_domain("software_development")

        assert len(dev_roles) == 2
        assert any(r.role == "dev" for r in dev_roles)
        assert any(r.role == "dev_senior" for r in dev_roles)

    def test_get_roles_by_domain_nonexistent(self, registry, sample_roles):
        """Test filtering by non-existent domain."""
        for role in sample_roles.values():
            registry.register(role)

        roles = registry.get_roles_by_domain("nonexistent_domain")

        assert len(roles) == 0

    def test_get_roles_by_authority(self, registry, sample_roles):
        """Test filtering roles by authority."""
        for role in sample_roles.values():
            registry.register(role)

        arch_roles = registry.get_roles_by_authority("architecture")

        assert len(arch_roles) == 1
        assert arch_roles[0].role == "dev_lead"

    def test_get_roles_by_authority_multiple(self, registry, sample_roles):
        """Test filtering when multiple roles have same authority."""
        # Add another role with same authority
        metadata = RoleMetadata(
            domain="technical_leadership",
            decision_authority="architecture",
        )
        another_lead = RoleDefinition(
            role="architect",
            description="Architect",
            model_provider="openai",
            model_name="gpt-4-turbo",
            customized_model_name="architect-gpt4-turbo",
            system_prompt="You are an architect...",
            metadata=metadata,
        )

        registry.register(sample_roles["dev_lead"])
        registry.register(another_lead)

        arch_roles = registry.get_roles_by_authority("architecture")

        assert len(arch_roles) == 2

    def test_overwrite_existing_role(self, registry, sample_roles):
        """Test that registering same role twice overwrites."""
        registry.register(sample_roles["dev"])
        assert len(registry) == 1

        # Register again with different description
        updated_role = RoleDefinition(
            role="dev",
            description="Updated Developer",
            model_provider="openai",
            model_name="gpt-4",
            customized_model_name="dev-gpt4",
            system_prompt="Updated prompt...",
            metadata=sample_roles["dev"].metadata,
        )
        registry.register(updated_role)

        assert len(registry) == 1
        assert registry.get("dev").description == "Updated Developer"

    def test_clear_registry(self, registry, sample_roles):
        """Test clearing all roles."""
        for role in sample_roles.values():
            registry.register(role)

        assert len(registry) == 3

        registry.clear()

        assert len(registry) == 0
        assert registry.list_roles() == []

    def test_contains_operator(self, registry, sample_roles):
        """Test using 'in' operator."""
        registry.register(sample_roles["dev"])

        assert "dev" in registry
        assert "nonexistent" not in registry

    def test_len_operator(self, registry, sample_roles):
        """Test using len() operator."""
        assert len(registry) == 0

        registry.register(sample_roles["dev"])
        assert len(registry) == 1

        registry.register(sample_roles["dev_lead"])
        assert len(registry) == 2

    def test_repr(self, registry, sample_roles):
        """Test string representation."""
        registry.register(sample_roles["dev"])
        registry.register(sample_roles["qa"])

        repr_str = repr(registry)

        assert "RoleRegistry" in repr_str
        assert "dev" in repr_str
        assert "qa" in repr_str


class TestGlobalRegistry:
    """Test global registry singleton."""

    def test_global_registry_singleton(self):
        """Test that get_global_registry returns same instance."""
        registry1 = get_global_registry()
        registry2 = get_global_registry()

        assert registry1 is registry2

    def test_global_registry_persistence(self, sample_roles):
        """Test that global registry persists across calls."""
        registry = get_global_registry()

        # Clear any existing roles
        registry.clear()

        # Register a role
        registry.register(sample_roles["dev"])

        # Get registry again
        registry2 = get_global_registry()

        assert registry2.exists("dev")
        assert len(registry2) == 1

        # Cleanup
        registry.clear()


class TestRegistryEdgeCases:
    """Test edge cases and error conditions."""

    def test_register_role_with_special_characters(self, registry):
        """Test registering role with special characters in name."""
        metadata = RoleMetadata(
            domain="test",
            decision_authority="test",
        )

        role = RoleDefinition(
            role="dev-lead-v2.0",
            description="Developer",
            model_provider="openai",
            model_name="gpt-4",
            customized_model_name="dev-lead-v2.0",
            system_prompt="Test",
            metadata=metadata,
        )

        registry.register(role)

        assert registry.exists("dev-lead-v2.0")
        assert registry.get("dev-lead-v2.0") is not None

    def test_register_role_with_empty_description(self, registry):
        """Test registering role with empty description."""
        metadata = RoleMetadata(
            domain="test",
            decision_authority="test",
        )

        role = RoleDefinition(
            role="test_role",
            description="",
            model_provider="openai",
            model_name="gpt-4",
            customized_model_name="test-gpt4",
            system_prompt="Test",
            metadata=metadata,
        )

        registry.register(role)

        assert registry.exists("test_role")

    def test_get_roles_by_domain_case_sensitive(self, registry, sample_roles):
        """Test that domain filtering is case-sensitive."""
        registry.register(sample_roles["dev"])

        roles_lower = registry.get_roles_by_domain("software_development")
        roles_upper = registry.get_roles_by_domain("SOFTWARE_DEVELOPMENT")

        assert len(roles_lower) == 1
        assert len(roles_upper) == 0
