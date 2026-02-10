"""Unit tests for roles package selector.

Tests for RoleSelector including:
- Role validation
- Role suggestion based on keywords
- Role information retrieval
- Filtering by domain and authority
"""

import pytest

from gearmeshing_ai.agent.roles.models.role_definition import RoleDefinition, RoleMetadata
from gearmeshing_ai.agent.roles.registry import RoleRegistry
from gearmeshing_ai.agent.roles.selector import RoleSelector


@pytest.fixture
def populated_registry():
    """Create a registry with default roles."""
    registry = RoleRegistry()

    roles_data = {
        "marketing": {
            "description": "Marketing Manager",
            "domain": "product_marketing",
            "authority": "positioning_and_messaging",
        },
        "planner": {
            "description": "Project Manager",
            "domain": "project_management",
            "authority": "planning_and_estimation",
        },
        "dev_lead": {
            "description": "Tech Lead",
            "domain": "technical_leadership",
            "authority": "architecture_and_code_approval",
        },
        "dev": {
            "description": "Developer",
            "domain": "software_development",
            "authority": "implementation",
        },
        "qa": {
            "description": "QA Engineer",
            "domain": "quality_assurance",
            "authority": "quality_assessment",
        },
        "sre": {
            "description": "SRE Engineer",
            "domain": "site_reliability_engineering",
            "authority": "infrastructure_and_deployment",
        },
    }

    for role_name, role_info in roles_data.items():
        metadata = RoleMetadata(
            domain=role_info["domain"],
            decision_authority=role_info["authority"],
        )

        role = RoleDefinition(
            role=role_name,
            description=role_info["description"],
            model_provider="openai",
            model_name="gpt-4",
            customized_model_name=f"{role_name}-gpt4",
            system_prompt=f"You are a {role_name}...",
            metadata=metadata,
        )

        registry.register(role)

    return registry


@pytest.fixture
def selector(populated_registry):
    """Create a selector with populated registry."""
    return RoleSelector(populated_registry)


class TestRoleSelector:
    """Test RoleSelector functionality."""

    def test_validate_existing_role(self, selector):
        """Test validating an existing role."""
        assert selector.validate_role("dev") is True
        assert selector.validate_role("dev_lead") is True
        assert selector.validate_role("qa") is True

    def test_validate_nonexistent_role(self, selector):
        """Test validating a non-existent role."""
        assert selector.validate_role("nonexistent") is False
        assert selector.validate_role("invalid_role") is False

    def test_list_available_roles(self, selector):
        """Test listing available roles."""
        roles = selector.list_available_roles()

        assert len(roles) == 6
        assert "dev" in roles
        assert "dev_lead" in roles
        assert "qa" in roles
        assert "marketing" in roles
        assert "planner" in roles
        assert "sre" in roles

    def test_get_role_info(self, selector):
        """Test getting role information."""
        info = selector.get_role_info("dev_lead")

        assert info["role"] == "dev_lead"
        assert info["description"] == "Tech Lead"
        assert info["model_provider"] == "openai"
        assert info["model_name"] == "gpt-4"
        assert info["domain"] == "technical_leadership"
        assert info["decision_authority"] == "architecture_and_code_approval"

    def test_get_role_info_nonexistent(self, selector):
        """Test getting info for non-existent role raises error."""
        with pytest.raises(ValueError, match="Role 'nonexistent' not found"):
            selector.get_role_info("nonexistent")

    def test_suggest_role_marketing(self, selector):
        """Test role suggestion for marketing task."""
        tasks = [
            "Analyze market positioning for new feature",
            "Create customer value proposition",
            "Competitive analysis for our product",
            "Feature messaging strategy",
        ]

        for task in tasks:
            role = selector.suggest_role(task)
            assert role == "marketing", f"Failed for task: {task}"

    def test_suggest_role_planner(self, selector):
        """Test role suggestion for planning task."""
        tasks = [
            "Create project timeline for feature",
            "Break down tasks and estimate effort",
            "Plan milestone schedule",
            "Create project roadmap",
        ]

        for task in tasks:
            role = selector.suggest_role(task)
            assert role == "planner", f"Failed for task: {task}"

    def test_suggest_role_dev_lead(self, selector):
        """Test role suggestion for architecture task."""
        tasks = [
            "Design system architecture",
            "Review code for quality",
            "Technical design decision",
            "Refactor codebase",
        ]

        for task in tasks:
            role = selector.suggest_role(task)
            assert role == "dev_lead", f"Failed for task: {task}"

    def test_suggest_role_dev(self, selector):
        """Test role suggestion for development task."""
        tasks = [
            "Implement new feature",
            "Fix bug in authentication",
            "Write code for API",
            "Develop new module",
        ]

        for task in tasks:
            role = selector.suggest_role(task)
            assert role == "dev", f"Failed for task: {task}"

    def test_suggest_role_qa(self, selector):
        """Test role suggestion for QA task."""
        tasks = [
            "Create test cases",
            "Test quality of feature",
            "Quality assurance testing",
        ]

        for task in tasks:
            role = selector.suggest_role(task)
            assert role == "qa", f"Failed for task: {task}"

    def test_suggest_role_sre(self, selector):
        """Test role suggestion for SRE task."""
        tasks = [
            "Deploy to production",
            "Infrastructure setup",
            "Monitor system performance",
            "Incident response",
        ]

        for task in tasks:
            role = selector.suggest_role(task)
            assert role == "sre", f"Failed for task: {task}"

    def test_suggest_role_no_match(self, selector):
        """Test role suggestion with no matching keywords."""
        role = selector.suggest_role("xyz abc def ghi")

        assert role is None

    def test_suggest_role_case_insensitive(self, selector):
        """Test that suggestion is case-insensitive."""
        role_lower = selector.suggest_role("design system architecture")
        role_upper = selector.suggest_role("DESIGN SYSTEM ARCHITECTURE")

        assert role_lower == role_upper == "dev_lead"

    def test_get_role_for_task_with_preference(self, selector):
        """Test get_role_for_task with preferred role."""
        role = selector.get_role_for_task(
            "Some task description",
            preferred_role="dev_lead",
        )

        assert role == "dev_lead"

    def test_get_role_for_task_invalid_preference(self, selector):
        """Test get_role_for_task with invalid preferred role."""
        # Should fall back to suggestion
        role = selector.get_role_for_task(
            "Create test cases",
            preferred_role="invalid_role",
        )

        assert role == "qa"  # Suggested based on task

    def test_get_role_for_task_no_preference_with_suggestion(self, selector):
        """Test get_role_for_task without preference but with suggestion."""
        role = selector.get_role_for_task(
            "Design the system architecture",
            preferred_role=None,
        )

        assert role == "dev_lead"

    def test_get_role_for_task_no_preference_no_suggestion(self, selector):
        """Test get_role_for_task with no preference and no suggestion."""
        with pytest.raises(ValueError, match="Could not determine appropriate role"):
            selector.get_role_for_task(
                "xyz abc def ghi",
                preferred_role=None,
            )

    def test_get_roles_by_domain(self, selector):
        """Test filtering roles by domain."""
        roles = selector.get_roles_by_domain("software_development")

        assert len(roles) == 1
        assert "dev" in roles

    def test_get_roles_by_domain_multiple(self, selector):
        """Test filtering when multiple roles in domain."""
        # Add another dev role
        registry = selector.registry
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
        registry.register(another_dev)

        roles = selector.get_roles_by_domain("software_development")

        assert len(roles) == 2
        assert "dev" in roles
        assert "dev_senior" in roles

    def test_get_roles_by_domain_nonexistent(self, selector):
        """Test filtering by non-existent domain."""
        roles = selector.get_roles_by_domain("nonexistent_domain")

        assert len(roles) == 0

    def test_get_roles_by_authority(self, selector):
        """Test filtering roles by authority."""
        roles = selector.get_roles_by_authority("architecture_and_code_approval")

        assert len(roles) == 1
        assert "dev_lead" in roles

    def test_get_roles_by_authority_multiple(self, selector):
        """Test filtering when multiple roles have same authority."""
        registry = selector.registry
        metadata = RoleMetadata(
            domain="technical_leadership",
            decision_authority="architecture_and_code_approval",
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
        registry.register(another_lead)

        roles = selector.get_roles_by_authority("architecture_and_code_approval")

        assert len(roles) == 2
        assert "dev_lead" in roles
        assert "architect" in roles

    def test_print_available_roles(self, selector, capsys):
        """Test printing available roles."""
        selector.print_available_roles()

        captured = capsys.readouterr()

        assert "Available Roles" in captured.out
        assert "DEV" in captured.out
        assert "DEV_LEAD" in captured.out
        assert "QA" in captured.out


class TestRoleSelectorEdgeCases:
    """Test edge cases for RoleSelector."""

    def test_suggest_role_with_multiple_keywords(self, selector):
        """Test suggestion with multiple matching keywords."""
        # Task with keywords from multiple roles
        task = "Design and implement new feature with testing"

        role = selector.suggest_role(task)

        # Should match one of the roles (dev_lead or dev or qa)
        assert role in ["dev_lead", "dev", "qa"]

    def test_suggest_role_with_partial_keyword(self, selector):
        """Test suggestion with partial keyword match."""
        # "design" is a keyword for dev_lead
        role = selector.suggest_role("design decision")

        assert role == "dev_lead"

    def test_empty_registry(self):
        """Test selector with empty registry."""
        empty_registry = RoleRegistry()
        selector = RoleSelector(empty_registry)

        assert selector.list_available_roles() == []
        assert selector.suggest_role("any task") is None

    def test_selector_with_custom_registry(self):
        """Test selector with custom registry."""
        custom_registry = RoleRegistry()

        metadata = RoleMetadata(
            domain="custom",
            decision_authority="custom",
        )

        custom_role = RoleDefinition(
            role="custom_role",
            description="Custom Role",
            model_provider="openai",
            model_name="gpt-4",
            customized_model_name="custom-gpt4",
            system_prompt="Custom prompt",
            metadata=metadata,
        )

        custom_registry.register(custom_role)

        selector = RoleSelector(custom_registry)

        assert selector.validate_role("custom_role")
        assert len(selector.list_available_roles()) == 1
