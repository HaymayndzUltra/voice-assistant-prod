"""
WP-05 ZMQ Connection Pool
High-performance ZMQ socket pooling with automatic lifecycle management
"""

import zmq
import zmq.asyncio
import threading
import time
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from queue import Queue, Empty
from contextlib import contextmanager
import weakref
from enum import Enum

from common.env_helpers import get_env

logger = logging.getLogger(__name__)

class SocketType(Enum):
    """ZMQ Socket types supported by the pool"""
    REQ = zmq.REQ
    REP = zmq.REP
    PUB = zmq.PUB
    SUB = zmq.SUB
    PUSH = zmq.PUSH
    PULL = zmq.PULL
    PAIR = zmq.PAIR
    DEALER = zmq.DEALER
    ROUTER = zmq.ROUTER

@dataclass
class SocketConfig:
    """Configuration for ZMQ socket creation"""
    socket_type: SocketType
    endpoint: str
    bind: bool = False  # True for bind, False for connect
    options: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.options is None:
            self.options = {}

@dataclass
class PooledSocket:
    """Wrapper for pooled ZMQ socket with metadata"""
    socket: zmq.Socket
    config: SocketConfig
    created_at: float
    last_used: float
    usage_count: int = 0
    is_healthy: bool = True
    
    def __post_init__(self):
        self.last_used = time.time()

class ZMQConnectionPool:
    """High-performance ZMQ connection pool with lifecycle management"""
    
    def __init__(self,
                 max_connections: int = 50,
                 max_idle_time: int = 300,  # 5 minutes
                 health_check_interval: int = 60,
                 cleanup_interval: int = 120):
        
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time
        self.health_check_interval = health_check_interval
        self.cleanup_interval = cleanup_interval
        
        # ZMQ contexts
        self._context = zmq.Context()
        self._async_context = zmq.asyncio.Context()
        
        # Connection pools by config
        self._pools: Dict[str, Queue] = {}
        self._active_sockets: Dict[str, List[PooledSocket]] = {}
        self._pool_locks: Dict[str, threading.Lock] = {}
        
        # Pool management
        self._lock = threading.RLock()
        self._cleanup_thread = None
        self._running = True
        
        # Metrics
        self._metrics = {
            'total_connections': 0,
            'active_connections': 0,
            'pool_hits': 0,
            'pool_misses': 0,
            'cleanup_count': 0,
            'error_count': 0
        }
        
        # Start background cleanup
        self._start_cleanup_thread()
        
        logger.info(f"ZMQConnectionPool initialized - max_connections: {max_connections}")
    
    def _get_pool_key(self, config: SocketConfig) -> str:
        """Generate unique key for socket configuration"""
        return f"{config.socket_type.name}:{config.endpoint}:{config.bind}"
    
    def _ensure_pool_exists(self, pool_key: str) -> None:
        """Ensure pool structures exist for the given key"""
        if pool_key not in self._pools:
            self._pools[pool_key] = Queue(maxsize=self.max_connections)
            self._active_sockets[pool_key] = []
            self._pool_locks[pool_key] = threading.Lock()
    
    def _create_socket(self, config: SocketConfig) -> zmq.Socket:
        """Create new ZMQ socket with configuration"""
        try:
            socket = self._context.socket(config.socket_type.value)
            
            # Apply socket options
            if config.options:
                for option, value in config.options.items():
                    if hasattr(zmq, option):
                        socket.setsockopt(getattr(zmq, option), value)
            
            # Bind or connect
            if config.bind:
                socket.bind(config.endpoint)
                logger.debug(f"ZMQ socket bound to {config.endpoint}")
            else:
                socket.connect(config.endpoint)
                logger.debug(f"ZMQ socket connected to {config.endpoint}")
            
            self._metrics['total_connections'] += 1
            return socket
            
        except Exception as e:
            self._metrics['error_count'] += 1
            logger.error(f"Failed to create ZMQ socket: {e}")
            raise
    
    def get_socket(self, config: SocketConfig) -> PooledSocket:
        """Get socket from pool or create new one"""
        pool_key = self._get_pool_key(config)
        
        with self._lock:
            self._ensure_pool_exists(pool_key)
        
        with self._pool_locks[pool_key]:
            # Try to get from pool
            try:
                pooled_socket = self._pools[pool_key].get_nowait()
                pooled_socket.last_used = time.time()
                pooled_socket.usage_count += 1
                self._metrics['pool_hits'] += 1
                logger.debug(f"Retrieved socket from pool: {pool_key}")
                return pooled_socket
                
            except Empty:
                # Create new socket
                socket = self._create_socket(config)
                pooled_socket = PooledSocket(
                    socket=socket,
                    config=config,
                    created_at=time.time(),
                    last_used=time.time(),
                    usage_count=1
                )
                
                self._active_sockets[pool_key].append(pooled_socket)
                self._metrics['active_connections'] += 1
                self._metrics['pool_misses'] += 1
                logger.debug(f"Created new socket: {pool_key}")
                return pooled_socket
    
    def return_socket(self, pooled_socket: PooledSocket) -> None:
        """Return socket to pool"""
        pool_key = self._get_pool_key(pooled_socket.config)
        
        if not pooled_socket.is_healthy:
            self._close_socket(pooled_socket)
            return
        
        with self._pool_locks.get(pool_key, threading.Lock()):
            try:
                # Update last used time
                pooled_socket.last_used = time.time()
                
                # Return to pool if not full
                self._pools[pool_key].put_nowait(pooled_socket)
                logger.debug(f"Returned socket to pool: {pool_key}")
                
            except Exception:
                # Pool is full, close the socket
                self._close_socket(pooled_socket)
    
    def _close_socket(self, pooled_socket: PooledSocket) -> None:
        """Close and cleanup socket"""
        try:
            pooled_socket.socket.close()
            
            # Remove from active sockets
            pool_key = self._get_pool_key(pooled_socket.config)
            if pool_key in self._active_sockets:
                try:
                    self._active_sockets[pool_key].remove(pooled_socket)
                    self._metrics['active_connections'] -= 1
                except ValueError:
                    pass  # Socket not in list
            
            logger.debug(f"Closed socket: {pool_key}")
            
        except Exception as e:
            logger.warning(f"Error closing socket: {e}")
    
    @contextmanager
    def socket(self, config: SocketConfig):
        """Context manager for getting and returning sockets"""
        pooled_socket = self.get_socket(config)
        try:
            yield pooled_socket.socket
        except Exception as e:
            # Mark socket as unhealthy on error
            pooled_socket.is_healthy = False
            logger.warning(f"Socket error, marking unhealthy: {e}")
            raise
        finally:
            self.return_socket(pooled_socket)
    
    def _cleanup_expired_sockets(self) -> int:
        """Remove expired and idle sockets"""
        current_time = time.time()
        cleanup_count = 0
        
        with self._lock:
            for pool_key in list(self._pools.keys()):
                expired_sockets = []
                
                # Check pooled sockets
                temp_queue = Queue()
                while not self._pools[pool_key].empty():
                    try:
                        pooled_socket = self._pools[pool_key].get_nowait()
                        
                        # Check if expired
                        if (current_time - pooled_socket.last_used) > self.max_idle_time:
                            expired_sockets.append(pooled_socket)
                        else:
                            temp_queue.put(pooled_socket)
                    except Empty:
                        break
                
                # Put back non-expired sockets
                while not temp_queue.empty():
                    self._pools[pool_key].put(temp_queue.get())
                
                # Close expired sockets
                for socket in expired_sockets:
                    self._close_socket(socket)
                    cleanup_count += 1
        
        if cleanup_count > 0:
            self._metrics['cleanup_count'] += cleanup_count
            logger.info(f"Cleaned up {cleanup_count} expired sockets")
        
        return cleanup_count
    
    def _health_check_sockets(self) -> int:
        """Perform health check on active sockets"""
        unhealthy_count = 0
        
        with self._lock:
            for pool_key, sockets in self._active_sockets.items():
                for pooled_socket in sockets[:]:  # Copy list to avoid modification during iteration
                    try:
                        # Simple health check - try to get socket option
                        pooled_socket.socket.getsockopt(zmq.TYPE)
                    except Exception:
                        pooled_socket.is_healthy = False
                        self._close_socket(pooled_socket)
                        unhealthy_count += 1
        
        if unhealthy_count > 0:
            logger.info(f"Removed {unhealthy_count} unhealthy sockets")
        
        return unhealthy_count
    
    def _cleanup_loop(self):
        """Background cleanup loop"""
        last_health_check = 0
        
        while self._running:
            try:
                current_time = time.time()
                
                # Cleanup expired sockets
                self._cleanup_expired_sockets()
                
                # Health check periodically
                if (current_time - last_health_check) > self.health_check_interval:
                    self._health_check_sockets()
                    last_health_check = current_time
                
                # Sleep until next cleanup
                time.sleep(self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                time.sleep(10)  # Sleep on error
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread"""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                daemon=True,
                name="ZMQPool-Cleanup"
            )
            self._cleanup_thread.start()
            logger.info("Started ZMQ pool cleanup thread")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        with self._lock:
            pool_stats = {}
            for pool_key, pool in self._pools.items():
                pool_stats[pool_key] = {
                    'pooled_connections': pool.qsize(),
                    'active_connections': len(self._active_sockets.get(pool_key, []))
                }
            
            return {
                'metrics': self._metrics.copy(),
                'pools': pool_stats,
                'total_pools': len(self._pools),
                'cleanup_thread_alive': self._cleanup_thread and self._cleanup_thread.is_alive()
            }
    
    def close_all(self):
        """Close all connections and cleanup"""
        logger.info("Closing all ZMQ connections...")
        
        self._running = False
        
        with self._lock:
            # Close all pooled sockets
            for pool_key, pool in self._pools.items():
                while not pool.empty():
                    try:
                        pooled_socket = pool.get_nowait()
                        self._close_socket(pooled_socket)
                    except Empty:
                        break
            
            # Close all active sockets
            for sockets in self._active_sockets.values():
                for pooled_socket in sockets[:]:
                    self._close_socket(pooled_socket)
            
            # Clear pools
            self._pools.clear()
            self._active_sockets.clear()
            self._pool_locks.clear()
        
        # Close contexts
        try:
            self._context.term()
            self._async_context.term()
        except Exception as e:
            logger.warning(f"Error closing ZMQ contexts: {e}")
        
        # Wait for cleanup thread
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        
        logger.info("ZMQ connection pool closed")


# Global ZMQ pool instance
_zmq_pool: Optional[ZMQConnectionPool] = None

def get_zmq_pool() -> ZMQConnectionPool:
    """Get global ZMQ connection pool"""
    global _zmq_pool
    if _zmq_pool is None:
        _zmq_pool = ZMQConnectionPool(
            max_connections=int(get_env("ZMQ_POOL_MAX_CONNECTIONS", "50")),
            max_idle_time=int(get_env("ZMQ_POOL_MAX_IDLE_TIME", "300")),
            health_check_interval=int(get_env("ZMQ_POOL_HEALTH_CHECK_INTERVAL", "60")),
            cleanup_interval=int(get_env("ZMQ_POOL_CLEANUP_INTERVAL", "120"))
        )
    return _zmq_pool

# Convenience functions for common socket types
def get_req_socket(endpoint: str, options: Optional[Dict[str, Any]] = None) -> PooledSocket:
    """Get REQ socket from pool"""
    pool = get_zmq_pool()
    config = SocketConfig(SocketType.REQ, endpoint, bind=False, options=options)
    return pool.get_socket(config)

def get_rep_socket(endpoint: str, options: Optional[Dict[str, Any]] = None) -> PooledSocket:
    """Get REP socket from pool"""
    pool = get_zmq_pool()
    config = SocketConfig(SocketType.REP, endpoint, bind=True, options=options)
    return pool.get_socket(config)

def get_pub_socket(endpoint: str, options: Optional[Dict[str, Any]] = None) -> PooledSocket:
    """Get PUB socket from pool"""
    pool = get_zmq_pool()
    config = SocketConfig(SocketType.PUB, endpoint, bind=True, options=options)
    return pool.get_socket(config)

def get_sub_socket(endpoint: str, options: Optional[Dict[str, Any]] = None) -> PooledSocket:
    """Get SUB socket from pool"""
    pool = get_zmq_pool()
    config = SocketConfig(SocketType.SUB, endpoint, bind=False, options=options)
    return pool.get_socket(config) 