"""
Unit tests for AgentAdapter abstract base class.
"""

from abc import ABC
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import Mock

import pytest

from gearmeshing_ai.agent.abstraction.adapter import AgentAdapter
from gearmeshing_ai.agent.abstraction.settings import AgentSettings, ModelSettings


class MockAgentAdapter(AgentAdapter):
    """Mock implementation of AgentAdapter for testing."""

    def create_agent(self, settings: AgentSettings, tools: list[Any]) -> Any:
        return Mock(spec=["run", "run_stream"])

    async def run(self, agent: Any, prompt: str, **kwargs: Any) -> Any:
        return f"Mock response to: {prompt}"

    async def run_stream(self, agent: Any, prompt: str, **kwargs: Any) -> AsyncGenerator[str, None]:  # type: ignore[override]
        yield f"Mock chunk 1 for: {prompt}"
        yield f"Mock chunk 2 for: {prompt}"


class IncompleteAgentAdapter(AgentAdapter):
    """Incomplete implementation missing required methods."""

    pass


class TestAgentAdapter:
    """Test cases for AgentAdapter abstract base class."""

    def test_agent_adapter_is_abstract_base_class(self) -> None:
        """Test that AgentAdapter is an abstract base class."""
        assert issubclass(AgentAdapter, ABC)
        assert hasattr(AgentAdapter, "__abstractmethods__")

        # Check that required methods are abstract
        abstract_methods = AgentAdapter.__abstractmethods__
        assert "create_agent" in abstract_methods
        assert "run" in abstract_methods
        assert "run_stream" in abstract_methods

    def test_agent_adapter_cannot_be_instantiated_directly(self) -> None:
        """Test that AgentAdapter cannot be instantiated directly."""
        with pytest.raises(TypeError) as exc_info:
            AgentAdapter()  # type: ignore[abstract]

        assert "abstract" in str(exc_info.value).lower()
        assert "create_agent" in str(exc_info.value) or "run" in str(exc_info.value)

    def test_incomplete_adapter_raises_type_error(self) -> None:
        """Test that incomplete adapter implementation raises TypeError."""
        with pytest.raises(TypeError) as exc_info:
            IncompleteAgentAdapter()  # type: ignore[abstract]

        assert "abstract" in str(exc_info.value).lower()

    def test_complete_adapter_can_be_instantiated(self) -> None:
        """Test that complete adapter implementation can be instantiated."""
        adapter = MockAgentAdapter()
        assert isinstance(adapter, AgentAdapter)
        assert isinstance(adapter, MockAgentAdapter)

    def test_create_agent_method_signature(self) -> None:
        """Test create_agent method signature and behavior."""
        adapter = MockAgentAdapter()

        # Create test settings
        model_settings = ModelSettings(customized_name="test-model", provider="openai", model="gpt-4")
        agent_settings = AgentSettings(role="test-agent", description="Test agent", model_settings=model_settings)

        # Test create_agent
        tools = [Mock(), Mock()]
        agent = adapter.create_agent(agent_settings, tools)

        # Should return a mock agent
        assert hasattr(agent, "run")
        assert hasattr(agent, "run_stream")

    def test_run_method_signature(self) -> None:
        """Test run method signature and behavior."""
        adapter = MockAgentAdapter()

        # Create a mock agent
        agent = Mock()

        # Test run method
        import asyncio

        result = asyncio.run(adapter.run(agent, "test prompt", temperature=0.5))

        assert result == "Mock response to: test prompt"

    def test_run_stream_method_signature(self) -> None:
        """Test run_stream method signature and behavior."""
        adapter = MockAgentAdapter()

        # Create a mock agent
        agent = Mock()

        # Test run_stream method
        import asyncio

        chunks = []

        async def collect_chunks() -> None:
            async for chunk in adapter.run_stream(agent, "test prompt"):
                chunks.append(chunk)

        asyncio.run(collect_chunks())

        assert len(chunks) == 2
        assert "Mock chunk 1 for: test prompt" in chunks
        assert "Mock chunk 2 for: test prompt" in chunks

    def test_adapter_methods_accept_various_kwargs(self) -> None:
        """Test that adapter methods properly handle additional kwargs."""
        adapter = MockAgentAdapter()
        agent = Mock()

        import asyncio

        # Test run with various kwargs
        result = asyncio.run(adapter.run(agent, "test prompt", temperature=0.7, max_tokens=1000, custom_param="value"))
        assert result == "Mock response to: test prompt"

        # Test run_stream with various kwargs
        chunks = []

        async def collect_chunks() -> None:
            async for chunk in adapter.run_stream(
                agent, "test prompt", temperature=0.7, max_tokens=1000, custom_param="value"
            ):
                chunks.append(chunk)

        asyncio.run(collect_chunks())
        assert len(chunks) == 2

    def test_adapter_with_complex_tools(self) -> None:
        """Test adapter with complex tool objects."""
        adapter = MockAgentAdapter()

        model_settings = ModelSettings(customized_name="test", provider="openai", model="gpt-4")
        agent_settings = AgentSettings(role="test", description="Test", model_settings=model_settings)

        # Test with various tool types
        tools = [
            Mock(spec=["name", "description"]),
            Mock(spec=["call"]),
            {"tool_name": "dict_tool"},
            "string_tool",
            42,  # Even numbers should be accepted (flexibility)
        ]

        agent = adapter.create_agent(agent_settings, tools)
        assert agent is not None

    def test_adapter_error_handling(self) -> None:
        """Test adapter error handling scenarios."""

        class ErrorAgentAdapter(AgentAdapter):
            def create_agent(self, settings: AgentSettings, tools: list[Any]) -> Any:
                msg = "Cannot create agent"
                raise ValueError(msg)

            async def run(self, agent: Any, prompt: str, **kwargs: Any) -> Any:
                msg = "Run failed"
                raise RuntimeError(msg)

            async def run_stream(self, agent: Any, prompt: str, **kwargs: Any) -> AsyncGenerator[str, None]:  # type: ignore[override]
                # This needs to be an async generator that raises an exception
                if False:  # Never enters, but makes it a generator
                    yield None
                msg = "Stream failed"
                raise RuntimeError(msg)

        adapter = ErrorAgentAdapter()
        model_settings = ModelSettings(customized_name="test", provider="openai", model="gpt-4")
        agent_settings = AgentSettings(role="test", description="Test", model_settings=model_settings)

        # Test create_agent error
        with pytest.raises(ValueError, match="Cannot create agent"):
            adapter.create_agent(agent_settings, [])

        # Test run error
        import asyncio

        with pytest.raises(RuntimeError, match="Run failed"):
            asyncio.run(adapter.run(Mock(), "test"))

        # Test run_stream error
        with pytest.raises(RuntimeError, match="Stream failed"):

            async def test_stream() -> None:
                error_adapter = ErrorAgentAdapter()
                try:
                    async for _chunk in error_adapter.run_stream(Mock(), "test"):
                        pass
                except RuntimeError:
                    raise

            asyncio.run(test_stream())

    def test_adapter_method_return_types(self) -> None:
        """Test that adapter methods return appropriate types."""
        adapter = MockAgentAdapter()
        agent = Mock()

        import asyncio

        # Test run returns Any type
        result = asyncio.run(adapter.run(agent, "test"))
        assert result is not None

        # Test run_stream returns async iterator
        async def test_stream() -> list[str]:
            chunks = []
            async for chunk in adapter.run_stream(agent, "test"):
                chunks.append(chunk)
            return chunks

        result = asyncio.run(test_stream())
        assert isinstance(result, list)
        assert len(result) > 0

    def test_adapter_documentation_strings(self) -> None:
        """Test that adapter methods have proper docstrings."""
        # Test that abstract methods have docstrings
        assert AgentAdapter.create_agent.__doc__ is not None
        assert "Create and return" in AgentAdapter.create_agent.__doc__

        assert AgentAdapter.run.__doc__ is not None
        assert "Run the agent" in AgentAdapter.run.__doc__

        assert AgentAdapter.run_stream.__doc__ is not None
        assert "streaming mode" in AgentAdapter.run_stream.__doc__
