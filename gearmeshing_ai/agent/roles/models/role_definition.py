"""Role definition models.

This module provides Pydantic models for defining AI agent roles with their
configuration, capabilities, and metadata.

## Design Overview

Role definitions are the core data structures that describe how an AI agent
should behave, what tools it can use, and how it should be configured.

### RoleMetadata

Metadata about a role including domain, version, decision authority, and
LLM configuration parameters.

**Fields:**
- domain: The domain/area of responsibility (e.g., 'software_development')
- version: Version of the role definition (default: '1.0')
- decision_authority: What decisions this role can make
- requires_approval: Whether this role's actions require approval
- max_tokens: Maximum tokens for LLM responses (default: 2048)
- temperature: Temperature for LLM sampling (default: 0.7)
- timeout_seconds: Timeout for agent execution (default: 300)
- cost_priority: Cost priority level - 'low', 'medium', 'high'
- additional_metadata: Any additional custom metadata

### RoleDefinition

Complete definition of an AI agent role including identity, model configuration,
system prompt, tools, and metadata.

**Fields:**
- role: Unique role identifier (e.g., 'dev_lead')
- description: Human-readable description of the role
- model_provider: AI model provider (e.g., 'openai')
- model_name: Specific model identifier (e.g., 'gpt-4')
- customized_model_name: Customized name for this model configuration
- system_prompt: System prompt for the agent (500-1000 words recommended)
- tools: List of tool names available to this role
- metadata: RoleMetadata instance

**Key Methods:**
- to_agent_settings(): Convert to AgentSettings for factory registration
- from_dict(): Create from dictionary (e.g., from YAML configuration)

## Usage Examples

### Creating a Role Programmatically

```python
from gearmeshing_ai.agent.roles.models.role_definition import RoleDefinition, RoleMetadata

metadata = RoleMetadata(
    domain="software_development",
    decision_authority="implementation",
    temperature=0.4,
    max_tokens=3072,
    cost_priority="medium",
)

role = RoleDefinition(
    role="dev",
    description="Senior Software Developer",
    model_provider="openai",
    model_name="gpt-4",
    customized_model_name="dev-gpt4",
    system_prompt=\"\"\"You are a Senior Software Developer...
    
    Your expertise includes:
    - Full-stack web development
    - Software design patterns
    - Testing and debugging
    
    Your responsibilities:
    1. Implement features according to specifications
    2. Write clean, maintainable code
    3. Write comprehensive unit tests
    ...\"\"\",
    tools=["read_file", "write_file", "run_command"],
    metadata=metadata,
)
```

### Loading from YAML Dictionary

```python
role_dict = {
    "role": "dev_lead",
    "description": "Senior Software Architect",
    "model_settings": {
        "customized_name": "dev-lead-gpt4-turbo",
        "provider": "openai",
        "model": "gpt-4-turbo",
    },
    "system_prompt": "You are a senior architect...",
    "tools": ["read_file", "write_file", "run_command"],
    "metadata": {
        "domain": "technical_leadership",
        "decision_authority": "architecture",
        "temperature": 0.3,
        "max_tokens": 4096,
    },
}

role = RoleDefinition.from_dict(role_dict)
```

### Converting to AgentSettings

```python
# Convert role to AgentSettings for factory registration
agent_settings = role.to_agent_settings()

# Now register with factory
factory.register_agent_settings(agent_settings)
```

## Design Principles

1. **Type Safety**: Pydantic models provide validation and IDE support
2. **Flexibility**: Support both programmatic and YAML-based configuration
3. **Conversion**: Easy conversion to AgentSettings for factory integration
4. **Metadata**: Rich metadata for role characterization and filtering
5. **Documentation**: Detailed system prompts for clear agent behavior
"""

from typing import Any

from pydantic import BaseModel, Field


class RoleMetadata(BaseModel):
    """Metadata for a role configuration.

    Attributes:
        domain: The domain/area of responsibility (e.g., 'software_development')
        version: Version of the role definition
        decision_authority: What decisions this role can make
        requires_approval: Whether this role's actions require approval
        max_tokens: Maximum tokens for LLM responses
        temperature: Temperature setting for LLM
        timeout_seconds: Timeout for agent execution
        cost_priority: Cost priority level (low, medium, high)
        additional_metadata: Any additional metadata
    """

    domain: str = Field(..., description="Domain/area of responsibility")
    version: str = Field(default="1.0", description="Version of the role definition")
    decision_authority: str = Field(..., description="What decisions this role can make")
    requires_approval: bool = Field(default=False, description="Whether actions require approval")
    max_tokens: int = Field(default=2048, description="Maximum tokens for LLM responses")
    temperature: float = Field(default=0.7, description="Temperature for LLM sampling")
    timeout_seconds: int = Field(default=300, description="Timeout for agent execution")
    cost_priority: str = Field(default="medium", description="Cost priority level")
    additional_metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RoleDefinition(BaseModel):
    """Complete definition of an AI agent role.

    Attributes:
        role: Unique role identifier
        description: Human-readable description of the role
        model_provider: AI model provider (e.g., 'openai')
        model_name: Specific model identifier (e.g., 'gpt-4')
        customized_model_name: Customized name for this model configuration
        system_prompt: System prompt for the agent
        tools: List of tool names available to this role
        metadata: Role metadata and configuration
    """

    role: str = Field(..., description="Unique role identifier")
    description: str = Field(..., description="Human-readable description")
    model_provider: str = Field(..., description="AI model provider")
    model_name: str = Field(..., description="Specific model identifier")
    customized_model_name: str = Field(..., description="Customized model configuration name")
    system_prompt: str = Field(..., description="System prompt for the agent")
    tools: list[str] = Field(default_factory=list, description="Available tools")
    metadata: RoleMetadata = Field(..., description="Role metadata")

    def to_agent_settings(self) -> "AgentSettings":
        """Convert to AgentSettings for factory registration.

        Returns:
            AgentSettings instance compatible with AgentFactory
        """
        from gearmeshing_ai.agent.abstraction.settings import AgentSettings, ModelSettings

        model_settings = ModelSettings(
            customized_name=self.customized_model_name,
            provider=self.model_provider,
            model=self.model_name,
            temperature=self.metadata.temperature,
            max_tokens=self.metadata.max_tokens,
        )

        return AgentSettings(
            role=self.role,
            description=self.description,
            model_settings=model_settings,
            tools=self.tools,
            system_prompt=self.system_prompt,
            metadata=self.metadata.model_dump(),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoleDefinition":
        """Create RoleDefinition from dictionary (e.g., from YAML).

        Args:
            data: Dictionary with role configuration

        Returns:
            RoleDefinition instance
        """
        # Extract metadata with required fields
        metadata_dict = data.get("metadata", {})
        
        # Ensure required metadata fields are present
        if "domain" not in metadata_dict:
            raise ValueError("Metadata must contain 'domain' field")
        if "decision_authority" not in metadata_dict:
            raise ValueError("Metadata must contain 'decision_authority' field")
        
        metadata = RoleMetadata(**metadata_dict)

        # Extract model settings
        model_settings = data.get("model_settings", {})

        return cls(
            role=data.get("role") or data.get("role_name"),
            description=data["description"],
            model_provider=model_settings.get("provider", "openai"),
            model_name=model_settings.get("model", "gpt-4"),
            customized_model_name=model_settings.get("customized_name", data.get("role") or data.get("role_name")),
            system_prompt=data["system_prompt"],
            tools=data.get("tools", []),
            metadata=metadata,
        )
