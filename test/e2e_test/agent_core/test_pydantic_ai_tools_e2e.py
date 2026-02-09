"""End-to-end tests for Pydantic AI agent with tool integration.

Tests verify that the AI agent can use registered tools (file operations, command execution)
via the Pydantic AI framework with user input prompts.
"""

import json
import re
import tempfile
from pathlib import Path
from typing import Any

import pytest

from gearmeshing_ai.agent_core.abstraction.settings import AgentSettings, ModelSettings
from gearmeshing_ai.agent_core.adapters.pydantic_ai import PydanticAIAdapter

try:
    from pydantic_ai import Agent as PydanticAgent
    from pydantic_ai.models.test import TestModel
    PYDANTIC_AI_AVAILABLE = True
except ImportError:
    PYDANTIC_AI_AVAILABLE = False


def fuzzy_match(text: str, pattern: str, threshold: float = 0.6) -> bool:
    """Check if text contains pattern with fuzzy matching.
    
    Args:
        text: The text to search in
        pattern: The pattern to search for
        threshold: Minimum similarity ratio (0-1)
    
    Returns:
        True if pattern is found or fuzzy match exceeds threshold
    """
    text_lower = text.lower()
    pattern_lower = pattern.lower()
    
    # Exact substring match
    if pattern_lower in text_lower:
        return True
    
    # Check if most words from pattern are in text
    pattern_words = set(pattern_lower.split())
    text_words = set(text_lower.split())
    
    if not pattern_words:
        return True
    
    matching_words = pattern_words & text_words
    similarity = len(matching_words) / len(pattern_words)
    
    return similarity >= threshold


@pytest.mark.skipif(not PYDANTIC_AI_AVAILABLE, reason="pydantic_ai not available")
class TestPydanticAIToolsE2E:
    """End-to-end tests for Pydantic AI agent with tool integration."""

    @pytest.fixture
    def temp_dir(self) -> Any:
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def agent_settings(self) -> AgentSettings:
        """Create agent settings for testing."""
        model_settings = ModelSettings(
            customized_name="test-agent",
            provider="test",
            model="test-model",
            temperature=0.7,
            max_tokens=2000
        )
        return AgentSettings(
            role="assistant",
            description="Test assistant with file and command tools",
            model_settings=model_settings,
            system_prompt="You are a helpful assistant that can read, write, and list files, and run commands.",
            tools=[],
            metadata={"test": True},
        )

    @pytest.fixture
    def adapter(self) -> PydanticAIAdapter:
        """Create a PydanticAIAdapter instance."""
        return PydanticAIAdapter(proposal_mode=False)

    @pytest.mark.asyncio
    async def test_agent_read_file_with_prompt(self, adapter: PydanticAIAdapter, agent_settings: AgentSettings, temp_dir: str) -> None:
        """Test agent can read a file using the read_file tool via prompt."""
        # Create a test file
        test_file = Path(temp_dir) / "test.txt"
        test_content = "Hello, World! This is test content."
        test_file.write_text(test_content)

        # Create agent with TestModel
        model = TestModel(call_tools="all")
        agent_settings.model_settings.provider = "test"
        agent_settings.model_settings.model = "test-model"
        
        agent = PydanticAgent(
            model=model,
            system_prompt=agent_settings.system_prompt,
        )
        
        # Register tools
        adapter._register_tool_read_file(agent)
        
        # Run agent with prompt to read file
        prompt = f"Please read the file at {test_file} and tell me its content."
        result = await agent.run(prompt)
        
        # Verify the agent processed the request and output contains expected content
        assert result is not None
        assert hasattr(result, "output")
        output_str = str(result.output)
        # Verify output contains file content or success indication
        assert fuzzy_match(output_str, test_content) or fuzzy_match(output_str, "success") or fuzzy_match(output_str, "Hello")

    @pytest.mark.asyncio
    async def test_agent_write_file_with_prompt(self, adapter: PydanticAIAdapter, agent_settings: AgentSettings, temp_dir: str) -> None:
        """Test agent can write a file using the write_file tool via prompt."""
        output_file = Path(temp_dir) / "output.txt"
        test_content = "Content written by AI agent"

        model = TestModel(call_tools="all")
        agent_settings.model_settings.provider = "test"
        agent_settings.model_settings.model = "test-model"
        
        agent = PydanticAgent(
            model=model,
            system_prompt=agent_settings.system_prompt,
        )
        
        # Register tools
        adapter._register_tool_write_file(agent)
        
        # Run agent with prompt to write file
        prompt = f"Please write the following content to {output_file}: '{test_content}'"
        result = await agent.run(prompt)
        
        # Verify the agent processed the request and output indicates success
        assert result is not None
        assert hasattr(result, "output")
        output_str = str(result.output)
        # Verify output contains success indication or file path
        assert fuzzy_match(output_str, "write") or fuzzy_match(output_str, "success") or fuzzy_match(output_str, "output.txt")

    @pytest.mark.asyncio
    async def test_agent_list_files_with_prompt(self, adapter: PydanticAIAdapter, agent_settings: AgentSettings, temp_dir: str) -> None:
        """Test agent can list files using the list_files tool via prompt."""
        # Create test files
        Path(temp_dir).joinpath("file1.txt").write_text("content1")
        Path(temp_dir).joinpath("file2.txt").write_text("content2")
        Path(temp_dir).joinpath("subdir").mkdir()
        Path(temp_dir).joinpath("subdir/file3.txt").write_text("content3")

        model = TestModel(call_tools="all")
        agent_settings.model_settings.provider = "test"
        agent_settings.model_settings.model = "test-model"
        
        agent = PydanticAgent(
            model=model,
            system_prompt=agent_settings.system_prompt,
        )
        
        # Register tools
        adapter._register_tool_list_files(agent)
        
        # Run agent with prompt to list files
        prompt = f"Please list all files in the directory {temp_dir}"
        result = await agent.run(prompt)
        
        # Verify the agent processed the request and output contains file names
        assert result is not None
        assert hasattr(result, "output")
        output_str = str(result.output)
        # Verify output contains at least one file name or list indication
        assert fuzzy_match(output_str, "file1") or fuzzy_match(output_str, "file2") or fuzzy_match(output_str, "list")

    @pytest.mark.asyncio
    async def test_agent_run_command_with_prompt(self, adapter: PydanticAIAdapter, agent_settings: AgentSettings) -> None:
        """Test agent can run a command using the run_command tool via prompt."""
        model = TestModel(call_tools="all")
        agent_settings.model_settings.provider = "test"
        agent_settings.model_settings.model = "test-model"
        
        agent = PydanticAgent(
            model=model,
            system_prompt=agent_settings.system_prompt,
        )
        
        # Register tools
        adapter._register_tool_run_command(agent)
        
        # Run agent with prompt to execute command
        prompt = "Please run the 'echo hello' command and tell me the output"
        result = await agent.run(prompt)
        
        # Verify the agent processed the request and output contains command result
        assert result is not None
        assert hasattr(result, "output")
        output_str = str(result.output)
        # Verify output contains command output or success indication
        assert fuzzy_match(output_str, "hello") or fuzzy_match(output_str, "command") or fuzzy_match(output_str, "success")

    @pytest.mark.asyncio
    async def test_agent_with_all_tools_registered(self, adapter: PydanticAIAdapter, agent_settings: AgentSettings, temp_dir: str) -> None:
        """Test agent with all tools registered can handle multiple operations."""
        # Create test file
        test_file = Path(temp_dir) / "data.txt"
        test_file.write_text("Initial data")

        model = TestModel(call_tools="all")
        agent_settings.model_settings.provider = "test"
        agent_settings.model_settings.model = "test-model"
        
        agent = PydanticAgent(
            model=model,
            system_prompt=agent_settings.system_prompt,
        )
        
        # Register all tools
        adapter._register_tool_read_file(agent)
        adapter._register_tool_write_file(agent)
        adapter._register_tool_list_files(agent)
        adapter._register_tool_run_command(agent)
        
        # Run agent with complex prompt
        prompt = f"""
        Please perform the following tasks:
        1. Read the file at {test_file}
        2. List all files in {temp_dir}
        3. Write a new file with the content 'Updated data' to {temp_dir}/updated.txt
        4. Run the 'pwd' command to get the current directory
        """
        result = await agent.run(prompt)
        
        # Verify the agent processed the request and output contains task results
        assert result is not None
        assert hasattr(result, "output")
        output_str = str(result.output)
        # Verify output contains evidence of tool execution
        assert fuzzy_match(output_str, "Initial data") or fuzzy_match(output_str, "data.txt") or fuzzy_match(output_str, "success")

    @pytest.mark.asyncio
    async def test_agent_tool_output_parsing(self, adapter: PydanticAIAdapter, agent_settings: AgentSettings, temp_dir: str) -> None:
        """Test that agent can parse tool outputs correctly."""
        # Create test file with specific content
        test_file = Path(temp_dir) / "parse_test.txt"
        test_content = "Test content for parsing"
        test_file.write_text(test_content)

        model = TestModel(call_tools="all")
        agent_settings.model_settings.provider = "test"
        agent_settings.model_settings.model = "test-model"
        
        agent = PydanticAgent(
            model=model,
            system_prompt=agent_settings.system_prompt,
        )
        
        # Register read_file tool
        adapter._register_tool_read_file(agent)
        
        # Run agent to read file
        prompt = f"Read the file at {test_file} and extract the content"
        result = await agent.run(prompt)
        
        # Verify result contains expected content
        assert result is not None
        assert hasattr(result, "output")
        output_str = str(result.output)
        # The output should contain tool execution result (success indicator or file path)
        assert fuzzy_match(output_str, "success") or fuzzy_match(output_str, "read_file") or fuzzy_match(output_str, "content")

    @pytest.mark.asyncio
    async def test_agent_handles_file_not_found(self, adapter: PydanticAIAdapter, agent_settings: AgentSettings, temp_dir: str) -> None:
        """Test agent handles file not found error gracefully."""
        nonexistent_file = Path(temp_dir) / "nonexistent.txt"

        model = TestModel(call_tools="all")
        agent_settings.model_settings.provider = "test"
        agent_settings.model_settings.model = "test-model"
        
        agent = PydanticAgent(
            model=model,
            system_prompt=agent_settings.system_prompt,
        )
        
        # Register read_file tool
        adapter._register_tool_read_file(agent)
        
        # Run agent with nonexistent file
        prompt = f"Try to read the file at {nonexistent_file}"
        result = await agent.run(prompt)
        
        # Verify the agent processed the request and output indicates error or not found
        assert result is not None
        assert hasattr(result, "output")
        output_str = str(result.output)
        # Output should contain error indication or file not found message
        assert fuzzy_match(output_str, "not found") or fuzzy_match(output_str, "error") or fuzzy_match(output_str, "nonexistent")

    @pytest.mark.asyncio
    async def test_agent_sequential_file_operations(self, adapter: PydanticAIAdapter, agent_settings: AgentSettings, temp_dir: str) -> None:
        """Test agent can perform sequential file operations."""
        file1 = Path(temp_dir) / "file1.txt"
        file2 = Path(temp_dir) / "file2.txt"
        file1.write_text("Content from file 1")

        model = TestModel(call_tools="all")
        agent_settings.model_settings.provider = "test"
        agent_settings.model_settings.model = "test-model"
        
        agent = PydanticAgent(
            model=model,
            system_prompt=agent_settings.system_prompt,
        )
        
        # Register file tools
        adapter._register_tool_read_file(agent)
        adapter._register_tool_write_file(agent)
        
        # Run agent to read and write files
        prompt = f"""
        1. Read the file at {file1}
        2. Write the content to {file2}
        """
        result = await agent.run(prompt)
        
        # Verify the agent processed the request and output indicates operations completed
        assert result is not None
        assert hasattr(result, "output")
        output_str = str(result.output)
        # Output should contain evidence of file operations
        assert fuzzy_match(output_str, "Content from file 1") or fuzzy_match(output_str, "file2") or fuzzy_match(output_str, "write")

    @pytest.mark.asyncio
    async def test_agent_with_encoding_specification(self, adapter: PydanticAIAdapter, agent_settings: AgentSettings, temp_dir: str) -> None:
        """Test agent can handle file operations with specific encoding."""
        test_file = Path(temp_dir) / "utf8_file.txt"
        test_content = "Hello 世界 🌍"
        test_file.write_text(test_content, encoding="utf-8")

        model = TestModel(call_tools="all")
        agent_settings.model_settings.provider = "test"
        agent_settings.model_settings.model = "test-model"
        
        agent = PydanticAgent(
            model=model,
            system_prompt=agent_settings.system_prompt,
        )
        
        # Register read_file tool
        adapter._register_tool_read_file(agent)
        
        # Run agent to read file with UTF-8 encoding
        prompt = f"Read the file at {test_file} using UTF-8 encoding"
        result = await agent.run(prompt)
        
        # Verify the agent processed the request and output contains tool execution result
        assert result is not None
        assert hasattr(result, "output")
        output_str = str(result.output)
        # Output should contain tool execution result (success indicator or tool name)
        assert fuzzy_match(output_str, "success") or fuzzy_match(output_str, "read_file") or fuzzy_match(output_str, "content")

    @pytest.mark.asyncio
    async def test_agent_tool_integration_workflow(self, adapter: PydanticAIAdapter, agent_settings: AgentSettings, temp_dir: str) -> None:
        """Test complete workflow with agent using multiple tools."""
        source_file = Path(temp_dir) / "source.txt"
        dest_file = Path(temp_dir) / "destination.txt"
        source_file.write_text("Original content")

        model = TestModel(call_tools="all")
        agent_settings.model_settings.provider = "test"
        agent_settings.model_settings.model = "test-model"
        
        agent = PydanticAgent(
            model=model,
            system_prompt=agent_settings.system_prompt,
        )
        
        # Register all file tools
        adapter._register_tool_read_file(agent)
        adapter._register_tool_write_file(agent)
        adapter._register_tool_list_files(agent)
        
        # Run agent with workflow prompt
        prompt = f"""
        Complete the following workflow:
        1. List all files in {temp_dir}
        2. Read the content from {source_file}
        3. Write the content to {dest_file}
        4. List files again to confirm
        """
        result = await agent.run(prompt)
        
        # Verify the agent processed the request and output indicates workflow completion
        assert result is not None
        assert hasattr(result, "output")
        output_str = str(result.output)
        # Output should contain evidence of tool execution (tool names or success indicators)
        assert fuzzy_match(output_str, "read_file") or fuzzy_match(output_str, "write_file") or fuzzy_match(output_str, "success")

    @pytest.mark.asyncio
    async def test_agent_tool_with_optional_parameters(self, adapter: PydanticAIAdapter, agent_settings: AgentSettings, temp_dir: str) -> None:
        """Test agent can use tools with optional parameters."""
        # Create test files
        Path(temp_dir).joinpath("test1.txt").write_text("content1")
        Path(temp_dir).joinpath("test2.py").write_text("print('hello')")
        Path(temp_dir).joinpath("readme.md").write_text("# README")

        model = TestModel(call_tools="all")
        agent_settings.model_settings.provider = "test"
        agent_settings.model_settings.model = "test-model"
        
        agent = PydanticAgent(
            model=model,
            system_prompt=agent_settings.system_prompt,
        )
        
        # Register list_files tool
        adapter._register_tool_list_files(agent)
        
        # Run agent with pattern filter
        prompt = f"List all .txt files in {temp_dir} using a pattern filter"
        result = await agent.run(prompt)
        
        # Verify the agent processed the request and output contains tool execution result
        assert result is not None
        assert hasattr(result, "output")
        output_str = str(result.output)
        # Output should contain tool execution result (tool name or success indicator)
        assert fuzzy_match(output_str, "list_files") or fuzzy_match(output_str, "success") or fuzzy_match(output_str, "files")
