#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Common Backends Package

Pluggable backend strategy implementations for memory storage across
ServiceRegistry and other components. Provides abstract interface and
multiple concrete implementations.

Part of Phase 3.1: Pluggable Backend Strategy - O3 Roadmap Implementation
"""

# Core backend interface
from .memory_backend import (
    MemoryBackend,
    BackendMetrics,
    InMemoryBackend,
    FileBackend,
    BackendFactory,
    get_backend,
    register_backend,
    create_and_register_backend,
    cleanup_all_backends,
    quick_get,
    quick_set
)

# Redis backend (optional)
try:
    from .redis_backend import (
        RedisBackend,
        RedisConfig,
        create_redis_backend,
        redis_url_to_config
    )
    REDIS_AVAILABLE = True
    
    __redis_exports = [
        "RedisBackend",
        "RedisConfig", 
        "create_redis_backend",
        "redis_url_to_config"
    ]
except ImportError:
    REDIS_AVAILABLE = False
    __redis_exports = []

__all__ = [
    # Core backend exports
    "MemoryBackend",
    "BackendMetrics",
    "InMemoryBackend", 
    "FileBackend",
    "BackendFactory",
    "get_backend",
    "register_backend",
    "create_and_register_backend",
    "cleanup_all_backends",
    "quick_get",
    "quick_set",
    # Redis availability
    "REDIS_AVAILABLE"
] + __redis_exports

# Version info
__version__ = "3.1.0"
__phase__ = "Phase 3.1: Pluggable Backend Strategy"

# Backend recommendations based on use case
BACKEND_RECOMMENDATIONS = {
    "development": "memory",
    "testing": "memory", 
    "staging": "redis",
    "production": "redis",
    "local_persistence": "file",
    "high_performance": "redis",
    "simple_setup": "memory"
}


def get_recommended_backend_type(environment: str = "development") -> str:
    """Get recommended backend type for environment."""
    return BACKEND_RECOMMENDATIONS.get(environment, "memory")


def create_recommended_backend(environment: str = "development", 
                             name: str = "default", 
                             **kwargs) -> MemoryBackend:
    """Create recommended backend for environment."""
    backend_type = get_recommended_backend_type(environment)
    return create_and_register_backend(backend_type, name=name, **kwargs)
