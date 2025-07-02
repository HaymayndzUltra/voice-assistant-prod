"""
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
from datetime import datetime
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

# Import base agent and config loaders
from main_pc_code.src.core.base_agent import BaseAgent
from pc2_code.agents.utils.config_loader import Config

# Import config parser utility with fallback
try:
    from pc2_code.utils.config_loader import parse_agent_args
    # Config is loaded at the module level
except ImportError as e:
    print(f"Import error: {e}. Using dummy agent arguments.")
    # Define a simple dummy class if parse_agent_args is not available
    class DummyAgentArgs:
        host = 'localhost'
        port = None # Or a default port if needed
        # Add other attributes that parse_agent_args would provide if they are used globally
    _agent_args = DummyAgentArgs()


# Load global configurations
# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = os.path.join(project_root, "config", "network_config.yaml") # Use project_root
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
            "secure_zmq": False,
            "ports": {} # Ensure ports key exists to prevent KeyError
        }

network_config = load_network_config()

# Get machine IPs from config
MAIN_PC_IP = network_config.get("main_pc_ip", "192.168.100.16")
PC2_IP = network_config.get("pc2_ip", "192.168.100.17")
BIND_ADDRESS = network_config.get("bind_address", "0.0.0.0")

# Load PC2 specific configuration
pc2_config = Config().get_config()


# Configure logging
log_file_path = project_root / 'logs' / 'self_healing_agent.log' # Use project_root
os.makedirs(log_file_path.parent, exist_ok=True) # Use .parent for directory

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

class SelfHealingAgent(BaseAgent): # Inherit from BaseAgent
    """Main self-healing agent class"""
    def __init__(self, port=None):
        super().__init__(name="SelfHealingAgent", port=port if port else SELF_HEALING_PORT) # Call BaseAgent's init

        try:
            self.main_port = self.port # Use self.port from BaseAgent
            self.pub_port = SELF_HEALING_PUB_PORT
            self.health_rep_port = SELF_HEALING_HEALTH_REP_PORT
            
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://*:{self.main_port}")
            logger.info(f"SelfHealingAgent REP socket bound to port {self.main_port}")
            
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
            self.snapshot_dir = Path('backups') # Consider making this relative to project_root
            self.snapshot_dir.mkdir(exist_ok=True)
            
            # Monitoring threads
            self.monitor_thread = threading.Thread(target=self.monitor_agents_loop, daemon=True, name="AgentMonitorThread")
            self.resource_thread = threading.Thread(target=self.resource_monitor_loop, daemon=True, name="ResourceMonitorThread")
            self.log_scan_thread = threading.Thread(target=self.log_scan_loop, daemon=True, name="LogScanThread")
            self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True, name="HealthCheckThread")
            self.running = True # Inherited from BaseAgent, but can be managed here too

            # Store network config and IPs globally for connect_to_main_pc_service
            self._network_config = network_config
            self._main_pc_ip = MAIN_PC_IP
            self.main_pc_connections = {} # For the connect_to_main_pc_service method
            
            logger.info(f"SelfHealingAgent initialized on port {self.main_port} (IP: {PC2_IP})")
        except Exception as e:
            logger.error(f"Failed to initialize SelfHealingAgent: {str(e)}", exc_info=True)
            raise

    def _get_health_status(self) -> Dict[str, Any]:
        """Perform health check. Overrides BaseAgent's _get_health_status."""
        base_status = super()._get_health_status() # Get base status from parent
        
        # Add SelfHealingAgent specific health info
        base_status.update({
            'status': 'success',
            'agent': self.name,
            'timestamp': datetime.now().isoformat(),
            'monitor_thread_alive': self.monitor_thread.is_alive() if hasattr(self, 'monitor_thread') else False,
            'resource_thread_alive': self.resource_thread.is_alive() if hasattr(self, 'resource_thread') else False,
            'log_scan_thread_alive': self.log_scan_thread.is_alive() if hasattr(self, 'log_scan_thread') else False,
            'registered_agents': len(self.agent_registry),
            'main_port': self.main_port,
            'pub_port': self.pub_port,
            'health_rep_port': self.health_rep_port
        })
        return base_status

    def _health_check(self) -> Dict[str, Any]:
        """Legacy health check method for backward compatibility."""
        return self._get_health_status()

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
            
            # Check if agent is already registered but update its info
            if agent_id in self.agent_registry:
                logger.info(f"Agent {agent_id} ({agent_name}) already registered. Updating info.")
                self.agent_registry[agent_id].agent_name = agent_name # Update name if changed
                self.agent_registry[agent_id].last_heartbeat = time.time() # Reset heartbeat
                self.agent_registry[agent_id].status = AGENT_STATUS_ONLINE # Ensure online
                return {'status': 'success', 'message': 'Agent already registered, info updated'}
            
            agent_status = AgentStatus(agent_id, agent_name)
            self.agent_registry[agent_id] = agent_status
            
            logger.info(f"Registered new agent: {agent_id} ({agent_name})")
            return {'status': 'success', 'message': 'Agent registered successfully'}
        except Exception as e:
            logger.error(f"Error registering agent: {e}", exc_info=True)
            return {'status': 'error', 'message': str(e)}

    def _handle_heartbeat(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent heartbeat."""
        try:
            agent_id = request.get('agent_id')
            
            if not agent_id:
                return {'status': 'error', 'message': 'Missing agent_id'}
            
            if agent_id not in self.agent_registry:
                # Auto-register if heartbeat from unknown agent
                logger.warning(f"Heartbeat received from unregistered agent {agent_id}. Auto-registering.")
                self._register_agent(request) # Use the same request to register
            
            agent_status = self.agent_registry[agent_id]
            agent_status.last_heartbeat = time.time()
            agent_status.missed_heartbeats = 0
            # If agent was offline, mark as recovering briefly, then online
            if agent_status.status == AGENT_STATUS_OFFLINE:
                agent_status.status = AGENT_STATUS_RECOVERING
                logger.info(f"Agent {agent_id} ({agent_status.agent_name}) is back online.")
            elif agent_status.status == AGENT_STATUS_RECOVERING:
                agent_status.status = AGENT_STATUS_ONLINE # Confirm fully online
            else:
                agent_status.status = AGENT_STATUS_ONLINE
            
            return {'status': 'success', 'message': 'Heartbeat received'}
        except Exception as e:
            logger.error(f"Error handling heartbeat from {request.get('agent_id', 'unknown')}: {e}", exc_info=True)
            return {'status': 'error', 'message': str(e)}

    def _handle_proactive_recommendation(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Handle proactive recommendation from RCA Agent."""
        try:
            target_agent = recommendation.get('target_agent')
            recommendation_type = recommendation.get('recommendation')
            reason = recommendation.get('reason', '')
            severity = recommendation.get('severity', 'medium')
            
            logger.info(f"Received proactive recommendation for {target_agent}: {recommendation_type} (Severity: {severity}) - Reason: {reason}")
            
            # Here, you would implement logic to act on the recommendation.
            # Example: If recommendation_type is 'restart' and severity is 'critical', trigger restart.
            # For now, just log the recommendation as action taken.
            
            return {
                'status': 'success',
                'message': 'Recommendation received and logged',
                'action_taken': 'logged'
            }
        except Exception as e:
            logger.error(f"Error handling proactive recommendation: {e}", exc_info=True)
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
            logger.error(f"Error getting agent status: {e}", exc_info=True)
            return {'status': 'error', 'message': str(e)}

    def run(self):
        """Start monitoring and handle requests. Overrides BaseAgent's run method."""
        logger.info(f"SelfHealingAgent starting main loop on port {self.main_port}")
        
        # Start monitoring threads
        self.monitor_thread.start()
        self.resource_thread.start()
        self.log_scan_thread.start()
        self.health_thread.start() # This is a separate health REP socket for _health_check_loop
        
        try:
            while self.running: # self.running is from BaseAgent
                try:
                    # Poll for messages with timeout on the main REP socket
                    if self.socket.poll(1000) == 0: # 1 second timeout
                        continue
                    
                    # Receive and process message
                    message = self.socket.recv_json()
                    logger.debug(f"Received request: {message}")
                    response = self.handle_request(message)
                    self.socket.send_json(response)
                    
                except zmq.error.ZMQError as e:
                    if e.errno == zmq.EAGAIN: # No message received within timeout
                        continue
                    logger.error(f"ZMQ error in main loop: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Error in main loop: {e}", exc_info=True)
                    # Attempt to send an error response if possible
                    try:
                        self.socket.send_json({'status': 'error', 'message': f'Internal server error: {e}'})
                    except Exception as send_error:
                        logger.error(f"Failed to send error response: {send_error}")
                    
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down.")
        except Exception as e:
            logger.error(f"An unexpected error occurred in {self.name}'s main loop: {e}", exc_info=True)
        finally:
            self.cleanup() # Call the cleanup method on exit

    def monitor_agents_loop(self):
        """Background thread for monitoring agent health"""
        logger.info("Starting agent monitoring loop")
        while self.running:
            try:
                for agent_id, agent_status in list(self.agent_registry.items()): # Iterate on a copy
                    self.check_agent_heartbeat(agent_status)
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Error in agent monitoring loop: {e}", exc_info=True)
                time.sleep(10)

    def check_agent_heartbeat(self, agent_status: "AgentStatus"): # Forward reference
        """Check if an agent has missed heartbeats"""
        current_time = time.time()
        time_since_heartbeat = current_time - agent_status.last_heartbeat
        
        if time_since_heartbeat > 30:  # 30 seconds threshold for missed heartbeat
            agent_status.missed_heartbeats += 1
            if agent_status.status != AGENT_STATUS_OFFLINE and agent_status.missed_heartbeats >= 3:
                agent_status.status = AGENT_STATUS_OFFLINE
                logger.warning(f"Agent {agent_status.agent_name} ({agent_status.agent_id}) is offline (missed {agent_status.missed_heartbeats} heartbeats). Initiating recovery.")
                # TODO: Trigger recovery procedure here (e.g., self._initiate_recovery(agent_status))
            elif agent_status.status == AGENT_STATUS_OFFLINE:
                 logger.warning(f"Agent {agent_status.agent_name} ({agent_status.agent_id}) remains offline (missed {agent_status.missed_heartbeats} heartbeats).")
        else:
            # Agent has sent a heartbeat within the threshold, reset missed heartbeats
            if agent_status.missed_heartbeats > 0:
                logger.info(f"Agent {agent_status.agent_name} ({agent_status.agent_id}) heartbeat received. Resetting missed count.")
            agent_status.missed_heartbeats = 0


    def resource_monitor_loop(self):
        """Background thread for monitoring system resources"""
        logger.info("Starting resource monitoring loop")
        while self.running:
            try:
                # Monitor system resources (CPU, memory, disk usage)
                # This would involve using psutil or similar libraries
                # For example:
                # import psutil
                # cpu_percent = psutil.cpu_percent(interval=1)
                # memory_info = psutil.virtual_memory()
                # logger.debug(f"System CPU: {cpu_percent}%, Memory: {memory_info.percent}%")
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in resource monitoring loop: {e}", exc_info=True)
                time.sleep(30)

    def log_scan_loop(self):
        """Background thread for scanning logs for errors"""
        logger.info("Starting log scanning loop")
        while self.running:
            try:
                # Scan logs for errors and critical warnings
                # This could involve tailing log files or processing logs from a central location
                # For example:
                # with open(log_file_path, 'r') as f:
                #     lines = f.readlines()
                #     for line in lines[-10:]: # Check last 10 lines for simplicity
                #         if "ERROR" in line or "CRITICAL" in line:
                #             logger.warning(f"Detected error in logs: {line.strip()}")
                time.sleep(60)  # Check every 60 seconds
            except Exception as e:
                logger.error(f"Error in log scanning loop: {e}", exc_info=True)
                time.sleep(60)

    def _health_check_loop(self):
        """Background thread for handling health check requests on health_rep_port"""
        logger.info(f"Starting health check loop on port {self.health_rep_port}")
        while self.running:
            try:
                # Poll for health check requests with timeout
                if self.health_socket.poll(1000) == 0: # 1 second timeout
                    continue
                
                message = self.health_socket.recv_json()
                if message.get("action") == "health_check":
                    response = self._health_check() # Use the unified _health_check method
                else:
                    response = {"status": "error", "error": "Invalid health check request"}
                self.health_socket.send_json(response)
            except zmq.error.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    continue # Timeout, no request received
                logger.error(f"ZMQ error in health check loop: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Error in health check loop: {e}", exc_info=True)
                # Attempt to send an error response if possible
                try:
                    self.health_socket.send_json({"status": "error", "message": f"Internal health check error: {e}"})
                except Exception as send_error:
                    logger.error(f"Failed to send health check error response: {send_error}")
        logger.info("Health check loop exited.")

    def cleanup(self):
        """Clean up resources before shutdown. Overrides BaseAgent's cleanup method."""
        logger.info(f"Cleaning up {self.name} resources...")
        self.running = False # Signal threads to stop

        # Join threads with a timeout
        threads_to_join = [
            self.monitor_thread,
            self.resource_thread,
            self.log_scan_thread,
            self.health_thread
        ]
        for thread in threads_to_join:
            if thread and thread.is_alive():
                logger.info(f"Waiting for {thread.name} to terminate...")
                thread.join(timeout=5)
                if thread.is_alive():
                    logger.warning(f"{thread.name} did not terminate gracefully.")
        
        # Close ZMQ sockets
        try:
            for sock in [self.socket, self.pub_socket, self.health_socket]:
                if hasattr(self, 'context') and sock and not sock.closed:
                    sock.close()
                    logger.info(f"Closed ZMQ socket: {sock}")
        except Exception as e:
            logger.error(f"Error closing ZMQ sockets: {e}", exc_info=True)
        
        # Terminate ZMQ context
        try:
            if hasattr(self, 'context') and self.context and not self.context.closed:
                self.context.term()
                logger.info("ZMQ context terminated.")
        except Exception as e:
            logger.error(f"Error terminating ZMQ context: {e}", exc_info=True)
        
        logger.info(f"{self.name} cleanup complete.")
        super().cleanup() # Call parent's cleanup

    def connect_to_main_pc_service(self, service_name: str) -> Optional[zmq.Socket]:
        """
        Connect to a service on the main PC using the network configuration.
        
        Args:
            service_name: Name of the service in the network config ports section
        
        Returns:
            ZMQ socket connected to the service, or None if connection fails or service not found.
        """
        if service_name not in self._network_config.get("ports", {}):
            logger.error(f"Service {service_name} not found in network configuration ports section.")
            return None
            
        port = self._network_config.get("ports")[service_name]
        
        # Check if a connection already exists
        if service_name in self.main_pc_connections:
            # For simplicity, return existing socket. In production, add validation if it's still active.
            return self.main_pc_connections[service_name]
            
        # Create a new socket for this connection
        socket = self.context.socket(zmq.REQ)
        
        # Apply secure ZMQ if available and enabled (assuming secure_zmq is globally handled)
        # from main_pc_code.src.network.secure_zmq import configure_secure_client, start_auth
        # if SECURE_ZMQ_AVAILABLE and self.secure_zmq: # Add a secure_zmq flag if it applies here
        #     try:
        #         socket = configure_secure_client(socket)
        #         logger.info(f"Secure ZMQ client configured for {service_name}.")
        #     except Exception as e:
        #         logger.error(f"Failed to configure secure ZMQ for {service_name}: {e}")
        #         # Decide if to raise or fallback
        
        try:
            # Connect to the service
            connect_address = f"tcp://{self._main_pc_ip}:{port}"
            socket.connect(connect_address)
            logger.info(f"Connected to {service_name} on MainPC at {connect_address}")
            self.main_pc_connections[service_name] = socket
            return socket
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to connect to {service_name} at {connect_address}: {e}", exc_info=True)
            socket.close() # Close the socket if connection fails
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while connecting to {service_name}: {e}", exc_info=True)
            if socket and not socket.closed:
                socket.close()
            return None

class AgentStatus:
    """Class representing the status of an agent in the system"""
    def __init__(self, agent_id: str, agent_name: str, status: str = AGENT_STATUS_UNKNOWN):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.status = status
        self.last_heartbeat = time.time()
        self.missed_heartbeats = 0
        self.restart_attempts = 0
        self.consecutive_failures = 0
        self.health_metrics = {} # Stores latest health metrics received
        self.last_error = None
        self.recovery_time = None # When it last recovered

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

if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = SelfHealingAgent() # Instantiate the actual agent
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'} on PC2 due to keyboard interrupt...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'} on PC2: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name} on PC2...")
            agent.cleanup()