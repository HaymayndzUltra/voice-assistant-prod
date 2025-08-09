#!/usr/bin/env python3
from common.config_manager import get_service_ip
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


# Utilities for path handling
from common.utils.path_manager import PathManager

import time
import json
from main_pc_code.agents.error_publisher import ErrorPublisher
import threading
from common.pools.zmq_pool import get_rep_socket
import psutil
import sqlite3
import redis
from datetime import datetime
from typing import Dict, Any, Optional, TypeVar
from collections import deque

from common.core.base_agent import BaseAgent
from main_pc_code.utils.service_discovery_client import get_service_discovery_client
from main_pc_code.utils.metrics_client import get_metrics_client
try:
    from main_pc_code.src.network.secure_zmq import is_secure_zmq_enabled, configure_secure_server, start_auth  # type: ignore
except Exception:
    from main_pc_code.agents.responder import configure_secure_server  # stubs
    def is_secure_zmq_enabled():
        return False
    def start_auth():
        return None
from common.utils.data_models import SystemEvent, ErrorReport
from common.env_helpers import get_env
from common.pools.redis_pool import get_redis_client_sync
from common_utils.port_registry import get_port

# Configure logging using canonical approach
from common.utils.log_setup import configure_logging
logger = configure_logging(__name__, log_to_file=True)

# Load configuration at module level
# Port registry removed - using startup_config.yaml as single source of truth

# Constants
BIND_ADDRESS = get_env('BIND_ADDRESS', '0.0.0.0')
ZMQ_REQUEST_TIMEOUT = 5000
# Port registry integration - replaced hardcoded ports
# DEFAULT_PORT = 7220  # Now obtained from port registry
# DEFAULT_HEALTH_PORT = 8220  # Now obtained from port registry
# Database & Cache Defaults

DEFAULT_CONFIG = {
    "prometheus_url": os.getenv("PROMETHEUS_URL", "http://prometheus:9090"),
    "metrics_poll_interval": 5,
    "metrics_history_length": 60,
    "vram_capacity_mb": 24000,
    "cpu_cores": 16,
    "ram_capacity_mb": 32000,
    "network_baseline_ms": 50,
    # Phase-3 new defaults
    "db_path": str(Path(PathManager.get_project_root()) / "data" / str(PathManager.get_data_dir() / "unified_memory.db")),
    "redis": {"host": get_service_ip("redis"), "port": 6379, "db": 0},
    "zmq_request_timeout": 5000,
}

# Type variable for better type hinting
T = TypeVar('T')

class SystemDigitalTwinAgent(BaseAgent):
    """
    A digital twin of the system that monitors real-time metrics
    and provides predictive analytics for resource management. Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:')."""
    
    def __init__(self, config=None, **kwargs):
        config = config or {}
        
        self.name = kwargs.get('name', "SystemDigitalTwin")
        # Fixed: Use port registry consistently
        try:
            self.port = get_port("SystemDigitalTwin")
        except Exception as e:
            # Fallback only if port registry completely fails
            self.port = int(os.getenv("SYSTEM_DIGITAL_TWIN_PORT", 7220))
            logger.warning(f"Port registry lookup failed ({e}), using env fallback: {self.port}")

        # Determine health port EARLY so BaseAgent can use it
        try:
            self.health_port = get_port("SystemDigitalTwin") + 1000  # Standard pattern
        except Exception:
            self.health_port = int(os.getenv("SYSTEM_DIGITAL_TWIN_HEALTH_PORT", 8220))

        self.bind_address = config.get("bind_address", BIND_ADDRESS)
        self.zmq_timeout = int(config.get("zmq_request_timeout", ZMQ_REQUEST_TIMEOUT))
        self.start_time = time.time()
        
        # Fix: Define endpoint for ZMQ socket binding
        self.endpoint = f"tcp://*:{self.port}"
        
        self.running = True
        self.service_registry = {}
        self.registered_agents = {}
        self.agent_endpoints = {}  # New: Store agent endpoints for discovery
        self.prom = None
        self.metrics_thread = None
        self.secure_zmq_enabled = False
        
        # Pass health_check_port explicitly to BaseAgent so its HTTP health server uses the pre-computed port
        super().__init__(name=self.name, port=self.port, health_check_port=self.health_port, **kwargs)
        
        self.config = DEFAULT_CONFIG.copy()
        self.config.update(config)
        # Extract frequently-used settings after merge
        self.db_path = self.config.get("db_path", str(Path(PathManager.get_project_root()) / "data" / str(PathManager.get_data_dir() / "unified_memory.db")))
        self.redis_settings = self.config.get("redis", {"host": "localhost", "port": 6379, "db": 0})
        
        self.main_port = self.port
        # Health port using standard pattern
        
        history_len = int(self.config.get("metrics_history_length", DEFAULT_CONFIG.get("metrics_history_length", 60)))
        self.metrics_history = {
            "cpu_usage": deque(maxlen=history_len),
            "vram_usage_mb": deque(maxlen=history_len),
            "ram_usage_mb": deque(maxlen=history_len),
            "network_latency_ms": deque(maxlen=history_len),
            "timestamps": deque(maxlen=history_len),
        }
        
        vram_capacity = self.config.get("vram_capacity_mb", 24000)
        pc2_vram_capacity = self.config.get("pc2_vram_capacity_mb", 12000)
        # --- Redis connection using shared pool ---
        self.redis_conn: Optional[redis.Redis] = None
        try:
            self.redis_conn = get_redis_client_sync()
            self.redis_conn.ping()
            logger.info("Successfully connected to Redis using shared connection pool")
        except Exception as r_err:
            logger.warning(f"Redis connection failed: {r_err}. Health checks will report degraded cache connectivity.")
            self.redis_conn = None

        self.vram_metrics = {
            "mainpc_vram_total_mb": vram_capacity, "mainpc_vram_used_mb": 0,
            "mainpc_vram_free_mb": vram_capacity, "pc2_vram_total_mb": pc2_vram_capacity,
            "pc2_vram_used_mb": 0, "pc2_vram_free_mb": pc2_vram_capacity,
            "loaded_models": {}, "last_update": datetime.now().isoformat()
        }
        
        self.last_update_time = datetime.now().isoformat()
        logger.info(f"{self.name} initialized.")
        # Initialise unified error publisher
        self.error_publisher = ErrorPublisher(self.name)

        # Deprecated direct ZMQ PUB socket removed – handled by ErrorPublisher

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
            self.error_publisher.publish_error(error_type="setup_failure", severity="critical", details=str(e))
            return False
    
    def _setup_zmq(self):
        """Set up ZMQ sockets."""
        self.context = None  # Using pool
        self.socket = get_rep_socket(self.endpoint).socket
        self.socket.setsockopt(zmq.RCVTIMEO, self.zmq_timeout)
        
        if is_secure_zmq_enabled():
            try:
                start_auth()
                self.socket = configure_secure_server(self.socket)
                self.secure_zmq_enabled = True
                logger.info("Secure ZMQ configured successfully.")
            except Exception as e:
                logger.error(f"Failed to configure secure ZMQ: {e}, continuing with standard ZMQ.")
                self.error_publisher.publish_error(error_type="secure_zmq_setup", severity="medium", details=str(e))
        
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
            self.error_publisher.publish_error(error_type="service_registration", severity="high", details=str(e))
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
            if self.prom is None:
                return default
                
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
                "cpu_usage": list(self.metrics_history["cpu_usage"]),
                "vram_usage_mb": list(self.metrics_history["vram_usage_mb"]),
                "ram_usage_mb": list(self.metrics_history["ram_usage_mb"]),
                "network_latency_ms": list(self.metrics_history["network_latency_ms"])
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
            # Database connectivity test (SQLite)
            db_connected = False
            try:
                conn = sqlite3.connect(self.db_path, timeout=1)
                conn.execute("SELECT 1")
                conn.close()
                db_connected = True
            except Exception as db_err:
                    logger.error(f"Health check DB error: {db_err}")

            # Redis connectivity test
            redis_connected = False
            if self.redis_conn:
                try:
                    self.redis_conn.ping()
                    redis_connected = True
                except Exception as redis_err:
                    logger.error(f"Health check Redis ping error: {redis_err}")

            # ZMQ socket status
            zmq_ready = hasattr(self, 'socket') and self.socket is not None

            specific_metrics = {
                "twin_status": "active" if self.running else "inactive",
                "registered_agents_count": len(self.registered_agents),
                "prometheus_connected": self.prom is not None and self._check_prometheus_connection(),
                "system_metrics": {"cpu_percent": psutil.cpu_percent(), "memory_percent": psutil.virtual_memory().percent},
                "db_connected": db_connected,
                "redis_connected": redis_connected,
                "zmq_ready": zmq_ready
            }
            # Aggregate overall status
            # Aggregate overall status
            overall_status = "ok" if all([db_connected, redis_connected, zmq_ready]) else "degraded"
            base_status.update({
                "agent_specific_metrics": specific_metrics,
                "status": overall_status
            })
        except Exception as e:
            logger.error(f"Error collecting health metrics: {e}")
            base_status.update({"health_metrics_error": str(e)})
        return base_status
    
    def _check_prometheus_connection(self) -> bool:
        """Check if Prometheus connection is working."""
        from common_utils.error_handling import SafeExecutor
        
        with SafeExecutor(self.logger, recoverable=(ConnectionError, TimeoutError), default_return=False):
            return self.prom.check_prometheus_connection() if self.prom else False

    # ------------------------------------------------------------------
    #                      HTTP HEALTH ENDPOINT
    # NOTE: _start_http_health_server is now handled by BaseAgent

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

    # ===================================================================
    #         NEW AGENT REGISTRATION AND DISCOVERY METHODS
    # ===================================================================
    
    # legacy local registration and endpoint lookup removed; delegated to ServiceRegistry

    # ===================================================================
    #         PHASE 2: DISCOVERY DELEGATION TO SERVICEREGISTRYAGENT
    # ===================================================================

    def _forward_to_registry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Forward a JSON payload to the ServiceRegistry agent and return its response.

        Uses config manager to get ServiceRegistry endpoint. Falls back to an error dict on timeout.
        """
        import os, zmq  # Local import to avoid circulars at module import time
        host = get_service_ip("service_registry")
        port = int(os.getenv("SERVICE_REGISTRY_PORT", "7200"))
        timeout = int(os.getenv("SERVICE_REGISTRY_TIMEOUT_MS", "5000"))

        ctx = self.context or zmq.Context.instance()
        with ctx.socket(zmq.REQ) as sock:
            sock.setsockopt(zmq.LINGER, 0)
            sock.setsockopt(zmq.RCVTIMEO, timeout)
            sock.connect(f"tcp://{host}:{port}")
            try:
                sock.send_json(payload)
                return sock.recv_json()
            except zmq.error.Again:
                return {"status": "error", "error": "ServiceRegistry timeout"}
            except Exception as exc:  # noqa: BLE001
                return {"status": "error", "error": str(exc)}

    # Thin wrappers that override the bulky legacy implementations -----------------
    def register_agent(self, registration_data):  # type: ignore[override]
        """Delegate agent registration to the external ServiceRegistry."""
        return self._forward_to_registry({
            "action": "register_agent",
            "registration_data": registration_data,
        })

    def get_agent_endpoint(self, agent_name):  # type: ignore[override]
        """Delegate endpoint lookup to the external ServiceRegistry."""
        return self._forward_to_registry({
            "action": "get_agent_endpoint",
            "agent_name": agent_name,
        })

    # -------------------------------------------------------------------
    def publish_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Publish a system event to all interested agents.
        
        Args:
            event: The event data to publish
            
        Returns:
            Response indicating success or failure
        """
        if event is None:
            return {"status": "error", "error": "Missing event data"}
            
        try:
            # Convert to SystemEvent model if plain dict
            if not isinstance(event, SystemEvent):
                try:
                    system_event = SystemEvent(**event)
                except Exception as e:
                    logger.error(f"Invalid event data: {e}")
                    return {"status": "error", "error": f"Invalid event data: {str(e)}"}
            else:
                system_event = event
                
            # Log the event
            logger.info(f"Publishing event: {system_event.event_type} from {system_event.source_agent}")
            
            # TODO: Implement event distribution to interested agents
            # For now, just log it
            
            return {
                "status": "success",
                "message": f"Event {system_event.event_id} published successfully",
                "event_id": system_event.event_id
            }
            
        except Exception as e:
            logger.error(f"Error publishing event: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    def report_error(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """Record an error report and take appropriate action.
        
        Args:
            error: The error report data
            
        Returns:
            Response indicating success or failure
        """
        if error is None:
            return {"status": "error", "error": "Missing error report data"}
            
        try:
            # Convert to ErrorReport model if plain dict
            if not isinstance(error, ErrorReport):
                try:
                    error_report = ErrorReport(**error)
                except Exception as e:
                    logger.error(f"Invalid error report data: {e}")
                    return {"status": "error", "error": f"Invalid error report data: {str(e)}"}
            else:
                error_report = error
                
            # Log the error
            logger.error(
                f"Error reported by {error_report.agent_id}: "
                f"[{error_report.severity}] {error_report.error_type} - {error_report.message}"
            )
            
            # TODO: Implement error handling logic
            # For critical errors, could trigger self-healing
            
            return {
                "status": "success",
                "message": f"Error {error_report.error_id} recorded successfully",
                "error_id": error_report.error_id
            }
            
        except Exception as e:
            logger.error(f"Error processing error report: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an incoming request by dispatching to the correct method."""
        if not isinstance(request, dict):
            return {"status": "error", "error": "Invalid request format"}
            
        action = request.get("action")
        
        if action == "ping":
            return {"status": "ok", "message": "pong", "timestamp": datetime.now().isoformat()}
        elif action == "get_metrics":
            return {"status": "success", "metrics": self._get_current_state()}
        elif action == "get_history":
            return self.get_metrics_history()
        elif action == "get_all_agents":
            return {"status": "success", "agents": self.get_all_agent_statuses()}
        elif action == "get_registered_agents":
            # Return all registered agents for SystemHealthManager
            return self._get_registered_agents()
        elif action == "get_agent_info":
            agent_name = request.get("agent_name")
            if not agent_name or not isinstance(agent_name, str):
                return {"status": "error", "error": "Missing or invalid agent_name parameter"}
            return self.get_agent_info(agent_name)
        elif action == "simulate_load":
            load_type = request.get("load_type")
            value = request.get("value")
            
            # Type validation
            if not isinstance(load_type, str):
                return {"status": "error", "error": "load_type must be a string"}
                
            try:
                value_float = float(value) if value is not None else 0.0
            except (ValueError, TypeError):
                return {"status": "error", "error": "value must be a number"}
                
            return self.simulate_load(load_type, value_float)
        elif action == "register_agent":
            # Check if this is a detailed registration with registration_data
            if "registration_data" in request:
                registration_data = request.get("registration_data")
                if registration_data is None or not isinstance(registration_data, dict):
                    return {"status": "error", "error": "Invalid registration_data, expected dictionary"}
                return self.register_agent(registration_data)
            
            # Otherwise fall back to simple registration
            agent_name = request.get("agent_name")
            status = request.get("status")
            
            if not agent_name or not isinstance(agent_name, str):
                return {"status": "error", "error": "Missing or invalid agent_name parameter"}
                
            if not status or not isinstance(status, str):
                return {"status": "error", "error": "Missing or invalid status parameter"}
                
            return self.update_agent_status(agent_name, status, request.get("location"))
        elif action == "get_agent_endpoint":
            agent_name = request.get("agent_name")
            if not agent_name or not isinstance(agent_name, str):
                return {"status": "error", "error": "Missing or invalid agent_name parameter"}
            return self.get_agent_endpoint(agent_name)
        elif action == "publish_event":
            event = request.get("event")
            if not event:
                return {"status": "error", "error": "Missing required parameter: event"}
            return self.publish_event(event)
        elif action == "report_error":
            error = request.get("error")
            if not error:
                return {"status": "error", "error": "Missing required parameter: error"}
            return self.report_error(error)
        elif action == "get_ok_agents":
            return self._get_ok_agents()
        elif action == "update_vram_metrics":
            payload = request.get("payload", {})
            return self._update_vram_metrics(payload)
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}

    def _get_ok_agents(self) -> Dict[str, Any]:
        """Return a list of agents whose health status is strictly 'ok'."""
        try:
            ok_agents = [name for name, info in self.registered_agents.items() if str(info.get("status", "")).lower() == "ok"]
            logger.info(f"Found {len(ok_agents)} agent(s) reporting OK health")
            return {
                "status": "success",
                "count": len(ok_agents),
                "agents": ok_agents
            }
        except Exception as e:
            logger.error(f"Error getting OK agents: {e}")
            self.error_publisher.publish_error(error_type="get_ok_agents", severity="medium", details=str(e))
            return {"status": "error", "error": str(e)}

    def _get_registered_agents(self) -> Dict[str, Any]:
        """Get a list of all registered agents with their information.
        
        Returns:
            Dictionary with status and list of agent information
        """
        try:
            # Combine information from agent_registry and agent_endpoints
            agents_list = []
            
            for agent_name, status_info in self.registered_agents.items():
                agent_info = {
                    "name": agent_name,
                    "status": status_info.get("status", "unknown"),
                    "location": status_info.get("location", "unknown"),
                    "last_updated": status_info.get("timestamp", "")
                }
                
                # Add endpoint information if available
                if agent_name in self.agent_endpoints:
                    endpoint = self.agent_endpoints[agent_name]
                    agent_info.update({
                        "host": endpoint.get("host", ""),
                        "port": endpoint.get("port", 0),
                        "health_check_port": endpoint.get("health_check_port", 0),
                        "agent_type": endpoint.get("agent_type", ""),
                        "capabilities": endpoint.get("capabilities", []),
                        "script_path": endpoint.get("metadata", {}).get("script_path", "")
                    })
                
                agents_list.append(agent_info)
            
            logger.info(f"Returning information for {len(agents_list)} registered agents")
            return {
                "status": "success",
                "agents": agents_list
            }
        except Exception as e:
            logger.error(f"Error getting registered agents: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    def get_agent_info(self, agent_name: str) -> Dict[str, Any]:
        """Get detailed information about a registered agent.
        
        Args:
            agent_name: Name of the agent to get information for
            
        Returns:
            Dict with agent information including script_path, port, etc.
        """
        if agent_name not in self.registered_agents:
            return {"status": "error", "error": f"Agent {agent_name} not found in registry"}
        
        # Get basic agent info from registry
        agent_info = self.registered_agents.get(agent_name, {}).copy()
        
        # Try to get additional information from configuration
        try:
            # Look for agent configuration in various places
            agent_config = {}
            
            # Check in startup_config.yaml (MainPC SOT)
            config_file = str(Path(PathManager.get_project_root()) / "main_pc_code" / "config" / "startup_config.yaml")
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    import yaml
                    config_data = yaml.safe_load(f)
                    
                    # Look in agent_groups (MainPC SOT structure)
                    agent_groups = config_data.get("agent_groups", {})
                    for group_name, group_agents in agent_groups.items():
                        if isinstance(group_agents, dict) and agent_name in group_agents:
                            agent_config = group_agents[agent_name].copy()
                            agent_config["group"] = group_name  # Add group info
                            break
            
            # If we found config, add it to agent_info
            if agent_config:
                # Get the script path
                if "script_path" in agent_config:
                    agent_info["script_path"] = agent_config["script_path"]
                
                # Get other useful info
                for key in ["port", "host", "health_check_port", "dependencies"]:
                    if key in agent_config:
                        agent_info[key] = agent_config[key]
                        
            # If we still don't have a script path, try to infer it
            if "script_path" not in agent_info:
                # Common patterns for agent script paths
                project_root = Path(PathManager.get_project_root())
                possible_paths = [
                    str(project_root / "main_pc_code" / "agents" / f"{agent_name.lower()}.py"),
                    str(project_root / "main_pc_code" / "agents" / f"{agent_name}.py"),
                    str(project_root / "pc2_code" / "agents" / f"{agent_name.lower()}.py"),
                    str(project_root / "pc2_code" / "agents" / f"{agent_name}.py")
                ]
                
                for path in possible_paths:
                    if os.path.exists(os.path.join(os.environ.get("PROJECT_ROOT", ""), path)):
                        agent_info["script_path"] = path
                        break
        
        except Exception as e:
            logger.error(f"Error getting additional agent info for {agent_name}: {e}")
        
        return {
            "status": "success",
            "agent_info": agent_info
        }

    async def run_async(self) -> None:
        """
        Type-checked async run method using azmq.Socket for improved async operations.
        Handles >5k req/min without thread thrashing.
        """
        import asyncio
        import zmq.asyncio as azmq
        
        if not self.setup():
            logger.critical("Setup failed, agent cannot start.")
            return
        
        logger.info(f"Starting async {self.name} on port {self.main_port}")
        
        # Create async ZMQ context and socket with type checking
        async_context = azmq.Context()
        async_socket: azmq.Socket = async_context.socket(zmq.REP)
        
        try:
            # Configure socket options for high-throughput operations
            async_socket.setsockopt(zmq.LINGER, 0)
            async_socket.bind(f"tcp://*:{self.main_port}")
            
            logger.info(f"✅ Async {self.name} listening on tcp://*:{self.main_port}")
            
            self.running = True
            
            while self.running:
                try:
                    # Async receive with timeout
                    raw_message = await asyncio.wait_for(
                        async_socket.recv(), timeout=1.0
                    )
                    
                    # Process message (reuse existing logic)
                    try:
                        message_str = raw_message.decode('utf-8')
                        if message_str == "ping":
                            await async_socket.send_string("pong")
                            continue
                            
                        message = json.loads(message_str)
                        response = self.handle_request(message)
                        await async_socket.send_json(response)
                        
                    except json.JSONDecodeError:
                        error_response = {"error": "Invalid JSON format"}
                        await async_socket.send_json(error_response)
                    except Exception as e:
                        error_response = {"error": f"Processing error: {str(e)}"}
                        await async_socket.send_json(error_response)
                        
                except asyncio.TimeoutError:
                    # Normal timeout, continue loop
                    continue
                except Exception as e:
                    logger.error(f"Error in async main loop: {e}", exc_info=True)
                    
        except KeyboardInterrupt:
            logger.info("Async shutdown signal received.")
        finally:
            async_socket.close()
            async_context.term()
            self.cleanup()

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
    import sys
    
    # Check if async mode is requested
    use_async = "--async" in sys.argv or os.getenv("ASYNC_MODE", "false").lower() == "true"
    
    agent = None
    try:
        # Pass the default config to the agent instance
        agent = SystemDigitalTwinAgent(config=DEFAULT_CONFIG)
        
        if use_async:
            import asyncio
            logger.info("Starting SystemDigitalTwin in ASYNC mode for high-throughput operations")
            asyncio.run(agent.run_async())
        else:
            logger.info("Starting SystemDigitalTwin in SYNC mode")
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