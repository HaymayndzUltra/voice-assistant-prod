"""
Redis cache adapter implementation for Memory Fusion Hub.

This module provides:
- RedisCache: TTL-aware cache with lazy connection
- Connection pooling and error handling
- JSON serialization for Pydantic models
- Async/await interface
"""

import json
import logging
from typing import Optional, Any, Dict
from datetime import datetime, timedelta

import redis.asyncio as aioredis
from pydantic import BaseModel

from ..core.models import MemoryItem, SessionData, KnowledgeRecord, MemoryEvent

logger = logging.getLogger(__name__)


class CacheException(Exception):
    """Base exception for cache operations."""
    pass


class RedisCache:
    """
    TTL-aware Redis cache with lazy connection logic.
    
    Provides async caching operations with automatic TTL management,
    JSON serialization for Pydantic models, and connection pooling.
    """
    
    def __init__(self, redis_url: str, default_ttl_seconds: int = 900):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379/0)
            default_ttl_seconds: Default TTL for cached items (15 minutes)
        """
        self.redis_url = redis_url
        self.default_ttl_seconds = default_ttl_seconds
        self.client: Optional[aioredis.Redis] = None
        self._connection_pool = None
        
    async def _ensure_connection(self) -> None:
        """Ensure Redis connection is established (lazy initialization)."""
        if self.client is None:
            try:
                # Create connection pool for better performance
                self._connection_pool = aioredis.ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=20,
                    retry_on_timeout=True,
                    socket_keepalive=True,
                    socket_keepalive_options={},
                    health_check_interval=30
                )
                
                self.client = aioredis.Redis(
                    connection_pool=self._connection_pool,
                    decode_responses=True,
                    encoding='utf-8'
                )
                
                # Test connection
                await self.client.ping()
                logger.info(f"Redis cache connected: {self.redis_url}")
                
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise CacheException(f"Redis connection failed: {e}")
    
    async def get(self, key: str) -> Optional[BaseModel]:
        """
        Retrieve a cached object by key.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Cached Pydantic model object or None if not found
        """
        try:
            await self._ensure_connection()
            
            # Get the cached data
            cached_data = await self.client.get(key)
            if cached_data is None:
                logger.debug(f"Cache miss: {key}")
                return None
            
            # Deserialize the JSON data
            data_dict = json.loads(cached_data)
            
            # Determine the model type and reconstruct object
            model_type = data_dict.get('__model_type__')
            if not model_type:
                logger.warning(f"Cached data missing model type: {key}")
                return None
            
            # Remove the model type from data before reconstruction
            model_data = {k: v for k, v in data_dict.items() if k != '__model_type__'}
            
            # Reconstruct the appropriate Pydantic model
            if model_type == 'MemoryItem':
                return MemoryItem(**model_data)
            elif model_type == 'SessionData':
                return SessionData(**model_data)
            elif model_type == 'KnowledgeRecord':
                return KnowledgeRecord(**model_data)
            elif model_type == 'MemoryEvent':
                return MemoryEvent(**model_data)
            else:
                logger.warning(f"Unknown model type in cache: {model_type}")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for cached key {key}: {e}")
            # Remove corrupted cache entry
            await self.evict(key)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def put(self, key: str, value: BaseModel, ttl_seconds: Optional[int] = None) -> None:
        """
        Cache a Pydantic model object with TTL.
        
        Args:
            key: Cache key to store under
            value: Pydantic model object to cache
            ttl_seconds: TTL in seconds (uses default if None)
        """
        try:
            await self._ensure_connection()
            
            if ttl_seconds is None:
                ttl_seconds = self.default_ttl_seconds
            
            # Add model type information for deserialization
            data_dict = value.dict()
            data_dict['__model_type__'] = value.__class__.__name__
            
            # Serialize to JSON
            cached_data = json.dumps(data_dict, default=self._json_serializer)
            
            # Store with TTL
            await self.client.setex(key, ttl_seconds, cached_data)
            logger.debug(f"Cached object: {key} (TTL: {ttl_seconds}s)")
            
        except Exception as e:
            logger.error(f"Cache put error for key {key}: {e}")
            raise CacheException(f"Failed to cache key {key}: {e}")
    
    async def evict(self, key: str) -> bool:
        """
        Remove a cached object.
        
        Args:
            key: Cache key to remove
            
        Returns:
            True if key was removed, False if key didn't exist
        """
        try:
            await self._ensure_connection()
            
            result = await self.client.delete(key)
            if result > 0:
                logger.debug(f"Evicted from cache: {key}")
                return True
            else:
                logger.debug(f"Cache key not found for eviction: {key}")
                return False
                
        except Exception as e:
            logger.error(f"Cache evict error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            await self._ensure_connection()
            
            result = await self.client.exists(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Cache exists check error for key {key}: {e}")
            return False
    
    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get the remaining TTL for a cached key.
        
        Args:
            key: Cache key to check
            
        Returns:
            Remaining TTL in seconds, None if key doesn't exist
        """
        try:
            await self._ensure_connection()
            
            ttl = await self.client.ttl(key)
            if ttl == -2:  # Key doesn't exist
                return None
            elif ttl == -1:  # Key exists but has no TTL
                return -1
            else:
                return ttl
                
        except Exception as e:
            logger.error(f"Cache TTL check error for key {key}: {e}")
            return None
    
    async def set_ttl(self, key: str, ttl_seconds: int) -> bool:
        """
        Update the TTL for an existing cached key.
        
        Args:
            key: Cache key to update
            ttl_seconds: New TTL in seconds
            
        Returns:
            True if TTL was updated, False if key doesn't exist
        """
        try:
            await self._ensure_connection()
            
            result = await self.client.expire(key, ttl_seconds)
            if result:
                logger.debug(f"Updated TTL for {key}: {ttl_seconds}s")
                return True
            else:
                logger.debug(f"Key not found for TTL update: {key}")
                return False
                
        except Exception as e:
            logger.error(f"Cache TTL update error for key {key}: {e}")
            return False
    
    async def clear_all(self) -> int:
        """
        Clear all cached data (use with caution).
        
        Returns:
            Number of keys that were removed
        """
        try:
            await self._ensure_connection()
            
            # Get all keys in the current database
            keys = await self.client.keys('*')
            if not keys:
                return 0
            
            # Delete all keys
            result = await self.client.delete(*keys)
            logger.warning(f"Cleared all cache data: {result} keys removed")
            return result
            
        except Exception as e:
            logger.error(f"Cache clear all error: {e}")
            return 0
    
    async def get_cache_info(self) -> Dict[str, Any]:
        """
        Get cache statistics and information.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            await self._ensure_connection()
            
            info = await self.client.info()
            keyspace_info = await self.client.info('keyspace')
            
            # Extract relevant statistics
            stats = {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', 'N/A'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'instantaneous_ops_per_sec': info.get('instantaneous_ops_per_sec', 0),
            }
            
            # Calculate hit rate
            hits = stats['keyspace_hits']
            misses = stats['keyspace_misses']
            total_requests = hits + misses
            
            if total_requests > 0:
                stats['hit_rate'] = hits / total_requests
            else:
                stats['hit_rate'] = 0.0
            
            # Add keyspace information
            if keyspace_info:
                for db_key, db_info in keyspace_info.items():
                    if db_key.startswith('db'):
                        stats[f'{db_key}_keys'] = db_info.get('keys', 0)
                        stats[f'{db_key}_expires'] = db_info.get('expires', 0)
            
            return stats
            
        except Exception as e:
            logger.error(f"Cache info error: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """
        Perform a health check on the Redis connection.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            await self._ensure_connection()
            
            # Test basic operations
            test_key = f"__health_check__{datetime.now().timestamp()}"
            
            # Test SET
            await self.client.set(test_key, "health_check", ex=5)
            
            # Test GET
            result = await self.client.get(test_key)
            
            # Test DELETE
            await self.client.delete(test_key)
            
            # Verify the operation worked
            is_healthy = (result == "health_check")
            
            if is_healthy:
                logger.debug("Redis cache health check passed")
            else:
                logger.warning("Redis cache health check failed")
            
            return is_healthy
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    async def close(self) -> None:
        """Close the Redis connection and clean up resources."""
        try:
            if self.client:
                await self.client.close()
                self.client = None
                
            if self._connection_pool:
                await self._connection_pool.disconnect()
                self._connection_pool = None
                
            logger.info("Redis cache connection closed")
            
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    # Context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_connection()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()