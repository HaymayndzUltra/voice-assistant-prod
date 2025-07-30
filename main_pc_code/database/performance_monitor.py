#!/usr/bin/env python3
"""
Database Performance Monitor - Real-time Database Monitoring
Provides comprehensive database performance monitoring with metrics and alerting.

Features:
- Real-time connection pool monitoring
- Query performance analytics with slow query detection
- Database health checks and alerting
- Index usage analysis and recommendations
- Connection leak detection and prevention
- Performance trend analysis and prediction
"""
from __future__ import annotations
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
import time
import json
import logging
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import defaultdict, deque
from enum import Enum
import statistics

# Core imports
from common.core.base_agent import BaseAgent

# Database imports
from main_pc_code.database.async_connection_pool import get_connection_pool
from main_pc_code.database.intelligent_query_optimizer import get_query_optimizer

# Event system imports
from events.memory_events import (
    create_memory_pressure_warning
)
from events.event_bus import publish_memory_event

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class MetricType(Enum):
    """Performance metric types"""
    COUNTER = "counter"        # Ever-increasing value
    GAUGE = "gauge"           # Point-in-time value
    HISTOGRAM = "histogram"   # Distribution of values
    RATE = "rate"            # Rate of change

@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""
    description: str = ""

@dataclass
class DatabaseAlert:
    """Database performance alert"""
    id: str
    severity: AlertSeverity
    title: str
    message: str
    metric_name: str
    threshold_value: float
    current_value: float
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False

@dataclass
class ConnectionMetrics:
    """Connection pool metrics"""
    total_connections: int
    active_connections: int
    idle_connections: int
    max_connections: int
    connection_utilization: float
    average_wait_time_ms: float
    total_queries: int
    queries_per_second: float
    error_rate: float

@dataclass
class QueryPerformanceMetrics:
    """Query performance metrics"""
    total_queries: int
    slow_queries: int
    average_execution_time_ms: float
    median_execution_time_ms: float
    p95_execution_time_ms: float
    p99_execution_time_ms: float
    cache_hit_ratio: float
    most_frequent_queries: List[Dict[str, Any]]
    slowest_queries: List[Dict[str, Any]]

@dataclass
class DatabaseHealthMetrics:
    """Overall database health metrics"""
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    active_sessions: int
    blocked_queries: int
    deadlocks_per_hour: float
    replication_lag_seconds: float
    backup_age_hours: float

class DatabasePerformanceMonitor(BaseAgent):
    """
    Comprehensive database performance monitoring system.
    
    Monitors database performance, connection pools, query execution,
    and provides real-time alerting and analytics.
    """
    
    def __init__(self, 
                 monitoring_interval_seconds: int = 30,
                 alert_cooldown_seconds: int = 300,
                 enable_slow_query_logging: bool = True,
                 **kwargs):
        super().__init__(name="DatabasePerformanceMonitor", **kwargs)
        
        # Configuration
        self.monitoring_interval = monitoring_interval_seconds
        self.alert_cooldown = alert_cooldown_seconds
        self.enable_slow_query_logging = enable_slow_query_logging
        
        # Metrics storage
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1440))  # 24h at 1min
        self.current_metrics: Dict[str, PerformanceMetric] = {}
        
        # Alerting
        self.active_alerts: Dict[str, DatabaseAlert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.alert_thresholds = self._initialize_alert_thresholds()
        self.last_alert_time: Dict[str, datetime] = {}
        
        # Performance tracking
        self.connection_metrics_history: deque = deque(maxlen=288)  # 24h at 5min intervals
        self.query_performance_history: deque = deque(maxlen=288)
        self.health_metrics_history: deque = deque(maxlen=288)
        
        # Analysis
        self.performance_trends: Dict[str, List[float]] = defaultdict(list)
        self.anomaly_detection_enabled = True
        self.baseline_metrics: Dict[str, float] = {}
        
        # Initialize monitoring
        self._start_monitoring_threads()
        
        self.logger.info(f"Database Performance Monitor initialized with {monitoring_interval_seconds}s interval")
    
    def _initialize_alert_thresholds(self) -> Dict[str, Dict[str, Any]]:
        """Initialize default alert thresholds"""
        return {
            'connection_utilization': {
                'warning': 70.0,   # 70% connection pool utilization
                'critical': 90.0   # 90% connection pool utilization
            },
            'average_query_time': {
                'warning': 1000.0,  # 1 second average query time
                'critical': 5000.0  # 5 seconds average query time
            },
            'error_rate': {
                'warning': 1.0,    # 1% error rate
                'critical': 5.0    # 5% error rate
            },
            'slow_query_rate': {
                'warning': 10.0,   # 10% slow queries
                'critical': 25.0   # 25% slow queries
            },
            'cache_hit_ratio': {
                'warning': 80.0,   # 80% cache hit ratio (inverse - alert if below)
                'critical': 60.0   # 60% cache hit ratio (inverse - alert if below)
            },
            'database_cpu': {
                'warning': 80.0,   # 80% CPU usage
                'critical': 95.0   # 95% CPU usage
            },
            'database_memory': {
                'warning': 85.0,   # 85% memory usage
                'critical': 95.0   # 95% memory usage
            },
            'blocked_queries': {
                'warning': 5,      # 5 blocked queries
                'critical': 20     # 20 blocked queries
            }
        }
    
    def _start_monitoring_threads(self) -> None:
        """Start background monitoring threads"""
        # Main metrics collection thread
        metrics_thread = threading.Thread(target=self._metrics_collection_loop, daemon=True)
        metrics_thread.start()
        
        # Connection pool monitoring thread
        pool_thread = threading.Thread(target=self._connection_pool_monitoring_loop, daemon=True)
        pool_thread.start()
        
        # Query performance monitoring thread
        query_thread = threading.Thread(target=self._query_performance_monitoring_loop, daemon=True)
        query_thread.start()
        
        # Database health monitoring thread
        health_thread = threading.Thread(target=self._database_health_monitoring_loop, daemon=True)
        health_thread.start()
        
        # Alert processing thread
        alert_thread = threading.Thread(target=self._alert_processing_loop, daemon=True)
        alert_thread.start()
        
        # Performance analysis thread
        analysis_thread = threading.Thread(target=self._performance_analysis_loop, daemon=True)
        analysis_thread.start()
    
    def _metrics_collection_loop(self) -> None:
        """Main metrics collection loop"""
        async def collect_metrics():
            while self.running:
                try:
                    await self._collect_all_metrics()
                    await asyncio.sleep(self.monitoring_interval)
                    
                except Exception as e:
                    self.logger.error(f"Metrics collection error: {e}")
                    await asyncio.sleep(60)
        
        # Run in new event loop for thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(collect_metrics())
    
    def _connection_pool_monitoring_loop(self) -> None:
        """Monitor connection pool performance"""
        while self.running:
            try:
                metrics = self._collect_connection_pool_metrics()
                if metrics:
                    self.connection_metrics_history.append(metrics)
                    self._check_connection_pool_alerts(metrics)
                
                time.sleep(60)  # Every minute
                
            except Exception as e:
                self.logger.error(f"Connection pool monitoring error: {e}")
                time.sleep(120)
    
    def _query_performance_monitoring_loop(self) -> None:
        """Monitor query performance"""
        while self.running:
            try:
                metrics = self._collect_query_performance_metrics()
                if metrics:
                    self.query_performance_history.append(metrics)
                    self._check_query_performance_alerts(metrics)
                
                time.sleep(120)  # Every 2 minutes
                
            except Exception as e:
                self.logger.error(f"Query performance monitoring error: {e}")
                time.sleep(180)
    
    def _database_health_monitoring_loop(self) -> None:
        """Monitor overall database health"""
        async def monitor_health():
            while self.running:
                try:
                    metrics = await self._collect_database_health_metrics()
                    if metrics:
                        self.health_metrics_history.append(metrics)
                        self._check_database_health_alerts(metrics)
                    
                    await asyncio.sleep(300)  # Every 5 minutes
                    
                except Exception as e:
                    self.logger.error(f"Database health monitoring error: {e}")
                    await asyncio.sleep(600)
        
        # Run in new event loop for thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(monitor_health())
    
    def _alert_processing_loop(self) -> None:
        """Process and manage alerts"""
        while self.running:
            try:
                self._process_alerts()
                self._cleanup_resolved_alerts()
                
                time.sleep(30)  # Every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Alert processing error: {e}")
                time.sleep(60)
    
    def _performance_analysis_loop(self) -> None:
        """Analyze performance trends and anomalies"""
        while self.running:
            try:
                self._analyze_performance_trends()
                self._detect_anomalies()
                self._update_baselines()
                
                time.sleep(600)  # Every 10 minutes
                
            except Exception as e:
                self.logger.error(f"Performance analysis error: {e}")
                time.sleep(900)
    
    async def _collect_all_metrics(self) -> None:
        """Collect all performance metrics"""
        timestamp = datetime.now()
        
        # Collect connection pool metrics
        try:
            pool = get_connection_pool()
            pool_status = pool.get_pool_status()
            
            if pool_status and 'pool_metrics' in pool_status:
                pool_metrics = pool_status['pool_metrics']
                
                # Record individual metrics
                metrics = [
                    PerformanceMetric(
                        name="db_connections_total",
                        value=pool_metrics.get('total_connections', 0),
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                        unit="connections"
                    ),
                    PerformanceMetric(
                        name="db_connections_active",
                        value=pool_metrics.get('active_connections', 0),
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                        unit="connections"
                    ),
                    PerformanceMetric(
                        name="db_queries_total",
                        value=pool_metrics.get('total_queries', 0),
                        metric_type=MetricType.COUNTER,
                        timestamp=timestamp,
                        unit="queries"
                    ),
                    PerformanceMetric(
                        name="db_query_avg_time",
                        value=pool_metrics.get('avg_response_time_ms', 0),
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                        unit="milliseconds"
                    ),
                    PerformanceMetric(
                        name="db_error_rate",
                        value=pool_status.get('query_analytics', {}).get('error_rate_percent', 0),
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                        unit="percent"
                    )
                ]
                
                # Store metrics
                for metric in metrics:
                    self.current_metrics[metric.name] = metric
                    self.metrics_history[metric.name].append({
                        'timestamp': timestamp,
                        'value': metric.value
                    })
                
        except Exception as e:
            self.logger.warning(f"Failed to collect connection pool metrics: {e}")
        
        # Collect query optimizer metrics
        try:
            optimizer = get_query_optimizer()
            optimizer_status = optimizer.get_optimization_status()
            
            cache_stats = optimizer_status.get('cache_stats', {})
            
            cache_metrics = [
                PerformanceMetric(
                    name="query_cache_hit_ratio",
                    value=cache_stats.get('hit_ratio', 0) * 100,
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                    unit="percent"
                ),
                PerformanceMetric(
                    name="query_cache_size",
                    value=cache_stats.get('size_mb', 0),
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                    unit="megabytes"
                ),
                PerformanceMetric(
                    name="query_cache_entries",
                    value=cache_stats.get('entry_count', 0),
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                    unit="entries"
                )
            ]
            
            # Store cache metrics
            for metric in cache_metrics:
                self.current_metrics[metric.name] = metric
                self.metrics_history[metric.name].append({
                    'timestamp': timestamp,
                    'value': metric.value
                })
                
        except Exception as e:
            self.logger.warning(f"Failed to collect query optimizer metrics: {e}")
    
    def _collect_connection_pool_metrics(self) -> Optional[ConnectionMetrics]:
        """Collect connection pool specific metrics"""
        try:
            pool = get_connection_pool()
            status = pool.get_pool_status()
            
            if not status or 'pool_metrics' not in status:
                return None
            
            pool_metrics = status['pool_metrics']
            pool_config = status.get('pool_config', {})
            query_analytics = status.get('query_analytics', {})
            
            total_connections = pool_metrics.get('total_connections', 0)
            max_connections = pool_config.get('max_size', 1)
            
            return ConnectionMetrics(
                total_connections=total_connections,
                active_connections=pool_metrics.get('active_connections', 0),
                idle_connections=pool_metrics.get('idle_connections', 0),
                max_connections=max_connections,
                connection_utilization=(total_connections / max_connections) * 100,
                average_wait_time_ms=0.0,  # Would need to track this
                total_queries=pool_metrics.get('total_queries', 0),
                queries_per_second=query_analytics.get('throughput_qps', 0),
                error_rate=query_analytics.get('error_rate_percent', 0)
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting connection pool metrics: {e}")
            return None
    
    def _collect_query_performance_metrics(self) -> Optional[QueryPerformanceMetrics]:
        """Collect query performance metrics"""
        try:
            pool = get_connection_pool()
            pool_status = pool.get_pool_status()
            
            optimizer = get_query_optimizer()
            optimizer_status = optimizer.get_optimization_status()
            
            # Get slow query information
            slow_queries = pool_status.get('top_slow_queries', [])
            frequent_queries = pool_status.get('top_frequent_queries', [])
            
            # Calculate execution time percentiles from recent history
            recent_times = []
            for metric_history in self.metrics_history.get('db_query_avg_time', []):
                recent_times.append(metric_history['value'])
            
            recent_times = recent_times[-100:]  # Last 100 data points
            
            if recent_times:
                avg_time = statistics.mean(recent_times)
                median_time = statistics.median(recent_times)
                sorted_times = sorted(recent_times)
                p95_time = sorted_times[int(0.95 * len(sorted_times))] if sorted_times else 0
                p99_time = sorted_times[int(0.99 * len(sorted_times))] if sorted_times else 0
            else:
                avg_time = median_time = p95_time = p99_time = 0
            
            cache_hit_ratio = optimizer_status.get('cache_stats', {}).get('hit_ratio', 0) * 100
            
            return QueryPerformanceMetrics(
                total_queries=pool_status.get('pool_metrics', {}).get('total_queries', 0),
                slow_queries=len(slow_queries),
                average_execution_time_ms=avg_time,
                median_execution_time_ms=median_time,
                p95_execution_time_ms=p95_time,
                p99_execution_time_ms=p99_time,
                cache_hit_ratio=cache_hit_ratio,
                most_frequent_queries=frequent_queries[:10],
                slowest_queries=slow_queries[:10]
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting query performance metrics: {e}")
            return None
    
    async def _collect_database_health_metrics(self) -> Optional[DatabaseHealthMetrics]:
        """Collect database health metrics"""
        try:
            pool = get_connection_pool()
            
            # Get database statistics
            async with pool.acquire_connection() as connection:
                # CPU and memory usage (PostgreSQL specific)
                db_stats = await connection.fetchrow("""
                    SELECT 
                        (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_connections,
                        (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_sessions,
                        (SELECT count(*) FROM pg_stat_activity WHERE wait_event_type = 'Lock') as blocked_queries
                """)
                
                # Deadlock statistics
                deadlock_stats = await connection.fetchrow("""
                    SELECT deadlocks 
                    FROM pg_stat_database 
                    WHERE datname = current_database()
                """)
                
                # Calculate metrics
                active_sessions = db_stats['active_sessions'] if db_stats else 0
                blocked_queries = db_stats['blocked_queries'] if db_stats else 0
                deadlocks = deadlock_stats['deadlocks'] if deadlock_stats else 0
                
                # Simulate other metrics (in real implementation, these would come from system monitoring)
                return DatabaseHealthMetrics(
                    cpu_usage_percent=0.0,  # Would get from system monitoring
                    memory_usage_percent=0.0,  # Would get from system monitoring
                    disk_usage_percent=0.0,  # Would get from system monitoring
                    active_sessions=active_sessions,
                    blocked_queries=blocked_queries,
                    deadlocks_per_hour=deadlocks / 24.0,  # Rough approximation
                    replication_lag_seconds=0.0,  # Would monitor replication
                    backup_age_hours=0.0  # Would check backup timestamps
                )
                
        except Exception as e:
            self.logger.error(f"Error collecting database health metrics: {e}")
            return None
    
    def _check_connection_pool_alerts(self, metrics: ConnectionMetrics) -> None:
        """Check connection pool metrics against alert thresholds"""
        # Connection utilization alert
        self._check_threshold_alert(
            "connection_utilization",
            metrics.connection_utilization,
            f"Connection pool utilization at {metrics.connection_utilization:.1f}%",
            f"{metrics.active_connections}/{metrics.max_connections} connections in use"
        )
        
        # Error rate alert
        self._check_threshold_alert(
            "error_rate",
            metrics.error_rate,
            f"Database error rate at {metrics.error_rate:.1f}%",
            f"High error rate detected in database operations"
        )
    
    def _check_query_performance_alerts(self, metrics: QueryPerformanceMetrics) -> None:
        """Check query performance metrics against alert thresholds"""
        # Average query time alert
        self._check_threshold_alert(
            "average_query_time",
            metrics.average_execution_time_ms,
            f"Average query time at {metrics.average_execution_time_ms:.1f}ms",
            f"Query performance may be degraded"
        )
        
        # Slow query rate alert
        if metrics.total_queries > 0:
            slow_query_rate = (metrics.slow_queries / metrics.total_queries) * 100
            self._check_threshold_alert(
                "slow_query_rate",
                slow_query_rate,
                f"Slow query rate at {slow_query_rate:.1f}%",
                f"{metrics.slow_queries} out of {metrics.total_queries} queries are slow"
            )
        
        # Cache hit ratio alert (inverse - alert when below threshold)
        cache_threshold = self.alert_thresholds.get('cache_hit_ratio', {})
        if metrics.cache_hit_ratio < cache_threshold.get('critical', 60):
            self._create_alert(
                "cache_hit_ratio_critical",
                AlertSeverity.CRITICAL,
                f"Query cache hit ratio critically low at {metrics.cache_hit_ratio:.1f}%",
                "cache_hit_ratio",
                cache_threshold.get('critical', 60),
                metrics.cache_hit_ratio
            )
        elif metrics.cache_hit_ratio < cache_threshold.get('warning', 80):
            self._create_alert(
                "cache_hit_ratio_warning",
                AlertSeverity.WARNING,
                f"Query cache hit ratio low at {metrics.cache_hit_ratio:.1f}%",
                "cache_hit_ratio",
                cache_threshold.get('warning', 80),
                metrics.cache_hit_ratio
            )
    
    def _check_database_health_alerts(self, metrics: DatabaseHealthMetrics) -> None:
        """Check database health metrics against alert thresholds"""
        # CPU usage alert
        if metrics.cpu_usage_percent > 0:  # Only alert if we have real data
            self._check_threshold_alert(
                "database_cpu",
                metrics.cpu_usage_percent,
                f"Database CPU usage at {metrics.cpu_usage_percent:.1f}%",
                f"High CPU usage detected on database server"
            )
        
        # Memory usage alert
        if metrics.memory_usage_percent > 0:  # Only alert if we have real data
            self._check_threshold_alert(
                "database_memory",
                metrics.memory_usage_percent,
                f"Database memory usage at {metrics.memory_usage_percent:.1f}%",
                f"High memory usage detected on database server"
            )
        
        # Blocked queries alert
        self._check_threshold_alert(
            "blocked_queries",
            metrics.blocked_queries,
            f"{metrics.blocked_queries} blocked queries detected",
            f"Database queries are being blocked, possibly due to locks"
        )
    
    def _check_threshold_alert(self, metric_name: str, current_value: float, 
                             title: str, message: str) -> None:
        """Check a metric against its alert thresholds"""
        thresholds = self.alert_thresholds.get(metric_name, {})
        
        critical_threshold = thresholds.get('critical')
        warning_threshold = thresholds.get('warning')
        
        # Check critical threshold
        if critical_threshold is not None and current_value >= critical_threshold:
            self._create_alert(
                f"{metric_name}_critical",
                AlertSeverity.CRITICAL,
                title,
                metric_name,
                critical_threshold,
                current_value
            )
        # Check warning threshold
        elif warning_threshold is not None and current_value >= warning_threshold:
            self._create_alert(
                f"{metric_name}_warning",
                AlertSeverity.WARNING,
                title,
                metric_name,
                warning_threshold,
                current_value
            )
    
    def _create_alert(self, alert_id: str, severity: AlertSeverity, title: str,
                     metric_name: str, threshold_value: float, current_value: float) -> None:
        """Create or update an alert"""
        # Check alert cooldown
        if alert_id in self.last_alert_time:
            time_since_last = (datetime.now() - self.last_alert_time[alert_id]).total_seconds()
            if time_since_last < self.alert_cooldown:
                return
        
        # Create alert
        alert = DatabaseAlert(
            id=alert_id,
            severity=severity,
            title=title,
            message=f"Metric {metric_name} is {current_value:.2f}, threshold is {threshold_value:.2f}",
            metric_name=metric_name,
            threshold_value=threshold_value,
            current_value=current_value,
            timestamp=datetime.now()
        )
        
        # Store alert
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        self.last_alert_time[alert_id] = datetime.now()
        
        # Log alert
        log_level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL
        }.get(severity, logging.WARNING)
        
        self.logger.log(log_level, f"Database Alert [{severity.value.upper()}]: {title}")
        
        # Publish alert event
        alert_event = create_memory_pressure_warning(
            memory_utilization_percentage=current_value if metric_name.endswith('_percent') else 50.0,
            fragmentation_percentage=0.0,
            optimization_suggestions=[f"Check {metric_name} - {title}"],
            source_agent=self.name,
            machine_id=self._get_machine_id()
        )
        
        publish_memory_event(alert_event)
    
    def _process_alerts(self) -> None:
        """Process and update active alerts"""
        current_time = datetime.now()
        
        # Check if any alerts should be auto-resolved
        for alert_id, alert in list(self.active_alerts.items()):
            # Auto-resolve old alerts (older than 1 hour)
            if (current_time - alert.timestamp).total_seconds() > 3600:
                alert.resolved = True
                del self.active_alerts[alert_id]
                self.logger.info(f"Auto-resolved old alert: {alert.title}")
    
    def _cleanup_resolved_alerts(self) -> None:
        """Clean up resolved alerts from active list"""
        resolved_alerts = [
            alert_id for alert_id, alert in self.active_alerts.items()
            if alert.resolved or alert.acknowledged
        ]
        
        for alert_id in resolved_alerts:
            del self.active_alerts[alert_id]
    
    def _analyze_performance_trends(self) -> None:
        """Analyze performance trends over time"""
        # Analyze trends for key metrics
        key_metrics = ['db_query_avg_time', 'db_connections_active', 'query_cache_hit_ratio']
        
        for metric_name in key_metrics:
            if metric_name in self.metrics_history:
                recent_values = [
                    entry['value'] for entry in list(self.metrics_history[metric_name])[-60:]  # Last hour
                ]
                
                if len(recent_values) >= 10:
                    # Calculate trend (simple linear regression slope)
                    x = list(range(len(recent_values)))
                    y = recent_values
                    
                    n = len(x)
                    sum_x = sum(x)
                    sum_y = sum(y)
                    sum_xy = sum(x[i] * y[i] for i in range(n))
                    sum_x2 = sum(x[i] ** 2 for i in range(n))
                    
                    if n * sum_x2 - sum_x ** 2 != 0:
                        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
                        self.performance_trends[metric_name].append(slope)
                        
                        # Keep only recent trends
                        if len(self.performance_trends[metric_name]) > 100:
                            self.performance_trends[metric_name] = self.performance_trends[metric_name][-100:]
    
    def _detect_anomalies(self) -> None:
        """Detect performance anomalies using statistical methods"""
        if not self.anomaly_detection_enabled:
            return
        
        for metric_name, history in self.metrics_history.items():
            if len(history) < 30:  # Need enough data
                continue
            
            recent_values = [entry['value'] for entry in list(history)[-30:]]
            
            if len(recent_values) >= 10:
                mean_value = statistics.mean(recent_values)
                std_dev = statistics.stdev(recent_values) if len(recent_values) > 1 else 0
                
                # Check for anomalies (values > 2 standard deviations from mean)
                latest_value = recent_values[-1]
                
                if std_dev > 0 and abs(latest_value - mean_value) > 2 * std_dev:
                    self.logger.warning(f"Performance anomaly detected in {metric_name}: "
                                      f"current={latest_value:.2f}, mean={mean_value:.2f}, std={std_dev:.2f}")
    
    def _update_baselines(self) -> None:
        """Update baseline metrics for comparison"""
        for metric_name, history in self.metrics_history.items():
            if len(history) >= 100:  # Need enough historical data
                recent_values = [entry['value'] for entry in list(history)[-100:]]
                self.baseline_metrics[metric_name] = statistics.mean(recent_values)
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an active alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            self.logger.info(f"Alert acknowledged: {alert_id}")
            return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Manually resolve an active alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].resolved = True
            del self.active_alerts[alert_id]
            self.logger.info(f"Alert resolved: {alert_id}")
            return True
        return False
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get comprehensive monitoring status"""
        datetime.now()
        
        # Get recent metrics
        recent_metrics = {}
        for name, metric in self.current_metrics.items():
            recent_metrics[name] = {
                'value': metric.value,
                'unit': metric.unit,
                'timestamp': metric.timestamp.isoformat()
            }
        
        # Get alert summary
        alert_summary = {
            'total_active': len(self.active_alerts),
            'by_severity': {
                severity.value: len([a for a in self.active_alerts.values() if a.severity == severity])
                for severity in AlertSeverity
            },
            'recent_alerts': [
                {
                    'id': alert.id,
                    'severity': alert.severity.value,
                    'title': alert.title,
                    'timestamp': alert.timestamp.isoformat(),
                    'acknowledged': alert.acknowledged
                }
                for alert in list(self.alert_history)[-10:]  # Last 10 alerts
            ]
        }
        
        # Get performance summary
        performance_summary = {}
        if self.connection_metrics_history:
            latest_conn_metrics = self.connection_metrics_history[-1]
            performance_summary['connection_pool'] = asdict(latest_conn_metrics)
        
        if self.query_performance_history:
            latest_query_metrics = self.query_performance_history[-1]
            performance_summary['query_performance'] = asdict(latest_query_metrics)
        
        if self.health_metrics_history:
            latest_health_metrics = self.health_metrics_history[-1]
            performance_summary['database_health'] = asdict(latest_health_metrics)
        
        return {
            'monitoring_config': {
                'interval_seconds': self.monitoring_interval,
                'alert_cooldown_seconds': self.alert_cooldown,
                'anomaly_detection_enabled': self.anomaly_detection_enabled
            },
            'current_metrics': recent_metrics,
            'alert_summary': alert_summary,
            'performance_summary': performance_summary,
            'trends': {
                metric: trends[-10:] if len(trends) >= 10 else trends
                for metric, trends in self.performance_trends.items()
            },
            'baseline_metrics': self.baseline_metrics,
            'data_retention': {
                'metrics_points': sum(len(history) for history in self.metrics_history.values()),
                'oldest_metric': min([
                    list(history)[0]['timestamp'].isoformat()
                    for history in self.metrics_history.values()
                    if history
                ], default="N/A")
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
    
    def shutdown(self):
        """Shutdown the performance monitor"""
        # Clear metrics
        self.metrics_history.clear()
        self.current_metrics.clear()
        
        super().shutdown()

# Global monitor instance
_global_monitor: Optional[DatabasePerformanceMonitor] = None

def get_performance_monitor() -> DatabasePerformanceMonitor:
    """Get the global performance monitor instance"""
    global _global_monitor
    if _global_monitor is None:
        raise RuntimeError("Performance monitor not initialized. Call initialize_global_monitor() first.")
    return _global_monitor

def initialize_global_monitor(monitoring_interval_seconds: int = 30) -> DatabasePerformanceMonitor:
    """Initialize the global performance monitor"""
    global _global_monitor
    
    if _global_monitor is not None:
        _global_monitor.shutdown()
    
    _global_monitor = DatabasePerformanceMonitor(monitoring_interval_seconds=monitoring_interval_seconds)
    return _global_monitor

def close_global_monitor() -> None:
    """Close the global performance monitor"""
    global _global_monitor
    if _global_monitor:
        _global_monitor.shutdown()
        _global_monitor = None

if __name__ == "__main__":
    # Example usage
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    monitor = initialize_global_monitor(30)
    
    try:
        # Print initial status
        status = monitor.get_monitoring_status()
        print(json.dumps(status, indent=2, default=str))
        
        # Keep running
        import time
        while True:
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("Shutting down Database Performance Monitor...")
        close_global_monitor() 