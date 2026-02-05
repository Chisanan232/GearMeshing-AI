# Abstraction Smoke Tests

This directory contains comprehensive smoke tests for the `gearmeshing_ai.agent_core.abstraction` module that verify the entire design and implementation by making real AI model calls through the adapter pattern.

## Overview

The smoke tests verify:

- **AgentAdapter**: Abstract interface implementation with PydanticAI adapter
- **AgentFactory**: Real agent creation, caching, and lifecycle management
- **AgentSettings & ModelSettings**: Configuration validation and real API key usage
- **EnvManager**: API key validation and environment variable export
- **AgentCache**: Singleton behavior and thread safety
- **MCPClientAbstraction**: Integration with factory and tool management
- **End-to-end workflows**: Complete abstraction system integration

## Test Structure

### Main Test Files

- `test_abstraction_smoke.py` - Comprehensive smoke tests with real AI model calls
- `conftest.py` - Test configuration, fixtures, and custom markers

### Settings and Configuration

- `../../settings.py` - Test settings model with Pydantic validation
- `../../.env.example` - Environment variables template for testing

## Running the Tests

### Prerequisites

1. **Install dependencies**:
   ```bash
   uv install
   ```

2. **Configure API keys** (optional but recommended for full testing):
   ```bash
   cp test/.env.example test/.env
   # Edit test/.env with your actual API keys
   ```

3. **Available AI Providers**:
   - OpenAI (requires `OPENAI_API_KEY`)
   - Anthropic (requires `ANTHROPIC_API_KEY`)
   - Google Gemini (requires `GEMINI_API_KEY`)

### Test Execution

#### Run All Smoke Tests
```bash
# Run all abstraction smoke tests
uv run python -m pytest test/ai_smoke_test/agent_core/abstraction/ -v

# Run with coverage
uv run python -m pytest test/ai_smoke_test/agent_core/abstraction/ --cov=gearmeshing_ai.agent_core.abstraction -v
```

#### Run Specific Test Categories
```bash
# Test only adapter functionality
uv run python -m pytest test/ai_smoke_test/agent_core/abstraction/test_abstraction_smoke.py::TestAgentAdapter -v

# Test only factory functionality
uv run python -m pytest test/ai_smoke_test/agent_core/abstraction/test_abstraction_smoke.py::TestAgentFactory -v

# Test only settings models
uv run python -m pytest test/ai_smoke_test/agent_core/abstraction/test_abstraction_smoke.py::TestAgentSettings -v
```

#### Run with Custom Markers
```bash
# Run only tests that call real AI models
uv run python -m pytest test/ai_smoke_test/agent_core/abstraction/ -m ai_test -v

# Run only OpenAI-specific tests
uv run python -m pytest test/ai_smoke_test/agent_core/abstraction/ -m openai -v

# Run only Anthropic-specific tests
uv run python -m pytest test/ai_smoke_test/agent_core/abstraction/ -m anthropic -v

# Run only Google-specific tests
uv run python -m pytest test/ai_smoke_test/agent_core/abstraction/ -m google -v
```

#### Test Settings Model
```bash
# Test the settings model independently
uv run python -m pytest test/test_settings.py -v
```

## Test Configuration

### Environment Variables

The tests use the following environment variables (configured in `test/.env`):

```bash
# AI Provider API Keys
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Test Execution Control
RUN_AI_TESTS=true          # Enable/disable AI model calls
RUN_SLOW_TESTS=false       # Enable/disable slow integration tests
TEST_TIMEOUT=60            # Timeout per test in seconds
```

### Test Settings Model

The `test/settings.py` module provides:

- **TestSettings**: Main settings container with environment variable loading
- **TestModelSettings**: AI model configuration for testing
- **TestAgentSettings**: Agent configuration for testing
- **Automatic configuration**: Default test setups for available providers

### Custom Pytest Markers

- `@pytest.mark.ai_test`: Tests that call real AI models
- `@pytest.mark.slow_test`: Tests that take longer to run
- `@pytest.mark.openai`: Tests requiring OpenAI API key
- `@pytest.mark.anthropic`: Tests requiring Anthropic API key
- `@pytest.mark.google`: Tests requiring Google API key

## Test Categories

### 1. AgentAdapter Tests
- Verify abstract interface cannot be instantiated directly
- Test concrete PydanticAI adapter implementation
- Test agent creation, running, and streaming with real AI models

### 2. AgentFactory Tests
- Test factory initialization and component setup
- Test settings registration and retrieval
- Test agent creation with and without caching
- Test settings overrides and error handling
- Test MCP client integration

### 3. Settings Tests
- Test ModelSettings and AgentSettings validation
- Test configuration with real API keys
- Test Pydantic SecretStr behavior for sensitive data
- Test default configuration creation

### 4. EnvManager Tests
- Test API key validation for different providers
- Test environment variable export functionality
- Test settings retrieval and management

### 5. AgentCache Tests
- Test singleton pattern implementation
- Test basic cache operations (get, set, remove, clear)
- Test thread safety with concurrent operations

### 6. MCPClientAbstraction Tests
- Test abstract interface implementation
- Test mock MCP client functionality
- Test integration with AgentFactory

### 7. Integration Tests
- Test complete workflow: settings → factory → adapter → AI model
- Test multiple providers in single workflow
- Test end-to-end system integration

## Expected Test Results

### Without API Keys
- **Basic functionality tests**: Pass (verify interfaces, caching, etc.)
- **AI model tests**: Skipped (no API keys available)
- **Integration tests**: Skipped (require real AI calls)

### With API Keys
- **All tests**: Pass (complete verification of abstraction system)
- **Real AI calls**: Successful (verify actual model integration)
- **Performance**: Fast (caching and efficient design)

### Typical Test Output
```
============================= test session starts ==============================
collected 25 items

test_abstraction_smoke.py::TestAgentAdapter::test_adapter_is_abstract PASSED
test_abstraction_smoke.py::TestAgentAdapter::test_concrete_adapter_implementation PASSED
test_abstraction_smoke.py::TestAgentAdapter::test_adapter_create_agent PASSED
test_abstraction_smoke.py::TestAgentAdapter::test_adapter_run_agent PASSED
test_abstraction_smoke.py::TestAgentFactory::test_factory_initialization PASSED
...
test_abstraction_smoke.py::TestIntegrationSmoke::test_full_abstraction_workflow PASSED

================= 20 passed, 5 skipped in 45.23s ==================
```

## Troubleshooting

### Common Issues

1. **Tests skipped due to missing API keys**:
   - Solution: Configure API keys in `test/.env`
   - Or set `RUN_AI_TESTS=false` to test without AI calls

2. **Import errors**:
   - Solution: Ensure all dependencies are installed with `uv install`
   - Check that you're running from the project root directory

3. **Timeout errors**:
   - Solution: Increase `TEST_TIMEOUT` in environment
   - Check network connectivity for AI API calls

4. **Pydantic validation errors**:
   - Solution: Check environment variable names and formats
   - Ensure `.env` file is in the correct location

### Debug Mode

Run tests with extra verbosity and debugging:

```bash
uv run python -m pytest test/ai_smoke_test/agent_core/abstraction/ -vvs --tb=long
```

### Coverage Report

Generate detailed coverage report:

```bash
uv run python -m pytest test/ai_smoke_test/agent_core/abstraction/ --cov=gearmeshing_ai.agent_core.abstraction --cov-report=html
```

## Best Practices

### For Developers

1. **Always test with real API keys** when making changes to adapters
2. **Use the test settings model** instead of hardcoded configurations
3. **Mock external dependencies** in unit tests, use real services in smoke tests
4. **Respect the test markers** to ensure appropriate test categorization

### For CI/CD

1. **Configure API keys** as environment variables in CI
2. **Use conditional test execution** based on available keys
3. **Set appropriate timeouts** for AI model calls
4. **Generate coverage reports** for code quality monitoring

## Architecture Verification

These smoke tests verify that the abstraction layer:

1. **Provides clean interfaces** for AI agent frameworks
2. **Supports multiple providers** through adapter pattern
3. **Manages configuration** securely with SecretStr
4. **Implements caching** for performance optimization
5. **Handles errors** gracefully with proper validation
6. **Integrates seamlessly** with MCP and tool management
7. **Maintains thread safety** in concurrent environments
8. **Supports real workflows** with actual AI model calls

The tests ensure the abstraction design is production-ready and can handle real-world AI agent workloads.
