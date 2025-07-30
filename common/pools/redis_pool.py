"""
WP-04 Redis Connection Pool with LRU Caching
High-performance Redis pool with connection reuse and LRU cache implementation
"""

import asyncio
import redis
import redis.asyncio as aioredis
from typing import Optional, Dict, Any, Union, List
import time
import logging
from dataclasses import dataclass
from threading import Lock
import hashlib
import pickle

from common.env_helpers import get_env

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache entry with TTL support"""
    value: Any
    expires_at: float
    access_count: int = 0
    last_accessed: float = 0

class LRUCache:
    """High-performance LRU cache with TTL support"""
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []
        self._lock = Lock()
        
    def _generate_key(self, key: Union[str, bytes, tuple]) -> str:
        """Generate cache key from various input types"""
        if isinstance(key, str):
            return key
        elif isinstance(key, bytes):
            return key.decode('utf-8', errors='ignore')
        else:
            # For complex objects, create hash
            key_str = str(key)
            return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: Union[str, bytes, tuple]) -> Optional[Any]:
        """Get value from cache with LRU tracking"""
        cache_key = self._generate_key(key)
        
        with self._lock:
            entry = self._cache.get(cache_key)
            
            if entry is None:
                return None
            
            # Check TTL
            current_time = time.time()
            if entry.expires_at < current_time:
                self._evict_key(cache_key)
                return None
            
            # Update access tracking
            entry.access_count += 1
            entry.last_accessed = current_time
            
            # Move to end of access order
            if cache_key in self._access_order:
                self._access_order.remove(cache_key)
            self._access_order.append(cache_key)
            
            return entry.value
    
    def set(self, key: Union[str, bytes, tuple], value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        cache_key = self._generate_key(key)
        ttl = ttl or self.default_ttl
        
        with self._lock:
            current_time = time.time()
            expires_at = current_time + ttl
            
            entry = CacheEntry(
                value=value,
                expires_at=expires_at,
                access_count=1,
                last_accessed=current_time
            )
            
            # Add to cache
            self._cache[cache_key] = entry
            
            # Update access order
            if cache_key in self._access_order:
                self._access_order.remove(cache_key)
            self._access_order.append(cache_key)
            
            # Evict if necessary
            self._evict_if_needed()
    
    def delete(self, key: Union[str, bytes, tuple]) -> bool:
        """Delete key from cache"""
        cache_key = self._generate_key(key)
        
        with self._lock:
            if cache_key in self._cache:
                self._evict_key(cache_key)
                return True
            return False
    
    def _evict_key(self, cache_key: str) -> None:
        """Remove key from cache and access order"""
        if cache_key in self._cache:
            del self._cache[cache_key]
        if cache_key in self._access_order:
            self._access_order.remove(cache_key)
    
    def _evict_if_needed(self) -> None:
        """Evict least recently used items if cache is full"""
        while len(self._cache) > self.max_size:
            if self._access_order:
                lru_key = self._access_order.pop(0)
                if lru_key in self._cache:
                    del self._cache[lru_key]
    
    def cleanup_expired(self) -> int:
        """Remove expired entries, return count of removed items"""
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for key, entry in self._cache.items():
                if entry.expires_at < current_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._evict_key(key)
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_access_count = sum(entry.access_count for entry in self._cache.values())
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hit_ratio': 0.0,  # Would need hit/miss tracking for accurate ratio
                'total_accesses': total_access_count,
                'memory_usage_mb': len(pickle.dumps(self._cache)) / (1024 * 1024)
            }

class RedisConnectionPool:
    """High-performance Redis connection pool with async support"""
    
    def __init__(self, 
                 host: Optional[str] = None,
                 port: Optional[int] = None,
                 db: int = 0,
                 max_connections: int = 20,
                 max_connections_per_pool: int = 50,
                 socket_keepalive: bool = True,
                 socket_keepalive_options: Optional[Dict] = None,
                 health_check_interval: int = 30,
                 retry_on_timeout: bool = True,
                 socket_connect_timeout: int = 5,
                 socket_timeout: int = 5):
        
        self.host = host or get_env("REDIS_HOST", "redis")
        self.port = port or int(get_env("REDIS_PORT", "6379"))
        self.db = db
        self.max_connections = max_connections
        self.max_connections_per_pool = max_connections_per_pool
        self.health_check_interval = health_check_interval
        self.retry_on_timeout = retry_on_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.socket_timeout = socket_timeout
        
        # Connection pools
        self._sync_pool: Optional[redis.ConnectionPool] = None
        self._async_pool: Optional[aioredis.ConnectionPool] = None
        
        # Clients
        self._sync_client: Optional[redis.Redis] = None
        self._async_client: Optional[aioredis.Redis] = None
        
        # Health monitoring
        self._last_health_check = 0
        self._is_healthy = False
        
        # LRU Cache
        self.cache = LRUCache(
            max_size=int(get_env("REDIS_CACHE_SIZE", "10000")),
            default_ttl=int(get_env("REDIS_CACHE_TTL", "3600"))
        )
        
        # Connection options
        self.socket_keepalive_options = socket_keepalive_options or {
            'TCP_KEEPIDLE': 1,
            'TCP_KEEPINTVL': 3,
            'TCP_KEEPCNT': 5
        }
        
        # Initialize pools
        self._initialize_pools()
        
        logger.info(f"RedisConnectionPool initialized - {self.host}:{self.port}/{self.db}")
    
    def _initialize_pools(self):
        """Initialize Redis connection pools"""
        try:
            # Sync pool
            self._sync_pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                max_connections=self.max_connections_per_pool,
                socket_keepalive=True,
                socket_keepalive_options=self.socket_keepalive_options,
                socket_connect_timeout=self.socket_connect_timeout,
                socket_timeout=self.socket_timeout,
                retry_on_timeout=self.retry_on_timeout,
                health_check_interval=self.health_check_interval
            )
            
            # Async pool  
            self._async_pool = aioredis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                max_connections=self.max_connections_per_pool,
                socket_keepalive=True,
                socket_keepalive_options=self.socket_keepalive_options,
                socket_connect_timeout=self.socket_connect_timeout,
                socket_timeout=self.socket_timeout,
                retry_on_timeout=self.retry_on_timeout,
                health_check_interval=self.health_check_interval
            )
            
            # Create clients
            self._sync_client = redis.Redis(connection_pool=self._sync_pool)
            self._async_client = aioredis.Redis(connection_pool=self._async_pool)
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis pools: {e}")
            raise
    
    def get_sync_client(self) -> redis.Redis:
        """Get synchronous Redis client"""
        if not self._sync_client:
            self._initialize_pools()
        if not self._sync_client:
            raise RuntimeError("Failed to initialize Redis sync client")
        return self._sync_client
    
    def get_async_client(self) -> aioredis.Redis:
        """Get asynchronous Redis client"""
        if not self._async_client:
            self._initialize_pools()
        if not self._async_client:
            raise RuntimeError("Failed to initialize Redis async client")
        return self._async_client
    
    async def health_check(self) -> bool:
        """Check Redis connection health"""
        current_time = time.time()
        
        # Only check if enough time has passed
        if current_time - self._last_health_check < self.health_check_interval:
            return self._is_healthy
        
        try:
            client = self.get_async_client()
            await client.ping()
            self._is_healthy = True
            self._last_health_check = current_time
            return True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            self._is_healthy = False
            return False
    
    async def get_cached(self, key: str, fetch_func=None, ttl: Optional[int] = None) -> Any:
        """Get value with cache-aside pattern"""
        # Check local cache first
        cached_value = self.cache.get(key)
        if cached_value is not None:
            return cached_value
        
        # Check Redis
        try:
            client = self.get_async_client()
            redis_value = await client.get(key)
            
            if redis_value is not None:
                try:
                    value = pickle.loads(redis_value)
                    self.cache.set(key, value, ttl)
                    return value
                except (pickle.PickleError, TypeError):
                    # Fallback to string value
                    self.cache.set(key, redis_value.decode(), ttl)
                    return redis_value.decode()
        except Exception as e:
            logger.warning(f"Redis get failed for key {key}: {e}")
        
        # Fetch from source if provided
        if fetch_func:
            try:
                if asyncio.iscoroutinefunction(fetch_func):
                    value = await fetch_func()
                else:
                    value = fetch_func()
                
                # Cache the fetched value
                await self.set_cached(key, value, ttl)
                return value
            except Exception as e:
                logger.error(f"Fetch function failed for key {key}: {e}")
                return None
        
        return None
    
    async def set_cached(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in both local cache and Redis"""
        ttl = ttl or self.cache.default_ttl
        
        # Set in local cache
        self.cache.set(key, value, ttl)
        
        # Set in Redis
        try:
            client = self.get_async_client()
            serialized_value = pickle.dumps(value)
            await client.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.warning(f"Redis set failed for key {key}: {e}")
            return False
    
    async def delete_cached(self, key: str) -> bool:
        """Delete from both local cache and Redis"""
        # Delete from local cache
        local_deleted = self.cache.delete(key)
        
        # Delete from Redis
        try:
            client = self.get_async_client()
            redis_deleted = await client.delete(key)
            return local_deleted or bool(redis_deleted)
        except Exception as e:
            logger.warning(f"Redis delete failed for key {key}: {e}")
            return local_deleted
    
    def cleanup_expired_cache(self) -> int:
        """Clean up expired cache entries"""
        return self.cache.cleanup_expired()
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        stats = {
            'cache_stats': self.cache.get_stats(),
            'is_healthy': self._is_healthy,
            'last_health_check': self._last_health_check,
            'config': {
                'host': self.host,
                'port': self.port,
                'db': self.db,
                'max_connections': self.max_connections_per_pool
            }
        }
        
        # Add pool-specific stats if available
        if self._sync_pool:
            try:
                stats['sync_pool'] = {
                    'max_connections': self._sync_pool.max_connections,
                    'connection_kwargs': str(self._sync_pool.connection_kwargs)
                }
            except AttributeError:
                stats['sync_pool'] = {'status': 'pool_active'}
        
        return stats
    
    def close(self):
        """Close all connections"""
        try:
            if self._sync_pool:
                self._sync_pool.disconnect()
            if self._async_pool:
                # Note: async pool closing would need to be awaited
                pass
        except Exception as e:
            logger.error(f"Error closing Redis pools: {e}")


# Global Redis pool instance
_redis_pool: Optional[RedisConnectionPool] = None

def get_redis_pool() -> RedisConnectionPool:
    """Get global Redis connection pool"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = RedisConnectionPool()
    return _redis_pool

async def get_redis_client() -> aioredis.Redis:
    """Get async Redis client from pool"""
    pool = get_redis_pool()
    return pool.get_async_client()

def get_redis_client_sync() -> redis.Redis:
    """Get sync Redis client from pool"""
    pool = get_redis_pool()
    return pool.get_sync_client() 