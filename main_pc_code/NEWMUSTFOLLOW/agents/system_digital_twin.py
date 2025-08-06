#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging
"""
SystemDigitalTwin Agent
-----------------------
Serves as a central registry for all system components and provides real-time
monitoring of system resources. Acts as the primary service discovery mechanism
for other agents in the system.
"""

import os
import sys
import time
import json
import logging
import threading
import socket
import psutil
from typing import Dict, List, Any, Optional
from datetime import datetime
import zmq
from pathlib import Path

# Add parent directory to path for imports
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from main_pc_code.src.core.base_agent import BaseAgent
from common.env_helpers import get_env

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SystemDigitalTwin")

class SystemDigitalTwin(BaseAgent):
    """
    SystemDigitalTwin maintains a real-time digital representation of the entire system.
    
    It serves as:
    1. Service registry for agent discovery
    2. System resource monitor
    3. Health status aggregator
    4. Load prediction service
    """
    
    def __init__(self, config=None):
        """Initialize the SystemDigitalTwin agent"""
        super().__init__(config)
        
        # Override agent name and description
        self.agent_name = "SystemDigitalTwin"
        self.agent_description = "Central system registry and resource monitor"
        
        # Initialize service registry
        self.services = {}
        self.services_lock = threading.Lock()
        
        # Initialize metrics history
        self.metrics_history = {
            "timestamps": [],
            "cpu_usage": [],
            "ram_usage_mb": [],
            "vram_usage_mb": [],
            "network_latency_ms": []
        }
        
        # Optional Prometheus client for metrics
        self.prom = None
        try:
            from prometheus_client import CollectorRegistry, Counter, Gauge, push_to_gateway
            self.prom_registry = CollectorRegistry()
            # Initialize Prometheus metrics if needed
        except ImportError:
            logger.info("Prometheus client not available, using internal metrics only")
        
        # Initialize threads
        self.metrics_thread = None
        self.registry_cleanup_thread = None
    
    def setup(self):
        """Set up the SystemDigitalTwin agent"""
        try:
            logger.info("Setting up SystemDigitalTwin agent")
            
            # Initialize ZMQ context and socket with proper error handling
            if not hasattr(self, 'context') or self.context is None:
                self.context = zmq.Context()
            
            # Set up REP socket for service registry requests
            self.socket = self.context.socket(zmq.REP)
            
            # Get port with safe conversion
            port = self.safe_get_port()
            bind_address = f"tcp://*:{port}"
            
            # Try to bind with retry logic
            max_retries = 5
            retry_count = 0
            while retry_count < max_retries:
                try:
                    logger.info(f"Binding to {bind_address}")
                    self.socket.bind(bind_address)
                    break
                except zmq.error.ZMQError as e:
                    retry_count += 1
                    logger.warning(f"Failed to bind to {bind_address}: {e}")
                    if retry_count >= max_retries:
                        logger.error(f"Could not bind to {bind_address} after {max_retries} attempts")
                        raise
                    time.sleep(1)  # Wait before retrying
            
            # Set up health check socket
            self.setup_health_check()
        
        # Start metrics collection thread
            self.running = True
            self.metrics_thread = threading.Thread(
                target=self._collect_metrics_loop,
                daemon=True
            )
        self.metrics_thread.start()
        
            # Start registry cleanup thread
            self.registry_cleanup_thread = threading.Thread(
                target=self._registry_cleanup_loop,
                daemon=True
            )
            self.registry_cleanup_thread.start()
            
            logger.info("SystemDigitalTwin setup complete")
            return True
        
        except Exception as e:
            logger.error(f"Error setting up SystemDigitalTwin: {e}")
            self.cleanup()
            return False
    
    def safe_get_port(self) -> int:
        """Safely get port number from config with proper type handling"""
        port = self.config.get("port", 7120)
        if port is None:
            logger.warning("Port not specified in config, using default 7120")
            return 7120
        
        try:
            return int(port)
        except (ValueError, TypeError):
            logger.warning(f"Invalid port value '{port}', using default 7120")
            return 7120
    
    def run(self):
        """Run the SystemDigitalTwin agent main loop"""
        logger.info("Starting SystemDigitalTwin main loop")
        
        try:
            while self.running:
                try:
                    # Use poll with timeout to allow for clean shutdown
                    if self.socket.poll(1000) == 0:  # 1 second timeout
                        continue
                    
                    # Receive request
                    request_bytes = self.socket.recv()
                    request = json.loads(request_bytes.decode('utf-8'))
                    
                    # Process request
                    response = self._process_request(request)
                    
                    # Send response
                    self.socket.send(json.dumps(response).encode('utf-8'))
                
                except zmq.error.ZMQError as e:
                    if self.running:  # Only log if not shutting down
                        logger.error(f"ZMQ error in main loop: {e}")
                    time.sleep(0.1)
                
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    # Send error response if possible
                    try:
                        error_response = {
                            "status": "error",
                            "error": str(e),
                            "timestamp": datetime.now().isoformat()
                        }
                        self.socket.send(json.dumps(error_response).encode('utf-8'))
                    except:
                        pass  # Ignore errors in error handling
                    
                    time.sleep(0.1)
        
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt, shutting down")
        
        finally:
            self.cleanup()
    
    def _process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming requests to the digital twin.
        
        Args:
            request: Dictionary containing the request
            
        Returns:
            Dictionary containing the response
        """
        action = request.get("action", "")
        
        # Initialize response
        response = {
            "status": "success",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Handle different action types
            if action == "register":
                # Register a new service
                service_info = request.get("service_info", {})
                if not service_info or "name" not in service_info:
                    response["status"] = "error"
                    response["error"] = "Missing required service information"
                    return response
                
                with self.services_lock:
                    service_name = service_info["name"]
                    # Add registration timestamp
                    service_info["registered_at"] = datetime.now().isoformat()
                    service_info["last_heartbeat"] = datetime.now().isoformat()
                    self.services[service_name] = service_info
                
                logger.info(f"Registered service: {service_name}")
                response["message"] = f"Service {service_name} registered successfully"
                response["registry_id"] = service_name
            
            elif action == "unregister":
                # Unregister a service
                service_name = request.get("name", "")
                if not service_name:
                    response["status"] = "error"
                    response["error"] = "Missing service name"
                    return response
                
                with self.services_lock:
                    if service_name in self.services:
                        del self.services[service_name]
                        logger.info(f"Unregistered service: {service_name}")
                        response["message"] = f"Service {service_name} unregistered successfully"
                    else:
                        response["status"] = "error"
                        response["error"] = f"Service {service_name} not found"
            
            elif action == "heartbeat":
                # Update service heartbeat
                service_name = request.get("name", "")
                if not service_name:
                    response["status"] = "error"
                    response["error"] = "Missing service name"
                    return response
                
                with self.services_lock:
                    if service_name in self.services:
                        self.services[service_name]["last_heartbeat"] = datetime.now().isoformat()
                        response["message"] = "Heartbeat received"
                    else:
                        response["status"] = "error"
                        response["error"] = f"Service {service_name} not found, please register first"
            
            elif action == "discover":
                # Discover services
                service_type = request.get("service_type", None)
                
                with self.services_lock:
                    if service_type:
                        # Filter by service type
                        matching_services = {
                            name: info for name, info in self.services.items()
                            if info.get("type") == service_type
                        }
                        response["services"] = matching_services
                    else:
                        # Return all services
                        response["services"] = self.services
            
            elif action == "get_metrics":
                # Get system metrics
                metrics_type = request.get("metrics_type", "current")
                
                if metrics_type == "current":
                    response["metrics"] = self._get_current_state()
                elif metrics_type == "history":
                    response["metrics"] = self.metrics_history
        else:
                    response["status"] = "error"
                    response["error"] = f"Unknown metrics type: {metrics_type}"
            
            elif action == "simulate_load":
                # Simulate additional load
                load_type = request.get("load_type", "")
                value = request.get("value", 0.0)
                
                if not load_type:
                    response["status"] = "error"
                    response["error"] = "Missing load type"
                    return response
                
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    response["status"] = "error"
                    response["error"] = f"Invalid value: {value}"
                    return response
                
                # Get load simulation results
                simulation_result = self.simulate_load(load_type, value)
                response.update(simulation_result)
            
            else:
                response["status"] = "error"
                response["error"] = f"Unknown action: {action}"
        
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            response["status"] = "error"
            response["error"] = str(e)
        
        return response
    
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
                max_len = self.config.get("metrics_history_length", 60)  # Default to 60 if None
                if len(self.metrics_history["timestamps"]) > max_len:
                    for key in self.metrics_history:
                        self.metrics_history[key] = self.metrics_history[key][-max_len:]
                
                logger.debug(f"Collected metrics: {metrics}")
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
            
            # Wait for next collection interval
            time.sleep(self.config.get("metrics_poll_interval", 5))  # Default to 5 seconds if None
    
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
                    "network_latency_ms": float(network_latency) if network_latency is not None else float(self.config.get("network_baseline_ms", 50.0))
                }
            else:
                # Use psutil to get real metrics
                cpu_usage = psutil.cpu_percent(interval=0.1)
                ram = psutil.virtual_memory()
                ram_mb = ram.used / (1024 * 1024)  # Convert to MB
                
                # Try to get GPU metrics if available
                vram_mb = 0.0
                try:
                    import pynvml
                    pynvml.nvmlInit()
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    vram_mb = info.used / (1024 * 1024)  # Convert to MB
                    pynvml.nvmlShutdown()
                except:
                    # No NVIDIA GPU or pynvml not available
                    pass
                
                # Get network latency by pinging localhost
                network_latency_ms = 0.0
                try:
                    start_time = time.time()
                    socket.create_connection(("localhost", 22), timeout=1.0)
                    network_latency_ms = (time.time() - start_time) * 1000
                except:
                    network_latency_ms = float(self.config.get("network_baseline_ms", 50.0))
                
                return {
                    "cpu_usage": cpu_usage,
                    "vram_usage_mb": vram_mb,
                    "ram_usage_mb": ram_mb,
                    "network_latency_ms": network_latency_ms
                }
        except Exception as e:
            logger.error(f"Error fetching metrics: {e}")
            # Return fallback values
            return {
                "cpu_usage": 0.0,
                "vram_usage_mb": 0.0,
                "ram_usage_mb": 0.0,
                "network_latency_ms": float(self.config.get("network_baseline_ms", 50.0))
            }
    
    def _get_prometheus_value(self, metric_name: str) -> Optional[float]:
        """
        Query Prometheus for a specific metric value.
        
        Args:
            metric_name: Name of the Prometheus metric to query
            
        Returns:
            Current value of the metric or None if not available
        """
        # This is a placeholder for Prometheus integration
        # In a real implementation, this would query Prometheus
            return None
    
    def _registry_cleanup_loop(self):
        """Background thread that periodically cleans up stale service registrations"""
        while self.running:
            try:
                now = datetime.now()
                stale_threshold = self.config.get("service_timeout_seconds", 60)
                
                with self.services_lock:
                    stale_services = []
                    for name, info in self.services.items():
                        last_heartbeat_str = info.get("last_heartbeat")
                        if not last_heartbeat_str:
                            continue
                        
                        try:
                            last_heartbeat = datetime.fromisoformat(last_heartbeat_str)
                            elapsed_seconds = (now - last_heartbeat).total_seconds()
                            
                            if elapsed_seconds > stale_threshold:
                                stale_services.append(name)
                        except (ValueError, TypeError):
                            # Invalid timestamp format
                            pass
                    
                    # Remove stale services
                    for name in stale_services:
                        logger.info(f"Removing stale service: {name}")
                        del self.services[name]
            
            except Exception as e:
                logger.error(f"Error in registry cleanup: {e}")
            
            # Wait before next cleanup
            time.sleep(15)  # Check every 15 seconds
    
    def _get_current_state(self) -> Dict[str, float]:
        """
        Get the current system state metrics.
        
        Returns:
            Dictionary with current system metrics
        """
        # Get the latest metrics
            return self._fetch_current_metrics()
    
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
            vram_capacity = self.config.get("vram_capacity_mb", 24000)  # Default to 24GB if None
            
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
            ram_capacity = self.config.get("ram_capacity_mb", 32000)  # Default to 32GB if None
            
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
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on this agent.
        
        Returns:
            Dictionary with health status information
        """
        try:
            # Check if metrics thread is running
            metrics_thread_alive = self.metrics_thread is not None and self.metrics_thread.is_alive()
            
            # Check if registry cleanup thread is running
            cleanup_thread_alive = self.registry_cleanup_thread is not None and self.registry_cleanup_thread.is_alive()
            
            # Check socket status
            socket_ok = hasattr(self, 'socket') and self.socket is not None
            
            # Check if we have recent metrics
            has_recent_metrics = len(self.metrics_history["timestamps"]) > 0
            
            # Determine overall health status
            all_checks_passed = metrics_thread_alive and cleanup_thread_alive and socket_ok and has_recent_metrics
            
            health_status = {
                "status": "HEALTHY" if all_checks_passed else "DEGRADED",
                "timestamp": datetime.now().isoformat(),
                "agent_name": self.agent_name,
                "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else 0,
                "checks": {
                    "metrics_thread": metrics_thread_alive,
                    "cleanup_thread": cleanup_thread_alive,
                    "socket": socket_ok,
                    "has_metrics": has_recent_metrics,
                },
                "registered_services_count": len(self.services),
                "metrics_history_length": len(self.metrics_history["timestamps"])
            }
            
            return health_status
        
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            return {
                "status": "ERROR",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "agent_name": self.agent_name
            }
    
    def cleanup(self):
        """Clean up resources used by the agent"""
        logger.info("Cleaning up SystemDigitalTwin resources")
        
        # Stop background threads
        self.running = False
        
        # Wait for threads to terminate
        if self.metrics_thread and self.metrics_thread.is_alive():
            self.metrics_thread.join(timeout=2.0)
        
        if self.registry_cleanup_thread and self.registry_cleanup_thread.is_alive():
            self.registry_cleanup_thread.join(timeout=2.0)
        
        # Close ZMQ sockets
        if hasattr(self, 'socket') and self.socket is not None:
            try:
                self.socket.close(linger=0)
                logger.info("Closed main socket")
        except Exception as e:
                logger.error(f"Error closing main socket: {e}")
        
        # Close health check socket
        self.cleanup_health_check()
        
        # Terminate ZMQ context
        if hasattr(self, 'context') and self.context is not None:
            try:
                self.context.term()
                logger.info("Terminated ZMQ context")
            except Exception as e:
                logger.error(f"Error terminating ZMQ context: {e}")
        
        logger.info("SystemDigitalTwin cleanup complete")
    

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="SystemDigitalTwin Agent")
    parser.add_argument("--port", type=int, default=7120, help="Port to bind to")
    parser.add_argument("--health-port", type=int, default=7121, help="Health check port")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))
    
    # Create agent configuration
    config = {
        "port": args.port,
        "health_check_port": args.health_port,
        "metrics_history_length": 60,
        "metrics_poll_interval": 5,
        "service_timeout_seconds": 60,
        "vram_capacity_mb": 24000,
        "ram_capacity_mb": 32000,
        "network_baseline_ms": 50.0
    }
    
    # Create and run agent
    agent = SystemDigitalTwin(config)
    agent.start_time = time.time()
    
    if agent.setup():
        try:
        agent.run()
    except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down")
    finally:
            agent.cleanup() 
    else:
        logger.error("Failed to set up SystemDigitalTwin agent")
        sys.exit(1)
