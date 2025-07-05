#!/usr/bin/env python3
"""
System Digital Twin Agent

This agent monitors real-time system metrics, provides a simulation endpoint
to predict the impact of future actions, and serves as a central registry
for other agents in the system.
"""

# ===================================================================
#         FINAL REFACTORED CODE - COMPLETE & INTEGRATED
# ===================================================================

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path

# FINAL: Kept the modern pathlib approach and removed the redundant os.path block.
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

import time
import json
import logging
import threading
import zmq
import psutil
from datetime import datetime
from typing import Dict, Any, Optional

from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config
from main_pc_code.utils.service_discovery_client import get_service_discovery_client
from main_pc_code.utils.metrics_client import get_metrics_client
from main_pc_code.utils.env_loader import get_env
from main_pc_code.src.network.secure_zmq import is_secure_zmq_enabled, configure_secure_server, start_auth

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

# Load configuration at module level
config = load_config()

# Constants
BIND_ADDRESS = get_env('BIND_ADDRESS', '0.0.0.0')
ZMQ_REQUEST_TIMEOUT = 5000
DEFAULT_PORT = 7120
DEFAULT_HEALTH_PORT = 8120
DEFAULT_CONFIG = {
    "prometheus_url": "http://prometheus:9090",
    "metrics_poll_interval": 5,
    "metrics_history_length": 60,
    "vram_capacity_mb": 24000,
    "cpu_cores": 16,
    "ram_capacity_mb": 32000,
    "network_baseline_ms": 50,
}

class SystemDigitalTwinAgent(BaseAgent):
    """
    A digital twin of the system that monitors real-time metrics
    and provides predictive analytics for resource management.
    """
    
    def __init__(self, config=None, **kwargs):
        config = config or {}
        
        self.name = kwargs.get('name', "SystemDigitalTwin")
        self.port = int(config.get("port", DEFAULT_PORT))
        self.bind_address = config.get("bind_address", BIND_ADDRESS)
        self.zmq_timeout = int(config.get("zmq_request_timeout", ZMQ_REQUEST_TIMEOUT))
        self.start_time = time.time()
        
        self.running = True
        self.service_registry = {}
        self.registered_agents = {}
        self.prom = None
        self.metrics_thread = None
        self.secure_zmq_enabled = False
        
        super().__init__(name=self.name, port=self.port, **kwargs)
        
        self.config = DEFAULT_CONFIG.copy()
        self.config.update(config)
        
        self.main_port = self.port
        self.health_port = config.get("health_check_port", DEFAULT_HEALTH_PORT)
        
        self.metrics_history = {
            "cpu_usage": [], "vram_usage_mb": [], "ram_usage_mb": [],
            "network_latency_ms": [], "timestamps": []
        }
        
        vram_capacity = self.config.get("vram_capacity_mb", 24000)
        pc2_vram_capacity = self.config.get("pc2_vram_capacity_mb", 12000)
        self.vram_metrics = {
            "mainpc_vram_total_mb": vram_capacity, "mainpc_vram_used_mb": 0,
            "mainpc_vram_free_mb": vram_capacity, "pc2_vram_total_mb": pc2_vram_capacity,
            "pc2_vram_used_mb": 0, "pc2_vram_free_mb": pc2_vram_capacity,
            "loaded_models": {}, "last_update": datetime.now().isoformat()
        }
        
        self.last_update_time = datetime.now().isoformat()
        logger.info(f"{self.name} initialized.")

    def setup(self):
        """Set up the agent's components after initialization."""
        try:
            self._setup_zmq()
            self._register_service()
            self._setup_prometheus()
            self._register_self_agent()
            self._start_metrics_collection()
            logger.info(f"{self.name} setup completed successfully on port {self.main_port}.")
            return True
        except Exception as e:
            logger.error(f"Error during setup: {e}", exc_info=True)
            return False
    
    def _setup_zmq(self):
        """Set up ZMQ sockets."""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, self.zmq_timeout)
        
        if is_secure_zmq_enabled():
            try:
                start_auth()
                self.socket = configure_secure_server(self.socket)
                self.secure_zmq_enabled = True
                logger.info("Secure ZMQ configured successfully.")
            except Exception as e:
                logger.error(f"Failed to configure secure ZMQ: {e}, continuing with standard ZMQ.")
        
        socket_address = f"tcp://{self.bind_address}:{self.main_port}"
        self.socket.bind(socket_address)
        logger.info(f"Successfully bound to {socket_address}.")
    
    def _register_service(self):
        """Register this agent with the service discovery system."""
        try:
            get_service_discovery_client()
            self.service_registry[self.name] = {
                "name": self.name, "ip": self.bind_address, "port": self.main_port,
                "health_check_port": self.health_port,
                "capabilities": ["system_monitoring", "resource_management", "predictive_analytics"],
                "status": "running"
            }
            logger.info("Successfully registered with service registry.")
        except Exception as e:
            logger.error(f"Error registering service: {e}")
            raise

    def _setup_prometheus(self):
        """Initialize Prometheus client."""
        self.metrics_client = get_metrics_client()
        if os.environ.get("ENABLE_PROMETHEUS", "false").lower() == "true":
            try:
                from prometheus_api_client import PrometheusConnect
                self.prom = PrometheusConnect(url=self.config["prometheus_url"], disable_ssl=True)
                logger.info("Prometheus client initialized.")
            except Exception as e:
                logger.warning(f"Failed to init Prometheus client: {e}, using mock metrics.")
        else:
            logger.info("Prometheus disabled, using mock metrics.")

    def _register_self_agent(self):
        """Register self in the agent registry."""
        self._register_agent(self.name, "MainPC", "HEALTHY", datetime.now().isoformat())
        
    def _start_metrics_collection(self):
        """Start the background thread for metrics collection."""
        if not self.metrics_thread or not self.metrics_thread.is_alive():
            self.metrics_thread = threading.Thread(target=self._collect_metrics_loop)
            self.metrics_thread.daemon = True
            self.metrics_thread.start()
            logger.info("Started metrics collection thread.")

    def _register_agent(self, agent_name: str, location: str, status: str, timestamp: str) -> None:
        """Register an agent in the system."""
        self.registered_agents[agent_name] = {
            "location": location,
            "status": status,
            "last_seen": timestamp
        }
        logger.info(f"Registered agent {agent_name} at {location} with status {status}")
        
    def update_agent_status(self, agent_name: str, status: str, location: Optional[str] = None) -> Dict[str, Any]:
        """Update the status of a registered agent or register a new agent."""
        current_time = datetime.now().isoformat()
        if agent_name in self.registered_agents:
            agent_data = self.registered_agents[agent_name]
            old_status = agent_data["status"]
            agent_data["status"] = status
            agent_data["last_seen"] = current_time
            if location is not None:
                agent_data["location"] = location
            logger.info(f"Updated agent {agent_name} status from {old_status} to {status}")
            return {"status": "success", "message": f"Updated {agent_name} status to {status}", "agent": agent_name}
        else:
            location = location or "Unknown"
            self._register_agent(agent_name, location, status, current_time)
            return {"status": "success", "message": f"Registered new agent {agent_name} at {location} with status {status}", "agent": agent_name}
            
    def get_all_agent_statuses(self) -> Dict[str, Any]:
        """Get the statuses of all registered agents."""
        logger.info(f"Returning statuses for {len(self.registered_agents)} registered agents")
        return self.registered_agents
    
    def _collect_metrics_loop(self):
        """Background thread that periodically collects system metrics."""
        while self.running:
            try:
                metrics = self._fetch_current_metrics()
                timestamp = datetime.now()
                self.metrics_history["timestamps"].append(timestamp)
                for key, value in metrics.items():
                    if key in self.metrics_history:
                        self.metrics_history[key].append(value)
                
                max_len = self.config.get("metrics_history_length", 60)
                if len(self.metrics_history["timestamps"]) > max_len:
                    for key in self.metrics_history:
                        self.metrics_history[key].pop(0)
                
                logger.debug(f"Collected metrics: {metrics}")
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
            time.sleep(self.config.get("metrics_poll_interval", 5))
    
    def _fetch_current_metrics(self) -> Dict[str, float]:
        """Fetch current system metrics from Prometheus or return mock data."""
        if self.prom:
            try:
                cpu = self._get_prometheus_value('node_cpu_utilization', 0.0)
                vram = self._get_prometheus_value('nvidia_gpu_memory_used_bytes', 0.0)
                ram = self._get_prometheus_value('node_memory_MemUsed_bytes', 0.0)
                latency = self._get_prometheus_value('network_round_trip_time_milliseconds', self.config["network_baseline_ms"])
                return {
                    "cpu_usage": cpu, "vram_usage_mb": vram / (1024*1024),
                    "ram_usage_mb": ram / (1024*1024), "network_latency_ms": latency
                }
            except Exception as e:
                logger.error(f"Error fetching Prometheus metrics: {e}")
        
        return {
            "cpu_usage": 25.0, "vram_usage_mb": 8000.0,
            "ram_usage_mb": 16000.0, "network_latency_ms": self.config["network_baseline_ms"]
        }
    
    def _get_prometheus_value(self, metric_name: str, default: float) -> float:
        """Get the latest value for a specific Prometheus metric."""
        try:
            metric_data = self.prom.get_current_metric_value(metric_name)
            if metric_data:
                return float(metric_data[0]['value'][1])
        except Exception as e:
            logger.warning(f"Failed to get metric {metric_name}: {e}")
        return default
    
    def _get_current_state(self) -> Dict[str, float]:
        """Get the current system state based on the latest metrics."""
        if not self.metrics_history["timestamps"]:
            return self._fetch_current_metrics()
        return {key: values[-1] for key, values in self.metrics_history.items()}
    
    def get_metrics_history(self) -> Dict[str, Any]:
        """Returns the entire metrics history."""
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

    def simulate_load(self, load_type: str, value: float) -> Dict[str, Any]:
        """Simulate the impact of additional load on system resources."""
        current_state = self._get_current_state()
        response = {"status": "success", "timestamp": datetime.now().isoformat(), "current_state": current_state, "load_type": load_type, "requested_value": value, "recommendation": "proceed"}
        
        if load_type == "vram":
            projected = current_state["vram_usage_mb"] + value
            capacity = self.config["vram_capacity_mb"]
            response.update({"projected_vram_mb": projected, "vram_capacity_mb": capacity})
            if projected > capacity * 0.95:
                response.update({"recommendation": "deny_insufficient_resources", "reason": f"Projected VRAM ({projected:.2f}MB) exceeds 95% of capacity."})
        elif load_type == "cpu":
            projected = min(100.0, current_state["cpu_usage"] + value)
            response.update({"projected_cpu_percent": projected})
            if projected > 90.0:
                response.update({"recommendation": "caution_high_cpu", "reason": f"Projected CPU ({projected:.2f}%) exceeds 90%."})
        elif load_type == "ram":
            projected = current_state["ram_usage_mb"] + value
            capacity = self.config["ram_capacity_mb"]
            response.update({"projected_ram_mb": projected, "ram_capacity_mb": capacity})
            if projected > capacity * 0.9:
                response.update({"recommendation": "deny_insufficient_resources", "reason": f"Projected RAM ({projected:.2f}MB) exceeds 90% of capacity."})
        else:
            response.update({"status": "error", "error": f"Unknown load type: {load_type}", "recommendation": "error_invalid_request"})
        
        return response
    
    def _get_health_status(self):
        """Get the current health status of the agent."""
        base_status = super()._get_health_status()
        try:
            specific_metrics = {
                "twin_status": "active" if self.running else "inactive",
                "registered_agents_count": len(self.registered_agents),
                "prometheus_connected": self.prom is not None and self._check_prometheus_connection(),
                "system_metrics": {"cpu_percent": psutil.cpu_percent(), "memory_percent": psutil.virtual_memory().percent}
            }
            base_status.update({"agent_specific_metrics": specific_metrics})
        except Exception as e:
            logger.error(f"Error collecting health metrics: {e}")
            base_status.update({"health_metrics_error": str(e)})
        return base_status
    
    def _check_prometheus_connection(self) -> bool:
        """Check if Prometheus connection is working."""
        try:
            return self.prom.check_prometheus_connection() if self.prom else False
        except Exception:
            return False

    def _update_vram_metrics(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update VRAM metrics from ModelManagerAgent reports."""
        try:
            agent_name = payload.get("agent_name", "ModelManagerAgent")
            self.vram_metrics["mainpc_vram_total_mb"] = payload.get("total_vram_mb", self.vram_metrics["mainpc_vram_total_mb"])
            self.vram_metrics["mainpc_vram_used_mb"] = payload.get("total_vram_used_mb", 0)
            self.vram_metrics["mainpc_vram_free_mb"] = self.vram_metrics["mainpc_vram_total_mb"] - self.vram_metrics["mainpc_vram_used_mb"]
            
            pc2_vram_used = 0
            for model_id, model_info in payload.get("loaded_models", {}).items():
                self.vram_metrics["loaded_models"][model_id] = model_info
                if model_info.get("device") == "PC2":
                    pc2_vram_used += model_info.get("vram_usage_mb", 0)
            
            self.vram_metrics["pc2_vram_used_mb"] = pc2_vram_used
            self.vram_metrics["pc2_vram_free_mb"] = self.vram_metrics["pc2_vram_total_mb"] - pc2_vram_used
            self.vram_metrics["last_update"] = datetime.now().isoformat()
            
            logger.info(f"Updated VRAM metrics from {agent_name}.")
            return {"status": "success", "message": "VRAM metrics updated successfully"}
        except Exception as e:
            logger.error(f"Error updating VRAM metrics: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an incoming request by dispatching to the correct method."""
        action = request.get("action")
        
        if action in ["ping", "health", "health_check"]:
            return self._get_health_status()
        elif action == "get_metrics":
            return {"status": "success", "metrics": self._get_current_state()}
        elif action == "get_history":
            return self.get_metrics_history()
        elif action == "get_all_agents":
            return {"status": "success", "agents": self.get_all_agent_statuses()}
        elif action == "simulate_load":
            load_type = request.get("load_type")
            value = request.get("value")
            if not all([load_type, isinstance(value, (int, float))]):
                return {"status": "error", "error": "Missing or invalid parameters: load_type, value"}
            return self.simulate_load(load_type, value)
        elif action == "register_agent":
            agent_name = request.get("agent_name")
            status = request.get("status")
            if not all([agent_name, status]):
                return {"status": "error", "error": "Missing required parameters: agent_name, status"}
            return self.update_agent_status(agent_name, status, request.get("location"))
        elif action == "update_vram_metrics":
            payload = request.get("payload", {})
            return self._update_vram_metrics(payload)
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}

    def run(self):
        """Main run loop that handles incoming requests."""
        if not self.setup():
            logger.critical("Setup failed, agent cannot start.")
            return
            
        logger.info(f"{self.name} is now running...")
        try:
            while self.running:
                try:
                    if self.socket.poll(1000) == 0:
                        continue
                    
                    raw_message = self.socket.recv()
                    
                    # --- Temporary Compatibility Layer ---
                    try:
                        message_str = raw_message.decode('utf-8')
                        if message_str == "ping":
                            logger.warning("DEPRECATED: Received 'ping' as string. Update client to send JSON: {'action': 'ping'}")
                            self.socket.send_json(self._get_health_status())
                            continue
                    except UnicodeDecodeError:
                        # Not a string, proceed to JSON parsing
                        pass
                    # --- End of Compatibility Layer ---

                    message = json.loads(raw_message)
                    response = self.handle_request(message)
                    self.socket.send_json(response)

                except zmq.error.Again:
                    continue
                except json.JSONDecodeError:
                    logger.error("Received invalid JSON message.")
                    self.socket.send_json({"status": "error", "error": "Invalid JSON format."})
                except Exception as e:
                    logger.error(f"Error in main loop: {e}", exc_info=True)
        except KeyboardInterrupt:
            logger.info("Shutdown signal received.")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info(f"Cleaning up {self.name} resources...")
        self.running = False
        if self.metrics_thread and self.metrics_thread.is_alive():
            self.metrics_thread.join(timeout=2.0)
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        super().cleanup()
        logger.info(f"{self.name} cleanup complete.")

    def request_shutdown(self):
        """Requests a graceful shutdown of the agent."""
        logger.info(f"Shutdown requested for {self.name}")
        self.running = False

# FINAL: The redundant health_check() method has been removed.
# The official health check is handled by _get_health_status(), called via handle_request.

if __name__ == "__main__":
    agent = None
    try:
        # Pass the globally loaded config to the agent instance
        agent = SystemDigitalTwinAgent(config=config)
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent:
            agent.cleanup()