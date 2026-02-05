"""
Unit tests for MCPClientAbstraction abstract base class.
"""

import pytest
from abc import ABC
from typing import Any, List
from unittest.mock import Mock, AsyncMock

from gearmeshing_ai.agent_core.abstraction.mcp import MCPClientAbstraction


class MockMCPClient(MCPClientAbstraction):
    """Mock implementation of MCPClientAbstraction for testing."""
    
    def __init__(self, tools_map=None):
        self.tools_map = tools_map or {}
        self.get_tools_calls = []
    
    async def get_tools(self, tool_names: List[str]) -> List[Any]:
        self.get_tools_calls.append(tool_names)
        return [self.tools_map.get(name, Mock(name=f"tool_{name}")) for name in tool_names]


class IncompleteMCPClient(MCPClientAbstraction):
    """Incomplete implementation missing required methods."""
    pass


class TestMCPClientAbstraction:
    """Test cases for MCPClientAbstraction abstract base class."""

    def test_mcp_client_is_abstract_base_class(self):
        """Test that MCPClientAbstraction is an abstract base class."""
        assert issubclass(MCPClientAbstraction, ABC)
        assert hasattr(MCPClientAbstraction, '__abstractmethods__')
        
        # Check that required methods are abstract
        abstract_methods = MCPClientAbstraction.__abstractmethods__
        assert 'get_tools' in abstract_methods

    def test_mcp_client_cannot_be_instantiated_directly(self):
        """Test that MCPClientAbstraction cannot be instantiated directly."""
        with pytest.raises(TypeError) as exc_info:
            MCPClientAbstraction()
        
        assert "abstract" in str(exc_info.value).lower()
        assert "get_tools" in str(exc_info.value)

    def test_incomplete_mcp_client_raises_type_error(self):
        """Test that incomplete MCP client implementation raises TypeError."""
        with pytest.raises(TypeError) as exc_info:
            IncompleteMCPClient()
        
        assert "abstract" in str(exc_info.value).lower()

    def test_complete_mcp_client_can_be_instantiated(self):
        """Test that complete MCP client implementation can be instantiated."""
        client = MockMCPClient()
        assert isinstance(client, MCPClientAbstraction)
        assert isinstance(client, MockMCPClient)

    def test_get_tools_method_signature(self):
        """Test get_tools method signature and behavior."""
        tools_map = {
            "tool1": Mock(name="tool1"),
            "tool2": Mock(name="tool2"),
            "tool3": Mock(name="tool3")
        }
        client = MockMCPClient(tools_map)
        
        import asyncio
        
        # Test get_tools with existing tools
        tool_names = ["tool1", "tool2"]
        tools = asyncio.run(client.get_tools(tool_names))
        
        assert len(tools) == 2
        assert tools[0] is tools_map["tool1"]
        assert tools[1] is tools_map["tool2"]
        assert client.get_tools_calls == [["tool1", "tool2"]]

    def test_get_tools_with_nonexistent_tools(self):
        """Test get_tools with tools that don't exist in the map."""
        tools_map = {
            "tool1": Mock(name="tool1")
        }
        client = MockMCPClient(tools_map)
        
        import asyncio
        
        # Request tools including non-existent ones
        tool_names = ["tool1", "nonexistent", "another_missing"]
        tools = asyncio.run(client.get_tools(tool_names))
        
        assert len(tools) == 3
        assert tools[0] is tools_map["tool1"]
        assert tools[1] is not None  # Mock created for missing tool
        assert tools[2] is not None  # Mock created for missing tool

    def test_get_tools_with_empty_list(self):
        """Test get_tools with empty tool names list."""
        client = MockMCPClient()
        
        import asyncio
        
        tools = asyncio.run(client.get_tools([]))
        
        assert tools == []
        assert client.get_tools_calls == [[]]

    def test_get_tools_with_duplicate_names(self):
        """Test get_tools with duplicate tool names."""
        tools_map = {
            "tool1": Mock(name="tool1")
        }
        client = MockMCPClient(tools_map)
        
        import asyncio
        
        # Request same tool multiple times
        tool_names = ["tool1", "tool1", "tool1"]
        tools = asyncio.run(client.get_tools(tool_names))
        
        assert len(tools) == 3
        assert all(tool is tools_map["tool1"] for tool in tools)

    def test_get_tools_with_various_name_types(self):
        """Test get_tools with various tool name types."""
        client = MockMCPClient()
        
        import asyncio
        
        # Test with different string types
        tool_names = ["tool1", "tool_2", "TOOL3", "tool-4", "tool5"]
        tools = asyncio.run(client.get_tools(tool_names))
        
        assert len(tools) == 5
        assert all(tool is not None for tool in tools)

    def test_mcp_client_error_handling(self):
        """Test MCP client error handling scenarios."""
        class ErrorMCPClient(MCPClientAbstraction):
            async def get_tools(self, tool_names: List[str]) -> List[Any]:
                raise RuntimeError("MCP connection failed")
        
        client = ErrorMCPClient()
        
        import asyncio
        
        with pytest.raises(RuntimeError, match="MCP connection failed"):
            asyncio.run(client.get_tools(["tool1"]))

    def test_mcp_client_with_complex_tool_objects(self):
        """Test MCP client returning complex tool objects."""
        class ComplexTool:
            def __init__(self, name, config):
                self.name = name
                self.config = config
            
            def __eq__(self, other):
                return isinstance(other, ComplexTool) and self.name == other.name
        
        tools_map = {
            "complex_tool": ComplexTool("complex_tool", {"param": "value"}),
            "simple_tool": Mock(name="simple_tool")
        }
        client = MockMCPClient(tools_map)
        
        import asyncio
        
        tools = asyncio.run(client.get_tools(["complex_tool", "simple_tool"]))
        
        assert len(tools) == 2
        assert tools[0] is tools_map["complex_tool"]
        assert tools[1] is tools_map["simple_tool"]

    def test_mcp_client_return_type_validation(self):
        """Test that get_tools returns correct types."""
        client = MockMCPClient()
        
        import asyncio
        
        tools = asyncio.run(client.get_tools(["tool1", "tool2"]))
        
        # Should return a list
        assert isinstance(tools, list)
        assert len(tools) == 2
        
        # All items should be non-None
        assert all(tool is not None for tool in tools)

    def test_mcp_client_method_documentation(self):
        """Test that MCP client methods have proper docstrings."""
        # Test that abstract method has docstring
        assert MCPClientAbstraction.get_tools.__doc__ is not None
        assert "Fetches tool implementations" in MCPClientAbstraction.get_tools.__doc__
        assert "tool_names" in MCPClientAbstraction.get_tools.__doc__

    def test_mcp_client_async_method(self):
        """Test that get_tools is properly async."""
        client = MockMCPClient()
        
        # Verify the method is async
        import inspect
        assert inspect.iscoroutinefunction(client.get_tools)

    def test_mcp_client_state_tracking(self):
        """Test MCP client can track internal state."""
        class StatefulMCPClient(MCPClientAbstraction):
            def __init__(self):
                self.call_count = 0
                self.tool_requests = []
            
            async def get_tools(self, tool_names: List[str]) -> List[Any]:
                self.call_count += 1
                self.tool_requests.append(tool_names)
                return [Mock(name=f"tool_{name}") for name in tool_names]
        
        client = StatefulMCPClient()
        
        import asyncio
        
        # Make multiple calls
        asyncio.run(client.get_tools(["tool1"]))
        asyncio.run(client.get_tools(["tool2", "tool3"]))
        asyncio.run(client.get_tools(["tool1"]))
        
        # Verify state tracking
        assert client.call_count == 3
        assert client.tool_requests == [["tool1"], ["tool2", "tool3"], ["tool1"]]

    def test_mcp_client_with_none_tool_names(self):
        """Test MCP client behavior with None in tool names list."""
        client = MockMCPClient()
        
        import asyncio
        
        # This should ideally be handled by the implementation
        # but we test that our mock handles it gracefully
        tool_names = ["tool1", None, "tool2"]
        
        try:
            tools = asyncio.run(client.get_tools(tool_names))
            # If it works, verify the results
            assert len(tools) == 3
        except (TypeError, AttributeError):
            # Expected if None is not handled properly
            pass

    def test_mcp_client_performance_characteristics(self):
        """Test MCP client performance characteristics."""
        client = MockMCPClient()
        
        import asyncio
        import time
        
        # Test with many tool names
        tool_names = [f"tool_{i}" for i in range(1000)]
        
        start_time = time.time()
        tools = asyncio.run(client.get_tools(tool_names))
        end_time = time.time()
        
        # Should complete reasonably quickly (less than 1 second for 1000 tools)
        assert end_time - start_time < 1.0
        assert len(tools) == 1000

    def test_mcp_client_concurrent_calls(self):
        """Test MCP client with concurrent calls."""
        client = MockMCPClient()
        
        import asyncio
        
        async def make_concurrent_calls():
            tasks = []
            for i in range(10):
                task = client.get_tools([f"tool_{i}"])
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            return results
        
        results = asyncio.run(make_concurrent_calls())
        
        # Verify all calls completed
        assert len(results) == 10
        for i, result in enumerate(results):
            assert len(result) == 1
            assert result[0] is not None
        
        # Verify all calls were recorded
        assert len(client.get_tools_calls) == 10
