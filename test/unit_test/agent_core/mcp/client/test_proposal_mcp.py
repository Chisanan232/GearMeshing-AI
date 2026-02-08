import pytest
from unittest.mock import AsyncMock, MagicMock
from gearmeshing_ai.agent_core.mcp.client.core import MCPClient, EasyMCPClient
from gearmeshing_ai.agent_core.models.actions import MCPToolCatalog, MCPToolInfo


class MockMCPClient(MCPClient):
    """Mock MCP client for testing"""
    
    def __init__(self):
        super().__init__(None)  # No transport needed for tests
    
    async def get_tools(self, tool_names):
        """Mock implementation of get_tools"""
        return [f"MockTool_{name}" for name in tool_names]


class TestMCPClientProposal:
    
    @pytest.fixture
    def mock_transport(self):
        transport = MagicMock()
        transport.list_tools = AsyncMock(return_value=["run_tests", "create_pr"])
        transport.call_tool = AsyncMock(return_value={"result": "success"})
        return transport
    
    @pytest.fixture
    def mcp_client(self, mock_transport):
        client = MockMCPClient()
        client.set_transport(mock_transport)
        return client
    
    @pytest.mark.asyncio
    async def test_discover_tools_for_agent(self, mcp_client):
        catalog = await mcp_client.discover_tools_for_agent()
        
        assert isinstance(catalog, MCPToolCatalog)
        assert len(catalog.tools) == 2
        assert catalog.find_tool("run_tests") is not None
        assert catalog.find_tool("create_pr") is not None
    
    @pytest.mark.asyncio
    async def test_get_tool_details(self, mcp_client):
        tool_info = await mcp_client._get_tool_details("run_tests")
        
        assert isinstance(tool_info, MCPToolInfo)
        assert tool_info.name == "run_tests"
        assert tool_info.mcp_server == "unknown"
        assert tool_info.parameters == {}
    
    @pytest.mark.asyncio
    async def test_execute_proposed_tool_success(self, mcp_client):
        result = await mcp_client.execute_proposed_tool("run_tests", {"test_type": "unit"})
        
        assert result["success"] is True
        assert result["data"] == {"result": "success"}
        assert result["tool_used"] == "run_tests"
    
    @pytest.mark.asyncio
    async def test_execute_proposed_tool_failure(self, mcp_client):
        # Mock transport to raise exception
        mcp_client._transport.call_tool = AsyncMock(side_effect=Exception("Tool error"))
        
        # Mock metrics to avoid the record_failure error
        mcp_client._metrics.record_failure = MagicMock()
        
        result = await mcp_client.execute_proposed_tool("run_tests", {})
        
        assert result["success"] is False
        assert "Tool error" in result["error"]
        assert result["tool_used"] == "run_tests"

class TestEasyMCPClientProposal:
    
    @pytest.mark.asyncio
    async def test_discover_tools_for_agent_sse(self):
        # Mock the SSE transport
        with pytest.MonkeyPatch().context() as m:
            mock_transport = MagicMock()
            mock_transport.list_tools = AsyncMock(return_value=["run_tests"])
            
            # Mock SSETransport
            mock_sse = MagicMock()
            mock_sse.return_value = mock_transport
            m.setattr("gearmeshing_ai.agent_core.mcp.client.core.SSETransport", mock_sse)
            
            catalog = await EasyMCPClient.discover_tools_for_agent_sse("http://localhost:8082/sse")
            
            assert isinstance(catalog, MCPToolCatalog)
            assert len(catalog.tools) == 1
            assert catalog.tools[0].name == "run_tests"
            assert catalog.tools[0].mcp_server == "http://localhost:8082/sse"
