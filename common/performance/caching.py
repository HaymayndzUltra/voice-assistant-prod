"""
WP-08 Advanced Caching System
Multi-layer caching with TTL, LRU, and distributed caching for performance optimization
"""

import asyncio
import time
import threading
import hashlib
import pickle
import json
from typing import Dict, Any, Optional, Callable, List, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CacheBackend(Enum):
    """Available cache backends"""
    MEMORY = "memory"
    REDIS = "redis" 
    FILE = "file"
    HYBRID = "hybrid"

class EvictionPolicy(Enum):
    """Cache eviction policies"""
    LRU = "lru"         # Least Recently Used
    LFU = "lfu"         # Least Frequently Used
    TTL = "ttl"         # Time To Live
    FIFO = "fifo"       # First In First Out

@dataclass
class CacheConfig:
    """Configuration for cache instances"""
    backend: CacheBackend = CacheBackend.MEMORY
    max_size: int = 1000
    default_ttl: float = 3600.0  # 1 hour
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    compression: bool = False
    serializer: str = "pickle"  # pickle, json, msgpack
    namespace: str = "default"

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    value: Any
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: Optional[float] = None
    size: Optional[int] = None
    
    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if self.ttl is None:
            return False
        return time.time() > (self.created_at + self.ttl)
    
    def touch(self):
        """Update access time and count"""
        self.accessed_at = time.time()
        self.access_count += 1

class CacheBackendInterface(ABC):
    """Abstract interface for cache backends"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[CacheEntry]:
        pass
    
    @abstractmethod
    async def set(self, key: str, entry: CacheEntry) -> bool:
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        pass
    
    @abstractmethod
    async def keys(self) -> List[str]:
        pass
    
    @abstractmethod
    async def size(self) -> int:
        pass

class MemoryCacheBackend(CacheBackendInterface):
    """In-memory cache backend"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        
    async def get(self, key: str) -> Optional[CacheEntry]:
        with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired():
                entry.touch()
                return entry
            elif entry and entry.is_expired():
                del self._cache[key]
            return None
    
    async def set(self, key: str, entry: CacheEntry) -> bool:
        with self._lock:
            # Check size limits and evict if necessary
            if len(self._cache) >= self.config.max_size:
                await self._evict()
            
            self._cache[key] = entry
            return True
    
    async def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self) -> bool:
        with self._lock:
            self._cache.clear()
            return True
    
    async def keys(self) -> List[str]:
        with self._lock:
            return list(self._cache.keys())
    
    async def size(self) -> int:
        with self._lock:
            return len(self._cache)
    
    async def _evict(self):
        """Evict entries based on policy"""
        if not self._cache:
            return
        
        if self.config.eviction_policy == EvictionPolicy.LRU:
            # Remove least recently used
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].accessed_at)
            del self._cache[oldest_key]
        
        elif self.config.eviction_policy == EvictionPolicy.LFU:
            # Remove least frequently used
            least_used_key = min(self._cache.keys(), key=lambda k: self._cache[k].access_count)
            del self._cache[least_used_key]
        
        elif self.config.eviction_policy == EvictionPolicy.TTL:
            # Remove expired entries first
            expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
            if expired_keys:
                for key in expired_keys:
                    del self._cache[key]
            else:
                # Fallback to LRU if no expired entries
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].accessed_at)
                del self._cache[oldest_key]
        
        elif self.config.eviction_policy == EvictionPolicy.FIFO:
            # Remove oldest entry
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
            del self._cache[oldest_key]

class RedisCacheBackend(CacheBackendInterface):
    """Redis cache backend"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self._redis = None
        self._initialized = False
    
    async def _ensure_connection(self):
        """Ensure Redis connection is established"""
        if not self._initialized:
            try:
                from common.pools.redis_pool import get_redis_pool
                pool = get_redis_pool()
                self._redis = pool  # Use pool directly
                self._initialized = True
            except ImportError:
                logger.warning("Redis pool not available, falling back to direct connection")
                try:
                    import redis.asyncio as redis
                    self._redis = redis.Redis(decode_responses=True)
                    self._initialized = True
                except ImportError:
                    logger.error("Redis not available")
                    self._redis = None
    
    def _make_key(self, key: str) -> str:
        """Create namespaced key"""
        return f"{self.config.namespace}:{key}"
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        await self._ensure_connection()
        
        if self._redis is None:
            return None
        
        try:
            # Try to use Redis pool if available
            if hasattr(self._redis, 'execute'):
                data = await self._redis.execute('get', self._make_key(key))
            else:
                data = await self._redis.get(self._make_key(key))
            
            if data:
                entry = pickle.loads(data.encode('latin1'))
                if not entry.is_expired():
                    entry.touch()
                    # Update access info in Redis
                    serialized = pickle.dumps(entry).decode('latin1')
                    if hasattr(self._redis, 'execute'):
                        await self._redis.execute('set', self._make_key(key), serialized, 'EX', int(entry.ttl) if entry.ttl else 3600)
                    else:
                        await self._redis.set(
                            self._make_key(key), 
                            serialized,
                            ex=int(entry.ttl) if entry.ttl else None
                        )
                    return entry
                else:
                    await self.delete(key)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set(self, key: str, entry: CacheEntry) -> bool:
        await self._ensure_connection()
        
        try:
            data = pickle.dumps(entry).decode('latin1')
            await self._redis.set(
                self._make_key(key),
                data,
                ex=int(entry.ttl) if entry.ttl else None
            )
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        await self._ensure_connection()
        
        try:
            result = await self._redis.delete(self._make_key(key))
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def clear(self) -> bool:
        await self._ensure_connection()
        
        try:
            pattern = f"{self.config.namespace}:*"
            keys = await self._redis.keys(pattern)
            if keys:
                await self._redis.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return False
    
    async def keys(self) -> List[str]:
        await self._ensure_connection()
        
        try:
            pattern = f"{self.config.namespace}:*"
            redis_keys = await self._redis.keys(pattern)
            # Remove namespace prefix
            prefix_len = len(self.config.namespace) + 1
            return [key[prefix_len:] for key in redis_keys]
        except Exception as e:
            logger.error(f"Redis keys error: {e}")
            return []
    
    async def size(self) -> int:
        keys_list = await self.keys()
        return len(keys_list)

class Cache(Generic[T]):
    """High-performance cache with multiple backends and policies"""
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self._backend = self._create_backend()
        
        # Metrics
        self._metrics = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0,
            'total_requests': 0
        }
        
        logger.info(f"Cache initialized with {self.config.backend.value} backend")
    
    def _create_backend(self) -> CacheBackendInterface:
        """Create appropriate cache backend"""
        if self.config.backend == CacheBackend.MEMORY:
            return MemoryCacheBackend(self.config)
        elif self.config.backend == CacheBackend.REDIS:
            return RedisCacheBackend(self.config)
        else:
            # Default to memory
            return MemoryCacheBackend(self.config)
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items()) if kwargs else None
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[T]:
        """Get value from cache"""
        self._metrics['total_requests'] += 1
        
        entry = await self._backend.get(key)
        if entry:
            self._metrics['hits'] += 1
            return entry.value
        else:
            self._metrics['misses'] += 1
            return None
    
    async def set(self, key: str, value: T, ttl: Optional[float] = None) -> bool:
        """Set value in cache"""
        entry = CacheEntry(
            value=value,
            ttl=ttl or self.config.default_ttl
        )
        
        success = await self._backend.set(key, entry)
        if success:
            self._metrics['sets'] += 1
        
        return success
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        success = await self._backend.delete(key)
        if success:
            self._metrics['deletes'] += 1
        
        return success
    
    async def clear(self) -> bool:
        """Clear all cache entries"""
        return await self._backend.clear()
    
    async def keys(self) -> List[str]:
        """Get all cache keys"""
        return await self._backend.keys()
    
    async def size(self) -> int:
        """Get cache size"""
        return await self._backend.size()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics"""
        total = self._metrics['hits'] + self._metrics['misses']
        hit_rate = self._metrics['hits'] / total if total > 0 else 0
        
        return {
            **self._metrics,
            'hit_rate': hit_rate,
            'miss_rate': 1 - hit_rate,
            'backend': self.config.backend.value,
            'eviction_policy': self.config.eviction_policy.value
        }

class CacheManager:
    """Manages multiple cache instances"""
    
    def __init__(self):
        self._caches: Dict[str, Cache] = {}
        self._default_config = CacheConfig()
    
    def get_cache(self, name: str, config: CacheConfig = None) -> Cache:
        """Get or create named cache"""
        if name not in self._caches:
            cache_config = config or self._default_config
            self._caches[name] = Cache(cache_config)
            logger.info(f"Created cache: {name}")
        
        return self._caches[name]
    
    def list_caches(self) -> List[str]:
        """List all cache names"""
        return list(self._caches.keys())
    
    async def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all caches"""
        metrics = {}
        for name, cache in self._caches.items():
            metrics[name] = cache.get_metrics()
        return metrics
    
    async def clear_all(self):
        """Clear all caches"""
        for cache in self._caches.values():
            await cache.clear()

# Global cache manager
_cache_manager: Optional[CacheManager] = None

def get_cache_manager() -> CacheManager:
    """Get global cache manager"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager

def get_cache(name: str = "default", config: CacheConfig = None) -> Cache:
    """Get named cache instance"""
    manager = get_cache_manager()
    return manager.get_cache(name, config)

# Decorators for easy caching
def cached(cache_name: str = "default", 
          ttl: Optional[float] = None,
          key_func: Optional[Callable] = None):
    """Decorator for caching function results"""
    
    def decorator(func):
        cache = get_cache(cache_name)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache._generate_key(func.__name__, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to handle this differently
            # This is a simplified version - consider using asyncio.run in real scenarios
            cache._generate_key(func.__name__, *args, **kwargs) if not key_func else key_func(*args, **kwargs)
            
            # Execute function (cache operations would need async context)
            result = func(*args, **kwargs)
            
            # Note: Sync caching requires running in async context
            # This is a limitation that should be documented
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def cache_invalidate(cache_name: str = "default", pattern: str = None):
    """Decorator for cache invalidation"""
    
    def decorator(func):
        cache = get_cache(cache_name)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Invalidate cache
            if pattern:
                # Pattern-based invalidation (simplified)
                keys = await cache.keys()
                for key in keys:
                    if pattern in key:
                        await cache.delete(key)
            else:
                # Clear entire cache
                await cache.clear()
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            # Note: Sync invalidation needs async context
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Specialized cache types
class ModelCache(Cache):
    """Specialized cache for ML models"""
    
    def __init__(self):
        config = CacheConfig(
            backend=CacheBackend.MEMORY,
            max_size=10,  # Models are large
            default_ttl=86400.0,  # 24 hours
            eviction_policy=EvictionPolicy.LRU
        )
        super().__init__(config)

class ResponseCache(Cache):
    """Specialized cache for API responses"""
    
    def __init__(self):
        config = CacheConfig(
            backend=CacheBackend.REDIS,
            max_size=10000,
            default_ttl=300.0,  # 5 minutes
            eviction_policy=EvictionPolicy.TTL
        )
        super().__init__(config)

class ComputationCache(Cache):
    """Specialized cache for expensive computations"""
    
    def __init__(self):
        config = CacheConfig(
            backend=CacheBackend.HYBRID,
            max_size=1000,
            default_ttl=3600.0,  # 1 hour
            eviction_policy=EvictionPolicy.LFU
        )
        super().__init__(config)

# Convenience functions
async def cache_computation(key: str, computation_func: Callable, *args, **kwargs):
    """Cache expensive computation"""
    cache = get_cache("computation")
    
    result = await cache.get(key)
    if result is not None:
        return result
    
    result = await computation_func(*args, **kwargs)
    await cache.set(key, result)
    
    return result

async def warm_cache(cache_name: str, data: Dict[str, Any]):
    """Warm up cache with predefined data"""
    cache = get_cache(cache_name)
    
    for key, value in data.items():
        await cache.set(key, value)
    
    logger.info(f"Warmed cache '{cache_name}' with {len(data)} entries") 