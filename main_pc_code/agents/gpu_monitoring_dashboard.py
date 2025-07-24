#!/usr/bin/env python3
"""
GPU Monitoring Dashboard - Real-time GPU Resource Monitoring
Provides a web-based dashboard for monitoring GPU resources across MainPC and PC2.

Features:
- Real-time GPU metrics visualization
- Cross-machine resource monitoring
- Model placement tracking
- Performance analytics
- VRAM optimization insights
- Load balancing status
- Alert management
"""
from __future__ import annotations
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import time
import json
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import asyncio
from contextlib import asynccontextmanager

# Web framework imports
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False
    print("FastAPI not available - dashboard will run in data collection mode only")

# Core imports
from common.core.base_agent import BaseAgent
from common_utils.error_handling import SafeExecutor

# Event system imports
from events.model_events import (
    ModelEventType, ModelLoadEvent, VRAMEvent, ModelPerformanceEvent,
    CrossMachineModelEvent
)
from events.memory_events import MemoryEventType, MemoryPerformanceEvent
from events.event_bus import (
    get_event_bus, subscribe_to_model_events, subscribe_to_memory_events
)

@dataclass
class GPUMetric:
    """GPU performance metric data point"""
    timestamp: datetime
    gpu_id: int
    machine_id: str
    utilization_percent: float
    memory_used_mb: int
    memory_total_mb: int
    temperature_celsius: float
    power_usage_watts: float
    fan_speed_percent: float = 0.0
    
    @property
    def memory_utilization_percent(self) -> float:
        return (self.memory_used_mb / max(self.memory_total_mb, 1)) * 100

@dataclass
class ModelInfo:
    """Information about a loaded model"""
    model_id: str
    machine_id: str
    model_type: str
    memory_usage_mb: int
    load_time: datetime
    last_inference: Optional[datetime] = None
    inference_count: int = 0
    avg_inference_time_ms: float = 0.0
    status: str = "loaded"

@dataclass
class MachineStatus:
    """Overall machine status"""
    machine_id: str
    status: str  # online, offline, degraded
    gpu_count: int
    total_memory_mb: int
    used_memory_mb: int
    cpu_percent: float
    system_memory_percent: float
    network_latency_ms: float
    last_heartbeat: datetime
    model_count: int = 0

@dataclass
class Alert:
    """System alert"""
    id: str
    severity: str  # info, warning, error, critical
    title: str
    message: str
    timestamp: datetime
    machine_id: str
    acknowledged: bool = False
    category: str = "general"  # gpu, memory, performance, network

class GPUMonitoringDashboard(BaseAgent):
    """
    GPU Monitoring Dashboard with real-time web interface.
    
    Collects and visualizes GPU metrics from across the cluster,
    providing insights into resource utilization, model placement,
    and system performance.
    """
    
    def __init__(self, 
                 web_port: int = 8080,
                 metrics_retention_hours: int = 24,
                 **kwargs):
        super().__init__(name="GPUMonitoringDashboard", **kwargs)
        
        # Configuration
        self.web_port = web_port
        self.metrics_retention = timedelta(hours=metrics_retention_hours)
        
        # Data storage
        self.gpu_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1440))  # 24h at 1min intervals
        self.machine_status: Dict[str, MachineStatus] = {}
        self.model_info: Dict[str, ModelInfo] = {}
        self.alerts: Dict[str, Alert] = {}
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # WebSocket connections
        self.websocket_connections: List[WebSocket] = []
        
        # Analytics
        self.load_balancing_events: deque = deque(maxlen=1000)
        self.optimization_events: deque = deque(maxlen=1000)
        
        # Web application
        self.app = None
        self.web_server = None
        
        # Event subscriptions
        self.subscription_ids = []
        
        # Initialize components
        self._setup_event_subscriptions()
        self._initialize_machine_discovery()
        
        if WEB_AVAILABLE:
            self._setup_web_application()
            self._start_web_server()
        
        self._start_monitoring_threads()
        
        self.logger.info(f"GPU Monitoring Dashboard initialized on port {web_port}")
    
    def _setup_event_subscriptions(self) -> None:
        """Subscribe to relevant events for monitoring"""
        # Subscribe to all model events for comprehensive monitoring
        sub_id = subscribe_to_model_events(
            subscriber_id="GPUMonitoringDashboard",
            event_types="*",  # Subscribe to all model events
            callback=self._handle_model_event,
            priority=5  # Lower priority, just for monitoring
        )
        self.subscription_ids.append(sub_id)
        
        # Subscribe to memory events
        sub_id = subscribe_to_memory_events(
            subscriber_id="GPUMonitoringDashboard",
            event_types="*",  # Subscribe to all memory events
            callback=self._handle_memory_event,
            priority=5
        )
        self.subscription_ids.append(sub_id)
        
        self.logger.info("GPU Monitoring Dashboard event subscriptions configured")
    
    def _initialize_machine_discovery(self) -> None:
        """Initialize known machines"""
        # Initialize with known machine configurations
        machines = {
            "MainPC": {
                "gpu_count": 1,
                "total_memory_mb": 24576,  # 24GB RTX 4090
                "status": "online"
            },
            "PC2": {
                "gpu_count": 0,  # CPU-only
                "total_memory_mb": 0,
                "status": "online"
            }
        }
        
        for machine_id, config in machines.items():
            status = MachineStatus(
                machine_id=machine_id,
                status=config["status"],
                gpu_count=config["gpu_count"],
                total_memory_mb=config["total_memory_mb"],
                used_memory_mb=0,
                cpu_percent=0.0,
                system_memory_percent=0.0,
                network_latency_ms=0.0,
                last_heartbeat=datetime.now()
            )
            self.machine_status[machine_id] = status
    
    def _setup_web_application(self) -> None:
        """Set up FastAPI web application"""
        if not WEB_AVAILABLE:
            return
        
        # Create FastAPI app with lifespan
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            self.logger.info("Starting GPU Monitoring Dashboard web application")
            yield
            # Shutdown
            self.logger.info("Shutting down GPU Monitoring Dashboard web application")
        
        self.app = FastAPI(
            title="GPU Monitoring Dashboard",
            description="Real-time GPU resource monitoring across MainPC and PC2",
            version="1.0.0",
            lifespan=lifespan
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Set up routes
        self._setup_web_routes()
    
    def _setup_web_routes(self) -> None:
        """Set up web application routes"""
        if not self.app:
            return
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_home():
            """Main dashboard page"""
            return self._generate_dashboard_html()
        
        @self.app.get("/api/status")
        async def get_cluster_status():
            """Get overall cluster status"""
            return JSONResponse(self._get_cluster_status())
        
        @self.app.get("/api/machines")
        async def get_machines():
            """Get all machine status"""
            return JSONResponse({
                machine_id: asdict(status) 
                for machine_id, status in self.machine_status.items()
            })
        
        @self.app.get("/api/machines/{machine_id}/metrics")
        async def get_machine_metrics(machine_id: str):
            """Get metrics for a specific machine"""
            if machine_id not in self.machine_status:
                raise HTTPException(status_code=404, detail="Machine not found")
            
            metrics_key = f"{machine_id}_gpu_0"  # Simplified for single GPU
            metrics = list(self.gpu_metrics[metrics_key])
            
            return JSONResponse({
                "machine_id": machine_id,
                "metrics": [
                    {
                        "timestamp": metric.timestamp.isoformat(),
                        "utilization": metric.utilization_percent,
                        "memory_used_mb": metric.memory_used_mb,
                        "memory_total_mb": metric.memory_total_mb,
                        "temperature": metric.temperature_celsius,
                        "power": metric.power_usage_watts
                    }
                    for metric in metrics[-100:]  # Last 100 data points
                ]
            })
        
        @self.app.get("/api/models")
        async def get_models():
            """Get all loaded models"""
            return JSONResponse({
                model_id: asdict(info)
                for model_id, info in self.model_info.items()
            })
        
        @self.app.get("/api/alerts")
        async def get_alerts():
            """Get system alerts"""
            return JSONResponse({
                alert_id: asdict(alert)
                for alert_id, alert in self.alerts.items()
            })
        
        @self.app.post("/api/alerts/{alert_id}/acknowledge")
        async def acknowledge_alert(alert_id: str):
            """Acknowledge an alert"""
            if alert_id in self.alerts:
                self.alerts[alert_id].acknowledged = True
                return JSONResponse({"status": "acknowledged"})
            else:
                raise HTTPException(status_code=404, detail="Alert not found")
        
        @self.app.get("/api/analytics/load-balancing")
        async def get_load_balancing_analytics():
            """Get load balancing analytics"""
            events = list(self.load_balancing_events)[-50:]  # Last 50 events
            return JSONResponse({
                "events": events,
                "total_events": len(self.load_balancing_events),
                "recent_events": len([e for e in events if (datetime.now() - e['timestamp']).total_seconds() < 3600])
            })
        
        @self.app.get("/api/analytics/optimization")
        async def get_optimization_analytics():
            """Get optimization analytics"""
            events = list(self.optimization_events)[-50:]  # Last 50 events
            return JSONResponse({
                "events": events,
                "total_optimizations": len(self.optimization_events),
                "memory_freed_mb": sum(e.get('memory_freed_mb', 0) for e in events)
            })
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    # Send periodic updates
                    update_data = {
                        "type": "metrics_update",
                        "timestamp": datetime.now().isoformat(),
                        "cluster_status": self._get_cluster_status(),
                        "alerts": len([a for a in self.alerts.values() if not a.acknowledged])
                    }
                    
                    await websocket.send_json(update_data)
                    await asyncio.sleep(5)  # Update every 5 seconds
                    
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)
                self.logger.info("WebSocket client disconnected")
    
    def _generate_dashboard_html(self) -> str:
        """Generate the main dashboard HTML"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GPU Monitoring Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f0f2f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .metric-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }
        .status-online { background-color: #10b981; }
        .status-offline { background-color: #ef4444; }
        .status-degraded { background-color: #f59e0b; }
        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 20px;
        }
        .alert {
            background-color: #fef3c7;
            border: 1px solid #f59e0b;
            color: #92400e;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 10px;
        }
        .alert.error {
            background-color: #fee2e2;
            border-color: #ef4444;
            color: #991b1b;
        }
        .connection-status {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
        }
        .connected {
            background-color: #d1fae5;
            color: #065f46;
        }
        .disconnected {
            background-color: #fee2e2;
            color: #991b1b;
        }
    </style>
</head>
<body>
    <div class="connection-status" id="connectionStatus">Connecting...</div>
    
    <div class="header">
        <h1>🖥️ GPU Monitoring Dashboard</h1>
        <p>Real-time monitoring across MainPC and PC2</p>
    </div>
    
    <div id="alerts"></div>
    
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-title">MainPC Status</div>
            <div id="mainpc-status">
                <span class="status-indicator status-online"></span>
                <span>Online</span>
            </div>
            <div class="metric-value" id="mainpc-gpu-util">0%</div>
            <div>GPU Utilization</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-title">PC2 Status</div>
            <div id="pc2-status">
                <span class="status-indicator status-online"></span>
                <span>Online</span>
            </div>
            <div class="metric-value" id="pc2-cpu-util">0%</div>
            <div>CPU Utilization</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-title">Total VRAM</div>
            <div class="metric-value" id="total-vram">24 GB</div>
            <div>Available across cluster</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-title">Active Models</div>
            <div class="metric-value" id="active-models">0</div>
            <div>Currently loaded</div>
        </div>
    </div>
    
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-title">GPU Utilization</div>
            <div class="chart-container">
                <canvas id="gpuUtilChart"></canvas>
            </div>
        </div>
        
        <div class="metric-card">
            <div class="metric-title">VRAM Usage</div>
            <div class="chart-container">
                <canvas id="vramChart"></canvas>
            </div>
        </div>
    </div>
    
    <script>
        // WebSocket connection
        let ws = null;
        let charts = {};
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onopen = function() {
                document.getElementById('connectionStatus').textContent = 'Connected';
                document.getElementById('connectionStatus').className = 'connection-status connected';
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            ws.onclose = function() {
                document.getElementById('connectionStatus').textContent = 'Disconnected';
                document.getElementById('connectionStatus').className = 'connection-status disconnected';
                // Reconnect after 3 seconds
                setTimeout(connectWebSocket, 3000);
            };
        }
        
        function updateDashboard(data) {
            if (data.type === 'metrics_update') {
                const status = data.cluster_status;
                
                // Update machine status
                document.getElementById('mainpc-gpu-util').textContent = 
                    status.machines.MainPC ? `${status.machines.MainPC.avg_gpu_utilization.toFixed(1)}%` : '0%';
                    
                document.getElementById('pc2-cpu-util').textContent = 
                    status.machines.PC2 ? `${status.machines.PC2.cpu_percent.toFixed(1)}%` : '0%';
                    
                document.getElementById('active-models').textContent = status.total_models || '0';
                
                // Update alerts
                if (data.alerts > 0) {
                    document.getElementById('alerts').innerHTML = 
                        `<div class="alert">${data.alerts} unacknowledged alert(s)</div>`;
                } else {
                    document.getElementById('alerts').innerHTML = '';
                }
            }
        }
        
        function initCharts() {
            // GPU Utilization Chart
            const gpuCtx = document.getElementById('gpuUtilChart').getContext('2d');
            charts.gpuUtil = new Chart(gpuCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'MainPC GPU',
                        data: [],
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });
            
            // VRAM Usage Chart
            const vramCtx = document.getElementById('vramChart').getContext('2d');
            charts.vram = new Chart(vramCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Used', 'Available'],
                    datasets: [{
                        data: [40, 60],
                        backgroundColor: ['#ef4444', '#10b981']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            initCharts();
            connectWebSocket();
        });
    </script>
</body>
</html>
        """
    
    def _start_web_server(self) -> None:
        """Start the web server in a background thread"""
        if not WEB_AVAILABLE or not self.app:
            return
        
        def run_server():
            try:
                uvicorn.run(
                    self.app,
                    host="0.0.0.0",
                    port=self.web_port,
                    log_level="info"
                )
            except Exception as e:
                self.logger.error(f"Web server error: {e}")
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        self.logger.info(f"Web server started on http://0.0.0.0:{self.web_port}")
    
    def _start_monitoring_threads(self) -> None:
        """Start background monitoring threads"""
        # Metrics collection thread
        metrics_thread = threading.Thread(target=self._metrics_collection_loop, daemon=True)
        metrics_thread.start()
        
        # Machine health monitoring
        health_thread = threading.Thread(target=self._machine_health_loop, daemon=True)
        health_thread.start()
        
        # Alert processing
        alert_thread = threading.Thread(target=self._alert_processing_loop, daemon=True)
        alert_thread.start()
        
        # Data cleanup thread
        cleanup_thread = threading.Thread(target=self._data_cleanup_loop, daemon=True)
        cleanup_thread.start()
    
    def _metrics_collection_loop(self) -> None:
        """Collect metrics from machines"""
        while self.running:
            try:
                # Collect metrics for each machine
                for machine_id in self.machine_status:
                    self._collect_machine_metrics(machine_id)
                
                # Broadcast updates to WebSocket clients
                self._broadcast_updates()
                
                time.sleep(10)  # Collect every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Metrics collection error: {e}")
                time.sleep(30)
    
    def _collect_machine_metrics(self, machine_id: str) -> None:
        """Collect metrics for a specific machine"""
        def collect_metrics():
            current_time = datetime.now()
            
            if machine_id == "MainPC":
                # Try to get real GPU metrics
                try:
                    import torch
                    import GPUtil
                    
                    if torch.cuda.is_available():
                        memory_allocated = torch.cuda.memory_allocated(0)
                        memory_total = torch.cuda.get_device_properties(0).total_memory
                        
                        # Try to get GPU utilization
                        gpu_util = 0.0
                        gpu_temp = 65.0
                        gpu_power = 300.0
                        
                        if GPUtil:
                            gpus = GPUtil.getGPUs()
                            if gpus:
                                gpu = gpus[0]
                                gpu_util = gpu.load * 100
                                gpu_temp = gpu.temperature
                                gpu_power = getattr(gpu, 'powerDraw', 300.0)
                        
                        metric = GPUMetric(
                            timestamp=current_time,
                            gpu_id=0,
                            machine_id=machine_id,
                            utilization_percent=gpu_util,
                            memory_used_mb=int(memory_allocated / (1024 * 1024)),
                            memory_total_mb=int(memory_total / (1024 * 1024)),
                            temperature_celsius=gpu_temp,
                            power_usage_watts=gpu_power
                        )
                    else:
                        # Fallback to simulation
                        metric = self._generate_simulated_metric(machine_id, current_time)
                except Exception:
                    # Simulation fallback
                    metric = self._generate_simulated_metric(machine_id, current_time)
            else:
                # PC2 - CPU only, simulate basic metrics
                metric = GPUMetric(
                    timestamp=current_time,
                    gpu_id=0,
                    machine_id=machine_id,
                    utilization_percent=0.0,  # No GPU
                    memory_used_mb=0,
                    memory_total_mb=0,
                    temperature_celsius=45.0,  # CPU temp
                    power_usage_watts=150.0   # System power
                )
            
            # Store metric
            metrics_key = f"{machine_id}_gpu_0"
            self.gpu_metrics[metrics_key].append(metric)
            
            # Update machine status
            if machine_id in self.machine_status:
                status = self.machine_status[machine_id]
                status.used_memory_mb = metric.memory_used_mb
                status.last_heartbeat = current_time
                
                # Update model count
                status.model_count = len([m for m in self.model_info.values() if m.machine_id == machine_id])
        
        SafeExecutor.execute_with_fallback(
            collect_metrics,
            fallback_value=None,
            context=f"collect metrics for {machine_id}",
            expected_exceptions=(Exception,)
        )
    
    def _generate_simulated_metric(self, machine_id: str, current_time: datetime) -> GPUMetric:
        """Generate simulated GPU metrics for testing"""
        import math
        
        # Simulate varying utilization based on time
        time_factor = current_time.timestamp() / 3600  # Hours since epoch
        base_util = 30 + 20 * math.sin(time_factor * 0.1)  # Slow oscillation
        utilization = max(0, min(100, base_util + (time.time() % 10 - 5)))  # Add noise
        
        # Simulate memory usage
        base_memory = 8192  # 8GB base
        memory_used = int(base_memory + 4096 * math.sin(time_factor * 0.05))  # Memory oscillation
        
        return GPUMetric(
            timestamp=current_time,
            gpu_id=0,
            machine_id=machine_id,
            utilization_percent=utilization,
            memory_used_mb=memory_used,
            memory_total_mb=24576,  # 24GB total
            temperature_celsius=65 + 15 * (utilization / 100),
            power_usage_watts=200 + 200 * (utilization / 100)
        )
    
    def _machine_health_loop(self) -> None:
        """Monitor machine health and generate alerts"""
        while self.running:
            try:
                for machine_id, status in self.machine_status.items():
                    # Check for offline machines
                    time_since_heartbeat = (datetime.now() - status.last_heartbeat).total_seconds()
                    
                    if time_since_heartbeat > 60:  # 1 minute timeout
                        if status.status != "offline":
                            status.status = "offline"
                            self._create_alert(
                                f"machine_offline_{machine_id}",
                                "error",
                                f"Machine {machine_id} Offline",
                                f"No heartbeat received for {time_since_heartbeat:.0f} seconds",
                                machine_id,
                                "network"
                            )
                    else:
                        if status.status == "offline":
                            status.status = "online"
                            # Clear offline alert if it exists
                            alert_id = f"machine_offline_{machine_id}"
                            if alert_id in self.alerts:
                                del self.alerts[alert_id]
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Machine health monitoring error: {e}")
                time.sleep(60)
    
    def _alert_processing_loop(self) -> None:
        """Process and manage alerts"""
        while self.running:
            try:
                # Auto-acknowledge old alerts
                current_time = datetime.now()
                for alert_id, alert in list(self.alerts.items()):
                    if (current_time - alert.timestamp).total_seconds() > 3600:  # 1 hour
                        if not alert.acknowledged:
                            alert.acknowledged = True
                            self.logger.info(f"Auto-acknowledged old alert: {alert_id}")
                
                time.sleep(300)  # Process every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Alert processing error: {e}")
                time.sleep(60)
    
    def _data_cleanup_loop(self) -> None:
        """Clean up old data"""
        while self.running:
            try:
                cutoff_time = datetime.now() - self.metrics_retention
                
                # Clean old metrics
                for machine_metrics in self.gpu_metrics.values():
                    # Remove old metrics
                    while machine_metrics and machine_metrics[0].timestamp < cutoff_time:
                        machine_metrics.popleft()
                
                # Clean old performance history
                for history in self.performance_history.values():
                    while history and len(history) > 100:
                        history.popleft()
                
                time.sleep(3600)  # Clean every hour
                
            except Exception as e:
                self.logger.error(f"Data cleanup error: {e}")
                time.sleep(1800)
    
    def _broadcast_updates(self) -> None:
        """Broadcast updates to WebSocket clients"""
        if not self.websocket_connections:
            return
        
        update_data = {
            "type": "metrics_update",
            "timestamp": datetime.now().isoformat(),
            "cluster_status": self._get_cluster_status(),
            "alerts": len([a for a in self.alerts.values() if not a.acknowledged])
        }
        
        # Remove disconnected clients
        disconnected = []
        for ws in self.websocket_connections:
            try:
                asyncio.create_task(ws.send_json(update_data))
            except Exception:
                disconnected.append(ws)
        
        for ws in disconnected:
            self.websocket_connections.remove(ws)
    
    def _handle_model_event(self, event) -> None:
        """Handle model-related events"""
        if event.event_type == ModelEventType.MODEL_LOADED:
            # Track loaded model
            model_info = ModelInfo(
                model_id=event.model_id,
                machine_id=event.machine_id,
                model_type=getattr(event, 'model_type', 'unknown'),
                memory_usage_mb=getattr(event, 'vram_usage_mb', 0),
                load_time=datetime.now()
            )
            self.model_info[event.model_id] = model_info
            
        elif event.event_type == ModelEventType.MODEL_UNLOADED:
            # Remove unloaded model
            if event.model_id in self.model_info:
                del self.model_info[event.model_id]
        
        elif event.event_type == ModelEventType.VRAM_THRESHOLD_EXCEEDED:
            # Create VRAM alert
            self._create_alert(
                f"vram_threshold_{event.machine_id}",
                "warning",
                f"VRAM Threshold Exceeded",
                f"Machine {event.machine_id}: {event.used_vram_mb}MB used ({event.threshold_percentage:.1f}%)",
                event.machine_id,
                "memory"
            )
        
        elif event.event_type == ModelEventType.GPU_MEMORY_CRITICAL:
            # Create critical memory alert
            self._create_alert(
                f"gpu_critical_{event.machine_id}",
                "critical",
                f"Critical GPU Memory",
                f"Machine {event.machine_id}: Critical memory situation - {event.used_vram_mb}MB used",
                event.machine_id,
                "memory"
            )
        
        elif event.event_type in [ModelEventType.CROSS_MACHINE_MODEL_REQUEST, ModelEventType.LOAD_BALANCING_REQUIRED]:
            # Track load balancing events
            self.load_balancing_events.append({
                'timestamp': datetime.now(),
                'event_type': event.event_type.value,
                'source_machine': getattr(event, 'source_machine', ''),
                'target_machine': getattr(event, 'target_machine', ''),
                'model_id': getattr(event, 'model_id', '')
            })
    
    def _handle_memory_event(self, event) -> None:
        """Handle memory-related events"""
        if event.event_type == MemoryEventType.MEMORY_OPTIMIZATION_COMPLETED:
            # Track optimization events
            self.optimization_events.append({
                'timestamp': datetime.now(),
                'event_type': event.event_type.value,
                'machine_id': event.machine_id,
                'memory_freed_mb': getattr(event, 'memory_freed_mb', 0)
            })
    
    def _create_alert(self, alert_id: str, severity: str, title: str, message: str, machine_id: str, category: str) -> None:
        """Create a new alert"""
        alert = Alert(
            id=alert_id,
            severity=severity,
            title=title,
            message=message,
            timestamp=datetime.now(),
            machine_id=machine_id,
            category=category
        )
        
        self.alerts[alert_id] = alert
        self.logger.info(f"Alert created: {title} - {message}")
    
    def _get_cluster_status(self) -> Dict[str, Any]:
        """Get comprehensive cluster status"""
        total_memory_mb = sum(status.total_memory_mb for status in self.machine_status.values())
        used_memory_mb = sum(status.used_memory_mb for status in self.machine_status.values())
        
        # Calculate average GPU utilization
        avg_gpu_util = 0.0
        gpu_count = 0
        
        for machine_id, status in self.machine_status.items():
            metrics_key = f"{machine_id}_gpu_0"
            if metrics_key in self.gpu_metrics and self.gpu_metrics[metrics_key]:
                latest_metric = self.gpu_metrics[metrics_key][-1]
                avg_gpu_util += latest_metric.utilization_percent
                gpu_count += 1
        
        if gpu_count > 0:
            avg_gpu_util /= gpu_count
        
        return {
            'total_machines': len(self.machine_status),
            'online_machines': len([s for s in self.machine_status.values() if s.status == "online"]),
            'total_memory_mb': total_memory_mb,
            'used_memory_mb': used_memory_mb,
            'memory_utilization_percent': (used_memory_mb / max(total_memory_mb, 1)) * 100,
            'avg_gpu_utilization': avg_gpu_util,
            'total_models': len(self.model_info),
            'total_alerts': len([a for a in self.alerts.values() if not a.acknowledged]),
            'machines': {
                machine_id: {
                    'status': status.status,
                    'gpu_count': status.gpu_count,
                    'memory_mb': status.total_memory_mb,
                    'used_memory_mb': status.used_memory_mb,
                    'model_count': status.model_count,
                    'avg_gpu_utilization': self._get_machine_avg_utilization(machine_id),
                    'cpu_percent': status.cpu_percent
                }
                for machine_id, status in self.machine_status.items()
            }
        }
    
    def _get_machine_avg_utilization(self, machine_id: str) -> float:
        """Get average GPU utilization for a machine"""
        metrics_key = f"{machine_id}_gpu_0"
        if metrics_key in self.gpu_metrics and self.gpu_metrics[metrics_key]:
            recent_metrics = list(self.gpu_metrics[metrics_key])[-10:]  # Last 10 data points
            if recent_metrics:
                return sum(m.utilization_percent for m in recent_metrics) / len(recent_metrics)
        return 0.0
    
    def get_dashboard_url(self) -> str:
        """Get the dashboard URL"""
        return f"http://localhost:{self.web_port}"
    
    def shutdown(self):
        """Clean up subscriptions and resources"""
        event_bus = get_event_bus()
        for sub_id in self.subscription_ids:
            event_bus.unsubscribe(sub_id)
        
        # Close WebSocket connections
        for ws in self.websocket_connections:
            try:
                asyncio.create_task(ws.close())
            except Exception:
                pass
        
        super().shutdown()

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    dashboard = GPUMonitoringDashboard(web_port=8080)
    
    try:
        print(f"GPU Monitoring Dashboard running at: {dashboard.get_dashboard_url()}")
        
        # Keep running
        while True:
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("Shutting down GPU Monitoring Dashboard...")
        dashboard.shutdown() 