#!/usr/bin/env python3
"""common.utils.redis_pool
Shared Redis connection pool utility to avoid redundant TCP connections.
"""
import os
import functools
import redis

_POOL = redis.ConnectionPool.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

@functools.lru_cache(maxsize=1)
def get_client():
    """Return a singleton redis.Redis client bound to the global pool."""
    return redis.Redis(connection_pool=_POOL)