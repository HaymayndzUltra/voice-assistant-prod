#!/usr/bin/env python3
"""
Enhanced ObservabilityHub - Phase 1 Week 3 Day 2 Implementation
Distributed Architecture: Central Hub (MainPC Port 9000) + Edge Hub (PC2 Port 9100)
Enhanced with cross-machine metrics synchronization, failover, and comprehensive monitoring
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
log_file_path = Path(PathManager.get_project_root()) / "logs" / "enhanced_observability_hub.log"
log_file_path.parent.mkdir(parents=True, exist_ok=True)

logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(log_file_path))
    ]
)
logger = logging.getLogger("EnhancedObservabilityHub")

# Prometheus integration
try:
    from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, start_http_server, push_to_gateway, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    logger.warning("Prometheus client not available, using mock implementation")
    PROMETHEUS_AVAILABLE = False

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
    
    def export_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        if PROMETHEUS_AVAILABLE and self.registry:
            return generate_latest(self.registry).decode('utf-8')
        else:
            # Mock metrics export
            return f"# Enhanced ObservabilityHub metrics for {self.instance_name}\n# Prometheus not available\n"

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
    
    def get_metrics_for_sync(self, since_timestamp: float = None) -> List[Dict[str, Any]]:
        """Get metrics that need to be synchronized"""
        if since_timestamp is None:
            since_timestamp = time.time() - 3600  # Last hour by default
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute("""
                    SELECT timestamp, agent_name, metric_type, metric_value, source_hub, environment, metadata
                    FROM distributed_metrics 
                    WHERE timestamp > ? AND sync_status = 'local'
                    ORDER BY timestamp DESC
                    LIMIT 1000
                """, (since_timestamp,))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'timestamp': row[0],
                        'agent_name': row[1],
                        'metric_type': row[2],
                        'metric_value': row[3],
                        'source_hub': row[4],
                        'environment': row[5],
                        'metadata': json.loads(row[6]) if row[6] else {}
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Error retrieving metrics for sync: {e}")
            return []
    
    def record_sync_attempt(self, target_hub: str, sync_type: str, success: bool, latency_ms: float, records_synced: int = 0, error_message: str = None):
        """Record synchronization attempt"""
        try:
            with self.db_lock:
                with sqlite3.connect(str(self.db_path)) as conn:
                    conn.execute("""
                        INSERT INTO sync_log 
                        (timestamp, source_hub, target_hub, sync_type, status, latency_ms, records_synced, error_message)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        time.time(),
                        f"{self.config.environment}_{self.config.role}",
                        target_hub,
                        sync_type,
                        "success" if success else "failure",
                        latency_ms,
                        records_synced,
                        error_message
                    ))
        except Exception as e:
            logger.error(f"Error recording sync attempt: {e}")
    
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
    
    def _coordination_loop(self):
        """Main coordination loop"""
        while self.running:
            try:
                # Check peer hub status
                self._check_peer_status()
                
                # Perform data synchronization
                if self.peer_hub_status == "healthy":
                    self._perform_sync()
                
                # Update failover status
                self._update_failover_status()
                
                time.sleep(self.config.sync_interval)
                
            except Exception as e:
                logger.error(f"Error in coordination loop: {e}")
                time.sleep(5)
    
    def _check_peer_status(self):
        """Check status of peer hub"""
        try:
            start_time = time.time()
            response = requests.get(
                f"{self.config.peer_hub_endpoint}/health",
                timeout=self.config.failover_timeout
            )
            
            latency = (time.time() - start_time) * 1000  # Convert to ms
            
            if response.status_code == 200:
                self.peer_hub_status = "healthy"
                self.sync_failures = 0
                logger.debug(f"Peer hub healthy (latency: {latency:.1f}ms)")
            else:
                self.peer_hub_status = "unhealthy"
                self.sync_failures += 1
                logger.warning(f"Peer hub returned status {response.status_code}")
                
        except Exception as e:
            self.peer_hub_status = "unreachable"
            self.sync_failures += 1
            logger.error(f"Peer hub unreachable: {e}")
    
    def _perform_sync(self):
        """Perform data synchronization with peer hub"""
        try:
            # Get metrics to sync
            last_sync = self.last_successful_sync or (time.time() - 3600)
            metrics_to_sync = self.data_manager.get_metrics_for_sync(last_sync)
            
            if not metrics_to_sync:
                return
            
            # Prepare sync payload
            sync_payload = {
                "source_hub": f"{self.config.environment}_{self.config.role}",
                "timestamp": time.time(),
                "metrics": metrics_to_sync,
                "sync_type": "distributed_metrics"
            }
            
            # Send to peer hub
            start_time = time.time()
            response = requests.post(
                f"{self.config.peer_hub_endpoint}/api/v1/sync_from_peer",
                json=sync_payload,
                timeout=30
            )
            
            latency = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                self.last_successful_sync = time.time()
                self.metrics.record_sync_attempt(
                    self.config.peer_hub_endpoint,
                    True,
                    latency / 1000
                )
                
                self.data_manager.record_sync_attempt(
                    self.config.peer_hub_endpoint,
                    "distributed_metrics",
                    True,
                    latency,
                    len(metrics_to_sync)
                )
                
                logger.debug(f"Successfully synced {len(metrics_to_sync)} metrics to peer hub")
                
            else:
                raise Exception(f"Sync failed with status {response.status_code}")
                
        except Exception as e:
            self.metrics.record_sync_attempt(
                self.config.peer_hub_endpoint,
                False,
                0
            )
            
            self.data_manager.record_sync_attempt(
                self.config.peer_hub_endpoint,
                "distributed_metrics",
                False,
                0,
                0,
                str(e)
            )
            
            logger.error(f"Sync failed: {e}")
    
    def _update_failover_status(self):
        """Update failover status based on peer availability"""
        if self.config.enable_failover:
            should_failover = (
                self.sync_failures >= self.config.max_failover_attempts or
                self.peer_hub_status == "unreachable"
            )
            
            if should_failover != self.failover_active:
                self.failover_active = should_failover
                status_msg = "ACTIVATED" if should_failover else "DEACTIVATED"
                logger.warning(f"Failover mode {status_msg}")

class EnhancedObservabilityHub(BaseAgent):
    """
    Enhanced ObservabilityHub with distributed architecture
    Supports Central Hub (MainPC) and Edge Hub (PC2) configurations
    """
    
    def __init__(self, name="EnhancedObservabilityHub", port=9000, role="central_hub"):
        super().__init__(name, port)
        
        # Load enhanced configuration
        self.config = self._load_distributed_config(role)
        
        # Initialize enhanced components
        self.metrics = EnhancedPrometheusMetrics(self.config)
        self.data_manager = DistributedDataManager(self.config)
        self.coordinator = CrossMachineCoordinator(self.config, self.data_manager, self.metrics)
        
        # Agent monitoring
        self.monitored_agents = {}
        self.agent_discovery_enabled = True
        
        # Background threads
        self.monitoring_thread = None
        self.discovery_thread = None
        self.threads_running = False
        
        # FastAPI app with enhanced endpoints
        self.app = FastAPI(
            title=f"Enhanced ObservabilityHub ({self.config.role.upper()})",
            description=f"Distributed Observability Service - {self.config.environment}",
            version="2.0.0"
        )
        
        self._setup_enhanced_routes()
        self._start_background_services()
        
        # Auto-discover agents
        if self.agent_discovery_enabled:
            self._discover_agents()
        
        logger.info(f"Enhanced ObservabilityHub initialized as {self.config.role} on {self.config.environment}")
    
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
                "uptime_seconds": time.time() - getattr(self, 'start_time', time.time())
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
        
        @self.app.post("/api/v1/sync_from_peer")
        async def sync_from_peer(request: Request):
            """Receive synchronization data from peer hub"""
            try:
                sync_data = await request.json()
                
                # Validate sync data
                required_fields = ['source_hub', 'timestamp', 'metrics']
                if not all(field in sync_data for field in required_fields):
                    raise HTTPException(status_code=400, detail="Invalid sync data format")
                
                # Process incoming metrics
                metrics_received = 0
                for metric in sync_data.get('metrics', []):
                    self.data_manager.store_metric(
                        metric['agent_name'],
                        metric['metric_type'],
                        metric['metric_value'],
                        metric.get('metadata', {})
                    )
                    metrics_received += 1
                
                logger.info(f"Received {metrics_received} metrics from {sync_data['source_hub']}")
                
                return {"status": "success", "metrics_received": metrics_received}
                
            except Exception as e:
                logger.error(f"Error processing sync data: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/agents")
        async def get_monitored_agents():
            """Get list of monitored agents"""
            agents_data = []
            for agent_name, agent_info in self.monitored_agents.items():
                agents_data.append({
                    "name": agent_name,
                    "host": agent_info.get('host', 'localhost'),
                    "port": agent_info.get('port'),
                    "health_endpoint": agent_info.get('health_endpoint'),
                    "last_check": agent_info.get('last_check'),
                    "status": agent_info.get('status', 'unknown')
                })
            
            return {
                "agents": agents_data,
                "total_agents": len(agents_data),
                "hub_role": self.config.role,
                "environment": self.config.environment
            }
        
        @self.app.get("/api/v1/status")
        async def get_hub_status():
            """Get comprehensive hub status"""
            return {
                "hub_info": {
                    "role": self.config.role,
                    "environment": self.config.environment,
                    "uptime_seconds": time.time() - getattr(self, 'start_time', time.time())
                },
                "peer_coordination": {
                    "peer_hub_endpoint": self.config.peer_hub_endpoint,
                    "peer_status": getattr(self.coordinator, 'peer_hub_status', 'unknown'),
                    "last_successful_sync": getattr(self.coordinator, 'last_successful_sync', None),
                    "failover_active": getattr(self.coordinator, 'failover_active', False),
                    "sync_failures": getattr(self.coordinator, 'sync_failures', 0)
                },
                "monitoring": {
                    "monitored_agents": len(self.monitored_agents),
                    "prometheus_enabled": self.config.prometheus_enabled,
                    "data_persistence": self.config.enable_data_persistence
                }
            }
    
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
        
        logger.info(f"Started enhanced background services for {self.config.role}")
    
    def _discover_agents(self):
        """Discover agents from startup configuration"""
        try:
            if self.config.environment == "pc2":
                config_path = Path(PathManager.get_project_root()) / "pc2_code" / "config" / "startup_config.yaml"
            else:
                config_path = Path(PathManager.get_project_root()) / "main_pc_code" / "config" / "startup_config.yaml"
            
            if not config_path.exists():
                logger.warning(f"Startup config not found: {config_path}")
                return
            
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            agents_discovered = 0
            
            if self.config.environment == "pc2":
                # PC2 services format
                for service in config_data.get('pc2_services', []):
                    if isinstance(service, dict) and 'name' in service:
                        agent_name = service['name']
                        if agent_name != self.name:  # Don't monitor self
                            self.monitored_agents[agent_name] = {
                                'host': service.get('host', 'localhost'),
                                'port': service.get('port'),
                                'health_check_port': service.get('health_check_port'),
                                'health_endpoint': f"http://{service.get('host', 'localhost')}:{service.get('health_check_port', service.get('port', 8000) + 1)}/health",
                                'environment': 'pc2',
                                'discovered_at': time.time()
                            }
                            agents_discovered += 1
            else:
                # MainPC agent groups format
                agent_groups = config_data.get('agent_groups', {})
                for group_name, group_agents in agent_groups.items():
                    if isinstance(group_agents, dict) and 'agents' in group_agents:
                        for agent_name, agent_config in group_agents['agents'].items():
                            if agent_name != self.name:  # Don't monitor self
                                self.monitored_agents[agent_name] = {
                                    'host': agent_config.get('host', 'localhost'),
                                    'port': agent_config.get('port'),
                                    'health_check_port': agent_config.get('health_check_port'),
                                    'health_endpoint': f"http://{agent_config.get('host', 'localhost')}:{agent_config.get('health_check_port', agent_config.get('port', 8000) + 1)}/health",
                                    'environment': 'mainpc',
                                    'group': group_name,
                                    'discovered_at': time.time()
                                }
                                agents_discovered += 1
            
            logger.info(f"Discovered {agents_discovered} agents for monitoring")
            self.metrics.update_active_agents_count(agents_discovered)
            
        except Exception as e:
            logger.error(f"Error discovering agents: {e}")
    
    def _enhanced_monitoring_loop(self):
        """Enhanced monitoring loop with parallel health checks"""
        while self.threads_running:
            try:
                if not self.monitored_agents:
                    time.sleep(self.config.health_check_timeout)
                    continue
                
                # Perform parallel health checks
                health_results = self._perform_parallel_health_checks()
                
                # Update metrics and store data
                healthy_count = 0
                for agent_name, result in health_results.items():
                    health_status = 1.0 if result.get('status') == 'healthy' else 0.0
                    
                    # Update Prometheus metrics
                    self.metrics.update_agent_health(agent_name, health_status)
                    
                    # Store in distributed data manager
                    self.data_manager.store_metric(
                        agent_name,
                        'health_status',
                        health_status,
                        result
                    )
                    
                    if health_status == 1.0:
                        healthy_count += 1
                    
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
    
    def _perform_parallel_health_checks(self) -> Dict[str, Dict[str, Any]]:
        """Perform parallel health checks on all monitored agents"""
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_concurrent_health_checks) as executor:
            future_to_agent = {
                executor.submit(self._check_agent_health, agent_name, agent_info): agent_name
                for agent_name, agent_info in self.monitored_agents.items()
            }
            
            for future in concurrent.futures.as_completed(future_to_agent, timeout=30):
                agent_name = future_to_agent[future]
                try:
                    result = future.result()
                    results[agent_name] = result
                except Exception as e:
                    results[agent_name] = {
                        'status': 'error',
                        'error': str(e),
                        'timestamp': time.time()
                    }
        
        return results
    
    def _check_agent_health(self, agent_name: str, agent_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check health of individual agent"""
        try:
            endpoint = agent_info.get('health_endpoint')
            if not endpoint:
                return {
                    'status': 'error',
                    'error': 'No health endpoint configured',
                    'timestamp': time.time()
                }
            
            start_time = time.time()
            response = requests.get(endpoint, timeout=self.config.health_check_timeout)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    response_data = response.json() if response.content else {}
                except:
                    response_data = {}
                
                return {
                    'status': 'healthy',
                    'response_time': response_time,
                    'timestamp': time.time(),
                    'details': response_data,
                    'hub_role': self.config.role
                }
            else:
                return {
                    'status': 'unhealthy',
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'timestamp': time.time(),
                    'hub_role': self.config.role
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': time.time(),
                'hub_role': self.config.role
            }
    
    def _agent_discovery_loop(self):
        """Periodic agent discovery to handle dynamic agents"""
        while self.threads_running:
            try:
                # Re-discover agents every 5 minutes
                time.sleep(300)
                self._discover_agents()
                
            except Exception as e:
                logger.error(f"Error in agent discovery loop: {e}")
                time.sleep(60)
    
    def run_server(self, host: str = "0.0.0.0", port: int = None):
        """Run the enhanced ObservabilityHub server"""
        if port is None:
            port = 9100 if self.config.role == "edge_hub" else 9000
        
        logger.info(f"Starting Enhanced ObservabilityHub {self.config.role} on {host}:{port}")
        
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
    
    parser = argparse.ArgumentParser(description="Enhanced ObservabilityHub")
    parser.add_argument("--role", choices=["central_hub", "edge_hub"], default="central_hub",
                        help="Hub role (central_hub for MainPC, edge_hub for PC2)")
    parser.add_argument("--port", type=int, help="Port to run on (default: 9000 for central, 9100 for edge)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    
    args = parser.parse_args()
    
    # Create and run enhanced hub
    hub = EnhancedObservabilityHub(role=args.role)
    hub.run_server(host=args.host, port=args.port) 