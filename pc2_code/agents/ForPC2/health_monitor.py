#!/usr/bin/env python3
"""
Health Monitor Agent
- Monitors the health of all system agents and services
- Reports health status to other agents
- Performs parallel health checks for faster system startup
- Manages agent lifecycle and automatic recovery
"""
import os
import zmq
import json
import time
import logging
import threading
import sys
import asyncio
import socket
import errno
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple
import concurrent.futures
import requests
import subprocess


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("pc2_code", ".."))))
from common.utils.path_env import get_path, join_path, get_file_path
from pc2_code.agents.core_agents.http_server import setup_health_check_server
from pc2_code.agents.utils.config_loader import Config
config = Config()  # Instantiate the global config object
from pc2_code.agents.utils.config_parser import parse_agent_args
_agent_args = parse_agent_args()

# Import system_config for per-machine settings
from pc2_code.config import system_config

# Configure logging
log_file_path = join_path("logs", "health_monitor.log")
log_directory = os.path.dirname(log_file_path)
os.makedirs(log_directory, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('HealthMonitor')

# ZMQ ports - using high port numbers to avoid permission issues
HEALTH_MONITOR_PORT = 5584  # Base port for health monitor
STATUS_PORT = 6584  # Port for status updates
TASK_ROUTER_PORT = 5571  # Port for task router agent

# --- Orchestrator Logic Integration (from orchestrator.py) ---
from pc2_code.src.core.base_agent import BaseAgent
import signal
import psutil
from pathlib import Path
from common.env_helpers import get_env

class OrchestratorAgent(BaseAgent):
    # (Insert orchestrator.py's OrchestratorAgent class and log_collector function here, refactored to avoid conflict with HealthMonitor)
    pass
# ... existing code ...

class HealthMonitor:
    """Health Monitor Agent for checking and reporting the health of all system components."""
    
    def __init__(self, *args, **kwargs):
        """Initialize the Health Monitor Agent.
        
        Args:
            test_ports: Optional tuple of (health_port, status_port) for testing
        """
        # Initialize dictionary attributes
        self.pubsub_health_sockets = {}
        self.pubsub_health_configs = {}
        self.pubsub_health_last_msg = {}
        self.pubsub_health_expected = {}
        self.pubsub_health_timeout = {}
        self.agent_health_status = {}
        self.service_health_status = {}
        self._lock = threading.Lock()
        self.agent_endpoints = {}
        
        # Agent lifecycle management
        self.agent_processes = {}
        self.agent_last_restart = {}
        self.restart_cooldown = 30  # seconds between restart attempts
        
        # Load configuration
        self._load_configuration()
        
        # Initialize agent endpoints from config
        for agent in self.config.get('main_pc_agents', []):
            name = agent.get('name')
            port = agent.get('port')
            if name and port:
                # Assuming health port is main port + 1
                self.agent_endpoints[name] = f"http://{name.lower()}:{port + 1}/health"
        
        # Initialize ZMQ
        self._init_zmq(kwargs.get('test_ports'))
        
        # Running flag
        self.running = True
        
        # Start background threads
        self._start_background_threads()
        logger.info("Health Monitor Agent initialized successfully")
    
    def _init_zmq(self, test_ports: Optional[Tuple[int, int]] = None):
        """Initialize ZMQ sockets.
        
        Args:
            test_ports: Optional tuple of (health_port, status_port) for testing
        """
        try:
            self.context = zmq.Context()
            
            # Set up health check socket (REP)
            self.health_port = test_ports[0] if test_ports else HEALTH_MONITOR_PORT
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.bind(f"tcp://*:{self.health_port}")
            logger.info(f"Health socket bound to port {self.health_port}")
            
            # Set up status publishing socket (PUB)
            self.status_port = test_ports[1] if test_ports and len(test_ports) > 1 else STATUS_PORT
            self.status_socket = self.context.socket(zmq.PUB)
            self.status_socket.bind(f"tcp://*:{self.status_port}")
            logger.info(f"Status socket bound to port {self.status_port}")
            
            # Set up connection to Task Router with reconnection logic
            self._init_task_router_socket()
            
        except zmq.error.ZMQError as e:
            logger.error(f"ZMQ initialization error: {e}")
            raise

    def _init_task_router_socket(self):
        """Initialize Task Router socket with reconnection logic."""
        try:
            if hasattr(self, 'task_router_socket'):
                self.task_router_socket.close()
            
            self.task_router_socket = self.context.socket(zmq.REQ)
            self.task_router_socket.setsockopt(zmq.LINGER, 0)
            self.task_router_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            self.task_router_socket.setsockopt(zmq.RECONNECT_IVL, 1000)  # 1 second reconnection interval
            self.task_router_socket.setsockopt(zmq.RECONNECT_IVL_MAX, 5000)  # 5 second max reconnection interval
            host = getattr(_agent_args, 'host', 'localhost')
            self.task_router_socket.connect(f"tcp://{host}:{TASK_ROUTER_PORT}")
            logger.info(f"Connected to Task Router on port {TASK_ROUTER_PORT}")
        except zmq.error.ZMQError as e:
            logger.warning(f"Failed to connect to Task Router: {e}")
            # Don't raise - we'll try to reconnect later

    def _load_configuration(self):
        """Load configuration from files."""
        try:
            # Load main configuration
            self.config = config.get_config()
            logger.info("Configuration loaded successfully")
            
            # Load health check configuration
            self.health_check_interval = self.config.get('system_config', {}).get('health_check_interval', 30)
            logger.info(f"Health check interval: {self.health_check_interval} seconds")
            
            # Load agent configuration
            self.agents = self.config.get('main_pc_agents', []) + self.config.get('pc2_agents', [])
            logger.info(f"Loaded configuration for {len(self.agents)} agents")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self.config = {}
            self.health_check_interval = 30
            self.agents = []
    
    def _start_background_threads(self):
        """Start background threads for health checks."""
        # Start health check thread
        self.health_check_thread = threading.Thread(target=self._health_check_loop)
        self.health_check_thread.daemon = True
        self.health_check_thread.start()
        logger.info("Health check thread started")
    
    async def _check_agent_health_async(self, agent):
        """Check the health of a single agent asynchronously.
        
        Args:
            agent: Agent configuration dictionary
            
        Returns:
            Tuple of (agent_name, health_status)
        """
        agent_name = agent.get('name', 'Unknown')
        host = agent.get('host', _agent_args.host)
        port = agent.get('port', 0)
        
        try:
            # Create a socket with timeout
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.setsockopt(zmq.LINGER, 0)
            socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2 second timeout
            socket.connect(f"tcp://{host}:{port}")
            
            # Send health check request
            socket.send_json({"action": "health_check"})
            
            # Wait for response with timeout
            try:
                response = socket.recv_json()
            except zmq.error.Again:
                logger.warning(f"Health check timeout for {agent_name}")
                return agent_name, {
                    'status': 'timeout',
                    'last_checked': datetime.now().isoformat(),
                    'error': 'Request timed out'
                }
            
            # Close socket
            socket.close()
            
            # Process response
            status = response.get('status', 'unknown')
            is_healthy = status == 'ok' or status == 'healthy'
            
            logger.debug(f"Health check for {agent_name}: {'Healthy' if is_healthy else 'Unhealthy'}")
            return agent_name, {
                'status': 'healthy' if is_healthy else 'unhealthy',
                'last_checked': datetime.now().isoformat(),
                'details': response
            }
            
        except zmq.error.ZMQError as e:
            logger.error(f"ZMQ error checking {agent_name}: {e}")
            return agent_name, {
                'status': 'error',
                'last_checked': datetime.now().isoformat(),
                'error': f"ZMQ error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error checking {agent_name}: {e}")
            return agent_name, {
                'status': 'error',
                'last_checked': datetime.now().isoformat(),
                'error': f"Unexpected error: {str(e)}"
            }
        finally:
            try:
                socket.close()
            except:
                pass
    
    async def _check_all_agents_health_async(self):
        """Check the health of all agents in parallel using asyncio."""
        tasks = []
        for agent in self.agents:
            if agent.get('required', False):  # Only check required agents
                tasks.append(self._check_agent_health_async(agent))
        
        # Run all tasks concurrently and collect results
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        health_status = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error in health check: {result}")
                continue
                
            agent_name, status = result
            health_status[agent_name] = status
            
            # Update agent health status with thread safety
            with self._lock:
                self.agent_health_status[agent_name] = status
        
        return health_status
    
    def check_all_agents_health(self):
        results = {}
        for agent_name, url in self.agent_endpoints.items():
            try:
                resp = requests.get(url, timeout=2)
                results[agent_name] = resp.status_code == 200
            except Exception as e:
                results[agent_name] = False
        return results
    
    def check_pc2_services(self):
        """Check health of PC2 services with retry logic."""
        try:
            if not hasattr(self, 'task_router_socket') or self.task_router_socket.closed:
                self._init_task_router_socket()
                
            # Send health check request
            try:
                self.task_router_socket.send_json({
                    'type': 'health_check',
                    'timestamp': datetime.now().isoformat()
                })
            except zmq.error.ZMQError as e:
                logger.warning(f"Failed to send health check to Task Router: {e}")
                self._init_task_router_socket()
                return
                
            # Wait for response
            try:
                response = self.task_router_socket.recv_json()
                # Process response...
                return response
            except zmq.error.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    logger.warning("Task Router health check timed out")
                else:
                    logger.error(f"Error checking PC2 services: {e}")
                self._init_task_router_socket()
                return None
                
        except Exception as e:
            logger.error(f"Error checking PC2 services: {e}")
            return None
            # Don't raise - we'll try again next time
    
    def _publish_health_status(self):
        """Publish current health status to subscribers."""
        try:
            status = self._get_system_health()
            self.status_socket.send_json(status)
            logger.debug("Published health status")
        except Exception as e:
            logger.error(f"Error publishing health status: {e}")
    
    def _get_system_health(self):
        """Get the current health status of the entire system."""
        with self._lock:
            return {
                'timestamp': datetime.now().isoformat(),
                'agents': self.agent_health_status,
                'services': self.service_health_status,
                'overall_status': 'healthy' if all(
                    status.get('status') == 'healthy' 
                    for status in self.agent_health_status.values()
                ) else 'unhealthy'
            }
    
    def _health_check_loop(self):
        """Background thread for periodic health checks."""
        logger.info("Health check loop started")
        
        while self.running:
            try:
                # Check agent health
                self.check_all_agents_health()
                
                # Check PC2 services
                self.check_pc2_services()
                
                # Sleep until next check
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(5)  # Sleep for a short time before retrying
    
    def handle_request(self, request):
        """Handle incoming health check requests.
        
        Args:
            request: Request dictionary
            
        Returns:
            Response dictionary
        """
        action = request.get('action', '')
        
        if action == 'health_check':
            # Return own health status
            return {
                'status': 'ok',
                'timestamp': datetime.now().isoformat(),
                'agent': 'HealthMonitor',
                'version': '1.0.0'
            }
            
        elif action == 'get_agents_health':
            # Return health status of all agents
            return {
                'status': 'ok',
                'agents': self.agent_health_status
            }
            
        elif action == 'get_services_health':
            # Return health status of all services
            return {
                'status': 'ok',
                'services': self.service_health_status
            }
            
        elif action == 'get_system_health':
            # Return system health metrics
            return {
                'status': 'ok',
                'system': self._get_system_health()
            }
            
        else:
            # Unknown action
            return {
                'status': 'error',
                'error': f"Unknown action: {action}"
            }
    
    def run(self):
        """Main run loop."""
        logger.info("Health Monitor Agent starting...")
        
        try:
            while self.running:
                try:
                    # Wait for request
                    request = self.health_socket.recv_json()
                    logger.debug(f"Received request: {request}")
                    
                    # Process request
                    response = self.handle_request(request)
                    
                    # Send response
                    self.health_socket.send_json(response)
                    
                except zmq.error.ZMQError as e:
                    logger.error(f"ZMQ error in run loop: {e}")
                    # Try to send an error response
                    try:
                        self.health_socket.send_json({
                            'status': 'error',
                            'error': str(e)
                        })
                    except:
                        pass
                    
                except Exception as e:
                    logger.error(f"Error in run loop: {e}")
                    # Try to send an error response
                    try:
                        self.health_socket.send_json({
                            'status': 'error',
                            'error': str(e)
                        })
                    except:
                        pass
                    
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up resources...")
        
        # Stop background threads
        self.running = False
        
        # Close ZMQ sockets
        if hasattr(self, 'health_socket'):
            self.health_socket.close()
        
        if hasattr(self, 'status_socket'):
            self.status_socket.close()
        
        if hasattr(self, 'task_router_socket'):
            self.task_router_socket.close()
        
        # Close ZMQ context
        if hasattr(self, 'context'):
            self.context.term()
            
        # Stop HTTP health check server
        setup_health_check_server.stop()
        
        logger.info("Cleanup complete")

    def start_agent(self, agent_name: str, max_retries: int = 3) -> bool:
        """Start an agent process with retry logic.
        
        Args:
            agent_name: Name of the agent to start
            max_retries: Maximum number of retry attempts
            
        Returns:
            bool: True if agent started successfully, False otherwise
        """
        if agent_name in self.agent_processes and self.agent_processes[agent_name].poll() is None:
            logger.info(f"Agent {agent_name} is already running")
            return True
            
        agent_config = next((a for a in self.agents if a.get('name') == agent_name), None)
        if not agent_config:
            logger.error(f"Agent {agent_name} not found in configuration")
            return False
            
        script_path = agent_config.get('script_path')
        if not script_path or not os.path.exists(script_path):
            logger.error(f"Script path not found for agent {agent_name}: {script_path}")
            return False
            
        for attempt in range(max_retries):
            try:
                # Start the agent process
                process = subprocess.Popen(
                    [sys.executable, script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Store process info
                self.agent_processes[agent_name] = process
                self.agent_last_restart[agent_name] = time.time()
                
                # Start monitoring threads
                threading.Thread(
                    target=self._monitor_output,
                    args=(process.stdout, agent_name, "stdout"),
                    daemon=True
                ).start()
                
                threading.Thread(
                    target=self._monitor_output,
                    args=(process.stderr, agent_name, "stderr"),
                    daemon=True
                ).start()
                
                logger.info(f"Started agent {agent_name} (PID: {process.pid})")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start agent {agent_name} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
        return False

    def stop_agent(self, agent_name: str) -> bool:
        """Stop an agent process gracefully.
        
        Args:
            agent_name: Name of the agent to stop
            
        Returns:
            bool: True if agent stopped successfully, False otherwise
        """
        if agent_name not in self.agent_processes:
            logger.warning(f"Agent {agent_name} is not running")
            return True
            
        process = self.agent_processes[agent_name]
        try:
            # Try graceful shutdown first
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
                
            # Force kill if still running
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
                
            del self.agent_processes[agent_name]
            logger.info(f"Stopped agent {agent_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping agent {agent_name}: {e}")
            return False

    def restart_agent(self, agent_name: str) -> bool:
        """Restart an agent process.
        
        Args:
            agent_name: Name of the agent to restart
            
        Returns:
            bool: True if agent restarted successfully, False otherwise
        """
        # Check cooldown period
        last_restart = self.agent_last_restart.get(agent_name, 0)
        if time.time() - last_restart < self.restart_cooldown:
            logger.warning(f"Agent {agent_name} was restarted recently, waiting for cooldown")
            return False
            
        # Stop the agent
        if not self.stop_agent(agent_name):
            logger.error(f"Failed to stop agent {agent_name} before restart")
            return False
            
        # Start the agent
        return self.start_agent(agent_name)

    def _monitor_output(self, pipe, agent_name: str, stream_name: str):
        """Monitor agent process output.
        
        Args:
            pipe: Process output pipe
            agent_name: Name of the agent
            stream_name: Name of the stream (stdout/stderr)
        """
        try:
            for line in pipe:
                line = line.strip()
                if line:
                    log_level = logging.ERROR if stream_name == "stderr" else logging.INFO
                    logger.log(log_level, f"[{agent_name}] {line}")
        except Exception as e:
            logger.error(f"Error monitoring {stream_name} for agent {agent_name}: {e}")


    def _get_health_status(self) -> Dict[str, Any]:
        """
        Get the health status of the agent.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        return {
            "status": "ok",
            "uptime": time.time() - self.start_time,
            "name": self.name,
            "version": getattr(self, "version", "1.0.0"),
            "port": self.port,
            "health_port": getattr(self, "health_port", None),
            "error_reporting": bool(getattr(self, "error_bus", None))
        }
if __name__ == "__main__":
    # Create and run the health monitor agent
    monitor = HealthMonitor()
    monitor.run() 