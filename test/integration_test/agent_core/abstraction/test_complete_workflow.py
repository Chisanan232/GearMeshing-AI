"""
Integration tests for complete agent creation and execution workflow.
"""

import asyncio
from typing import Any, Optional, AsyncGenerator, cast
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import SecretStr

from gearmeshing_ai.agent_core.abstraction import (
    AgentAdapter,
    AgentFactory,
    AgentSettings,
    EnvManager,
    MCPClientAbstraction,
    ModelSettings,
)


class ProductionAgentAdapter(AgentAdapter):
    """Production-like adapter implementation for comprehensive testing."""

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.created_agents: list[Any] = []
        self.execution_history: list[dict[str, Any]] = []
        self.streaming_history: list[dict[str, Any]] = []

    def create_agent(self, settings: AgentSettings, tools: list[Any]) -> Any:
        agent = ProductionAgent(settings, tools, self.config)
        self.created_agents.append(agent)
        return agent

    async def run(self, agent: Any, prompt: str, **kwargs: Any) -> Any:
        execution_record = {
            "agent": agent,
            "prompt": prompt,
            "kwargs": kwargs,
            "timestamp": asyncio.get_event_loop().time(),
            "tools_used": [],
        }

        # Simulate tool usage if tools are available
        if agent.tools:
            for tool in agent.tools[:2]:  # Use up to 2 tools
                if hasattr(tool, "execute"):
                    result = await tool.execute(prompt)
                    execution_record["tools_used"].append({"tool": tool, "result": result})

        response = await agent._generate_response(prompt, **kwargs)
        execution_record["response"] = response

        self.execution_history.append(execution_record)
        return response

    async def run_stream(self, agent: Any, prompt: str, **kwargs: Any) -> AsyncGenerator[str, None]:  # type: ignore[override]
        streaming_record = {
            "agent": agent,
            "prompt": prompt,
            "kwargs": kwargs,
            "timestamp": asyncio.get_event_loop().time(),
            "chunks": [],
        }

        async for chunk in agent._generate_response_stream(prompt, **kwargs):
            streaming_record["chunks"].append(chunk)
            yield chunk

        self.streaming_history.append(streaming_record)


class ProductionAgent:
    """Production-like agent implementation."""

    def __init__(self, settings: AgentSettings, tools: list[Any], config: dict[str, Any]) -> None:
        self.settings = settings
        self.tools = tools
        self.config = config
        self.conversation_history: list[str] = []
        self.tool_execution_history: list[dict[str, Any]] = []

    async def _generate_response(self, prompt: str, **kwargs: Any) -> str:
        """Generate a response based on settings and prompt."""
        # Simulate processing time
        await asyncio.sleep(0.01)

        # Incorporate system prompt if available
        context = ""
        if self.settings.system_prompt:
            context = f"[System: {self.settings.system_prompt}] "

        # Include tool information
        tool_info = ""
        if self.tools:
            tool_names = [getattr(tool, "name", str(tool)) for tool in self.tools]
            tool_info = f"[Available tools: {', '.join(tool_names)}] "

        response = f"{context}{tool_info}Response from {self.settings.role}: {prompt}"

        # Apply model settings influence
        model_settings = self.settings.model_settings
        temperature = None
        if isinstance(model_settings, ModelSettings):
            temperature = model_settings.temperature
        elif isinstance(model_settings, dict):
            temperature = model_settings.get("temperature")

        if temperature is not None:
            if temperature > 0.8:
                response += " (creative)"
            elif temperature < 0.3:
                response += " (precise)"

        return response

    async def _generate_response_stream(self, prompt: str, **kwargs: Any) -> AsyncGenerator[str, None]:
        """Generate streaming response."""
        response = await self._generate_response(prompt, **kwargs)

        # Split response into chunks
        words = response.split()
        current_chunk = ""

        for i, word in enumerate(words):
            current_chunk += word + " "

            # Yield chunk every 3 words or at the end
            if (i + 1) % 3 == 0 or i == len(words) - 1:
                yield current_chunk.strip()
                current_chunk = ""
                await asyncio.sleep(0.005)  # Simulate streaming delay


class ProductionMCPClient(MCPClientAbstraction):
    """Production-like MCP client implementation."""

    def __init__(self, tools_registry: Optional[dict[str, Any]] = None, config: Optional[dict[str, Any]] = None) -> None:
        self.tools_registry = tools_registry or {}
        self.config = config or {}
        self.connection_pool: dict[str, Any] = {}
        self.request_history: list[dict[str, Any]] = []
        self.error_rate = 0.0  # Simulate occasional errors

    async def get_tools(self, tool_names: list[str]) -> list[Any]:
        """Fetch tools with production-like behavior."""
        self.request_history.append({"tool_names": tool_names, "timestamp": asyncio.get_event_loop().time()})

        # Simulate occasional errors
        if self.error_rate > 0 and len(self.request_history) % int(1 / self.error_rate) == 0:
            raise RuntimeError(f"MCP server error (simulated {self.error_rate * 100}% failure rate)")

        tools = []
        for name in tool_names:
            # Check connection pool
            if name not in self.connection_pool:
                self.connection_pool[name] = self._create_tool_connection(name)

            tools.append(self.connection_pool[name])

        return tools

    def _create_tool_connection(self, name: str) -> Any:
        """Create a tool connection."""
        if name in self.tools_registry:
            tool = self.tools_registry[name]
        else:
            # Create a mock tool
            tool = Mock(name=f"MCPTool_{name}")
            tool.name = name
            tool.description = f"Auto-generated MCP tool: {name}"
            tool.execute = AsyncMock(return_value=f"Result from {name}")

        return tool


@pytest.mark.asyncio
class TestCompleteWorkflowIntegration:
    """Integration tests for complete agent creation and execution workflow."""

    @pytest.fixture  # type: ignore[untyped-decorator]
    def production_config(self) -> dict[str, Any]:
        """Production-like configuration."""
        return {
            "max_concurrent_agents": 10,
            "default_timeout": 30,
            "enable_caching": True,
            "tool_timeout": 5,
            "streaming_chunk_size": 3,
        }

    @pytest.fixture  # type: ignore[untyped-decorator]
    def adapter(self, production_config: dict[str, Any]) -> ProductionAgentAdapter:
        """Production-like adapter."""
        return ProductionAgentAdapter(production_config)

    @pytest.fixture  # type: ignore[untyped-decorator]
    def tools_registry(self) -> dict[str, Any]:
        """Comprehensive tools registry."""
        calculator = Mock(name="calculator")
        calculator.name = "calculator"
        calculator.description = "Mathematical calculations"
        calculator.execute = AsyncMock(return_value="42")

        weather = Mock(name="weather")
        weather.name = "weather"
        weather.description = "Weather information"
        weather.execute = AsyncMock(return_value="Sunny, 72°F")

        database = Mock(name="database")
        database.name = "database"
        database.description = "Database queries"
        database.execute = AsyncMock(return_value="Query results: 5 rows")

        file_manager = Mock(name="file_manager")
        file_manager.name = "file_manager"
        file_manager.description = "File operations"
        file_manager.execute = AsyncMock(return_value="File processed successfully")

        return {"calculator": calculator, "weather": weather, "database": database, "file_manager": file_manager}

    @pytest.fixture  # type: ignore[untyped-decorator]
    def mcp_client(self, tools_registry: dict[str, Any], production_config: dict[str, Any]) -> ProductionMCPClient:
        """Production-like MCP client."""
        return ProductionMCPClient(tools_registry, production_config)

    @pytest.fixture  # type: ignore[untyped-decorator]
    def factory(self, adapter: ProductionAgentAdapter, mcp_client: ProductionMCPClient) -> AgentFactory:
        """Factory with production-like components."""
        return AgentFactory(adapter, mcp_client)

    @pytest.fixture  # type: ignore[untyped-decorator]
    def comprehensive_model_settings(self) -> ModelSettings:
        """Comprehensive model settings for testing."""
        return ModelSettings(
            customized_name="production-gpt4",
            provider="openai",
            model="gpt-4",
            api_key="sk-production-key",
            temperature=0.7,
            max_tokens=2048,
            additional_params={
                "top_p": 0.9,
                "frequency_penalty": 0.1,
                "presence_penalty": 0.1,
                "logit_bias": {},
                "stop_sequences": [],
            },
        )

    @pytest.fixture  # type: ignore[untyped-decorator]
    def agent_configurations(self, comprehensive_model_settings: ModelSettings) -> dict[str, AgentSettings]:
        """Multiple agent configurations for comprehensive testing."""
        return {
            "assistant": AgentSettings(
                role="assistant",
                description="General purpose AI assistant",
                model_settings=comprehensive_model_settings,
                tools=["calculator", "weather"],
                system_prompt="You are a helpful AI assistant. Be concise and accurate.",
                metadata={"category": "general", "priority": "high"},
            ),
            "analyst": AgentSettings(
                role="analyst",
                description="Data analysis specialist",
                model_settings=comprehensive_model_settings.model_copy(update={"temperature": 0.3}),
                tools=["database", "calculator"],
                system_prompt="You are a data analyst. Focus on accuracy and details.",
                metadata={"category": "analysis", "priority": "medium"},
            ),
            "developer": AgentSettings(
                role="developer",
                description="Software development assistant",
                model_settings=comprehensive_model_settings.model_copy(update={"temperature": 0.5}),
                tools=["file_manager", "calculator"],
                system_prompt="You are a developer assistant. Provide code examples.",
                metadata={"category": "development", "priority": "medium"},
            ),
        }

    async def test_complete_multi_agent_workflow(self, factory: AgentFactory, agent_configurations: dict[str, AgentSettings]) -> None:
        """Test complete workflow with multiple agents."""
        # Register all agents
        for role, settings in agent_configurations.items():
            factory.register_agent_settings(settings)

        # Create all agents
        agents = {}
        for role in agent_configurations.keys():
            agents[role] = await factory.get_or_create_agent(role)

        # Verify all agents were created correctly
        assert len(agents) == 3
        assert all(isinstance(agent, ProductionAgent) for agent in agents.values())

        # Verify agent-specific configurations
        assert agents["assistant"].settings.system_prompt == "You are a helpful AI assistant. Be concise and accurate."
        assert agents["analyst"].settings.model_settings.temperature == 0.3
        assert agents["developer"].tools[0].name == "file_manager"

        # Execute different prompts on different agents
        assistant_response = await factory.adapter.run(agents["assistant"], "What is 2+2?")
        analyst_response = await factory.adapter.run(agents["analyst"], "Analyze this dataset")
        developer_response = await factory.adapter.run(agents["developer"], "Help me debug this code")

        # Verify responses are agent-specific
        assert "Response from assistant:" in assistant_response
        assert "Response from analyst:" in analyst_response
        assert "Response from developer:" in developer_response

        # Verify execution history
        assert len(cast(ProductionAgentAdapter, factory.adapter).execution_history) == 3
        assert all(record["response"] is not None for record in cast(ProductionAgentAdapter, factory.adapter).execution_history)

    async def test_streaming_workflow_with_multiple_agents(self, factory: AgentFactory, agent_configurations: dict[str, AgentSettings]) -> None:
        """Test streaming workflow across multiple agents."""
        # Register agents
        for settings in agent_configurations.values():
            factory.register_agent_settings(settings)

        # Test streaming for each agent
        streaming_results = {}

        for role in agent_configurations.keys():
            agent = await factory.get_or_create_agent(role)
            chunks = []

            async for chunk in cast(AsyncGenerator[str, None], factory.adapter.run_stream(agent, f"Tell me about {role}")):
                chunks.append(chunk)

            streaming_results[role] = chunks

        # Verify streaming results
        assert len(streaming_results) == 3
        for role, chunks in streaming_results.items():
            assert len(chunks) > 0
            # Join all chunks and check the complete response
            full_response = " ".join(chunks)
            assert f"Response from {role}:" in full_response, (
                f"Full response '{full_response}' does not contain 'Response from {role}:'"
            )

        # Verify streaming history
        assert len(cast(ProductionAgentAdapter, factory.adapter).streaming_history) == 3

    async def test_concurrent_agent_execution(self, factory: AgentFactory, agent_configurations: dict[str, AgentSettings]) -> None:
        """Test concurrent execution of multiple agents."""
        # Register agents
        for settings in agent_configurations.values():
            factory.register_agent_settings(settings)

        # Create agents
        agents = {}
        for role in agent_configurations.keys():
            agents[role] = await factory.get_or_create_agent(role)

        # Execute concurrent tasks
        async def execute_agent_task(agent: Any, prompt: str) -> Any:
            return await factory.adapter.run(agent, prompt)

        tasks = [
            execute_agent_task(agents["assistant"], "Help me with math"),
            execute_agent_task(agents["analyst"], "Analyze trends"),
            execute_agent_task(agents["developer"], "Review this code"),
            execute_agent_task(agents["assistant"], "Another task"),
            execute_agent_task(agents["analyst"], "More analysis"),
        ]

        results = await asyncio.gather(*tasks)

        # Verify all tasks completed
        assert len(results) == 5
        assert all(result is not None for result in results)

        # Verify execution history includes all tasks
        assert len(cast(ProductionAgentAdapter, factory.adapter).execution_history) == 5

    async def test_workflow_with_override_settings(self, factory: AgentFactory, agent_configurations: dict[str, AgentSettings]) -> None:
        """Test workflow with dynamic override settings."""
        # Register base agent
        factory.register_agent_settings(agent_configurations["assistant"])

        # Create agents with different overrides
        base_agent = await factory.get_or_create_agent("assistant")

        creative_override = {"model_settings": {"temperature": 0.9}, "system_prompt": "Be creative and imaginative"}
        creative_agent = await factory.get_or_create_agent("assistant", creative_override)

        precise_override = {"model_settings": {"temperature": 0.1}, "system_prompt": "Be precise and factual"}
        precise_agent = await factory.get_or_create_agent("assistant", precise_override)

        # Execute same prompt on all agents
        prompt = "Describe the color blue"

        base_response = await factory.adapter.run(base_agent, prompt)
        creative_response = await factory.adapter.run(creative_agent, prompt)
        precise_response = await factory.adapter.run(precise_agent, prompt)

        # Verify different responses due to overrides
        assert base_response != creative_response
        assert base_response != precise_response
        assert creative_response != precise_response

        # Verify override characteristics
        assert "creative" in creative_response.lower()
        assert "precise" in precise_response.lower()

        # Verify model_settings were applied (check if they exist)
        if hasattr(creative_agent.settings.model_settings, "temperature"):
            assert creative_agent.settings.model_settings.temperature == 0.9
        else:
            # If it's a dict due to mock behavior
            assert creative_agent.settings.model_settings.get("temperature") == 0.9

        if hasattr(precise_agent.settings.model_settings, "temperature"):
            assert precise_agent.settings.model_settings.temperature == 0.1
        else:
            # If it's a dict due to mock behavior
            assert precise_agent.settings.model_settings.get("temperature") == 0.1

    async def test_workflow_with_mcp_failures(self, factory: AgentFactory, agent_configurations: dict[str, AgentSettings]) -> None:
        """Test workflow resilience with MCP client failures."""
        # Clear cache to ensure fresh creation
        factory.cache.clear()

        # Configure MCP client to have failures
        assert factory.mcp_client is not None
        factory.mcp_client.error_rate = 0.5  # 50% failure rate
        factory.mcp_client.request_history = []  # Reset history

        # Register agent with tools
        factory.register_agent_settings(agent_configurations["assistant"])

        # Attempt multiple agent creations (some should fail)
        successful_creations = []
        failed_creations = []

        for i in range(10):
            # Clear cache to force MCP client call each time
            factory.cache.clear()
            try:
                agent = await factory.get_or_create_agent("assistant")
                successful_creations.append(agent)
            except RuntimeError as e:
                if "MCP server error" in str(e):
                    failed_creations.append(e)
                else:
                    raise

        # Verify some succeeded and some failed
        assert len(successful_creations) > 0
        assert len(failed_creations) > 0

        # Since we clear cache each time, agents won't be cached
        # Remove this assertion as it doesn't apply with cache clearing
        # if len(successful_creations) > 1:
        #     assert all(agent is successful_creations[0] for agent in successful_creations)

    async def test_workflow_with_environment_integration(self) -> None:
        """Test workflow integration with environment management."""
        # Mock environment variables and settings before creating EnvManager
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("gearmeshing_ai.agent_core.abstraction.env_manager.AIProviderSettings") as mock_settings,
        ):
            # Configure mock settings
            mock_instance = Mock()
            mock_instance.openai_api_key = SecretStr("sk-test-key")
            mock_instance.anthropic_api_key = SecretStr("sk-ant-test-key")
            mock_instance.gemini_api_key = SecretStr("sk-gemini-test-key")
            mock_settings.return_value = mock_instance

            # Create environment manager after patching
            env_manager = EnvManager()

            # Export variables
            env_manager.export_variables()

            # Verify environment variables are set
            import os

            assert os.environ.get("OPENAI_API_KEY") == "sk-test-key"
            assert os.environ.get("ANTHROPIC_API_KEY") == "sk-ant-test-key"

            # Create factory and test workflow
            adapter = ProductionAgentAdapter()
            mcp_client = ProductionMCPClient()
            factory = AgentFactory(adapter, mcp_client)

            # Register and create agent
            model_settings = ModelSettings(customized_name="env-test-model", provider="openai", model="gpt-4")
            agent_settings = AgentSettings(
                role="env-test-agent", description="Environment integration test agent", model_settings=model_settings
            )

            factory.register_agent_settings(agent_settings)
            agent = await factory.get_or_create_agent("env-test-agent")

            # Execute with environment context
            response = await factory.adapter.run(agent, "Test with environment")
            assert "Response from env-test-agent:" in response

    async def test_workflow_performance_characteristics(self, factory: AgentFactory, agent_configurations: dict[str, AgentSettings]) -> None:
        """Test workflow performance characteristics."""
        import time

        # Register agents
        for settings in agent_configurations.values():
            factory.register_agent_settings(settings)

        # Measure performance metrics
        start_time = time.time()

        # Create agents
        creation_times = []
        for role in agent_configurations.keys():
            agent_start = time.time()
            agent = await factory.get_or_create_agent(role)
            agent_end = time.time()
            creation_times.append(agent_end - agent_start)

        # Execute agents
        execution_times = []
        for role in agent_configurations.keys():
            agent = await factory.get_or_create_agent(role)
            exec_start = time.time()
            await factory.adapter.run(agent, f"Test prompt for {role}")
            exec_end = time.time()
            execution_times.append(exec_end - exec_start)

        total_time = time.time() - start_time

        # Verify performance characteristics
        assert total_time < 5.0  # Should complete within 5 seconds
        assert all(ct < 1.0 for ct in creation_times)  # Each creation < 1 second
        assert all(et < 0.5 for et in execution_times)  # Each execution < 0.5 seconds

        # Verify caching effectiveness (second creation should be faster)
        if len(creation_times) >= 2:
            # Recreate first agent to test caching
            cache_start = time.time()
            await factory.get_or_create_agent(list(agent_configurations.keys())[0])
            cache_time = time.time() - cache_start
            assert cache_time < 0.01  # Cached creation should be very fast

    async def test_workflow_error_recovery(self, factory: AgentFactory, agent_configurations: dict[str, AgentSettings]) -> None:
        """Test workflow error recovery mechanisms."""
        # Register agent
        factory.register_agent_settings(agent_configurations["assistant"])

        # Create agent
        agent = await factory.get_or_create_agent("assistant")

        # Test normal execution
        normal_response = await factory.adapter.run(agent, "Normal prompt")
        assert normal_response is not None

        # Test execution with problematic prompt
        problematic_response = await factory.adapter.run(agent, "Problematic prompt")
        assert problematic_response is not None

        # Test streaming with error conditions
        chunks = []
        try:
            async for chunk in cast(AsyncGenerator[str, None], factory.adapter.run_stream(agent, "Streaming test")):
                chunks.append(chunk)
                if len(chunks) > 10:  # Prevent infinite loops
                    break
        except Exception as e:
            # Should handle errors gracefully
            assert isinstance(e, (RuntimeError, ValueError))

        # Verify agent is still functional after errors
        recovery_response = await factory.adapter.run(agent, "Recovery test")
        assert recovery_response is not None

    def test_workflow_state_consistency(self, factory: AgentFactory, agent_configurations: dict[str, AgentSettings]) -> None:
        """Test workflow state consistency across operations."""
        # Clear singleton cache
        factory.cache.clear()

        # Initial state
        assert len(factory._agent_settings_registry) == 0
        assert len(factory._model_settings_registry) == 0
        assert len(factory.cache._agents) == 0

        # Register agents
        for settings in agent_configurations.values():
            factory.register_agent_settings(settings)

        # Verify registration state
        assert len(factory._agent_settings_registry) == 3
        assert len(factory._model_settings_registry) == 0  # No model settings registered separately
        assert len(factory.cache._agents) == 0  # No agents created yet

        # The actual state consistency test would require async execution
        # but this verifies the initial state management is correct
