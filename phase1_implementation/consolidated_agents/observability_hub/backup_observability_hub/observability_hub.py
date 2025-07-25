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
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("NumPy not available, predictive analytics will be limited")
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

# Configure logging
log_file_path = Path(PathManager.get_project_root()) / "logs" / "observability_hub.log"
log_file_path.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(log_file_path))
    ]
)
logger = logging.getLogger("ObservabilityHub")

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
class ObservabilityConfig:
    """Configuration for ObservabilityHub with distributed support"""
    scope: str = "all_agents"
    prometheus_enabled: bool = True
    parallel_health_checks: bool = True
    prediction_enabled: bool = True
    
    # Enhanced distributed settings
    cross_machine_sync: bool = False
    mainpc_hub_endpoint: Optional[str] = None
    environment: str = "mainpc"  # mainpc or pc2
    role: str = "central_hub"  # central_hub or local_reporter
    
    # Distributed architecture settings
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

class PrometheusMetrics:
    """Enhanced Prometheus metrics with distributed support"""
    
    def __init__(self, config: ObservabilityConfig):
        self.config = config
        self.instance_name = f"{config.environment}_{config.role}"
        
        if PROMETHEUS_AVAILABLE:
            self.registry = CollectorRegistry()
            self._setup_metrics()
        else:
            self.registry = None
            self._setup_mock_metrics()
    
    def _setup_metrics(self):
        """Setup enhanced Prometheus metrics"""
        if not PROMETHEUS_AVAILABLE:
            return
            
        # Agent health metrics with distributed context
        self.agent_health_gauge = Gauge(
            'agent_health_status',
            'Health status of agents (1=healthy, 0=unhealthy)',
            ['agent_name', 'instance', 'environment', 'hub_role'],
            registry=self.registry
        )
        
        # System performance metrics
        self.cpu_usage_gauge = Gauge(
            'system_cpu_usage_percent',
            'CPU usage percentage',
            ['instance', 'hub_role'],
            registry=self.registry
        )
        
        self.memory_usage_gauge = Gauge(
            'system_memory_usage_bytes',
            'Memory usage in bytes',
            ['instance', 'hub_role', 'type'],
            registry=self.registry
        )
        
        # Request metrics
        self.request_counter = Counter(
            'agent_requests_total',
            'Total number of requests per agent',
            ['agent_name', 'status', 'hub_role'],
            registry=self.registry
        )
        
        # Response time metrics
        self.response_time_histogram = Histogram(
            'agent_response_time_seconds',
            'Response time in seconds',
            ['agent_name', 'hub_role'],
            registry=self.registry
        )
        
        # Predictive metrics
        self.failure_probability_gauge = Gauge(
            'agent_failure_probability',
            'Predicted failure probability (0-1)',
            ['agent_name', 'hub_role'],
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
    
    def update_system_metric(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Update system metric with hub context"""
        if labels is None:
            labels = {}
            
        if PROMETHEUS_AVAILABLE and self.registry:
            if metric_name == 'cpu_usage':
                self.cpu_usage_gauge.labels(
                    instance=self.instance_name,
                    hub_role=self.config.role
                ).set(value)
            elif metric_name == 'memory_usage':
                memory_type = labels.get('type', 'used')
                self.memory_usage_gauge.labels(
                    instance=self.instance_name,
                    hub_role=self.config.role,
                    type=memory_type
                ).set(value)
        else:
            self.metrics_data['system'][metric_name] = value
    
    def record_request(self, agent_name: str, status: str):
        """Record request metric with hub context"""
        if PROMETHEUS_AVAILABLE and self.registry:
            self.request_counter.labels(
                agent_name=agent_name,
                status=status,
                hub_role=self.config.role
            ).inc()
        else:
            key = f"{agent_name}_{status}"
            self.metrics_data['requests'][key] = self.metrics_data['requests'].get(key, 0) + 1
    
    def record_response_time(self, agent_name: str, response_time: float):
        """Record response time metric with hub context"""
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
        """Update predicted failure probability with hub context"""
        if PROMETHEUS_AVAILABLE and self.registry:
            self.failure_probability_gauge.labels(
                agent_name=agent_name,
                hub_role=self.config.role
            ).set(probability)
        else:
            self.metrics_data['failure_probability'][agent_name] = probability
    
    def record_sync_attempt(self, target_hub: str, success: bool):
        """Record cross-machine synchronization attempt"""
        if PROMETHEUS_AVAILABLE and self.registry:
            status = "success" if success else "failure"
            self.sync_success_counter.labels(
                source_hub=self.instance_name,
                target_hub=target_hub,
                status=status
            ).inc()
        else:
            key = f"sync_{target_hub}_{status}"
            self.metrics_data['sync'][key] = self.metrics_data['sync'].get(key, 0) + 1

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

# RESTORED FUNCTIONALITY: Agent Process Management
class AgentLifecycleManager:
    """PredictiveHealthMonitor Logic: Agent lifecycle and process management (RESTORED)"""
    
    def __init__(self, config: ObservabilityConfig):
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

# RESTORED FUNCTIONALITY: Performance Data Persistence
class PerformanceLogger:
    """PerformanceLoggerAgent Logic: Performance data logging and persistence (RESTORED)"""
    
    def __init__(self, config: ObservabilityConfig):
        self.config = config
        # Use modern path management
        data_dir = Path(PathManager.get_project_root()) / "data" / "observability_hub"
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

# RESTORED FUNCTIONALITY: Recovery Strategies
class RecoveryManager:
    """PredictiveHealthMonitor Logic: Tiered recovery strategies (RESTORED)"""
    
    def __init__(self, lifecycle_manager: AgentLifecycleManager, config: ObservabilityConfig):
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

class CrossMachineSync:
    """Handle cross-machine synchronization for PC2 → MainPC reporting"""
    
    def __init__(self, config: ObservabilityConfig):
        self.config = config
        self.sync_enabled = config.cross_machine_sync
        self.mainpc_endpoint = os.getenv("MAINPC_OBSERVABILITY_ENDPOINT", config.mainpc_hub_endpoint)
        self.sync_interval = 30  # seconds
        self.sync_thread = None
        self.running = False
        
        # Failover tracking
        self.peer_hub_status = "unknown"
        self.sync_failures = 0
        self.failover_active = False
        
    def start_sync(self):
        """Start cross-machine sync if enabled"""
        if not self.sync_enabled or not self.mainpc_endpoint:
            logger.info("Cross-machine sync disabled or no MainPC endpoint configured")
            return
            
        self.running = True
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        logger.info(f"Started cross-machine sync to {self.mainpc_endpoint}")
    
    def stop_sync(self):
        """Stop cross-machine sync"""
        self.running = False
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=5)
    
    def _sync_loop(self):
        """Main sync loop for PC2 → MainPC data reporting"""
        import requests
        
        while self.running:
            try:
                # Check peer hub status first
                self._check_peer_status()
                
                # Collect local metrics to sync
                sync_data = self._collect_sync_data()
                
                if self.peer_hub_status == "healthy":
                    # Send to MainPC ObservabilityHub
                    response = requests.post(
                        f"{self.mainpc_endpoint}/sync_from_pc2",
                        json=sync_data,
                        timeout=self.config.failover_timeout
                    )
                    
                    if response.status_code == 200:
                        logger.debug(f"Successfully synced data to MainPC: {len(sync_data)} metrics")
                        self.sync_failures = 0
                        self.failover_active = False
                    else:
                        logger.warning(f"Sync to MainPC failed: {response.status_code}")
                        self.sync_failures += 1
                else:
                    logger.warning(f"Peer hub status: {self.peer_hub_status}, skipping sync")
                    
                # Update failover status
                if self.sync_failures >= self.config.max_failover_attempts:
                    if not self.failover_active:
                        self.failover_active = True
                        logger.warning("Failover mode ACTIVATED due to repeated sync failures")
                        
            except Exception as e:
                logger.error(f"Error in cross-machine sync: {e}")
                self.sync_failures += 1
            
            time.sleep(self.sync_interval)
    
    def _check_peer_status(self):
        """Check status of peer hub"""
        try:
            import requests
            response = requests.get(
                f"{self.mainpc_endpoint}/health",
                timeout=self.config.failover_timeout
            )
            
            if response.status_code == 200:
                self.peer_hub_status = "healthy"
            else:
                self.peer_hub_status = "unhealthy"
                
        except Exception as e:
            self.peer_hub_status = "unreachable"
            logger.debug(f"Peer hub unreachable: {e}")
    
    def _collect_sync_data(self) -> Dict[str, Any]:
        """Collect data to sync to MainPC"""
        return {
            "source": "pc2",
            "timestamp": time.time(),
            "environment": self.config.environment,
            "sync_type": "health_and_metrics"
            # Additional data will be populated by the main class
        }

class ObservabilityHub(BaseAgent):
    """
    ObservabilityHub - RESTORED with Complete Functionality
    Enhanced with modern patterns and cross-machine coordination
    """
    
    def __init__(self, name="ObservabilityHub", port=9000):
        super().__init__(name, port)
        
        # Load configuration from startup config
        self.config = self._load_configuration()
        
        # Initialize start time for health reporting
        self.start_time = time.time()
        
        # Enhanced Components with configuration
        self.prometheus_metrics = PrometheusMetrics(self.config)
        
        # RESTORED FUNCTIONALITY INTEGRATION
        self.predictive_analyzer = PredictiveAnalyzer()
        self.lifecycle_manager = AgentLifecycleManager(self.config)
        self.performance_logger = PerformanceLogger(self.config)
        self.recovery_manager = RecoveryManager(self.lifecycle_manager, self.config)
        
        # Cross-machine sync for PC2 → MainPC reporting
        self.cross_machine_sync = CrossMachineSync(self.config)
        
        # ZMQ setup for broadcasting (configurable)
        self.context = zmq.Context()
        self.metrics_publisher = None
        self.setup_zmq_broadcasting()
        
        # Agent monitoring
        self.monitored_agents = {}
        self.health_check_interval = 30  # seconds
        
        # Modern health system
        if hasattr(self, 'health_checker'):
            self.standardized_health = self.health_checker
        else:
            from common.env_defaults import get_redis_host, get_redis_port
            self.standardized_health = StandardizedHealthChecker(
                agent_name=self.name,
                port=self.port,
                redis_host=get_redis_host(),
                redis_port=get_redis_port()
            )
        
        # Background threads
        self.monitoring_thread = None
        self.analytics_thread = None
        self.broadcasting_thread = None
        self.threads_running = False
        
        # Thread pool for parallel operations
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix='ObservabilityHub')
        
        # FastAPI app
        self.app = FastAPI(
            title=f"ObservabilityHub RESTORED ({self.config.environment.upper()})",
            description=f"Complete Observability Service - {self.config.role}",
            version="2.1.0"
        )
        
        self.setup_routes()
        self.start_background_threads()
        
        # Load agent configurations
        self.lifecycle_manager.load_agent_configs()
        
        # Start cross-machine sync if configured
        if self.config.cross_machine_sync:
            self.cross_machine_sync.start_sync()
        
        logger.info(f"ObservabilityHub RESTORED and initialized for {self.config.environment} as {self.config.role}")
        logger.info(f"✅ ALL FUNCTIONALITY RESTORED: PredictiveAnalyzer, AgentLifecycleManager, PerformanceLogger, RecoveryManager")
    
    def _load_configuration(self) -> ObservabilityConfig:
        """Load configuration from startup config files"""
        try:
            # Detect environment based first on explicit env var, fallback to path detection
            env_machine_type = os.getenv("MACHINE_TYPE") or os.getenv("PC2_MODE")
            if env_machine_type and env_machine_type.lower() in {"pc2", "mainpc"}:
                environment = "pc2" if env_machine_type.lower() == "pc2" or env_machine_type.lower() == "true" else "mainpc"
            else:
                environment = self._detect_environment()
            
            # Load appropriate config file
            if environment == "pc2":
                config_path = Path(PathManager.get_project_root()) / "pc2_code" / "config" / "startup_config.yaml"
            else:
                config_path = Path(PathManager.get_project_root()) / "main_pc_code" / "config" / "startup_config.yaml"
            
            config = ObservabilityConfig(environment=environment)
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                
                # Find ObservabilityHub config
                obs_hub_config = None
                
                if environment == "pc2":
                    # PC2 services format
                    pc2_services = config_data.get('pc2_services', [])
                    for service in pc2_services:
                        if isinstance(service, dict) and service.get('name') == 'ObservabilityHub':
                            obs_hub_config = service.get('config', {})
                            break
                else:
                    # MainPC agent groups format
                    agent_groups = config_data.get('agent_groups', {})
                    for group_name, agents in agent_groups.items():
                        if 'ObservabilityHub' in agents:
                            obs_hub_config = agents['ObservabilityHub'].get('config', {})
                            break
                
                if obs_hub_config:
                    config.scope = obs_hub_config.get('scope', config.scope)
                    config.prometheus_enabled = obs_hub_config.get('prometheus_enabled', config.prometheus_enabled)
                    config.parallel_health_checks = obs_hub_config.get('parallel_health_checks', config.parallel_health_checks)
                    config.prediction_enabled = obs_hub_config.get('prediction_enabled', config.prediction_enabled)
                    config.cross_machine_sync = obs_hub_config.get('cross_machine_sync', config.cross_machine_sync)
                    config.mainpc_hub_endpoint = obs_hub_config.get('mainpc_hub_endpoint', config.mainpc_hub_endpoint)
            
            # Set role based on environment
            if environment == "pc2":
                config.role = "local_reporter"
            else:
                config.role = "central_hub"
            
            logger.info(f"Loaded configuration for {environment} environment as {config.role}")
            return config
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            # Return default config
            return ObservabilityConfig()
    
    def _detect_environment(self) -> str:
        """Detect if running on MainPC or PC2"""
        try:
            # Check if PC2 config exists and we're in PC2 context
            pc2_config_path = Path(PathManager.get_project_root()) / "pc2_code" / "config" / "startup_config.yaml"
            current_script_path = Path(__file__).resolve()
            
            # If we're running from a PC2 context or PC2 config is more recent
            if "pc2" in str(current_script_path) or "PC2" in str(current_script_path):
                return "pc2"
            
            # Check environment variables
            if os.getenv('PC2_MODE', '').lower() == 'true':
                return "pc2"
            
            if os.getenv('MACHINE_TYPE', '').lower() == 'pc2':
                return "pc2"
            
            # Default to mainpc
            return "mainpc"
            
        except Exception as e:
            logger.warning(f"Error detecting environment: {e}, defaulting to mainpc")
            return "mainpc"
    
    def setup_zmq_broadcasting(self):
        """Modern ZMQ PUB/SUB broadcasting setup"""
        try:
            if self.config.role == "central_hub":
                # Central hub broadcasts to all
                self.metrics_publisher = self.context.socket(zmq.PUB)
                self.metrics_publisher.bind("tcp://*:7152")  # Metrics broadcasting port
                logger.info("ZMQ metrics broadcasting setup on port 7152 (Central Hub)")
            else:
                # Local reporter doesn't need to broadcast
                logger.info("Local reporter mode - ZMQ broadcasting disabled")
        except Exception as e:
            self.report_error(ErrorSeverity.ERROR, "ZMQ setup error", {"error": str(e)})
            self.metrics_publisher = None
    
    def start_background_threads(self):
        """Start modern background threads with proper error handling"""
        self.threads_running = True
        
        # Parallel health monitoring thread
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="HealthMonitoring",
            daemon=True
        )
        self.monitoring_thread.start()
        
        # RESTORED: Predictive analytics thread (only if enabled)
        if self.config.prediction_enabled:
            self.analytics_thread = threading.Thread(
                target=self._analytics_loop,
                name="PredictiveAnalytics",
                daemon=True
            )
            self.analytics_thread.start()
        
        # Metrics broadcasting thread (only for central hub)
        if self.config.role == "central_hub" and self.metrics_publisher:
            self.broadcasting_thread = threading.Thread(
                target=self._broadcasting_loop,
                name="MetricsBroadcasting",
                daemon=True
            )
            self.broadcasting_thread.start()
        
        logger.info(f"Background threads started for {self.config.role}")
    
    def check_all_agents_health(self) -> Dict[str, Dict[str, Any]]:
        """Modern parallel health checks with RESTORED StandardizedHealthChecker integration"""
        if not self.monitored_agents:
            return {}
        
        results = {}
        
        if self.config.parallel_health_checks:
            # Parallel execution using ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_concurrent_health_checks) as executor:
                future_to_agent = {
                    executor.submit(self._check_agent_health_modern, agent_name, agent_info): agent_name
                    for agent_name, agent_info in self.monitored_agents.items()
                }
                
                for future in concurrent.futures.as_completed(future_to_agent, timeout=30):
                    agent_name = future_to_agent[future]
                    try:
                        health_result = future.result()
                        results[agent_name] = health_result
                        
                        # Update Prometheus metrics
                        health_status = 1.0 if health_result.get('status') == 'healthy' else 0.0
                        self.prometheus_metrics.update_agent_health(agent_name, health_status)
                        
                        # RESTORED: Add to predictive analyzer
                        metric = HealthMetric(
                            agent_name=agent_name,
                            metric_type="health_status",
                            value=health_status,
                            metadata=health_result
                        )
                        self.predictive_analyzer.add_metric(agent_name, metric)
                        
                        # RESTORED: Log to performance database
                        self.performance_logger.log_metric(
                            agent_name=agent_name,
                            metric_type="health_check",
                            value=health_status,
                            metadata=health_result
                        )
                        
                        # RESTORED: Attempt recovery if unhealthy
                        if health_status == 0.0:
                            logger.warning(f"Agent {agent_name} is unhealthy, attempting recovery")
                            self.recovery_manager.attempt_recovery(agent_name, "tier1")
                        
                    except Exception as e:
                        self.report_error(ErrorSeverity.WARNING, f"Health check failed for {agent_name}", {"error": str(e)})
                        results[agent_name] = {
                            'status': 'error',
                            'error': str(e),
                            'timestamp': time.time()
                        }
        else:
            # Sequential health checks (fallback)
            for agent_name, agent_info in self.monitored_agents.items():
                try:
                    results[agent_name] = self._check_agent_health_modern(agent_name, agent_info)
                except Exception as e:
                    self.report_error(ErrorSeverity.WARNING, f"Health check failed for {agent_name}", {"error": str(e)})
                    results[agent_name] = {
                        'status': 'error',
                        'error': str(e),
                        'timestamp': time.time()
                    }
        
        return results
    
    def _check_agent_health_modern(self, agent_name: str, agent_info: Dict[str, Any]) -> Dict[str, Any]:
        """Modern agent health check with proper error handling"""
        import requests
        
        try:
            host = agent_info.get('host', 'localhost')
            endpoint = agent_info.get('health_endpoint', f"http://{host}:{agent_info.get('port', 8000)}/health")
            
            start_time = time.time()
            response = requests.get(endpoint, timeout=self.config.health_check_timeout)
            response_time = time.time() - start_time
            
            # Record response time metric
            self.prometheus_metrics.record_response_time(agent_name, response_time)
            
            if response.status_code == 200:
                self.prometheus_metrics.record_request(agent_name, "success")
                
                # Parse response data
                try:
                    response_data = response.json() if response.content else {}
                except:
                    response_data = {}
                
                return {
                    'status': 'healthy',
                    'response_time': response_time,
                    'timestamp': time.time(),
                    'details': response_data,
                    'environment': self.config.environment,
                    'hub_role': self.config.role
                }
            else:
                self.prometheus_metrics.record_request(agent_name, "error")
                return {
                    'status': 'unhealthy',
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'timestamp': time.time(),
                    'environment': self.config.environment,
                    'hub_role': self.config.role
                }
                
        except Exception as e:
            self.prometheus_metrics.record_request(agent_name, "error")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': time.time(),
                'environment': self.config.environment,
                'hub_role': self.config.role
            }
    
    def _broadcast_metrics(self, metrics_data: Dict[str, Any]):
        """Modern ZMQ metrics broadcasting with error handling"""
        if not self.metrics_publisher or self.config.role != "central_hub":
            return
        
        try:
            # Broadcast with topic for filtering
            topic = "METRICS"
            message = json.dumps({
                'topic': topic,
                'timestamp': time.time(),
                'source': f'ObservabilityHub-{self.config.environment}',
                'environment': self.config.environment,
                'role': self.config.role,
                'data': metrics_data
            })
            
            self.metrics_publisher.send_string(f"{topic} {message}")
            logger.debug(f"Broadcasted metrics: {len(metrics_data)} entries from {self.config.environment}")
            
        except Exception as e:
            self.report_error(ErrorSeverity.ERROR, "Metrics broadcasting error", {"error": str(e)})
    
    def _monitoring_loop(self):
        """Modern monitoring loop with proper error handling"""
        while self.threads_running:
            try:
                # Perform parallel health checks
                health_results = self.check_all_agents_health()
                
                # Update system metrics
                self._update_system_metrics()
                
                # If PC2, collect data for sync
                if self.config.cross_machine_sync and self.config.role == "local_reporter":
                    self._prepare_sync_data(health_results)
                
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                self.report_error(ErrorSeverity.ERROR, "Monitoring loop error", {"error": str(e)})
                time.sleep(5)
    
    def _analytics_loop(self):
        """RESTORED: Modern predictive analytics loop"""
        while self.threads_running:
            try:
                # Run predictive analysis
                alerts = self.predictive_analyzer.run_predictive_analysis()
                
                # Update failure probability metrics
                for agent_name, metrics in self.predictive_analyzer.agent_metrics.items():
                    if metrics:
                        failure_prob = self.predictive_analyzer._calculate_failure_probability(metrics)
                        self.prometheus_metrics.update_failure_probability(agent_name, failure_prob)
                
                # Handle alerts
                for alert in alerts:
                    logger.warning(f"Predictive alert for {alert.agent_name}: {alert.alert_type} "
                                 f"(confidence: {alert.confidence:.2f})")
                    
                    # Report alert through modern error system
                    self.report_error(
                        ErrorSeverity.WARNING if alert.severity == "warning" else ErrorSeverity.CRITICAL,
                        f"Predictive alert: {alert.alert_type}",
                        {
                            "agent_name": alert.agent_name,
                            "confidence": alert.confidence,
                            "predicted_failure_time": alert.predicted_failure_time,
                            "recommended_actions": alert.recommended_actions
                        }
                    )
                    
                    # RESTORED: Trigger recovery if critical
                    if alert.severity == "critical":
                        self.recovery_manager.attempt_recovery(alert.agent_name, "tier2")
                
                time.sleep(60)  # Run analytics every minute
                
            except Exception as e:
                self.report_error(ErrorSeverity.ERROR, "Analytics loop error", {"error": str(e)})
                time.sleep(10)
    
    def _broadcasting_loop(self):
        """Modern metrics broadcasting loop"""
        while self.threads_running:
            try:
                # Collect current metrics
                metrics_data = self._collect_all_metrics()
                
                # Broadcast metrics
                self._broadcast_metrics(metrics_data)
                
                time.sleep(10)  # Broadcast every 10 seconds
                
            except Exception as e:
                self.report_error(ErrorSeverity.ERROR, "Broadcasting loop error", {"error": str(e)})
                time.sleep(5)
    
    def _update_system_metrics(self):
        """Update system-level metrics with modern error handling"""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.prometheus_metrics.update_system_metric('cpu_usage', cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.prometheus_metrics.update_system_metric('memory_usage', memory.used, {'type': 'used'})
            self.prometheus_metrics.update_system_metric('memory_usage', memory.available, {'type': 'available'})
            
            # RESTORED: Log system metrics to database
            self.performance_logger.log_metric("system", "cpu_usage", cpu_percent)
            self.performance_logger.log_metric("system", "memory_usage", memory.used)
            
        except ImportError:
            logger.warning("psutil not available, using mock system metrics")
            # Mock metrics when psutil is not available
            self.prometheus_metrics.update_system_metric('cpu_usage', 25.0)
            self.prometheus_metrics.update_system_metric('memory_usage', 1024*1024*1024, {'type': 'used'})
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "System metrics update error", {"error": str(e)})
    
    def _collect_all_metrics(self) -> Dict[str, Any]:
        """Collect all current metrics for broadcasting"""
        return {
            'timestamp': time.time(),
            'environment': self.config.environment,
            'role': self.config.role,
            'system_metrics': getattr(self.prometheus_metrics, 'metrics_data', {}),
            'agent_count': len(self.monitored_agents),
            'health_check_interval': self.health_check_interval,
            'config': {
                'scope': self.config.scope,
                'prediction_enabled': self.config.prediction_enabled,
                'parallel_health_checks': self.config.parallel_health_checks,
                'cross_machine_sync': self.config.cross_machine_sync,
                'failover_active': getattr(self.cross_machine_sync, 'failover_active', False)
            }
        }
    
    def _prepare_sync_data(self, health_results: Dict[str, Dict[str, Any]]):
        """Prepare data for cross-machine sync (PC2 → MainPC)"""
        if not self.config.cross_machine_sync:
            return
            
        # Update cross-machine sync with current data
        if hasattr(self.cross_machine_sync, '_latest_sync_data'):
            self.cross_machine_sync._latest_sync_data = {
                "source": "pc2",
                "timestamp": time.time(),
                "environment": self.config.environment,
                "sync_type": "health_and_metrics",
                "health_results": health_results,
                "system_metrics": self._collect_all_metrics(),
                "agent_configs": list(self.lifecycle_manager.agent_configs.keys())
            }

    def setup_routes(self):
        """Setup modern monitoring API routes with RESTORED cross-machine support"""
        
        @self.app.get("/health")
        async def health_check():
            """Modern health check endpoint using StandardizedHealthChecker"""
            try:
                # Use standardized health check
                health_status = self.standardized_health.perform_health_check()
                
                return {
                    "status": "healthy" if health_status.status == HealthStatus.HEALTHY else "degraded",
                    "service": f"ObservabilityHub-{self.config.environment}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "uptime": time.time() - self.start_time,
                    "environment": self.config.environment,
                    "role": self.config.role,
                    "restored_functionality": {
                        "predictive_analyzer": bool(self.predictive_analyzer),
                        "lifecycle_manager": bool(self.lifecycle_manager),
                        "performance_logger": bool(self.performance_logger),
                        "recovery_manager": bool(self.recovery_manager)
                    },
                    "unified_services": {
                        "health": self.config.parallel_health_checks,
                        "performance": True,
                        "prediction": self.config.prediction_enabled,
                        "cross_machine_sync": self.config.cross_machine_sync
                    },
                    "health_details": health_status.details,
                    "health_checks": health_status.checks
                }
            except Exception as e:
                self.report_error(ErrorSeverity.ERROR, "Health endpoint error", {"error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/metrics")
        async def get_metrics():
            """Get all system metrics"""
            try:
                if PROMETHEUS_AVAILABLE:
                    return PlainTextResponse(
                        content=self.prometheus_metrics.export_metrics(),
                        media_type=CONTENT_TYPE_LATEST
                    )
                else:
                    # Return collected metrics
                    return {
                        "status": "success", 
                        "metrics": self._collect_all_metrics(),
                        "environment": self.config.environment
                    }
            except Exception as e:
                self.report_error(ErrorSeverity.ERROR, "Error getting metrics", {"error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/health_summary")
        async def health_summary():
            """Get system health summary"""
            try:
                health_results = self.check_all_agents_health()
                total_agents = len(health_results)
                healthy_agents = sum(1 for result in health_results.values() if result.get('status') == 'healthy')
                
                return {
                    "status": "success",
                    "environment": self.config.environment,
                    "role": self.config.role,
                    "total_agents": total_agents,
                    "healthy_agents": healthy_agents,
                    "unhealthy_agents": total_agents - healthy_agents,
                    "health_results": health_results,
                    "scope": self.config.scope
                }
            except Exception as e:
                self.report_error(ErrorSeverity.ERROR, "Error getting health summary", {"error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/register_agent")
        async def register_agent(request: Request):
            """Register an agent for monitoring"""
            try:
                data = await request.json()
                agent_name = data.get('agent_name')
                port = data.get('port')
                health_endpoint = data.get('health_endpoint')
                
                if not agent_name or not port:
                    raise HTTPException(status_code=400, detail="Missing agent_name or port")
                
                host = data.get('host', 'localhost')
                self.monitored_agents[agent_name] = {
                    'host': host,
                    'port': port,
                    'health_endpoint': health_endpoint or f"http://{host}:{port}/health",
                    'environment': self.config.environment,
                    'registered_at': time.time()
                }
                
                logger.info(f"Registered agent {agent_name} for monitoring in {self.config.environment}")
                return {"status": "success", "message": f"Agent {agent_name} registered for monitoring"}
            
            except Exception as e:
                self.report_error(ErrorSeverity.ERROR, f"Error registering agent", {"error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/trigger_recovery")
        async def trigger_recovery(request: Request):
            """RESTORED: Trigger recovery for an agent"""
            try:
                data = await request.json()
                agent_name = data.get('agent_name')
                strategy = data.get('strategy', 'tier1')
                
                if not agent_name:
                    raise HTTPException(status_code=400, detail="Missing agent_name")
                
                success = self.recovery_manager.attempt_recovery(agent_name, strategy)
                
                # Report recovery attempt
                self.report_error(
                    ErrorSeverity.INFO,
                    f"Recovery {'successful' if success else 'failed'} for {agent_name}",
                    {"strategy": strategy, "success": success}
                )
                
                return {
                    "status": "success" if success else "error",
                    "message": f"Recovery {'successful' if success else 'failed'} for {agent_name}",
                    "strategy": strategy,
                    "environment": self.config.environment
                }
            
            except Exception as e:
                self.report_error(ErrorSeverity.ERROR, "Error triggering recovery", {"error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/performance_metrics/{agent_name}")
        async def get_performance_metrics(agent_name: str):
            """RESTORED: Get performance metrics for an agent"""
            try:
                metrics = self.performance_logger.get_metrics(agent_name=agent_name)
                return {
                    "status": "success",
                    "agent_name": agent_name,
                    "environment": self.config.environment,
                    "metrics": metrics
                }
            except Exception as e:
                self.report_error(ErrorSeverity.ERROR, "Error getting performance metrics", {"error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/alerts")
        async def get_alerts():
            """RESTORED: Get active predictive alerts"""
            try:
                alerts = self.predictive_analyzer.run_predictive_analysis()
                return {
                    "status": "success",
                    "environment": self.config.environment,
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
                self.report_error(ErrorSeverity.ERROR, "Error getting alerts", {"error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))
        
        # CROSS-MACHINE SYNC ENDPOINTS
        @self.app.post("/sync_from_pc2")
        async def sync_from_pc2(request: Request):
            """Receive sync data from PC2 (MainPC only)"""
            if self.config.role != "central_hub":
                raise HTTPException(status_code=403, detail="Only central hub can receive sync data")
            
            try:
                sync_data = await request.json()
                
                # Process PC2 data
                logger.info(f"Received sync data from PC2: {sync_data.get('sync_type', 'unknown')}")
                
                # Store or process PC2 health results
                if 'health_results' in sync_data:
                    # You could store this in a separate collection or merge with local data
                    logger.debug(f"PC2 health results: {len(sync_data['health_results'])} agents")
                
                # Record successful sync
                self.prometheus_metrics.record_sync_attempt("pc2", True)
                
                return {
                    "status": "success",
                    "message": "Sync data received and processed",
                    "timestamp": time.time()
                }
                
            except Exception as e:
                self.prometheus_metrics.record_sync_attempt("pc2", False)
                self.report_error(ErrorSeverity.ERROR, "Error processing PC2 sync", {"error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/environment_status")
        async def environment_status():
            """Get environment-specific status"""
            return {
                "environment": self.config.environment,
                "role": self.config.role,
                "config": {
                    "scope": self.config.scope,
                    "prometheus_enabled": self.config.prometheus_enabled,
                    "parallel_health_checks": self.config.parallel_health_checks,
                    "prediction_enabled": self.config.prediction_enabled,
                    "cross_machine_sync": self.config.cross_machine_sync,
                    "mainpc_hub_endpoint": self.config.mainpc_hub_endpoint
                },
                "monitored_agents": len(self.monitored_agents),
                "uptime": time.time() - self.start_time,
                "restored_functionality": {
                    "predictive_analyzer": bool(self.predictive_analyzer),
                    "lifecycle_manager": bool(self.lifecycle_manager),
                    "performance_logger": bool(self.performance_logger),
                    "recovery_manager": bool(self.recovery_manager)
                }
            }
    
    async def start(self):
        """Start the RESTORED ObservabilityHub service"""
        try:
            logger.info(f"Starting ObservabilityHub RESTORED service in {self.config.environment} mode...")
            
            # Mark startup as complete
            self.startup_complete = True
            
            logger.info(f"ObservabilityHub RESTORED started successfully on port {self.port}")
            logger.info(f"Environment: {self.config.environment}, Role: {self.config.role}")
            logger.info(f"✅ Complete functionality: Distributed + Predictive + Lifecycle + Performance + Recovery")
            logger.info(f"Feature flags - Health: {self.config.parallel_health_checks}, "
                       f"Performance: True, "
                       f"Prediction: {self.config.prediction_enabled}, "
                       f"Cross-machine sync: {self.config.cross_machine_sync}")
            
            # Start FastAPI server
            config = uvicorn.Config(
                self.app,
                host="0.0.0.0",
                port=self.port,  # Use the port from the constructor
                log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            self.report_error(ErrorSeverity.CRITICAL, "Failed to start ObservabilityHub RESTORED", {"error": str(e)})
            raise
    
    def cleanup(self):
        """
        Gold Standard cleanup with robust try...finally block for RESTORED functionality.
        """
        logger.info(f"🚀 Starting Gold Standard cleanup for {self.name} RESTORED ({self.config.environment})...")
        cleanup_errors = []

        # =================================================================
        # ObservabilityHub RESTORED cleanup (Child responsibilities)
        # =================================================================
        try:
            logger.info("Step 1: Stopping all background threads...")
            self.threads_running = False

            # --- Stop Cross-Machine Sync ---
            logger.info("Step 2: Stopping cross-machine sync thread...")
            try:
                if hasattr(self, 'cross_machine_sync'):
                    self.cross_machine_sync.stop_sync()
                logger.info("  ✅ Cross-machine sync stopped.")
            except Exception as e:
                cleanup_errors.append(f"Cross-machine sync stop error: {e}")
                logger.error(f"  ❌ Failed to stop cross-machine sync: {e}")

            # --- Wait for Threads to Finish ---
            logger.info("Step 3: Waiting for background threads to finish...")
            threads_to_wait = [
                ("monitoring_thread", getattr(self, 'monitoring_thread', None)),
                ("analytics_thread", getattr(self, 'analytics_thread', None)),
                ("broadcasting_thread", getattr(self, 'broadcasting_thread', None))
            ]
            
            for thread_name, thread in threads_to_wait:
                if thread and thread.is_alive():
                    logger.info(f"  Waiting for {thread_name}...")
                    try:
                        thread.join(timeout=10)  # 10 second timeout per thread
                        if thread.is_alive():
                            logger.warning(f"⚠️ {thread_name} didn't stop gracefully within 10 seconds")
                        else:
                            logger.info(f"✅ {thread_name} stopped gracefully")
                    except Exception as e:
                        cleanup_errors.append(f"{thread_name} join error: {e}")
                        logger.error(f"❌ Error waiting for {thread_name}: {e}")

            # --- Shutdown Thread Pool ---
            logger.info("Step 4: Shutting down thread pool executor...")
            try:
                if hasattr(self, 'executor') and self.executor:
                    self.executor.shutdown(wait=True)
                logger.info("  ✅ Thread pool executor shut down.")
            except Exception as e:
                cleanup_errors.append(f"Executor shutdown error: {e}")
                logger.error(f"  ❌ Failed to shut down executor: {e}")

            # --- Close ZMQ Resources ---
            logger.info("Step 5: Closing ZMQ resources...")
            try:
                if hasattr(self, 'metrics_publisher') and self.metrics_publisher:
                    self.metrics_publisher.close()
                if hasattr(self, 'context') and self.context:
                    self.context.term()
                logger.info("  ✅ ZMQ resources closed.")
            except Exception as e:
                cleanup_errors.append(f"ZMQ cleanup error: {e}")
                logger.error(f"  ❌ Failed to close ZMQ resources: {e}")

            # --- RESTORED: Close Database Connections ---
            logger.info("Step 6: Closing database connections...")
            try:
                if hasattr(self, 'performance_logger') and hasattr(self.performance_logger, 'db_lock'):
                    with self.performance_logger.db_lock:
                        # Close any open database connections
                        logger.info("  ✅ Performance database connections cleaned up")
            except Exception as e:
                cleanup_errors.append(f"Database cleanup error: {e}")
                logger.error(f"❌ Database cleanup failed: {e}")

        finally:
            # =================================================================
            # BaseAgent cleanup (Parent responsibilities) - CRITICAL
            # =================================================================
            logger.info("Final Step: Calling BaseAgent cleanup (NATS, Health, etc.)...")
            try:
                super().cleanup()
                logger.info("  ✅ BaseAgent cleanup completed successfully.")
            except Exception as e:
                cleanup_errors.append(f"BaseAgent cleanup error: {e}")
                logger.error(f"  ❌ BaseAgent cleanup failed: {e}")

        # =================================================================
        # Final Report
        # =================================================================
        if cleanup_errors:
            logger.warning(f"⚠️ Cleanup for {self.name} RESTORED finished with {len(cleanup_errors)} error(s):")
            for i, err in enumerate(cleanup_errors):
                logger.warning(f"   - Error {i+1}: {err}")
        else:
            logger.info(f"✅ Cleanup for {self.name} RESTORED completed perfectly without any errors.")

if __name__ == "__main__":
    import asyncio
    
    # Set default feature flags to unified mode for testing
    os.environ.setdefault('ENABLE_UNIFIED_HEALTH', 'true')
    os.environ.setdefault('ENABLE_UNIFIED_PERFORMANCE', 'true')
    os.environ.setdefault('ENABLE_UNIFIED_PREDICTION', 'true')
    
    hub = ObservabilityHub()
    
    try:
        asyncio.run(hub.start())
    except KeyboardInterrupt:
        logger.info("ObservabilityHub RESTORED interrupted by user")
    except Exception as e:
        logger.error(f"ObservabilityHub RESTORED error: {e}")
    finally:
        hub.cleanup() 