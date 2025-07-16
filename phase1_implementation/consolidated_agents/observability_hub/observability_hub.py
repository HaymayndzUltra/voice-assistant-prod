#!/usr/bin/env python3
"""
ObservabilityHub - Phase 1 Implementation
Consolidates: PredictiveHealthMonitor (5613), PerformanceMonitor (7103), HealthMonitor (7114), 
PerformanceLoggerAgent (7128), SystemHealthManager (7117)
Target: Prometheus exporter, log shipper, anomaly detector threads (Port 7002)
Hardware: PC2
"""

import sys
import os
from pathlib import Path
import logging
import time
import threading
import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from collections import defaultdict, deque

# Add project paths for imports
project_root = Path(__file__).parent.parent.parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Request
import uvicorn

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('phase1_implementation/logs/observability_hub.log')
    ]
)
logger = logging.getLogger("ObservabilityHub")

# Import BaseAgent with safe fallback
try:
    from common.core.base_agent import BaseAgent
except ImportError as e:
    logger.warning(f"Could not import BaseAgent: {e}")
    # Create a minimal BaseAgent substitute
    class BaseAgent:
        def __init__(self, name, port, health_check_port=None, **kwargs):
            self.name = name
            self.port = port
            self.health_check_port = health_check_port or port + 100

@dataclass
class MetricData:
    """Data structure for metric information"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str]
    source: str

@dataclass
class HealthStatus:
    """Data structure for health status information"""
    agent_name: str
    status: str  # healthy, warning, critical, unknown
    last_seen: datetime
    details: Dict[str, Any]
    location: str  # MainPC or PC2

@dataclass
class AlertRule:
    """Data structure for alert rules"""
    rule_id: str
    metric_name: str
    condition: str  # gt, lt, eq, ne
    threshold: float
    enabled: bool
    severity: str  # info, warning, critical

class MetricsCollector:
    """Handles metrics collection from various sources"""
    
    def __init__(self):
        self.metrics_buffer = deque(maxlen=1000)
        self.last_collection_time = {}
        
    def collect_system_metrics(self) -> List[MetricData]:
        """Collect basic system metrics"""
        try:
            import psutil
            
            metrics = []
            timestamp = datetime.utcnow()
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            metrics.append(MetricData(
                name="cpu_percent",
                value=cpu_percent,
                timestamp=timestamp,
                tags={"type": "system"},
                source="system"
            ))
            
            # Memory metrics
            memory = psutil.virtual_memory()
            metrics.append(MetricData(
                name="memory_percent",
                value=memory.percent,
                timestamp=timestamp,
                tags={"type": "system"},
                source="system"
            ))
            
            metrics.append(MetricData(
                name="memory_available_gb",
                value=memory.available / (1024**3),
                timestamp=timestamp,
                tags={"type": "system"},
                source="system"
            ))
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            metrics.append(MetricData(
                name="disk_percent",
                value=disk.percent,
                timestamp=timestamp,
                tags={"type": "system"},
                source="system"
            ))
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return []
    
    def collect_gpu_metrics(self) -> List[MetricData]:
        """Collect GPU metrics (simplified implementation)"""
        try:
            # This would typically use nvidia-ml-py3 or similar
            # For now, return mock data
            timestamp = datetime.utcnow()
            
            return [
                MetricData(
                    name="gpu_utilization_percent",
                    value=45.0,  # Mock data
                    timestamp=timestamp,
                    tags={"gpu_id": "0", "type": "gpu"},
                    source="gpu"
                ),
                MetricData(
                    name="gpu_memory_percent",
                    value=60.0,  # Mock data
                    timestamp=timestamp,
                    tags={"gpu_id": "0", "type": "gpu"},
                    source="gpu"
                )
            ]
            
        except Exception as e:
            logger.error(f"Error collecting GPU metrics: {e}")
            return []

class HealthMonitor:
    """Handles health monitoring for all agents"""
    
    def __init__(self):
        self.health_status: Dict[str, HealthStatus] = {}
        self.health_check_interval = 30  # seconds
        
    def update_agent_health(self, agent_name: str, status: str, details: Dict[str, Any] = None, location: str = "Unknown"):
        """Update health status for an agent"""
        self.health_status[agent_name] = HealthStatus(
            agent_name=agent_name,
            status=status,
            last_seen=datetime.utcnow(),
            details=details or {},
            location=location
        )
        
    def get_agent_health(self, agent_name: str) -> Optional[HealthStatus]:
        """Get health status for a specific agent"""
        return self.health_status.get(agent_name)
    
    def get_all_health_status(self) -> Dict[str, HealthStatus]:
        """Get health status for all agents"""
        return self.health_status.copy()
    
    def check_stale_agents(self, max_age_seconds: int = 300) -> List[str]:
        """Check for agents that haven't reported in recently"""
        stale_agents = []
        cutoff_time = datetime.utcnow().timestamp() - max_age_seconds
        
        for agent_name, health in self.health_status.items():
            if health.last_seen.timestamp() < cutoff_time:
                stale_agents.append(agent_name)
                
        return stale_agents

class AnomalyDetector:
    """Handles anomaly detection in metrics"""
    
    def __init__(self):
        self.baseline_metrics: Dict[str, List[float]] = defaultdict(list)
        self.anomaly_threshold = 2.0  # Standard deviations
        
    def update_baseline(self, metric: MetricData):
        """Update baseline for a metric"""
        baseline = self.baseline_metrics[metric.name]
        baseline.append(metric.value)
        
        # Keep only last 100 values for baseline
        if len(baseline) > 100:
            baseline.pop(0)
    
    def detect_anomaly(self, metric: MetricData) -> bool:
        """Detect if a metric value is anomalous"""
        baseline = self.baseline_metrics.get(metric.name, [])
        
        if len(baseline) < 10:  # Need enough data for baseline
            self.update_baseline(metric)
            return False
        
        # Simple statistical anomaly detection
        import statistics
        mean = statistics.mean(baseline)
        stdev = statistics.stdev(baseline) if len(baseline) > 1 else 0
        
        if stdev == 0:
            return False
        
        z_score = abs(metric.value - mean) / stdev
        is_anomaly = z_score > self.anomaly_threshold
        
        if not is_anomaly:
            self.update_baseline(metric)
            
        return is_anomaly

class AlertManager:
    """Handles alert rules and notifications"""
    
    def __init__(self):
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        
    def add_alert_rule(self, rule: AlertRule):
        """Add an alert rule"""
        self.alert_rules[rule.rule_id] = rule
        
    def remove_alert_rule(self, rule_id: str):
        """Remove an alert rule"""
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
    
    def evaluate_alerts(self, metric: MetricData) -> List[Dict[str, Any]]:
        """Evaluate alert rules against a metric"""
        triggered_alerts = []
        
        for rule_id, rule in self.alert_rules.items():
            if not rule.enabled or rule.metric_name != metric.name:
                continue
                
            triggered = False
            
            if rule.condition == "gt" and metric.value > rule.threshold:
                triggered = True
            elif rule.condition == "lt" and metric.value < rule.threshold:
                triggered = True
            elif rule.condition == "eq" and metric.value == rule.threshold:
                triggered = True
            elif rule.condition == "ne" and metric.value != rule.threshold:
                triggered = True
            
            if triggered:
                alert = {
                    "rule_id": rule_id,
                    "metric_name": metric.name,
                    "metric_value": metric.value,
                    "threshold": rule.threshold,
                    "severity": rule.severity,
                    "timestamp": metric.timestamp.isoformat(),
                    "source": metric.source
                }
                triggered_alerts.append(alert)
                self.active_alerts[f"{rule_id}_{metric.name}"] = alert
        
        return triggered_alerts

class ObservabilityHub(BaseAgent):
    """
    Unified observability and monitoring for the entire system.
    Consolidates health monitoring, performance tracking, and alerting.
    """
    
    def __init__(self, **kwargs):
        super().__init__(name="ObservabilityHub", port=7002, health_check_port=7102)
        
        # Feature flags for gradual migration
        self.enable_unified_health = os.getenv('ENABLE_UNIFIED_HEALTH', 'false').lower() == 'true'
        self.enable_unified_performance = os.getenv('ENABLE_UNIFIED_PERFORMANCE', 'false').lower() == 'true'
        self.enable_unified_prediction = os.getenv('ENABLE_UNIFIED_PREDICTION', 'false').lower() == 'true'
        
        # Internal components
        self.metrics_collector = MetricsCollector()
        self.health_monitor = HealthMonitor()
        self.anomaly_detector = AnomalyDetector()
        self.alert_manager = AlertManager()
        
        # Threading components
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='ObservabilityHub')
        self.monitoring_threads = []
        self.running = True
        
        # Data storage
        self.metrics_history = deque(maxlen=10000)
        self.alert_history = deque(maxlen=1000)
        
        # FastAPI app for monitoring endpoints
        self.app = FastAPI(
            title="ObservabilityHub",
            description="Phase 1 Unified Observability and Monitoring",
            version="1.0.0"
        )
        
        self.setup_routes()
        self.setup_default_alert_rules()
        
        # Startup state
        self.startup_complete = False
        self.startup_time = time.time()
        
        logger.info("ObservabilityHub initialized")
    
    def setup_routes(self):
        """Setup monitoring API routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy" if self.startup_complete else "starting",
                "service": "ObservabilityHub",
                "timestamp": datetime.utcnow().isoformat(),
                "uptime": time.time() - self.startup_time,
                "unified_services": {
                    "health": self.enable_unified_health,
                    "performance": self.enable_unified_performance,
                    "prediction": self.enable_unified_prediction
                }
            }
        
        @self.app.get("/metrics")
        async def get_metrics():
            """Get all system metrics"""
            if self.enable_unified_performance:
                return self._get_unified_metrics()
            else:
                return await self._aggregate_legacy_metrics()
        
        @self.app.get("/health_summary")
        async def health_summary():
            """Get system health summary"""
            if self.enable_unified_health:
                return self._get_unified_health_summary()
            else:
                return await self._aggregate_legacy_health()
        
        @self.app.post("/update_agent_health")
        async def update_agent_health(request: Request):
            """Update health status for an agent"""
            try:
                data = await request.json()
                agent_name = data.get('agent_name')
                status = data.get('status')
                details = data.get('details', {})
                location = data.get('location', 'Unknown')
                
                self.health_monitor.update_agent_health(agent_name, status, details, location)
                
                return {"status": "success", "message": f"Updated health for {agent_name}"}
            except Exception as e:
                logger.error(f"Error updating agent health: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/add_alert_rule")
        async def add_alert_rule(request: Request):
            """Add monitoring alert rule"""
            try:
                data = await request.json()
                rule = AlertRule(
                    rule_id=data['rule_id'],
                    metric_name=data['metric_name'],
                    condition=data['condition'],
                    threshold=float(data['threshold']),
                    enabled=data.get('enabled', True),
                    severity=data.get('severity', 'warning')
                )
                
                self.alert_manager.add_alert_rule(rule)
                
                return {"status": "success", "rule_id": rule.rule_id}
            except Exception as e:
                logger.error(f"Error adding alert rule: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/alerts")
        async def get_alerts():
            """Get active alerts"""
            return {
                "active_alerts": list(self.alert_manager.active_alerts.values()),
                "alert_history": list(self.alert_history)[-50:]  # Last 50 alerts
            }
        
        @self.app.get("/anomalies")
        async def get_anomalies():
            """Get detected anomalies"""
            # Return recent anomalies (simplified implementation)
            return {"anomalies": []}
    
    def setup_default_alert_rules(self):
        """Setup default alert rules"""
        default_rules = [
            AlertRule("cpu_high", "cpu_percent", "gt", 90.0, True, "critical"),
            AlertRule("memory_high", "memory_percent", "gt", 85.0, True, "warning"),
            AlertRule("disk_full", "disk_percent", "gt", 95.0, True, "critical"),
        ]
        
        for rule in default_rules:
            self.alert_manager.add_alert_rule(rule)
    
    def _get_unified_metrics(self):
        """Get unified metrics in unified mode"""
        try:
            # Collect current metrics
            system_metrics = self.metrics_collector.collect_system_metrics()
            gpu_metrics = self.metrics_collector.collect_gpu_metrics()
            
            all_metrics = system_metrics + gpu_metrics
            
            # Store in history
            for metric in all_metrics:
                self.metrics_history.append(metric)
            
            # Convert to response format
            metrics_dict = {}
            for metric in all_metrics:
                metrics_dict[metric.name] = {
                    "value": metric.value,
                    "timestamp": metric.timestamp.isoformat(),
                    "source": metric.source,
                    "tags": metric.tags
                }
            
            return {
                "status": "success",
                "metrics": metrics_dict,
                "collection_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting unified metrics: {e}")
            return {"status": "error", "message": str(e)}
    
    def _get_unified_health_summary(self):
        """Get unified health summary"""
        try:
            all_health = self.health_monitor.get_all_health_status()
            stale_agents = self.health_monitor.check_stale_agents()
            
            # Categorize by status
            status_counts = {"healthy": 0, "warning": 0, "critical": 0, "unknown": 0}
            agents_by_location = {"MainPC": [], "PC2": [], "Unknown": []}
            
            for agent_name, health in all_health.items():
                status_counts[health.status] = status_counts.get(health.status, 0) + 1
                agents_by_location[health.location].append({
                    "name": agent_name,
                    "status": health.status,
                    "last_seen": health.last_seen.isoformat()
                })
            
            # Mark stale agents
            for agent_name in stale_agents:
                status_counts["unknown"] = status_counts.get("unknown", 0) + 1
            
            overall_status = "healthy"
            if status_counts["critical"] > 0:
                overall_status = "critical"
            elif status_counts["warning"] > 0:
                overall_status = "warning"
            elif status_counts["unknown"] > 0:
                overall_status = "degraded"
            
            return {
                "status": "success",
                "overall_status": overall_status,
                "agent_counts": status_counts,
                "agents_by_location": agents_by_location,
                "stale_agents": stale_agents,
                "total_agents": len(all_health),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting health summary: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _aggregate_legacy_metrics(self):
        """Aggregate metrics from legacy monitoring agents"""
        # This would connect to existing monitoring agents
        # For now, return a placeholder
        return {
            "status": "delegated",
            "message": "Metrics aggregated from legacy monitoring agents",
            "source": "legacy_agents"
        }
    
    async def _aggregate_legacy_health(self):
        """Aggregate health from legacy monitoring agents"""
        # This would connect to existing health monitoring agents
        # For now, return a placeholder
        return {
            "status": "delegated",
            "message": "Health aggregated from legacy monitoring agents",
            "source": "legacy_agents"
        }
    
    def start_monitoring_threads(self):
        """Start background monitoring threads"""
        # Metrics collection thread
        if self.enable_unified_performance:
            metrics_thread = threading.Thread(target=self._metrics_collection_loop, daemon=True)
            metrics_thread.start()
            self.monitoring_threads.append(metrics_thread)
        
        # Health monitoring thread
        if self.enable_unified_health:
            health_thread = threading.Thread(target=self._health_monitoring_loop, daemon=True)
            health_thread.start()
            self.monitoring_threads.append(health_thread)
        
        # Anomaly detection thread
        if self.enable_unified_prediction:
            anomaly_thread = threading.Thread(target=self._anomaly_detection_loop, daemon=True)
            anomaly_thread.start()
            self.monitoring_threads.append(anomaly_thread)
    
    def _metrics_collection_loop(self):
        """Background metrics collection loop"""
        while self.running:
            try:
                # Collect metrics
                system_metrics = self.metrics_collector.collect_system_metrics()
                gpu_metrics = self.metrics_collector.collect_gpu_metrics()
                
                all_metrics = system_metrics + gpu_metrics
                
                # Store metrics and check for alerts
                for metric in all_metrics:
                    self.metrics_history.append(metric)
                    
                    # Check for alerts
                    triggered_alerts = self.alert_manager.evaluate_alerts(metric)
                    for alert in triggered_alerts:
                        self.alert_history.append(alert)
                        logger.warning(f"Alert triggered: {alert}")
                
                time.sleep(60)  # Collect metrics every minute
                
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                time.sleep(60)
    
    def _health_monitoring_loop(self):
        """Background health monitoring loop"""
        while self.running:
            try:
                # Check for stale agents
                stale_agents = self.health_monitor.check_stale_agents()
                
                for agent_name in stale_agents:
                    logger.warning(f"Agent {agent_name} appears to be stale")
                    # Update status to unknown
                    current_health = self.health_monitor.get_agent_health(agent_name)
                    if current_health and current_health.status != "unknown":
                        self.health_monitor.update_agent_health(agent_name, "unknown", {"reason": "stale"})
                
                time.sleep(30)  # Check health every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                time.sleep(30)
    
    def _anomaly_detection_loop(self):
        """Background anomaly detection loop"""
        while self.running:
            try:
                # Process recent metrics for anomalies
                recent_metrics = list(self.metrics_history)[-50:]  # Last 50 metrics
                
                for metric in recent_metrics:
                    if self.anomaly_detector.detect_anomaly(metric):
                        logger.info(f"Anomaly detected in {metric.name}: {metric.value}")
                        # Could trigger additional alerts here
                
                time.sleep(120)  # Check for anomalies every 2 minutes
                
            except Exception as e:
                logger.error(f"Error in anomaly detection loop: {e}")
                time.sleep(120)
    
    async def start(self):
        """Start the ObservabilityHub service"""
        try:
            logger.info("Starting ObservabilityHub service...")
            
            # Start monitoring threads
            self.start_monitoring_threads()
            
            # Mark startup as complete
            self.startup_complete = True
            
            logger.info("ObservabilityHub started successfully on port 7002")
            logger.info(f"Feature flags - Health: {self.enable_unified_health}, "
                       f"Performance: {self.enable_unified_performance}, "
                       f"Prediction: {self.enable_unified_prediction}")
            
            # Start FastAPI server
            config = uvicorn.Config(
                self.app,
                host="0.0.0.0",
                port=7002,
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
            self.running = False
            if self.executor:
                self.executor.shutdown(wait=True)
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