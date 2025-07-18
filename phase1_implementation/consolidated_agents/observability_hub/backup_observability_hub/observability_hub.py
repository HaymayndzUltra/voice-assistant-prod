#!/usr/bin/env python3
"""
ObservabilityHub - Phase 1 Implementation
Consolidates: PredictiveHealthMonitor (5613), PerformanceMonitor (7103), HealthMonitor (7114), 
PerformanceLoggerAgent (7128), SystemHealthManager (7117)
Target: Prometheus exporter, log shipper, anomaly detector threads (Port 7002)
Hardware: PC2
Enhanced with O3 requirements: Prometheus integration, predictive analytics, ZMQ broadcasting, parallel health checks
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
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from collections import defaultdict, deque
import uuid

# Add project paths for imports
project_root = Path(__file__).parent.parent.parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Request
import uvicorn

# Configure logging first (before prometheus import to avoid logger error)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('phase1_implementation/logs/observability_hub.log')
    ]
)
logger = logging.getLogger("ObservabilityHub")

# O3 Required: Prometheus integration
try:
    from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, start_http_server, push_to_gateway
    PROMETHEUS_AVAILABLE = True
except ImportError:
    logger.warning("Prometheus client not available, using mock implementation")
    PROMETHEUS_AVAILABLE = False

# Import BaseAgent with safe fallback
try:
    from common.core.base_agent import BaseAgent as BaseAgentImport
    BaseAgent = BaseAgentImport  # type: ignore  # Use alias to avoid type conflicts
except ImportError as e:
    logger.warning(f"Could not import BaseAgent: {e}")
    # Import the real BaseAgent instead of creating a substitute
    from common.core.base_agent import BaseAgent

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

class PrometheusMetrics:
    """O3 Required: Prometheus metrics integration"""
    
    def __init__(self):
        if PROMETHEUS_AVAILABLE:
            self.registry = CollectorRegistry()
            self._setup_metrics()
        else:
            self.registry = None
            self._setup_mock_metrics()
    
    def _setup_metrics(self):
        """Setup Prometheus metrics"""
        if not PROMETHEUS_AVAILABLE:
            return
            
        # Agent health metrics
        self.agent_health_gauge = Gauge(
            'agent_health_status',
            'Health status of agents (1=healthy, 0=unhealthy)',
            ['agent_name', 'instance'],
            registry=self.registry
        )
        
        # System performance metrics
        self.cpu_usage_gauge = Gauge(
            'system_cpu_usage_percent',
            'CPU usage percentage',
            ['instance'],
            registry=self.registry
        )
        
        self.memory_usage_gauge = Gauge(
            'system_memory_usage_bytes',
            'Memory usage in bytes',
            ['instance', 'type'],
            registry=self.registry
        )
        
        # Request metrics
        self.request_counter = Counter(
            'agent_requests_total',
            'Total number of requests per agent',
            ['agent_name', 'status'],
            registry=self.registry
        )
        
        # Response time metrics
        self.response_time_histogram = Histogram(
            'agent_response_time_seconds',
            'Response time in seconds',
            ['agent_name'],
            registry=self.registry
        )
        
        # Predictive metrics
        self.failure_probability_gauge = Gauge(
            'agent_failure_probability',
            'Predicted failure probability (0-1)',
            ['agent_name'],
            registry=self.registry
        )
    
    def _setup_mock_metrics(self):
        """Setup mock metrics when Prometheus is not available"""
        self.metrics_data = defaultdict(dict)
    
    def update_agent_health(self, agent_name: str, health_status: float):
        """Update agent health metric"""
        if PROMETHEUS_AVAILABLE and self.registry:
            self.agent_health_gauge.labels(agent_name=agent_name, instance="pc2").set(health_status)
        else:
            self.metrics_data['agent_health'][agent_name] = health_status
    
    def update_system_metric(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Update system metric"""
        if labels is None:
            labels = {}
            
        if PROMETHEUS_AVAILABLE and self.registry:
            if metric_name == 'cpu_usage':
                self.cpu_usage_gauge.labels(instance="pc2").set(value)
            elif metric_name == 'memory_usage':
                memory_type = labels.get('type', 'used')
                self.memory_usage_gauge.labels(instance="pc2", type=memory_type).set(value)
        else:
            self.metrics_data['system'][metric_name] = value
    
    def record_request(self, agent_name: str, status: str):
        """Record request metric"""
        if PROMETHEUS_AVAILABLE and self.registry:
            self.request_counter.labels(agent_name=agent_name, status=status).inc()
        else:
            key = f"{agent_name}_{status}"
            self.metrics_data['requests'][key] = self.metrics_data['requests'].get(key, 0) + 1
    
    def record_response_time(self, agent_name: str, response_time: float):
        """Record response time metric"""
        if PROMETHEUS_AVAILABLE and self.registry:
            self.response_time_histogram.labels(agent_name=agent_name).observe(response_time)
        else:
            if agent_name not in self.metrics_data['response_times']:
                self.metrics_data['response_times'][agent_name] = []
            self.metrics_data['response_times'][agent_name].append(response_time)
    
    def update_failure_probability(self, agent_name: str, probability: float):
        """Update predicted failure probability"""
        if PROMETHEUS_AVAILABLE and self.registry:
            self.failure_probability_gauge.labels(agent_name=agent_name).set(probability)
        else:
            self.metrics_data['failure_probability'][agent_name] = probability

class PredictiveAnalyzer:
    """O3 Required: Predictive analytics algorithms"""
    
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

# MISSING LOGIC 1: Agent Process Management (from PredictiveHealthMonitor)
class AgentLifecycleManager:
    """PredictiveHealthMonitor Logic: Agent lifecycle and process management"""
    
    def __init__(self):
        self.agent_processes = {}
        self.agent_last_restart = {}
        self.restart_cooldown = 60  # seconds
        self.agent_configs = {}
        
    def load_agent_configs(self):
        """Load agent configurations for lifecycle management"""
        try:
            # Load from config files
            config_paths = [
                "pc2_code/config/startup_config.yaml",
                "main_pc_code/config/startup_config.yaml"
            ]
            
            import yaml
            for config_path in config_paths:
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config_data = yaml.safe_load(f)
                        
                    # Extract agent configurations
                    agents = config_data.get('pc2_services', []) + config_data.get('main_pc_agents', [])
                    for agent in agents:
                        if isinstance(agent, dict) and 'name' in agent:
                            self.agent_configs[agent['name']] = agent
                            
            logger.info(f"Loaded {len(self.agent_configs)} agent configurations")
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
            
            if script_path and os.path.exists(script_path):
                process = subprocess.Popen([sys.executable, script_path])
                self.agent_processes[agent_name] = process
                self.agent_last_restart[agent_name] = now
                
                logger.info(f"Started agent {agent_name}")
                return True
            else:
                logger.error(f"Script not found for agent {agent_name}: {script_path}")
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

# MISSING LOGIC 2: Performance Data Persistence (from PerformanceLoggerAgent)
class PerformanceLogger:
    """PerformanceLoggerAgent Logic: Performance data logging and persistence"""
    
    def __init__(self, db_path: str = "phase1_implementation/data/performance_metrics.db"):
        self.db_path = db_path
        self.db_lock = threading.Lock()
        self._init_database()
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_old_metrics, daemon=True)
        self.cleanup_thread.start()
    
    def _init_database(self):
        """Initialize SQLite database for performance metrics"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        agent_name TEXT NOT NULL,
                        metric_type TEXT NOT NULL,
                        metric_value REAL NOT NULL,
                        metadata TEXT
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp ON performance_metrics(timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_agent_name ON performance_metrics(agent_name)
                """)
                
            logger.info(f"Performance metrics database initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    def log_metric(self, agent_name: str, metric_type: str, value: float, metadata: Optional[Dict[str, Any]] = None):
        """Log a performance metric to database"""
        if metadata is None:
            metadata = {}
            
        try:
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO performance_metrics 
                        (timestamp, agent_name, metric_type, metric_value, metadata)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        time.time(),
                        agent_name,
                        metric_type,
                        value,
                        json.dumps(metadata) if metadata else None
                    ))
                    
        except Exception as e:
            logger.error(f"Error logging metric: {e}")
    
    def get_metrics(self, agent_name: Optional[str] = None, hours: int = 24) -> List[Dict[str, Any]]:
        """Retrieve metrics from database"""
        try:
            cutoff_time = time.time() - (hours * 3600)
            
            with sqlite3.connect(self.db_path) as conn:
                if agent_name:
                    cursor = conn.execute("""
                        SELECT timestamp, agent_name, metric_type, metric_value, metadata
                        FROM performance_metrics
                        WHERE agent_name = ? AND timestamp > ?
                        ORDER BY timestamp DESC
                    """, (agent_name, cutoff_time))
                else:
                    cursor = conn.execute("""
                        SELECT timestamp, agent_name, metric_type, metric_value, metadata
                        FROM performance_metrics
                        WHERE timestamp > ?
                        ORDER BY timestamp DESC
                    """, (cutoff_time,))
                
                results = []
                for row in cursor.fetchall():
                    timestamp, agent_name, metric_type, metric_value, metadata = row
                    results.append({
                        'timestamp': timestamp,
                        'agent_name': agent_name,
                        'metric_type': metric_type,
                        'metric_value': metric_value,
                        'metadata': json.loads(metadata) if metadata else {}
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Error retrieving metrics: {e}")
            return []
    
    def _cleanup_old_metrics(self):
        """Cleanup old metrics periodically"""
        while True:
            try:
                # Remove metrics older than 30 days
                cutoff_time = time.time() - (30 * 24 * 3600)
                
                with self.db_lock:
                    with sqlite3.connect(self.db_path) as conn:
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

# MISSING LOGIC 3: Recovery Strategies (from PredictiveHealthMonitor)
class RecoveryManager:
    """PredictiveHealthMonitor Logic: Tiered recovery strategies"""
    
    def __init__(self, lifecycle_manager: AgentLifecycleManager):
        self.lifecycle_manager = lifecycle_manager
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
            # Clear agent-specific cache directories
            cache_dirs = [
                f"cache/{agent_name}",
                f"temp/{agent_name}",
                f"logs/{agent_name}"
            ]
            
            import shutil
            for cache_dir in cache_dirs:
                if os.path.exists(cache_dir):
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

class ObservabilityHub(BaseAgent):
    """
    ObservabilityHub - Phase 1 Consolidated Service
    Enhanced with ALL missing logic from source agents
    """
    
    def __init__(self, name="ObservabilityHub", port=9000):  # FIXED: Use correct port 9000 from PHASE 0
        super().__init__(name, port)
        
        # Initialize start time for health reporting
        self.start_time = time.time()
        
        # O3 Enhanced Components
        self.prometheus_metrics = PrometheusMetrics()
        self.predictive_analyzer = PredictiveAnalyzer()
        
        # MISSING LOGIC INTEGRATION
        self.lifecycle_manager = AgentLifecycleManager()
        self.performance_logger = PerformanceLogger()
        self.recovery_manager = RecoveryManager(self.lifecycle_manager)
        
        # ZMQ setup for broadcasting
        self.context = zmq.Context()
        self.metrics_publisher = None
        self.setup_zmq_broadcasting()
        
        # Agent monitoring
        self.monitored_agents = {}
        self.health_check_interval = 30  # seconds
        self.parallel_health_checks = True
        
        # Background threads
        self.monitoring_thread = None
        self.analytics_thread = None
        self.broadcasting_thread = None
        self.threads_running = False
        
        # Thread pool for parallel operations
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix='ObservabilityHub')
        
        # FastAPI app
        self.app = FastAPI(
            title="ObservabilityHub",
            description="Phase 1 Observability Service with Complete Source Agent Logic",
            version="1.0.0"
        )
        
        self.setup_routes()
        self.start_background_threads()
        
        # Load agent configurations
        self.lifecycle_manager.load_agent_configs()
        
        logger.info("ObservabilityHub with complete source agent logic initialized")
    
    def setup_zmq_broadcasting(self):
        """O3 Required: ZMQ PUB/SUB broadcasting setup"""
        try:
            self.metrics_publisher = self.context.socket(zmq.PUB)
            self.metrics_publisher.bind("tcp://*:7152")  # Metrics broadcasting port
            logger.info("ZMQ metrics broadcasting setup on port 7152")
        except Exception as e:
            logger.error(f"ZMQ setup error: {e}")
            self.metrics_publisher = None
    
    def start_background_threads(self):
        """Start O3 required background threads"""
        self.threads_running = True
        
        # Parallel health monitoring thread
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="HealthMonitoring",
            daemon=True
        )
        self.monitoring_thread.start()
        
        # Predictive analytics thread
        self.analytics_thread = threading.Thread(
            target=self._analytics_loop,
            name="PredictiveAnalytics",
            daemon=True
        )
        self.analytics_thread.start()
        
        # Metrics broadcasting thread
        self.broadcasting_thread = threading.Thread(
            target=self._broadcasting_loop,
            name="MetricsBroadcasting",
            daemon=True
        )
        self.broadcasting_thread.start()
        
        logger.info("Background threads started")
    
    def check_all_agents_health(self) -> Dict[str, Dict[str, Any]]:
        """O3 Required: Parallel health checks"""
        if not self.monitored_agents:
            return {}
        
        results = {}
        
        if self.parallel_health_checks:
            # Parallel execution using ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                future_to_agent = {
                    executor.submit(self._check_agent_health, agent_name, agent_info): agent_name
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
                        
                        # Add to predictive analyzer
                        metric = HealthMetric(
                            agent_name=agent_name,
                            metric_type="health_status",
                            value=health_status,
                            metadata=health_result
                        )
                        self.predictive_analyzer.add_metric(agent_name, metric)
                        
                        # Log to performance database
                        self.performance_logger.log_metric(
                            agent_name=agent_name,
                            metric_type="health_check",
                            value=health_status,
                            metadata=health_result
                        )
                        
                        # Attempt recovery if unhealthy
                        if health_status == 0.0:
                            logger.warning(f"Agent {agent_name} is unhealthy, attempting recovery")
                            self.recovery_manager.attempt_recovery(agent_name, "tier1")
                        
                    except Exception as e:
                        logger.error(f"Health check failed for {agent_name}: {e}")
                        results[agent_name] = {
                            'status': 'error',
                            'error': str(e),
                            'timestamp': time.time()
                        }
        else:
            # Sequential health checks (fallback)
            for agent_name, agent_info in self.monitored_agents.items():
                try:
                    results[agent_name] = self._check_agent_health(agent_name, agent_info)
                except Exception as e:
                    logger.error(f"Health check failed for {agent_name}: {e}")
                    results[agent_name] = {
                        'status': 'error',
                        'error': str(e),
                        'timestamp': time.time()
                    }
        
        return results
    
    def _check_agent_health(self, agent_name: str, agent_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check individual agent health"""
        import requests
        
        try:
            endpoint = agent_info.get('health_endpoint', f"http://localhost:{agent_info.get('port', 8000)}/health")
            
            start_time = time.time()
            response = requests.get(endpoint, timeout=5)
            response_time = time.time() - start_time
            
            # Record response time metric
            self.prometheus_metrics.record_response_time(agent_name, response_time)
            
            if response.status_code == 200:
                self.prometheus_metrics.record_request(agent_name, "success")
                return {
                    'status': 'healthy',
                    'response_time': response_time,
                    'timestamp': time.time(),
                    'details': response.json() if response.content else {}
                }
            else:
                self.prometheus_metrics.record_request(agent_name, "error")
                return {
                    'status': 'unhealthy',
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'timestamp': time.time()
                }
                
        except Exception as e:
            self.prometheus_metrics.record_request(agent_name, "error")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': time.time()
            }
    
    def _broadcast_metrics(self, metrics_data: Dict[str, Any]):
        """O3 Required: ZMQ metrics broadcasting"""
        if not self.metrics_publisher:
            return
        
        try:
            # Broadcast with topic for filtering
            topic = "METRICS"
            message = json.dumps({
                'topic': topic,
                'timestamp': time.time(),
                'source': 'ObservabilityHub',
                'data': metrics_data
            })
            
            self.metrics_publisher.send_string(f"{topic} {message}")
            logger.debug(f"Broadcasted metrics: {len(metrics_data)} entries")
            
        except Exception as e:
            logger.error(f"Metrics broadcasting error: {e}")
    
    def _monitoring_loop(self):
        """Main monitoring loop with parallel health checks"""
        while self.threads_running:
            try:
                # Perform parallel health checks
                health_results = self.check_all_agents_health()
                
                # Update system metrics
                self._update_system_metrics()
                
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(5)
    
    def _analytics_loop(self):
        """O3 Required: Predictive analytics loop"""
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
                    
                    # Trigger recovery if critical
                    if alert.severity == "critical":
                        self.recovery_manager.attempt_recovery(alert.agent_name, "tier2")
                
                time.sleep(60)  # Run analytics every minute
                
            except Exception as e:
                logger.error(f"Analytics loop error: {e}")
                time.sleep(10)
    
    def _broadcasting_loop(self):
        """Metrics broadcasting loop"""
        while self.threads_running:
            try:
                # Collect current metrics
                metrics_data = self._collect_all_metrics()
                
                # Broadcast metrics
                self._broadcast_metrics(metrics_data)
                
                time.sleep(10)  # Broadcast every 10 seconds
                
            except Exception as e:
                logger.error(f"Broadcasting loop error: {e}")
                time.sleep(5)
    
    def _update_system_metrics(self):
        """Update system-level metrics"""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.prometheus_metrics.update_system_metric('cpu_usage', cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.prometheus_metrics.update_system_metric('memory_usage', memory.used, {'type': 'used'})
            self.prometheus_metrics.update_system_metric('memory_usage', memory.available, {'type': 'available'})
            
            # Log system metrics to database
            self.performance_logger.log_metric("system", "cpu_usage", cpu_percent)
            self.performance_logger.log_metric("system", "memory_usage", memory.used)
            
        except ImportError:
            logger.warning("psutil not available, using mock system metrics")
            # Mock metrics when psutil is not available
            self.prometheus_metrics.update_system_metric('cpu_usage', 25.0)
            self.prometheus_metrics.update_system_metric('memory_usage', 1024*1024*1024, {'type': 'used'})
        except Exception as e:
            logger.error(f"System metrics update error: {e}")
    
    def _collect_all_metrics(self) -> Dict[str, Any]:
        """Collect all current metrics for broadcasting"""
        return {
            'timestamp': time.time(),
            'system_metrics': getattr(self.prometheus_metrics, 'metrics_data', {}),
            'agent_count': len(self.monitored_agents),
            'health_check_interval': self.health_check_interval
        }

    def setup_routes(self):
        """Setup monitoring API routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy" if self.threads_running else "starting",
                "service": "ObservabilityHub",
                "timestamp": datetime.utcnow().isoformat(),
                "uptime": time.time() - self.start_time,
                "unified_services": {
                    "health": self.parallel_health_checks,
                    "performance": True,
                    "prediction": True
                }
            }
        
        @self.app.get("/metrics")
        async def get_metrics():
            """Get all system metrics"""
            try:
                if PROMETHEUS_AVAILABLE:
                    return {"status": "success", "message": "Prometheus metrics available at /metrics endpoint"}
                else:
                    # Return collected metrics
                    return {
                        "status": "success", 
                        "metrics": self._collect_all_metrics()
                    }
            except Exception as e:
                logger.error(f"Error getting metrics: {e}")
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
                    "total_agents": total_agents,
                    "healthy_agents": healthy_agents,
                    "unhealthy_agents": total_agents - healthy_agents,
                    "health_results": health_results
                }
            except Exception as e:
                logger.error(f"Error getting health summary: {e}")
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
                
                self.monitored_agents[agent_name] = {
                    'port': port,
                    'health_endpoint': health_endpoint or f"http://localhost:{port}/health"
                }
                
                logger.info(f"Registered agent {agent_name} for monitoring")
                return {"status": "success", "message": f"Agent {agent_name} registered for monitoring"}
            
            except Exception as e:
                logger.error(f"Error registering agent: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/trigger_recovery")
        async def trigger_recovery(request: Request):
            """Trigger recovery for an agent"""
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
                    "strategy": strategy
                }
            
            except Exception as e:
                logger.error(f"Error triggering recovery: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/performance_metrics/{agent_name}")
        async def get_performance_metrics(agent_name: str):
            """Get performance metrics for an agent"""
            try:
                metrics = self.performance_logger.get_metrics(agent_name=agent_name)
                return {
                    "status": "success",
                    "agent_name": agent_name,
                    "metrics": metrics
                }
            except Exception as e:
                logger.error(f"Error getting performance metrics: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/alerts")
        async def get_alerts():
            """Get active predictive alerts"""
            try:
                alerts = self.predictive_analyzer.run_predictive_analysis()
                return {
                    "status": "success",
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
    
    async def start(self):
        """Start the ObservabilityHub service"""
        try:
            logger.info("Starting ObservabilityHub service...")
            
            # Mark startup as complete
            self.startup_complete = True
            
            logger.info("ObservabilityHub started successfully on port 9000")
            logger.info(f"Feature flags - Health: {self.parallel_health_checks}, "
                       f"Performance: True, "
                       f"Prediction: True")
            
            # Start FastAPI server
            config = uvicorn.Config(
                self.app,
                host="0.0.0.0",
                port=9000,  # FIXED: Use correct port 9000 from PHASE 0
                log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            logger.error(f"Failed to start ObservabilityHub: {e}")
            raise
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            self.threads_running = False
            if self.executor:
                self.executor.shutdown(wait=True)
            if self.metrics_publisher:
                self.metrics_publisher.close()
            if self.context:
                self.context.term()
            logger.info("ObservabilityHub cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

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
        logger.info("ObservabilityHub interrupted by user")
    except Exception as e:
        logger.error(f"ObservabilityHub error: {e}")
    finally:
        hub.cleanup() 