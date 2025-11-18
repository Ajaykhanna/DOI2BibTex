"""
Advanced caching system for DOI2BibTex application.

This module provides a professional caching layer with multiple backends:
- MemoryCache: In-memory LRU cache with TTL support
- FileCache: Persistent file-based cache
- CacheManager: Unified interface supporting multiple cache backends

Features:
- TTL (time-to-live) for automatic expiration
- LRU (least recently used) eviction policy
- Persistent storage across sessions
- Thread-safe operations
- Type-safe protocol interface
"""

from __future__ import annotations

import time
import pickle
import hashlib
import threading
from pathlib import Path
from typing import Any, Protocol, Optional
from collections import OrderedDict
from datetime import datetime, timedelta
import logging


# Configure logger
logger = logging.getLogger(__name__)


class CacheProtocol(Protocol):
    """
    Protocol defining the cache interface.

    All cache implementations must support these methods for consistency.
    """

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        ...

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = no expiration)
        """
        ...

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        ...

    def clear(self) -> None:
        """Clear all cache entries."""
        ...

    def exists(self, key: str) -> bool:
        """
        Check if key exists and is not expired.

        Args:
            key: Cache key

        Returns:
            True if key exists and is valid
        """
        ...


class MemoryCache:
    """
    In-memory LRU cache with TTL support.

    Features:
    - Thread-safe operations
    - Automatic expiration based on TTL
    - LRU eviction when maxsize is reached
    - O(1) get/set operations

    Example:
        >>> cache = MemoryCache(maxsize=100, default_ttl=3600)
        >>> cache.set("doi:10.1234/test", bibtex_data)
        >>> data = cache.get("doi:10.1234/test")
    """

    def __init__(self, maxsize: int = 1000, default_ttl: int = 3600):
        """
        Initialize memory cache.

        Args:
            maxsize: Maximum number of items to store
            default_ttl: Default TTL in seconds (3600 = 1 hour)
        """
        self.maxsize = maxsize
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache if not expired."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            value, expiry = self._cache[key]

            # Check expiration
            if expiry > 0 and time.time() > expiry:
                # Expired - remove it
                del self._cache[key]
                self._misses += 1
                logger.debug(f"Cache MISS (expired): {key}")
                return None

            # Move to end (mark as recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            logger.debug(f"Cache HIT: {key}")
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store value in cache with optional TTL."""
        with self._lock:
            # Calculate expiry time
            if ttl is None:
                ttl = self.default_ttl

            expiry = time.time() + ttl if ttl > 0 else 0  # 0 = never expires

            # Add/update entry
            self._cache[key] = (value, expiry)
            self._cache.move_to_end(key)  # Mark as most recently used

            # Enforce maxsize with LRU eviction
            if len(self._cache) > self.maxsize:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                logger.debug(f"LRU evicted: {oldest_key}")

            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache DELETE: {key}")
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            logger.info(f"Cache cleared: {count} entries removed")

    def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        return self.get(key) is not None

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "size": len(self._cache),
                "maxsize": self.maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.1f}%",
                "utilization": f"{len(self._cache) / self.maxsize * 100:.1f}%"
            }


class FileCache:
    """
    Persistent file-based cache using pickle serialization.

    Features:
    - Survives application restarts
    - Thread-safe file operations
    - Automatic directory creation
    - TTL support with metadata

    Example:
        >>> cache = FileCache(cache_dir=Path(".cache"))
        >>> cache.set("crossref:10.1234/test", metadata, ttl=86400)
        >>> data = cache.get("crossref:10.1234/test")
    """

    def __init__(self, cache_dir: Path = Path(".cache"), default_ttl: int = 86400):
        """
        Initialize file cache.

        Args:
            cache_dir: Directory to store cache files
            default_ttl: Default TTL in seconds (86400 = 24 hours)
        """
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        self._lock = threading.Lock()

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"FileCache initialized: {self.cache_dir}")

    def _get_cache_path(self, key: str) -> Path:
        """Generate filesystem path for cache key."""
        # Hash key to create safe filename
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from file cache if not expired."""
        cache_path = self._get_cache_path(key)

        with self._lock:
            if not cache_path.exists():
                logger.debug(f"File cache MISS: {key}")
                return None

            try:
                with open(cache_path, 'rb') as f:
                    data = pickle.load(f)

                value, expiry = data['value'], data['expiry']

                # Check expiration
                if expiry > 0 and time.time() > expiry:
                    # Expired - remove file
                    cache_path.unlink()
                    logger.debug(f"File cache MISS (expired): {key}")
                    return None

                logger.debug(f"File cache HIT: {key}")
                return value

            except Exception as e:
                logger.warning(f"File cache read error for {key}: {e}")
                # Corrupted cache file - remove it
                if cache_path.exists():
                    cache_path.unlink()
                return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store value in file cache with optional TTL."""
        cache_path = self._get_cache_path(key)

        if ttl is None:
            ttl = self.default_ttl

        expiry = time.time() + ttl if ttl > 0 else 0

        data = {
            'value': value,
            'expiry': expiry,
            'created': time.time(),
            'key': key  # Store original key for debugging
        }

        with self._lock:
            try:
                with open(cache_path, 'wb') as f:
                    pickle.dump(data, f)
                logger.debug(f"File cache SET: {key} (TTL: {ttl}s)")
            except Exception as e:
                logger.error(f"File cache write error for {key}: {e}")

    def delete(self, key: str) -> bool:
        """Delete key from file cache."""
        cache_path = self._get_cache_path(key)

        with self._lock:
            if cache_path.exists():
                cache_path.unlink()
                logger.debug(f"File cache DELETE: {key}")
                return True
            return False

    def clear(self) -> None:
        """Clear all cache files."""
        with self._lock:
            count = 0
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()
                count += 1
            logger.info(f"File cache cleared: {count} files removed")

    def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        return self.get(key) is not None

    def cleanup_expired(self) -> int:
        """
        Remove all expired cache files.

        Returns:
            Number of files removed
        """
        with self._lock:
            removed = 0
            current_time = time.time()

            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    with open(cache_file, 'rb') as f:
                        data = pickle.load(f)

                    expiry = data['expiry']
                    if expiry > 0 and current_time > expiry:
                        cache_file.unlink()
                        removed += 1
                except Exception:
                    # Corrupted file - remove it
                    cache_file.unlink()
                    removed += 1

            if removed > 0:
                logger.info(f"Cleaned up {removed} expired cache files")

            return removed


class CacheManager:
    """
    Unified cache manager supporting multiple backends.

    Implements a two-tier caching strategy:
    1. Memory cache (fast, L1)
    2. File cache (persistent, L2)

    Features:
    - Automatic fallback from memory to file cache
    - Write-through to both caches
    - Configurable cache layers
    - Unified statistics

    Example:
        >>> cache = CacheManager(memory=True, file=True)
        >>> cache.set("doi:10.1234/test", data, ttl=3600)
        >>> data = cache.get("doi:10.1234/test")  # Checks memory first, then file
    """

    def __init__(
        self,
        memory: bool = True,
        file: bool = True,
        memory_maxsize: int = 1000,
        memory_ttl: int = 3600,
        file_dir: Path = Path(".cache"),
        file_ttl: int = 86400
    ):
        """
        Initialize cache manager.

        Args:
            memory: Enable in-memory cache
            file: Enable file-based cache
            memory_maxsize: Max items in memory cache
            memory_ttl: Default TTL for memory cache (seconds)
            file_dir: Directory for file cache
            file_ttl: Default TTL for file cache (seconds)
        """
        self.memory_cache: Optional[MemoryCache] = (
            MemoryCache(maxsize=memory_maxsize, default_ttl=memory_ttl) if memory else None
        )
        self.file_cache: Optional[FileCache] = (
            FileCache(cache_dir=file_dir, default_ttl=file_ttl) if file else None
        )

        logger.info(
            f"CacheManager initialized: "
            f"memory={memory}, file={file}"
        )

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache (checks memory first, then file).

        If found in file cache but not memory, promotes to memory cache.
        """
        # Try memory cache first (L1)
        if self.memory_cache:
            value = self.memory_cache.get(key)
            if value is not None:
                return value

        # Try file cache (L2)
        if self.file_cache:
            value = self.file_cache.get(key)
            if value is not None:
                # Promote to memory cache
                if self.memory_cache:
                    self.memory_cache.set(key, value)
                    logger.debug(f"Promoted to memory cache: {key}")
                return value

        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store value in cache (write-through to both layers).

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = use default)
        """
        # Write to memory cache (L1)
        if self.memory_cache:
            self.memory_cache.set(key, value, ttl)

        # Write to file cache (L2)
        if self.file_cache:
            self.file_cache.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """Delete key from all cache layers."""
        deleted = False

        if self.memory_cache:
            deleted = self.memory_cache.delete(key) or deleted

        if self.file_cache:
            deleted = self.file_cache.delete(key) or deleted

        return deleted

    def clear(self) -> None:
        """Clear all cache layers."""
        if self.memory_cache:
            self.memory_cache.clear()

        if self.file_cache:
            self.file_cache.clear()

    def exists(self, key: str) -> bool:
        """Check if key exists in any cache layer."""
        if self.memory_cache and self.memory_cache.exists(key):
            return True

        if self.file_cache and self.file_cache.exists(key):
            return True

        return False

    def stats(self) -> dict[str, Any]:
        """Get statistics from all cache layers."""
        stats = {}

        if self.memory_cache:
            stats["memory"] = self.memory_cache.stats()

        if self.file_cache:
            # Count files
            cache_files = list(self.file_cache.cache_dir.glob("*.cache"))
            stats["file"] = {
                "cached_files": len(cache_files),
                "cache_dir": str(self.file_cache.cache_dir)
            }

        return stats

    def cleanup(self) -> None:
        """Cleanup expired entries from file cache."""
        if self.file_cache:
            removed = self.file_cache.cleanup_expired()
            logger.info(f"Cache cleanup: {removed} expired files removed")
