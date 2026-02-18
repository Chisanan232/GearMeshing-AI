# Orchestrator Smoke Tests

## Overview

This directory contains comprehensive smoke tests for the GearMeshing-AI orchestrator layer that use real AI models and external services to verify end-to-end functionality.

## Architecture

### Test Infrastructure
- **testcontainers Integration**: Docker Compose service management for Redis, PostgreSQL, and MCP Gateway
- **Status Polling**: Proper async waiting for AI workflow completion
- **LangGraph Verification**: Validates proper execution flow through LangGraph nodes
- **Comprehensive Cleanup**: Each test cleans up its own resources immediately

### Test Categories

#### 1. Basic Workflow Tests (`test_basic_workflows.py`)
- Simple task execution with file generation
- Code analysis workflows
- Timeout handling
- Error handling
- State consistency verification

#### 2. MCP Integration Tests (`test_mcp_integration.py`)
- ClickUp task creation and management
- Multi-tool workflows
- MCP service availability
- Error handling and graceful degradation
- Tool execution verification

#### 3. Approval Workflow Tests (`test_approval_workflows.py`)
- Approval-required workflows
- Rejection with alternative actions
- Workflow cancellation
- State persistence
- Approval with comments

## Test Utilities

### Core Helpers
- **WorkflowTestHelper**: Status polling and workflow management
- **FileTestHelper**: File operations and cleanup
- **MCPTestHelper**: MCP service integration testing
- **WorkflowAssertions**: Custom assertion helpers
- **VerificationHelper**: Result verification and validation

### Key Features

#### Status Polling Architecture
```python
# Automatic workflow completion waiting
result = await workflow_helper.run_and_wait_for_completion(
    task_description="Create a Python script",
    agent_role="dev",
    timeout_seconds=120,
    poll_interval=5.0
)
```

#### LangGraph Execution Verification
```python
# Verify proper LangGraph node execution
workflow_helper.verify_langgraph_execution_flow(result)
```

#### Comprehensive Cleanup
```python
try:
    # Test logic
    result = await orchestrator_service.run_workflow(...)
finally:
    # Immediate cleanup
    file_helper.cleanup_files(created_file, backup_file)
    await mcp_helper.cleanup_test_resources(task_id=task_id)
```

## Running Tests

### Prerequisites
1. Docker and Docker Compose installed
2. Test environment configured in `test/.env`
3. At least one AI provider API key configured
4. MCP services available (if running MCP tests)

### Quick Start
```bash
# Run all orchestrator smoke tests
pytest test/ai_smoke_test/agent/orchestrator/ -v

# Run specific test categories
pytest test/ai_smoke_test/agent/orchestrator/ -m basic_workflow
pytest test/ai_smoke_test/agent/orchestrator/ -m mcp_integration
pytest test/ai_smoke_test/agent/orchestrator/ -m approval_workflow

# Run with specific markers
pytest test/ai_smoke_test/agent/orchestrator/ -m smoke_test
```

### Test Configuration
Tests use the following environment variables from `test/.env`:
- AI provider API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
- Database configuration (DATABASE_URL)
- Redis configuration (REDIS_URL)
- MCP Gateway configuration (MCP_GATEWAY_URL)

## Test Structure

```
test/ai_smoke_test/agent/orchestrator/
├── conftest.py                           # Test infrastructure and fixtures
├── test_basic_workflows.py               # Basic workflow tests
├── test_mcp_integration.py               # MCP integration tests
├── test_approval_workflows.py            # Approval workflow tests
├── utils/
│   ├── __init__.py
│   ├── workflow_helpers.py              # Status polling and management
│   ├── file_helpers.py                  # File operations
│   ├── mcp_helpers.py                   # MCP integration helpers
│   ├── assertions.py                    # Custom assertions
│   └── verification_helpers.py          # Result verification
└── README.md                           # This file
```

## Key Benefits

### 1. Real AI Model Testing
- Tests use actual AI models (OpenAI, Anthropic, etc.)
- Verifies real-world behavior and performance
- Catches issues that mocks might miss

### 2. Comprehensive Service Integration
- Tests with real databases (PostgreSQL)
- Tests with real cache (Redis)
- Tests with real MCP services
- End-to-end verification

### 3. Proper Async Handling
- Status polling for long-running workflows
- Timeout management
- Race condition prevention

### 4. LangGraph Verification
- Validates proper node execution
- Checks state transitions
- Verifies workflow completion

### 5. Reliable Cleanup
- Each test cleans up its own resources
- No test pollution
- Consistent test environment

## Test Markers

- `@pytest.mark.smoke_test`: All orchestrator smoke tests
- `@pytest.mark.basic_workflow`: Basic workflow tests
- `@pytest.mark.mcp_integration`: MCP integration tests
- `@pytest.mark.approval_workflow`: Approval workflow tests

## Performance Considerations

### Time Management
- Simple tasks: 60-120 seconds
- Complex workflows: 180-240 seconds
- MCP integration: 240-300 seconds
- Approval workflows: 180-300 seconds

### Cost Management
- Tests use real AI APIs and incur costs
- Monitor usage and set spending limits
- Consider using cheaper models for testing

## Troubleshooting

### Common Issues

1. **Docker Services Not Starting**
   - Check Docker is running
   - Verify docker-compose.yml exists
   - Check port conflicts

2. **AI API Key Issues**
   - Verify API keys in test/.env
   - Check API key permissions
   - Verify API service availability

3. **MCP Service Issues**
   - Check MCP Gateway connectivity
   - Verify MCP server configuration
   - Check service health endpoints

4. **Test Timeouts**
   - Increase timeout values for complex workflows
   - Check AI model response times
   - Verify network connectivity

### Debug Mode
Run tests with verbose output for debugging:
```bash
pytest test/ai_smoke_test/agent/orchestrator/ -v -s --tb=short
```

## Best Practices

1. **Always use explicit file paths** in AI task descriptions
2. **Clean up resources immediately** in try/finally blocks
3. **Use appropriate timeouts** for different task types
4. **Verify LangGraph execution** for comprehensive testing
5. **Monitor costs** when running with real AI models
6. **Use test markers** to organize test execution

## Future Enhancements

1. **Performance Tests**: Add workflow performance benchmarks
2. **Load Tests**: Test concurrent workflow execution
3. **Integration Tests**: Add more external service integrations
4. **Regression Tests**: Add specific regression test cases
5. **Monitoring**: Add test execution monitoring and alerting

## Contributing

When adding new tests:
1. Follow the existing test patterns
2. Use the helper utilities provided
3. Include proper cleanup logic
4. Add appropriate test markers
5. Update documentation as needed

## Support

For questions or issues with the orchestrator smoke tests:
1. Check this README first
2. Review the test code for examples
3. Check the troubleshooting section
4. Contact the development team
