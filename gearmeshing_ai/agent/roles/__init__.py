"""AI Agent Roles package.

Comprehensive role-based agent configuration, selection, and management system.

## Infrastructure Design

The roles package provides a layered architecture for managing AI agent roles:

```
┌─────────────────────────────────────────────────────────────┐
│                     RoleService (High-Level API)            │
│  - Load and register roles with AgentFactory                │
│  - Unified interface for all role operations                │
│  - Integration point for REST API and CLI                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  RoleLoader    │  RoleSelector   │  RoleRegistry            │
│  - Load from   │  - Validate     │  - Store and retrieve    │
│    YAML/dict   │  - Suggest      │  - Filter by domain/     │
│  - Parse       │  - Get info     │    authority             │
│    config      │                 │  - Singleton pattern     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  RoleDefinition & RoleMetadata (Data Models)                │
│  - Pydantic models with validation                          │
│  - Conversion to AgentSettings                              │
│  - Metadata configuration                                   │
└─────────────────────────────────────────────────────────────┘
```

## Feature Design

### 1. Role Definition
Each role is defined with:
- **Identity**: Unique role name and description
- **Model Configuration**: Provider, model name, temperature, max tokens
- **System Prompt**: Detailed instructions for the AI agent
- **Tools**: List of available tools/capabilities
- **Metadata**: Domain, decision authority, approval requirements, etc.

### 2. Role Registry
Centralized storage for role definitions:
- Register and retrieve roles by name
- Filter by domain or decision authority
- Singleton pattern for global access
- Thread-safe operations

### 3. Role Selector
Intelligent role selection and validation:
- Validate role existence
- Suggest roles based on task description keywords
- Get detailed role information
- Filter roles by domain or authority

### 4. Role Loader
Load role configurations from external sources:
- Load from YAML files
- Load from dictionaries
- Automatic registration with registry
- Error handling for invalid configurations

### 5. Role Service
High-level API for role management:
- Load and register roles with AgentFactory
- Unified interface for all operations
- Integration with selector, registry, and loader
- Optional AgentFactory integration

## Default Roles

Six default software development roles are provided:

1. **marketing** (gpt-4, temp=0.8)
   - Domain: product_marketing
   - Authority: positioning_and_messaging
   - Tools: read_file, query_database, generate_report, create_visualization

2. **planner** (gpt-4, temp=0.5)
   - Domain: project_management
   - Authority: planning_and_estimation
   - Tools: read_file, query_database, generate_report, create_visualization

3. **dev_lead** (gpt-4-turbo, temp=0.3)
   - Domain: technical_leadership
   - Authority: architecture_and_code_approval
   - Tools: read_file, write_file, run_command, query_database, generate_report

4. **dev** (gpt-4, temp=0.4)
   - Domain: software_development
   - Authority: implementation
   - Tools: read_file, write_file, run_command, list_files, query_database

5. **qa** (gpt-4, temp=0.4)
   - Domain: quality_assurance
   - Authority: quality_assessment
   - Tools: read_file, write_file, run_command, query_database, generate_report

6. **sre** (gpt-4-turbo, temp=0.3)
   - Domain: site_reliability_engineering
   - Authority: infrastructure_and_deployment
   - Tools: read_file, write_file, run_command, query_database, generate_report

## Usage Guidelines

### Quick Start

```python
from gearmeshing_ai.agent.roles.service import get_global_role_service

# Get service and load default roles
service = get_global_role_service(agent_factory)
service.load_and_register_roles(
    "gearmeshing_ai/agent/roles/config/default_roles_config.yaml"
)

# List available roles
roles = service.list_available_roles()

# Suggest role for task
role = service.suggest_role("Design the system architecture")
```

### Integration with Workflows

```python
from gearmeshing_ai.agent.runtime.nodes.agent_decision import agent_decision_node

# Use agent_decision_node with role support
result = await agent_decision_node(
    state=workflow_state,
    agent_factory=factory,
    auto_select_role=True  # Auto-select based on task
)
```

### Custom Roles

```python
from gearmeshing_ai.agent.roles.models.role_definition import RoleDefinition, RoleMetadata

metadata = RoleMetadata(
    domain="custom_domain",
    decision_authority="custom_authority",
    temperature=0.5,
)

role = RoleDefinition(
    role="custom_role",
    description="Custom Role Description",
    model_provider="openai",
    model_name="gpt-4",
    customized_model_name="custom-gpt4",
    system_prompt="Your system prompt here...",
    tools=["tool1", "tool2"],
    metadata=metadata,
)

service.register_role(role)
```

## Key Design Principles

1. **Separation of Concerns**: Each component has a single responsibility
2. **Singleton Pattern**: Global instances for easy access
3. **Type Safety**: Pydantic models with validation
4. **Extensibility**: Easy to add custom roles and extend functionality
5. **Integration**: Seamless integration with AgentFactory and workflows
6. **Error Handling**: Comprehensive error messages and logging
7. **Backward Compatibility**: Works with existing agent code

## Components

- `models.role_definition`: RoleDefinition and RoleMetadata data models
- `registry`: RoleRegistry for storing and retrieving roles
- `selector`: RoleSelector for role validation and suggestion
- `loader`: RoleLoader for loading roles from YAML/dict
- `service`: RoleService high-level API
- `config/default_roles_config.yaml`: Default role definitions
"""

from .models.role_definition import RoleDefinition, RoleMetadata
from .registry import RoleRegistry
from .selector import RoleSelector
from .service import RoleService

__all__ = [
    "RoleDefinition",
    "RoleMetadata",
    "RoleRegistry",
    "RoleSelector",
    "RoleService",
]
