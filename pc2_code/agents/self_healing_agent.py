"""
from typing import Dict, Any, Optional
import yaml
Self-Healing Agent
---------------------
Monitors and maintains the health of all agents in the distributed voice assistant system.

Responsibilities:
- Monitors the health of all agents in the system via heartbeat mechanism
- Detects failures through missed heartbeats and resource monitoring
- Recovers agents by restarting them when necessary
- Analyzes error patterns to predict and prevent future failures
- Optimizes system performance by tracking resource usage
- Provides self-healing capabilities with minimal human intervention
- Manages agent dependencies and system state snapshots
- Handles proactive recommendations from the RCA Agent

Heartbeat Protocol:
- Each agent sends periodic heartbeat signals (default: every 10 seconds)
- Self-Healing Agent maintains a registry of all agents with their expected heartbeat intervals
- When an agent misses multiple consecutive heartbeats (default: 3), it's considered offline
- Recovery procedure is initiated for critical agents that are offline

Restart Mechanism:
1. When agent failure is detected, Self-Healing Agent attempts recovery:
   a. First tries a soft restart via process signal
   b. If soft restart fails, attempts a full process termination and respawn
   c. If multiple restart attempts fail, enters degraded mode and alerts system
2. Implements exponential backoff for repeated failures
3. Tracks success rates to identify chronically problematic agents
4. Respects agent dependencies during recovery

System Snapshots:
1. Creates comprehensive system state snapshots including:
   - Agent configurations and states
   - System resource metrics
   - Error and recovery history
   - Critical system files
2. Supports snapshot restoration for system recovery
3. Maintains snapshot history with timestamps

This agent uses ZMQ REP socket on port 7125 to receive commands and monitoring requests,
and a PUB socket on port 7126 to broadcast health status updates to interested components.
"""
import zmq
import json
import time
import logging
import sys
import os
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
import threading
import datetime
from collections import defaultdict, deque
import subprocess
import signal
import shutil
import uuid

# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import config parser utility with fallback
try:
    from agents.utils.config_parser import parse_agent_args
    # Config is loaded at the module level
except ImportError:
    class DummyArgs(BaseAgent):
        host = 'localhost'
    _agent_args = DummyArgs()

# Configure logging
log_file_path = 'logs/self_healing_agent.log'
log_directory = os.path.dirname(log_file_path)
os.makedirs(log_directory, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SelfHealingAgent")

# ZMQ ports
SELF_HEALING_PORT = 7125
SELF_HEALING_PUB_PORT = 7126
SELF_HEALING_HEALTH_REP_PORT = 7129

# Agent status constants
AGENT_STATUS_UNKNOWN = "unknown"
AGENT_STATUS_ONLINE = "online"
AGENT_STATUS_OFFLINE = "offline"
AGENT_STATUS_DEGRADED = "degraded"
AGENT_STATUS_RECOVERING = "recovering"

# Error severity levels
ERROR_SEVERITY_INFO = "info"
ERROR_SEVERITY_WARNING = "warning"
ERROR_SEVERITY_ERROR = "error"
ERROR_SEVERITY_CRITICAL = "critical"

# Recovery action types
RECOVERY_ACTION_RESTART = "restart"
RECOVERY_ACTION_RESET = "reset"
RECOVERY_ACTION_CLEAR_MEMORY = "clear_memory"
RECOVERY_ACTION_OPTIMIZE = "optimize"
RECOVERY_ACTION_NOTIFY = "notify"

def generate_unique_id():
    """Generate a unique ID"""
    return str(uuid.uuid4())



        def connect_to_main_pc_service(self, service_name: str):

            """

            Connect to a service on the main PC using the network configuration.

            

            Args:

                service_name: Name of the service in the network config ports section

            

            Returns:

                ZMQ socket connected to the service

            """

            if not hasattr(self, 'main_pc_connections'):

                self.main_pc_connections = {}

                

            if service_name not in network_config.get("ports", {}):

                logger.error(f"Service {service_name} not found in network configuration")

                return None

                

            port = network_config["ports"][service_name]

            

            # Create a new socket for this connection

            socket = self.context.socket(zmq.REQ)

            

            # Connect to the service

            socket.connect(f"tcp://{MAIN_PC_IP}:{port}")

            

            # Store the connection

            self.main_pc_connections[service_name] = socket

            

            logger.info(f"Connected to {service_name} on MainPC at {MAIN_PC_IP}:{port}")

            return socket
class AgentStatus:
    """Class representing the status of an agent in the system"""
    def __init__(self, agent_id, agent_name, status=AGENT_STATUS_UNKNOWN):
         super().__init__(name="DummyArgs", port=None)

         # Record start time for uptime calculation

         self.start_time = time.time()

         

         # Initialize agent state

         self.running = True

         self.request_count = 0

         

         # Set up connection to main PC if needed

         self.main_pc_connections = {}

         

         logger.info(f"{self.__class__.__name__} initialized on PC2 (IP: {PC2_IP}) port {self.port}")

self.agent_id = agent_id
        self.agent_name = agent_name
        self.status = status
        self.last_heartbeat = time.time()
        self.missed_heartbeats = 0
        self.restart_attempts = 0
        self.consecutive_failures = 0
        self.health_metrics = {}
        self.last_error = None
        self.recovery_time = None
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": self.status,
            "last_heartbeat": self.last_heartbeat,
            "missed_heartbeats": self.missed_heartbeats,
            "restart_attempts": self.restart_attempts,
            "consecutive_failures": self.consecutive_failures,
            "health_metrics": self.health_metrics,
            "last_error": self.last_error,
            "recovery_time": self.recovery_time
        }

class SelfHealingAgent:
    """Main self-healing agent class"""
    def __init__(self, port=None):
        try:
            self.main_port = port if port else SELF_HEALING_PORT
            self.pub_port = SELF_HEALING_PUB_PORT
            self.health_rep_port = SELF_HEALING_HEALTH_REP_PORT
            
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://*:{self.main_port}")
            
            self.pub_socket = self.context.socket(zmq.PUB)
            self.pub_socket.bind(f"tcp://*:{self.pub_port}")
            logger.info(f"SelfHealingAgent PUB socket bound to port {self.pub_port}")

            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.bind(f"tcp://*:{self.health_rep_port}")
            logger.info(f"SelfHealingAgent health REP socket bound to port {self.health_rep_port}")

            # Agent registry and dependencies
            self.agent_registry: Dict[str, AgentStatus] = {}  # agent_id -> AgentStatus
            self.agent_dependencies: Dict[str, List[str]] = {}  # agent_id -> [dependency_ids]
            self.critical_agents: Set[str] = set()  # Set of critical agent IDs
            
            # Snapshot management
            self.snapshot_dir = Path('backups')
            self.snapshot_dir.mkdir(exist_ok=True)
            
            # Monitoring threads
            self.monitor_thread = threading.Thread(target=self.monitor_agents_loop, daemon=True)
            self.resource_thread = threading.Thread(target=self.resource_monitor_loop, daemon=True)
            self.log_scan_thread = threading.Thread(target=self.log_scan_loop, daemon=True)
            self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
            self.running = True
            
            logger.info(f"SelfHealingAgent initialized on port {self.main_port}")
        except Exception as e:
            logger.error(f"Failed to initialize SelfHealingAgent: {str(e)}")
            raise

    def _health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            'status': 'success',
            'agent': 'SelfHealingAgent',
            'timestamp': datetime.datetime.now().isoformat(),
            'monitor_thread_alive': self.monitor_thread.is_alive() if hasattr(self, 'monitor_thread') else False,
            'resource_thread_alive': self.resource_thread.is_alive() if hasattr(self, 'resource_thread') else False,
            'registered_agents': len(self.agent_registry),
            'main_port': self.main_port,
            'pub_port': self.pub_port,
            'health_rep_port': self.health_rep_port
        }

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action', '')
        
        if action == 'health_check':
            return self._health_check()
        elif action == 'register_agent':
            return self._register_agent(request)
        elif action == 'heartbeat':
            return self._handle_heartbeat(request)
        elif action == 'proactive_recommendation':
            return self._handle_proactive_recommendation(request)
        elif action == 'get_agent_status':
            return self._get_agent_status(request)
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}

    def _register_agent(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new agent for monitoring."""
        try:
            agent_id = request.get('agent_id')
            agent_name = request.get('agent_name', agent_id)
            
            if not agent_id:
                return {'status': 'error', 'message': 'Missing agent_id'}
            
            if agent_id in self.agent_registry:
                return {'status': 'success', 'message': 'Agent already registered'}
            
            agent_status = AgentStatus(agent_id, agent_name)
            self.agent_registry[agent_id] = agent_status
            
            logger.info(f"Registered agent: {agent_id} ({agent_name})")
            return {'status': 'success', 'message': 'Agent registered successfully'}
        except Exception as e:
            logger.error(f"Error registering agent: {e}")
            return {'status': 'error', 'message': str(e)}

    def _handle_heartbeat(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent heartbeat."""
        try:
            agent_id = request.get('agent_id')
            
            if not agent_id:
                return {'status': 'error', 'message': 'Missing agent_id'}
            
            if agent_id not in self.agent_registry:
                return {'status': 'error', 'message': 'Agent not registered'}
            
            agent_status = self.agent_registry[agent_id]
            agent_status.last_heartbeat = time.time()
            agent_status.missed_heartbeats = 0
            agent_status.status = AGENT_STATUS_ONLINE
            
            return {'status': 'success', 'message': 'Heartbeat received'}
        except Exception as e:
            logger.error(f"Error handling heartbeat: {e}")
            return {'status': 'error', 'message': str(e)}

    def _handle_proactive_recommendation(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Handle proactive recommendation from RCA 
from main_pc_code.src.core.base_agent import BaseAgentAgent.
from main_pc_code.utils.config_loader import load_config

# Load configuration at the module level
config = load_config()"""
        try:
            target_agent = recommendation.get('target_agent')
            recommendation_type = recommendation.get('recommendation')
            reason = recommendation.get('reason', '')
            severity = recommendation.get('severity', 'medium')
            
            logger.info(f"Received proactive recommendation for {target_agent}: {recommendation_type} - {reason}")
            
            # For now, just log the recommendation
            # In a full implementation, this would trigger recovery actions
            
            return {
                'status': 'success',
                'message': 'Recommendation received and logged',
                'action_taken': 'logged'
            }
        except Exception as e:
            logger.error(f"Error handling proactive recommendation: {e}")
            return {'status': 'error', 'message': str(e)}

    def _get_agent_status(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Get status of all agents or a specific agent."""
        try:
            agent_id = request.get('agent_id')
            
            if agent_id:
                if agent_id not in self.agent_registry:
                    return {'status': 'error', 'message': 'Agent not found'}
                return {
                    'status': 'success',
                    'agent_status': self.agent_registry[agent_id].to_dict()
                }
            else:
                return {
                    'status': 'success',
                    'agents': {aid: status.to_dict() for aid, status in self.agent_registry.items()}
                }
        except Exception as e:
            logger.error(f"Error getting agent status: {e}")
            return {'status': 'error', 'message': str(e)}

    def run(self):
        """Start monitoring and handle requests"""
        logger.info(f"SelfHealingAgent starting on port {self.main_port}")
        
        # Start monitoring threads
        self.monitor_thread.start()
        self.resource_thread.start()
        self.log_scan_thread.start()
        self.health_thread.start()
        
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

    def monitor_agents_loop(self):
        """Background thread for monitoring agent health"""
        logger.info("Starting agent monitoring loop")
        while self.running:
            try:
                for agent_id, agent_status in self.agent_registry.items():
                    self.check_agent_heartbeat(agent_status)
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Error in agent monitoring loop: {e}")
                time.sleep(10)

    def check_agent_heartbeat(self, agent_status: AgentStatus):
        """Check if an agent has missed heartbeats"""
        current_time = time.time()
        time_since_heartbeat = current_time - agent_status.last_heartbeat
        
        if time_since_heartbeat > 30:  # 30 seconds threshold
            agent_status.missed_heartbeats += 1
            if agent_status.missed_heartbeats >= 3:
                agent_status.status = AGENT_STATUS_OFFLINE
                logger.warning(f"Agent {agent_status.agent_name} is offline (missed {agent_status.missed_heartbeats} heartbeats)")
                # In a full implementation, this would trigger recovery

    def resource_monitor_loop(self):
        """Background thread for monitoring system resources"""
        logger.info("Starting resource monitoring loop")
        while self.running:
            try:
                # Monitor system resources
                # In a full implementation, this would check CPU, memory, disk usage
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in resource monitoring loop: {e}")
                time.sleep(30)

    def log_scan_loop(self):
        """Background thread for scanning logs for errors"""
        logger.info("Starting log scanning loop")
        while self.running:
            try:
                # Scan logs for errors
                # In a full implementation, this would scan log files for error patterns
                time.sleep(60)  # Check every 60 seconds
            except Exception as e:
                logger.error(f"Error in log scanning loop: {e}")
                time.sleep(60)

    def _health_check_loop(self):
        logger.info("Starting health check loop (health port REP)")
        while self.running:
            try:
                if self.health_socket.poll(1000) == 0:
                    continue
                message = self.health_socket.recv_json()
                if message.get("action") == "health_check":
                    response = self._health_check()
                else:
                    response = {"status": "error", "error": "Invalid health check request"}
                self.health_socket.send_json(response)
            except zmq.error.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    continue
                logger.error(f"ZMQ error in health check loop: {e}")
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")

    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info("Cleaning up SelfHealingAgent resources...")
        self.running = False
        
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=5)
        if hasattr(self, 'resource_thread'):
            self.resource_thread.join(timeout=5)
        if hasattr(self, 'log_scan_thread'):
            self.log_scan_thread.join(timeout=5)
        if hasattr(self, 'health_thread'):
            self.health_thread.join(timeout=5)
        
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'pub_socket'):
            self.pub_socket.close()
        if hasattr(self, 'health_socket'):
            self.health_socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        
        logger.info("Cleanup complete")



def _get_health_status(self) -> dict:


    """Return health status information."""


    base_status = super()._get_health_status()


    # Add any additional health information specific to DummyArgs


    base_status.update({


        'service': 'DummyArgs',


        'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,


        'additional_info': {}


    })


    return base_status

    def stop(self):
        """Stop the agent gracefully."""
        self.running = False





if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = DummyArgs()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'} on PC2...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'} on PC2: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name} on PC2...")
            agent.cleanup()

# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "network_config.yaml")
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": "192.168.100.16",
            "pc2_ip": "192.168.100.17",
            "bind_address": "0.0.0.0",
            "secure_zmq": False
        }

# Load both configurations
network_config = load_network_config()

# Get machine IPs from config
MAIN_PC_IP = network_config.get("main_pc_ip", "192.168.100.16")
PC2_IP = network_config.get("pc2_ip", "192.168.100.17")
BIND_ADDRESS = network_config.get("bind_address", "0.0.0.0")
print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()
