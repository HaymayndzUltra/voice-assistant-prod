#!/usr/bin/env python3
"""
PHASE 1 WEEK 2 DAY 5: Advanced Health Monitoring System
Real-time system health tracking and automated recovery
"""

import time
import json
import threading
import psutil
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import deque
import zmq

logger = logging.getLogger(__name__)

@dataclass
class HealthMetric:
    """Health metric definition"""
    metric_name: str
    metric_type: str  # 'performance', 'resource', 'availability', 'error'
    current_value: Any
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    unit: str = ""
    timestamp: float = 0.0

@dataclass
class AgentHealthStatus:
    """Comprehensive agent health status"""
    agent_name: str
    overall_status: str  # 'healthy', 'warning', 'critical', 'unknown'
    last_heartbeat: float
    uptime_seconds: float
    metrics: Dict[str, HealthMetric]
    recent_errors: List[Dict[str, Any]]
    performance_score: float
    recovery_actions: List[str]

class AdvancedHealthMonitor:
    """
    Advanced Health Monitoring System for Enhanced BaseAgent
    - Real-time health metrics collection
    - Automated anomaly detection
    - Self-healing capabilities
    - System-wide health dashboard
    """
    
    def __init__(self, monitoring_port: int = 8901):
        self.monitoring_port = monitoring_port
        self.running = False
        
        # Health data storage
        self.agent_health: Dict[str, AgentHealthStatus] = {}
        self.system_metrics: Dict[str, Any] = {}
        self.health_history: Dict[str, deque] = {}
        
        # Monitoring configuration
        self.monitoring_interval = 30.0  # 30 seconds
        self.history_retention = 1000  # Keep last 1000 entries per agent
        
        # Thread safety
        self.health_lock = threading.RLock()
        self.monitor_thread = None
        self.alert_thread = None
        
        # ZMQ setup
        self.context = zmq.Context()
        self.monitor_socket = None
        
        # Alert and recovery system
        self.alert_callbacks: List[Callable] = []
        self.recovery_handlers: Dict[str, Callable] = {}
        self.automated_recovery_enabled = True
        
        # Health thresholds
        self.default_thresholds = {
            'cpu_usage': {'warning': 80.0, 'critical': 95.0},
            'memory_usage': {'warning': 85.0, 'critical': 95.0},
            'response_time': {'warning': 5.0, 'critical': 10.0},
            'error_rate': {'warning': 5.0, 'critical': 10.0},
            'heartbeat_age': {'warning': 60.0, 'critical': 120.0}
        }
    
    def start(self):
        """Start the advanced health monitoring system"""
        if self.running:
            return
        
        self.running = True
        
        # Setup ZMQ monitoring socket
        self.monitor_socket = self.context.socket(zmq.REP)
        self.monitor_socket.bind(f"tcp://*:{self.monitoring_port}")
        
        # Start monitoring threads
        self.monitor_thread = threading.Thread(target=self._run_health_monitor, daemon=True)
        self.alert_thread = threading.Thread(target=self._run_alert_system, daemon=True)
        
        self.monitor_thread.start()
        self.alert_thread.start()
        
        logger.info(f"Advanced Health Monitor started on port {self.monitoring_port}")
    
    def stop(self):
        """Stop the health monitoring system"""
        self.running = False
        
        if self.monitor_socket:
            self.monitor_socket.close()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        
        if self.alert_thread:
            self.alert_thread.join(timeout=1.0)
        
        logger.info("Advanced Health Monitor stopped")
    
    def register_agent_for_monitoring(self, agent_name: str, 
                                    initial_metrics: Optional[Dict[str, HealthMetric]] = None):
        """Register agent for health monitoring"""
        with self.health_lock:
            current_time = time.time()
            
            metrics = initial_metrics or {}
            
            health_status = AgentHealthStatus(
                agent_name=agent_name,
                overall_status='healthy',
                last_heartbeat=current_time,
                uptime_seconds=0.0,
                metrics=metrics,
                recent_errors=[],
                performance_score=1.0,
                recovery_actions=[]
            )
            
            self.agent_health[agent_name] = health_status
            self.health_history[agent_name] = deque(maxlen=self.history_retention)
            
            logger.info(f"Agent {agent_name} registered for health monitoring")
    
    def update_agent_health(self, agent_name: str, metrics: Dict[str, Any],
                           errors: Optional[List[Dict[str, Any]]] = None):
        """Update agent health metrics"""
        with self.health_lock:
            if agent_name not in self.agent_health:
                self.register_agent_for_monitoring(agent_name)
            
            agent_health = self.agent_health[agent_name]
            current_time = time.time()
            
            # Update heartbeat
            agent_health.last_heartbeat = current_time
            
            # Update metrics
            for metric_name, metric_value in metrics.items():
                if isinstance(metric_value, dict) and 'value' in metric_value:
                    # Detailed metric format
                    health_metric = HealthMetric(
                        metric_name=metric_name,
                        metric_type=metric_value.get('type', 'performance'),
                        current_value=metric_value['value'],
                        threshold_warning=metric_value.get('warning_threshold'),
                        threshold_critical=metric_value.get('critical_threshold'),
                        unit=metric_value.get('unit', ''),
                        timestamp=current_time
                    )
                else:
                    # Simple metric format
                    health_metric = HealthMetric(
                        metric_name=metric_name,
                        metric_type='performance',
                        current_value=metric_value,
                        timestamp=current_time
                    )
                
                agent_health.metrics[metric_name] = health_metric
            
            # Update errors
            if errors:
                agent_health.recent_errors.extend(errors)
                # Keep only recent errors (last 50)
                agent_health.recent_errors = agent_health.recent_errors[-50:]
            
            # Calculate performance score
            agent_health.performance_score = self._calculate_performance_score(agent_health)
            
            # Determine overall health status
            agent_health.overall_status = self._determine_health_status(agent_health)
            
            # Add to history
            health_snapshot = {
                'timestamp': current_time,
                'status': agent_health.overall_status,
                'performance_score': agent_health.performance_score,
                'metrics': {name: metric.current_value for name, metric in agent_health.metrics.items()},
                'error_count': len(agent_health.recent_errors)
            }
            
            self.health_history[agent_name].append(health_snapshot)
    
    def _calculate_performance_score(self, agent_health: AgentHealthStatus) -> float:
        """Calculate agent performance score (0.0 to 1.0)"""
        if not agent_health.metrics:
            return 1.0
        
        score_components = []
        
        for metric_name, metric in agent_health.metrics.items():
            if metric.threshold_critical is not None and metric.threshold_warning is not None:
                value = float(metric.current_value) if isinstance(metric.current_value, (int, float)) else 0.0
                
                # Calculate metric score based on thresholds
                if metric_name in ['cpu_usage', 'memory_usage', 'error_rate', 'response_time']:
                    # Lower is better
                    if value <= metric.threshold_warning:
                        metric_score = 1.0
                    elif value <= metric.threshold_critical:
                        # Linear degradation between warning and critical
                        range_size = metric.threshold_critical - metric.threshold_warning
                        metric_score = max(0.1, 1.0 - ((value - metric.threshold_warning) / range_size) * 0.8)
                    else:
                        metric_score = 0.1
                else:
                    # Higher is better (throughput, availability, etc.)
                    if value >= metric.threshold_warning:
                        metric_score = 1.0
                    elif value >= metric.threshold_critical:
                        range_size = metric.threshold_warning - metric.threshold_critical
                        metric_score = max(0.1, 1.0 - ((metric.threshold_warning - value) / range_size) * 0.8)
                    else:
                        metric_score = 0.1
                
                score_components.append(metric_score)
        
        # Error penalty
        error_penalty = min(0.5, len(agent_health.recent_errors) * 0.02)  # 2% per error, max 50%
        error_factor = 1.0 - error_penalty
        
        # Calculate overall score
        if score_components:
            base_score = sum(score_components) / len(score_components)
        else:
            base_score = 1.0
        
        return max(0.0, min(1.0, base_score * error_factor))
    
    def _determine_health_status(self, agent_health: AgentHealthStatus) -> str:
        """Determine overall health status based on metrics"""
        current_time = time.time()
        
        # Check heartbeat age
        heartbeat_age = current_time - agent_health.last_heartbeat
        if heartbeat_age > self.default_thresholds['heartbeat_age']['critical']:
            return 'critical'
        elif heartbeat_age > self.default_thresholds['heartbeat_age']['warning']:
            return 'warning'
        
        # Check critical metrics
        critical_violations = 0
        warning_violations = 0
        
        for metric_name, metric in agent_health.metrics.items():
            if metric.threshold_critical is not None:
                value = float(metric.current_value) if isinstance(metric.current_value, (int, float)) else 0.0
                
                if metric_name in ['cpu_usage', 'memory_usage', 'error_rate', 'response_time']:
                    # Lower is better
                    if value > metric.threshold_critical:
                        critical_violations += 1
                    elif value > metric.threshold_warning:
                        warning_violations += 1
                else:
                    # Higher is better
                    if value < metric.threshold_critical:
                        critical_violations += 1
                    elif value < metric.threshold_warning:
                        warning_violations += 1
        
        # Determine status based on violations
        if critical_violations > 0:
            return 'critical'
        elif warning_violations > 0 or agent_health.performance_score < 0.7:
            return 'warning'
        else:
            return 'healthy'
    
    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive system health summary"""
        with self.health_lock:
            current_time = time.time()
            
            # Agent status counts
            status_counts = {'healthy': 0, 'warning': 0, 'critical': 0, 'unknown': 0}
            total_agents = len(self.agent_health)
            
            # Performance metrics
            performance_scores = []
            system_errors = 0
            
            agent_details = {}
            
            for agent_name, agent_health in self.agent_health.items():
                status_counts[agent_health.overall_status] += 1
                performance_scores.append(agent_health.performance_score)
                system_errors += len(agent_health.recent_errors)
                
                agent_details[agent_name] = {
                    'status': agent_health.overall_status,
                    'performance_score': agent_health.performance_score,
                    'last_heartbeat': agent_health.last_heartbeat,
                    'heartbeat_age': current_time - agent_health.last_heartbeat,
                    'error_count': len(agent_health.recent_errors),
                    'uptime': agent_health.uptime_seconds,
                    'key_metrics': {
                        name: {
                            'value': metric.current_value,
                            'status': self._get_metric_status(metric)
                        } for name, metric in agent_health.metrics.items()
                    }
                }
            
            # System-wide calculations
            avg_performance = sum(performance_scores) / len(performance_scores) if performance_scores else 0.0
            health_percentage = (status_counts['healthy'] / total_agents * 100) if total_agents > 0 else 0.0
            
            # System resource metrics
            system_resources = self._get_system_resources()
            
            return {
                'timestamp': current_time,
                'system_status': self._get_overall_system_status(status_counts),
                'total_agents': total_agents,
                'status_distribution': status_counts,
                'health_percentage': health_percentage,
                'average_performance_score': avg_performance,
                'total_system_errors': system_errors,
                'system_resources': system_resources,
                'agent_details': agent_details,
                'alerts': self._get_active_alerts()
            }
    
    def _get_metric_status(self, metric: HealthMetric) -> str:
        """Get metric status based on thresholds"""
        if metric.threshold_critical is None:
            return 'unknown'
        
        value = float(metric.current_value) if isinstance(metric.current_value, (int, float)) else 0.0
        
        if metric.metric_name in ['cpu_usage', 'memory_usage', 'error_rate', 'response_time']:
            # Lower is better
            if value > metric.threshold_critical:
                return 'critical'
            elif value > metric.threshold_warning:
                return 'warning'
            else:
                return 'healthy'
        else:
            # Higher is better
            if value < metric.threshold_critical:
                return 'critical'
            elif value < metric.threshold_warning:
                return 'warning'
            else:
                return 'healthy'
    
    def _get_overall_system_status(self, status_counts: Dict[str, int]) -> str:
        """Determine overall system status"""
        if status_counts['critical'] > 0:
            return 'critical'
        elif status_counts['warning'] > 0:
            return 'warning'
        elif status_counts['healthy'] > 0:
            return 'healthy'
        else:
            return 'unknown'
    
    def _get_system_resources(self) -> Dict[str, Any]:
        """Get system resource metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_usage': cpu_percent,
                'memory_usage': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_usage': disk.percent,
                'disk_free_gb': disk.free / (1024**3),
                'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
            }
        except Exception as e:
            logger.error(f"Failed to get system resources: {e}")
            return {}
    
    def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get current active alerts"""
        alerts = []
        current_time = time.time()
        
        for agent_name, agent_health in self.agent_health.items():
            if agent_health.overall_status in ['warning', 'critical']:
                alert = {
                    'agent_name': agent_name,
                    'severity': agent_health.overall_status,
                    'timestamp': current_time,
                    'performance_score': agent_health.performance_score,
                    'issues': []
                }
                
                # Check specific metric issues
                for metric_name, metric in agent_health.metrics.items():
                    metric_status = self._get_metric_status(metric)
                    if metric_status in ['warning', 'critical']:
                        alert['issues'].append({
                            'metric': metric_name,
                            'current_value': metric.current_value,
                            'severity': metric_status,
                            'threshold_warning': metric.threshold_warning,
                            'threshold_critical': metric.threshold_critical
                        })
                
                # Check heartbeat issues
                heartbeat_age = current_time - agent_health.last_heartbeat
                if heartbeat_age > self.default_thresholds['heartbeat_age']['warning']:
                    severity = 'critical' if heartbeat_age > self.default_thresholds['heartbeat_age']['critical'] else 'warning'
                    alert['issues'].append({
                        'metric': 'heartbeat_age',
                        'current_value': heartbeat_age,
                        'severity': severity,
                        'threshold_warning': self.default_thresholds['heartbeat_age']['warning'],
                        'threshold_critical': self.default_thresholds['heartbeat_age']['critical']
                    })
                
                alerts.append(alert)
        
        return alerts
    
    def trigger_recovery_action(self, agent_name: str, action_type: str) -> bool:
        """Trigger automated recovery action for agent"""
        if not self.automated_recovery_enabled:
            logger.info(f"Automated recovery disabled, skipping action {action_type} for {agent_name}")
            return False
        
        try:
            if action_type in self.recovery_handlers:
                handler = self.recovery_handlers[action_type]
                result = handler(agent_name)
                
                # Log recovery action
                with self.health_lock:
                    if agent_name in self.agent_health:
                        self.agent_health[agent_name].recovery_actions.append({
                            'action': action_type,
                            'timestamp': time.time(),
                            'result': 'success' if result else 'failed'
                        })
                
                logger.info(f"Recovery action {action_type} for {agent_name}: {'success' if result else 'failed'}")
                return result
            else:
                logger.warning(f"No recovery handler for action type: {action_type}")
                return False
                
        except Exception as e:
            logger.error(f"Recovery action {action_type} failed for {agent_name}: {e}")
            return False
    
    def add_recovery_handler(self, action_type: str, handler: Callable[[str], bool]):
        """Add recovery handler for specific action type"""
        self.recovery_handlers[action_type] = handler
        logger.info(f"Added recovery handler for action type: {action_type}")
    
    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add alert callback for notifications"""
        self.alert_callbacks.append(callback)
    
    def _run_health_monitor(self):
        """Main health monitoring loop"""
        while self.running:
            try:
                if self.monitor_socket.poll(timeout=1000):  # 1 second timeout
                    message = self.monitor_socket.recv_json(zmq.NOBLOCK)
                    response = self._handle_health_request(message)
                    self.monitor_socket.send_json(response)
            except zmq.Again:
                continue
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                time.sleep(0.1)
    
    def _handle_health_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle health monitoring requests"""
        try:
            request_type = request.get('type', '')
            
            if request_type == 'update_health':
                agent_name = request['agent_name']
                metrics = request['metrics']
                errors = request.get('errors', [])
                
                self.update_agent_health(agent_name, metrics, errors)
                return {'status': 'success'}
            
            elif request_type == 'get_health':
                agent_name = request.get('agent_name')
                
                if agent_name:
                    # Get specific agent health
                    if agent_name in self.agent_health:
                        return {'status': 'success', 'health': asdict(self.agent_health[agent_name])}
                    else:
                        return {'status': 'not_found'}
                else:
                    # Get system health summary
                    summary = self.get_system_health_summary()
                    return {'status': 'success', 'system_health': summary}
            
            elif request_type == 'trigger_recovery':
                agent_name = request['agent_name']
                action_type = request['action_type']
                
                result = self.trigger_recovery_action(agent_name, action_type)
                return {'status': 'success', 'recovery_triggered': result}
            
            else:
                return {'status': 'error', 'message': f'Unknown request type: {request_type}'}
        
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _run_alert_system(self):
        """Run alert system for proactive monitoring"""
        while self.running:
            try:
                # Check for alerts every minute
                time.sleep(60.0)
                
                alerts = self._get_active_alerts()
                
                for alert in alerts:
                    # Trigger alert callbacks
                    for callback in self.alert_callbacks:
                        try:
                            callback(alert)
                        except Exception as e:
                            logger.error(f"Alert callback error: {e}")
                    
                    # Consider automated recovery
                    if alert['severity'] == 'critical':
                        agent_name = alert['agent_name']
                        
                        # Check if recovery actions should be triggered
                        for issue in alert['issues']:
                            metric = issue['metric']
                            
                            if metric == 'heartbeat_age':
                                self.trigger_recovery_action(agent_name, 'restart_agent')
                            elif metric in ['memory_usage', 'cpu_usage']:
                                self.trigger_recovery_action(agent_name, 'resource_optimization')
                            elif metric == 'error_rate':
                                self.trigger_recovery_action(agent_name, 'error_recovery')
                
            except Exception as e:
                logger.error(f"Alert system error: {e}")
                time.sleep(5.0)


class HealthMonitoringClient:
    """Client for health monitoring system"""
    
    def __init__(self, monitor_host: str = 'localhost', monitor_port: int = 8901):
        self.monitor_host = monitor_host
        self.monitor_port = monitor_port
        self.context = zmq.Context()
        self.socket = None
    
    def connect(self):
        """Connect to health monitor"""
        if not self.socket:
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(f"tcp://{self.monitor_host}:{self.monitor_port}")
    
    def disconnect(self):
        """Disconnect from health monitor"""
        if self.socket:
            self.socket.close()
            self.socket = None
    
    def update_health(self, agent_name: str, metrics: Dict[str, Any],
                     errors: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Update agent health"""
        self.connect()
        
        request = {
            'type': 'update_health',
            'agent_name': agent_name,
            'metrics': metrics,
            'errors': errors or []
        }
        
        try:
            self.socket.send_json(request)
            response = self.socket.recv_json()
            return response.get('status') == 'success'
        except Exception as e:
            logger.error(f"Failed to update health: {e}")
            return False
    
    def get_system_health(self) -> Optional[Dict[str, Any]]:
        """Get system health summary"""
        self.connect()
        
        request = {'type': 'get_health'}
        
        try:
            self.socket.send_json(request)
            response = self.socket.recv_json()
            
            if response.get('status') == 'success':
                return response.get('system_health')
            
            return None
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return None


# Global health monitor instance
_global_health_monitor = None

def get_health_monitor(monitoring_port: int = 8901) -> AdvancedHealthMonitor:
    """Get global health monitor instance"""
    global _global_health_monitor
    if _global_health_monitor is None:
        _global_health_monitor = AdvancedHealthMonitor(monitoring_port)
    return _global_health_monitor

def get_health_monitoring_client(monitor_host: str = 'localhost',
                                monitor_port: int = 8901) -> HealthMonitoringClient:
    """Get health monitoring client"""
    return HealthMonitoringClient(monitor_host, monitor_port) 