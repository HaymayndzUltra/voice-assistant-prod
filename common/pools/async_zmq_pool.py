#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Async ZMQ Pool - Phase 2.3

High-performance async socket wrappers for ZMQ with connection pooling,
automatic reconnection, and asyncio integration. Provides non-blocking
socket operations for high-throughput agent communication.

Part of Phase 2.3: Async Socket Wrappers - O3 Roadmap Implementation
"""

import asyncio
import logging
import time
import weakref
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Union
from enum import Enum

import zmq
import zmq.asyncio

# Global async context - singleton pattern
_async_context: Optional[zmq.asyncio.Context] = None
_socket_pools: Dict[str, 'AsyncSocketPool'] = {}
_cleanup_tasks: Set[asyncio.Task] = set()


class SocketType(Enum):
    """Supported socket types for async operations."""
    REQ = zmq.REQ
    REP = zmq.REP
    PUB = zmq.PUB
    SUB = zmq.SUB
    PUSH = zmq.PUSH
    PULL = zmq.PULL
    DEALER = zmq.DEALER
    ROUTER = zmq.ROUTER


@dataclass
class SocketConfig:
    """Configuration for async socket creation."""
    socket_type: SocketType
    endpoint: str
    bind: bool = False  # True for bind, False for connect
    high_water_mark: int = 1000
    linger: int = 1000  # milliseconds
    connect_timeout: int = 5000  # milliseconds
    max_retries: int = 3
    heartbeat_interval: int = 30000  # milliseconds
    subscription_topics: List[str] = field(default_factory=list)  # For SUB sockets


@dataclass
class SocketMetrics:
    """Metrics tracking for async sockets."""
    created_at: float = field(default_factory=time.time)
    messages_sent: int = 0
    messages_received: int = 0
    errors: int = 0
    reconnections: int = 0
    last_activity: float = field(default_factory=time.time)
    total_bytes_sent: int = 0
    total_bytes_received: int = 0


class AsyncSocket:
    """Wrapper for async ZMQ socket with enhanced features."""
    
    def __init__(self, config: SocketConfig, context: zmq.asyncio.Context):
        self.config = config
        self.context = context
        self.socket: Optional[zmq.asyncio.Socket] = None
        self.metrics = SocketMetrics()
        self.logger = logging.getLogger(f"async_socket.{config.socket_type.name}")
        self._connected = False
        self._lock = asyncio.Lock()
        
    async def _create_socket(self) -> zmq.asyncio.Socket:
        """Create and configure the ZMQ socket."""
        socket = self.context.socket(self.config.socket_type.value)
        
        # Configure socket options
        socket.setsockopt(zmq.SNDHWM, self.config.high_water_mark)
        socket.setsockopt(zmq.RCVHWM, self.config.high_water_mark)
        socket.setsockopt(zmq.LINGER, self.config.linger)
        
        # Set timeouts
        if self.config.connect_timeout > 0:
            socket.setsockopt(zmq.CONNECT_TIMEOUT, self.config.connect_timeout)
        
        # Set heartbeat for connection monitoring
        if self.config.heartbeat_interval > 0:
            socket.setsockopt(zmq.HEARTBEAT_IVL, self.config.heartbeat_interval)
            socket.setsockopt(zmq.HEARTBEAT_TIMEOUT, self.config.heartbeat_interval * 3)
            socket.setsockopt(zmq.HEARTBEAT_TTL, self.config.heartbeat_interval * 10)
        
        # Configure SUB socket subscriptions
        if self.config.socket_type == SocketType.SUB:
            for topic in self.config.subscription_topics:
                socket.setsockopt_string(zmq.SUBSCRIBE, topic)
        
        return socket
    
    async def connect(self) -> bool:
        """Connect or bind the socket."""
        async with self._lock:
            try:
                if self.socket is None:
                    self.socket = await self._create_socket()
                
                if self.config.bind:
                    self.socket.bind(self.config.endpoint)
                    self.logger.debug(f"Socket bound to {self.config.endpoint}")
                else:
                    self.socket.connect(self.config.endpoint)
                    self.logger.debug(f"Socket connected to {self.config.endpoint}")
                
                self._connected = True
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to connect socket: {e}")
                self.metrics.errors += 1
                return False
    
    async def disconnect(self):
        """Disconnect and cleanup the socket."""
        async with self._lock:
            if self.socket is not None:
                try:
                    self.socket.close()
                    self.logger.debug(f"Socket disconnected from {self.config.endpoint}")
                except Exception as e:
                    self.logger.warning(f"Error during socket disconnect: {e}")
                finally:
                    self.socket = None
                    self._connected = False
    
    async def send(self, data: Union[str, bytes], flags: int = 0) -> bool:
        """Send data through the socket."""
        if not self._connected or self.socket is None:
            if not await self.connect():
                return False
        
        try:
            if isinstance(data, str):
                await self.socket.send_string(data, flags)
                self.metrics.total_bytes_sent += len(data.encode('utf-8'))
            else:
                await self.socket.send(data, flags)
                self.metrics.total_bytes_sent += len(data)
            
            self.metrics.messages_sent += 1
            self.metrics.last_activity = time.time()
            return True
            
        except Exception as e:
            self.logger.error(f"Send error: {e}")
            self.metrics.errors += 1
            return False
    
    async def recv(self, flags: int = 0, timeout: Optional[float] = None) -> Optional[bytes]:
        """Receive data from the socket."""
        if not self._connected or self.socket is None:
            if not await self.connect():
                return None
        
        try:
            if timeout:
                data = await asyncio.wait_for(self.socket.recv(flags), timeout=timeout)
            else:
                data = await self.socket.recv(flags)
            
            self.metrics.messages_received += 1
            self.metrics.total_bytes_received += len(data)
            self.metrics.last_activity = time.time()
            return data
            
        except asyncio.TimeoutError:
            self.logger.debug("Receive timeout")
            return None
        except Exception as e:
            self.logger.error(f"Receive error: {e}")
            self.metrics.errors += 1
            return None
    
    async def recv_string(self, flags: int = 0, timeout: Optional[float] = None) -> Optional[str]:
        """Receive string data from the socket."""
        if not self._connected or self.socket is None:
            if not await self.connect():
                return None
        
        try:
            if timeout:
                data = await asyncio.wait_for(self.socket.recv_string(flags), timeout=timeout)
            else:
                data = await self.socket.recv_string(flags)
            
            self.metrics.messages_received += 1
            self.metrics.total_bytes_received += len(data.encode('utf-8'))
            self.metrics.last_activity = time.time()
            return data
            
        except asyncio.TimeoutError:
            self.logger.debug("Receive string timeout")
            return None
        except Exception as e:
            self.logger.error(f"Receive string error: {e}")
            self.metrics.errors += 1
            return None
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get socket metrics."""
        uptime = time.time() - self.metrics.created_at
        return {
            "endpoint": self.config.endpoint,
            "socket_type": self.config.socket_type.name,
            "connected": self._connected,
            "uptime_seconds": uptime,
            "messages_sent": self.metrics.messages_sent,
            "messages_received": self.metrics.messages_received,
            "total_bytes_sent": self.metrics.total_bytes_sent,
            "total_bytes_received": self.metrics.total_bytes_received,
            "errors": self.metrics.errors,
            "reconnections": self.metrics.reconnections,
            "last_activity": self.metrics.last_activity,
            "throughput_msg_per_sec": (self.metrics.messages_sent + self.metrics.messages_received) / max(1, uptime)
        }


class AsyncSocketPool:
    """Pool manager for async ZMQ sockets."""
    
    def __init__(self, pool_name: str, max_sockets: int = 100):
        self.pool_name = pool_name
        self.max_sockets = max_sockets
        self.sockets: Dict[str, AsyncSocket] = {}
        self.socket_refs: Dict[str, weakref.ref] = {}
        self.logger = logging.getLogger(f"async_pool.{pool_name}")
        self._cleanup_interval = 60  # seconds
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def get_socket(self, config: SocketConfig) -> AsyncSocket:
        """Get or create a socket from the pool."""
        socket_key = f"{config.socket_type.name}:{config.endpoint}:{config.bind}"
        
        # Check if socket already exists
        if socket_key in self.sockets:
            socket = self.sockets[socket_key]
            if socket._connected:
                return socket
            else:
                # Reconnect if needed
                await socket.connect()
                return socket
        
        # Create new socket
        if len(self.sockets) >= self.max_sockets:
            await self._cleanup_inactive_sockets()
        
        context = get_async_context()
        socket = AsyncSocket(config, context)
        
        self.sockets[socket_key] = socket
        self.socket_refs[socket_key] = weakref.ref(socket, lambda ref: self._on_socket_deleted(socket_key))
        
        self.logger.debug(f"Created new socket: {socket_key}")
        return socket
    
    def _on_socket_deleted(self, socket_key: str):
        """Callback when socket is garbage collected."""
        self.sockets.pop(socket_key, None)
        self.socket_refs.pop(socket_key, None)
    
    async def _cleanup_inactive_sockets(self):
        """Remove inactive sockets from the pool."""
        current_time = time.time()
        inactive_threshold = 300  # 5 minutes
        
        to_remove = []
        for key, socket in self.sockets.items():
            if current_time - socket.metrics.last_activity > inactive_threshold:
                to_remove.append(key)
        
        for key in to_remove:
            socket = self.sockets[key]
            await socket.disconnect()
            del self.sockets[key]
            self.socket_refs.pop(key, None)
            self.logger.debug(f"Cleaned up inactive socket: {key}")
    
    async def close_all(self):
        """Close all sockets in the pool."""
        for socket in self.sockets.values():
            await socket.disconnect()
        
        self.sockets.clear()
        self.socket_refs.clear()
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
    
    def get_pool_metrics(self) -> Dict[str, Any]:
        """Get pool-level metrics."""
        total_sent = sum(s.metrics.messages_sent for s in self.sockets.values())
        total_received = sum(s.metrics.messages_received for s in self.sockets.values())
        total_errors = sum(s.metrics.errors for s in self.sockets.values())
        
        return {
            "pool_name": self.pool_name,
            "active_sockets": len(self.sockets),
            "max_sockets": self.max_sockets,
            "total_messages_sent": total_sent,
            "total_messages_received": total_received,
            "total_errors": total_errors,
            "sockets": [socket.get_metrics() for socket in self.sockets.values()]
        }


def get_async_context() -> zmq.asyncio.Context:
    """Get or create the global async ZMQ context."""
    global _async_context
    
    if _async_context is None or _async_context.closed:
        _async_context = zmq.asyncio.Context()
        logging.getLogger("async_zmq").info("Created new async ZMQ context")
    
    return _async_context


def get_socket_pool(pool_name: str = "default") -> AsyncSocketPool:
    """Get or create a socket pool."""
    if pool_name not in _socket_pools:
        _socket_pools[pool_name] = AsyncSocketPool(pool_name)
        logging.getLogger("async_zmq").info(f"Created socket pool: {pool_name}")
    
    return _socket_pools[pool_name]


@asynccontextmanager
async def async_socket(config: SocketConfig, pool_name: str = "default"):
    """Context manager for async socket usage."""
    pool = get_socket_pool(pool_name)
    socket = await pool.get_socket(config)
    
    try:
        yield socket
    finally:
        # Socket remains in pool for reuse
        pass


# Convenience functions for common socket patterns
async def async_req_socket(endpoint: str, **kwargs) -> AsyncSocket:
    """Create async REQ socket."""
    config = SocketConfig(SocketType.REQ, endpoint, **kwargs)
    pool = get_socket_pool()
    return await pool.get_socket(config)


async def async_rep_socket(endpoint: str, **kwargs) -> AsyncSocket:
    """Create async REP socket."""
    config = SocketConfig(SocketType.REP, endpoint, bind=True, **kwargs)
    pool = get_socket_pool()
    return await pool.get_socket(config)


async def async_pub_socket(endpoint: str, **kwargs) -> AsyncSocket:
    """Create async PUB socket."""
    config = SocketConfig(SocketType.PUB, endpoint, bind=True, **kwargs)
    pool = get_socket_pool()
    return await pool.get_socket(config)


async def async_sub_socket(endpoint: str, topics: List[str] = None, **kwargs) -> AsyncSocket:
    """Create async SUB socket."""
    topics = topics or [""]  # Subscribe to all if no topics specified
    config = SocketConfig(SocketType.SUB, endpoint, subscription_topics=topics, **kwargs)
    pool = get_socket_pool()
    return await pool.get_socket(config)


async def async_push_socket(endpoint: str, **kwargs) -> AsyncSocket:
    """Create async PUSH socket."""
    config = SocketConfig(SocketType.PUSH, endpoint, **kwargs)
    pool = get_socket_pool()
    return await pool.get_socket(config)


async def async_pull_socket(endpoint: str, **kwargs) -> AsyncSocket:
    """Create async PULL socket."""
    config = SocketConfig(SocketType.PULL, endpoint, bind=True, **kwargs)
    pool = get_socket_pool()
    return await pool.get_socket(config)


# High-level async patterns
class AsyncRequestReply:
    """High-level async request-reply pattern."""
    
    def __init__(self, endpoint: str, timeout: float = 10.0):
        self.endpoint = endpoint
        self.timeout = timeout
        self.socket: Optional[AsyncSocket] = None
    
    async def request(self, data: Union[str, bytes]) -> Optional[Union[str, bytes]]:
        """Send request and wait for reply."""
        if self.socket is None:
            self.socket = await async_req_socket(self.endpoint)
        
        success = await self.socket.send(data)
        if not success:
            return None
        
        if isinstance(data, str):
            return await self.socket.recv_string(timeout=self.timeout)
        else:
            return await self.socket.recv(timeout=self.timeout)


class AsyncPublisher:
    """High-level async publisher pattern."""
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.socket: Optional[AsyncSocket] = None
    
    async def publish(self, topic: str, data: Union[str, bytes]) -> bool:
        """Publish message with topic."""
        if self.socket is None:
            self.socket = await async_pub_socket(self.endpoint)
        
        if isinstance(data, str):
            message = f"{topic}:{data}"
            return await self.socket.send(message)
        else:
            message = f"{topic}:".encode() + data
            return await self.socket.send(message)


class AsyncSubscriber:
    """High-level async subscriber pattern."""
    
    def __init__(self, endpoint: str, topics: List[str] = None):
        self.endpoint = endpoint
        self.topics = topics or [""]
        self.socket: Optional[AsyncSocket] = None
    
    async def subscribe(self) -> AsyncSocket:
        """Get subscriber socket."""
        if self.socket is None:
            self.socket = await async_sub_socket(self.endpoint, self.topics)
        return self.socket
    
    async def receive(self, timeout: Optional[float] = None) -> Optional[tuple]:
        """Receive message, returns (topic, data) tuple."""
        socket = await self.subscribe()
        message = await socket.recv_string(timeout=timeout)
        
        if message and ":" in message:
            topic, data = message.split(":", 1)
            return topic, data
        
        return None


# Cleanup and shutdown
async def cleanup_async_zmq():
    """Cleanup all async ZMQ resources."""
    global _async_context, _socket_pools, _cleanup_tasks
    
    # Close all socket pools
    for pool in _socket_pools.values():
        await pool.close_all()
    _socket_pools.clear()
    
    # Cancel cleanup tasks
    for task in _cleanup_tasks:
        if not task.done():
            task.cancel()
    _cleanup_tasks.clear()
    
    # Close context
    if _async_context and not _async_context.closed:
        _async_context.term()
        _async_context = None
    
    logging.getLogger("async_zmq").info("Async ZMQ cleanup completed")


# Auto-cleanup on event loop shutdown
def _setup_cleanup():
    """Setup automatic cleanup on event loop shutdown."""
    try:
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(cleanup_async_zmq()))
        loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(cleanup_async_zmq()))
    except (RuntimeError, NotImplementedError):
        # Signal handlers not available on this platform
        pass


# Performance monitoring
def get_global_metrics() -> Dict[str, Any]:
    """Get global async ZMQ metrics."""
    return {
        "context_active": _async_context is not None and not _async_context.closed,
        "active_pools": len(_socket_pools),
        "pools": {name: pool.get_pool_metrics() for name, pool in _socket_pools.items()}
    }
