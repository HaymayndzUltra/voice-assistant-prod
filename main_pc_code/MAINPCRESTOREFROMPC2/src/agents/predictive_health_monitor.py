"""
Predictive Health Monitor
- Uses machine learning to predict potential agent failures
- Monitors system resources and agent performance
- Implements tiered recovery strategies
- Provides proactive health management
- Coordinates agent lifecycle and dependencies
- Supports distributed system deployment
"""

import logging
import socket
import zmq
import yaml
import time
import sys
import os
import signal
import sqlite3
import threading
import subprocess
import platform
import psutil
import pickle
import json
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

from src.core.base_agent import BaseAgent, logger
from config.system_config import DEFAULT_CONFIG as config

# Load distributed config
with open(Path(__file__).parent.parent.parent / "config" / "distributed_config.json") as f:
    distributed_config = json.load(f)

# Configure logging
logger = logging.getLogger(__name__)

# Constants
HEALTH_MONITOR_PORT = config.get('zmq.health_monitor_port', 5605)
SELF_HEALING_PORT = config.get('zmq.self_healing_port', 5606)
RESTART_COOLDOWN = config.get('system.restart_cooldown', 60)  # seconds
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for health check requests

class PredictiveHealthMonitor(BaseAgent):
    """Predictive health monitoring system for voice assistant agents"""
    
    def __init__(self, port: Optional[int] = None, **kwargs):
        super().__init__(port=port, name="PredictiveHealthMonitor")
        """Initialize the predictive health monitor"""
        # Get machine information
        self.hostname = socket.gethostname()
        self.ip_address = socket.gethostbyname(self.hostname)
        logger.info(f"Running on {self.hostname} ({self.ip_address})")
        
        # Initialize psutil availability
        self.psutil_available = True
        try:
            import psutil
        except ImportError:
            logger.warning("psutil is not installed. Some functionality will be limited.")
            logger.warning("Install psutil with: pip install psutil")
            self.psutil_available = False
        
        # Identify which machine this is in the distributed config
        self.machine_id = self._identify_machine()
        if self.machine_id:
            logger.info(f"Identified as machine '{self.machine_id}' in distributed configuration")
        else:
            logger.warning("This machine is not in the distributed configuration")
        
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Socket to receive requests
        self.receiver = self.context.socket(zmq.REP)
        self.receiver.bind(f"tcp://127.0.0.1:{HEALTH_MONITOR_PORT}")
        logger.info(f"Predictive Health Monitor bound to port {HEALTH_MONITOR_PORT}")
        
        # Socket to communicate with self-healing agent
        self.self_healing = self.context.socket(zmq.REQ)
        self.self_healing.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.self_healing.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.self_healing.connect(f"tcp://localhost:{SELF_HEALING_PORT}")
        logger.info(f"Connected to Self-Healing Agent on port {SELF_HEALING_PORT}")
        
        # Initialize discovery service if enabled
        self.discovery_socket = None
        if distributed_config["discovery_service"]["enabled"]:
            self.discovery_port = distributed_config["discovery_service"]["port"]
            
            if self.machine_id == "main_pc":
                # Main PC hosts the discovery service
                self.discovery_socket = self.context.socket(zmq.REP)
                self.discovery_socket.bind(f"tcp://*:{self.discovery_port}")
                logger.info(f"Discovery service bound to port {self.discovery_port}")
            elif self.machine_id:
                # Other machines connect to the discovery service
                self.discovery_socket = self.context.socket(zmq.REQ)
                self.discovery_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
                self.discovery_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
                main_pc_ip = distributed_config["machines"]["main_pc"]["ip"]
                self.discovery_socket.connect(f"tcp://{main_pc_ip}:{self.discovery_port}")
                logger.info(f"Connected to discovery service at {main_pc_ip}:{self.discovery_port}")
        
        # Initialize database
        self.db_path = Path(config.get('system.data_dir', 'data')) / "health_monitor.sqlite"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._create_tables()
        
        # Initialize model
        self.model_path = Path(config.get('system.models_dir', 'models')) / "health_monitor" / "failure_predictor.pkl"
        self.model = self._load_model()
        
        # Agent health status
        self.agent_health = {}
        
        # Resource usage history
        self.resource_history = {}
        
        # Agent processes and dependencies
        self.agent_processes = {}
        self.agent_last_restart = {}
        self.agent_dependencies = {}
        self.agent_configs = {}
        
        # Load agent configurations
        self._load_agent_configs()
        
        # Recovery strategies
        self.recovery_strategies = {
            "tier1": {
                "description": "Basic recovery: restart agent",
                "actions": ["restart_agent"]
            },
            "tier2": {
                "description": "Intermediate recovery: restart agent with clean state",
                "actions": ["clear_agent_state", "restart_agent"]
            },
            "tier3": {
                "description": "Advanced recovery: restart agent with dependencies",
                "actions": ["restart_dependencies", "clear_agent_state", "restart_agent"]
            },
            "tier4": {
                "description": "Critical recovery: restart all agents",
                "actions": ["restart_all_agents"]
            }
        }
        
        # Running flag
        self.running = True
        
        # Start monitoring thread
        self.monitor_thread = None
        
        # Initialize optimization configuration
        self.optimization_config = {
            "memory_threshold": 80,  # percent
            "cpu_threshold": 80,  # percent
            "disk_threshold": 90,  # percent
            "process_memory_limit": 5.0,  # percent
            "optimization_interval": 300  # 5 minutes
        }
        
        # Initialize performance metrics
        self.performance_metrics: Dict[str, List[float]] = {
            "cpu_usage": [],
            "memory_usage": [],
            "disk_usage": [],
            "response_times": []
        }
        
        # Ensure psutil is available
        self._ensure_dependencies()
        
        # Start optimization thread
        self.optimization_thread = threading.Thread(target=self._optimization_loop, daemon=True)
        self.optimization_thread.start()
        
        logger.info("Predictive Health Monitor initialized")

    def _create_tables(self) -> None:
        """Create necessary database tables."""
        try:
            cursor = self.conn.cursor()
            
            # Create health metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS health_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    cpu_usage REAL,
                    memory_usage REAL,
                    response_time REAL,
                    error_rate REAL
                )
            """)
            
            # Create recovery actions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recovery_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    action_type TEXT NOT NULL,
                    success BOOLEAN,
                    error_message TEXT
                )
            """)
            
            self.conn.commit()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    def _load_model(self) -> Any:
        """Load the failure prediction model."""
        try:
            if self.model_path.exists():
                with open(self.model_path, 'rb') as f:
                    model = pickle.load(f)
                logger.info("Failure prediction model loaded successfully")
                return model
            else:
                logger.warning("No failure prediction model found")
                return None
        except Exception as e:
            logger.error(f"Error loading failure prediction model: {e}")
            return None

    def _monitor_output(self, pipe, agent_name: str, stream_type: str) -> None:
        """Monitor agent process output.
        
        Args:
            pipe: Process output pipe
            agent_name: Name of the agent
            stream_type: Type of stream (stdout/stderr)
        """
        try:
            for line in pipe:
                line = line.strip()
                if line:
                    if stream_type == "stderr":
                        logger.error(f"[{agent_name}] {line}")
                    else:
                        logger.info(f"[{agent_name}] {line}")
        except Exception as e:
            logger.error(f"Error monitoring {stream_type} for {agent_name}: {e}")

    def _identify_machine(self) -> Optional[str]:
        """Identify which machine this is in the distributed configuration.
        
        Returns:
            Optional[str]: Machine ID if found, None otherwise
        """
        # Check by IP address
        for machine_id, machine_info in distributed_config["machines"].items():
            if machine_info["ip"] == self.ip_address:
                return machine_id
        
        # If IP doesn't match, try hostname
        for machine_id, machine_info in distributed_config["machines"].items():
            if machine_id.lower() in self.hostname.lower():
                return machine_id
        
        return None

    def _load_agent_configs(self):
        """Load agent configurations from startup config"""
        try:
            with open("config/startup_config.yaml", 'r') as f:
                startup_config = yaml.safe_load(f)
            
            for agent in startup_config.get('agents', []):
                name = agent.get('name')
                if name:
                    self.agent_configs[name] = {
                        'script': agent.get('script_path'),
                        'host': agent.get('host', 'localhost'),
                        'port': agent.get('port'),
                        'dependencies': agent.get('dependencies', []),
                        'required': agent.get('required', False)
                    }
                    self.agent_dependencies[name] = agent.get('dependencies', [])
            
            logger.info(f"Loaded configurations for {len(self.agent_configs)} agents")
        except Exception as e:
            logger.error(f"Error loading agent configurations: {e}")
            self.agent_configs = {}

    def start_agent(self, agent_name: str, max_retries: int = 3) -> bool:
        """Start a specific agent process with dependency handling.
        
        Args:
            agent_name: Name of the agent to start
            max_retries: Maximum number of retry attempts
            
        Returns:
            bool: True if agent started successfully, False otherwise
        """
        if agent_name not in self.agent_configs:
            logger.error(f"Unknown agent: {agent_name}")
            return False
            
        # Check if already running
        if agent_name in self.agent_processes and self.agent_processes[agent_name].poll() is None:
            logger.warning(f"Agent {agent_name} is already running")
            return True
            
        # Check cooldown period
        now = time.time()
        if agent_name in self.agent_last_restart and (now - self.agent_last_restart[agent_name]) < RESTART_COOLDOWN:
            logger.warning(f"Agent {agent_name} in cooldown period, not restarting yet")
            return False
            
        # Start dependencies first
        for dep in self.agent_dependencies.get(agent_name, []):
            if not self.start_agent(dep):
                logger.error(f"Failed to start dependency {dep} for agent {agent_name}")
                return False
        
        # Start the agent
        config = self.agent_configs[agent_name]
        attempt = 0
        while attempt < max_retries:
            try:
                python_executable = sys.executable
                cmd = [python_executable, config["script"]]
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                )
                
                self.agent_processes[agent_name] = process
                self.agent_last_restart[agent_name] = now
                
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
                
                logger.info(f"Started agent {agent_name} (attempt {attempt+1})")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start agent {agent_name} on attempt {attempt+1}: {e}")
                attempt += 1
                if attempt < max_retries:
                    backoff = 2 ** attempt
                    logger.info(f"Retrying agent {agent_name} in {backoff}s...")
                    time.sleep(backoff)
                else:
                    logger.error(f"Giving up on starting agent {agent_name} after {max_retries} attempts")
                    return False

    def stop_agent(self, agent_name: str) -> bool:
        """Stop a specific agent process and its dependencies.
        
        Args:
            agent_name: Name of the agent to stop
            
        Returns:
            bool: True if agent stopped successfully, False otherwise
        """
        if agent_name not in self.agent_processes:
            logger.warning(f"Agent {agent_name} is not running")
            return True
            
        process = self.agent_processes[agent_name]
        if process.poll() is not None:
            # Already terminated
            self.agent_processes.pop(agent_name)
            return True
            
        try:
            # Try graceful termination first
            if os.name == 'nt':
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                process.terminate()
                
            # Wait for termination
            for _ in range(5):  # 5 seconds timeout
                if process.poll() is not None:
                    logger.info(f"Agent {agent_name} stopped gracefully")
                    self.agent_processes.pop(agent_name)
                    return True
                time.sleep(1)
                
            # Force kill if still running
            process.kill()
            logger.warning(f"Agent {agent_name} force killed")
            self.agent_processes.pop(agent_name)
            return True
            
        except Exception as e:
            logger.error(f"Error stopping agent {agent_name}: {e}")
            return False

    def restart_agent(self, agent_name: str) -> bool:
        """Restart a specific agent and its dependencies.
        
        Args:
            agent_name: Name of the agent to restart
            
        Returns:
            bool: True if agent restarted successfully, False otherwise
        """
        # Stop the agent and its dependencies
        for dep in reversed(self.agent_dependencies.get(agent_name, [])):
            self.stop_agent(dep)
        
        self.stop_agent(agent_name)
        time.sleep(1)  # Give it a moment to fully stop
        
        # Start the agent and its dependencies
        return self.start_agent(agent_name)

    def handle_discovery_requests(self):
        """Handle discovery service requests for distributed deployment"""
        if not self.discovery_socket:
            logger.error("Discovery socket not initialized")
            return
            
        logger.info("Starting discovery service handler")
        
        # Remote agent status tracking
        remote_agents = {}
        
        while self.running:
            try:
                # Wait for message with timeout
                if self.discovery_socket.poll(timeout=1000) == 0:
                    continue
                
                # Receive request
                request_str = self.discovery_socket.recv_string()
                request = json.loads(request_str)
                
                # Handle request
                request_type = request.get("request_type")
                
                if request_type == "register":
                    # Register a remote agent
                    machine_id = request.get("machine_id")
                    agent_name = request.get("agent_name")
                    
                    if not machine_id or not agent_name:
                        response = {
                            "status": "error",
                            "error": "Missing machine_id or agent_name"
                        }
                    else:
                        remote_agents[(machine_id, agent_name)] = {
                            "status": "running",
                            "last_update": time.time()
                        }
                        
                        response = {
                            "status": "success",
                            "message": f"Registered agent {agent_name} on machine {machine_id}"
                        }
                
                elif request_type == "unregister":
                    # Unregister a remote agent
                    machine_id = request.get("machine_id")
                    agent_name = request.get("agent_name")
                    
                    if not machine_id or not agent_name:
                        response = {
                            "status": "error",
                            "error": "Missing machine_id or agent_name"
                        }
                    else:
                        if (machine_id, agent_name) in remote_agents:
                            del remote_agents[(machine_id, agent_name)]
                        
                        response = {
                            "status": "success",
                            "message": f"Unregistered agent {agent_name} on machine {machine_id}"
                        }
                
                elif request_type == "heartbeat":
                    # Update agent heartbeat
                    machine_id = request.get("machine_id")
                    agent_name = request.get("agent_name")
                    
                    if not machine_id or not agent_name:
                        response = {
                            "status": "error",
                            "error": "Missing machine_id or agent_name"
                        }
                    else:
                        if (machine_id, agent_name) in remote_agents:
                            remote_agents[(machine_id, agent_name)]["last_update"] = time.time()
                        else:
                            remote_agents[(machine_id, agent_name)] = {
                                "status": "running",
                                "last_update": time.time()
                            }
                        
                        response = {
                            "status": "success"
                        }
                
                elif request_type == "get_status":
                    # Get status of all agents
                    response = {
                        "status": "success",
                        "agents": remote_agents
                    }
                
                else:
                    response = {
                        "status": "error",
                        "error": f"Unknown request type: {request_type}"
                    }
                
                # Send response
                self.discovery_socket.send_string(json.dumps(response))
            
            except zmq.Again:
                # Timeout, continue loop
                pass
            except json.JSONDecodeError:
                response = {
                    "status": "error",
                    "error": "Invalid JSON in request"
                }
                self.discovery_socket.send_string(json.dumps(response))
            except Exception as e:
                logger.error(f"Error in discovery service: {str(e)}")
                traceback.print_exc()
                
                try:
                    response = {
                        "status": "error",
                        "error": f"Error in discovery service: {str(e)}"
                    }
                    self.discovery_socket.send_string(json.dumps(response))
                except:
                    pass 

    def optimize_memory(self) -> Dict[str, Any]:
        """Optimize memory usage by identifying and managing high-memory processes.
        
        Returns:
            dict: Optimization results including memory freed and processes terminated
        """
        logger.info("Optimizing memory usage")
        
        if not self.psutil_available:
            return {"error": "psutil is not available"}
        
        result = {
            "before": self._get_memory_usage(),
            "processes_terminated": 0,
            "errors": []
        }
        
        try:
            # Get memory usage before optimization
            before_memory = psutil.virtual_memory()
            
            # Find high memory processes
            high_memory_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent']):
                try:
                    # Skip system processes
                    if proc.username() in ['SYSTEM', 'LOCAL SERVICE', 'NETWORK SERVICE'] or proc.name() in ['svchost.exe', 'services.exe', 'lsass.exe', 'winlogon.exe', 'csrss.exe', 'smss.exe']:
                        continue
                    
                    # Skip current process
                    if proc.pid == os.getpid():
                        continue
                    
                    # Add high memory processes to the list
                    if proc.info['memory_percent'] > 5.0:  # Processes using more than 5% of memory
                        high_memory_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Sort by memory usage (highest first)
            high_memory_processes.sort(key=lambda p: p.info['memory_percent'], reverse=True)
            
            # Terminate high memory processes (with caution)
            for proc in high_memory_processes[:3]:  # Limit to top 3 processes
                try:
                    logger.info(f"Terminating high memory process: {proc.name()} (PID: {proc.pid}, Memory: {proc.info['memory_percent']:.2f}%)")
                    proc.terminate()
                    result["processes_terminated"] += 1
                except Exception as e:
                    result["errors"].append(f"Error terminating process {proc.name()} (PID: {proc.pid}): {str(e)}")
            
            # Wait a moment for memory to be freed
            time.sleep(2)
            
            # Get memory usage after optimization
            after_memory = psutil.virtual_memory()
            result["after"] = self._get_memory_usage()
            
            # Calculate memory freed
            memory_freed = after_memory.available - before_memory.available
            result["memory_freed"] = memory_freed
            result["memory_freed_human"] = self._format_bytes(memory_freed)
            
            logger.info(f"Memory optimized: {result['processes_terminated']} processes terminated, {result['memory_freed_human']} freed")
            
            return result
        
        except Exception as e:
            logger.error(f"Error optimizing memory: {str(e)}")
            result["errors"].append(f"Error optimizing memory: {str(e)}")
            return result

    def find_large_files(self, path: str = None, min_size_mb: int = 100, limit: int = 20) -> List[Dict[str, Any]]:
        """Find large files on the system that might impact performance.
        
        Args:
            path: Path to search (default: system drive)
            min_size_mb: Minimum file size in MB (default: 100)
            limit: Maximum number of files to return (default: 20)
            
        Returns:
            list: List of large files with their sizes
        """
        logger.info(f"Finding large files (min size: {min_size_mb} MB, limit: {limit})")
        
        if path is None:
            # Use system drive as default path
            if platform.system() == "Windows":
                path = "C:\\"
            else:
                path = "/"
        
        min_size_bytes = min_size_mb * 1024 * 1024
        
        large_files = []
        
        try:
            for root, dirs, files in os.walk(path):
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        if os.path.isfile(file_path):
                            size = os.path.getsize(file_path)
                            if size >= min_size_bytes:
                                large_files.append({
                                    "path": file_path,
                                    "size": size,
                                    "size_human": self._format_bytes(size)
                                })
                    except Exception as e:
                        logger.error(f"Error checking file {file_path}: {str(e)}")
                
                # Sort by size (largest first) and limit the results
                large_files.sort(key=lambda x: x["size"], reverse=True)
                large_files = large_files[:limit]
        
        except Exception as e:
            logger.error(f"Error finding large files: {str(e)}")
        
        return large_files

    def optimize_system(self) -> Dict[str, Any]:
        """Perform a full system optimization.
        
        Returns:
            dict: Optimization results including memory and disk space freed
        """
        logger.info("Performing full system optimization")
        
        result = {
            "status": "success",
            "steps": {}
        }
        
        # Step 1: Optimize memory
        logger.info("Step 1: Optimizing memory")
        result["steps"]["memory"] = self.optimize_memory()
        
        # Step 2: Find large files
        logger.info("Step 2: Finding large files")
        result["steps"]["large_files"] = self.find_large_files()
        
        # Step 3: Run Windows Disk Cleanup (Windows only)
        if platform.system() == "Windows":
            logger.info("Step 3: Running Windows Disk Cleanup")
            result["steps"]["disk_cleanup"] = self._run_windows_disk_cleanup()
        
        # Calculate total memory freed
        total_memory_freed = 0
        if "memory" in result["steps"]:
            total_memory_freed = result["steps"]["memory"].get("memory_freed", 0)
        
        result["total_memory_freed"] = total_memory_freed
        result["total_memory_freed_human"] = self._format_bytes(total_memory_freed)
        
        logger.info(f"System optimization completed. Total memory freed: {result['total_memory_freed_human']}")
        
        return result

    def _run_windows_disk_cleanup(self) -> Dict[str, Any]:
        """Run Windows Disk Cleanup utility.
        
        Returns:
            dict: Cleanup results
        """
        logger.info("Running Windows Disk Cleanup")
        
        result = {
            "status": "success",
            "message": "",
            "errors": []
        }
        
        if platform.system() != "Windows":
            result["status"] = "error"
            result["message"] = "Windows Disk Cleanup is only available on Windows"
            return result
        
        try:
            # Run cleanmgr.exe with /sagerun:1 flag
            logger.info("Running cleanmgr.exe")
            subprocess.run(["cleanmgr.exe", "/sagerun:1"], check=True)
            
            result["message"] = "Windows Disk Cleanup completed successfully"
            logger.info(result["message"])
            
            return result
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running Windows Disk Cleanup: {str(e)}")
            result["status"] = "error"
            result["message"] = f"Error running Windows Disk Cleanup: {str(e)}"
            result["errors"].append(str(e))
            return result
        
        except Exception as e:
            logger.error(f"Error running Windows Disk Cleanup: {str(e)}")
            result["status"] = "error"
            result["message"] = f"Error running Windows Disk Cleanup: {str(e)}"
            result["errors"].append(str(e))
            return result

    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage information.
        
        Returns:
            dict: Memory usage statistics
        """
        if not self.psutil_available:
            return {"error": "psutil is not available"}
        
        try:
            memory = psutil.virtual_memory()
            return {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "free": memory.free,
                "percent": memory.percent
            }
        except Exception as e:
            logger.error(f"Error getting memory usage: {str(e)}")
            return {"error": str(e)}

    def _format_bytes(self, bytes: Union[int, float]) -> str:
        """Format bytes in a human-readable format.
        
        Args:
            bytes: Number of bytes
            
        Returns:
            str: Formatted string (e.g., "1.5 MB")
        """
        try:
            bytes_float = float(bytes)
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_float < 1024:
                    return f"{bytes_float:.2f} {unit}"
                bytes_float /= 1024
            return f"{bytes_float:.2f} PB"
        except Exception as e:
            logger.error(f"Error formatting bytes: {str(e)}")
            return "0 B"

    def _ensure_dependencies(self) -> None:
        """Ensure all required dependencies are installed"""
        try:
            import psutil
            logger.info("All required dependencies are installed")
            self.psutil_available = True
        except ImportError:
            logger.warning("psutil is not installed. Some functionality will be limited.")
            logger.warning("Install psutil with: pip install psutil")
            self.psutil_available = False

    def _optimize_memory(self) -> Dict[str, Any]:
        """Optimize memory usage"""
        logger.info("Optimizing memory usage")
        
        if not self.psutil_available:
            return {"error": "psutil is not available"}
        
        result = {
            "before": self._get_memory_usage(),
            "processes_terminated": 0,
            "errors": []
        }
        
        try:
            # Get memory usage before optimization
            before_memory = psutil.virtual_memory()
            
            # Find high memory processes
            high_memory_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent']):
                try:
                    # Skip system processes
                    if proc.username() in ['SYSTEM', 'LOCAL SERVICE', 'NETWORK SERVICE'] or proc.name() in ['svchost.exe', 'services.exe', 'lsass.exe', 'winlogon.exe', 'csrss.exe', 'smss.exe']:
                        continue
                    
                    # Skip current process
                    if proc.pid == os.getpid():
                        continue
                    
                    # Add high memory processes to the list
                    if proc.info['memory_percent'] > self.optimization_config["process_memory_limit"]:
                        high_memory_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Sort by memory usage (highest first)
            high_memory_processes.sort(key=lambda p: p.info['memory_percent'], reverse=True)
            
            # Terminate high memory processes (with caution)
            for proc in high_memory_processes[:3]:  # Limit to top 3 processes
                try:
                    logger.info(f"Terminating high memory process: {proc.name()} (PID: {proc.pid}, Memory: {proc.info['memory_percent']:.2f}%)")
                    proc.terminate()
                    result["processes_terminated"] += 1
                except Exception as e:
                    result["errors"].append(f"Error terminating process {proc.name()} (PID: {proc.pid}): {str(e)}")
            
            # Wait a moment for memory to be freed
            time.sleep(2)
            
            # Get memory usage after optimization
            after_memory = psutil.virtual_memory()
            result["after"] = self._get_memory_usage()
            
            # Calculate memory freed
            memory_freed = after_memory.available - before_memory.available
            result["memory_freed"] = memory_freed
            result["memory_freed_human"] = self._format_bytes(memory_freed)
            
            logger.info(f"Memory optimized: {result['processes_terminated']} processes terminated, {result['memory_freed_human']} freed")
            
            return result
        
        except Exception as e:
            logger.error(f"Error optimizing memory: {str(e)}")
            result["errors"].append(f"Error optimizing memory: {str(e)}")
            return result

    def _optimization_loop(self) -> None:
        """Main optimization loop"""
        while self.running:
            try:
                # Get current system metrics
                metrics = self._get_system_metrics()
                
                # Check if optimization is needed
                if self._needs_optimization(metrics):
                    logger.info("System needs optimization")
                    
                    # Optimize memory
                    memory_result = self._optimize_memory()
                    
                    # Log optimization results
                    logger.info(f"Optimization completed: {memory_result}")
                
                # Sleep until next check
                time.sleep(self.optimization_config["optimization_interval"])
                
            except Exception as e:
                logger.error(f"Error in optimization loop: {str(e)}")
                time.sleep(5)  # Wait before retrying

    def _needs_optimization(self, metrics: Dict[str, Any]) -> bool:
        """Check if system needs optimization"""
        try:
            # Check memory usage
            if metrics.get("memory", {}).get("percent", 0) > self.optimization_config["memory_threshold"]:
                return True
            
            # Check CPU usage
            if metrics.get("cpu_percent", 0) > self.optimization_config["cpu_threshold"]:
                return True
            
            # Check disk usage
            for mount, usage in metrics.get("disk", {}).items():
                if usage.get("percent", 0) > self.optimization_config["disk_threshold"]:
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking optimization needs: {str(e)}")
            return False  # Ensure a bool is always returned

    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            return {
                "timestamp": time.time(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory": self._get_memory_usage(),
                "disk": self._get_disk_usage(),
                "network": psutil.net_io_counters()._asdict()
            }
        except Exception as e:
            error_msg = str(e) if e is not None else "Unknown error"
            logger.error(f"Error getting system metrics: {error_msg}")
            return {
                "timestamp": time.time(),
                "cpu_percent": 0,
                "memory": {"error": error_msg},
                "disk": {"error": error_msg},
                "network": {"error": error_msg}
            }

    def _get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage information"""
        if not self.psutil_available:
            return {"error": "psutil is not available"}
        
        try:
            disk_usage = {}
            for part in psutil.disk_partitions():
                if part.fstype:
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                        disk_usage[part.mountpoint] = {
                            "total": usage.total,
                            "used": usage.used,
                            "free": usage.free,
                            "percent": usage.percent
                        }
                    except PermissionError:
                        disk_usage[part.mountpoint] = {"error": "Permission denied"}
            return disk_usage
        except Exception as e:
            logger.error(f"Error getting disk usage: {str(e)}")
            return {"error": str(e)}

    def check_agent_health(self, agent_name: str, host: str, port: int) -> bool:
        """Check the health of an agent.
        
        Args:
            agent_name: Name of the agent
            host: Host address
            port: Port number
            
        Returns:
            True if agent is healthy, False otherwise
        """
        try:
            # Create a new context and socket for each health check
            # This prevents socket contention issues
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            
            # Set timeout values to prevent hanging
            socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            
            # Connect to agent
            socket.connect(f"tcp://{host}:{port}")
            
            # Send health check request
            request = {"action": "health"}
            socket.send_json(request)
            
            # Wait for response
            response = socket.recv_json()
            
            # Check response
            if "status" in response and response["status"] == "ok":
                logger.debug(f"Agent {agent_name} health check passed")
                socket.close()
                context.term()
                return True
            else:
                logger.warning(f"Agent {agent_name} returned unexpected health status: {response}")
                socket.close()
                context.term()
                return False
                
        except zmq.error.Again:
            logger.warning(f"Agent {agent_name} health check failed: Timeout")
            return False
        except ConnectionRefusedError:
            logger.warning(f"Agent {agent_name} health check failed: Connection refused")
            return False
        except Exception as e:
            logger.warning(f"Agent {agent_name} health check failed: {str(e)}")
            return False
        finally:
            # Ensure we clean up the socket resources even if an exception occurs
            try:
                socket.close()
                context.term()
            except:
                pass
            return False  # Ensure we always return a boolean

    def _record_health_event(self, agent_name: str, event_type: str, details: Dict[str, Any]) -> None:
        """Record a health event in the database.
        
        Args:
            agent_name: Name of the agent
            event_type: Type of event
            details: Event details
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO health_events (agent_name, event_type, details) VALUES (?, ?, ?)",
                (agent_name, event_type, json.dumps(details))
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error recording health event: {e}")
    
    def _attempt_recovery(self, agent_name: str, agent_config: Dict[str, Any]) -> None:
        """Attempt to recover an unhealthy agent.
        
        Args:
            agent_name: Name of the agent
            agent_config: Agent configuration
        """
        # Check last restart time to avoid restart loops
        last_restart = self.agent_last_restart.get(agent_name, 0)
        now = time.time()
        
        if now - last_restart < RESTART_COOLDOWN:
            logger.warning(f"Skipping recovery for {agent_name} - in cooldown period")
            return
            
        try:
            # Determine recovery strategy
            strategy = agent_config.get("recovery_strategy", "tier1")
            recovery_actions = self.recovery_strategies.get(strategy, {}).get("actions", ["restart_agent"])
            
            logger.info(f"Attempting recovery for {agent_name} using strategy {strategy}")
            
            # Execute recovery actions
            for action in recovery_actions:
                if action == "restart_agent":
                    self.restart_agent(agent_name)
                elif action == "clear_agent_state":
                    # Clear agent state logic here
                    pass
                elif action == "restart_dependencies":
                    # Restart dependencies logic here
                    for dep in agent_config.get("dependencies", []):
                        self.restart_agent(dep)
                elif action == "restart_all_agents":
                    # Restart all agents logic here
                    for name in self.agent_configs.keys():
                        self.restart_agent(name)
                        
            # Update last restart time
            self.agent_last_restart[agent_name] = now
            
            # Record recovery action
            self._record_health_event(agent_name, "recovery_attempted", 
                                     {"strategy": strategy, "actions": recovery_actions})
                                     
        except Exception as e:
            logger.error(f"Error attempting recovery for {agent_name}: {e}")
            self._record_health_event(agent_name, "recovery_failed", {"error": str(e)})

    def _record_system_metrics(self, metrics: Dict[str, Any]) -> None:
        """Record system metrics in the database.
        
        Args:
            metrics: System metrics
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO system_metrics 
                   (timestamp, cpu_usage, memory_usage, disk_usage, process_count) 
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    datetime.now().isoformat(),
                    metrics.get("cpu_usage", 0),
                    metrics.get("memory_usage", 0),
                    metrics.get("disk_usage", 0),
                    metrics.get("process_count", 0)
                )
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error recording system metrics: {e}")
    
    def _predict_failures(self) -> None:
        """Predict potential agent failures using the machine learning model."""
        if not self.model:
            return
            
        try:
            # Get latest metrics for each agent
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT agent_name, cpu_usage, memory_usage, response_time, error_rate
                FROM health_metrics
                WHERE id IN (
                    SELECT MAX(id) FROM health_metrics GROUP BY agent_name
                )
            """)
            
            latest_metrics = {}
            for row in cursor.fetchall():
                agent_name, cpu_usage, memory_usage, response_time, error_rate = row
                latest_metrics[agent_name] = {
                    "cpu_usage": cpu_usage,
                    "memory_usage": memory_usage,
                    "response_time": response_time,
                    "error_rate": error_rate
                }
                
            # Predict failures for each agent
            for agent_name, metrics in latest_metrics.items():
                # Skip if not enough data
                if None in metrics.values():
                    continue
                    
                # Prepare input for model
                X = [
                    metrics["cpu_usage"],
                    metrics["memory_usage"],
                    metrics["response_time"],
                    metrics["error_rate"]
                ]
                
                # Make prediction
                try:
                    failure_probability = self.model.predict_proba([X])[0][1]
                    
                    # Log high probability failures
                    if failure_probability > 0.7:
                        logger.warning(f"High failure probability for {agent_name}: {failure_probability:.2f}")
                        
                        # Record prediction
                        self._record_health_event(agent_name, "failure_predicted", 
                                                {"probability": failure_probability})
                                                
                        # Send alert to self-healing agent
                        self._send_alert(agent_name, "failure_predicted", failure_probability)
                except Exception as e:
                    logger.error(f"Error making prediction for {agent_name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error predicting failures: {e}")

    def _send_alert(self, agent_name: str, alert_type: str, severity: float) -> None:
        """Send an alert to the self-healing agent.
        
        Args:
            agent_name: Name of the agent
            alert_type: Type of alert
            severity: Alert severity (0.0 to 1.0)
        """
        try:
            # Prepare alert message
            alert = {
                "action": "alert",
                "agent_name": agent_name,
                "alert_type": alert_type,
                "severity": severity,
                "timestamp": datetime.now().isoformat()
            }
            
            # Send alert to self-healing agent
            self.self_healing.send_json(alert)
            
            # Wait for response with timeout
            try:
                response = self.self_healing.recv_json()
                logger.info(f"Self-healing agent acknowledged alert: {response.get('status', 'unknown')}")
            except zmq.error.Again:
                logger.warning("Self-healing agent did not respond to alert")
                
        except Exception as e:
            logger.error(f"Error sending alert: {e}")

    def _run_health_check_loop(self) -> None:
        """Run the health check loop."""
        try:
            logger.info("Starting health check loop")
            while self.running:
                try:
                    for agent_name, agent_config in self.agent_configs.items():
                        # Skip disabled agents
                        if not agent_config.get("enabled", True):
                            continue
                            
                        # Check if agent is running on this machine
                        if agent_config.get("machine") != self.machine_id and self.machine_id is not None:
                            continue
                            
                        # Get agent host and port
                        host = agent_config.get("host", "localhost")
                        port = agent_config.get("health_port", agent_config.get("port", 0))
                        
                        if port > 0:
                            # Check agent health
                            is_healthy = self.check_agent_health(agent_name, host, port)
                            
                            # Update agent health status
                            self.agent_health[agent_name] = {
                                "healthy": is_healthy,
                                "last_checked": datetime.now().isoformat(),
                                "host": host,
                                "port": port
                            }
                            
                            # Log warning for unhealthy agents
                            if not is_healthy:
                                logger.warning(f"Agent {agent_name} health check failed: Resource temporarily unavailable")
                                
                                # Record failure in database
                                self._record_health_event(agent_name, "health_check_failed", {"error": "Resource temporarily unavailable"})
                                
                                # Attempt recovery if needed
                                if agent_config.get("auto_recover", False):
                                    self._attempt_recovery(agent_name, agent_config)
                        
                        # Small delay between checks to prevent overwhelming the system
                        time.sleep(2)
                        
                    # Update system metrics
                    system_metrics = self._get_system_metrics()
                    self._record_system_metrics(system_metrics)
                    
                    # Predict potential failures
                    self._predict_failures()
                    
                    # Check if optimization is needed
                    if self._needs_optimization(system_metrics):
                        self.optimize_system()
                        
                except KeyboardInterrupt:
                    logger.info("Keyboard interrupt received, shutting down")
                    self.running = False
                    break
                except Exception as e:
                    logger.error(f"Error in health check loop: {str(e)}")
                    logger.debug(traceback.format_exc())
                    time.sleep(5)  # Wait before continuing
                
                # Wait before next check cycle
                time.sleep(10)
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down")
            self.running = False
        finally:
            logger.info("Cleaning up resources")
            try:
                # Clean up resources
                for agent_name in list(self.agent_processes.keys()):
                    self.stop_agent(agent_name)
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
            logger.info("Cleanup complete")

# --- Orchestrator Logic Integration (from orchestrator.py) ---
from src.core.base_agent import BaseAgent
import signal
import psutil
from pathlib import Path

class OrchestratorAgent(BaseAgent):
    # (Insert orchestrator.py's OrchestratorAgent class and log_collector function here, refactored to avoid conflict with PredictiveHealthMonitor)
    pass 