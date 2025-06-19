from src.core.base_agent import BaseAgent
"""
Orchestrator Agent for AI Assistant System

This agent monitors the health of all other agents, provides centralized logging,
and automatically restarts agents that crash or become unresponsive.

Usage:
    python orchestrator.py

Author: Cascade AI
Date: 2025-05-16
"""

import zmq
import json
import logging
import time
import threading
import subprocess
import os
import sys
import signal
import psutil
import socket
import argparse
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Ensure virtual environment is active
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print("WARNING: Virtual environment is not activated. Please activate your venv before running this script.")
    print("Activate with: .\\venv\\Scripts\\activate (Windows) or source venv/bin/activate (Unix/Mac)")
    # Continue execution but with warning

# Configuration
LOG_PATH = "logs/orchestrator.log"
AGENT_LOG_PATH = "logs/agents.log"
ZMQ_HEALTH_PORT = 5599
HEALTH_CHECK_INTERVAL = 10  # seconds
RESTART_COOLDOWN = 30  # seconds between restart attempts for the same agent

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# Agent-specific logger
agent_logger = logging.getLogger("AgentLogger")
agent_logger.setLevel(logging.INFO)
agent_handler = logging.FileHandler(AGENT_LOG_PATH, encoding="utf-8")
agent_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
agent_logger.addHandler(agent_handler)
agent_logger.addHandler(logging.StreamHandler())

# Centralized log collector (ZMQ)
ZMQ_LOG_PORT = 5600

def log_collector():
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.bind(f"tcp://127.0.0.1:{ZMQ_LOG_PORT}")
    socket.setsockopt_string(zmq.SUBSCRIBE, "")
    agent_logger.info("[Orchestrator] Central log collector started on port %d", ZMQ_LOG_PORT)
    while True:
        try:
            msg = socket.recv_string()
            try:
                log_data = json.loads(msg)
                agent = log_data.get("agent", "unknown")
                level = log_data.get("level", "INFO").upper()
                message = log_data.get("message", "")
                timestamp = log_data.get("timestamp", None)
                log_line = f"[{agent}] {message}"
                if hasattr(logging, level):
                    agent_logger.log(getattr(logging, level), log_line)
                else:
                    agent_logger.info(log_line)
            except Exception as e:
                agent_logger.error(f"[Orchestrator] Failed to parse log message: {e} | Raw: {msg}")
        except Exception as e:
            agent_logger.error(f"[Orchestrator] Log collector error: {e}")

# Start log collector in background
log_thread = threading.Thread(target=log_collector, daemon=True)
log_thread.start()

# Load distributed configuration
try:
    distributed_config_path = Path(__file__).parent.parent / "config" / "distributed_config.json"
    with open(distributed_config_path, 'r') as f:
        distributed_config = json.load(f)
    logging.info(f"Loaded distributed configuration from {distributed_config_path}")
except Exception as e:
    logging.error(f"Error loading distributed configuration: {str(e)}")
    distributed_config = {"machines": {}, "ports": {}, "discovery_service": {"enabled": False}}

class OrchestratorAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="Orchestrator")
        # Get machine information
        self.hostname = socket.gethostname()
        self.ip_address = socket.gethostbyname(self.hostname)
        logging.info(f"Running on {self.hostname} ({self.ip_address})")
        
        # Identify which machine this is in the distributed config
        self.machine_id = self._identify_machine()
        if self.machine_id:
            logging.info(f"Identified as machine '{self.machine_id}' in distributed configuration")
        else:
            logging.warning("This machine is not in the distributed configuration")
        
        # Initialize ZMQ
        self.context = zmq.Context()
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.bind(f"tcp://127.0.0.1:{ZMQ_HEALTH_PORT}")
        
        # Initialize discovery service if enabled
        self.discovery_socket = None
        if distributed_config["discovery_service"]["enabled"]:
            self.discovery_port = distributed_config["discovery_service"]["port"]
            
            if self.machine_id == "main_pc":
                # Main PC hosts the discovery service
                self.discovery_socket = self.context.socket(zmq.REP)
                self.discovery_socket.bind(f"tcp://*:{self.discovery_port}")
                logging.info(f"Discovery service bound to port {self.discovery_port}")
            elif self.machine_id:
                # Other machines connect to the discovery service
                self.discovery_socket = self.context.socket(zmq.REQ)
                main_pc_ip = distributed_config["machines"]["main_pc"]["ip"]
                self.discovery_socket.connect(f"tcp://{main_pc_ip}:{self.discovery_port}")
                logging.info(f"Connected to discovery service at {main_pc_ip}:{self.discovery_port}")
        
        self.running = True
        self.agents = {}
        self.agent_processes = {}
        self.agent_last_restart = {}
        
        # Default agent configurations
        self.agent_configs = {
            "listener": {
                "script": "agents/listener.py",
                "args": [],
                "critical": True,
                "zmq_port": 5555
            },
            "interpreter": {
                "script": "agents/interpreter.py",
                "args": [],
                "critical": True,
                "zmq_port": 5556
            },
            "responder": {
                "script": "agents/responder.py",
                "args": [],
                "critical": True,
                "zmq_port": 5557
            },
            "executor": {
                "script": "agents/executor.py",
                "args": [],
                "critical": True,
                "zmq_port": 5587
            },
            "face_recognition": {
                "script": "agents/face_recognition_agent.py",
                "args": [],
                "critical": True,
                "zmq_port": 5556
            },
            "memory": {
                "script": "agents/memory.py",
                "args": [],
                "critical": True,
                "zmq_port": 5590
            },
            "translator": {
                "script": "agents/translator_agent.py",
                "args": [],
                "critical": True,
                "zmq_port": 8044
            },
            "tts": {
                "script": "agents/tts_agent.py",
                "args": [],
                "critical": False,
                "zmq_port": 5559
            },
            "dashboard": {
                "script": "agents/dashboard.py",
                "args": [],
                "critical": False,
                "zmq_port": 8080
            }
        }
        
        # Update agent configurations from distributed config
        self._update_agent_configs_from_distributed()
        
        logging.info("[Orchestrator] Agent initialized")
        
    def _identify_machine(self):
        """Identify which machine this is in the distributed configuration"""
        # Check by IP address
        for machine_id, machine_info in distributed_config["machines"].items():
            if machine_info["ip"] == self.ip_address:
                return machine_id
        
        # If IP doesn't match, try hostname
        for machine_id, machine_info in distributed_config["machines"].items():
            if machine_id.lower() in self.hostname.lower():
                return machine_id
        
        return None

    def _update_agent_configs_from_distributed(self):
        """Update agent configurations based on distributed config"""
        if not self.machine_id:
            logging.warning("Cannot update agent configs: machine not identified in distributed config")
            return
        
        # Get agents assigned to this machine
        machine_info = distributed_config["machines"][self.machine_id]
        assigned_agents = machine_info.get("agents", [])
        
        # Filter agent_configs to only include agents for this machine
        filtered_configs = {}
        for agent_name in assigned_agents:
            if agent_name in self.agent_configs:
                filtered_configs[agent_name] = self.agent_configs[agent_name]
            else:
                # Create a new config for this agent
                script_path = f"agents/{agent_name}.py"
                port = distributed_config["ports"].get(agent_name, 0)
                filtered_configs[agent_name] = {
                    "script": script_path,
                    "args": [],
                    "critical": False,
                    "zmq_port": port
                }
                logging.info(f"Added new agent config for {agent_name} from distributed config")
        
        # Update agent_configs
        if filtered_configs:
            self.agent_configs = filtered_configs
            logging.info(f"Updated agent configurations for machine {self.machine_id}")
            logging.info(f"Managing agents: {', '.join(self.agent_configs.keys())}")
        else:
            logging.warning(f"No agents assigned to machine {self.machine_id} in distributed config")

    def start_agent(self, agent_name, max_retries=3):
        """
        Start a specific agent process. Retry up to max_retries times on failure with exponential backoff.
        Logs all errors with traceback. Recovery is robust to avoid orchestrator crash.
        """
        import traceback
        if agent_name not in self.agent_configs:
            logging.error(f"[Orchestrator] Unknown agent: {agent_name}")
            return False
        config = self.agent_configs[agent_name]
        # Check if already running
        if agent_name in self.agent_processes and self.agent_processes[agent_name].poll() is None:
            logging.warning(f"[Orchestrator] Agent {agent_name} is already running")
            return True
        # Check cooldown period
        now = time.time()
        if agent_name in self.agent_last_restart and (now - self.agent_last_restart[agent_name]) < RESTART_COOLDOWN:
            logging.warning(f"[Orchestrator] Agent {agent_name} in cooldown period, not restarting yet")
            return False
        attempt = 0
        while attempt < max_retries:
            try:
                python_executable = sys.executable  # Use same Python as orchestrator
                cmd = [python_executable, config["script"]] + config["args"]
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
                # Start threads to monitor stdout/stderr
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
                logging.info(f"[Orchestrator] Started agent: {agent_name} (attempt {attempt+1})")
                return True
            except Exception as e:
                logging.error(f"[Orchestrator] Failed to start agent {agent_name} on attempt {attempt+1}: {e}\n{traceback.format_exc()}")
                attempt += 1
                if attempt < max_retries:
                    backoff = 2 ** attempt
                    logging.info(f"[Orchestrator] Retrying agent {agent_name} in {backoff}s...")
                    time.sleep(backoff)
                else:
                    logging.error(f"[Orchestrator] Giving up on starting agent {agent_name} after {max_retries} attempts.")
                    return False
    
    def _monitor_output(self, pipe, agent_name, stream_name):
        """Monitor and log output from agent processes"""
        for line in iter(pipe.readline, ''):
            if line:
                agent_logger.info(f"[{agent_name}] [{stream_name}] {line.rstrip()}")
        
    def stop_agent(self, agent_name):
        """Stop a specific agent process"""
        if agent_name not in self.agent_processes:
            logging.warning(f"[Orchestrator] Agent {agent_name} is not running")
            return True
            
        process = self.agent_processes[agent_name]
        if process.poll() is not None:
            # Already terminated
            self.agent_processes.pop(agent_name)
            return True
            
        try:
            # Try graceful termination first
            if os.name == 'nt':
                # Windows
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                # Unix
                process.terminate()
                
            # Wait for termination
            for _ in range(5):  # 5 seconds timeout
                if process.poll() is not None:
                    logging.info(f"[Orchestrator] Agent {agent_name} stopped gracefully")
                    self.agent_processes.pop(agent_name)
                    return True
                time.sleep(1)
                
            # Force kill if still running
            process.kill()
            logging.warning(f"[Orchestrator] Agent {agent_name} force killed")
            self.agent_processes.pop(agent_name)
            return True
            
        except Exception as e:
            logging.error(f"[Orchestrator] Error stopping agent {agent_name}: {e}")
            return False
    
    def restart_agent(self, agent_name):
        """Restart a specific agent"""
        self.stop_agent(agent_name)
        time.sleep(1)  # Give it a moment to fully stop
        return self.start_agent(agent_name)
        
    def check_agent_health(self, agent_name):
        """Check if an agent is running and responsive"""
        # First check if process is running
        if agent_name not in self.agent_processes:
            return {"status": "not_running", "agent": agent_name}
            
        process = self.agent_processes[agent_name]
        if process.poll() is not None:
            return {"status": "crashed", "agent": agent_name, "exit_code": process.poll()}
            
        # Check process resource usage
        try:
            proc = psutil.Process(process.pid)
            memory_percent = proc.memory_percent()
            cpu_percent = proc.cpu_percent(interval=0.1)
            
            # Check if process is zombie or unresponsive
            if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
                return {"status": "zombie", "agent": agent_name}
                
            # Check for high resource usage
            if memory_percent > 90:  # Using more than 90% of memory
                return {"status": "high_memory", "agent": agent_name, "memory_percent": memory_percent}
                
            # TODO: Add ZMQ health check for agents that support it
            
            return {
                "status": "healthy", 
                "agent": agent_name,
                "memory_percent": memory_percent,
                "cpu_percent": cpu_percent
            }
            
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return {"status": "process_error", "agent": agent_name}
        except Exception as e:
            return {"status": "check_error", "agent": agent_name, "error": str(e)}
    
    def check_all_agents(self):
        """Check health of all agents and restart if necessary"""
        results = {}
        
        for agent_name in self.agent_configs:
            health = self.check_agent_health(agent_name)
            results[agent_name] = health
            
            # Auto-restart critical agents that aren't healthy
            config = self.agent_configs[agent_name]
            if config["critical"] and health["status"] not in ["healthy", "starting"]:
                logging.warning(f"[Orchestrator] Critical agent {agent_name} is {health['status']}, attempting restart")
                self.restart_agent(agent_name)
                
        return results
        
    def start_all_agents(self, parallel=True, stagger_seconds=2):
        """Start all configured agents in parallel (default) or sequentially (legacy). Logs per-agent and total startup time."""
        import threading
        start_times = {}
        threads = []
        results = {}
        def start_wrapper(agent_name):
            t0 = time.time()
            result = self.start_agent(agent_name)
            t1 = time.time()
            results[agent_name] = result
            start_times[agent_name] = t1 - t0
            logging.info(f"[Orchestrator] Startup time for {agent_name}: {start_times[agent_name]:.2f}s")
        t_total0 = time.time()
        if parallel:
            for agent_name in self.agent_configs:
                th = threading.Thread(target=start_wrapper, args=(agent_name,))
                th.start()
                threads.append(th)
            for th in threads:
                th.join()
        else:
            for agent_name in self.agent_configs:
                start_wrapper(agent_name)
                time.sleep(stagger_seconds)
        t_total1 = time.time()
        logging.info(f"[Orchestrator] All agents started. Total startup time: {t_total1-t_total0:.2f}s. Per-agent: {start_times}")
            
    def stop_all_agents(self):
        """Stop all running agents"""
        for agent_name in list(self.agent_processes.keys()):
            self.stop_agent(agent_name)
            
    def handle_health_requests(self):
        """Handle incoming health check requests via ZMQ"""
        while self.running:
            try:
                # Set timeout so we can check for self.running periodically
                if self.health_socket.poll(1000) == 0:
                    continue
                    
                msg = self.health_socket.recv_string()
                data = json.loads(msg)
                command = data.get("command", "")
                agent = data.get("agent", "")
                
                response = {"status": "error", "message": "Unknown command"}
                
                if command == "health":
                    if agent:
                        response = self.check_agent_health(agent)
                    else:
                        response = self.check_all_agents()
                elif command == "start":
                    if agent:
                        success = self.start_agent(agent)
                        response = {"status": "started" if success else "error", "agent": agent}
                    else:
                        self.start_all_agents()
                        response = {"status": "starting_all"}
                elif command == "stop":
                    if agent:
                        success = self.stop_agent(agent)
                        response = {"status": "stopped" if success else "error", "agent": agent}
                    else:
                        self.stop_all_agents()
                        response = {"status": "stopping_all"}
                elif command == "restart":
                    if agent:
                        success = self.restart_agent(agent)
                        response = {"status": "restarted" if success else "error", "agent": agent}
                    else:
                        self.stop_all_agents()
                        time.sleep(2)
                        self.start_all_agents()
                        response = {"status": "restarting_all"}
                elif command == "list":
                    response = {
                        "status": "ok",
                        "agents": list(self.agent_configs.keys()),
                        "running": [a for a in self.agent_processes if self.agent_processes[a].poll() is None]
                    }
                
                self.health_socket.send_string(json.dumps(response))
                
            except Exception as e:
                logging.error(f"[Orchestrator] Error handling health request: {e}")
                try:
                    self.health_socket.send_string(json.dumps({"status": "error", "message": str(e)}))
                except:
                    pass
    
    def run(self):
        """Main run loop for the orchestrator"""
        logging.info("[Orchestrator] Starting all agents")
        self.start_all_agents()
        
        # Start health check thread
        health_thread = threading.Thread(target=self.handle_health_requests, daemon=True)
        health_thread.start()
        
        # Start discovery service if this is the main PC
        discovery_thread = None
        if self.machine_id == "main_pc" and distributed_config["discovery_service"]["enabled"]:
            logging.info("[Orchestrator] Starting discovery service")
            discovery_thread = threading.Thread(target=self.handle_discovery_requests, daemon=True)
            discovery_thread.start()
        
        # Main monitoring loop
        try:
            while self.running:
                self.check_all_agents()
                time.sleep(HEALTH_CHECK_INTERVAL)
        except KeyboardInterrupt:
            logging.info("[Orchestrator] Received shutdown signal")
        finally:
            logging.info("[Orchestrator] Stopping all agents")
            self.running = False
            self.stop_all_agents()
            
            # Close ZMQ sockets
            self.health_socket.close()
            if self.discovery_socket:
                self.discovery_socket.close()
            self.context.term()
            
            logging.info("[Orchestrator] Shutdown complete")
    
    def get_system_stats(self):
        """Get overall system statistics"""
        stats = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "timestamp": datetime.now().isoformat()
        }
        return stats
        
    def handle_discovery_requests(self):
        """Handle discovery service requests for distributed deployment"""
        if not self.discovery_socket:
            logging.error("[Orchestrator] Discovery socket not initialized")
            return
            
        logging.info("[Orchestrator] Starting discovery service handler")
        
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
                logging.error(f"[Orchestrator] Error in discovery service: {str(e)}")
                traceback.print_exc()
                
                try:
                    response = {
                        "status": "error",
                        "error": f"Error in discovery service: {str(e)}"
                    }
                    self.discovery_socket.send_string(json.dumps(response))
                except:
                    pass


def main():
    """Main entry point"""
    print("=" * 50)
    print("AI Assistant Orchestrator")
    print("=" * 50)
    print("Starting orchestrator. Press Ctrl+C to stop all agents and exit.")
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Voice Assistant Orchestrator")
    parser.add_argument("--distributed", action="store_true", help="Enable distributed mode")
    parser.add_argument("--machine-id", type=str, help="Override machine ID detection")
    parser.add_argument("--config", type=str, help="Path to custom distributed config file")
    args = parser.parse_args()
    
    # Override distributed config if specified
    global distributed_config
    if args.config:
        try:
            config_path = Path(args.config)
            with open(config_path, 'r') as f:
                distributed_config = json.load(f)
            logging.info(f"Loaded custom distributed configuration from {config_path}")
        except Exception as e:
            logging.error(f"Error loading custom distributed configuration: {str(e)}")
    
    # Create and run orchestrator
    orchestrator = OrchestratorAgent()
    
    # Override machine ID if specified
    if args.machine_id:
        orchestrator.machine_id = args.machine_id
        logging.info(f"Overriding machine ID to: {args.machine_id}")
        
    orchestrator.run()


if __name__ == "__main__":
    main()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
