from __future__ import annotations

import logging
import os
import time
from collections.abc import Iterable
from pathlib import Path

import httpx
import pytest
from testcontainers.compose import DockerCompose

from gearmeshing_ai.agent_core.mcp.client import EasyMCPClient
from gearmeshing_ai.agent_core.mcp.gateway import GatewayApiClient
from gearmeshing_ai.core.models.setting import settings
from test.settings import TestSettings


def clickup_port() -> int:
    """Get ClickUp MCP server port from test settings."""
    test_settings = TestSettings()
    if test_settings.mcp.server and test_settings.mcp.server.clickup:
        return int(test_settings.mcp.server.clickup.server_port)
    return 8082  # Default fallback


def endpoint_candidates(host: str, port: int) -> list[str]:
    """Create a list of common SSE endpoint candidates for testing."""
    return [
        f"http://{host}:{port}/sse/sse",
    ]


def wait_clickup_ready(urls: Iterable[str], timeout: float = 5.0) -> str:
    """Wait for ClickUp MCP server to be ready and return the working URL."""
    import asyncio
    import time

    async def _wait_for_ready():
        start_time = time.time()

        # If no URL is ready immediately, wait and retry
        while time.time() - start_time < timeout:
            for url in urls:
                try:
                    # Try to list tools from the server to verify it's ready
                    tools = await EasyMCPClient.list_tools_sse(url)
                    logging.info(f"ClickUp MCP server ready at {url} with {tools}")
                    # If we got tools (or empty list), server is ready
                    return url
                except Exception:
                    logging.error("Fail to connect to ClickUp MCP server", exc_info=True)
                    pass
            await asyncio.sleep(0.5)

        raise RuntimeError(f"No ClickUp MCP server became ready within {timeout}s")

    try:
        return asyncio.run(_wait_for_ready())
    except Exception as e:
        raise RuntimeError(f"ClickUp MCP server not ready: {e}")


@pytest.fixture(scope="session")
def _compose_env() -> Iterable[None]:
    # Provide env vars required by docker-compose.yml services
    prev: dict[str, str] = {}

    def _set(k: str, v: str) -> None:
        if k in os.environ:
            prev[k] = os.environ[k]
        os.environ[k] = v

    # Load test settings to get MCP server configurations
    test_settings = TestSettings()

    # MCP Gateway *IBM/mcp-context-forge* - get all secrets from test settings model
    mcp_gateway_config = test_settings.mcp.gateway
    _set("MCP__GATEWAY__JWT_SECRET", mcp_gateway_config.jwt_secret.get_secret_value())
    _set("MCP__GATEWAY__ADMIN_PASSWORD", mcp_gateway_config.admin_password.get_secret_value())
    _set("MCP__GATEWAY__ADMIN_EMAIL", mcp_gateway_config.admin_email)
    _set("MCP__GATEWAY__ADMIN_FULL_NAME", mcp_gateway_config.admin_full_name)
    _set("MCP__GATEWAY__DB_URL", mcp_gateway_config.db_url.get_secret_value())
    _set("MCP__GATEWAY__REDIS_URL", mcp_gateway_config.redis_url)

    # MCP Server configurations from test settings
    if test_settings.mcp.server:
        # ClickUp MCP Server
        clickup_config = test_settings.mcp.server.clickup
        _set("MCP__SERVER__CLICKUP__SERVER_HOST", clickup_config.server_host)
        _set("MCP__SERVER__CLICKUP__SERVER_PORT", clickup_config.server_port)
        _set("MCP__SERVER__CLICKUP__MCP_TRANSPORT", clickup_config.mcp_transport)
        if clickup_config.api_token:
            _set("MCP__SERVER__CLICKUP__API_TOKEN", clickup_config.api_token.get_secret_value())
        _set("MCP__SERVER__CLICKUP__MQ_BACKEND", clickup_config.mq_backend)

        # Slack MCP Server
        slack_config = test_settings.mcp.server.slack
        _set("MCP__SERVER__SLACK__HOST", slack_config.host)
        _set("MCP__SERVER__SLACK__PORT", slack_config.port)
        _set("MCP__SERVER__SLACK__MCP_TRANSPORT", slack_config.mcp_transport)
        if slack_config.bot_token:
            _set("MCP__SERVER__SLACK__BOT_TOKEN", slack_config.bot_token.get_secret_value())
        if slack_config.bot_id:
            _set("MCP__SERVER__SLACK__BOT_ID", slack_config.bot_id)
        if slack_config.app_id:
            _set("MCP__SERVER__SLACK__APP_ID", slack_config.app_id)
        if slack_config.user_token:
            _set("MCP__SERVER__SLACK__USER_TOKEN", slack_config.user_token.get_secret_value())
        if slack_config.signing_secret:
            _set("MCP__SERVER__SLACK__SIGNING_SECRET", slack_config.signing_secret.get_secret_value())
        _set("MCP__SERVER__SLACK__MQ_BACKEND", slack_config.mq_backend)

        # GitHub MCP Server
        github_config = test_settings.mcp.server.github
        if github_config.token:
            _set("MCP__SERVER__GITHUB__TOKEN", github_config.token.get_secret_value())
        _set("MCP__SERVER__GITHUB__TOOLSETS", github_config.toolsets)
        if github_config.default_repo:
            _set("MCP__SERVER__GITHUB__DEFAULT_REPO", github_config.default_repo)

        # Atlassian MCP Server
        atlassian_config = test_settings.mcp.server.atlassian
        if atlassian_config.base_url:
            _set("MCP__SERVER__ATLASSIAN__BASE_URL", atlassian_config.base_url)
        if atlassian_config.email:
            _set("MCP__SERVER__ATLASSIAN__EMAIL", atlassian_config.email)
        if atlassian_config.api_token:
            _set("MCP__SERVER__ATLASSIAN__API_TOKEN", atlassian_config.api_token.get_secret_value())

        # Grafana MCP Server
        grafana_config = test_settings.mcp.server.grafana
        if grafana_config.url:
            _set("MCP__SERVER__GRAFANA__URL", grafana_config.url)
        if grafana_config.api_token:
            _set("MCP__SERVER__GRAFANA__API_TOKEN", grafana_config.api_token.get_secret_value())

        # Loki MCP Server
        loki_config = test_settings.mcp.server.loki
        if loki_config.url:
            _set("MCP__SERVER__LOKI__URL", loki_config.url)
        if loki_config.api_token:
            _set("MCP__SERVER__LOKI__API_TOKEN", loki_config.api_token.get_secret_value())

    try:
        yield
    finally:
        env_keys = {
            "MCP__GATEWAY__JWT_SECRET",
            "MCP__GATEWAY__ADMIN_PASSWORD",
            "MCP__GATEWAY__ADMIN_EMAIL",
            "MCP__GATEWAY__ADMIN_FULL_NAME",
            "MCP__GATEWAY__DB_URL",
            "MCP__GATEWAY__REDIS_URL",
            # ClickUp
            "MCP__SERVER__CLICKUP__SERVER_HOST",
            "MCP__SERVER__CLICKUP__SERVER_PORT",
            "MCP__SERVER__CLICKUP__MCP_TRANSPORT",
            "MCP__SERVER__CLICKUP__API_TOKEN",
            "MCP__SERVER__CLICKUP__MQ_BACKEND",
            # Slack
            "MCP__SERVER__SLACK__HOST",
            "MCP__SERVER__SLACK__PORT",
            "MCP__SERVER__SLACK__MCP_TRANSPORT",
            "MCP__SERVER__SLACK__BOT_TOKEN",
            "MCP__SERVER__SLACK__BOT_ID",
            "MCP__SERVER__SLACK__APP_ID",
            "MCP__SERVER__SLACK__USER_TOKEN",
            "MCP__SERVER__SLACK__SIGNING_SECRET",
            "MCP__SERVER__SLACK__MQ_BACKEND",
            # GitHub
            "MCP__SERVER__GITHUB__TOKEN",
            "MCP__SERVER__GITHUB__TOOLSETS",
            "MCP__SERVER__GITHUB__DEFAULT_REPO",
            # Atlassian
            "MCP__SERVER__ATLASSIAN__BASE_URL",
            "MCP__SERVER__ATLASSIAN__EMAIL",
            "MCP__SERVER__ATLASSIAN__API_TOKEN",
            # Grafana
            "MCP__SERVER__GRAFANA__URL",
            "MCP__SERVER__GRAFANA__API_TOKEN",
            # Loki
            "MCP__SERVER__LOKI__URL",
            "MCP__SERVER__LOKI__API_TOKEN",
        }
        for k in env_keys:
            if k in prev:
                os.environ[k] = prev[k]
            else:
                os.environ.pop(k, None)


@pytest.fixture(scope="session")
def compose_stack(_compose_env: Iterable[None]) -> Iterable[DockerCompose]:
    # Repo root is the CWD when running tests; compose file is at the root
    project_test_root = Path("./test")
    compose = DockerCompose(str(project_test_root))
    compose.start()
    try:
        yield compose
    finally:
        compose.stop()


@pytest.fixture
def clickup_container(compose_stack: DockerCompose) -> DockerCompose:
    return compose_stack


@pytest.fixture
def clickup_base_url(clickup_container: DockerCompose) -> str:
    port_int = clickup_port()
    base = wait_clickup_ready(endpoint_candidates("127.0.0.1", port_int), timeout=20.0)
    return base


def gateway_port() -> int:
    return 4444


def _write_catalog_for_gateway(clickup_base_url: str) -> Path:
    # Deprecated: compose uses a static catalog file; keep function for compatibility
    return Path("./configs/mcp_gateway/mcp-catalog_e2e.yml").resolve()


def _wait_gateway_ready(base_url: str, timeout: float = 30.0) -> None:
    start = time.time()
    last: Exception | None = None
    while time.time() - start < timeout:
        try:
            user: str = settings.mcp.gateway.admin_email
            secret: str = settings.mcp.gateway.admin_password.get_secret_value()
            token = GatewayApiClient.generate_bearer_token(jwt_secret_key=secret, username=user)
            r = httpx.get(f"{base_url}/health", headers={"Authorization": token}, timeout=3.0)
            if r.status_code == 200:
                return
        except Exception as e:
            last = e
        time.sleep(0.5)
    if last:
        raise last
    raise RuntimeError("Gateway not ready and no error captured")


@pytest.fixture(scope="session")
def gateway_client(compose_stack: DockerCompose):
    base = f"http://127.0.0.1:{gateway_port()}"
    # Generate token once
    user: str = settings.mcp.gateway.admin_email
    secret: str = settings.mcp.gateway.admin_password.get_secret_value()
    token = GatewayApiClient.generate_bearer_token(jwt_secret_key=secret, username=user)

    mgmt_client = httpx.Client(base_url=base)
    client = GatewayApiClient(base, client=mgmt_client, auth_token=token)

    # Ensure health before yielding
    start = time.time()
    last_err: Exception | None = None
    while time.time() - start < 30.0:
        try:
            h = client.health()
            if h:
                break
        except Exception as e:
            last_err = e
            time.sleep(0.5)
            continue
    if last_err and time.time() - start >= 30.0:
        raise last_err

    try:
        yield client
    finally:
        try:
            mgmt_client.close()
        except Exception:
            pass


@pytest.fixture(scope="session")
def gateway_client_with_register_servers(gateway_client: GatewayApiClient):
    # pre-prcoess
    gateway_list = gateway_client.admin.gateway.list()
    if not gateway_list:
        mcp_registry = gateway_client.admin.mcp_registry.list()
        for mr in mcp_registry.servers:
            register_result = gateway_client.admin.mcp_registry.register(mr.id)
            assert register_result.success, (
                f"Register the MCP server fail. Please check it. Error: {register_result.error}"
            )
    return gateway_client
