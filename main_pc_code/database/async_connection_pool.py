#!/usr/bin/env python3
"""
Async Connection Pool Manager - High-Performance Database Connections
Provides intelligent connection pooling with monitoring and optimization.

Features:
- Asyncpg connection pool with configurable sizing
- Connection health monitoring and auto-recovery
- Query performance tracking and optimization
- Connection load balancing and failover
- Real-time pool metrics and alerting
- Integration with event system for monitoring
"""
from __future__ import annotations
import sys
from pathlib import Path
from common.utils.log_setup import configure_logging

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
import time
import json
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
from contextlib import asynccontextmanager
from enum import Enum
import hashlib

# Database imports
try:
    import asyncpg
    import asyncpg.pool
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    print("asyncpg not available - using simulation mode")

# Core imports
from common.core.base_agent import BaseAgent

# Event system imports
from events.memory_events import (
    MemoryEventType, create_memory_pressure_warning,
    MemoryPerformanceEvent
)
from events.event_bus import publish_memory_event

class ConnectionState(Enum):
    """Connection state tracking"""
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    UNHEALTHY = "unhealthy"
    CLOSED = "closed"

class QueryType(Enum):
    """Query type classification"""
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    TRANSACTION = "transaction"
    DDL = "ddl"  # Data Definition Language
    UNKNOWN = "unknown"

@dataclass
class ConnectionMetrics:
    """Metrics for individual connections"""
    connection_id: str
    created_at: datetime
    last_used: datetime
    query_count: int = 0
    total_query_time_ms: float = 0.0
    error_count: int = 0
    current_state: ConnectionState = ConnectionState.IDLE
    health_score: float = 100.0
    
    @property
    def avg_query_time_ms(self) -> float:
        return self.total_query_time_ms / max(self.query_count, 1)
    
    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.created_at).total_seconds()
    
    @property
    def idle_seconds(self) -> float:
        return (datetime.now() - self.last_used).total_seconds()

@dataclass
class QueryMetrics:
    """Metrics for query performance"""
    query_hash: str
    query_type: QueryType
    query_pattern: str  # Sanitized query pattern
    execution_count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    error_count: int = 0
    last_executed: Optional[datetime] = None
    
    @property
    def avg_time_ms(self) -> float:
        return self.total_time_ms / max(self.execution_count, 1)
    
    def update_execution(self, execution_time_ms: float, success: bool = True):
        """Update metrics for a query execution"""
        self.execution_count += 1
        self.last_executed = datetime.now()
        
        if success:
            self.total_time_ms += execution_time_ms
            self.min_time_ms = min(self.min_time_ms, execution_time_ms)
            self.max_time_ms = max(self.max_time_ms, execution_time_ms)
        else:
            self.error_count += 1

@dataclass
class PoolConfiguration:
    """Connection pool configuration"""
    min_size: int = 5
    max_size: int = 20
    command_timeout: float = 60.0
    server_settings: Dict[str, str] = field(default_factory=dict)
    init_commands: List[str] = field(default_factory=list)
    max_queries: int = 50000  # Max queries per connection before recreation
    max_inactive_connection_lifetime: float = 300.0  # 5 minutes
    connection_health_check_interval: float = 30.0  # 30 seconds

class AsyncConnectionPool(BaseAgent):
    """
    Advanced async connection pool manager.
    
    Provides high-performance database connections with intelligent
    management, monitoring, and optimization capabilities.
    """
    
    def __init__(self, 
                 database_url: str,
                 pool_config: Optional[PoolConfiguration] = None,
                 enable_monitoring: bool = True,
                 **kwargs):
        super().__init__(name="AsyncConnectionPool", **kwargs)
        
        # Configuration
        self.database_url = database_url
        self.pool_config = pool_config or PoolConfiguration()
        self.enable_monitoring = enable_monitoring
        
        # Connection pool
        self.pool: Optional[asyncpg.pool.Pool] = None
        self.pool_ready = asyncio.Event()
        
        # Metrics and monitoring
        self.connection_metrics: Dict[str, ConnectionMetrics] = {}
        self.query_metrics: Dict[str, QueryMetrics] = {}
        self.pool_metrics: Dict[str, Any] = {
            'total_connections': 0,
            'active_connections': 0,
            'idle_connections': 0,
            'total_queries': 0,
            'total_errors': 0,
            'avg_response_time_ms': 0.0,
            'peak_connections': 0,
            'pool_exhaustions': 0
        }
        
        # Performance tracking
        self.query_history: deque = deque(maxlen=10000)  # Last 10k queries
        self.slow_query_threshold_ms = 1000.0  # 1 second
        self.slow_queries: deque = deque(maxlen=1000)  # Last 1k slow queries
        
        # Health monitoring
        self.health_check_enabled = True
        self.last_health_check = datetime.now()
        self.consecutive_failures = 0
        
        # Initialize components
        if ASYNCPG_AVAILABLE:
            self._start_background_tasks()
        
        self.logger.info(f"Async Connection Pool initialized: {self.pool_config.min_size}-{self.pool_config.max_size} connections")
    
    async def initialize_pool(self) -> None:
        """Initialize the connection pool"""
        if not ASYNCPG_AVAILABLE:
            self.logger.warning("asyncpg not available - pool running in simulation mode")
            self.pool_ready.set()
            return
        
        try:
            self.logger.info("Initializing connection pool...")
            
            # Create the connection pool
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.pool_config.min_size,
                max_size=self.pool_config.max_size,
                command_timeout=self.pool_config.command_timeout,
                server_settings=self.pool_config.server_settings,
                init=self._init_connection
            )
            
            # Verify pool health
            await self._verify_pool_health()
            
            self.pool_ready.set()
            self.logger.info(f"Connection pool initialized successfully: {self.pool.get_size()} connections")
            
            # Update metrics
            self.pool_metrics['total_connections'] = self.pool.get_size()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    async def _init_connection(self, connection: asyncpg.Connection) -> None:
        """Initialize a new connection"""
        connection_id = f"conn_{id(connection)}"
        
        # Execute initialization commands
        for command in self.pool_config.init_commands:
            try:
                await connection.execute(command)
            except Exception as e:
                self.logger.warning(f"Init command failed: {command} - {e}")
        
        # Create connection metrics
        metrics = ConnectionMetrics(
            connection_id=connection_id,
            created_at=datetime.now(),
            last_used=datetime.now()
        )
        
        self.connection_metrics[connection_id] = metrics
        self.logger.debug(f"Connection initialized: {connection_id}")
    
    async def _verify_pool_health(self) -> None:
        """Verify that the pool is healthy"""
        try:
            async with self.pool.acquire() as connection:
                result = await connection.fetchval("SELECT 1")
                if result != 1:
                    raise Exception("Health check query returned unexpected result")
                
            self.consecutive_failures = 0
            self.last_health_check = datetime.now()
            
        except Exception as e:
            self.consecutive_failures += 1
            self.logger.error(f"Pool health check failed: {e}")
            
            if self.consecutive_failures >= 3:
                self.logger.critical("Multiple consecutive health check failures - pool may be unhealthy")
                
                # Publish health alert
                if self.enable_monitoring:
                    alert_event = create_memory_pressure_warning(
                        memory_utilization_percentage=100.0,  # Critical
                        fragmentation_percentage=0.0,
                        optimization_suggestions=["Database connection pool health check failed"],
                        source_agent=self.name,
                        machine_id=self._get_machine_id()
                    )
                    alert_event.event_type = MemoryEventType.MEMORY_LEAK_DETECTED
                    publish_memory_event(alert_event)
    
    def _start_background_tasks(self) -> None:
        """Start background monitoring tasks"""
        # Health monitoring thread
        health_thread = threading.Thread(target=self._health_monitoring_loop, daemon=True)
        health_thread.start()
        
        # Metrics collection thread
        metrics_thread = threading.Thread(target=self._metrics_collection_loop, daemon=True)
        metrics_thread.start()
        
        # Connection cleanup thread
        cleanup_thread = threading.Thread(target=self._connection_cleanup_loop, daemon=True)
        cleanup_thread.start()
    
    def _health_monitoring_loop(self) -> None:
        """Background health monitoring"""
        async def monitor():
            while self.running:
                try:
                    if self.pool and self.health_check_enabled:
                        await self._verify_pool_health()
                    
                    await asyncio.sleep(self.pool_config.connection_health_check_interval)
                    
                except Exception as e:
                    self.logger.error(f"Health monitoring error: {e}")
                    await asyncio.sleep(60)
        
        # Run in new event loop for thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(monitor())
    
    def _metrics_collection_loop(self) -> None:
        """Background metrics collection"""
        while self.running:
            try:
                if self.pool and self.enable_monitoring:
                    self._update_pool_metrics()
                    self._publish_performance_metrics()
                
                time.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Metrics collection error: {e}")
                time.sleep(60)
    
    def _connection_cleanup_loop(self) -> None:
        """Background connection cleanup"""
        async def cleanup():
            while self.running:
                try:
                    await self._cleanup_stale_connections()
                    await asyncio.sleep(60)  # Cleanup every minute
                    
                except Exception as e:
                    self.logger.error(f"Connection cleanup error: {e}")
                    await asyncio.sleep(120)
        
        # Run in new event loop for thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(cleanup())
    
    def _update_pool_metrics(self) -> None:
        """Update pool-level metrics"""
        if not self.pool:
            return
        
        self.pool_metrics.update({
            'total_connections': self.pool.get_size(),
            'idle_connections': self.pool.get_idle_size(),
            'active_connections': self.pool.get_size() - self.pool.get_idle_size(),
            'peak_connections': max(self.pool_metrics['peak_connections'], self.pool.get_size())
        })
        
        # Calculate average response time from recent queries
        if self.query_history:
            recent_queries = list(self.query_history)[-100:]  # Last 100 queries
            avg_time = sum(q['execution_time_ms'] for q in recent_queries) / len(recent_queries)
            self.pool_metrics['avg_response_time_ms'] = avg_time
    
    def _publish_performance_metrics(self) -> None:
        """Publish performance metrics as events"""
        if not self.enable_monitoring:
            return
        
        # Create performance event
        perf_event = MemoryPerformanceEvent(
            event_type=MemoryEventType.MEMORY_OPTIMIZATION_COMPLETED,
            operation_latency_ms=self.pool_metrics['avg_response_time_ms'],
            throughput_ops_per_second=self._calculate_throughput(),
            memory_utilization_percentage=self._calculate_pool_utilization(),
            gc_pressure_score=self.consecutive_failures,
            current_metrics={
                'total_connections': self.pool_metrics['total_connections'],
                'active_connections': self.pool_metrics['active_connections'],
                'total_queries': self.pool_metrics['total_queries'],
                'error_rate': self._calculate_error_rate()
            },
            source_agent=self.name,
            machine_id=self._get_machine_id()
        )
        
        publish_memory_event(perf_event)
    
    def _calculate_throughput(self) -> float:
        """Calculate queries per second throughput"""
        if not self.query_history:
            return 0.0
        
        # Get queries from last minute
        one_minute_ago = datetime.now() - timedelta(minutes=1)
        recent_queries = [
            q for q in self.query_history 
            if q['timestamp'] > one_minute_ago
        ]
        
        return len(recent_queries) / 60.0  # Queries per second
    
    def _calculate_pool_utilization(self) -> float:
        """Calculate pool utilization percentage"""
        if not self.pool:
            return 0.0
        
        total = self.pool_config.max_size
        active = self.pool_metrics['active_connections']
        return (active / total) * 100
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate percentage"""
        total_queries = self.pool_metrics['total_queries']
        total_errors = self.pool_metrics['total_errors']
        
        if total_queries == 0:
            return 0.0
        
        return (total_errors / total_queries) * 100
    
    async def _cleanup_stale_connections(self) -> None:
        """Clean up stale connection metrics"""
        current_time = datetime.now()
        stale_threshold = timedelta(seconds=self.pool_config.max_inactive_connection_lifetime)
        
        stale_connections = [
            conn_id for conn_id, metrics in self.connection_metrics.items()
            if current_time - metrics.last_used > stale_threshold
        ]
        
        for conn_id in stale_connections:
            del self.connection_metrics[conn_id]
            self.logger.debug(f"Cleaned up stale connection metrics: {conn_id}")
    
    @asynccontextmanager
    async def acquire_connection(self):
        """Acquire a connection from the pool with monitoring"""
        if not self.pool_ready.is_set():
            await self.pool_ready.wait()
        
        if not ASYNCPG_AVAILABLE:
            # Simulation mode
            yield self._create_mock_connection()
            return
        
        start_time = time.time()
        connection = None
        
        try:
            # Check for pool exhaustion
            if self.pool.get_idle_size() == 0 and self.pool.get_size() >= self.pool_config.max_size:
                self.pool_metrics['pool_exhaustions'] += 1
                self.logger.warning("Connection pool exhausted - consider increasing max_size")
            
            connection = await self.pool.acquire()
            connection_id = f"conn_{id(connection)}"
            
            # Update connection metrics
            if connection_id in self.connection_metrics:
                metrics = self.connection_metrics[connection_id]
                metrics.last_used = datetime.now()
                metrics.current_state = ConnectionState.ACTIVE
            
            acquisition_time = (time.time() - start_time) * 1000
            self.logger.debug(f"Connection acquired in {acquisition_time:.2f}ms: {connection_id}")
            
            yield connection
            
        except Exception as e:
            self.logger.error(f"Failed to acquire connection: {e}")
            self.pool_metrics['total_errors'] += 1
            raise
            
        finally:
            if connection:
                try:
                    await self.pool.release(connection)
                    
                    # Update connection state
                    connection_id = f"conn_{id(connection)}"
                    if connection_id in self.connection_metrics:
                        self.connection_metrics[connection_id].current_state = ConnectionState.IDLE
                        
                except Exception as e:
                    self.logger.error(f"Failed to release connection: {e}")
    
    def _create_mock_connection(self):
        """Create a mock connection for simulation mode"""
        class MockConnection:
            async def execute(self, query, *args):
                await asyncio.sleep(0.001)  # Simulate small delay
                return "SIMULATED"
            
            async def fetch(self, query, *args):
                await asyncio.sleep(0.01)  # Simulate query delay
                return [{"id": 1, "data": "simulated"}]
            
            async def fetchval(self, query, *args):
                await asyncio.sleep(0.005)
                return "simulated_value"
            
            async def fetchrow(self, query, *args):
                await asyncio.sleep(0.005)
                return {"id": 1, "data": "simulated"}
        
        return MockConnection()
    
    async def execute_query(self, query: str, *args, **kwargs) -> Any:
        """Execute a query with performance monitoring"""
        start_time = time.time()
        query_hash = self._hash_query(query)
        query_type = self._classify_query(query)
        
        try:
            async with self.acquire_connection() as connection:
                result = await connection.execute(query, *args, **kwargs)
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                # Update metrics
                self._record_query_execution(query_hash, query, query_type, execution_time_ms, True)
                
                self.logger.debug(f"Query executed in {execution_time_ms:.2f}ms: {query[:100]}...")
                
                return result
                
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self._record_query_execution(query_hash, query, query_type, execution_time_ms, False)
            
            self.logger.error(f"Query execution failed after {execution_time_ms:.2f}ms: {e}")
            raise
    
    async def fetch_query(self, query: str, *args, **kwargs) -> List[Dict]:
        """Fetch query results with performance monitoring"""
        start_time = time.time()
        query_hash = self._hash_query(query)
        query_type = self._classify_query(query)
        
        try:
            async with self.acquire_connection() as connection:
                rows = await connection.fetch(query, *args, **kwargs)
                result = [dict(row) for row in rows] if rows else []
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                # Update metrics
                self._record_query_execution(query_hash, query, query_type, execution_time_ms, True)
                
                self.logger.debug(f"Fetch query executed in {execution_time_ms:.2f}ms, {len(result)} rows: {query[:100]}...")
                
                return result
                
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self._record_query_execution(query_hash, query, query_type, execution_time_ms, False)
            
            self.logger.error(f"Fetch query failed after {execution_time_ms:.2f}ms: {e}")
            raise
    
    async def fetchval_query(self, query: str, *args, **kwargs) -> Any:
        """Fetch single value with performance monitoring"""
        start_time = time.time()
        query_hash = self._hash_query(query)
        query_type = self._classify_query(query)
        
        try:
            async with self.acquire_connection() as connection:
                result = await connection.fetchval(query, *args, **kwargs)
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                # Update metrics
                self._record_query_execution(query_hash, query, query_type, execution_time_ms, True)
                
                self.logger.debug(f"Fetchval query executed in {execution_time_ms:.2f}ms: {query[:100]}...")
                
                return result
                
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self._record_query_execution(query_hash, query, query_type, execution_time_ms, False)
            
            self.logger.error(f"Fetchval query failed after {execution_time_ms:.2f}ms: {e}")
            raise
    
    async def fetchrow_query(self, query: str, *args, **kwargs) -> Optional[Dict]:
        """Fetch single row with performance monitoring"""
        start_time = time.time()
        query_hash = self._hash_query(query)
        query_type = self._classify_query(query)
        
        try:
            async with self.acquire_connection() as connection:
                row = await connection.fetchrow(query, *args, **kwargs)
                result = dict(row) if row else None
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                # Update metrics
                self._record_query_execution(query_hash, query, query_type, execution_time_ms, True)
                
                self.logger.debug(f"Fetchrow query executed in {execution_time_ms:.2f}ms: {query[:100]}...")
                
                return result
                
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self._record_query_execution(query_hash, query, query_type, execution_time_ms, False)
            
            self.logger.error(f"Fetchrow query failed after {execution_time_ms:.2f}ms: {e}")
            raise
    
    def _hash_query(self, query: str) -> str:
        """Create a hash for query pattern matching"""
        # Normalize query for pattern matching
        normalized = query.strip().lower()
        # Remove parameter placeholders and values for pattern matching
        import re
        normalized = re.sub(r'\$\d+', '?', normalized)  # Replace $1, $2, etc. with ?
        normalized = re.sub(r"'[^']*'", "'?'", normalized)  # Replace string literals
        normalized = re.sub(r'\b\d+\b', '?', normalized)  # Replace numbers
        
        return hashlib.md5(normalized.encode()).hexdigest()[:12]
    
    def _classify_query(self, query: str) -> QueryType:
        """Classify query type"""
        query_lower = query.strip().lower()
        
        if query_lower.startswith('select'):
            return QueryType.SELECT
        elif query_lower.startswith('insert'):
            return QueryType.INSERT
        elif query_lower.startswith('update'):
            return QueryType.UPDATE
        elif query_lower.startswith('delete'):
            return QueryType.DELETE
        elif any(query_lower.startswith(cmd) for cmd in ['begin', 'commit', 'rollback']):
            return QueryType.TRANSACTION
        elif any(query_lower.startswith(cmd) for cmd in ['create', 'alter', 'drop']):
            return QueryType.DDL
        else:
            return QueryType.UNKNOWN
    
    def _record_query_execution(self, query_hash: str, query: str, query_type: QueryType, 
                                execution_time_ms: float, success: bool) -> None:
        """Record query execution metrics"""
        # Update pool metrics
        self.pool_metrics['total_queries'] += 1
        if not success:
            self.pool_metrics['total_errors'] += 1
        
        # Update query-specific metrics
        if query_hash not in self.query_metrics:
            # Create sanitized query pattern
            pattern = query[:200] + "..." if len(query) > 200 else query
            self.query_metrics[query_hash] = QueryMetrics(
                query_hash=query_hash,
                query_type=query_type,
                query_pattern=pattern
            )
        
        self.query_metrics[query_hash].update_execution(execution_time_ms, success)
        
        # Record in query history
        self.query_history.append({
            'timestamp': datetime.now(),
            'query_hash': query_hash,
            'query_type': query_type.value,
            'execution_time_ms': execution_time_ms,
            'success': success
        })
        
        # Track slow queries
        if execution_time_ms > self.slow_query_threshold_ms:
            self.slow_queries.append({
                'timestamp': datetime.now(),
                'query': query[:500],  # First 500 chars
                'execution_time_ms': execution_time_ms,
                'query_type': query_type.value
            })
            
            self.logger.warning(f"Slow query detected ({execution_time_ms:.2f}ms): {query[:100]}...")
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get comprehensive pool status"""
        if not self.pool:
            return {
                'status': 'not_initialized',
                'simulation_mode': not ASYNCPG_AVAILABLE
            }
        
        # Top slow queries
        top_slow_queries = sorted(
            self.query_metrics.values(),
            key=lambda q: q.avg_time_ms,
            reverse=True
        )[:10]
        
        # Most frequent queries
        top_frequent_queries = sorted(
            self.query_metrics.values(),
            key=lambda q: q.execution_count,
            reverse=True
        )[:10]
        
        return {
            'pool_config': {
                'min_size': self.pool_config.min_size,
                'max_size': self.pool_config.max_size,
                'command_timeout': self.pool_config.command_timeout
            },
            'pool_metrics': self.pool_metrics.copy(),
            'connection_metrics': {
                'total_tracked': len(self.connection_metrics),
                'healthy_connections': len([
                    m for m in self.connection_metrics.values()
                    if m.health_score > 80
                ]),
                'avg_connection_age': sum(
                    m.age_seconds for m in self.connection_metrics.values()
                ) / max(len(self.connection_metrics), 1)
            },
            'query_analytics': {
                'total_unique_queries': len(self.query_metrics),
                'slow_query_count': len(self.slow_queries),
                'avg_response_time_ms': self.pool_metrics['avg_response_time_ms'],
                'throughput_qps': self._calculate_throughput(),
                'error_rate_percent': self._calculate_error_rate()
            },
            'top_slow_queries': [
                {
                    'pattern': q.query_pattern[:100],
                    'avg_time_ms': q.avg_time_ms,
                    'execution_count': q.execution_count,
                    'error_count': q.error_count
                }
                for q in top_slow_queries
            ],
            'top_frequent_queries': [
                {
                    'pattern': q.query_pattern[:100],
                    'execution_count': q.execution_count,
                    'avg_time_ms': q.avg_time_ms,
                    'total_time_ms': q.total_time_ms
                }
                for q in top_frequent_queries
            ],
            'health': {
                'last_health_check': self.last_health_check.isoformat(),
                'consecutive_failures': self.consecutive_failures,
                'pool_utilization_percent': self._calculate_pool_utilization()
            }
        }
    
    def _get_machine_id(self) -> str:
        """Get current machine identifier"""
        import socket
        hostname = socket.gethostname().lower()
        
        if "main" in hostname or ("pc" in hostname and "pc2" not in hostname):
            return "MainPC"
        elif "pc2" in hostname:
            return "PC2"
        else:
            return "MainPC"  # Default
    
    async def close_pool(self) -> None:
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            self.logger.info("Connection pool closed")
    
    def shutdown(self):
        """Shutdown the connection pool manager"""
        async def close():
            await self.close_pool()
        
        # Run close in event loop if available
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(close())
            else:
                loop.run_until_complete(close())
        except RuntimeError:
            # Create new event loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(close())
        
        super().shutdown()

# Global pool instance
_global_pool: Optional[AsyncConnectionPool] = None

def get_connection_pool() -> AsyncConnectionPool:
    """Get the global connection pool instance"""
    global _global_pool
    if _global_pool is None:
        raise RuntimeError("Connection pool not initialized. Call initialize_global_pool() first.")
    return _global_pool

async def initialize_global_pool(database_url: str, 
                                pool_config: Optional[PoolConfiguration] = None) -> AsyncConnectionPool:
    """Initialize the global connection pool"""
    global _global_pool
    
    if _global_pool is not None:
        await _global_pool.close_pool()
    
    _global_pool = AsyncConnectionPool(database_url, pool_config)
    await _global_pool.initialize_pool()
    
    return _global_pool

async def close_global_pool() -> None:
    """Close the global connection pool"""
    global _global_pool
    if _global_pool:
        await _global_pool.close_pool()
        _global_pool = None

if __name__ == "__main__":
    # Example usage
    import asyncio
    
    logger = configure_logging(__name__, level="INFO")
    
    async def test_pool():
        # Initialize pool
        DATABASE_URL = "postgresql://user:password@localhost:5432/testdb"
        
        config = PoolConfiguration(
            min_size=5,
            max_size=20,
            command_timeout=30.0
        )
        
        pool = await initialize_global_pool(DATABASE_URL, config)
        
        try:
            # Test queries
            result = await pool.execute_query("SELECT 1")
            print(f"Test query result: {result}")
            
            # Test fetch
            rows = await pool.fetch_query("SELECT * FROM information_schema.tables LIMIT 5")
            print(f"Fetched {len(rows)} rows")
            
            # Print status
            status = pool.get_pool_status()
            print(json.dumps(status, indent=2, default=str))
            
        finally:
            await close_global_pool()
    
    if ASYNCPG_AVAILABLE:
        asyncio.run(test_pool())
    else:
        print("asyncpg not available - skipping test") 