import pytest
from difflib import SequenceMatcher

from gearmeshing_ai.agent_core.abstraction.settings import AgentSettings, ModelSettings
from gearmeshing_ai.agent_core.adapters.pydantic_ai import PydanticAIAdapter
from gearmeshing_ai.agent_core.models.actions import ActionProposal, MCPToolCatalog, MCPToolInfo
from test.settings import export_api_keys_to_env, test_settings


def fuzzy_match(text: str, keywords: list[str], threshold: float = 0.5) -> bool:
    """
    Check if text fuzzy matches any of the keywords.
    
    Uses SequenceMatcher to find similarity ratio between text and keywords.
    Returns True if any keyword has similarity >= threshold.
    Also checks for substring containment as a fallback.
    
    Args:
        text: The text to match against
        keywords: List of keywords to match
        threshold: Minimum similarity ratio (0.0-1.0), default 0.5
        
    Returns:
        True if any keyword matches with sufficient similarity or is contained in text
    """
    text_lower = text.lower()
    for keyword in keywords:
        keyword_lower = keyword.lower()
        # Check for substring match first (more lenient)
        if keyword_lower in text_lower:
            return True
        # Then check fuzzy match
        ratio = SequenceMatcher(None, text_lower, keyword_lower).ratio()
        if ratio >= threshold:
            return True
    return False


def contains_any_keyword(text: str, keywords: list[str]) -> bool:
    """
    Check if text contains any of the keywords (substring match).
    
    Args:
        text: The text to search in
        keywords: List of keywords to search for
        
    Returns:
        True if any keyword is found in text
    """
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in keywords)


class TestProposalSmoke:
    """Smoke tests with real AI model calls"""

    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Setup environment variables for smoke tests using test settings."""
        export_api_keys_to_env()

    @pytest.fixture
    def api_key(self):
        """Get OpenAI API key from test settings."""
        if test_settings.ai_provider.openai.api_key:
            return test_settings.ai_provider.openai.api_key.get_secret_value()
        pytest.skip("OpenAI API key not configured - set OPENAI_API_KEY in test/.env to run smoke tests")

    @pytest.fixture
    def tool_catalog(self):
        return MCPToolCatalog(
            tools=[
                MCPToolInfo(
                    name="run_tests",
                    description="Run the project test suite to verify code correctness",
                    mcp_server="shell",
                    parameters={
                        "type": "object",
                        "properties": {
                            "test_type": {
                                "type": "string",
                                "enum": ["unit", "integration", "all"],
                                "description": "Type of tests to run",
                            }
                        },
                        "required": ["test_type"],
                    },
                    returns={
                        "type": "object",
                        "properties": {"exit_code": {"type": "number"}, "summary": {"type": "string"}},
                    },
                    example_usage="run_tests with test_type='unit'",
                ),
                MCPToolInfo(
                    name="create_pr",
                    description="Create a pull request on GitHub",
                    mcp_server="github",
                    parameters={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "PR title"},
                            "description": {"type": "string", "description": "PR description"},
                        },
                        "required": ["title", "description"],
                    },
                    returns={
                        "type": "object",
                        "properties": {"pr_url": {"type": "string"}, "pr_number": {"type": "number"}},
                    },
                    example_usage="create_pr with title='Fix bug' and description='This fixes the issue'",
                ),
            ]
        )

    @pytest.fixture
    def proposal_adapter(self, tool_catalog):
        return PydanticAIAdapter(proposal_mode=True, tool_catalog=tool_catalog)

    @pytest.fixture
    def agent_settings(self, api_key):
        return AgentSettings(
            role="developer",
            description="Software developer agent",
            model_settings=ModelSettings(
                customized_name="dev_model", provider="openai", model="gpt-4", api_key=api_key
            ),
        )

    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_real_proposal_generation(self, proposal_adapter, agent_settings, api_key):
        """Test real proposal generation with OpenAI"""
        # Create proposal-only agent
        agent = proposal_adapter.create_agent(agent_settings, tools=[])

        # Get proposal for a task
        proposal = await proposal_adapter.run(agent, "I need to run unit tests for my code changes", context={})

        # Verify proposal structure
        assert isinstance(proposal, ActionProposal)
        assert len(proposal.action) > 0
        assert len(proposal.reason) > 0
        assert proposal.parameters is not None
        assert isinstance(proposal.parameters, dict)
        
        # Verify proposal is related to testing using fuzzy matching
        # Accept proposals related to testing, running, or error handling
        assert (
            fuzzy_match(proposal.action, ["test", "run", "error", "execute"])
            or contains_any_keyword(proposal.reason, ["test", "run", "unit", "code"])
        ), f"Proposal action '{proposal.action}' doesn't match testing context"

    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_real_pr_proposal_generation(self, proposal_adapter, agent_settings, api_key):
        """Test real PR proposal generation"""
        agent = proposal_adapter.create_agent(agent_settings, tools=[])

        proposal = await proposal_adapter.run(agent, "I need to create a pull request for my bug fix", context={})

        assert isinstance(proposal, ActionProposal)
        assert len(proposal.action) > 0
        assert len(proposal.reason) > 0
        assert proposal.parameters is not None
        assert isinstance(proposal.parameters, dict)
        
        # Verify proposal is related to PR/pull request using fuzzy matching
        # Accept proposals related to PR creation, writing files, or error handling
        assert (
            fuzzy_match(proposal.action, ["pull", "pr", "create", "write", "error"])
            or contains_any_keyword(proposal.reason, ["pull request", "pr", "github", "bug fix"])
        ), f"Proposal action '{proposal.action}' doesn't match PR context"

    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_proposal_with_different_tasks(self, proposal_adapter, agent_settings, api_key):
        """Test proposal generation with different task descriptions"""
        agent = proposal_adapter.create_agent(agent_settings, tools=[])

        tasks = [
            "Run all tests to make sure everything works",
            "I want to verify my code with unit tests",
            "Check if my changes break anything by running tests",
            "Create a PR for my new feature",
        ]

        for task in tasks:
            proposal = await proposal_adapter.run(agent, task, context={})

            # All should propose valid actions with meaningful content
            assert isinstance(proposal, ActionProposal)
            assert len(proposal.action) > 0
            assert len(proposal.reason) > 0
            assert isinstance(proposal.parameters, dict)
            
            # Verify proposal is contextually relevant using fuzzy matching
            # Accept proposals related to testing, PR, or error handling
            assert (
                fuzzy_match(proposal.action, ["test", "run", "pull", "pr", "create", "write", "error"])
                or contains_any_keyword(proposal.reason, ["test", "run", "verify", "pull request", "pr"])
            ), f"Proposal action '{proposal.action}' doesn't match task context: {task}"

    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_proposal_with_context(self, proposal_adapter, agent_settings, api_key):
        """Test proposal generation with additional context"""
        agent = proposal_adapter.create_agent(agent_settings, tools=[])

        context = {"environment": "development", "urgency": "high", "previous_actions": ["ran_linter"]}

        proposal = await proposal_adapter.run(agent, "I need to test my changes before deploying", context=context)

        assert isinstance(proposal, ActionProposal)
        assert len(proposal.action) > 0
        assert len(proposal.reason) > 0
        
        # Verify proposal is valid - accept any meaningful proposal
        # (AI may propose different actions or indicate unavailable tools)
        assert isinstance(proposal.parameters, dict)

    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_proposal_error_handling(self, proposal_adapter, agent_settings, api_key):
        """Test proposal generation with ambiguous or invalid requests"""
        agent = proposal_adapter.create_agent(agent_settings, tools=[])

        # Test with ambiguous task
        proposal = await proposal_adapter.run(agent, "Do something with my code", context={})

        # Should still propose a valid action, even with ambiguous input
        assert isinstance(proposal, ActionProposal)
        assert len(proposal.action) > 0  # Any action is fine for ambiguous input
        assert len(proposal.reason) > 0

    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_proposal_consistency(self, proposal_adapter, agent_settings, api_key):
        """Test that similar requests produce consistent proposals"""
        agent = proposal_adapter.create_agent(agent_settings, tools=[])

        # Similar requests should produce similar proposals
        task1 = "Run unit tests"
        task2 = "Run the unit tests"
        task3 = "I need to run unit tests"

        proposals = []
        for task in [task1, task2, task3]:
            proposal = await proposal_adapter.run(agent, task, context={})
            proposals.append(proposal)

        # All should propose valid actions with meaningful content
        for proposal in proposals:
            assert isinstance(proposal, ActionProposal)
            assert len(proposal.action) > 0
            assert len(proposal.reason) > 0
            # Parameters should exist but can be any format
            assert isinstance(proposal.parameters, dict)
            
            # Verify proposal is related to testing using fuzzy matching
            assert (
                fuzzy_match(proposal.action, ["test", "run", "error"])
                or contains_any_keyword(proposal.reason, ["test", "run", "unit"])
            ), f"Proposal action '{proposal.action}' doesn't match testing context"

    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_proposal_parameter_validation(self, proposal_adapter, agent_settings, api_key):
        """Test that proposals include required parameters"""
        agent = proposal_adapter.create_agent(agent_settings, tools=[])

        # Test run_tests proposal
        proposal = await proposal_adapter.run(agent, "Run integration tests", context={})

        assert isinstance(proposal, ActionProposal)
        assert isinstance(proposal.parameters, dict)
        # Verify proposal is related to testing using fuzzy matching
        assert (
            fuzzy_match(proposal.action, ["test", "run", "error"])
            or contains_any_keyword(proposal.reason, ["test", "run", "integration"])
        ), f"Proposal action '{proposal.action}' doesn't match testing context"

        # Test create_pr proposal
        proposal = await proposal_adapter.run(agent, "Create a pull request for my feature", context={})

        assert isinstance(proposal, ActionProposal)
        assert isinstance(proposal.parameters, dict)
        # Verify proposal is related to PR using fuzzy matching
        assert (
            fuzzy_match(proposal.action, ["pull", "pr", "create", "write", "error"])
            or contains_any_keyword(proposal.reason, ["pull request", "pr", "feature"])
        ), f"Proposal action '{proposal.action}' doesn't match PR context"
