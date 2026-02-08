import pytest

from gearmeshing_ai.agent_core.models.actions import ActionProposal, MCPToolCatalog, MCPToolInfo


class TestActionProposal:
    def test_action_proposal_creation(self):
        proposal = ActionProposal(
            action="run_tests",
            parameters={"test_type": "unit"},
            reason="Need to verify code changes",
            expected_result="Tests pass",
        )
        assert proposal.action == "run_tests"
        assert proposal.parameters["test_type"] == "unit"
        assert proposal.reason == "Need to verify code changes"
        assert proposal.expected_result == "Tests pass"

    def test_action_proposal_minimal(self):
        proposal = ActionProposal(action="run_tests", reason="Need to verify code changes")
        assert proposal.action == "run_tests"
        assert proposal.parameters is None
        assert proposal.reason == "Need to verify code changes"
        assert proposal.expected_result is None

    def test_action_proposal_validation(self):
        # Pydantic doesn't validate empty strings by default
        # Test that required fields are enforced
        with pytest.raises(ValueError):
            ActionProposal(
                # action missing - should fail
                reason="Some reason"
            )


class TestMCPToolInfo:
    def test_tool_info_creation(self):
        tool = MCPToolInfo(
            name="run_tests",
            description="Run the project test suite",
            mcp_server="shell",
            parameters={"test_type": {"type": "string"}},
            returns={"exit_code": "number"},
        )
        assert tool.name == "run_tests"
        assert tool.mcp_server == "shell"
        assert "test_type" in tool.parameters
        assert tool.returns["exit_code"] == "number"

    def test_tool_info_minimal(self):
        tool = MCPToolInfo(name="run_tests", description="Run tests", mcp_server="shell", parameters={})
        assert tool.name == "run_tests"
        assert tool.parameters == {}
        assert tool.returns is None
        assert tool.example_usage is None


class TestMCPToolCatalog:
    def test_catalog_operations(self):
        tools = [
            MCPToolInfo(name="run_tests", description="Run tests", mcp_server="shell", parameters={}),
            MCPToolInfo(name="create_pr", description="Create PR", mcp_server="github", parameters={}),
        ]
        catalog = MCPToolCatalog(tools=tools)

        assert len(catalog.get_tool_names()) == 2
        assert catalog.find_tool("run_tests") is not None
        assert catalog.find_tool("nonexistent") is None

    def test_catalog_empty(self):
        catalog = MCPToolCatalog(tools=[])
        assert len(catalog.get_tool_names()) == 0
        assert catalog.find_tool("anything") is None

    def test_catalog_duplicate_tools(self):
        tools = [
            MCPToolInfo(name="run_tests", description="Run tests", mcp_server="shell", parameters={}),
            MCPToolInfo(name="run_tests", description="Run tests again", mcp_server="shell", parameters={}),
        ]
        catalog = MCPToolCatalog(tools=tools)

        # Should return the first match
        tool = catalog.find_tool("run_tests")
        assert tool is not None
        assert tool.description == "Run tests"
