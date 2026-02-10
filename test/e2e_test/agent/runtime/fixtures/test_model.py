"""TestModel fixture for E2E tests - simulates AI agent decision making."""

import os

from gearmeshing_ai.agent.models.actions import ActionProposal


class MockTestModel:
    """Mock agent with predefined responses for testing."""

    def __init__(self):
        """Initialize mock test model."""
        self.response_map = {
            "read": ActionProposal(
                action="file_read",
                reason="User requested to read file",
                parameters={"path": "/src/main.py"},
            ),
            "analyze": ActionProposal(
                action="file_read",
                reason="User requested code analysis",
                parameters={"path": "/src/utils.py"},
            ),
            "deploy": ActionProposal(
                action="deploy",
                reason="User requested deployment",
                parameters={"environment": "production"},
            ),
            "backup": ActionProposal(
                action="backup_database",
                reason="User requested database backup",
                parameters={"database": "production"},
            ),
            "delete": ActionProposal(
                action="delete_file",
                reason="User requested file deletion",
                parameters={"path": "/backups/db_backup.sql"},
            ),
            "test": ActionProposal(
                action="run_tests",
                reason="User requested test execution",
                parameters={},
            ),
            "staging": ActionProposal(
                action="deploy_staging",
                reason="User requested staging deployment",
                parameters={"environment": "staging"},
            ),
            "production": ActionProposal(
                action="deploy_production",
                reason="User requested production deployment",
                parameters={"environment": "production"},
            ),
        }

    async def process_prompt(self, prompt: str) -> ActionProposal:
        """Process prompt and return action proposal."""
        prompt_lower = prompt.lower()

        for key, response in self.response_map.items():
            if key in prompt_lower:
                return response

        # Default response
        return ActionProposal(
            action="file_read",
            reason="Default action",
            parameters={"path": "/src/main.py"},
        )


class HybridTestModel:
    """Hybrid model that uses real or mock agent."""

    def __init__(self, use_real: bool = False):
        """Initialize hybrid test model."""
        self.use_real = use_real and os.getenv("OPENAI_API_KEY")
        self.mock_agent = MockTestModel()

        if self.use_real:
            try:
                from pydantic_ai import Agent

                self.agent = Agent(
                    model="openai:gpt-4",
                    system_prompt="""You are an AI assistant helping with software development tasks.
                    When given a task, respond with a JSON object containing:
                    {
                        "action": "read_file|write_file|run_command|deploy|run_tests|delete_file",
                        "reason": "explanation of why this action",
                        "parameters": {
                            "path": "file path",
                            "command": "command to run",
                            "environment": "deployment environment"
                        }
                    }
                    """,
                )
            except ImportError:
                self.use_real = False

    async def process_prompt(self, prompt: str) -> ActionProposal:
        """Process prompt and return action proposal."""
        if self.use_real:
            try:
                response = await self.agent.run(prompt)
                return ActionProposal.model_validate(response.data)
            except Exception:
                # Fall back to mock on error
                return await self.mock_agent.process_prompt(prompt)
        else:
            return await self.mock_agent.process_prompt(prompt)
