"""
Persistence backends for orchestrator state storage.

Supports multiple backends:
- local: In-memory storage (for testing/development)
- database: SQL database (PostgreSQL, SQLite, etc.)
- redis: Redis cache
- filesystem: Local filesystem
"""

from .local import LocalPersistenceBackend

__all__ = [
    "LocalPersistenceBackend",
]
