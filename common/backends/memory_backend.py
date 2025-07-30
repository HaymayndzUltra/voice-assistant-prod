#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Memory Backend Strategy - Phase 3.1

Pluggable backend strategy pattern for memory storage across ServiceRegistry
and other components. Provides abstract interface and multiple implementations
including in-memory, Redis, and file-based backends.

Part of Phase 3.1: Pluggable Backend Strategy - O3 Roadmap Implementation
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union, Iterator
from threading import Lock, RLock
from contextlib import contextmanager

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


@dataclass
class BackendMetrics:
    """Metrics for backend operations."""
    operations: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    total_time: float = 0.0
    started_at: float = field(default_factory=time.time)
    
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0
    
    def avg_response_time(self) -> float:
        """Calculate average response time."""
        return self.total_time / self.operations if self.operations > 0 else 0.0


class MemoryBackend(ABC):
    """Abstract base class for memory backend implementations."""
    
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.logger = logging.getLogger(f"backend.{name}")
        self.metrics = BackendMetrics()
        self._lock = RLock()
        self._connected = False
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the backend storage."""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Disconnect from the backend storage."""
        pass
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set key-value pair with optional TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass
    
    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all data."""
        pass
    
    @abstractmethod
    async def size(self) -> int:
        """Get number of stored items."""
        pass
    
    # Batch operations
    async def mget(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values."""
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result
    
    async def mset(self, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple key-value pairs."""
        success = True
        for key, value in data.items():
            if not await self.set(key, value, ttl):
                success = False
        return success
    
    async def mdelete(self, keys: List[str]) -> int:
        """Delete multiple keys, return count deleted."""
        count = 0
        for key in keys:
            if await self.delete(key):
                count += 1
        return count
    
    # Advanced operations
    async def increment(self, key: str, delta: int = 1) -> Optional[int]:
        """Increment integer value."""
        value = await self.get(key)
        if value is None:
            new_value = delta
        else:
            try:
                new_value = int(value) + delta
            except (ValueError, TypeError):
                return None
        
        if await self.set(key, new_value):
            return new_value
        return None
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key."""
        # Default implementation - get and reset with TTL
        value = await self.get(key)
        if value is not None:
            return await self.set(key, value, ttl)
        return False
    
    # Context manager support
    @contextmanager
    def _metrics_timer(self):
        """Context manager for timing operations."""
        start_time = time.time()
        try:
            yield
            self.metrics.operations += 1
        except Exception as e:
            self.metrics.errors += 1
            raise
        finally:
            self.metrics.total_time += time.time() - start_time
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get backend metrics."""
        uptime = time.time() - self.metrics.started_at
        return {
            "backend_name": self.name,
            "connected": self._connected,
            "uptime_seconds": uptime,
            "operations": self.metrics.operations,
            "cache_hits": self.metrics.cache_hits,
            "cache_misses": self.metrics.cache_misses,
            "errors": self.metrics.errors,
            "hit_rate": self.metrics.hit_rate(),
            "avg_response_time": self.metrics.avg_response_time(),
            "ops_per_second": self.metrics.operations / max(1, uptime)
        }
    
    @property
    def connected(self) -> bool:
        """Check if backend is connected."""
        return self._connected


class InMemoryBackend(MemoryBackend):
    """In-memory backend using Python dictionaries."""
    
    def __init__(self, name: str = "memory", max_size: int = 10000, **kwargs):
        super().__init__(name, **kwargs)
        self.max_size = max_size
        self._data: Dict[str, Any] = {}
        self._ttl: Dict[str, float] = {}  # TTL timestamps
        self._access_times: Dict[str, float] = {}  # For LRU eviction
        
    async def connect(self) -> bool:
        """Connect to in-memory storage."""
        with self._lock:
            self._connected = True
            self.logger.info(f"In-memory backend '{self.name}' connected")
            return True
    
    async def disconnect(self):
        """Disconnect from in-memory storage."""
        with self._lock:
            self._data.clear()
            self._ttl.clear()
            self._access_times.clear()
            self._connected = False
            self.logger.info(f"In-memory backend '{self.name}' disconnected")
    
    def _cleanup_expired(self):
        """Remove expired keys."""
        current_time = time.time()
        expired_keys = [
            key for key, expiry in self._ttl.items()
            if expiry <= current_time
        ]
        
        for key in expired_keys:
            self._data.pop(key, None)
            self._ttl.pop(key, None)
            self._access_times.pop(key, None)
    
    def _evict_lru(self):
        """Evict least recently used items if at capacity."""
        while len(self._data) >= self.max_size:
            # Find LRU key
            lru_key = min(self._access_times, key=self._access_times.get)
            self._data.pop(lru_key, None)
            self._ttl.pop(lru_key, None)
            self._access_times.pop(lru_key, None)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        with self._metrics_timer():
            with self._lock:
                self._cleanup_expired()
                
                if key in self._data:
                    self._access_times[key] = time.time()
                    self.metrics.cache_hits += 1
                    return self._data[key]
                else:
                    self.metrics.cache_misses += 1
                    return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set key-value pair with optional TTL."""
        with self._metrics_timer():
            with self._lock:
                self._cleanup_expired()
                self._evict_lru()
                
                self._data[key] = value
                self._access_times[key] = time.time()
                
                if ttl is not None:
                    self._ttl[key] = time.time() + ttl
                else:
                    self._ttl.pop(key, None)
                
                return True
    
    async def delete(self, key: str) -> bool:
        """Delete key."""
        with self._metrics_timer():
            with self._lock:
                deleted = key in self._data
                self._data.pop(key, None)
                self._ttl.pop(key, None)
                self._access_times.pop(key, None)
                return deleted
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        with self._metrics_timer():
            with self._lock:
                self._cleanup_expired()
                return key in self._data
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        with self._metrics_timer():
            with self._lock:
                self._cleanup_expired()
                
                if pattern == "*":
                    return list(self._data.keys())
                
                # Simple pattern matching
                import fnmatch
                return [key for key in self._data.keys() if fnmatch.fnmatch(key, pattern)]
    
    async def clear(self) -> bool:
        """Clear all data."""
        with self._metrics_timer():
            with self._lock:
                self._data.clear()
                self._ttl.clear()
                self._access_times.clear()
                return True
    
    async def size(self) -> int:
        """Get number of stored items."""
        with self._metrics_timer():
            with self._lock:
                self._cleanup_expired()
                return len(self._data)


class FileBackend(MemoryBackend):
    """File-based backend using JSON storage."""
    
    def __init__(self, name: str = "file", file_path: Optional[Path] = None, 
                 auto_save: bool = True, save_interval: int = 60, **kwargs):
        super().__init__(name, **kwargs)
        self.file_path = file_path or Path(f"backend_{name}.json")
        self.auto_save = auto_save
        self.save_interval = save_interval
        self._data: Dict[str, Any] = {}
        self._ttl: Dict[str, float] = {}
        self._dirty = False
        self._last_save = time.time()
    
    async def connect(self) -> bool:
        """Connect to file backend."""
        with self._lock:
            try:
                if self.file_path.exists():
                    self._load_from_file()
                else:
                    self._data = {}
                    self._ttl = {}
                    
                self._connected = True
                self.logger.info(f"File backend '{self.name}' connected to {self.file_path}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to connect file backend: {e}")
                return False
    
    async def disconnect(self):
        """Disconnect from file backend."""
        with self._lock:
            if self._dirty:
                self._save_to_file()
            self._connected = False
            self.logger.info(f"File backend '{self.name}' disconnected")
    
    def _load_from_file(self):
        """Load data from file."""
        try:
            with open(self.file_path, 'r') as f:
                file_data = json.load(f)
                self._data = file_data.get('data', {})
                self._ttl = file_data.get('ttl', {})
                self.logger.debug(f"Loaded {len(self._data)} items from {self.file_path}")
        except Exception as e:
            self.logger.warning(f"Failed to load from file: {e}")
            self._data = {}
            self._ttl = {}
    
    def _save_to_file(self):
        """Save data to file."""
        try:
            # Create directory if needed
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_data = {
                'data': self._data,
                'ttl': self._ttl,
                'saved_at': time.time()
            }
            
            with open(self.file_path, 'w') as f:
                json.dump(file_data, f, indent=2)
            
            self._dirty = False
            self._last_save = time.time()
            self.logger.debug(f"Saved {len(self._data)} items to {self.file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save to file: {e}")
    
    def _cleanup_expired(self):
        """Remove expired keys."""
        current_time = time.time()
        expired_keys = [
            key for key, expiry in self._ttl.items()
            if expiry <= current_time
        ]
        
        for key in expired_keys:
            self._data.pop(key, None)
            self._ttl.pop(key, None)
            if expired_keys:
                self._dirty = True
    
    def _maybe_save(self):
        """Save to file if auto-save enabled and needed."""
        if (self.auto_save and self._dirty and 
            time.time() - self._last_save > self.save_interval):
            self._save_to_file()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        with self._metrics_timer():
            with self._lock:
                self._cleanup_expired()
                
                if key in self._data:
                    self.metrics.cache_hits += 1
                    return self._data[key]
                else:
                    self.metrics.cache_misses += 1
                    return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set key-value pair with optional TTL."""
        with self._metrics_timer():
            with self._lock:
                self._data[key] = value
                
                if ttl is not None:
                    self._ttl[key] = time.time() + ttl
                else:
                    self._ttl.pop(key, None)
                
                self._dirty = True
                self._maybe_save()
                return True
    
    async def delete(self, key: str) -> bool:
        """Delete key."""
        with self._metrics_timer():
            with self._lock:
                deleted = key in self._data
                self._data.pop(key, None)
                self._ttl.pop(key, None)
                
                if deleted:
                    self._dirty = True
                    self._maybe_save()
                
                return deleted
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        with self._metrics_timer():
            with self._lock:
                self._cleanup_expired()
                return key in self._data
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        with self._metrics_timer():
            with self._lock:
                self._cleanup_expired()
                
                if pattern == "*":
                    return list(self._data.keys())
                
                import fnmatch
                return [key for key in self._data.keys() if fnmatch.fnmatch(key, pattern)]
    
    async def clear(self) -> bool:
        """Clear all data."""
        with self._metrics_timer():
            with self._lock:
                self._data.clear()
                self._ttl.clear()
                self._dirty = True
                self._maybe_save()
                return True
    
    async def size(self) -> int:
        """Get number of stored items."""
        with self._metrics_timer():
            with self._lock:
                self._cleanup_expired()
                return len(self._data)


# Backend factory and management
class BackendFactory:
    """Factory for creating backend instances."""
    
    _backends: Dict[str, type] = {
        "memory": InMemoryBackend,
        "file": FileBackend
    }
    
    @classmethod
    def create_backend(cls, backend_type: str, name: str = None, **kwargs) -> MemoryBackend:
        """Create backend instance."""
        if backend_type not in cls._backends:
            raise ValueError(f"Unknown backend type: {backend_type}")
        
        backend_class = cls._backends[backend_type]
        name = name or f"{backend_type}_backend"
        return backend_class(name=name, **kwargs)
    
    @classmethod
    def register_backend(cls, backend_type: str, backend_class: type):
        """Register custom backend type."""
        cls._backends[backend_type] = backend_class
    
    @classmethod
    def available_backends(cls) -> List[str]:
        """Get list of available backend types."""
        return list(cls._backends.keys())


# Global backend registry
_backend_registry: Dict[str, MemoryBackend] = {}
_registry_lock = Lock()


def get_backend(name: str = "default") -> Optional[MemoryBackend]:
    """Get backend instance from registry."""
    with _registry_lock:
        return _backend_registry.get(name)


def register_backend(name: str, backend: MemoryBackend):
    """Register backend instance."""
    with _registry_lock:
        _backend_registry[name] = backend


def create_and_register_backend(backend_type: str, name: str = "default", **kwargs) -> MemoryBackend:
    """Create and register backend instance."""
    backend = BackendFactory.create_backend(backend_type, name=name, **kwargs)
    register_backend(name, backend)
    return backend


async def cleanup_all_backends():
    """Cleanup all registered backends."""
    with _registry_lock:
        for backend in _backend_registry.values():
            try:
                await backend.disconnect()
            except Exception as e:
                logging.getLogger("backend.cleanup").warning(f"Error cleaning up backend {backend.name}: {e}")
        
        _backend_registry.clear()


# Convenience functions
async def quick_get(key: str, backend_name: str = "default") -> Optional[Any]:
    """Quick get from named backend."""
    backend = get_backend(backend_name)
    if backend:
        return await backend.get(key)
    return None


async def quick_set(key: str, value: Any, backend_name: str = "default", ttl: Optional[int] = None) -> bool:
    """Quick set to named backend."""
    backend = get_backend(backend_name)
    if backend:
        return await backend.set(key, value, ttl)
    return False
