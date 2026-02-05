import threading
from typing import Any


class AgentCache:
    """Singleton cache for storing instantiated AI agents.
    Uses 'role' as the primary key.
    """

    _instance = None
    _lock = threading.Lock()
    _agents: dict[str, Any] = {}

    def __new__(cls) -> "AgentCache":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AgentCache, cls).__new__(cls)
        return cls._instance

    def get(self, role: str) -> Any | None:
        """Retrieve an agent instance by role."""
        return self._agents.get(role)

    def set(self, role: str, agent: Any) -> None:
        """Store an agent instance by role."""
        self._agents[role] = agent

    def remove(self, role: str) -> None:
        """Remove an agent instance from cache."""
        if role in self._agents:
            del self._agents[role]

    def clear(self) -> None:
        """Clear all cached agents."""
        self._agents.clear()
