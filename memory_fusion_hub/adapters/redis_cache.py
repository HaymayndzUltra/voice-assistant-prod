"""
Redis cache adapter for Memory Fusion Hub.

This module provides TTL-aware caching functionality using Redis as the cache
backend. It supports automatic expiration, cache statistics, and efficient
serialization of Pydantic models.
"""
import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta

import redis.asyncio as redis
from pydantic import BaseModel

from ..core.models import MemoryItem, SessionData, KnowledgeRecord, MemoryEvent


logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis-based cache with TTL support for Memory Fusion Hub.
    
    Provides efficient caching of Pydantic models with automatic expiration,
    cache statistics, and memory management features.
    """

    def __init__(self, redis_url: str, default_ttl_seconds: int = 900):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL (e.g., "redis://localhost:6379/0")
            default_ttl_seconds: Default time-to-live for cached items in seconds
        """
        self.redis_url = redis_url
        self.default_ttl_seconds = default_ttl_seconds
        self.client: Optional[redis.Redis] = None
        self._initialized = False
        
        # Cache configuration
        self.key_prefix = "mfh:"
        self.stats_key = f"{self.key_prefix}stats"
        
        # Serialization settings
        self.compression_enabled = True
        self.compression_threshold = 1024  # bytes

    async def _ensure_connection(self) -> redis.Redis:
        """Ensure Redis connection is established."""
        if self.client is None:
            try:
                self.client = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=False,  # We handle binary data for compression
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                
                # Test connection
                await self.client.ping()
                self._initialized = True
                
                logger.info(f"Redis cache initialized: {self.redis_url}")
                
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise ConnectionError(f"Redis connection failed: {e}")
                
        return self.client

    def _make_key(self, key: str) -> str:
        """Create a prefixed cache key."""
        return f"{self.key_prefix}{key}"

    def _serialize_value(self, value: BaseModel) -> bytes:
        """Serialize a Pydantic model for storage."""
        try:
            # Convert to JSON string
            json_str = value.json()
            data = json_str.encode('utf-8')
            
            # Add model type information
            model_type = value.__class__.__name__
            
            # Create payload with metadata
            payload = {
                "model_type": model_type,
                "data": json_str,
                "cached_at": datetime.utcnow().isoformat(),
                "size": len(data)
            }
            
            # Serialize the payload
            payload_bytes = json.dumps(payload).encode('utf-8')
            
            # Optional compression for large items
            if self.compression_enabled and len(payload_bytes) > self.compression_threshold:
                try:
                    import gzip
                    compressed = gzip.compress(payload_bytes)
                    if len(compressed) < len(payload_bytes):
                        # Add compression marker
                        return b"GZIP:" + compressed
                except ImportError:
                    pass  # Compression not available
            
            return payload_bytes
            
        except Exception as e:
            logger.error(f"Error serializing value: {e}")
            raise ValueError(f"Serialization failed: {e}")

    def _deserialize_value(self, data: bytes) -> Optional[BaseModel]:
        """Deserialize data back to a Pydantic model."""
        try:
            # Handle compression
            if data.startswith(b"GZIP:"):
                try:
                    import gzip
                    data = gzip.decompress(data[5:])  # Remove "GZIP:" prefix
                except ImportError:
                    logger.error("Compressed data found but gzip not available")
                    return None
            
            # Parse payload
            payload = json.loads(data.decode('utf-8'))
            model_type = payload["model_type"]
            model_data = json.loads(payload["data"])
            
            # Determine model class and deserialize
            if model_type == "MemoryItem":
                return MemoryItem(**model_data)
            elif model_type == "SessionData":
                return SessionData(**model_data)
            elif model_type == "KnowledgeRecord":
                return KnowledgeRecord(**model_data)
            elif model_type == "MemoryEvent":
                return MemoryEvent(**model_data)
            else:
                logger.warning(f"Unknown model type in cache: {model_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error deserializing cached value: {e}")
            return None

    async def get(self, key: str) -> Optional[BaseModel]:
        """
        Retrieve an item from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached item if found and valid, None otherwise
        """
        client = await self._ensure_connection()
        cache_key = self._make_key(key)
        
        try:
            data = await client.get(cache_key)
            
            if data is None:
                await self._update_stats("cache_miss")
                return None
            
            # Deserialize the cached value
            value = self._deserialize_value(data)
            
            if value is None:
                # Invalid cached data, remove it
                await client.delete(cache_key)
                await self._update_stats("cache_error")
                return None
            
            # Update access statistics
            await self._update_stats("cache_hit")
            logger.debug(f"Cache hit: {key}")
            
            return value
            
        except Exception as e:
            logger.error(f"Error retrieving from cache {key}: {e}")
            await self._update_stats("cache_error")
            return None

    async def set(self, key: str, value: BaseModel, ttl_seconds: Optional[int] = None) -> bool:
        """
        Store an item in the cache with TTL.
        
        Args:
            key: Cache key
            value: Pydantic model to cache
            ttl_seconds: Time-to-live in seconds (uses default if None)
            
        Returns:
            True if successfully cached, False otherwise
        """
        client = await self._ensure_connection()
        cache_key = self._make_key(key)
        
        try:
            # Serialize the value
            data = self._serialize_value(value)
            
            # Determine TTL
            ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
            
            # Store in Redis with TTL
            await client.setex(cache_key, ttl, data)
            
            # Update statistics
            await self._update_stats("cache_set", len(data))
            logger.debug(f"Cached item: {key} (TTL: {ttl}s, Size: {len(data)} bytes)")
            
            return True
            
        except Exception as e:
            logger.error(f"Error caching item {key}: {e}")
            await self._update_stats("cache_error")
            return False

    async def delete(self, key: str) -> bool:
        """
        Remove an item from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if item was removed, False if not found
        """
        client = await self._ensure_connection()
        cache_key = self._make_key(key)
        
        try:
            result = await client.delete(cache_key)
            deleted = result > 0
            
            if deleted:
                await self._update_stats("cache_delete")
                logger.debug(f"Cache item deleted: {key}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Error deleting from cache {key}: {e}")
            await self._update_stats("cache_error")
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if an item exists in the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if item exists, False otherwise
        """
        client = await self._ensure_connection()
        cache_key = self._make_key(key)
        
        try:
            result = await client.exists(cache_key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Error checking cache existence {key}: {e}")
            return False

    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get the remaining time-to-live for a cached item.
        
        Args:
            key: Cache key
            
        Returns:
            Remaining TTL in seconds, None if key doesn't exist
        """
        client = await self._ensure_connection()
        cache_key = self._make_key(key)
        
        try:
            ttl = await client.ttl(cache_key)
            return ttl if ttl > 0 else None
            
        except Exception as e:
            logger.error(f"Error getting TTL for {key}: {e}")
            return None

    async def extend_ttl(self, key: str, additional_seconds: int) -> bool:
        """
        Extend the TTL of a cached item.
        
        Args:
            key: Cache key
            additional_seconds: Additional seconds to add to TTL
            
        Returns:
            True if TTL was extended, False if key doesn't exist
        """
        client = await self._ensure_connection()
        cache_key = self._make_key(key)
        
        try:
            current_ttl = await client.ttl(cache_key)
            if current_ttl > 0:
                new_ttl = current_ttl + additional_seconds
                result = await client.expire(cache_key, new_ttl)
                return result
            return False
            
        except Exception as e:
            logger.error(f"Error extending TTL for {key}: {e}")
            return False

    async def list_keys(self, pattern: str = "*") -> List[str]:
        """
        List cache keys matching a pattern.
        
        Args:
            pattern: Redis key pattern (default: all keys)
            
        Returns:
            List of matching keys (without prefix)
        """
        client = await self._ensure_connection()
        
        try:
            # Add prefix to pattern
            full_pattern = f"{self.key_prefix}{pattern}"
            keys = await client.keys(full_pattern)
            
            # Remove prefix from results
            prefix_len = len(self.key_prefix)
            return [key.decode('utf-8')[prefix_len:] for key in keys]
            
        except Exception as e:
            logger.error(f"Error listing cache keys: {e}")
            return []

    async def clear(self, pattern: str = "*") -> int:
        """
        Clear cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match (default: all entries)
            
        Returns:
            Number of entries cleared
        """
        client = await self._ensure_connection()
        
        try:
            # Get matching keys
            full_pattern = f"{self.key_prefix}{pattern}"
            keys = await client.keys(full_pattern)
            
            if not keys:
                return 0
            
            # Delete all matching keys
            result = await client.delete(*keys)
            await self._update_stats("cache_clear", result)
            
            logger.info(f"Cleared {result} cache entries matching pattern: {pattern}")
            return result
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        client = await self._ensure_connection()
        
        try:
            # Get Redis info
            redis_info = await client.info()
            
            # Get our custom stats
            stats_data = await client.hgetall(self.stats_key)
            custom_stats = {k.decode('utf-8'): int(v) for k, v in stats_data.items()}
            
            # Calculate hit rate
            hits = custom_stats.get("cache_hit", 0)
            misses = custom_stats.get("cache_miss", 0)
            total_requests = hits + misses
            hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0
            
            # Get cache key count
            cache_keys = await client.keys(f"{self.key_prefix}*")
            cache_count = len([k for k in cache_keys if not k.decode('utf-8').endswith(':stats')])
            
            return {
                "hit_rate_percent": round(hit_rate, 2),
                "total_requests": total_requests,
                "cache_hits": hits,
                "cache_misses": misses,
                "cache_sets": custom_stats.get("cache_set", 0),
                "cache_deletes": custom_stats.get("cache_delete", 0),
                "cache_errors": custom_stats.get("cache_error", 0),
                "cache_clears": custom_stats.get("cache_clear", 0),
                "total_cached_items": cache_count,
                "total_bytes_cached": custom_stats.get("bytes_cached", 0),
                "redis_memory_used": redis_info.get("used_memory", 0),
                "redis_memory_human": redis_info.get("used_memory_human", "Unknown"),
                "redis_connected_clients": redis_info.get("connected_clients", 0),
                "redis_uptime_seconds": redis_info.get("uptime_in_seconds", 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}

    async def _update_stats(self, stat_name: str, value: int = 1) -> None:
        """Update cache statistics."""
        try:
            client = await self._ensure_connection()
            await client.hincrby(self.stats_key, stat_name, value)
            
            # Set TTL for stats (7 days)
            await client.expire(self.stats_key, 7 * 24 * 3600)
            
        except Exception as e:
            logger.debug(f"Error updating stats: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the cache.
        
        Returns:
            Health check results
        """
        try:
            client = await self._ensure_connection()
            
            # Test basic connectivity
            start_time = datetime.utcnow()
            await client.ping()
            ping_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Test read/write operations
            test_key = f"{self.key_prefix}health_check"
            test_value = {"test": True, "timestamp": datetime.utcnow().isoformat()}
            
            await client.setex(test_key, 10, json.dumps(test_value))
            retrieved = await client.get(test_key)
            await client.delete(test_key)
            
            write_read_ok = retrieved is not None
            
            return {
                "healthy": True,
                "ping_ms": round(ping_time, 2),
                "write_read_ok": write_read_ok,
                "connection_ok": True,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {
                "healthy": False,
                "ping_ms": None,
                "write_read_ok": False,
                "connection_ok": False,
                "error": str(e)
            }

    async def close(self) -> None:
        """Close the Redis connection."""
        if self.client:
            await self.client.close()
            self.client = None
            self._initialized = False
            logger.info("Redis cache connection closed")

    # Utility methods for different TTL strategies
    async def set_short_term(self, key: str, value: BaseModel, minutes: int = 5) -> bool:
        """Cache item for short-term use (default: 5 minutes)."""
        return await self.set(key, value, minutes * 60)

    async def set_medium_term(self, key: str, value: BaseModel, hours: int = 1) -> bool:
        """Cache item for medium-term use (default: 1 hour)."""
        return await self.set(key, value, hours * 3600)

    async def set_long_term(self, key: str, value: BaseModel, days: int = 1) -> bool:
        """Cache item for long-term use (default: 1 day)."""
        return await self.set(key, value, days * 24 * 3600)

    async def set_session_cache(self, session_id: str, data: SessionData) -> bool:
        """Cache session data with appropriate TTL."""
        # Sessions cached for 24 hours
        return await self.set_long_term(f"session:{session_id}", data)

    async def set_memory_cache(self, key: str, item: MemoryItem, relevance_based: bool = True) -> bool:
        """Cache memory item with TTL based on relevance score."""
        if relevance_based and hasattr(item, 'relevance_score'):
            # Higher relevance = longer cache time
            base_minutes = 15
            relevance_multiplier = item.relevance_score if item.relevance_score else 1.0
            ttl_minutes = int(base_minutes * (1 + relevance_multiplier))
            return await self.set(key, item, ttl_minutes * 60)
        else:
            return await self.set_short_term(key, item)


# Cache factory function
def create_redis_cache(config: Dict[str, Any]) -> RedisCache:
    """
    Factory function to create RedisCache instances.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured RedisCache instance
    """
    redis_url = config.get("redis_url", "redis://localhost:6379/0")
    ttl_seconds = config.get("cache_ttl_seconds", 900)
    
    cache = RedisCache(redis_url, ttl_seconds)
    
    # Optional configuration
    if "compression_enabled" in config:
        cache.compression_enabled = config["compression_enabled"]
    if "compression_threshold" in config:
        cache.compression_threshold = config["compression_threshold"]
    if "key_prefix" in config:
        cache.key_prefix = config["key_prefix"]
    
    return cache