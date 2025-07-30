#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Common Pools Package

High-performance connection pooling and async socket wrappers for the AI System Monorepo.
Provides both synchronous ZMQ pools and async ZMQ pools for different use cases.

Part of Phase 2.3: Async Socket Wrappers - O3 Roadmap Implementation
"""

# Sync ZMQ Pool (existing)
try:
    from .zmq_pool import (
        get_req_socket,
        get_rep_socket, 
        get_pub_socket,
        get_sub_socket,
        cleanup_zmq_pool
    )
    __sync_zmq_available = True
except ImportError:
    __sync_zmq_available = False

# Async ZMQ Pool (new)
from .async_zmq_pool import (
    # Core classes
    AsyncSocket,
    AsyncSocketPool,
    SocketType,
    SocketConfig,
    SocketMetrics,
    
    # Context and pool management
    get_async_context,
    get_socket_pool,
    async_socket,
    
    # Convenience socket creators
    async_req_socket,
    async_rep_socket,
    async_pub_socket,
    async_sub_socket,
    async_push_socket,
    async_pull_socket,
    
    # High-level patterns
    AsyncRequestReply,
    AsyncPublisher,
    AsyncSubscriber,
    
    # Cleanup and monitoring
    cleanup_async_zmq,
    get_global_metrics
)

__all__ = [
    # Async ZMQ exports
    "AsyncSocket",
    "AsyncSocketPool", 
    "SocketType",
    "SocketConfig",
    "SocketMetrics",
    "get_async_context",
    "get_socket_pool",
    "async_socket",
    "async_req_socket",
    "async_rep_socket",
    "async_pub_socket", 
    "async_sub_socket",
    "async_push_socket",
    "async_pull_socket",
    "AsyncRequestReply",
    "AsyncPublisher",
    "AsyncSubscriber",
    "cleanup_async_zmq",
    "get_global_metrics"
]

# Add sync exports if available
if __sync_zmq_available:
    __all__.extend([
        "get_req_socket",
        "get_rep_socket",
        "get_pub_socket", 
        "get_sub_socket",
        "cleanup_zmq_pool"
    ])

# Version info
__version__ = "2.3.0"
__phase__ = "Phase 2.3: Async Socket Wrappers"
