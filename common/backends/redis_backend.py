#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Redis Backend Strategy - Phase 3.1

Redis-based backend implementation for ServiceRegistry and other components.
Provides high-performance, distributed memory storage with persistence,
clustering support, and advanced Redis features.

Part of Phase 3.1: Pluggable Backend Strategy - O3 Roadmap Implementation
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

try:
    import redis
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    aioredis = None
    REDIS_AVAILABLE = False

from .memory_backend import MemoryBackend, BackendMetrics


@dataclass
class RedisConfig:
    """Configuration for Redis backend."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    username: Optional[str] = None
    ssl: bool = False
    max_connections: int = 20
    connection_timeout: float = 5.0
    socket_timeout: float = 5.0
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    decode_responses: bool = True
    encoding: str = "utf-8"
    # Clustering
    cluster_mode: bool = False
    cluster_nodes: List[Dict[str, Union[str, int]]] = None
    # Sentinel
    sentinel_mode: bool = False
    sentinel_hosts: List[Dict[str, Union[str, int]]] = None
    sentinel_service: str = "mymaster"


class RedisBackend(MemoryBackend):
    """Redis-based backend implementation."""
    
    def __init__(self, name: str = "redis", config: RedisConfig = None, **kwargs):
        super().__init__(name, **kwargs)
        self.config = config or RedisConfig()
        self.redis_client: Optional[aioredis.Redis] = None
        self.connection_pool: Optional[aioredis.ConnectionPool] = None
        self._key_prefix = kwargs.get('key_prefix', f"{name}:")
        self._json_serializer = kwargs.get('json_serializer', json)
        
        if not REDIS_AVAILABLE:
            raise ImportError("Redis is not available. Install with: pip install redis")
    
    async def connect(self) -> bool:
        """Connect to Redis server."""
        try:
            with self._lock:
                if self._connected:
                    return True
                
                # Create connection pool
                pool_kwargs = {
                    'host': self.config.host,
                    'port': self.config.port,
                    'db': self.config.db,
                    'password': self.config.password,
                    'username': self.config.username,
                    'ssl': self.config.ssl,
                    'max_connections': self.config.max_connections,
                    'socket_timeout': self.config.socket_timeout,
                    'socket_connect_timeout': self.config.connection_timeout,
                    'retry_on_timeout': self.config.retry_on_timeout,
                    'decode_responses': self.config.decode_responses,
                    'encoding': self.config.encoding
                }
                
                if self.config.cluster_mode:
                    # Redis Cluster mode
                    if self.config.cluster_nodes:
                        nodes = [aioredis.RedisCluster.RedisNode(**node) for node in self.config.cluster_nodes]
                        self.redis_client = aioredis.RedisCluster(
                            startup_nodes=nodes,
                            decode_responses=self.config.decode_responses,
                            skip_full_coverage_check=True
                        )
                    else:
                        raise ValueError("Cluster nodes must be specified for cluster mode")
                
                elif self.config.sentinel_mode:
                    # Redis Sentinel mode
                    if self.config.sentinel_hosts:
                        sentinel = aioredis.Sentinel(
                            [(host['host'], host['port']) for host in self.config.sentinel_hosts]
                        )
                        self.redis_client = sentinel.master_for(
                            self.config.sentinel_service,
                            socket_timeout=self.config.socket_timeout
                        )
                    else:
                        raise ValueError("Sentinel hosts must be specified for sentinel mode")
                
                else:
                    # Standard Redis mode
                    self.connection_pool = aioredis.ConnectionPool(**pool_kwargs)
                    self.redis_client = aioredis.Redis(connection_pool=self.connection_pool)
                
                # Test connection
                await self.redis_client.ping()
                self._connected = True
                
                self.logger.info(f"Redis backend '{self.name}' connected to {self.config.host}:{self.config.port}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Redis server."""
        with self._lock:
            if self.redis_client:
                try:
                    await self.redis_client.close()
                    if self.connection_pool:
                        await self.connection_pool.disconnect()
                    self.logger.info(f"Redis backend '{self.name}' disconnected")
                except Exception as e:
                    self.logger.warning(f"Error during Redis disconnect: {e}")
                finally:
                    self.redis_client = None
                    self.connection_pool = None
                    self._connected = False
    
    def _make_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self._key_prefix}{key}"
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for Redis storage."""
        if isinstance(value, (str, int, float, bool)):
            return str(value)
        else:
            return self._json_serializer.dumps(value)
    
    def _deserialize_value(self, value: str) -> Any:
        """Deserialize value from Redis storage."""
        if value is None:
            return None
        
        # Try to parse as JSON first
        try:
            return self._json_serializer.loads(value)
        except (json.JSONDecodeError, TypeError):
            # Return as string if not valid JSON
            return value
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key from Redis."""
        if not self._connected:
            if not await self.connect():
                return None
        
        with self._metrics_timer():
            try:
                redis_key = self._make_key(key)
                value = await self.redis_client.get(redis_key)
                
                if value is not None:
                    self.metrics.cache_hits += 1
                    return self._deserialize_value(value)
                else:
                    self.metrics.cache_misses += 1
                    return None
                    
            except Exception as e:
                self.logger.error(f"Redis get error for key {key}: {e}")
                self.metrics.errors += 1
                return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set key-value pair in Redis with optional TTL."""
        if not self._connected:
            if not await self.connect():
                return False
        
        with self._metrics_timer():
            try:
                redis_key = self._make_key(key)
                serialized_value = self._serialize_value(value)
                
                if ttl is not None:
                    result = await self.redis_client.setex(redis_key, ttl, serialized_value)
                else:
                    result = await self.redis_client.set(redis_key, serialized_value)
                
                return bool(result)
                
            except Exception as e:
                self.logger.error(f"Redis set error for key {key}: {e}")
                self.metrics.errors += 1
                return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        if not self._connected:
            if not await self.connect():
                return False
        
        with self._metrics_timer():
            try:
                redis_key = self._make_key(key)
                result = await self.redis_client.delete(redis_key)
                return result > 0
                
            except Exception as e:
                self.logger.error(f"Redis delete error for key {key}: {e}")
                self.metrics.errors += 1
                return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self._connected:
            if not await self.connect():
                return False
        
        with self._metrics_timer():
            try:
                redis_key = self._make_key(key)
                result = await self.redis_client.exists(redis_key)
                return result > 0
                
            except Exception as e:
                self.logger.error(f"Redis exists error for key {key}: {e}")
                self.metrics.errors += 1
                return False
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern from Redis."""
        if not self._connected:
            if not await self.connect():
                return []
        
        with self._metrics_timer():
            try:
                redis_pattern = self._make_key(pattern)
                redis_keys = await self.redis_client.keys(redis_pattern)
                
                # Remove prefix from keys
                prefix_len = len(self._key_prefix)
                return [key[prefix_len:] for key in redis_keys]
                
            except Exception as e:
                self.logger.error(f"Redis keys error for pattern {pattern}: {e}")
                self.metrics.errors += 1
                return []
    
    async def clear(self) -> bool:
        """Clear all data with this backend's prefix."""
        if not self._connected:
            if not await self.connect():
                return False
        
        with self._metrics_timer():
            try:
                # Get all keys with prefix
                all_keys = await self.redis_client.keys(f"{self._key_prefix}*")
                
                if all_keys:
                    await self.redis_client.delete(*all_keys)
                
                return True
                
            except Exception as e:
                self.logger.error(f"Redis clear error: {e}")
                self.metrics.errors += 1
                return False
    
    async def size(self) -> int:
        """Get number of stored items with this backend's prefix."""
        if not self._connected:
            if not await self.connect():
                return 0
        
        with self._metrics_timer():
            try:
                all_keys = await self.redis_client.keys(f"{self._key_prefix}*")
                return len(all_keys)
                
            except Exception as e:
                self.logger.error(f"Redis size error: {e}")
                self.metrics.errors += 1
                return 0
    
    # Enhanced Redis operations
    async def mget(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values efficiently using Redis MGET."""
        if not self._connected:
            if not await self.connect():
                return {}
        
        with self._metrics_timer():
            try:
                redis_keys = [self._make_key(key) for key in keys]
                values = await self.redis_client.mget(redis_keys)
                
                result = {}
                for key, value in zip(keys, values):
                    if value is not None:
                        result[key] = self._deserialize_value(value)
                        self.metrics.cache_hits += 1
                    else:
                        self.metrics.cache_misses += 1
                
                return result
                
            except Exception as e:
                self.logger.error(f"Redis mget error: {e}")
                self.metrics.errors += 1
                return {}
    
    async def mset(self, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple key-value pairs efficiently."""
        if not self._connected:
            if not await self.connect():
                return False
        
        with self._metrics_timer():
            try:
                if ttl is not None:
                    # Use pipeline for SETEX operations
                    pipeline = self.redis_client.pipeline()
                    for key, value in data.items():
                        redis_key = self._make_key(key)
                        serialized_value = self._serialize_value(value)
                        pipeline.setex(redis_key, ttl, serialized_value)
                    
                    await pipeline.execute()
                else:
                    # Use MSET for better performance
                    redis_data = {}
                    for key, value in data.items():
                        redis_key = self._make_key(key)
                        redis_data[redis_key] = self._serialize_value(value)
                    
                    await self.redis_client.mset(redis_data)
                
                return True
                
            except Exception as e:
                self.logger.error(f"Redis mset error: {e}")
                self.metrics.errors += 1
                return False
    
    async def mdelete(self, keys: List[str]) -> int:
        """Delete multiple keys efficiently."""
        if not self._connected:
            if not await self.connect():
                return 0
        
        with self._metrics_timer():
            try:
                redis_keys = [self._make_key(key) for key in keys]
                return await self.redis_client.delete(*redis_keys)
                
            except Exception as e:
                self.logger.error(f"Redis mdelete error: {e}")
                self.metrics.errors += 1
                return 0
    
    async def increment(self, key: str, delta: int = 1) -> Optional[int]:
        """Increment integer value atomically."""
        if not self._connected:
            if not await self.connect():
                return None
        
        with self._metrics_timer():
            try:
                redis_key = self._make_key(key)
                
                if delta == 1:
                    result = await self.redis_client.incr(redis_key)
                else:
                    result = await self.redis_client.incrby(redis_key, delta)
                
                return result
                
            except Exception as e:
                self.logger.error(f"Redis increment error for key {key}: {e}")
                self.metrics.errors += 1
                return None
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key."""
        if not self._connected:
            if not await self.connect():
                return False
        
        with self._metrics_timer():
            try:
                redis_key = self._make_key(key)
                result = await self.redis_client.expire(redis_key, ttl)
                return bool(result)
                
            except Exception as e:
                self.logger.error(f"Redis expire error for key {key}: {e}")
                self.metrics.errors += 1
                return False
    
    # Advanced Redis features
    async def hget(self, name: str, key: str) -> Optional[Any]:
        """Get field from Redis hash."""
        if not self._connected:
            if not await self.connect():
                return None
        
        try:
            redis_name = self._make_key(name)
            value = await self.redis_client.hget(redis_name, key)
            return self._deserialize_value(value) if value else None
        except Exception as e:
            self.logger.error(f"Redis hget error: {e}")
            return None
    
    async def hset(self, name: str, key: str, value: Any) -> bool:
        """Set field in Redis hash."""
        if not self._connected:
            if not await self.connect():
                return False
        
        try:
            redis_name = self._make_key(name)
            serialized_value = self._serialize_value(value)
            result = await self.redis_client.hset(redis_name, key, serialized_value)
            return True
        except Exception as e:
            self.logger.error(f"Redis hset error: {e}")
            return False
    
    async def hgetall(self, name: str) -> Dict[str, Any]:
        """Get all fields from Redis hash."""
        if not self._connected:
            if not await self.connect():
                return {}
        
        try:
            redis_name = self._make_key(name)
            hash_data = await self.redis_client.hgetall(redis_name)
            return {k: self._deserialize_value(v) for k, v in hash_data.items()}
        except Exception as e:
            self.logger.error(f"Redis hgetall error: {e}")
            return {}
    
    async def lpush(self, name: str, *values) -> int:
        """Push values to left of Redis list."""
        if not self._connected:
            if not await self.connect():
                return 0
        
        try:
            redis_name = self._make_key(name)
            serialized_values = [self._serialize_value(v) for v in values]
            return await self.redis_client.lpush(redis_name, *serialized_values)
        except Exception as e:
            self.logger.error(f"Redis lpush error: {e}")
            return 0
    
    async def rpop(self, name: str) -> Optional[Any]:
        """Pop value from right of Redis list."""
        if not self._connected:
            if not await self.connect():
                return None
        
        try:
            redis_name = self._make_key(name)
            value = await self.redis_client.rpop(redis_name)
            return self._deserialize_value(value) if value else None
        except Exception as e:
            self.logger.error(f"Redis rpop error: {e}")
            return None
    
    async def publish(self, channel: str, message: Any) -> int:
        """Publish message to Redis pub/sub channel."""
        if not self._connected:
            if not await self.connect():
                return 0
        
        try:
            serialized_message = self._serialize_value(message)
            return await self.redis_client.publish(channel, serialized_message)
        except Exception as e:
            self.logger.error(f"Redis publish error: {e}")
            return 0
    
    def get_redis_info(self) -> Dict[str, Any]:
        """Get Redis server information."""
        if not self._connected or not self.redis_client:
            return {}
        
        try:
            # Get basic info synchronously for metrics
            import asyncio
            loop = asyncio.get_event_loop()
            info = loop.run_until_complete(self.redis_client.info())
            
            return {
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "role": info.get("role")
            }
        except Exception as e:
            self.logger.error(f"Failed to get Redis info: {e}")
            return {}
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get enhanced metrics including Redis info."""
        base_metrics = super().get_metrics()
        redis_info = self.get_redis_info()
        
        base_metrics.update({
            "redis_info": redis_info,
            "cluster_mode": self.config.cluster_mode,
            "sentinel_mode": self.config.sentinel_mode,
            "key_prefix": self._key_prefix
        })
        
        return base_metrics


# Register Redis backend with factory
from .memory_backend import BackendFactory

if REDIS_AVAILABLE:
    BackendFactory.register_backend("redis", RedisBackend)


# Convenience functions for Redis-specific operations
async def create_redis_backend(name: str = "redis", config: RedisConfig = None, **kwargs) -> RedisBackend:
    """Create and connect Redis backend."""
    backend = RedisBackend(name=name, config=config, **kwargs)
    await backend.connect()
    return backend


def redis_url_to_config(redis_url: str) -> RedisConfig:
    """Parse Redis URL into RedisConfig."""
    try:
        from urllib.parse import urlparse
        
        parsed = urlparse(redis_url)
        
        return RedisConfig(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            db=int(parsed.path.lstrip('/')) if parsed.path else 0,
            password=parsed.password,
            username=parsed.username,
            ssl=parsed.scheme == "rediss"
        )
    except Exception as e:
        logging.getLogger("redis_backend").error(f"Failed to parse Redis URL: {e}")
        return RedisConfig()
