"""Unit tests for PydanticAI adapter."""

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from gearmeshing_ai.agent_core.abstraction.settings import AgentSettings, ModelSettings
from gearmeshing_ai.agent_core.adapters.pydantic_ai import PydanticAIAdapter


# Mock the PydanticAgent class for isinstance checks
class MockPydanticAgent:
    """Mock PydanticAgent class for testing."""

    pass


class TestPydanticAIAdapter:
    """Test suite for PydanticAIAdapter."""

    @pytest.fixture  # type: ignore[untyped-decorator]
    def adapter(self) -> PydanticAIAdapter:
        """Create a PydanticAIAdapter instance for testing."""
        return PydanticAIAdapter()

    @pytest.fixture  # type: ignore[untyped-decorator]
    def sample_agent_settings(self) -> AgentSettings:
        """Create sample agent settings for testing."""
        model_settings = ModelSettings(
            customized_name="test-model", provider="openai", model="gpt-4", temperature=0.7, max_tokens=1000
        )
        return AgentSettings(
            role="assistant",
            description="Test assistant",
            model_settings=model_settings,
            system_prompt="You are a helpful assistant.",
            tools=[],
            metadata={"test": True},
        )

    @pytest.fixture  # type: ignore[untyped-decorator]
    def sample_tools(self) -> list[Any]:
        """Create sample tools for testing."""
        tool1 = Mock()
        tool1.name = "calculator"
        tool1.description = "Performs calculations"

        tool2 = Mock()
        tool2.name = "weather"
        tool2.description = "Gets weather information"

        return [tool1, tool2]

    @pytest.fixture  # type: ignore[untyped-decorator]
    def mock_pydantic_agent(self) -> Any:
        """Create a mock PydanticAgent instance."""
        return Mock(spec=MockPydanticAgent)

    class TestGetModel:
        """Test the _get_model method."""

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_get_openai_model(self, adapter: Any) -> None:
            """Test getting OpenAI model."""
            with patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.OpenAIModel") as mock_model:
                mock_model.return_value = "openai_model"

                result = adapter._get_model("openai", "gpt-4")

                mock_model.assert_called_once_with("gpt-4")
                assert result == "openai_model"

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_get_anthropic_model(self, adapter: Any) -> None:
            """Test getting Anthropic model."""
            with patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.AnthropicModel") as mock_model:
                mock_model.return_value = "anthropic_model"

                result = adapter._get_model("anthropic", "claude-3")

                mock_model.assert_called_once_with("claude-3")
                assert result == "anthropic_model"

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_get_gemini_model_google_provider(self, adapter: Any) -> None:
            """Test getting Gemini model with 'google' provider."""
            with patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.GeminiModel") as mock_model:
                mock_model.return_value = "gemini_model"

                result = adapter._get_model("google", "gemini-pro")

                mock_model.assert_called_once_with("gemini-pro")
                assert result == "gemini_model"

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_get_gemini_model_gemini_provider(self, adapter: Any) -> None:
            """Test getting Gemini model with 'gemini' provider."""
            with patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.GeminiModel") as mock_model:
                mock_model.return_value = "gemini_model"

                result = adapter._get_model("gemini", "gemini-pro")

                mock_model.assert_called_once_with("gemini-pro")
                assert result == "gemini_model"

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_get_unsupported_provider(self, adapter: Any) -> None:
            """Test getting model with unsupported provider."""
            result = adapter._get_model("unsupported", "model-name")

            assert result == "unsupported:model-name"

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_provider_case_insensitive(self, adapter: Any) -> None:
            """Test that provider names are case insensitive."""
            with patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.OpenAIModel") as mock_model:
                mock_model.return_value = "openai_model"

                # Test various cases
                adapter._get_model("OPENAI", "gpt-4")
                mock_model.assert_called_once_with("gpt-4")

                mock_model.reset_mock()
                adapter._get_model("OpenAi", "gpt-4")
                mock_model.assert_called_once_with("gpt-4")

    class TestCreateAgent:
        """Test the create_agent method."""

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_create_agent_openai(self, adapter: Any, sample_agent_settings: Any, sample_tools: Any) -> None:
            """Test creating an agent with OpenAI provider."""
            with (
                patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.OpenAIModel") as mock_model,
                patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.PydanticAgent") as mock_agent_class,
            ):
                mock_model_instance = Mock()
                mock_model.return_value = mock_model_instance
                mock_agent_instance = Mock()
                mock_agent_class.return_value = mock_agent_instance

                result = adapter.create_agent(sample_agent_settings, sample_tools)

                # Verify model creation
                mock_model.assert_called_once_with("gpt-4")

                # Verify agent creation
                mock_agent_class.assert_called_once_with(
                    model=mock_model_instance, system_prompt="You are a helpful assistant."
                )

                assert result is mock_agent_instance

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_create_agent_anthropic(
            self, adapter: Any, sample_agent_settings: Any, sample_tools: Any
        ) -> None:
            """Test creating an agent with Anthropic provider."""
            # Update settings to use Anthropic
            sample_agent_settings.model_settings.provider = "anthropic"
            sample_agent_settings.model_settings.model = "claude-3"

            with (
                patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.AnthropicModel") as mock_model,
                patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.PydanticAgent") as mock_agent_class,
            ):
                mock_model_instance = Mock()
                mock_model.return_value = mock_model_instance
                mock_agent_instance = Mock()
                mock_agent_class.return_value = mock_agent_instance

                result = adapter.create_agent(sample_agent_settings, sample_tools)

                mock_model.assert_called_once_with("claude-3")
                mock_agent_class.assert_called_once_with(
                    model=mock_model_instance, system_prompt="You are a helpful assistant."
                )

                assert result is mock_agent_instance

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_create_agent_with_empty_system_prompt(
            self, adapter: Any, sample_agent_settings: Any, sample_tools: Any
        ) -> None:
            """Test creating an agent with empty system prompt."""
            sample_agent_settings.system_prompt = ""

            with (
                patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.OpenAIModel") as mock_model,
                patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.PydanticAgent") as mock_agent_class,
            ):
                mock_model_instance = Mock()
                mock_model.return_value = mock_model_instance
                mock_agent_instance = Mock()
                mock_agent_class.return_value = mock_agent_instance

                result = adapter.create_agent(sample_agent_settings, sample_tools)

                mock_agent_class.assert_called_once_with(model=mock_model_instance, system_prompt="")

                assert result is mock_agent_instance

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_create_agent_with_no_tools(self, adapter: Any, sample_agent_settings: Any) -> None:
            """Test creating an agent with no tools."""
            with (
                patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.OpenAIModel") as mock_model,
                patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.PydanticAgent") as mock_agent_class,
            ):
                mock_model_instance = Mock()
                mock_model.return_value = mock_model_instance
                mock_agent_instance = Mock()
                mock_agent_class.return_value = mock_agent_instance

                result = adapter.create_agent(sample_agent_settings, [])

                # Tools are not currently passed to PydanticAI (TODO in code)
                mock_agent_class.assert_called_once_with(
                    model=mock_model_instance, system_prompt="You are a helpful assistant."
                )

                assert result is mock_agent_instance

    class TestRun:
        """Test the run method."""

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_run_success(self, adapter: Any, mock_pydantic_agent: Any) -> None:
            """Test successful agent run."""
            # Create a mock PydanticAgent
            mock_run_result = Mock()
            mock_run_result.output = "Test response"
            mock_pydantic_agent.run = AsyncMock(return_value=mock_run_result)

            # Patch isinstance check
            with patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.PydanticAgent", MockPydanticAgent):
                result = await adapter.run(mock_pydantic_agent, "Test prompt")

            mock_pydantic_agent.run.assert_called_once_with("Test prompt")
            assert result == "Test response"

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_run_with_kwargs(self, adapter: Any, mock_pydantic_agent: Any) -> None:
            """Test agent run with additional kwargs."""
            mock_run_result = Mock()
            mock_run_result.output = "Test response"
            mock_pydantic_agent.run = AsyncMock(return_value=mock_run_result)

            # Patch isinstance check
            with patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.PydanticAgent", MockPydanticAgent):
                result = await adapter.run(mock_pydantic_agent, "Test prompt", temperature=0.5, max_tokens=100)

            mock_pydantic_agent.run.assert_called_once_with("Test prompt")
            assert result == "Test response"

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_run_invalid_agent_type(self, adapter: Any) -> None:
            """Test run with invalid agent type."""
            invalid_agent = Mock()  # Not a PydanticAgent instance

            with pytest.raises(ValueError, match=r"Agent must be an instance of pydantic_ai.Agent"):
                await adapter.run(invalid_agent, "Test prompt")

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_run_agent_exception(self, adapter: Any, mock_pydantic_agent: Any) -> None:
            """Test run when agent raises an exception."""
            mock_pydantic_agent.run = AsyncMock(side_effect=Exception("Agent error"))

            # Patch isinstance check
            with (
                patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.PydanticAgent", MockPydanticAgent),
                pytest.raises(Exception, match="Agent error"),
            ):
                await adapter.run(mock_pydantic_agent, "Test prompt")

    class TestRunStream:
        """Test the run_stream method."""

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_run_stream_success(self, adapter: Any, mock_pydantic_agent: Any) -> None:
            """Test successful agent streaming."""
            # Create a mock PydanticAgent with streaming capability
            mock_stream_result = Mock()

            # Create async generator for stream_text
            async def mock_stream_generator() -> AsyncGenerator[str, None]:
                yield "Chunk 1"
                yield "Chunk 2"
                yield "Chunk 3"

            # Make stream_text return an async generator directly
            mock_stream_result.stream_text = mock_stream_generator
            mock_stream_result.__aenter__ = AsyncMock(return_value=mock_stream_result)
            mock_stream_result.__aexit__ = AsyncMock(return_value=None)
            mock_pydantic_agent.run_stream = Mock(return_value=mock_stream_result)

            # Patch isinstance check
            with patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.PydanticAgent", MockPydanticAgent):
                # Collect streamed chunks
                chunks = []
                async for chunk in adapter.run_stream(mock_pydantic_agent, "Test prompt"):
                    chunks.append(chunk)

            assert chunks == ["Chunk 1", "Chunk 2", "Chunk 3"]
            mock_pydantic_agent.run_stream.assert_called_once_with("Test prompt")

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_run_stream_with_kwargs(self, adapter: Any, mock_pydantic_agent: Any) -> None:
            """Test streaming with additional kwargs."""
            mock_stream_result = Mock()

            async def mock_stream_generator() -> AsyncGenerator[str, None]:
                yield "Response"

            mock_stream_result.stream_text = mock_stream_generator
            mock_stream_result.__aenter__ = AsyncMock(return_value=mock_stream_result)
            mock_stream_result.__aexit__ = AsyncMock(return_value=None)
            mock_pydantic_agent.run_stream = Mock(return_value=mock_stream_result)

            # Patch isinstance check
            with patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.PydanticAgent", MockPydanticAgent):
                chunks = []
                async for chunk in adapter.run_stream(mock_pydantic_agent, "Test prompt", temperature=0.8):
                    chunks.append(chunk)

            assert chunks == ["Response"]
            mock_pydantic_agent.run_stream.assert_called_once_with("Test prompt")

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_run_stream_invalid_agent_type(self, adapter: Any) -> None:
            """Test streaming with invalid agent type."""
            invalid_agent = Mock()  # Not a PydanticAgent instance

            with pytest.raises(ValueError, match=r"Agent must be an instance of pydantic_ai.Agent"):
                async for _chunk in adapter.run_stream(invalid_agent, "Test prompt"):
                    pass

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_run_stream_empty_stream(self, adapter: Any, mock_pydantic_agent: Any) -> None:
            """Test streaming with empty response."""
            mock_stream_result = Mock()

            async def mock_stream_generator() -> AsyncGenerator[str, None]:
                if False:  # Never enters, so it's empty
                    yield "nothing"

            mock_stream_result.stream_text = mock_stream_generator
            mock_stream_result.__aenter__ = AsyncMock(return_value=mock_stream_result)
            mock_stream_result.__aexit__ = AsyncMock(return_value=None)
            mock_pydantic_agent.run_stream = Mock(return_value=mock_stream_result)

            # Patch isinstance check
            with patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.PydanticAgent", MockPydanticAgent):
                chunks = []
                async for chunk in adapter.run_stream(mock_pydantic_agent, "Test prompt"):
                    chunks.append(chunk)

            assert chunks == []

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_run_stream_agent_exception(self, adapter: Any, mock_pydantic_agent: Any) -> None:
            """Test streaming when agent raises an exception."""
            mock_pydantic_agent.run_stream = Mock(side_effect=Exception("Streaming error"))

            # Patch isinstance check
            with (
                patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.PydanticAgent", MockPydanticAgent),
                pytest.raises(Exception, match="Streaming error"),
            ):
                async for _chunk in adapter.run_stream(mock_pydantic_agent, "Test prompt"):
                    pass

    class TestIntegration:
        """Integration tests for the adapter."""

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_full_workflow(self, adapter: Any, sample_agent_settings: Any, mock_pydantic_agent: Any) -> None:
            """Test complete workflow from agent creation to execution."""
            # Mock all external dependencies
            with (
                patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.OpenAIModel") as mock_model,
                patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.PydanticAgent") as mock_agent_class,
            ):
                # Setup mocks
                mock_model_instance = Mock()
                mock_model.return_value = mock_model_instance
                
                # Setup mock agent with tool decorator support
                mock_pydantic_agent.tool = Mock(side_effect=lambda f: f)  # tool decorator that returns the function
                mock_agent_class.return_value = mock_pydantic_agent

                # Setup run mock
                mock_run_result = Mock()
                mock_run_result.output = "Integration test response"
                mock_pydantic_agent.run = AsyncMock(return_value=mock_run_result)

                # Create agent
                agent = adapter.create_agent(sample_agent_settings, [])

                # Verify agent creation
                assert agent is mock_pydantic_agent
                mock_agent_class.assert_called_once_with(
                    model=mock_model_instance, system_prompt="You are a helpful assistant."
                )

                # Patch isinstance check and run agent
                with patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.PydanticAgent", MockPydanticAgent):
                    response = await adapter.run(agent, "Integration test prompt")

                assert response == "Integration test response"
                mock_pydantic_agent.run.assert_called_once_with("Integration test prompt")

        @pytest.mark.asyncio  # type: ignore[untyped-decorator]
        async def test_error_handling_workflow(
            self, adapter: Any, sample_agent_settings: Any, mock_pydantic_agent: Any
        ) -> None:
            """Test error handling throughout the workflow."""
            with (
                patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.OpenAIModel") as mock_model,
                patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.PydanticAgent") as mock_agent_class,
            ):
                # Setup mocks with error
                mock_model_instance = Mock()
                mock_model.return_value = mock_model_instance
                
                # Setup mock agent with tool decorator support
                mock_pydantic_agent.tool = Mock(side_effect=lambda f: f)  # tool decorator that returns the function
                mock_agent_class.return_value = mock_pydantic_agent

                # Setup run mock with error
                mock_pydantic_agent.run = AsyncMock(side_effect=RuntimeError("Agent runtime error"))

                # Create agent
                agent = adapter.create_agent(sample_agent_settings, [])

                # Patch isinstance check and run agent
                with (
                    patch("gearmeshing_ai.agent_core.adapters.pydantic_ai.PydanticAgent", MockPydanticAgent),
                    pytest.raises(RuntimeError, match="Agent runtime error"),
                ):
                    await adapter.run(agent, "Error test prompt")
