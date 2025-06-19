#!/usr/bin/env python3
"""
System Digital Twin Agent

This agent monitors real-time system metrics through Prometheus and provides
a simulation endpoint to predict the impact of future actions on system resources.
It serves as a predictive analytics layer for resource management decisions.
"""

import os
import sys
import time
import json
import logging
import threading
import zmq
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union, cast

# Add project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import config parser utility with fallback
try:
    from agents.utils.config_parser import parse_agent_args
    _agent_args = parse_agent_args()
except ImportError:
    class DummyArgs:
        host = 'localhost'
    _agent_args = DummyArgs()

# Configure logging
log_file_path = 'logs/system_digital_twin.log'
log_directory = os.path.dirname(log_file_path)
os.makedirs(log_directory, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file_path)
    ]
)
logger = logging.getLogger("SystemDigitalTwinAgent")

# ZMQ ports
DIGITAL_TWIN_PORT = 7120
DIGITAL_TWIN_HEALTH_PORT = 7121

# Default configuration
DEFAULT_CONFIG = {
    "prometheus_url": "http://prometheus:9090",
    "metrics_poll_interval": 5,  # seconds
    "metrics_history_length": 60,  # Keep 60 data points (5 min at 5s intervals)
    "vram_capacity_mb": 24000,  # Default for RTX 4090
    "cpu_cores": 16,  # Default value
    "ram_capacity_mb": 32000,  # Default value
    "network_baseline_ms": 50,  # Default expected network latency
}

class SystemDigitalTwin:
    """
    A digital twin of the voice assistant system that monitors real-time metrics
    and provides predictive analytics for resource management.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, port: int = None):
        """
        Initialize the System Digital Twin agent.
        
        Args:
            config: Configuration dictionary that can override defaults
            port: Optional port override for testing
        """
        # Merge provided config with defaults
        self.config = DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)
            
        # Set up ports
        self.main_port = port if port else DIGITAL_TWIN_PORT
        self.health_port = self.main_port + 1
        
        # Initialize ZMQ
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.main_port}")
        
        # Initialize Prometheus client with error handling
        self.prom = None
        try:
            from prometheus_api_client import PrometheusConnect
            self.prom = PrometheusConnect(url=self.config["prometheus_url"], disable_ssl=True)
            logger.info("Prometheus client initialized successfully")
        except ImportError:
            logger.warning("Prometheus client not available, using mock metrics")
        except Exception as e:
            logger.warning(f"Failed to initialize Prometheus client: {e}, using mock metrics")
            
        # Initialize metrics storage
        self.metrics_history = {
            "cpu_usage": [],
            "vram_usage_mb": [],
            "ram_usage_mb": [],
            "network_latency_ms": [],
            "timestamps": []
        }
        
        # Flag to control background threads
        self.running = True
        
        # Start metrics collection thread
        self.metrics_thread = threading.Thread(target=self._collect_metrics_loop)
        self.metrics_thread.daemon = True
        self.metrics_thread.start()
        
        logger.info(f"SystemDigitalTwin initialized on port {self.main_port}")
        
    def _collect_metrics_loop(self):
        """Background thread that periodically collects system metrics"""
        while self.running:
            try:
                # Collect current metrics
                metrics = self._fetch_current_metrics()
                
                # Store metrics with timestamp
                timestamp = datetime.now()
                self.metrics_history["timestamps"].append(timestamp)
                self.metrics_history["cpu_usage"].append(metrics["cpu_usage"])
                self.metrics_history["vram_usage_mb"].append(metrics["vram_usage_mb"])
                self.metrics_history["ram_usage_mb"].append(metrics["ram_usage_mb"])
                self.metrics_history["network_latency_ms"].append(metrics["network_latency_ms"])
                
                # Trim history to configured length
                max_len = self.config["metrics_history_length"]
                if len(self.metrics_history["timestamps"]) > max_len:
                    for key in self.metrics_history:
                        self.metrics_history[key] = self.metrics_history[key][-max_len:]
                
                logger.debug(f"Collected metrics: {metrics}")
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
            
            # Wait for next collection interval
            time.sleep(self.config["metrics_poll_interval"])
    
    def _fetch_current_metrics(self) -> Dict[str, float]:
        """
        Fetch current system metrics from Prometheus or return mock data.
        
        Returns:
            Dictionary containing current system metrics
        """
        try:
            if self.prom is not None:
                # Query Prometheus for metrics
                cpu_usage = self._get_prometheus_value('node_cpu_utilization')
                vram_usage = self._get_prometheus_value('nvidia_gpu_memory_used_bytes')
                ram_usage = self._get_prometheus_value('node_memory_MemUsed_bytes')
                network_latency = self._get_prometheus_value('network_round_trip_time_milliseconds')
                
                # Convert memory values to MB if they exist
                vram_mb = float(vram_usage) / (1024 * 1024) if vram_usage is not None else 0.0
                ram_mb = float(ram_usage) / (1024 * 1024) if ram_usage is not None else 0.0
                
                # Return collected metrics
                return {
                    "cpu_usage": float(cpu_usage) if cpu_usage is not None else 0.0,
                    "vram_usage_mb": vram_mb,
                    "ram_usage_mb": ram_mb,
                    "network_latency_ms": float(network_latency) if network_latency is not None else self.config["network_baseline_ms"]
                }
            else:
                # Return mock metrics
                return {
                    "cpu_usage": 25.0,  # Mock 25% CPU usage
                    "vram_usage_mb": 8000.0,  # Mock 8GB VRAM usage
                    "ram_usage_mb": 16000.0,  # Mock 16GB RAM usage
                    "network_latency_ms": self.config["network_baseline_ms"]
                }
        except Exception as e:
            logger.error(f"Error fetching metrics: {e}")
            # Return fallback values
            return {
                "cpu_usage": 0.0,
                "vram_usage_mb": 0.0,
                "ram_usage_mb": 0.0,
                "network_latency_ms": self.config["network_baseline_ms"]
            }
    
    def _get_prometheus_value(self, metric_name: str) -> Optional[float]:
        """
        Get the latest value for a specific Prometheus metric.
        
        Args:
            metric_name: Name of the Prometheus metric to query
            
        Returns:
            Latest value for the metric or None if not available
        """
        try:
            if self.prom is None:
                return None
            # Query Prometheus for the metric
            metric_data = self.prom.get_current_metric_value(metric_name)
            if metric_data and len(metric_data) > 0:
                return float(metric_data[0]['value'][1])
            return None
        except Exception as e:
            logger.warning(f"Failed to get metric {metric_name}: {e}")
            return None
    
    def _get_current_state(self) -> Dict[str, float]:
        """
        Get the current system state based on the latest metrics.
        
        Returns:
            Dictionary with the current system state metrics
        """
        if not self.metrics_history["timestamps"]:
            # No metrics collected yet, return current fetch
            return self._fetch_current_metrics()
        
        # Return the most recent metrics
        return {
            "cpu_usage": self.metrics_history["cpu_usage"][-1],
            "vram_usage_mb": self.metrics_history["vram_usage_mb"][-1],
            "ram_usage_mb": self.metrics_history["ram_usage_mb"][-1],
            "network_latency_ms": self.metrics_history["network_latency_ms"][-1]
        }
    
    def simulate_load(self, load_type: str, value: float) -> Dict[str, Any]:
        """
        Simulate the impact of additional load on system resources.
        
        Args:
            load_type: Type of resource to simulate (vram, cpu, ram, network)
            value: Amount of additional load to simulate
            
        Returns:
            Prediction dictionary with current state, projected state, and recommendation
        """
        current_state = self._get_current_state()
        
        # Initialize response
        response = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "current_state": current_state,
            "load_type": load_type,
            "requested_value": value,
            "recommendation": "proceed"  # Default recommendation
        }
        
        # Simulate different resource types
        if load_type == "vram":
            current_vram = current_state["vram_usage_mb"]
            projected_vram = current_vram + value
            vram_capacity = self.config["vram_capacity_mb"]
            
            response["current_vram_mb"] = current_vram
            response["requested_vram_mb"] = value
            response["projected_vram_mb"] = projected_vram
            response["vram_capacity_mb"] = vram_capacity
            
            # Check if we would exceed capacity
            if projected_vram > vram_capacity * 0.95:  # 95% threshold
                response["recommendation"] = "deny_insufficient_resources"
                response["reason"] = f"Projected VRAM usage ({projected_vram:.2f} MB) would exceed 95% of capacity ({vram_capacity} MB)"
        
        elif load_type == "cpu":
            current_cpu = current_state["cpu_usage"]
            projected_cpu = min(100.0, current_cpu + value)  # Cap at 100%
            
            response["current_cpu_percent"] = current_cpu
            response["requested_cpu_percent"] = value
            response["projected_cpu_percent"] = projected_cpu
            
            # Check if CPU would be overloaded
            if projected_cpu > 90.0:  # 90% threshold
                response["recommendation"] = "caution_high_cpu"
                response["reason"] = f"Projected CPU usage ({projected_cpu:.2f}%) would exceed 90% threshold"
        
        elif load_type == "ram":
            current_ram = current_state["ram_usage_mb"]
            projected_ram = current_ram + value
            ram_capacity = self.config["ram_capacity_mb"]
            
            response["current_ram_mb"] = current_ram
            response["requested_ram_mb"] = value
            response["projected_ram_mb"] = projected_ram
            response["ram_capacity_mb"] = ram_capacity
            
            # Check if RAM would be overloaded
            if projected_ram > ram_capacity * 0.9:  # 90% threshold
                response["recommendation"] = "deny_insufficient_resources"
                response["reason"] = f"Projected RAM usage ({projected_ram:.2f} MB) would exceed 90% of capacity ({ram_capacity} MB)"
        
        elif load_type == "network":
            current_latency = current_state["network_latency_ms"]
            # Network impact is more complex - we use a simple model here
            # Assuming latency increases proportionally to bandwidth usage
            impact_factor = 1.5  # Empirical factor
            projected_latency = current_latency + (value * impact_factor)
            
            response["current_latency_ms"] = current_latency
            response["requested_bandwidth_mb"] = value
            response["projected_latency_ms"] = projected_latency
            
            # Check if latency would be too high
            if projected_latency > 200.0:  # 200ms threshold
                response["recommendation"] = "caution_high_latency"
                response["reason"] = f"Projected network latency ({projected_latency:.2f} ms) would exceed 200ms threshold"
        
        else:
            response["status"] = "error"
            response["error"] = f"Unknown load type: {load_type}"
            response["recommendation"] = "error_invalid_request"
        
        return response
    
    def _health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            'status': 'success',
            'agent': 'SystemDigitalTwin',
            'timestamp': datetime.now().isoformat(),
            'metrics_thread_alive': self.metrics_thread.is_alive() if hasattr(self, 'metrics_thread') else False,
            'metrics_history_length': len(self.metrics_history["timestamps"]),
            'last_metrics_update': self.metrics_history["timestamps"][-1].isoformat() if self.metrics_history["timestamps"] else None,
            'prometheus_connected': self._check_prometheus_connection(),
            'port': self.main_port
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an incoming request to the digital twin.
        
        Args:
            request: Request dictionary with action and parameters
            
        Returns:
            Response dictionary
        """
        # First check if it's a health check request
        if request.get("action") in ["ping", "health", "health_check"]:
            return self._health_check()
            
        action = request.get("action", "")
        
        if action == "simulate_load":
            load_type = request.get("load_type", "")
            try:
                value = float(request.get("value", 0))
            except (TypeError, ValueError):
                return {
                    "status": "error",
                    "error": "Invalid value parameter - must be a number"
                }
            
            # Validate load type
            if load_type not in ["vram", "cpu", "ram", "network"]:
                return {
                    "status": "error",
                    "error": f"Invalid load_type: {load_type}. Must be one of: vram, cpu, ram, network"
                }
            
            # Validate value
            if value <= 0:
                return {
                    "status": "error",
                    "error": f"Invalid value: {value}. Must be positive"
                }
            
            # Run simulation
            return self.simulate_load(load_type, value)
        
        elif action == "get_metrics":
            # Return current system state
            return {
                "status": "success",
                "metrics": self._get_current_state()
            }
        
        elif action == "get_history":
            # Return metrics history
            return {
                "status": "success",
                "history": {
                    "timestamps": [ts.isoformat() for ts in self.metrics_history["timestamps"]],
                    "cpu_usage": self.metrics_history["cpu_usage"],
                    "vram_usage_mb": self.metrics_history["vram_usage_mb"],
                    "ram_usage_mb": self.metrics_history["ram_usage_mb"],
                    "network_latency_ms": self.metrics_history["network_latency_ms"]
                }
            }
        
        else:
            return {
                "status": "error",
                "error": f"Unknown action: {action}"
            }
    
    def _check_prometheus_connection(self) -> bool:
        """Check if Prometheus connection is working."""
        try:
            if self.prom is None:
                return False
            self.prom.check_prometheus_connection()
            return True
        except Exception:
            return False
    
    def run(self):
        """Main run loop that handles incoming requests."""
        logger.info(f"SystemDigitalTwin starting on port {self.main_port}")
        try:
            while self.running:
                try:
                    # Wait for messages with timeout
                    if self.socket.poll(1000) == 0:
                        continue
                    
                    # Receive and process message
                    message = self.socket.recv_json()
                    logger.debug(f"Received request: {message}")
                    response = self.handle_request(message)
                    self.socket.send_json(response)
                    
                except zmq.error.ZMQError as e:
                    if e.errno == zmq.EAGAIN:
                        continue
                    logger.error(f"ZMQ error in main loop: {e}")
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info("Cleaning up SystemDigitalTwin resources...")
        self.running = False
        if hasattr(self, 'metrics_thread'):
            self.metrics_thread.join(timeout=5)
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        logger.info("Cleanup complete")
    
    def stop(self):
        """Stop the agent gracefully."""
        self.running = False

if __name__ == "__main__":
    agent = SystemDigitalTwin()
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("SystemDigitalTwin interrupted")
    finally:
        agent.cleanup() 