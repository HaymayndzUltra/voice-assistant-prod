"""
WP-05 SQL Connection Pool
High-performance database connection pooling with automatic lifecycle management
"""

import threading
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from contextlib import contextmanager
import sqlite3
from queue import Queue, Empty

try:
    ASYNC_PG_AVAILABLE = True
except ImportError:
    ASYNC_PG_AVAILABLE = False

try:
    import psycopg2
    import psycopg2.pool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

from common.env_helpers import get_env

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Configuration for database connection"""
    database_type: str  # sqlite, postgresql, mysql
    host: str = get_env("BIND_ADDRESS", "0.0.0.0")
    port: int = 5432
    database: str = ""
    username: str = ""
    password: str = ""
    options: Dict[str, Any] = field(default_factory=dict)
    
    def get_connection_string(self) -> str:
        """Generate connection string for the database"""
        if self.database_type.lower() == "sqlite":
            return f"sqlite:///{self.database}"
        elif self.database_type.lower() == "postgresql":
            return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        else:
            raise ValueError(f"Unsupported database type: {self.database_type}")

@dataclass
class PooledConnection:
    """Wrapper for pooled database connection with metadata"""
    connection: Any
    config: DatabaseConfig
    created_at: float
    last_used: float
    usage_count: int = 0
    is_healthy: bool = True
    
    def __post_init__(self):
        self.last_used = time.time()

class SQLConnectionPool:
    """High-performance SQL connection pool with lifecycle management"""
    
    def __init__(self,
                 max_connections: int = 20,
                 min_connections: int = 2,
                 max_idle_time: int = 600,  # 10 minutes
                 health_check_interval: int = 120,
                 cleanup_interval: int = 180):
        
        self.max_connections = max_connections
        self.min_connections = min_connections
        self.max_idle_time = max_idle_time
        self.health_check_interval = health_check_interval
        self.cleanup_interval = cleanup_interval
        
        # Connection pools by config
        self._pools: Dict[str, Queue] = {}
        self._active_connections: Dict[str, List[PooledConnection]] = {}
        self._pool_locks: Dict[str, threading.Lock] = {}
        self._pool_configs: Dict[str, DatabaseConfig] = {}
        
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
            'error_count': 0,
            'query_count': 0
        }
        
        # Start background cleanup
        self._start_cleanup_thread()
        
        logger.info(f"SQLConnectionPool initialized - max_connections: {max_connections}")
    
    def _get_pool_key(self, config: DatabaseConfig) -> str:
        """Generate unique key for database configuration"""
        return f"{config.database_type}:{config.host}:{config.port}:{config.database}"
    
    def _ensure_pool_exists(self, pool_key: str, config: DatabaseConfig) -> None:
        """Ensure pool structures exist for the given key"""
        if pool_key not in self._pools:
            self._pools[pool_key] = Queue(maxsize=self.max_connections)
            self._active_connections[pool_key] = []
            self._pool_locks[pool_key] = threading.Lock()
            self._pool_configs[pool_key] = config
    
    def _create_connection(self, config: DatabaseConfig) -> Any:
        """Create new database connection"""
        try:
            if config.database_type.lower() == "sqlite":
                conn = sqlite3.connect(config.database, **config.options)
                conn.row_factory = sqlite3.Row  # Enable column access by name
                
            elif config.database_type.lower() == "postgresql" and PSYCOPG2_AVAILABLE:
                conn = psycopg2.connect(
                    host=config.host,
                    port=config.port,
                    database=config.database,
                    user=config.username,
                    password=config.password,
                    **config.options
                )
                
            else:
                raise ValueError(f"Unsupported database type or missing dependencies: {config.database_type}")
            
            self._metrics['total_connections'] += 1
            logger.debug(f"Created database connection: {config.database_type}")
            return conn
            
        except Exception as e:
            self._metrics['error_count'] += 1
            logger.error(f"Failed to create database connection: {e}")
            raise
    
    def get_connection(self, config: DatabaseConfig) -> PooledConnection:
        """Get connection from pool or create new one"""
        pool_key = self._get_pool_key(config)
        
        with self._lock:
            self._ensure_pool_exists(pool_key, config)
        
        with self._pool_locks[pool_key]:
            # Try to get from pool
            try:
                pooled_conn = self._pools[pool_key].get_nowait()
                pooled_conn.last_used = time.time()
                pooled_conn.usage_count += 1
                self._metrics['pool_hits'] += 1
                logger.debug(f"Retrieved connection from pool: {pool_key}")
                return pooled_conn
                
            except Empty:
                # Create new connection
                conn = self._create_connection(config)
                pooled_conn = PooledConnection(
                    connection=conn,
                    config=config,
                    created_at=time.time(),
                    last_used=time.time(),
                    usage_count=1
                )
                
                self._active_connections[pool_key].append(pooled_conn)
                self._metrics['active_connections'] += 1
                self._metrics['pool_misses'] += 1
                logger.debug(f"Created new connection: {pool_key}")
                return pooled_conn
    
    def return_connection(self, pooled_conn: PooledConnection) -> None:
        """Return connection to pool"""
        pool_key = self._get_pool_key(pooled_conn.config)
        
        if not pooled_conn.is_healthy:
            self._close_connection(pooled_conn)
            return
        
        with self._pool_locks.get(pool_key, threading.Lock()):
            try:
                # Update last used time
                pooled_conn.last_used = time.time()
                
                # Return to pool if not full
                self._pools[pool_key].put_nowait(pooled_conn)
                logger.debug(f"Returned connection to pool: {pool_key}")
                
            except Exception:
                # Pool is full, close the connection
                self._close_connection(pooled_conn)
    
    def _close_connection(self, pooled_conn: PooledConnection) -> None:
        """Close and cleanup connection"""
        try:
            pooled_conn.connection.close()
            
            # Remove from active connections
            pool_key = self._get_pool_key(pooled_conn.config)
            if pool_key in self._active_connections:
                try:
                    self._active_connections[pool_key].remove(pooled_conn)
                    self._metrics['active_connections'] -= 1
                except ValueError:
                    pass  # Connection not in list
            
            logger.debug(f"Closed connection: {pool_key}")
            
        except Exception as e:
            logger.warning(f"Error closing connection: {e}")
    
    @contextmanager
    def connection(self, config: DatabaseConfig):
        """Context manager for getting and returning connections"""
        pooled_conn = self.get_connection(config)
        try:
            yield pooled_conn.connection
        except Exception as e:
            # Mark connection as unhealthy on error
            pooled_conn.is_healthy = False
            logger.warning(f"Connection error, marking unhealthy: {e}")
            raise
        finally:
            self.return_connection(pooled_conn)
    
    def execute_query(self, config: DatabaseConfig, query: str, params: Optional[tuple] = None) -> List[Any]:
        """Execute query and return results"""
        self._metrics['query_count'] += 1
        
        with self.connection(config) as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if query.strip().lower().startswith(('select', 'show', 'describe')):
                    results = cursor.fetchall()
                    return results
                else:
                    conn.commit()
                    return []
                    
            finally:
                cursor.close()
    
    def execute_many(self, config: DatabaseConfig, query: str, params_list: List[tuple]) -> None:
        """Execute query with multiple parameter sets"""
        self._metrics['query_count'] += len(params_list)
        
        with self.connection(config) as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany(query, params_list)
                conn.commit()
            finally:
                cursor.close()
    
    def _test_connection_health(self, pooled_conn: PooledConnection) -> bool:
        """Test if connection is healthy"""
        try:
            if pooled_conn.config.database_type.lower() == "sqlite":
                cursor = pooled_conn.connection.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                return True
                
            elif pooled_conn.config.database_type.lower() == "postgresql":
                cursor = pooled_conn.connection.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                return True
                
        except Exception:
            return False
        
        return False
    
    def _cleanup_expired_connections(self) -> int:
        """Remove expired and idle connections"""
        current_time = time.time()
        cleanup_count = 0
        
        with self._lock:
            for pool_key in list(self._pools.keys()):
                expired_connections = []
                
                # Check pooled connections
                temp_queue = Queue()
                while not self._pools[pool_key].empty():
                    try:
                        pooled_conn = self._pools[pool_key].get_nowait()
                        
                        # Check if expired
                        if (current_time - pooled_conn.last_used) > self.max_idle_time:
                            expired_connections.append(pooled_conn)
                        else:
                            temp_queue.put(pooled_conn)
                    except Empty:
                        break
                
                # Put back non-expired connections
                while not temp_queue.empty():
                    self._pools[pool_key].put(temp_queue.get())
                
                # Close expired connections
                for conn in expired_connections:
                    self._close_connection(conn)
                    cleanup_count += 1
        
        if cleanup_count > 0:
            self._metrics['cleanup_count'] += cleanup_count
            logger.info(f"Cleaned up {cleanup_count} expired connections")
        
        return cleanup_count
    
    def _health_check_connections(self) -> int:
        """Perform health check on active connections"""
        unhealthy_count = 0
        
        with self._lock:
            for pool_key, connections in self._active_connections.items():
                for pooled_conn in connections[:]:  # Copy list to avoid modification during iteration
                    if not self._test_connection_health(pooled_conn):
                        pooled_conn.is_healthy = False
                        self._close_connection(pooled_conn)
                        unhealthy_count += 1
        
        if unhealthy_count > 0:
            logger.info(f"Removed {unhealthy_count} unhealthy connections")
        
        return unhealthy_count
    
    def _cleanup_loop(self):
        """Background cleanup loop"""
        last_health_check = 0
        
        while self._running:
            try:
                current_time = time.time()
                
                # Cleanup expired connections
                self._cleanup_expired_connections()
                
                # Health check periodically
                if (current_time - last_health_check) > self.health_check_interval:
                    self._health_check_connections()
                    last_health_check = current_time
                
                # Sleep until next cleanup
                time.sleep(self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"Error in SQL pool cleanup loop: {e}")
                time.sleep(10)  # Sleep on error
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread"""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                daemon=True,
                name="SQLPool-Cleanup"
            )
            self._cleanup_thread.start()
            logger.info("Started SQL pool cleanup thread")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        with self._lock:
            pool_stats = {}
            for pool_key, pool in self._pools.items():
                pool_stats[pool_key] = {
                    'pooled_connections': pool.qsize(),
                    'active_connections': len(self._active_connections.get(pool_key, []))
                }
            
            return {
                'metrics': self._metrics.copy(),
                'pools': pool_stats,
                'total_pools': len(self._pools),
                'cleanup_thread_alive': self._cleanup_thread and self._cleanup_thread.is_alive()
            }
    
    def close_all(self):
        """Close all connections and cleanup"""
        logger.info("Closing all SQL connections...")
        
        self._running = False
        
        with self._lock:
            # Close all pooled connections
            for pool_key, pool in self._pools.items():
                while not pool.empty():
                    try:
                        pooled_conn = pool.get_nowait()
                        self._close_connection(pooled_conn)
                    except Empty:
                        break
            
            # Close all active connections
            for connections in self._active_connections.values():
                for pooled_conn in connections[:]:
                    self._close_connection(pooled_conn)
            
            # Clear pools
            self._pools.clear()
            self._active_connections.clear()
            self._pool_locks.clear()
            self._pool_configs.clear()
        
        # Wait for cleanup thread
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        
        logger.info("SQL connection pool closed")


# Global SQL pool instance
_sql_pool: Optional[SQLConnectionPool] = None

def get_sql_pool() -> SQLConnectionPool:
    """Get global SQL connection pool"""
    global _sql_pool
    if _sql_pool is None:
        _sql_pool = SQLConnectionPool(
            max_connections=int(get_env("SQL_POOL_MAX_CONNECTIONS", "20")),
            min_connections=int(get_env("SQL_POOL_MIN_CONNECTIONS", "2")),
            max_idle_time=int(get_env("SQL_POOL_MAX_IDLE_TIME", "600")),
            health_check_interval=int(get_env("SQL_POOL_HEALTH_CHECK_INTERVAL", "120")),
            cleanup_interval=int(get_env("SQL_POOL_CLEANUP_INTERVAL", "180"))
        )
    return _sql_pool

# Convenience functions for common database configurations
def get_sqlite_config(database_path: str, **options) -> DatabaseConfig:
    """Get SQLite database configuration"""
    return DatabaseConfig(
        database_type="sqlite",
        database=database_path,
        options=options
    )

def get_postgresql_config(host: str = get_env("BIND_ADDRESS", "0.0.0.0"), 
                         port: int = 5432,
                         database: str = "",
                         username: str = "",
                         password: str = "",
                         **options) -> DatabaseConfig:
    """Get PostgreSQL database configuration"""
    return DatabaseConfig(
        database_type="postgresql",
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
        options=options
    ) 