from typing import Any, Optional

# pydantic_ai imports
from pydantic_ai import Agent as PydanticAgent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.models.openai import OpenAIModel

from ..abstraction.adapter import AgentAdapter
from ..abstraction.settings import AgentSettings
from ..abstraction.tools import (
    read_file_handler, write_file_handler, list_files_handler, run_command_handler,
    FileReadInput, FileWriteInput, FileListInput, CommandRunInput
)
from ..models.actions import ActionProposal, MCPToolCatalog


class PydanticAIAdapter(AgentAdapter):
    """Adapter implementation for Pydantic AI framework with tool registration support."""

    def __init__(self, proposal_mode: bool = False, tool_catalog: MCPToolCatalog | None = None):
        """Initialize adapter with optional proposal-only mode.

        Args:
            proposal_mode: If True, creates proposal-only agents
            tool_catalog: Tool catalog for proposal-only agents

        """
        self.proposal_mode = proposal_mode
        self.tool_catalog = tool_catalog

    def _get_model(self, provider: str, model_name: str) -> Any:
        """Create a Pydantic AI model."""
        provider = provider.lower()
        if provider == "openai":
            return OpenAIModel(model_name)
        if provider == "anthropic":
            return AnthropicModel(model_name)
        if provider in ["google", "gemini"]:
            return GeminiModel(model_name)
        # Fallback or default to string which Pydantic AI might handle or fail
        return f"{provider}:{model_name}"

    def create_agent(self, settings: AgentSettings, tools: list[Any]) -> Any:
        """Create a Pydantic AI Agent instance with tool registration."""
        model_instance = self._get_model(settings.model_settings.provider, settings.model_settings.model)

        if self.proposal_mode:
            # Create proposal-only agent
            system_prompt = self._build_proposal_prompt(settings.system_prompt)
            agent = PydanticAgent(
                model=model_instance,
                system_prompt=system_prompt,
                output_type=ActionProposal,
            )
            # Register only file tools for proposal mode (no command execution)
            self._register_file_tools(agent)
            return agent
        
        # Create traditional agent with tools
        agent = PydanticAgent(
            model=model_instance,
            system_prompt=settings.system_prompt,
        )
        
        # Register all tools (file + command) using the template method
        self._register_tools(agent)
        
        return agent

    # Implement protected tool registration methods
    def _register_tool_read_file(self, agent: PydanticAgent) -> None:
        """Register read_file tool with Pydantic AI agent"""
        @agent.tool
        async def read_file(ctx: RunContext, file_path: str, encoding: str = "utf-8") -> str:
            """Read a file from the filesystem"""
            input_data = FileReadInput(file_path=file_path, encoding=encoding)
            result = await read_file_handler(input_data)
            return result.model_dump_json()

    def _register_tool_write_file(self, agent: PydanticAgent) -> None:
        """Register write_file tool with Pydantic AI agent"""
        @agent.tool
        async def write_file(
            ctx: RunContext,
            file_path: str,
            content: str,
            encoding: str = "utf-8",
            create_dirs: bool = True,
        ) -> str:
            """Write content to a file"""
            input_data = FileWriteInput(
                file_path=file_path,
                content=content,
                encoding=encoding,
                create_dirs=create_dirs
            )
            result = await write_file_handler(input_data)
            return result.model_dump_json()

    def _register_tool_list_files(self, agent: PydanticAgent) -> None:
        """Register list_files tool with Pydantic AI agent"""
        @agent.tool
        async def list_files(
            ctx: RunContext,
            directory_path: str,
            pattern: Optional[str] = None,
            recursive: bool = False,
        ) -> str:
            """List files in a directory"""
            input_data = FileListInput(
                directory_path=directory_path,
                pattern=pattern,
                recursive=recursive
            )
            result = await list_files_handler(input_data)
            return result.model_dump_json()

    def _register_tool_run_command(self, agent: PydanticAgent) -> None:
        """Register run_command tool with Pydantic AI agent"""
        @agent.tool
        async def run_command(
            ctx: RunContext,
            command: str,
            cwd: Optional[str] = None,
            timeout: float = 30.0,
            shell: bool = True,
        ) -> str:
            """Execute a shell command"""
            input_data = CommandRunInput(
                command=command,
                cwd=cwd,
                timeout=timeout,
                shell=shell
            )
            result = await run_command_handler(input_data)
            return result.model_dump_json()

    async def run(self, agent: Any, prompt: str, **kwargs: Any) -> Any:
        """Run the Pydantic AI agent."""
        if not isinstance(agent, PydanticAgent):
            msg = "Agent must be an instance of pydantic_ai.Agent"
            raise ValueError(msg)

        if self.proposal_mode:
            # For proposal-only agents, filter out context parameter
            # The tool catalog is handled during agent creation
            filtered_kwargs = {k: v for k, v in kwargs.items() if k != "context"}
            result = await agent.run(prompt, **filtered_kwargs)

            # Parse the result into ActionProposal
            if hasattr(result, "data") and result.data is not None:
                return self._parse_proposal_result(result.data)
            return self._parse_proposal_result(str(result))
        # Traditional agent execution
        result = await agent.run(prompt)
        return result.output

    async def run_stream(self, agent: Any, prompt: str, **kwargs: Any) -> Any:
        """Run the Pydantic AI agent in streaming mode."""
        if not isinstance(agent, PydanticAgent):
            msg = "Agent must be an instance of pydantic_ai.Agent"
            raise ValueError(msg)

        if self.proposal_mode:
            # Streaming not implemented for proposal-only agents
            raise NotImplementedError("Streaming not implemented for proposal-only agents")

        # Traditional streaming
        async with agent.run_stream(prompt) as result:
            async for message in result.stream_text():
                yield message

    def _build_proposal_prompt(self, original_prompt: str = None) -> str:
        """Build system prompt for proposal-only behavior."""
        base_prompt = """
        You are an AI assistant that proposes actions but does NOT execute them.

        You will be given a list of available tools in your context.
        For each tool you'll see:
        - name: tool identifier
        - description: what the tool does
        - parameters: what parameters it needs
        - returns: what it returns
        - example: usage example

        Your job:
        1. Understand the task
        2. Choose the best tool for the job
        3. Provide the parameters needed
        4. Explain why you chose this tool

        Return ONLY an ActionProposal with:
        - action: the tool name
        - parameters: the parameters for the tool
        - reason: why you chose this action
        - expected_result: what you expect to happen

        Do NOT make up tools. Only use the provided tools.
        """

        if original_prompt:
            return f"{original_prompt}\n\n{base_prompt}"
        return base_prompt

    def _format_tools_for_agent(self) -> list[dict]:
        """Format tools for LLM consumption."""
        if not self.tool_catalog:
            return []

        formatted = []
        for tool in self.tool_catalog.tools:
            formatted.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                    "returns": tool.returns,
                    "example": tool.example_usage,
                }
            )
        return formatted

    def _parse_proposal_result(self, result: Any) -> ActionProposal:
        """Parse result into ActionProposal."""
        import json
        import re

        # Handle AgentRunResult objects
        if hasattr(result, "output") and result.output is not None:
            result_str = str(result.output)
        else:
            result_str = str(result)

        # Try to extract JSON from the result
        # Look for JSON patterns in the response
        json_match = re.search(r'\{.*"action".*\}', result_str, re.DOTALL)
        if json_match:
            try:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                return ActionProposal(**data)
            except (json.JSONDecodeError, TypeError):
                pass

        # Try to extract ActionProposal from string representation
        # Look for ActionProposal(action='...', ...) pattern
        proposal_match = re.search(r'ActionProposal\(action=[\'"]([^\'"]+)[\'"]', result_str)
        if proposal_match:
            action = proposal_match.group(1)

            # Try to extract parameters - handle multiple formats
            parameters = {}

            # Try JSON format first
            params_match = re.search(r"parameters=(\{.*?\})", result_str, re.DOTALL)
            if params_match:
                try:
                    params_str = params_match.group(1)
                    # Clean up the string to make it valid JSON
                    params_str = params_str.replace("'", '"')
                    params_str = re.sub(r"(\w+):", r'"\1":', params_str)
                    parameters = json.loads(params_str)
                except (json.JSONDecodeError, AttributeError):
                    # Try to extract key-value pairs manually
                    kv_pairs = re.findall(r'(\w+)=([\'"][^\'"]*[\'"]|\w+)', params_match.group(1))
                    parameters = {k: v.strip("'\"") for k, v in kv_pairs}

            # Try to extract reason
            reason_match = re.search(r'reason=[\'"]([^\'"]+)[\'"]', result_str)
            reason = reason_match.group(1) if reason_match else result_str[:200] + "..."

            return ActionProposal(action=action, reason=reason, parameters=parameters)

        # Fallback: create a simple proposal from text
        # Try to extract action from text
        action_match = re.search(r'action[:\s]+["\']?(\w+)["\']?', result_str, re.IGNORECASE)
        action = action_match.group(1) if action_match else "unknown"

        # Try to extract parameters
        params_match = re.search(r"parameters[:\s]+(\{.*?\})", result_str, re.DOTALL)
        parameters = {}
        if params_match:
            try:
                parameters = json.loads(params_match.group(1))
            except json.JSONDecodeError:
                parameters = {}

        return ActionProposal(
            action=action,
            reason=result_str[:200] + "..." if len(result_str) > 200 else result_str,
            parameters=parameters,
        )
