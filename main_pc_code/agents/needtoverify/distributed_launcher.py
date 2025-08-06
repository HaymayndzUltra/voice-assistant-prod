from common.core.base_agent import BaseAgent
from common.utils.log_setup import configure_logging
"""
Distributed Agent Launcher
- Manages agent distribution across multiple machines
- Handles network communication and agent coordination
- Supports automatic discovery of available machines
- Provides monitoring and health checks for distributed agents
"""
import zmq
import json
import time
import logging
import sys
import os
import traceback
import subprocess
import socket
import threading
import argparse
from pathlib import Path
from typing import List, Optional

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from main_pc_code.config.system_config import config

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / str(PathManager.get_logs_dir() / "distributed_launcher.log")
log_file.parent.mkdir(exist_ok=True)

logger = configure_logging(__name__),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DistributedLauncher")

# Load distributed configuration
try:
    distributed_config_path = Path(__file__).parent.parent / "config" / "distributed_config.json"
    with open(distributed_config_path, 'r') as f:
        distributed_config = json.load(f)
    logger.info(f"Loaded distributed configuration from {distributed_config_path}")
except Exception as e:
    logger.error(f"Error loading distributed configuration: {str(e)}")
    distributed_config = {"machines": {}, "ports": {}, "discovery_service": {"enabled": False}}

class DistributedLauncher(BaseAgent):
    """Launcher for distributed voice assistant agents"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="DistributedLauncher")
        """Initialize the distributed launcher"""
        # Get machine information
        self.hostname = socket.gethostname()
        self.ip_address = socket.gethostbyname(self.hostname)
        logger.info(f"Running on {self.hostname} ({self.ip_address})")
        
        # Identify which machine this is in the config
        self.machine_id = self._identify_machine()
        if self.machine_id:
            logger.info(f"Identified as machine '{self.machine_id}' in configuration")
        else:
            logger.warning("This machine is not in the distributed configuration")
        
        # Initialize ZMQ for discovery service
        if distributed_config["discovery_service"]["enabled"]:
            self.context = zmq.Context()
            self.discovery_port = distributed_config["discovery_service"]["port"]
            
            if self.machine_id == "main_pc":
                # Main PC hosts the discovery service
                self.discovery_socket = self.context.socket(zmq.REP)
                self.discovery_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
                self.discovery_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
                self.discovery_socket.bind(f"tcp://*:{self.discovery_port}")
                logger.info(f"Discovery service bound to port {self.discovery_port}")
            else:
                # Other machines connect to the discovery service
                self.discovery_socket = self.context.socket(zmq.REQ)
                self.discovery_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
                self.discovery_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
                main_pc_ip = distributed_config["machines"]["main_pc"]["ip"]
                self.discovery_socket.connect(f"tcp://{main_pc_ip}:{self.discovery_port}")
                logger.info(f"Connected to discovery service at {main_pc_ip}:{self.discovery_port}")
        
        # Process handles for local agents
        self.processes = {}
        
        # Remote agent status
        self.remote_agents = {}
        
        # Running flag
        self.running = True
    
    def _identify_machine(self) -> Optional[str]:
        """Identify which machine this is in the configuration"""
        for machine_id, machine_info in distributed_config["machines"].items():
            if machine_info["ip"] == self.ip_address:
                return machine_id
        
        # If IP doesn't match, try hostname
        for machine_id, machine_info in distributed_config["machines"].items():
            if machine_id.lower() in self.hostname.lower():
                return machine_id
        
        return None
    
    def _get_agent_command(self, agent_name: str) -> List[str]:
        """Get the command to run an agent"""
        # Get the agent script path
        script_path = os.path.join(os.path.dirname(__file__), f"{agent_name}.py")
        
        # Check if the agent should run in server mode
        server_mode_agents = [
            "progressive_code_generator",
            "auto_fixer_agent",
            "self_healing_agent",
            "predictive_health_monitor",
            "enhanced_web_scraper"
        ]
        
        server_flag = "--server" if agent_name in server_mode_agents else ""
        
        # Build the command
        cmd = [sys.executable, script_path]
        if server_flag:
            cmd.append(server_flag)
        
        return cmd
    
    def start_local_agent(self, agent_name: str) -> bool:
        """Start an agent on this machine"""
        if agent_name in self.processes and self.processes[agent_name] and self.processes[agent_name].poll() is None:
            logger.warning(f"Agent {agent_name} is already running")
            return True
        
        cmd = self._get_agent_command(agent_name)
        
        try:
            logger.info(f"Starting agent: {agent_name} ({' '.join(cmd)})")
            
            # Create log file
            log_dir = Path(config.get('system.logs_dir', 'logs'))
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / fstr(PathManager.get_logs_dir() / "{agent_name}.log")
            
            # Start process with log redirection
            with open(log_file, "a") as log:
                process = subprocess.Popen(
                    cmd,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True
                )
            
            # Wait a bit to ensure the agent starts
            time.sleep(1)
            
            # Check if the process is still running
            if process.poll() is not None:
                logger.error(f"Agent {agent_name} failed to start (exit code: {process.returncode})")
                return False
            
            self.processes[agent_name] = process
            logger.info(f"Agent {agent_name} started (PID: {process.pid})")
            return True
        
        except Exception as e:
            logger.error(f"Error starting agent {agent_name}: {str(e)}")
            return False
    
    def stop_local_agent(self, agent_name: str) -> bool:
        """Stop an agent on this machine"""
        if agent_name not in self.processes or self.processes[agent_name] is None:
            logger.warning(f"Agent {agent_name} is not running")
            return False
        
        process = self.processes[agent_name]
        
        try:
            # Try to terminate gracefully
            process.terminate()
            
            # Wait for up to 5 seconds
            for _ in range(5):
                if process.poll() is not None:
                    break
                time.sleep(1)
            
            # If still running, kill forcefully
            if process.poll() is None:
                process.kill()
                process.wait()
            
            logger.info(f"Agent {agent_name} stopped")
            self.processes[agent_name] = None
            return True
        
        except Exception as e:
            logger.error(f"Error stopping agent {agent_name}: {str(e)}")
            return False
    
    def start_all_local_agents(self) -> bool:
        """Start all agents assigned to this machine"""
        if not self.machine_id:
            logger.error("This machine is not in the distributed configuration")
            return False
        
        machine_info = distributed_config["machines"][self.machine_id]
        agents = machine_info["agents"]
        
        success = True
        for agent in agents:
            if not self.start_local_agent(agent):
                logger.error(f"Failed to start agent: {agent}")
                success = False
            
            # Wait a bit between agent startups
            time.sleep(2)
        
        return success
    
    def stop_all_local_agents(self) -> bool:
        """Stop all agents running on this machine"""
        success = True
        for agent in list(self.processes.keys()):
            if not self.stop_local_agent(agent):
                success = False
        
        return success
    
    def monitor_local_agents(self) -> None:
        """Monitor running agents and restart if needed"""
        while self.running:
            try:
                for agent, process in list(self.processes.items()):
                    if process and process.poll() is not None:
                        logger.warning(f"Agent {agent} has stopped unexpectedly (exit code: {process.returncode})")
                        
                        # Restart the agent
                        if self.start_local_agent(agent):
                            logger.info(f"Agent {agent} restarted")
                        else:
                            logger.error(f"Failed to restart agent {agent}")
                
                time.sleep(5)
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in monitor thread: {str(e)}")
                time.sleep(30)
    
    def run_discovery_service(self) -> None:
        """Run the discovery service for agent coordination"""
        if not distributed_config["discovery_service"]["enabled"]:
            return
        
        if self.machine_id != "main_pc":
            logger.warning("Discovery service should only run on the main PC")
            return
        
        logger.info("Starting discovery service...")
        
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
                        self.remote_agents[(machine_id, agent_name)] = {
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
                        if (machine_id, agent_name) in self.remote_agents:
                            del self.remote_agents[(machine_id, agent_name)]
                        
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
                        if (machine_id, agent_name) in self.remote_agents:
                            self.remote_agents[(machine_id, agent_name)]["last_update"] = time.time()
                        else:
                            self.remote_agents[(machine_id, agent_name)] = {
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
                        "agents": self.remote_agents
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
    
    def run(self) -> None:
        """Run the distributed launcher"""
        try:
            # Start all local agents
            if self.machine_id:
                logger.info(f"Starting all agents for machine '{self.machine_id}'...")
                self.start_all_local_agents()
            
            # Start monitor thread
            monitor_thread = threading.Thread(target=self.monitor_local_agents)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # Start discovery service if this is the main PC
            if self.machine_id == "main_pc" and distributed_config["discovery_service"]["enabled"]:
                discovery_thread = threading.Thread(target=self.run_discovery_service)
                discovery_thread.daemon = True
                discovery_thread.start()
            
            # Wait for Ctrl+C
            logger.info("Distributed launcher running, press Ctrl+C to stop")
            while self.running:
                time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            traceback.print_exc()
        finally:
            self.cleanup()
    
    def cleanup(self) -> None:
        """Clean up resources"""
        self.running = False
        
        # Stop all local agents
        logger.info("Stopping all local agents...")
        self.stop_all_local_agents()
        
        # Close ZMQ sockets
        if hasattr(self, 'discovery_socket'):
            self.discovery_socket.close()
        
        if hasattr(self, 'context'):
            self.context.term()
        
        logger.info("Distributed launcher stopped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Distributed Agent Launcher: Manages agent distribution across multiple machines.")
    parser.add_argument('--agent', help='Start a specific agent')
    parser.add_argument('--stop', action='store_true', help='Stop agents')
    parser.add_argument('--list', action='store_true', help='List available agents for this machine')
    args = parser.parse_args()
    
    launcher = DistributedLauncher()
    
    if args.list:
        if launcher.machine_id:
            machine_info = distributed_config["machines"][launcher.machine_id]
            print(f"Available agents for {launcher.machine_id} ({machine_info['description']}):")
            for agent in machine_info["agents"]:
                print(f"  {agent}")
        else:
            print("This machine is not in the distributed configuration")
        sys.exit(0)
    
    if args.agent:
        if args.stop:
            launcher.stop_local_agent(args.agent)
        else:
            launcher.start_local_agent(args.agent)
        sys.exit(0)
    
    if args.stop:
        launcher.stop_all_local_agents()
        sys.exit(0)
    
    # Run the full launcher
    launcher.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise