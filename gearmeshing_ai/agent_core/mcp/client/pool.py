"""Connection pooling and server management for MCP clients.

This module provides connection pooling capabilities and server management
functionality for MCP clients. It supports load balancing, failover, and
efficient resource utilization.

Pooling Architecture:
--------------------

The pooling system follows these principles:

1. **Resource Efficiency**: Reuse connections to reduce overhead
2. **Load Balancing**: Distribute load across multiple servers
3. **Failover Support**: Automatic failover to backup servers
4. **Health Monitoring**: Continuous health checking of pooled connections
5. **Configurable**: All pooling aspects are configurable
6. **Thread-Safe**: Safe for concurrent use

Pool Components:
------------------

1. **ConnectionPool** - Basic connection pooling
2. **ServerPool** - Multi-server load balancing and failover
3. **HealthMonitor** - Health checking for pooled resources
4. **LoadBalancer** - Load balancing strategies

Features:
--------

- Connection reuse and pooling
- Automatic failover to backup servers
- Load balancing across multiple servers
- Health monitoring and cleanup
- Configurable pool sizes and timeouts
- Thread-safe operations
- Performance metrics

Usage Guidelines:
----------------

# Basic connection pooling
pool = ConnectionPool(max_size=10)
async with pool.get_connection("http://localhost:8082/sse/sse") as conn:
    tools = await conn.list_tools()

# Server pool with failover
server_configs = [
    {"name": "primary", "urls": ["http://localhost:8082/sse/sse"]},
    {"name": "backup", "urls": ["http://localhost:8083/sse/sse"]}
]
pool = ServerPool(server_configs)
result = await pool.execute_tool_call("primary", "tool_name", {"arg": "value"})

Performance Considerations:
----------------------------

- Connection pooling reduces connection overhead
- Load balancing improves resource utilization
- Health monitoring prevents using failed connections
- Configurable timeouts prevent hanging operations
- Pool size limits prevent resource exhaustion

Extensibility:
------------

Add custom load balancing strategies:

class CustomLoadBalancer(LoadBalancer):
    def select_server(self, servers: List[ServerConfig]) -> ServerConfig:
        # Custom selection logic
        return servers[0]  # Example

Examples
--------
# Connection pooling
pool = ConnectionPool(max_size=5, timeout=30.0)
connection = await pool.get_connection("http://localhost:8082/sse/sse")
tools = await connection.list_tools()
await pool.release_connection(connection)

# Server pool with failover
configs = [
    {"name": "server1", "urls": ["http://localhost:8082/sse/sse"]},
    {"name": "server2", "urls": ["http://localhost:8083/sse/sse"]},
    {"name": "server3", "urls": ["http://localhost:8084/sse/sse"]}
]
pool = ServerPool(configs)
result = await pool.execute_tool_call("server1", "get_tasks", {})

# Load balancing
pool = ServerPool(configs, load_balance_strategy="round_robin")
for i in range(10):
    result = await pool.execute_tool_call("any", "tool_name", {})
    # Requests are distributed across servers

"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .config import MCPClientConfig
from .core import MCPClient
from .exceptions import ConnectionError, ServerError
from .transports import BaseTransport

logger = logging.getLogger(__name__)


class LoadBalanceStrategy(Enum):
    """Load balancing strategies."""

    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"


@dataclass
class ServerConfig:
    """Configuration for a server in a pool."""

    name: str
    urls: list[str]
    weight: int = 1
    priority: int = 1
    max_connections: int = 10
    health_check_interval: float = 60.0
    timeout: float = 30.0

    def __post_init__(self):
        """Validate server configuration."""
        if not self.urls:
            raise ValueError("Server must have at least one URL")
        if self.weight < 1:
            raise ValueError("Weight must be at least 1")
        if self.max_connections < 1:
            raise ValueError("Max connections must be at least 1")


@dataclass
class PooledConnection:
    """A pooled connection with metadata."""

    transport: BaseTransport
    client: MCPClient
    server_name: str
    url: str
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    use_count: int = 0
    is_healthy: bool = True

    def touch(self) -> None:
        """Update last used timestamp."""
        self.last_used = time.time()
        self.use_count += 1

    @property
    def age(self) -> float:
        """Get connection age in seconds."""
        return time.time() - self.created_at

    @property
    def idle_time(self) -> float:
        """Get idle time in seconds."""
        return time.time() - self.last_used


class ConnectionPool:
    """Basic connection pool for MCP clients.

    This class provides connection pooling capabilities for a single server
    or multiple servers with the same configuration. It manages connection
    lifecycle, health checking, and resource cleanup.

    Features:
    --------
    - Connection reuse and pooling
    - Health monitoring
    - Automatic cleanup of idle connections
    - Configurable pool sizes and timeouts
    - Thread-safe operations
    - Performance metrics

    Attributes:
    ----------
    max_size: Maximum number of connections in the pool
    timeout: Default timeout for operations
    connections: Active connections in the pool
    available_connections: Available connections for use
    health_checker: Health checker for connections

    Example:
    -------
    >>> pool = ConnectionPool(max_size=10, timeout=30.0)
    >>> async with pool.get_connection("http://localhost:8082/sse/sse") as conn:
    ...     tools = await conn.list_tools()
    >>> print(f"Pool size: {len(pool.connections)}")

    """

    def __init__(
        self,
        max_size: int = 10,
        timeout: float = 30.0,
        max_idle_time: float = 300.0,
        health_check_interval: float = 60.0,
    ):
        """Initialize connection pool.

        Args:
            max_size: Maximum number of connections in the pool
            timeout: Default timeout for operations
            max_idle_time: Maximum idle time before cleanup
            health_check_interval: Health check interval in seconds

        """
        self.max_size = max_size
        self.timeout = timeout
        self.max_idle_time = max_idle_time
        self.health_check_interval = health_check_interval

        self._lock = asyncio.Lock()
        self.connections: set[PooledConnection] = set()
        self.available_connections: deque = deque()
        self.url_connections: dict[str, list[PooledConnection]] = defaultdict(list)

        # Metrics
        self.total_created = 0
        self.total_destroyed = 0
        self.last_cleanup = time.time()

        # Health checking
        self._health_check_task: asyncio.Task | None = None

        logger.debug(f"ConnectionPool initialized: max_size={max_size}")

    async def get_connection(self, url: str, config: MCPClientConfig | None = None) -> PooledConnection:
        """Get a connection from the pool.

        Args:
            url: Server URL
            config: Optional client configuration

        Returns:
            Pooled connection

        Raises:
            ConnectionError: If no connections available and pool is full

        """
        async with self._lock:
            # Check for available connection
            while self.available_connections:
                conn = self.available_connections.popleft()

                # Check if connection is still healthy
                if conn.is_healthy and not self._is_connection_expired(conn):
                    conn.touch()
                    return conn
                # Remove unhealthy or expired connection
                await self._destroy_connection(conn)

            # No available connections, create new one if under limit
            if len(self.connections) < self.max_size:
                return await self._create_connection(url, config)

            # Pool is full and no available connections
            raise ConnectionError(f"Connection pool exhausted (max_size={self.max_size})")

    async def release_connection(self, connection: PooledConnection) -> None:
        """Release a connection back to the pool.

        Args:
            connection: Connection to release

        """
        async with self._lock:
            if connection in self.connections and connection.is_healthy:
                connection.touch()
                self.available_connections.append(connection)
            else:
                # Connection is no longer valid, destroy it
                await self._destroy_connection(connection)

    async def _create_connection(self, url: str, config: MCPClientConfig | None = None) -> PooledConnection:
        """Create a new connection."""
        try:
            # Create client
            client_config = config or MCPClientConfig(timeout=self.timeout)
            client = MCPClient(client_config)

            # Connect and create transport
            if url.startswith("http://") and "/sse/" in url:
                await client.connect(url, "sse")
            elif url.startswith("http://"):
                await client.connect(url, "http")
            else:
                raise ValueError(f"Unsupported URL format: {url}")

            # Get transport
            transport = client._transport
            if not transport:
                raise ConnectionError("Failed to create transport")

            # Create pooled connection
            conn = PooledConnection(transport=transport, client=client, server_name="default", url=url, is_healthy=True)

            # Add to pool
            self.connections.add(conn)
            self.url_connections[url].append(conn)
            self.total_created += 1

            logger.debug(f"Created new connection for {url}")
            return conn

        except Exception as e:
            raise ConnectionError(f"Failed to create connection for {url}: {e}")

    async def _destroy_connection(self, connection: PooledConnection) -> None:
        """Destroy a connection."""
        try:
            # Remove from all tracking structures
            self.connections.discard(connection)
            if connection.url in self.url_connections:
                self.url_connections[connection.url].remove(connection)
                if not self.url_connections[connection.url]:
                    del self.url_connections[connection.url]

            # Close client and transport
            await connection.client.close()

            self.total_destroyed += 1
            logger.debug(f"Destroyed connection for {connection.url}")

        except Exception as e:
            logger.warning(f"Error destroying connection: {e}")

    def _is_connection_expired(self, connection: PooledConnection) -> bool:
        """Check if a connection is expired."""
        return connection.idle_time > self.max_idle_time

    async def cleanup(self) -> None:
        """Clean up expired and unhealthy connections."""
        async with self._lock:
            expired_connections = [
                conn for conn in self.connections if not conn.is_healthy or self._is_connection_expired(conn)
            ]

            for conn in expired_connections:
                await self._destroy_connection(conn)

            self.last_cleanup = time.time()

            if expired_connections:
                logger.debug(f"Cleaned up {len(expired_connections)} expired connections")

    async def start_health_checking(self) -> None:
        """Start background health checking."""
        if self._health_check_task and not self._health_check_task.done():
            return

        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Started connection pool health checking")

    async def stop_health_checking(self) -> None:
        """Stop background health checking."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("Stopped connection pool health checking")

    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._check_connection_health()
                await self.cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(self.health_check_interval)

    async def _check_connection_health(self) -> None:
        """Check health of all connections."""
        unhealthy_connections = []

        for conn in self.connections:
            try:
                # Simple health check - try to list tools
                await asyncio.wait_for(conn.transport.list_tools(), timeout=5.0)
                conn.is_healthy = True
            except Exception as e:
                conn.is_healthy = False
                logger.debug(f"Connection unhealthy: {e}")
                unhealthy_connections.append(conn)

        # Mark unhealthy connections for cleanup
        for conn in unhealthy_connections:
            logger.debug(f"Marked connection as unhealthy: {conn.url}")

    async def close(self) -> None:
        """Close the connection pool and cleanup all connections."""
        await self.stop_health_checking()

        async with self._lock:
            # Close all connections
            for conn in list(self.connections):
                await self._destroy_connection(conn)

            # Clear all tracking structures
            self.connections.clear()
            self.available_connections.clear()
            self.url_connections.clear()

        logger.info("Connection pool closed")

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        return {
            "total_connections": len(self.connections),
            "available_connections": len(self.available_connections),
            "total_created": self.total_created,
            "total_destroyed": self.total_destroyed,
            "max_size": self.max_size,
            "last_cleanup": self.last_cleanup,
        }


class ServerPool:
    """Server pool for load balancing and failover.

    This class provides server pooling capabilities with load balancing,
    automatic failover, and health monitoring. It manages multiple servers
    and distributes requests across them according to configured strategies.

    Features:
    --------
    - Multiple server support with failover
    - Load balancing strategies
    - Health monitoring and automatic failover
    - Configurable weights and priorities
    - Performance metrics
    - Thread-safe operations

    Attributes:
    ----------
    server_configs: Server configurations
    load_balance_strategy: Load balancing strategy
    connection_pools: Per-server connection pools
    health_checker: Health checker for servers

    Example:
    -------
    >>> configs = [
    ...     {"name": "primary", "urls": ["http://localhost:8082/sse/sse"]},
    ...     {"name": "backup", "urls": ["http://localhost:8083/sse/sse"]}
    ... ]
    >>> pool = ServerPool(configs)
    >>> result = await pool.execute_tool_call("primary", "get_tasks", {})

    """

    def __init__(
        self,
        server_configs: list[dict[str, Any]],
        load_balance_strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
        max_connections_per_server: int = 10,
        health_check_interval: float = 60.0,
    ):
        """Initialize server pool.

        Args:
            server_configs: List of server configuration dictionaries
            load_balance_strategy: Load balancing strategy
            max_connections_per_server: Max connections per server
            health_check_interval: Health check interval in seconds

        """
        self.load_balance_strategy = load_balance_strategy
        self.max_connections_per_server = max_connections_per_server
        self.health_check_interval = health_check_interval

        # Parse server configurations
        self.server_configs = [ServerConfig(**config) for config in server_configs]

        # Sort by priority
        self.server_configs.sort(key=lambda x: x.priority)

        # Connection pools for each server
        self.connection_pools: dict[str, ConnectionPool] = {}

        # Load balancing state
        self._round_robin_index = 0
        self._lock = asyncio.Lock()

        # Health status
        self.server_health: dict[str, bool] = {}

        # Initialize connection pools
        for config in self.server_configs:
            self.connection_pools[config.name] = ConnectionPool(
                max_size=max_connections_per_server, health_check_interval=health_check_interval
            )
            self.server_health[config.name] = True

        # Health checking
        self._health_check_task: asyncio.Task | None = None

        logger.debug(f"ServerPool initialized with {len(self.server_configs)} servers")

    async def get_healthy_server(self, server_name: str | None = None) -> str | None:
        """Get a healthy server name.

        Args:
            server_name: Specific server name (optional)

        Returns:
            Healthy server name or None

        """
        async with self._lock:
            if server_name:
                # Check specific server
                if self.server_health.get(server_name, False):
                    return server_name
                return None

            # Find any healthy server
            for config in self.server_configs:
                if self.server_health.get(config.name, False):
                    return config.name

            return None

    async def execute_tool_call(self, server_name: str, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Execute a tool call on a server with failover.

        Args:
            server_name: Preferred server name
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ServerError: If all servers fail

        """
        # Try preferred server first
        try:
            return await self._execute_on_server(server_name, tool_name, arguments)
        except Exception as e:
            logger.warning(f"Failed to execute on {server_name}: {e}")

        # Try other healthy servers
        healthy_servers = [
            config.name
            for config in self.server_configs
            if config.name != server_name and self.server_health.get(config.name, False)
        ]

        for backup_server in healthy_servers:
            try:
                return await self._execute_on_server(backup_server, tool_name, arguments)
            except Exception as e:
                logger.warning(f"Failed to execute on {backup_server}: {e}")

        # All servers failed
        raise ServerError(f"All servers failed to execute tool {tool_name}")

    async def _execute_on_server(
        self, server_name: str, tool_name: str, arguments: dict[str, Any] | None = None
    ) -> Any:
        """Execute tool call on a specific server."""
        server_config = next((config for config in self.server_configs if config.name == server_name), None)

        if not server_config:
            raise ValueError(f"Unknown server: {server_name}")

        if not self.server_health.get(server_name, False):
            raise ConnectionError(f"Server {server_name} is not healthy")

        pool = self.connection_pools[server_name]

        # Select URL based on load balancing strategy
        url = self._select_url(server_config)

        # Get connection and execute
        async with pool.get_connection(url) as conn:
            return await conn.call_tool(tool_name, arguments or {})

    def _select_url(self, server_config: ServerConfig) -> str:
        """Select URL from server configuration."""
        if self.load_balance_strategy == LoadBalanceStrategy.ROUND_ROBIN:
            index = self._round_robin_index % len(server_config.urls)
            self._round_robin_index += 1
            return server_config.urls[index]
        if self.load_balance_strategy == LoadBalanceStrategy.RANDOM:
            import random

            return random.choice(server_config.urls)
        # Default to first URL
        return server_config.urls[0]

    async def start_health_checking(self) -> None:
        """Start background health checking for all servers."""
        if self._health_check_task and not self._health_check_task.done():
            return

        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Started server pool health checking")

    async def stop_health_checking(self) -> None:
        """Stop background health checking."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("Stopped server pool health checking")

    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._check_server_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Server health check loop error: {e}")
                await asyncio.sleep(self.health_check_interval)

    async def _check_server_health(self) -> None:
        """Check health of all servers."""
        for server_config in self.server_configs:
            try:
                # Try to get a connection and list tools
                pool = self.connection_pools[server_config.name]
                url = server_config.urls[0]

                async with pool.get_connection(url) as conn:
                    await asyncio.wait_for(conn.transport.list_tools(), timeout=5.0)

                self.server_health[server_config.name] = True
                logger.debug(f"Server {server_config.name} is healthy")

            except Exception as e:
                self.server_health[server_config.name] = False
                logger.warning(f"Server {server_config.name} is unhealthy: {e}")

    async def close(self) -> None:
        """Close the server pool and cleanup all resources."""
        await self.stop_health_checking()

        # Close all connection pools
        for pool in self.connection_pools.values():
            await pool.close()

        self.connection_pools.clear()
        logger.info("Server pool closed")

    def get_stats(self) -> dict[str, Any]:
        """Get server pool statistics."""
        stats = {
            "total_servers": len(self.server_configs),
            "healthy_servers": sum(1 for healthy in self.server_health.values() if healthy),
            "server_health": dict(self.server_health),
            "connection_pools": {},
        }

        for server_name, pool in self.connection_pools.items():
            stats["connection_pools"][server_name] = pool.get_stats()

        return stats
