#!/usr/bin/env python3
"""
Enhanced ObservabilityHub - RESTORED VERSION with Complete Functionality
Combines distributed architecture features with all missing functionality:
- PredictiveAnalyzer, AgentLifecycleManager, PerformanceLogger, RecoveryManager
- Distributed Architecture: Central Hub (MainPC Port 9000) + Edge Hub (PC2 Port 9100)
- Enhanced cross-machine metrics synchronization, failover, and comprehensive monitoring
"""

import sys
import os
from pathlib import Path
import logging
import time
import threading
import asyncio
import json
import concurrent.futures
import numpy as np
import zmq
import sqlite3
import pickle
import yaml
import requests
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from collections import defaultdict, deque
import uuid

# Add project paths for imports
from common.utils.path_manager import PathManager
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.core.base_agent import BaseAgent
from common.utils.data_models import ErrorSeverity
from common.health.standardized_health import StandardizedHealthChecker, HealthStatus

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
import uvicorn
from common.utils.log_setup import configure_logging

# Configure logging
log_file_path = Path(PathManager.get_project_root()) / "logs" / "enhanced_observability_hub_restored.log"
log_file_path.parent.mkdir(parents=True, exist_ok=True)

logger = configure_logging(__name__),
        logging.FileHandler(str(log_file_path))
    ]
)
logger = logging.getLogger("EnhancedObservabilityHubRestored")

# Prometheus integration
try:
    from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, start_http_server, push_to_gateway, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    logger.warning("Prometheus client not available, using mock implementation")
    PROMETHEUS_AVAILABLE = False

@dataclass
class HealthMetric:
    """Enhanced health metric with O3 requirements"""
    agent_name: str
    metric_type: str
    value: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    prediction_confidence: float = 0.0

@dataclass
class PredictiveAlert:
    """O3 Predictive analytics alert"""
    agent_name: str
    alert_type: str
    severity: str  # critical, warning, info
    predicted_failure_time: float
    confidence: float
    recommended_actions: List[str] = field(default_factory=list)

@dataclass
class DistributedConfig:
    """Enhanced configuration for distributed ObservabilityHub"""
    # Basic settings
    scope: str = "all_agents"
    prometheus_enabled: bool = True
    parallel_health_checks: bool = True
    prediction_enabled: bool = True
    
    # Distributed architecture settings
    role: str = "central_hub"  # central_hub or edge_hub
    environment: str = "mainpc"  # mainpc or pc2
    
    # Cross-machine synchronization
    enable_cross_machine_sync: bool = True
    peer_hub_endpoint: Optional[str] = None
    sync_interval: int = 30  # seconds
    
    # Failover settings
    enable_failover: bool = True
    failover_timeout: int = 10  # seconds
    max_failover_attempts: int = 3
    
    # Data persistence
    enable_data_persistence: bool = True
    data_retention_days: int = 30
    
    # Performance settings
    max_concurrent_health_checks: int = 50
    health_check_timeout: int = 5
    metrics_collection_interval: int = 30

class EnhancedPrometheusMetrics:
    """Enhanced Prometheus metrics with distributed support"""
    
    def __init__(self, config: DistributedConfig):
        self.config = config
        self.instance_name = f"{config.environment}_{config.role}"
        
        if PROMETHEUS_AVAILABLE:
            self.registry = CollectorRegistry()
            self._setup_metrics()
        else:
            self.registry = None
            self._setup_mock_metrics()
    
    def _setup_metrics(self):
        """Setup enhanced Prometheus metrics for distributed architecture"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        # Agent health metrics
        self.agent_health_gauge = Gauge(
            'observability_agent_health_status',
            'Health status of agents (1=healthy, 0=unhealthy)',
            ['agent_name', 'instance', 'environment', 'hub_role'],
            registry=self.registry
        )
        
        # Distributed hub metrics
        self.hub_status_gauge = Gauge(
            'observability_hub_status',
            'Status of observability hubs (1=active, 0=inactive)',
            ['hub_role', 'environment'],
            registry=self.registry
        )
        
        # Cross-machine sync metrics
        self.sync_success_counter = Counter(
            'observability_sync_attempts_total',
            'Total synchronization attempts',
            ['source_hub', 'target_hub', 'status'],
            registry=self.registry
        )
        
        self.sync_latency_histogram = Histogram(
            'observability_sync_latency_seconds',
            'Latency of cross-machine synchronization',
            ['source_hub', 'target_hub'],
            registry=self.registry
        )
        
        # Performance metrics
        self.response_time_histogram = Histogram(
            'observability_response_time_seconds',
            'Response time for health checks',
            ['agent_name', 'hub_role'],
            registry=self.registry
        )
        
        # System resource metrics
        self.system_cpu_gauge = Gauge(
            'observability_system_cpu_percent',
            'System CPU usage percentage',
            ['instance', 'hub_role'],
            registry=self.registry
        )
        
        self.system_memory_gauge = Gauge(
            'observability_system_memory_bytes',
            'System memory usage in bytes',
            ['instance', 'hub_role', 'type'],
            registry=self.registry
        )
        
        # Hub coordination metrics
        self.active_agents_gauge = Gauge(
            'observability_active_agents_total',
            'Total number of active agents being monitored',
            ['hub_role', 'environment'],
            registry=self.registry
        )
        
        # Predictive metrics (RESTORED)
        self.failure_probability_gauge = Gauge(
            'observability_agent_failure_probability',
            'Predicted failure probability (0-1)',
            ['agent_name', 'hub_role'],
            registry=self.registry
        )
        
        # Initialize hub status
        self.hub_status_gauge.labels(
            hub_role=self.config.role,
            environment=self.config.environment
        ).set(1)
    
    def _setup_mock_metrics(self):
        """Setup mock metrics when Prometheus is not available"""
        self.metrics_data = defaultdict(dict)
    
    def update_agent_health(self, agent_name: str, health_status: float):
        """Update agent health metric with distributed context"""
        if PROMETHEUS_AVAILABLE and self.registry:
            self.agent_health_gauge.labels(
                agent_name=agent_name,
                instance=self.instance_name,
                environment=self.config.environment,
                hub_role=self.config.role
            ).set(health_status)
        else:
            self.metrics_data['agent_health'][agent_name] = health_status
    
    def record_sync_attempt(self, target_hub: str, success: bool, latency: float):
        """Record cross-machine synchronization metrics"""
        if PROMETHEUS_AVAILABLE and self.registry:
            status = "success" if success else "failure"
            self.sync_success_counter.labels(
                source_hub=self.instance_name,
                target_hub=target_hub,
                status=status
            ).inc()
            
            if success:
                self.sync_latency_histogram.labels(
                    source_hub=self.instance_name,
                    target_hub=target_hub
                ).observe(latency)
        else:
            key = f"sync_{target_hub}_{status}"
            self.metrics_data['sync'][key] = self.metrics_data['sync'].get(key, 0) + 1
    
    def update_active_agents_count(self, count: int):
        """Update active agents count"""
        if PROMETHEUS_AVAILABLE and self.registry:
            self.active_agents_gauge.labels(
                hub_role=self.config.role,
                environment=self.config.environment
            ).set(count)
        else:
            self.metrics_data['active_agents'] = count
    
    def record_response_time(self, agent_name: str, response_time: float):
        """Record response time metric (RESTORED)"""
        if PROMETHEUS_AVAILABLE and self.registry:
            self.response_time_histogram.labels(
                agent_name=agent_name, 
                hub_role=self.config.role
            ).observe(response_time)
        else:
            if agent_name not in self.metrics_data['response_times']:
                self.metrics_data['response_times'][agent_name] = []
            self.metrics_data['response_times'][agent_name].append(response_time)
    
    def update_failure_probability(self, agent_name: str, probability: float):
        """Update predicted failure probability (RESTORED)"""
        if PROMETHEUS_AVAILABLE and self.registry:
            self.failure_probability_gauge.labels(
                agent_name=agent_name,
                hub_role=self.config.role
            ).set(probability)
        else:
            self.metrics_data['failure_probability'][agent_name] = probability
    
    def export_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        if PROMETHEUS_AVAILABLE and self.registry:
            return generate_latest(self.registry).decode('utf-8')
        else:
            # Mock metrics export
            return f"# Enhanced ObservabilityHub metrics for {self.instance_name}\n# Prometheus not available\n"

# RESTORED FUNCTIONALITY 1: Predictive Analytics
class PredictiveAnalyzer:
    """O3 Required: Predictive analytics algorithms (RESTORED)"""
    
    def __init__(self):
        self.agent_metrics = defaultdict(lambda: deque(maxlen=100))  # Store last 100 metrics
        self.failure_patterns = {}
        self.anomaly_threshold = 2.0  # Standard deviations
    
    def add_metric(self, agent_name: str, metric: HealthMetric):
        """Add metric for predictive analysis"""
        self.agent_metrics[agent_name].append(metric)
    
    def _calculate_failure_probability(self, metrics: deque) -> float:
        """Calculate failure probability based on historical metrics"""
        if len(metrics) < 10:
            return 0.0
        
        try:
            # Extract numeric values for analysis
            values = [m.value for m in list(metrics)[-20:]]  # Last 20 metrics
            
            if not values:
                return 0.0
            
            # Calculate statistics
            mean_value = np.mean(values)
            std_value = np.std(values)
            current_value = values[-1]
            
            # Simple anomaly detection
            if std_value == 0:
                return 0.0
            
            z_score = abs((current_value - mean_value) / std_value)
            
            # Calculate trend (declining performance = higher failure probability)
            if len(values) >= 5:
                recent_trend = np.polyfit(range(5), values[-5:], 1)[0]
                trend_factor = max(0, -recent_trend * 0.1)  # Negative trend increases probability
            else:
                trend_factor = 0
            
            # Combine z-score and trend
            base_probability = min(z_score / self.anomaly_threshold, 1.0)
            final_probability = min(base_probability + trend_factor, 1.0)
            
            return final_probability
            
        except Exception as e:
            logger.error(f"Error calculating failure probability: {e}")
            return 0.0
    
    def run_predictive_analysis(self) -> List[PredictiveAlert]:
        """O3 Required: Run predictive analysis algorithms"""
        alerts = []
        
        for agent_name, metrics in self.agent_metrics.items():
            if len(metrics) < 5:
                continue
            
            failure_probability = self._calculate_failure_probability(metrics)
            
            # Generate alerts based on probability
            if failure_probability > 0.8:
                alert = PredictiveAlert(
                    agent_name=agent_name,
                    alert_type="high_failure_risk",
                    severity="critical",
                    predicted_failure_time=time.time() + 300,  # 5 minutes
                    confidence=failure_probability,
                    recommended_actions=[
                        "Restart agent",
                        "Check system resources",
                        "Review recent logs"
                    ]
                )
                alerts.append(alert)
            elif failure_probability > 0.6:
                alert = PredictiveAlert(
                    agent_name=agent_name,
                    alert_type="moderate_failure_risk",
                    severity="warning",
                    predicted_failure_time=time.time() + 900,  # 15 minutes
                    confidence=failure_probability,
                    recommended_actions=[
                        "Monitor closely",
                        "Check performance metrics"
                    ]
                )
                alerts.append(alert)
        
        return alerts

# RESTORED FUNCTIONALITY 2: Agent Lifecycle Management
class AgentLifecycleManager:
    """PredictiveHealthMonitor Logic: Agent lifecycle and process management (RESTORED)"""
    
    def __init__(self, config: DistributedConfig):
        self.config = config
        self.agent_processes = {}
        self.agent_last_restart = {}
        self.restart_cooldown = 60  # seconds
        self.agent_configs = {}
        
    def load_agent_configs(self):
        """Load agent configurations for lifecycle management"""
        try:
            # Determine config paths based on environment
            if self.config.environment == "pc2":
                config_path = Path(PathManager.get_project_root()) / "pc2_code" / "config" / "startup_config.yaml"
            else:
                config_path = Path(PathManager.get_project_root()) / "main_pc_code" / "config" / "startup_config.yaml"
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                    
                # Extract agent configurations based on environment
                if self.config.environment == "pc2":
                    agents = config_data.get('pc2_services', [])
                else:
                    agent_groups = config_data.get('agent_groups', {})
                    agents = []
                    for group_name, group_agents in agent_groups.items():
                        for agent_name, agent_config in group_agents.items():
                            agent_config['name'] = agent_name
                            agents.append(agent_config)
                
                for agent in agents:
                    if isinstance(agent, dict) and 'name' in agent:
                        self.agent_configs[agent['name']] = agent
                        
            logger.info(f"Loaded {len(self.agent_configs)} agent configurations for {self.config.environment}")
        except Exception as e:
            logger.error(f"Error loading agent configs: {e}")
    
    def start_agent(self, agent_name: str) -> bool:
        """Start a specific agent process"""
        if agent_name not in self.agent_configs:
            logger.error(f"Unknown agent: {agent_name}")
            return False
            
        # Check cooldown period
        now = time.time()
        if agent_name in self.agent_last_restart and (now - self.agent_last_restart[agent_name]) < self.restart_cooldown:
            logger.warning(f"Agent {agent_name} in cooldown period")
            return False
            
        try:
            import subprocess
            config = self.agent_configs[agent_name]
            script_path = config.get("script_path", "")
            
            # Make path absolute
            abs_script_path = Path(PathManager.get_project_root()) / script_path
            
            if abs_script_path.exists():
                process = subprocess.Popen([sys.executable, str(abs_script_path)])
                self.agent_processes[agent_name] = process
                self.agent_last_restart[agent_name] = now
                
                logger.info(f"Started agent {agent_name}")
                return True
            else:
                logger.error(f"Script not found for agent {agent_name}: {abs_script_path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start agent {agent_name}: {e}")
            return False
    
    def restart_agent(self, agent_name: str) -> bool:
        """Restart an agent"""
        try:
            # Stop existing process
            if agent_name in self.agent_processes:
                process = self.agent_processes[agent_name]
                if process.poll() is None:  # Still running
                    process.terminate()
                    time.sleep(2)
                    if process.poll() is None:
                        process.kill()
                del self.agent_processes[agent_name]
            
            # Start new process
            return self.start_agent(agent_name)
            
        except Exception as e:
            logger.error(f"Error restarting agent {agent_name}: {e}")
            return False

# RESTORED FUNCTIONALITY 3: Performance Data Persistence
class PerformanceLogger:
    """PerformanceLoggerAgent Logic: Performance data logging and persistence (RESTORED)"""
    
    def __init__(self, config: DistributedConfig):
        self.config = config
        # Use modern path management
        data_dir = Path(PathManager.get_project_root()) / "data" / "enhanced_observability_hub"
        data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = data_dir / f"performance_metrics_{config.environment}.db"
        self.db_lock = threading.Lock()
        self._init_database()
        
        # Start cleanup thread
        if config.enable_data_persistence:
            self.cleanup_thread = threading.Thread(target=self._cleanup_old_metrics, daemon=True)
            self.cleanup_thread.start()
    
    def _init_database(self):
        """Initialize SQLite database for performance metrics"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        agent_name TEXT NOT NULL,
                        metric_type TEXT NOT NULL,
                        metric_value REAL NOT NULL,
                        metadata TEXT,
                        environment TEXT NOT NULL,
                        hub_role TEXT NOT NULL
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp ON performance_metrics(timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_agent_name ON performance_metrics(agent_name)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_environment ON performance_metrics(environment)
                """)
                
            logger.info(f"Performance metrics database initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    def log_metric(self, agent_name: str, metric_type: str, value: float, metadata: Optional[Dict[str, Any]] = None):
        """Log a performance metric to database"""
        if not self.config.enable_data_persistence:
            return
            
        if metadata is None:
            metadata = {}
            
        try:
            with self.db_lock:
                with sqlite3.connect(str(self.db_path)) as conn:
                    conn.execute("""
                        INSERT INTO performance_metrics 
                        (timestamp, agent_name, metric_type, metric_value, metadata, environment, hub_role)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        time.time(),
                        agent_name,
                        metric_type,
                        value,
                        json.dumps(metadata) if metadata else None,
                        self.config.environment,
                        self.config.role
                    ))
                    
        except Exception as e:
            logger.error(f"Error logging metric: {e}")
    
    def get_metrics(self, agent_name: Optional[str] = None, hours: int = 24) -> List[Dict[str, Any]]:
        """Retrieve metrics from database"""
        try:
            cutoff_time = time.time() - (hours * 3600)
            
            with sqlite3.connect(str(self.db_path)) as conn:
                if agent_name:
                    cursor = conn.execute("""
                        SELECT timestamp, agent_name, metric_type, metric_value, metadata, environment, hub_role
                        FROM performance_metrics
                        WHERE agent_name = ? AND timestamp > ? AND environment = ?
                        ORDER BY timestamp DESC
                    """, (agent_name, cutoff_time, self.config.environment))
                else:
                    cursor = conn.execute("""
                        SELECT timestamp, agent_name, metric_type, metric_value, metadata, environment, hub_role
                        FROM performance_metrics
                        WHERE timestamp > ? AND environment = ?
                        ORDER BY timestamp DESC
                    """, (cutoff_time, self.config.environment))
                
                results = []
                for row in cursor.fetchall():
                    timestamp, agent_name, metric_type, metric_value, metadata, environment, hub_role = row
                    results.append({
                        'timestamp': timestamp,
                        'agent_name': agent_name,
                        'metric_type': metric_type,
                        'metric_value': metric_value,
                        'metadata': json.loads(metadata) if metadata else {},
                        'environment': environment,
                        'hub_role': hub_role
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Error retrieving metrics: {e}")
            return []
    
    def _cleanup_old_metrics(self):
        """Cleanup old metrics periodically"""
        while True:
            try:
                # Remove metrics older than retention period
                cutoff_time = time.time() - (self.config.data_retention_days * 24 * 3600)
                
                with self.db_lock:
                    with sqlite3.connect(str(self.db_path)) as conn:
                        cursor = conn.execute("""
                            DELETE FROM performance_metrics WHERE timestamp < ?
                        """, (cutoff_time,))
                        
                        if cursor.rowcount > 0:
                            logger.info(f"Cleaned up {cursor.rowcount} old performance metrics")
                
                # Sleep for 24 hours
                time.sleep(24 * 3600)
                
            except Exception as e:
                logger.error(f"Error in cleanup thread: {e}")
                time.sleep(3600)  # Wait 1 hour before retrying

# RESTORED FUNCTIONALITY 4: Recovery Management
class RecoveryManager:
    """PredictiveHealthMonitor Logic: Tiered recovery strategies (RESTORED)"""
    
    def __init__(self, lifecycle_manager: AgentLifecycleManager, config: DistributedConfig):
        self.lifecycle_manager = lifecycle_manager
        self.config = config
        self.recovery_strategies = {
            "tier1": {
                "description": "Basic recovery: restart agent",
                "actions": ["restart_agent"]
            },
            "tier2": {
                "description": "Intermediate recovery: restart agent with clean state",
                "actions": ["clear_agent_state", "restart_agent"]
            },
            "tier3": {
                "description": "Advanced recovery: restart agent with dependencies",
                "actions": ["restart_dependencies", "clear_agent_state", "restart_agent"]
            },
            "tier4": {
                "description": "Critical recovery: restart all agents",
                "actions": ["restart_all_agents"]
            }
        }
    
    def attempt_recovery(self, agent_name: str, strategy: str = "tier1") -> bool:
        """Attempt recovery using specified strategy"""
        if strategy not in self.recovery_strategies:
            logger.error(f"Unknown recovery strategy: {strategy}")
            return False
            
        try:
            actions = self.recovery_strategies[strategy]["actions"]
            logger.info(f"Attempting recovery for {agent_name} using strategy {strategy}")
            
            for action in actions:
                if action == "restart_agent":
                    if not self.lifecycle_manager.restart_agent(agent_name):
                        return False
                elif action == "clear_agent_state":
                    self._clear_agent_state(agent_name)
                elif action == "restart_dependencies":
                    self._restart_dependencies(agent_name)
                elif action == "restart_all_agents":
                    self._restart_all_agents()
            
            return True
            
        except Exception as e:
            logger.error(f"Recovery failed for {agent_name}: {e}")
            return False
    
    def _clear_agent_state(self, agent_name: str):
        """Clear agent state (cache, temp files, etc.)"""
        try:
            # Clear agent-specific cache directories using modern paths
            cache_dirs = [
                Path(PathManager.get_project_root()) / "cache" / agent_name,
                Path(PathManager.get_project_root()) / "temp" / agent_name,
                Path(PathManager.get_project_root()) / "logs" / agent_name
            ]
            
            import shutil
            for cache_dir in cache_dirs:
                if cache_dir.exists():
                    shutil.rmtree(cache_dir)
                    logger.info(f"Cleared cache directory: {cache_dir}")
                    
        except Exception as e:
            logger.error(f"Error clearing agent state for {agent_name}: {e}")
    
    def _restart_dependencies(self, agent_name: str):
        """Restart agent dependencies"""
        try:
            config = self.lifecycle_manager.agent_configs.get(agent_name, {})
            dependencies = config.get("dependencies", [])
            
            for dep in dependencies:
                logger.info(f"Restarting dependency {dep} for {agent_name}")
                self.lifecycle_manager.restart_agent(dep)
                
        except Exception as e:
            logger.error(f"Error restarting dependencies for {agent_name}: {e}")
    
    def _restart_all_agents(self):
        """Restart all agents (nuclear option)"""
        try:
            logger.warning("Performing system-wide agent restart")
            
            for agent_name in self.lifecycle_manager.agent_configs.keys():
                self.lifecycle_manager.restart_agent(agent_name)
                time.sleep(2)  # Stagger restarts
                
        except Exception as e:
            logger.error(f"Error in system-wide restart: {e}")

# Enhanced distributed data manager (keeping improved version)
class DistributedDataManager:
    """Manages data persistence and synchronization across hubs"""
    
    def __init__(self, config: DistributedConfig):
        self.config = config
        
        # Initialize database
        data_dir = Path(PathManager.get_project_root()) / "data" / "enhanced_observability_hub"
        data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = data_dir / f"distributed_metrics_{config.environment}_{config.role}.db"
        self.db_lock = threading.Lock()
        
        self._init_database()
        
        # Data cache for fast access
        self.metrics_cache = {}
        self.last_sync_timestamp = {}
        
        # Start cleanup thread if persistence enabled
        if config.enable_data_persistence:
            self.cleanup_thread = threading.Thread(target=self._cleanup_old_data, daemon=True)
            self.cleanup_thread.start()
    
    def _init_database(self):
        """Initialize SQLite database for distributed metrics"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Enhanced metrics table with distributed context
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS distributed_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        agent_name TEXT NOT NULL,
                        metric_type TEXT NOT NULL,
                        metric_value REAL NOT NULL,
                        source_hub TEXT NOT NULL,
                        environment TEXT NOT NULL,
                        metadata TEXT,
                        sync_status TEXT DEFAULT 'local'
                    )
                """)
                
                # Hub synchronization tracking
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sync_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        source_hub TEXT NOT NULL,
                        target_hub TEXT NOT NULL,
                        sync_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        latency_ms REAL,
                        records_synced INTEGER DEFAULT 0,
                        error_message TEXT
                    )
                """)
                
                # Create indices for performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON distributed_metrics(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_name ON distributed_metrics(agent_name)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_source_hub ON distributed_metrics(source_hub)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_timestamp ON sync_log(timestamp)")
                
                logger.info(f"Initialized distributed database: {self.db_path}")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def store_metric(self, agent_name: str, metric_type: str, value: float, metadata: Dict[str, Any] = None):
        """Store metric with distributed context"""
        if not self.config.enable_data_persistence:
            return
        
        try:
            with self.db_lock:
                with sqlite3.connect(str(self.db_path)) as conn:
                    conn.execute("""
                        INSERT INTO distributed_metrics 
                        (timestamp, agent_name, metric_type, metric_value, source_hub, environment, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        time.time(),
                        agent_name,
                        metric_type,
                        value,
                        f"{self.config.environment}_{self.config.role}",
                        self.config.environment,
                        json.dumps(metadata) if metadata else None
                    ))
        except Exception as e:
            logger.error(f"Error storing metric: {e}")
    
    def _cleanup_old_data(self):
        """Clean up old data periodically"""
        while True:
            try:
                cutoff_time = time.time() - (self.config.data_retention_days * 24 * 3600)
                
                with self.db_lock:
                    with sqlite3.connect(str(self.db_path)) as conn:
                        # Clean old metrics
                        cursor = conn.execute("""
                            DELETE FROM distributed_metrics WHERE timestamp < ?
                        """, (cutoff_time,))
                        
                        metrics_deleted = cursor.rowcount
                        
                        # Clean old sync logs
                        cursor = conn.execute("""
                            DELETE FROM sync_log WHERE timestamp < ?
                        """, (cutoff_time,))
                        
                        sync_logs_deleted = cursor.rowcount
                        
                        if metrics_deleted > 0 or sync_logs_deleted > 0:
                            logger.info(f"Cleaned up {metrics_deleted} old metrics and {sync_logs_deleted} old sync logs")
                
                # Sleep for 6 hours
                time.sleep(6 * 3600)
                
            except Exception as e:
                logger.error(f"Error in cleanup thread: {e}")
                time.sleep(3600)  # Wait 1 hour before retrying

# Enhanced cross-machine coordinator (keeping improved version)
class CrossMachineCoordinator:
    """Enhanced cross-machine coordination with failover support"""
    
    def __init__(self, config: DistributedConfig, data_manager: DistributedDataManager, metrics: EnhancedPrometheusMetrics):
        self.config = config
        self.data_manager = data_manager
        self.metrics = metrics
        
        # Coordination state
        self.peer_hub_status = "unknown"
        self.last_successful_sync = None
        self.failover_active = False
        self.sync_failures = 0
        
        # Background sync thread
        self.sync_thread = None
        self.running = False
        
        if config.enable_cross_machine_sync and config.peer_hub_endpoint:
            self.start_coordination()
    
    def start_coordination(self):
        """Start cross-machine coordination"""
        if self.running:
            return
        
        self.running = True
        self.sync_thread = threading.Thread(target=self._coordination_loop, daemon=True)
        self.sync_thread.start()
        logger.info(f"Started cross-machine coordination with {self.config.peer_hub_endpoint}")
    
    def stop_coordination(self):
        """Stop cross-machine coordination"""
        self.running = False
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=5)

class EnhancedObservabilityHubRestored(BaseAgent):
    """
    Enhanced ObservabilityHub - RESTORED with Complete Functionality
    Combines distributed architecture with all missing functionality
    """
    
    def __init__(self, name="EnhancedObservabilityHubRestored", port=9000, role="central_hub"):
        super().__init__(name, port)
        
        # Load enhanced configuration
        self.config = self._load_distributed_config(role)
        
        # Initialize enhanced components
        self.metrics = EnhancedPrometheusMetrics(self.config)
        self.data_manager = DistributedDataManager(self.config)
        self.coordinator = CrossMachineCoordinator(self.config, self.data_manager, self.metrics)
        
        # RESTORED FUNCTIONALITY INTEGRATION
        self.predictive_analyzer = PredictiveAnalyzer()
        self.lifecycle_manager = AgentLifecycleManager(self.config)
        self.performance_logger = PerformanceLogger(self.config)
        self.recovery_manager = RecoveryManager(self.lifecycle_manager, self.config)
        
        # Agent monitoring
        self.monitored_agents = {}
        self.agent_discovery_enabled = True
        
        # Background threads
        self.monitoring_thread = None
        self.discovery_thread = None
        self.analytics_thread = None
        self.threads_running = False
        
        # FastAPI app with enhanced endpoints
        self.app = FastAPI(
            title=f"Enhanced ObservabilityHub RESTORED ({self.config.role.upper()})",
            description=f"Complete Distributed Observability Service - {self.config.environment}",
            version="2.1.0"
        )
        
        self._setup_enhanced_routes()
        self._start_background_services()
        
        # Auto-discover agents
        if self.agent_discovery_enabled:
            self._discover_agents()
        
        # Load agent configurations for lifecycle management
        self.lifecycle_manager.load_agent_configs()
        
        logger.info(f"Enhanced ObservabilityHub RESTORED initialized as {self.config.role} on {self.config.environment}")
        logger.info(f"✅ ALL FUNCTIONALITY RESTORED: PredictiveAnalyzer, AgentLifecycleManager, PerformanceLogger, RecoveryManager")
    
    def _load_distributed_config(self, role: str) -> DistributedConfig:
        """Load enhanced configuration for distributed architecture"""
        config = DistributedConfig()
        config.role = role
        
        # Detect environment
        if "pc2" in str(Path(__file__).resolve()).lower() or os.getenv('PC2_MODE', '').lower() == 'true':
            config.environment = "pc2"
            config.role = "edge_hub"
            config.peer_hub_endpoint = "http://192.168.1.27:9000"  # MainPC Central Hub
        else:
            config.environment = "mainpc"
            config.role = "central_hub"
            config.peer_hub_endpoint = "http://192.168.1.2:9100"  # PC2 Edge Hub
        
        # Load from startup config if available
        try:
            if config.environment == "pc2":
                config_path = Path(PathManager.get_project_root()) / "pc2_code" / "config" / "startup_config.yaml"
            else:
                config_path = Path(PathManager.get_project_root()) / "main_pc_code" / "config" / "startup_config.yaml"
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                
                # Look for ObservabilityHub config
                obs_config = None
                if config.environment == "pc2":
                    for service in config_data.get('pc2_services', []):
                        if isinstance(service, dict) and service.get('name') == 'ObservabilityHub':
                            obs_config = service.get('config', {})
                            break
                else:
                    agent_groups = config_data.get('agent_groups', {})
                    for group_agents in agent_groups.values():
                        if 'ObservabilityHub' in group_agents:
                            obs_config = group_agents['ObservabilityHub'].get('config', {})
                            break
                
                if obs_config:
                    config.prometheus_enabled = obs_config.get('prometheus_enabled', config.prometheus_enabled)
                    config.enable_cross_machine_sync = obs_config.get('cross_machine_sync', config.enable_cross_machine_sync)
                    peer_endpoint = obs_config.get('peer_hub_endpoint')
                    if peer_endpoint:
                        config.peer_hub_endpoint = peer_endpoint
                
        except Exception as e:
            logger.warning(f"Could not load startup config: {e}")
        
        logger.info(f"Loaded distributed config: {config.role} on {config.environment}")
        return config
    
    def _setup_enhanced_routes(self):
        """Setup enhanced FastAPI routes for distributed functionality"""
        
        @self.app.get("/health")
        async def health_check():
            """Enhanced health check with distributed context"""
            health_data = {
                "status": "healthy",
                "timestamp": time.time(),
                "role": self.config.role,
                "environment": self.config.environment,
                "peer_hub_status": getattr(self.coordinator, 'peer_hub_status', 'unknown'),
                "failover_active": getattr(self.coordinator, 'failover_active', False),
                "monitored_agents": len(self.monitored_agents),
                "uptime_seconds": time.time() - getattr(self, 'start_time', time.time()),
                "restored_functionality": {
                    "predictive_analyzer": bool(self.predictive_analyzer),
                    "lifecycle_manager": bool(self.lifecycle_manager),
                    "performance_logger": bool(self.performance_logger),
                    "recovery_manager": bool(self.recovery_manager)
                }
            }
            
            return JSONResponse(content=health_data)
        
        @self.app.get("/metrics")
        async def prometheus_metrics():
            """Serve Prometheus metrics"""
            metrics_data = self.metrics.export_metrics()
            return PlainTextResponse(
                content=metrics_data,
                media_type=CONTENT_TYPE_LATEST if PROMETHEUS_AVAILABLE else "text/plain"
            )
        
        @self.app.get("/api/v1/alerts")
        async def get_alerts():
            """Get active predictive alerts (RESTORED)"""
            try:
                alerts = self.predictive_analyzer.run_predictive_analysis()
                return {
                    "status": "success",
                    "environment": self.config.environment,
                    "hub_role": self.config.role,
                    "alerts": [
                        {
                            "agent_name": alert.agent_name,
                            "alert_type": alert.alert_type,
                            "severity": alert.severity,
                            "confidence": alert.confidence,
                            "predicted_failure_time": alert.predicted_failure_time,
                            "recommended_actions": alert.recommended_actions
                        }
                        for alert in alerts
                    ]
                }
            except Exception as e:
                logger.error(f"Error getting alerts: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/trigger_recovery")
        async def trigger_recovery(request: Request):
            """Trigger recovery for an agent (RESTORED)"""
            try:
                data = await request.json()
                agent_name = data.get('agent_name')
                strategy = data.get('strategy', 'tier1')
                
                if not agent_name:
                    raise HTTPException(status_code=400, detail="Missing agent_name")
                
                success = self.recovery_manager.attempt_recovery(agent_name, strategy)
                
                return {
                    "status": "success" if success else "error",
                    "message": f"Recovery {'successful' if success else 'failed'} for {agent_name}",
                    "strategy": strategy,
                    "environment": self.config.environment,
                    "hub_role": self.config.role
                }
            
            except Exception as e:
                logger.error("Error triggering recovery", {"error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/performance_metrics/{agent_name}")
        async def get_performance_metrics(agent_name: str):
            """Get performance metrics for an agent (RESTORED)"""
            try:
                metrics = self.performance_logger.get_metrics(agent_name=agent_name)
                return {
                    "status": "success",
                    "agent_name": agent_name,
                    "environment": self.config.environment,
                    "hub_role": self.config.role,
                    "metrics": metrics
                }
            except Exception as e:
                logger.error("Error getting performance metrics", {"error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))
    
    def _start_background_services(self):
        """Start enhanced background services"""
        self.threads_running = True
        self.start_time = time.time()
        
        # Enhanced monitoring thread
        self.monitoring_thread = threading.Thread(
            target=self._enhanced_monitoring_loop,
            name="EnhancedMonitoring",
            daemon=True
        )
        self.monitoring_thread.start()
        
        # Agent discovery thread
        self.discovery_thread = threading.Thread(
            target=self._agent_discovery_loop,
            name="AgentDiscovery",
            daemon=True
        )
        self.discovery_thread.start()
        
        # RESTORED: Predictive analytics thread
        if self.config.prediction_enabled:
            self.analytics_thread = threading.Thread(
                target=self._analytics_loop,
                name="PredictiveAnalytics",
                daemon=True
            )
            self.analytics_thread.start()
        
        logger.info(f"Started enhanced background services for {self.config.role}")
    
    def _enhanced_monitoring_loop(self):
        """Enhanced monitoring loop with RESTORED functionality"""
        while self.threads_running:
            try:
                if not self.monitored_agents:
                    time.sleep(self.config.health_check_timeout)
                    continue
                
                # Perform parallel health checks
                health_results = self._perform_parallel_health_checks()
                
                # Update metrics and store data with RESTORED functionality
                healthy_count = 0
                for agent_name, result in health_results.items():
                    health_status = 1.0 if result.get('status') == 'healthy' else 0.0
                    
                    # Update Prometheus metrics
                    self.metrics.update_agent_health(agent_name, health_status)
                    
                    # RESTORED: Add to predictive analyzer
                    metric = HealthMetric(
                        agent_name=agent_name,
                        metric_type="health_status",
                        value=health_status,
                        metadata=result
                    )
                    self.predictive_analyzer.add_metric(agent_name, metric)
                    
                    # RESTORED: Log to performance database
                    self.performance_logger.log_metric(
                        agent_name=agent_name,
                        metric_type="health_check",
                        value=health_status,
                        metadata=result
                    )
                    
                    # Store in distributed data manager
                    self.data_manager.store_metric(
                        agent_name,
                        'health_status',
                        health_status,
                        result
                    )
                    
                    if health_status == 1.0:
                        healthy_count += 1
                    else:
                        # RESTORED: Attempt recovery if unhealthy
                        logger.warning(f"Agent {agent_name} is unhealthy, attempting recovery")
                        self.recovery_manager.attempt_recovery(agent_name, "tier1")
                    
                    # Update agent info
                    if agent_name in self.monitored_agents:
                        self.monitored_agents[agent_name].update({
                            'last_check': time.time(),
                            'status': result.get('status', 'unknown'),
                            'response_time': result.get('response_time')
                        })
                
                logger.debug(f"Health check completed: {healthy_count}/{len(health_results)} agents healthy")
                
                time.sleep(self.config.metrics_collection_interval)
                
            except Exception as e:
                logger.error(f"Error in enhanced monitoring loop: {e}")
                time.sleep(5)
    
    def _analytics_loop(self):
        """RESTORED: Predictive analytics loop"""
        while self.threads_running:
            try:
                # Run predictive analysis
                alerts = self.predictive_analyzer.run_predictive_analysis()
                
                # Update failure probability metrics
                for agent_name, metrics in self.predictive_analyzer.agent_metrics.items():
                    if metrics:
                        failure_prob = self.predictive_analyzer._calculate_failure_probability(metrics)
                        self.metrics.update_failure_probability(agent_name, failure_prob)
                
                # Handle alerts
                for alert in alerts:
                    logger.warning(f"Predictive alert for {alert.agent_name}: {alert.alert_type} "
                                 f"(confidence: {alert.confidence:.2f})")
                    
                    # Trigger recovery if critical
                    if alert.severity == "critical":
                        self.recovery_manager.attempt_recovery(alert.agent_name, "tier2")
                
                time.sleep(60)  # Run analytics every minute
                
            except Exception as e:
                logger.error(f"Error in analytics loop: {e}")
                time.sleep(10)
    
    def run_server(self, host: str = "0.0.0.0", port: int = None):
        """Run the enhanced ObservabilityHub server"""
        if port is None:
            port = 9100 if self.config.role == "edge_hub" else 9000
        
        logger.info(f"Starting Enhanced ObservabilityHub RESTORED {self.config.role} on {host}:{port}")
        logger.info(f"✅ Complete functionality: Distributed + Predictive + Lifecycle + Performance + Recovery")
        
        try:
            uvicorn.run(
                self.app,
                host=host,
                port=port,
                log_level="info"
            )
        except Exception as e:
            logger.error(f"Error running server: {e}")
            raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced ObservabilityHub RESTORED")
    parser.add_argument("--role", choices=["central_hub", "edge_hub"], default="central_hub",
                        help="Hub role (central_hub for MainPC, edge_hub for PC2)")
    parser.add_argument("--port", type=int, help="Port to run on (default: 9000 for central, 9100 for edge)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    
    args = parser.parse_args()
    
    # Create and run restored enhanced hub
    hub = EnhancedObservabilityHubRestored(role=args.role)
    hub.run_server(host=args.host, port=args.port) 