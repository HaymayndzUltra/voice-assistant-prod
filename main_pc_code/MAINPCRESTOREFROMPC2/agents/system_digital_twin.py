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

# Define fallback functions
def fallback_get_env(key, default=None):
    """Fallback implementation for get_env"""
    return os.environ.get(key, default)

# Import config parser utility with fallback
try:
from main_pc_code.agents.utils.config_parser import parse_agent_args
    except ImportError as e:
        print(f"Import error: {e}")
from main_pc_code.utils.service_discovery_client import discover_service, register_service, get_service_address
from main_pc_code.utils.env_loader import get_env
from main_pc_code.src.network.secure_zmq import is_secure_zmq_enabled, configure_secure_client, configure_secure_server, start_auth
    _agent_args = parse_agent_args()
except ImportError:
    logger = logging.getLogger("SystemDigitalTwinAgent")
    logger.error("Failed to import required modules. Falling back to defaults.")
    class DummyArgs:
        host = '0.0.0.0'  # Use 0.0.0.0 to allow external connections
    _agent_args = DummyArgs()
    # Define fallback functions if imports fail
    get_env = fallback_get_env
    
    def is_secure_zmq_enabled():
        return False
    
    def configure_secure_server(socket):
        return socket
    
    def start_auth():
        pass
    
    def register_service(name, port, additional_info=None):
        return {"status": "SUCCESS", "message": "Fallback registration"}

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

# Get bind address from environment variables with default to 0.0.0.0 for Docker compatibility
BIND_ADDRESS = get_env('BIND_ADDRESS', '0.0.0.0')

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

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
            
        # Set up ports and host from configuration
        # Use parameter port first, then config, then fall back to default
        self.main_port = port if port is not None else self.config.get('port', 7120)
        self.health_port = self.config.get('health_check_port', 8100)
        logger.info(f"Initializing with ZMQ port {self.main_port} and Health port {self.health_port} from configuration.")
        
        # Initialize ZMQ
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        
        # Check if secure ZMQ is enabled
        secure_zmq = is_secure_zmq_enabled()
        if secure_zmq:
            try:
                # First ensure the authenticator is running
                start_auth()
                
                # Then configure the socket
                self.socket = configure_secure_server(self.socket)
                logger.info("Secure ZMQ configured successfully")
            except Exception as e:
                logger.error(f"Failed to configure secure ZMQ: {e}, continuing with standard ZMQ")
                secure_zmq = False
        
        # Bind to address using BIND_ADDRESS for Docker compatibility
        socket_address = f"tcp://{BIND_ADDRESS}:{self.main_port}"
        logger.info(f"Attempting to bind to {socket_address}")
        self.socket.bind(socket_address)
        logger.info(f"Successfully bound to {socket_address}")
        
        # Register with service discovery
        self._register_service()
        
        # Save secure ZMQ flag for future reference
        self.secure_zmq_enabled = secure_zmq
        
        # Initialize Prometheus client with error handling
        self.prom = None
        try:
            from prometheus_api_client import PrometheusConnect
    except ImportError as e:
        print(f"Import error: {e}")
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
        
        # Initialize agent registry
        self.registered_agents = {}
        
        # Initialize service registry for service discovery
        self.service_registry = {}
        
        # Add self to agent registry
        self._register_agent("SystemDigitalTwin", "MainPC", "HEALTHY", datetime.now().isoformat())
        
        # Track VRAM usage from ModelManagerAgent
        self.vram_metrics = {
            "mainpc_vram_total_mb": self.config.get("vram_capacity_mb", 24000),  # Default 24GB for RTX 4090
            "mainpc_vram_used_mb": 0,
            "mainpc_vram_free_mb": self.config.get("vram_capacity_mb", 24000),
            "pc2_vram_total_mb": 12000,  # Default 12GB for RTX 3060
            "pc2_vram_used_mb": 0,
            "pc2_vram_free_mb": 12000,
            "loaded_models": {},
            "last_update": datetime.now().isoformat()
        }
        
        # Flag to control background threads
        self.running = True
        
        # Start metrics collection thread
        self.metrics_thread = threading.Thread(target=self._collect_metrics_loop)
        self.metrics_thread.daemon = True
        self.metrics_thread.start()
        
        logger.info(f"SystemDigitalTwin initialized on port {self.main_port}" + 
                   f" with {'secure' if secure_zmq else 'standard'} ZMQ")
    
    def _register_service(self):
        """Register this agent with the service discovery system"""
        try:
            register_result = register_service(
                name="SystemDigitalTwin",
                port=self.main_port,
                additional_info={
                    "health_check_port": self.health_port,
                    "capabilities": ["system_monitoring", "resource_management", "predictive_analytics"],
                    "status": "running"
                }
            )
            if register_result and register_result.get("status") == "SUCCESS":
                logger.info("Successfully registered with service discovery")
            else:
                logger.warning(f"Service registration failed: {register_result.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error registering service: {e}")
        
    def _register_agent(self, agent_name: str, location: str, status: str, timestamp: str) -> None:
        """
        Register an agent in the system.
        
        Args:
            agent_name: Name of the agent
            location: Location of the agent (MainPC/PC2)
            status: Current status of the agent (HEALTHY/UNHEALTHY/NO_RESPONSE)
            timestamp: ISO-formatted timestamp of the last status update
        """
        self.registered_agents[agent_name] = {
            "location": location,
            "status": status,
            "last_seen": timestamp
        }
        logger.info(f"Registered agent {agent_name} at {location} with status {status}")
        
    def update_agent_status(self, agent_name: str, status: str, location: str = None) -> Dict[str, Any]:
        """
        Update the status of a registered agent or register a new agent.
        
        Args:
            agent_name: Name of the agent
            status: New status of the agent (HEALTHY/UNHEALTHY/NO_RESPONSE)
            location: Location of the agent if new (MainPC/PC2), otherwise uses existing
            
        Returns:
            Dictionary with the result of the operation
        """
        current_time = datetime.now().isoformat()
        
        if agent_name in self.registered_agents:
            # Update existing agent
            agent_data = self.registered_agents[agent_name]
            old_status = agent_data["status"]
            agent_data["status"] = status
            agent_data["last_seen"] = current_time
            if location is not None:
                agent_data["location"] = location
                
            logger.info(f"Updated agent {agent_name} status from {old_status} to {status}")
            return {
                "status": "success",
                "message": f"Updated {agent_name} status to {status}",
                "agent": agent_name
            }
        else:
            # Register new agent
            if location is None:
                location = "Unknown"
            
            self._register_agent(agent_name, location, status, current_time)
            return {
                "status": "success",
                "message": f"Registered new agent {agent_name} at {location} with status {status}",
                "agent": agent_name
            }
            
    def get_all_agent_statuses(self) -> Dict[str, Any]:
        """
        Get the statuses of all registered agents.
        
        Returns:
            Dictionary with all registered agents and their statuses
        """
        logger.info(f"Returning statuses for {len(self.registered_agents)} registered agents")
        return self.registered_agents
    
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
        # Don't check Prometheus connection for health checks to avoid long timeouts
        # when Prometheus is not available
        return {
            'status': 'success',
            'agent': 'SystemDigitalTwin',
            'timestamp': datetime.now().isoformat(),
            'metrics_thread_alive': self.metrics_thread.is_alive() if hasattr(self, 'metrics_thread') else False,
            'metrics_history_length': len(self.metrics_history["timestamps"]),
            'last_metrics_update': self.metrics_history["timestamps"][-1].isoformat() if self.metrics_history["timestamps"] else None,
            'prometheus_connected': self.prom is not None,  # Fast check without actual connection attempt
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
            
        elif action == "register_agent":
            # Register a new agent or update existing
            agent_name = request.get("agent_name", "")
            status = request.get("status", "UNKNOWN")
            location = request.get("location", None)
            
            if not agent_name:
                return {
                    "status": "error",
                    "error": "Missing required parameter: agent_name"
                }
                
            return self.update_agent_status(agent_name, status, location)
            
        elif action == "get_all_agents":
            # Return all registered agents
            return {
                "status": "success",
                "agents": self.get_all_agent_statuses()
            }
        
        elif action == "update_vram_metrics":
            # Update VRAM metrics from ModelManagerAgent reports
            payload = request.get("payload", {})
            self._update_vram_metrics(payload)
            return {
                "status": "success",
                "message": "VRAM metrics updated successfully"
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
                    
                    # Receive the raw message first (works with both secure and non-secure sockets)
                    try:
                        raw_message = self.socket.recv()
                        logger.info(f"Received raw message of {len(raw_message)} bytes")
                        
                        # First try to decode as string for special commands
                        try:
                            message_str = raw_message.decode('utf-8')
                            
                            # Handle simple string commands
                            if message_str == "ping":
                                logger.info("Received ping message, sending pong")
                                self.socket.send_string("pong")
                                logger.info("Pong response sent")
                                continue
                            elif message_str == "GET_ALL_STATUS":
                                logger.info("Received request for all agent statuses")
                                all_statuses = self.get_all_agent_statuses()
                                self.socket.send_json(all_statuses)
                                logger.info(f"Sent status info for {len(all_statuses)} agents")
                                continue
                                
                            # Try to parse as JSON
                            try:
                                message = json.loads(message_str)
                                logger.info(f"Parsed message as JSON: {message}")
                                
                                # Handle service discovery commands
                                command = message.get("command")
                                if command == "REGISTER":
                                    payload = message.get("payload", {})
                                    agent_name = payload.get("name")
                                    if agent_name:
                                        self.service_registry[agent_name] = payload
                                        logger.info(f"Registered service: {agent_name} with details: {payload}")
                                        self.socket.send_json({
                                            "status": "SUCCESS", 
                                            "message": f"Service {agent_name} registered successfully"
                                        })
                                    else:
                                        logger.warning("Registration request missing agent name")
                                        self.socket.send_json({
                                            "status": "ERROR", 
                                            "message": "Missing required field 'name' in registration payload"
                                        })
                                    continue
                                    
                                elif command == "DISCOVER":
                                    payload = message.get("payload", {})
                                    agent_name = payload.get("name")
                                    if agent_name:
                                        service_info = self.service_registry.get(agent_name)
                                        if service_info:
                                            logger.info(f"Service discovery request for {agent_name} - found")
                                            self.socket.send_json({
                                                "status": "SUCCESS",
                                                "payload": service_info
                                            })
                                        else:
                                            logger.warning(f"Service discovery request for {agent_name} - not found")
                                            self.socket.send_json({
                                                "status": "NOT_FOUND",
                                                "message": f"Service '{agent_name}' not registered"
                                            })
                                    else:
                                        logger.warning("Discovery request missing agent name")
                                        self.socket.send_json({
                                            "status": "ERROR",
                                            "message": "Missing required field 'name' in discovery payload"
                                        })
                                    continue
                                
                                # Handle special command types
                                if command == "REPORT_MODEL_VRAM":
                                    payload = message.get("payload", {})
                                    self._update_vram_metrics(payload)
                                    self.socket.send_json({
                                        "status": "SUCCESS",
                                        "message": "VRAM metrics updated successfully"
                                    })
                                    logger.info("VRAM metrics updated successfully")
                                    continue
                                elif command == "GET_METRICS":
                                    payload = message.get("payload", {})
                                    metrics_list = payload.get("metrics", [])
                                    
                                    # If no specific metrics requested, return all
                                    if not metrics_list:
                                        metrics_data = self._get_current_state()
                                    else:
                                        # Handle specific metrics requests
                                        metrics_data = {}
                                        
                                        # Handle VRAM usage metrics
                                        if "vram_usage" in metrics_list:
                                            # Return VRAM metrics
                                            for key, value in self.vram_metrics.items():
                                                if key != "loaded_models":  # Skip the detailed models list
                                                    metrics_data[key] = value
                                        
                                        # Add other metrics as needed
                                        if "cpu_usage" in metrics_list:
                                            # Get current CPU metrics
                                            current_metrics = self._get_current_state()
                                            metrics_data["cpu_usage"] = current_metrics.get("cpu_usage", 0)
                                    
                                    self.socket.send_json({
                                        "status": "SUCCESS",
                                        "payload": metrics_data
                                    })
                                    logger.info(f"Sent metrics data for requested metrics: {metrics_list if metrics_list else 'all'}")
                                    continue
                                
                                # Proceed with existing message handling
                                response = self.handle_request(message)
                                logger.info(f"Sending response: {response}")
                                self.socket.send_json(response)
                                logger.info("Response sent successfully")
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse as JSON: {message_str}")
                                self.socket.send_string(f"ERROR: Unknown command: {message_str}")
                        except UnicodeDecodeError:
                            # This means the message is binary (possibly encrypted)
                            logger.warning("Received binary message that cannot be decoded as UTF-8. This may be a secure ZMQ message.")
                            self.socket.send_json({
                                "status": "ERROR",
                                "message": "Received binary data that could not be processed. Check if your client is using secure ZMQ correctly."
                            })
                    except zmq.error.Again:
                        logger.warning("Socket timeout or no message received")
                    except Exception as e:
                        logger.error(f"Error processing raw message: {e}")
                        try:
                            self.socket.send_json({"status": "error", "error": str(e)})
                        except Exception as send_error:
                            logger.error(f"Failed to send error response: {send_error}")
                    
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
        
        # Stop threads
        try:
            if hasattr(self, 'metrics_thread') and self.metrics_thread.is_alive():
                self.metrics_thread.join(timeout=2.0)
                if self.metrics_thread.is_alive():
                    logger.warning("Metrics thread did not terminate gracefully")
        except Exception as e:
            logger.error(f"Error stopping threads: {e}")
        
        # Close sockets in a try-finally block to ensure they're all closed
        try:
            if hasattr(self, 'socket'):
                self.socket.close()
                logger.debug("Closed main socket")
        except Exception as e:
            logger.error(f"Error during socket cleanup: {e}")
        finally:
            # Terminate ZMQ context
            if hasattr(self, 'context'):
                self.context.term()
                logger.debug("Terminated ZMQ context")
        
        logger.info("SystemDigitalTwin cleanup complete")
    
    def stop(self):
        """Stop the agent gracefully."""
        self.running = False

    def _update_vram_metrics(self, payload: Dict[str, Any]) -> None:
        """
        Update VRAM metrics from ModelManagerAgent reports
        
        Args:
            payload: Dictionary containing VRAM metrics from ModelManagerAgent
        """
        try:
            agent_name = payload.get("agent_name", "ModelManagerAgent")
            total_vram_mb = payload.get("total_vram_mb", self.vram_metrics.get("mainpc_vram_total_mb"))
            total_vram_used_mb = payload.get("total_vram_used_mb", 0)
            loaded_models = payload.get("loaded_models", {})
            
            # Update MainPC VRAM metrics
            self.vram_metrics["mainpc_vram_total_mb"] = total_vram_mb
            self.vram_metrics["mainpc_vram_used_mb"] = total_vram_used_mb
            self.vram_metrics["mainpc_vram_free_mb"] = total_vram_mb - total_vram_used_mb
            
            # Keep track of PC2 model VRAM usage
            pc2_models_vram = 0
            
            # Update loaded models info
            for model_id, model_info in loaded_models.items():
                vram_usage = model_info.get("vram_usage_mb", 0)
                device = model_info.get("device", "MainPC")
                
                # Track PC2 VRAM usage
                if device == "PC2":
                    pc2_models_vram += vram_usage
                
                # Store model info
                self.vram_metrics["loaded_models"][model_id] = {
                    "vram_usage_mb": vram_usage,
                    "device": device,
                    "reported_by": agent_name
                }
            
            # Update PC2 VRAM metrics if models are reported
            if pc2_models_vram > 0:
                self.vram_metrics["pc2_vram_used_mb"] = pc2_models_vram
                self.vram_metrics["pc2_vram_free_mb"] = self.vram_metrics["pc2_vram_total_mb"] - pc2_models_vram
            
            # Update timestamp
            self.vram_metrics["last_update"] = datetime.now().isoformat()
            
            logger.info(f"Updated VRAM metrics from {agent_name}: "
                       f"MainPC: {total_vram_used_mb}/{total_vram_mb}MB, "
                       f"PC2: {pc2_models_vram}/{self.vram_metrics['pc2_vram_total_mb']}MB, "
                       f"{len(loaded_models)} models tracked")
        
        except Exception as e:
            logger.error(f"Error updating VRAM metrics: {e}")
            import traceback
            logger.error(traceback.format_exc())

if __name__ == "__main__":
    agent = SystemDigitalTwin()
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("SystemDigitalTwin interrupted")
    finally:
        agent.cleanup() 