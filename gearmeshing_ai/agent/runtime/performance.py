"""Performance optimization and caching for runtime engine.

This module provides caching strategies, batch processing, and resource pooling
for optimized workflow execution.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheEntry(Generic[T]):
    """A cache entry with expiration.

    Attributes:
        value: Cached value
        created_at: Creation timestamp
        ttl_seconds: Time-to-live in seconds
        access_count: Number of times accessed

    """

    def __init__(self, value: T, ttl_seconds: int = 3600) -> None:
        """Initialize CacheEntry.

        Args:
            value: Value to cache
            ttl_seconds: Time-to-live in seconds

        """
        self.value = value
        self.created_at = datetime.utcnow()
        self.ttl_seconds = ttl_seconds
        self.access_count = 0

    def is_expired(self) -> bool:
        """Check if cache entry has expired.

        Returns:
            True if expired, False otherwise

        """
        expiration_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.utcnow() > expiration_time

    def access(self) -> T:
        """Access the cached value.

        Returns:
            Cached value

        """
        self.access_count += 1
        return self.value


class PerformanceCache(Generic[T]):
    """High-performance cache with TTL and statistics.

    Attributes:
        cache: Dictionary of cached entries
        max_size: Maximum cache size
        hit_count: Number of cache hits
        miss_count: Number of cache misses

    """

    def __init__(self, max_size: int = 1000) -> None:
        """Initialize PerformanceCache.

        Args:
            max_size: Maximum cache size

        """
        self.cache: dict[str, CacheEntry[T]] = {}
        self.max_size = max_size
        self.hit_count = 0
        self.miss_count = 0
        logger.debug(f"PerformanceCache initialized with max_size={max_size}")

    def set(self, key: str, value: T, ttl_seconds: int = 3600) -> None:
        """Set a cache entry.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time-to-live in seconds

        """
        # Evict oldest entry if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k].created_at,
            )
            del self.cache[oldest_key]
            logger.debug(f"Evicted cache entry: {oldest_key}")

        self.cache[key] = CacheEntry(value, ttl_seconds)
        logger.debug(f"Cached entry: {key}")

    def get(self, key: str) -> T | None:
        """Get a cache entry.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired

        """
        if key not in self.cache:
            self.miss_count += 1
            logger.debug(f"Cache miss: {key}")
            return None

        entry = self.cache[key]
        if entry.is_expired():
            del self.cache[key]
            self.miss_count += 1
            logger.debug(f"Cache expired: {key}")
            return None

        self.hit_count += 1
        logger.debug(f"Cache hit: {key}")
        return entry.access()

    def invalidate(self, key: str) -> None:
        """Invalidate a cache entry.

        Args:
            key: Cache key

        """
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"Invalidated cache entry: {key}")

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        logger.debug("Cleared all cache entries")

    def get_hit_rate(self) -> float:
        """Get cache hit rate.

        Returns:
            Hit rate as percentage

        """
        total = self.hit_count + self.miss_count
        if total == 0:
            return 0.0
        return (self.hit_count / total) * 100

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics

        """
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate_percent": self.get_hit_rate(),
            "utilization_percent": (len(self.cache) / self.max_size) * 100,
        }


class BatchProcessor:
    """Batch processor for efficient bulk operations.

    Attributes:
        batch_size: Size of batches
        pending_items: Items pending processing
        processed_count: Number of processed items

    """

    def __init__(self, batch_size: int = 100) -> None:
        """Initialize BatchProcessor.

        Args:
            batch_size: Size of batches

        """
        self.batch_size = batch_size
        self.pending_items: list[Any] = []
        self.processed_count = 0
        logger.debug(f"BatchProcessor initialized with batch_size={batch_size}")

    def add_item(self, item: Any) -> bool:
        """Add an item to the batch.

        Args:
            item: Item to add

        Returns:
            True if batch is ready for processing, False otherwise

        """
        self.pending_items.append(item)
        logger.debug(f"Added item to batch: {len(self.pending_items)}/{self.batch_size}")
        return len(self.pending_items) >= self.batch_size

    def get_batch(self) -> list[Any]:
        """Get the current batch.

        Returns:
            List of items in the batch

        """
        batch = self.pending_items[: self.batch_size]
        self.pending_items = self.pending_items[self.batch_size :]
        self.processed_count += len(batch)
        logger.debug(f"Retrieved batch of {len(batch)} items")
        return batch

    def has_pending(self) -> bool:
        """Check if there are pending items.

        Returns:
            True if there are pending items, False otherwise

        """
        return len(self.pending_items) > 0

    def flush(self) -> list[Any]:
        """Flush remaining items.

        Returns:
            List of remaining items

        """
        batch = self.pending_items
        self.pending_items = []
        self.processed_count += len(batch)
        logger.debug(f"Flushed {len(batch)} items")
        return batch

    def get_stats(self) -> dict[str, Any]:
        """Get batch processor statistics.

        Returns:
            Dictionary with statistics

        """
        return {
            "batch_size": self.batch_size,
            "pending_items": len(self.pending_items),
            "processed_count": self.processed_count,
        }


class ResourcePool:
    """Resource pool for managing reusable resources.

    Attributes:
        available_resources: Pool of available resources
        in_use_resources: Resources currently in use
        max_resources: Maximum resources in pool

    """

    def __init__(self, max_resources: int = 10) -> None:
        """Initialize ResourcePool.

        Args:
            max_resources: Maximum resources in pool

        """
        self.available_resources: list[Any] = []
        self.in_use_resources: list[Any] = []
        self.max_resources = max_resources
        self.resource_id_counter = 0
        logger.debug(f"ResourcePool initialized with max_resources={max_resources}")

    def acquire(self) -> Any:
        """Acquire a resource from the pool.

        Returns:
            Resource from pool or None if pool is exhausted

        """
        if self.available_resources:
            resource = self.available_resources.pop()
            self.in_use_resources.append(resource)
            logger.debug(f"Acquired resource from pool")
            return resource

        if len(self.in_use_resources) < self.max_resources:
            resource_id = self.resource_id_counter
            self.resource_id_counter += 1
            self.in_use_resources.append(resource_id)
            logger.debug(f"Created new resource: {resource_id}")
            return resource_id

        logger.warning("Resource pool exhausted")
        return None

    def release(self, resource: Any) -> None:
        """Release a resource back to the pool.

        Args:
            resource: Resource to release

        """
        if resource in self.in_use_resources:
            self.in_use_resources.remove(resource)
            self.available_resources.append(resource)
            logger.debug(f"Released resource to pool")

    def get_stats(self) -> dict[str, Any]:
        """Get resource pool statistics.

        Returns:
            Dictionary with statistics

        """
        return {
            "available": len(self.available_resources),
            "in_use": len(self.in_use_resources),
            "max_resources": self.max_resources,
            "utilization_percent": (len(self.in_use_resources) / self.max_resources) * 100,
        }
