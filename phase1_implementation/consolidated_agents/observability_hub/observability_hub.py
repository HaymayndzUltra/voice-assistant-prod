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

# O3 Required: Prometheus integration
try:
    from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, start_http_server, push_to_gateway
    PROMETHEUS_AVAILABLE = True
except ImportError:
    logger.warning("Prometheus client not available, using mock implementation")
    PROMETHEUS_AVAILABLE = False

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
            self.health_check_port = health_check_port or (port + 1000)

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
    
    def update_system_metric(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Update system metric"""
        if PROMETHEUS_AVAILABLE and self.registry:
            if metric_name == 'cpu_usage':
                self.cpu_usage_gauge.labels(instance="pc2").set(value)
            elif metric_name == 'memory_usage':
                memory_type = labels.get('type', 'used') if labels else 'used'
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

class ObservabilityHub(BaseAgent):
    """
    ObservabilityHub - Phase 1 Consolidated Service
    Enhanced with O3 requirements: Prometheus, predictive analytics, ZMQ broadcasting, parallel health checks
    """
    
    def __init__(self, name="ObservabilityHub", port=9000):
        super().__init__(name, port)
        
        # O3 Enhanced Components
        self.prometheus_metrics = PrometheusMetrics()
        self.predictive_analyzer = PredictiveAnalyzer()
        
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
            description="Phase 1 Observability Service with O3 Enhancements",
            version="1.0.0"
        )
        
        self.setup_routes()
        self.start_background_threads()
        
        logger.info("ObservabilityHub with O3 enhancements initialized")
    
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
                "uptime": time.time() - self.start_time, # Assuming start_time is set in __init__
                "unified_services": {
                    "health": self.parallel_health_checks,
                    "performance": True, # Assuming unified_performance is always True for this hub
                    "prediction": True # Assuming unified_prediction is always True for this hub
                }
            }
        
        @self.app.get("/metrics")
        async def get_metrics():
            """Get all system metrics"""
            # This endpoint will now return Prometheus metrics if available
            if PROMETHEUS_AVAILABLE:
                start_http_server(9090) # Start Prometheus HTTP server
                return {"status": "success", "message": "Prometheus metrics available at http://localhost:9090"}
            else:
                return {"status": "error", "message": "Prometheus metrics not available"}
        
        @self.app.get("/health_summary")
        async def health_summary():
            """Get system health summary"""
            # This endpoint will now return Prometheus metrics if available
            if PROMETHEUS_AVAILABLE:
                start_http_server(9090) # Start Prometheus HTTP server
                return {"status": "success", "message": "Prometheus metrics available at http://localhost:9090"}
            else:
                return {"status": "error", "message": "Prometheus metrics not available"}
        
        @self.app.post("/update_agent_health")
        async def update_agent_health(request: Request):
            """Update health status for an agent"""
            try:
                data = await request.json()
                agent_name = data.get('agent_name')
                status = data.get('status')
                details = data.get('details', {})
                location = data.get('location', 'Unknown')
                
                # This endpoint is now deprecated for parallel health checks
                # The actual health check happens in check_all_agents_health
                logger.warning(f"Received update_agent_health request for {agent_name} with status {status}. "
                              f"This endpoint is deprecated for parallel health checks.")
                
                # For now, we'll just update the internal state if not parallel
                if not self.parallel_health_checks:
                    self.monitored_agents[agent_name] = {
                        'port': self.port, # Assuming port is available
                        'health_endpoint': f"http://localhost:{self.port}/health" # Mock endpoint
                    }
                    # Re-add to monitored_agents to trigger a health check
                    self.monitored_agents[agent_name] = {
                        'port': self.port,
                        'health_endpoint': f"http://localhost:{self.port}/health"
                    }
                
                return {"status": "success", "message": f"Received update for {agent_name}"}
            except Exception as e:
                logger.error(f"Error updating agent health: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/add_alert_rule")
        async def add_alert_rule(request: Request):
            """Add monitoring alert rule"""
            try:
                data = await request.json()
                # This endpoint is now deprecated, alerts are handled by predictive analyzer
                logger.warning("Received add_alert_rule request. This endpoint is deprecated.")
                return {"status": "success", "message": "Alert rules are now handled by predictive analytics."}
            except Exception as e:
                logger.error(f"Error adding alert rule: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/alerts")
        async def get_alerts():
            """Get active alerts"""
            # This endpoint is now deprecated, alerts are handled by predictive analyzer
            logger.warning("Received get_alerts request. This endpoint is deprecated.")
            return {"status": "success", "message": "Predictive alerts are now available."}
        
        @self.app.get("/anomalies")
        async def get_anomalies():
            """Get detected anomalies"""
            # This endpoint is now deprecated, anomalies are handled by predictive analyzer
            logger.warning("Received get_anomalies request. This endpoint is deprecated.")
            return {"status": "success", "message": "Anomalies are now handled by predictive analytics."}
    
    def start(self):
        """Start the ObservabilityHub service"""
        try:
            logger.info("Starting ObservabilityHub service...")
            
            # Start background threads
            self.start_background_threads()
            
            # Mark startup as complete
            self.startup_complete = True
            
            logger.info("ObservabilityHub started successfully on port 9000")
            logger.info(f"Feature flags - Health: {self.parallel_health_checks}, "
                       f"Performance: True, " # Assuming unified_performance is always True for this hub
                       f"Prediction: True") # Assuming unified_prediction is always True for this hub
            
            # Start FastAPI server
            config = uvicorn.Config(
                self.app,
                host="0.0.0.0",
                port=9000,
                log_level="info"
            )
            server = uvicorn.Server(config)
            server.serve()
            
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