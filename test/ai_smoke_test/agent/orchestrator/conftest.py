from __future__ import annotations

import logging
import os
import time
from collections.abc import Iterable
from pathlib import Path
from typing import AsyncGenerator

import httpx
import pytest
from testcontainers.compose import DockerCompose

from gearmeshing_ai.agent.orchestrator.service import OrchestratorService
from gearmeshing_ai.agent.orchestrator.models import WorkflowResult, WorkflowStatus
from gearmeshing_ai.agent.mcp.client import EasyMCPClient
from gearmeshing_ai.agent.mcp.gateway import GatewayApiClient
from test.settings import test_settings
from test.ai_smoke_test.agent.orchestrator.utils.workflow_helpers import workflow_helper
from test.ai_smoke_test.agent.orchestrator.utils.file_helpers import file_helper
from test.ai_smoke_test.agent.orchestrator.utils.mcp_helpers import mcp_helper
from test.ai_smoke_test.agent.orchestrator.utils.assertions import workflow_assertions
from test.ai_smoke_test.agent.orchestrator.utils.verification_helpers import verification_helper


def endpoint_candidates(host: str, port: int) -> list[str]:
    """Create a list of common SSE endpoint candidates for testing."""
    return [
        f"http://{host}:{port}/sse/sse",
    ]


def wait_mcp_gateway_ready(urls: Iterable[str], timeout: float = 30.0) -> str:
    """Wait for MCP Gateway to be ready and return the working URL."""
    import asyncio

    async def _wait_for_ready() -> str:
        start_time = time.time()

        while time.time() - start_time < timeout:
            for url in urls:
                try:
                    # Try to connect to the gateway to verify it's ready
                    async with httpx.AsyncClient() as client:
                        response = await client.get(f"{url}/health", timeout=5.0)
                        if response.status_code == 200:
                            logging.info(f"MCP Gateway ready at {url}")
                            return url
                except Exception:
                    logging.error(f"Failed to connect to MCP Gateway at {url}", exc_info=True)
                    pass
            
            await asyncio.sleep(2.0)
        
        raise TimeoutError(f"MCP Gateway not ready within {timeout} seconds at any of: {list(urls)}")

    return asyncio.run(_wait_for_ready())


@pytest.fixture(scope="session")
def _compose_env() -> Iterable[None]:
    """Set up environment variables for Docker Compose services."""
    # Backup original environment
    original_env = os.environ.copy()
    
    try:
        # Set up test environment variables
        os.environ.update({
            # Redis configuration
            "REDIS_URL": "redis://localhost:6379/0",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "REDIS_DB": "0",
            
            # MCP Gateway configuration
            "MCP_GATEWAY_URL": "http://localhost:4444",
            "MCP_GATEWAY_HOST": "localhost",
            "MCP_GATEWAY_PORT": "4444",
            
            # ClickUp MCP Server
            "CLICKUP_MCP_URL": "http://localhost:8082",
            "CLICKUP_MCP_HOST": "localhost",
            "CLICKUP_MCP_PORT": "8082",
            
            # Database configuration
            "DATABASE_URL": "postgresql://postgres:password@localhost:5432/gearmeshing_test",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "gearmeshing_test",
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "password",
            
            # Test settings
            "TESTING": "true",
            "ENVIRONMENT": "test",
        })
        
        # Export AI provider API keys from test settings
        if test_settings.ai_provider.openai.api_key:
            os.environ["OPENAI_API_KEY"] = test_settings.ai_provider.openai.api_key.get_secret_value()
        if test_settings.ai_provider.anthropic.api_key:
            os.environ["ANTHROPIC_API_KEY"] = test_settings.ai_provider.anthropic.api_key.get_secret_value()
        if test_settings.ai_provider.gemini.api_key:
            os.environ["GOOGLE_API_KEY"] = test_settings.ai_provider.gemini.api_key.get_secret_value()
        if test_settings.ai_provider.xai.api_key:
            os.environ["XAI_API_KEY"] = test_settings.ai_provider.xai.api_key.get_secret_value()
        
        yield
    
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


@pytest.fixture(scope="session")
def compose_stack(_compose_env: Iterable[None]) -> Iterable[DockerCompose]:
    """Start Docker Compose stack for smoke tests."""
    project_test_root = Path("./test")
    compose_file = project_test_root / "docker-compose.yml"
    
    if not compose_file.exists():
        pytest.skip(f"Docker Compose file not found at {compose_file}")
    
    compose = DockerCompose(str(project_test_root))
    
    try:
        logging.info("Starting Docker Compose stack for orchestrator smoke tests...")
        compose.start()
        
        # Wait a bit for services to initialize
        time.sleep(10)
        
        logging.info("Docker Compose stack started successfully")
        yield compose
    
    finally:
        logging.info("Stopping Docker Compose stack...")
        try:
            compose.stop()
            logging.info("Docker Compose stack stopped")
        except Exception as e:
            logging.error(f"Error stopping Docker Compose stack: {e}")


@pytest.fixture(scope="session")
def mcp_gateway_url(compose_stack: DockerCompose) -> str:
    """Get MCP Gateway URL from Docker Compose stack."""
    gateway_urls = endpoint_candidates("localhost", 4444)
    return wait_mcp_gateway_ready(gateway_urls)


@pytest.fixture(scope="session")
def mcp_gateway_client(mcp_gateway_url: str) -> GatewayApiClient:
    """Create MCP Gateway client for smoke tests."""
    return GatewayApiClient(mcp_gateway_url)


@pytest.fixture(scope="session")
def orchestrator_service(compose_stack: DockerCompose) -> OrchestratorService:
    """Create orchestrator service for smoke tests."""
    # Initialize orchestrator service with test configuration
    service = OrchestratorService()
    
    # OrchestratorService doesn't have a configure method,
    # it uses the runtime system which reads from environment
    return service


@pytest.fixture
def smoke_test_environment() -> dict[str, bool]:
    """Provide smoke test environment configuration."""
    return {
        "use_real_ai": True,
        "use_real_mcp": True,
        "cleanup_after_test": True,
        "verify_langgraph": True,
    }


@pytest.fixture
def test_file_workspace(tmp_path: Path) -> Path:
    """Isolated temporary directory for file generation tests."""
    return tmp_path


# Custom markers for test organization
def pytest_configure(config):
    """Register custom markers for orchestrator smoke tests."""
    config.addinivalue_line(
        "markers", "smoke_test: Mark test as orchestrator smoke test"
    )
    config.addinivalue_line(
        "markers", "basic_workflow: Mark test as basic workflow test"
    )
    config.addinivalue_line(
        "markers", "mcp_integration: Mark test as MCP integration test"
    )
    config.addinivalue_line(
        "markers", "approval_workflow: Mark test as approval workflow test"
    )


@pytest.fixture(scope="session", autouse=True)
def check_dependencies():
    """Check if required dependencies are available for smoke tests."""
    # Enable debug logging for troubleshooting
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load default roles from config
    from gearmeshing_ai.agent.roles.loader import load_default_roles
    try:
        roles = load_default_roles()
        logging.info(f"Loaded {len(roles)} default roles for smoke tests")
    except Exception as e:
        logging.warning(f"Failed to load default roles: {e}")
    
    # Check for testcontainers
    try:
        import testcontainers
    except ImportError:
        pytest.skip("testcontainers not installed - required for orchestrator smoke tests")
    
    # Check for AI provider API keys
    has_ai_keys = any([
        test_settings.ai_provider.openai.api_key,
        test_settings.ai_provider.anthropic.api_key,
        test_settings.ai_provider.gemini.api_key,
        test_settings.ai_provider.xai.api_key,
    ])
    
    if not has_ai_keys:
        pytest.skip("No AI provider API keys configured - set up test/.env with at least one provider")
    
    # Check for docker
    try:
        import docker
        client = docker.from_env()
        client.ping()
    except Exception:
        pytest.skip("Docker not available - required for orchestrator smoke tests")
