import zmq
from typing import Dict, Any, Optional
import yaml
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys
import os
import re
from collections import defaultdict, deque

# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import config parser utility
try:
    from pc2_code.utils.config_loader import parse_agent_args
    _agent_args = parse_agent_args()
    from common.core.base_agent import BaseAgent
    from pc2_code.agents.utils.config_loader import Config

    # Load configuration at the module level
    config = Config().get_config()
except ImportError as e:
    print(f"Import error: {e}")
    class DummyArgs:
        host = 'localhost'
    _agent_args = DummyArgs()

# Configure logging
log_file_path = 'logs/unified_error_agent.log'
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
logger = logging.getLogger('UnifiedErrorAgent')

# ZMQ ports
ERROR_AGENT_PORT = 7117  # Default, will be overridden by configuration
ERROR_AGENT_HEALTH_PORT = 8117  # Default health check port

class ErrorPattern:
    """Class to represent an error pattern with its regex and metadata"""
    def __init__(self, name: str, regex: str, severity: str = "medium", 
                 recommendation: str = "proactive_restart", description: str = ""):
        self.name = name
        self.regex = regex
        self.severity = severity  # low, medium, high, critical
        self.recommendation = recommendation
        self.description = description
        self.compiled_regex = re.compile(regex)
    def matches(self, line: str) -> bool:
        return bool(self.compiled_regex.search(line))

class ErrorOccurrence:
    def __init__(self, agent_name: str, error_pattern: ErrorPattern, timestamp: float, line: str):
        self.agent_name = agent_name
        self.error_pattern = error_pattern
        self.timestamp = timestamp
        self.line = line

class SystemHealthManager(BaseAgent):
    """SystemHealthManager: Unified error management, health monitoring, and self-healing agent.

    Now manages a central event-driven Error Bus using ZMQ PUB/SUB. Agents publish errors to the bus (topic 'ERROR:'),
    and SystemHealthManager subscribes to this topic for scalable, decoupled error processing.
    
    Integrates with SystemDigitalTwin for dynamic agent discovery and monitoring.
    """
    
    def __init__(self, port=None, health_check_port=None, host="0.0.0.0"):
        # Call BaseAgent's constructor with correct name
        super().__init__(name="SystemHealthManager", port=port if port else ERROR_AGENT_PORT)

        # Record start time for uptime calculation
        self.start_time = time.time()

        # Initialize agent state
        self.running = True
        self.request_count = 0

        # Agent registry for health monitoring
        self.agent_registry = {}  # agent_name -> status dict
        self.heartbeat_interval = 10  # seconds
        self.heartbeat_timeout = 30   # seconds
        self.max_missed_heartbeats = 3
        self.recovery_lock = threading.Lock()
        
        # SystemDigitalTwin integration
        self.digital_twin_discovery_interval = 60  # seconds
        self.last_discovery_time = 0
        
        # Set up connection to SystemDigitalTwin on Main PC
        self.digital_twin_connected = self._connect_to_system_digital_twin()
        if self.digital_twin_connected:
            logger.info("Successfully connected to SystemDigitalTwin")
            # Initial agent discovery
            self._discover_agents_from_digital_twin()
        else:
            logger.warning("Failed to connect to SystemDigitalTwin, will use local agent registry only")

        # Start heartbeat monitoring thread
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_monitor_loop, daemon=True)
        self.heartbeat_thread.start()

        # Set up connection to main PC if needed
        self.main_pc_connections = {}
        self.main_port = self.port
        self.health_port = health_check_port if health_check_port is not None else ERROR_AGENT_HEALTH_PORT
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.main_port}")

        # Initialize error tracking
        self.error_history = []
        self.error_patterns = {}
        self.error_thresholds = {
            'critical': 1,
            'high': 3,
            'medium': 5,
            'low': 10
        }
        self.analysis_thread = threading.Thread(target=self._analyze_errors_loop)
        self.analysis_thread.daemon = True
        self.analysis_thread.start()
        logger.info(f"SystemHealthManager initialized on port {self.main_port}")

        # --- Begin RCA_Agent logic integration ---
        self.logs_dir = Path(config.get('logs_dir', 'logs'))
        self.SCAN_INTERVAL = config.get('scan_interval', 60)
        self.ERROR_WINDOW = config.get('error_window', 600)
        self.ERROR_THRESHOLD = config.get('error_threshold', 5)
        self.error_patterns_list = [
            ErrorPattern(
                name="timeout_error",
                regex=r"TimeoutError|timed? out|connection timeout",
                severity="medium",
                recommendation="proactive_restart",
                description="Connection timeout detected"
            ),
            ErrorPattern(
                name="zmq_error",
                regex=r"ZMQError|Address in use|Address already in use|Cannot bind to address",
                severity="high",
                recommendation="proactive_restart",
                description="ZMQ socket binding error detected"
            ),
            ErrorPattern(
                name="cuda_out_of_memory",
                regex=r"CUDA out of memory|CUDA error|CUDA allocation failed|GPU out of memory",
                severity="critical",
                recommendation="proactive_restart",
                description="GPU memory allocation failure detected"
            ),
            ErrorPattern(
                name="connection_refused",
                regex=r"Connection refused|Failed to connect|Cannot connect to|Connection error",
                severity="medium",
                recommendation="proactive_restart",
                description="Connection refused error detected"
            ),
            ErrorPattern(
                name="file_not_found",
                regex=r"FileNotFoundError|No such file or directory|Cannot find the file|File does not exist",
                severity="medium",
                recommendation="proactive_restart",
                description="File not found error detected"
            ),
            ErrorPattern(
                name="permission_error",
                regex=r"PermissionError|Access denied|Permission denied|Not authorized",
                severity="high",
                recommendation="proactive_restart",
                description="Permission error detected"
            ),
            ErrorPattern(
                name="memory_error",
                regex=r"MemoryError|Out of memory|Cannot allocate memory|Memory allocation failed",
                severity="critical",
                recommendation="proactive_restart",
                description="Memory allocation failure detected"
            ),
            ErrorPattern(
                name="json_decode_error",
                regex=r"JSONDecodeError|Invalid JSON|Failed to parse JSON|JSON parsing error",
                severity="low",
                recommendation="proactive_restart",
                description="JSON parsing error detected"
            ),
            ErrorPattern(
                name="key_error",
                regex=r"KeyError|Key not found|Missing key|Invalid key",
                severity="low",
                recommendation="proactive_restart",
                description="Dictionary key error detected"
            ),
            ErrorPattern(
                name="import_error",
                regex=r"ImportError|ModuleNotFoundError|No module named|Failed to import",
                severity="high",
                recommendation="proactive_restart",
                description="Module import error detected"
            )
        ]
        self.error_occurrences = deque()
        self.file_positions = {}
        self.sent_recommendations = {}
        self.log_scan_thread = threading.Thread(target=self._scan_logs_loop)
        self.log_scan_thread.daemon = True
        self.log_scan_thread.start()
        # --- End RCA_Agent logic integration ---

        # Error Bus configuration
        self.error_bus_port = config.get('error_bus_port', 7150)
        self.error_bus_endpoint = f"tcp://*:{self.error_bus_port}"
        self.error_bus_sub_endpoint = f"tcp://localhost:{self.error_bus_port}"

        # ZMQ PUB socket for Error Bus (for future use, e.g., broadcasting error events)
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.bind(self.error_bus_endpoint)
        logger.info(f"Error Bus PUB socket bound to {self.error_bus_endpoint}")

        # ZMQ SUB socket for Error Bus (subscribe to error events)
        self.error_bus_sub = self.context.socket(zmq.SUB)
        self.error_bus_sub.connect(self.error_bus_sub_endpoint)
        self.error_bus_sub.setsockopt(zmq.SUBSCRIBE, b"ERROR:")
        logger.info(f"Error Bus SUB socket connected to {self.error_bus_sub_endpoint} (topic: 'ERROR:')")

        # Start background thread to listen for error events
        self.error_bus_thread = threading.Thread(target=self._listen_error_bus, daemon=True)
        self.error_bus_thread.start()
        logger.info("Error Bus listener thread started.")
    
    def _connect_to_system_digital_twin(self) -> bool:
        """Establish connection to SystemDigitalTwin on Main PC."""
        try:
            # Use the existing connect_to_main_pc_service method
            self.digital_twin_socket = self.connect_to_main_pc_service("SystemDigitalTwin")
            if self.digital_twin_socket:
                logger.info("Connected to SystemDigitalTwin service")
                return True
            else:
                logger.warning("Failed to connect to SystemDigitalTwin service")
                return False
        except Exception as e:
            logger.error(f"Error connecting to SystemDigitalTwin: {e}")
            return False
    
    def _discover_agents_from_digital_twin(self) -> None:
        """Query SystemDigitalTwin for the list of registered agents."""
        if not hasattr(self, 'digital_twin_socket') or not self.digital_twin_socket:
            logger.warning("Cannot discover agents: No connection to SystemDigitalTwin")
            return
        
        try:
            # Use BaseAgent's send_request_to_agent method for standardized communication
            response = self.send_request_to_agent(
                agent_name="SystemDigitalTwin",
                request={"action": "get_registered_agents"},
                timeout=5000  # 5 seconds timeout
            )
            
            if isinstance(response, dict) and response.get("status") == "success" and "agents" in response:
                agents = response.get("agents", [])
                if isinstance(agents, list):
                    logger.info(f"Discovered {len(agents)} agents from SystemDigitalTwin")
                    
                    # Register all discovered agents
                    for agent_info in agents:
                        if isinstance(agent_info, dict):
                            agent_name = agent_info.get("name")
                            if agent_name:
                                self.register_agent(agent_name)
                                logger.debug(f"Registered agent from discovery: {agent_name}")
                    
                    # Update last discovery time
                    self.last_discovery_time = time.time()
                else:
                    logger.warning("Agents data from SystemDigitalTwin is not a list")
            else:
                error_msg = "Unknown error"
                if isinstance(response, dict):
                    error_msg = response.get("message", error_msg)
                logger.warning(f"Failed to get agents from SystemDigitalTwin: {error_msg}")
        except Exception as e:
            logger.error(f"Error discovering agents from SystemDigitalTwin: {e}")
    
    def register_agent(self, agent_name: str):
        """Register an agent for health monitoring."""
        if agent_name is None:
            logger.error('register_agent called with None agent_name')
            return
        if agent_name not in self.agent_registry:
            self.agent_registry[agent_name] = {
                'status': 'unknown',
                'last_heartbeat': time.time(),
                'missed_heartbeats': 0,
                'restart_attempts': 0
            }
            logger.info(f"Agent {agent_name} registered for health monitoring")

    def receive_heartbeat(self, agent_name: str):
        """Update heartbeat info for an agent."""
        if agent_name is None:
            logger.error('receive_heartbeat called with None agent_name')
            return
        self.register_agent(agent_name)
        self.agent_registry[agent_name]['last_heartbeat'] = time.time()
        self.agent_registry[agent_name]['missed_heartbeats'] = 0
        self.agent_registry[agent_name]['status'] = 'online'

    def _heartbeat_monitor_loop(self):
        while self.running:
            now = time.time()
            
            # Periodically discover agents from SystemDigitalTwin
            if self.digital_twin_connected and (now - self.last_discovery_time) > self.digital_twin_discovery_interval:
                self._discover_agents_from_digital_twin()
            
            # Monitor registered agents
            for agent_name, info in list(self.agent_registry.items()):
                if now - info['last_heartbeat'] > self.heartbeat_timeout:
                    info['missed_heartbeats'] += 1
                    if info['missed_heartbeats'] >= self.max_missed_heartbeats:
                        if info['status'] != 'offline':
                            logger.warning(f"Agent {agent_name} missed {info['missed_heartbeats']} heartbeats. Marking as offline and attempting recovery.")
                            info['status'] = 'offline'
                            self._recover_agent(agent_name)
                else:
                    info['status'] = 'online'
            time.sleep(self.heartbeat_interval)

    def _recover_agent(self, agent_name: str):
        if not isinstance(agent_name, str):
            logger.error(f"_recover_agent called with non-string agent_name: {agent_name}")
            return
        with self.recovery_lock:
            logger.info(f"Attempting to recover agent: {agent_name}")
            try:
                # First, try to get agent information from SystemDigitalTwin
                agent_info = self._get_agent_info_from_digital_twin(agent_name)
                
                if agent_info:
                    # Use agent info from SystemDigitalTwin for recovery
                    self._restart_agent(agent_name, agent_info)
                else:
                    # Fall back to basic restart without additional info
                    self._restart_agent(agent_name)
                    
                if agent_name in self.agent_registry:
                    self.agent_registry[agent_name]['restart_attempts'] += 1
                logger.info(f"Restarted agent {agent_name} successfully.")
            except Exception as e:
                logger.error(f"Failed to restart agent {agent_name}: {e}")

    def _get_agent_info_from_digital_twin(self, agent_name: str) -> Dict[str, Any]:
        """Get detailed agent information from SystemDigitalTwin."""
        if not self.digital_twin_connected:
            return {}
            
        try:
            response = self.send_request_to_agent(
                agent_name="SystemDigitalTwin",
                request={"action": "get_agent_info", "agent_name": agent_name},
                timeout=5000
            )
            
            if isinstance(response, dict) and response.get("status") == "success" and "agent_info" in response:
                logger.info(f"Retrieved agent info for {agent_name} from SystemDigitalTwin")
                return response.get("agent_info", {})
            else:
                logger.warning(f"Failed to get agent info for {agent_name} from SystemDigitalTwin")
                return {}
        except Exception as e:
            logger.error(f"Error getting agent info from SystemDigitalTwin: {e}")
            return {}

    def _restart_agent(self, agent_name: str, agent_info: Optional[Dict[str, Any]] = None):
        """Restart an agent using information from SystemDigitalTwin if available."""
        if agent_info and isinstance(agent_info, dict) and "script_path" in agent_info:
            script_path = agent_info.get("script_path")
            port = agent_info.get("port")
            logger.info(f"Restarting agent {agent_name} using script: {script_path} on port {port}")
            
            # Here you would implement the actual restart logic using subprocess
            # For now, this is still a placeholder
            logger.info(f"Restart logic for {agent_name} would use script_path: {script_path} and port: {port}")
        else:
            # Fall back to basic restart without script path
            logger.info(f"Restart logic for {agent_name} would be executed here (no script path available).")
        
        # Placeholder for actual restart implementation
        pass

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests to the agent."""
        if not isinstance(request, dict):
            return {'status': 'error', 'message': 'Invalid request type, expected dict'}
            
        action = request.get('action', '')
        if action == 'heartbeat':
            agent_name = request.get('agent_name')
            if agent_name is not None:
                self.receive_heartbeat(agent_name)
                return {'status': 'success', 'message': f'Heartbeat received for {agent_name}'}
            else:
                return {'status': 'error', 'message': 'Missing agent_name in heartbeat'}
        elif action == 'register_agent':
            agent_name = request.get('agent_name')
            if agent_name is not None:
                self.register_agent(agent_name)
                return {'status': 'success', 'message': f'Agent {agent_name} registered'}
            else:
                return {'status': 'error', 'message': 'Missing agent_name in registration'}
        elif action == 'report_error':
            # Ensure request is properly typed before passing to _handle_error_report
            if isinstance(request, dict):
                return self._handle_error_report(request)
            else:
                return {'status': 'error', 'message': 'Invalid request format for error report'}
        elif action == 'get_error_stats':
            return self._get_error_stats()
        elif action == 'health_check':
            return self._health_check()
        elif action == 'get_monitored_agents':
            # New action to get the list of agents being monitored
            return {
                'status': 'success',
                'agents': [
                    {'name': name, 'status': info['status'], 'last_heartbeat': info['last_heartbeat']}
                    for name, info in self.agent_registry.items()
                ]
            }
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}
    
    def _analyze_errors_loop(self):
        """Background thread for analyzing errors."""
        while self.running:
            try:
                self._analyze_error_patterns()
                self._check_error_thresholds()
                time.sleep(60)  # Analyze every minute
            except Exception as e:
                logger.error(f"Error in analysis loop: {e}")
    
    def _analyze_error_patterns(self):
        """Analyze error patterns in the history."""
        # Group errors by type
        error_groups = {}
        for error in self.error_history:
            error_type = error.get('type', 'unknown')
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append(error)
        
        # Update patterns
        self.error_patterns = {
            error_type: {
                'count': len(errors),
                'last_occurrence': max(e['timestamp'] for e in errors),
                'severity': self._determine_severity(errors)
            }
            for error_type, errors in error_groups.items()
        }
    
    def _determine_severity(self, errors: List[Dict]) -> str:
        """Determine the severity of a group of errors."""
        if any(e.get('severity') == 'critical' for e in errors):
            return 'critical'
        elif any(e.get('severity') == 'high' for e in errors):
            return 'high'
        elif any(e.get('severity') == 'medium' for e in errors):
            return 'medium'
        return 'low'
    
    def _check_error_thresholds(self):
        """Check if any error patterns exceed thresholds."""
        for error_type, pattern in self.error_patterns.items():
            threshold = self.error_thresholds.get(pattern['severity'], float('inf'))
            if pattern['count'] >= threshold:
                logger.warning(f"Error threshold exceeded for {error_type}: {pattern['count']} occurrences")
                self._trigger_alert(error_type, pattern)
    
    def _trigger_alert(self, error_type: str, pattern: Dict):
        logger.warning(f"Triggering internal recovery for error type: {error_type}")
        affected_agents = [e['agent_name'] for e in self.error_history if e.get('type') == error_type]
        for agent_name in set(affected_agents):
            self._recover_agent(agent_name)
    
    def _handle_error_report(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle error report requests."""
        try:
            # Check if this is a standardized error report
            standardized_format = request.get('standardized_format', None)
            
            if standardized_format and standardized_format.get('message_type') == 'error_report':
                # Process standardized error report
                error_data = standardized_format.get('error_data', {})
                
                # Extract data from standardized format
                error_entry = {
                    'type': error_data.get('error_type', 'unknown'),
                    'message': error_data.get('details', {}).get('description', ''),
                    'severity': error_data.get('severity', 'low'),
                    'timestamp': standardized_format.get('timestamp', datetime.now().isoformat()),
                    'source': standardized_format.get('source', 'unknown'),
                    'details': error_data.get('details', {})
                }
                
                # Add target agent if present
                if 'target_agent' in error_data.get('details', {}):
                    error_entry['target_agent'] = error_data['details']['target_agent']
                
                logger.info(f"Processed standardized error report from {error_entry['source']}: {error_entry['type']} (Severity: {error_entry['severity']})")
            else:
                # Process legacy format
                error_entry = {
                    'type': request.get('error_type', 'unknown'),
                    'message': request.get('reason', request.get('message', '')),
                    'severity': request.get('severity', 'low'),
                    'timestamp': datetime.now().isoformat(),
                    'source': request.get('source', 'unknown'),
                    'details': request.get('details', {})
                }
                
                # Add additional fields from RCA_Agent if present
                if 'target_agent' in request:
                    error_entry['target_agent'] = request['target_agent']
                if 'error_pattern' in request:
                    error_entry['error_pattern'] = request['error_pattern']
                if 'error_count' in request:
                    error_entry['count'] = request['error_count']
                
                logger.info(f"Processed legacy error report from {error_entry['source']}: {error_entry['type']} (Severity: {error_entry['severity']})")
            
            # Store the error in history
            self.error_history.append(error_entry)
            # Keep only last 1000 errors
            self.error_history = self.error_history[-1000:]
            
            # Check if this is a critical error that needs immediate recovery
            if error_entry['severity'] == 'critical':
                agent_name = error_entry.get('type')
                if isinstance(agent_name, str):
                    self._recover_agent(agent_name)
            
            return {'status': 'success', 'message': 'Error reported successfully'}
        except Exception as e:
            logger.error(f"Error handling error report: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        return {
            'status': 'success',
            'error_patterns': self.error_patterns,
            'total_errors': len(self.error_history),
            'recent_errors': self.error_history[-10:] if self.error_history else []
        }
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Return health status information. Overrides BaseAgent's _get_health_status."""
        # Get base status from parent class
        base_status = super()._get_health_status()
        
        # Add UnifiedErrorAgent specific health info
        base_status.update({
            'agent': 'SystemHealthManager',
            'timestamp': datetime.now().isoformat(),
            'error_count': len(self.error_history),
            'analysis_thread_alive': self.analysis_thread.is_alive(),
            'port': self.main_port
        })
        
        return base_status

    def _health_check(self) -> Dict[str, Any]:
        """Legacy health check method for backward compatibility."""
        return self._get_health_status()
    
    def run(self):
        logger.info(f"SystemHealthManager starting on port {self.main_port}")
        try:
            while self.running:
                try:
                    request = self.socket.recv_json()
                    logger.debug(f"Received request: {request}")
                    response = self.handle_request(request)
                    self.socket.send_json(response)
                except zmq.error.ZMQError as e:
                    logger.error(f"ZMQ error in run loop: {e}")
                    try:
                        self.socket.send_json({'status': 'error', 'error': str(e)})
                    except:
                        pass
                except Exception as e:
                    logger.error(f"Error in run loop: {e}")
                    try:
                        self.socket.send_json({'status': 'error', 'error': str(e)})
                    except:
                        pass
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        logger.info("Cleaning up resources...")
        self.running = False
        if self.analysis_thread.is_alive():
            self.analysis_thread.join(timeout=5)
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        logger.info("Cleanup complete")

    def stop(self):
        self.running = False

    def connect_to_main_pc_service(self, service_name: str):
        """Connect to a service on the main PC."""
        if not hasattr(self, 'main_pc_connections'):
            self.main_pc_connections = {}
            
        # Safely handle network_config
        if not network_config or not isinstance(network_config, dict):
            logger.error(f"Invalid network configuration")
            return None
            
        ports = {}
        if "ports" in network_config and isinstance(network_config["ports"], dict):
            ports = network_config["ports"]
            
        if service_name not in ports:
            logger.error(f"Service {service_name} not found in network configuration")
            return None
            
        port = ports[service_name]
        socket = self.context.socket(zmq.REQ)
        socket.connect(f"tcp://{MAIN_PC_IP}:{port}")
        self.main_pc_connections[service_name] = socket
        logger.info(f"Connected to {service_name} on MainPC at {MAIN_PC_IP}:{port}")
        return socket

    def _scan_logs_loop(self):
        logger.info("Starting log scanning loop (SystemHealthManager)")
        while self.running:
            try:
                self._scan_logs()
                self._analyze_log_errors()
                time.sleep(self.SCAN_INTERVAL)
            except Exception as e:
                logger.error(f"Error in log scanning loop: {e}")
                time.sleep(self.SCAN_INTERVAL)

    def _scan_logs(self):
        if not self.logs_dir.exists():
            logger.warning(f"Logs directory not found: {self.logs_dir}")
            return
        log_files = list(self.logs_dir.glob("*.log"))
        logger.debug(f"Found {len(log_files)} log files")
        for log_file in log_files:
            try:
                self._process_log_file(log_file)
            except Exception as e:
                logger.error(f"Error processing log file {log_file}: {e}")

    def _process_log_file(self, log_file: Path):
        agent_name = log_file.stem
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                if log_file in self.file_positions:
                    f.seek(self.file_positions[log_file])
                new_lines = f.readlines()
                self.file_positions[log_file] = f.tell()
                if new_lines:
                    logger.debug(f"Processing {len(new_lines)} new lines from {log_file}")
                    self._process_log_lines(agent_name, new_lines)
        except Exception as e:
            logger.error(f"Error reading log file {log_file}: {e}")

    def _process_log_lines(self, agent_name: str, lines: List[str]):
        current_time = time.time()
        for line in lines:
            for pattern in self.error_patterns_list:
                if pattern.matches(line):
                    occurrence = ErrorOccurrence(
                        agent_name=agent_name,
                        error_pattern=pattern,
                        timestamp=current_time,
                        line=line
                    )
                    self.error_occurrences.append(occurrence)
                    logger.debug(f"Found error pattern '{pattern.name}' in {agent_name}: {line.strip()}")

    def _analyze_log_errors(self):
        current_time = time.time()
        while self.error_occurrences and self.error_occurrences[0].timestamp < current_time - self.ERROR_WINDOW:
            self.error_occurrences.popleft()
        error_counts = defaultdict(lambda: defaultdict(int))
        for occurrence in self.error_occurrences:
            error_counts[occurrence.agent_name][occurrence.error_pattern.name] += 1
        for agent_name, patterns in error_counts.items():
            for pattern_name, count in patterns.items():
                if count >= self.ERROR_THRESHOLD:
                    pattern = next((p for p in self.error_patterns_list if p.name == pattern_name), None)
                    if pattern:
                        recommendation_key = f"{agent_name}:{pattern_name}"
                        last_sent = self.sent_recommendations.get(recommendation_key, 0)
                        if current_time - last_sent > self.ERROR_WINDOW:
                            self._handle_log_error_detection(agent_name, pattern, count)
                            self.sent_recommendations[recommendation_key] = current_time

    def _handle_log_error_detection(self, agent_name: str, pattern: ErrorPattern, count: int):
        logger.info(f"[LogScan] Detected {pattern.name} for {agent_name} ({count} occurrences)")
        # Integrate with the existing error reporting logic
        error_report = {
            "message_type": "error_report",
            "source": "SystemHealthManager-LogScanner",
            "timestamp": datetime.now().isoformat(),
            "error_data": {
                "error_id": f"{agent_name}_{pattern.name}_{int(time.time())}",
                "error_type": pattern.name,
                "severity": pattern.severity,
                "details": {
                    "target_agent": agent_name,
                    "count": count,
                    "description": pattern.description,
                    "time_window_seconds": self.ERROR_WINDOW
                }
            }
        }
        # Directly handle as if received via _handle_error_report
        self._handle_error_report({
            'action': 'report_error',
            'source': 'SystemHealthManager-LogScanner',
            'error_type': 'log_pattern_detected',
            'target_agent': agent_name,
            'reason': f"High frequency of {pattern.name} detected ({count} occurrences in {self.ERROR_WINDOW/60} minutes). {pattern.description}",
            'severity': pattern.severity,
            'error_pattern': pattern.name,
            'error_count': count,
            'standardized_format': error_report
        })

    def _listen_error_bus(self):
        while self.running:
            try:
                topic, msg = self.error_bus_sub.recv_multipart()
                if topic == b"ERROR:":
                    try:
                        error_data = json.loads(msg.decode('utf-8'))
                        if isinstance(error_data, dict):
                            self._handle_error_report(error_data)
                        else:
                            logger.error(f"Received non-dict error data on error bus: {error_data}")
                    except Exception as e:
                        logger.error(f"Failed to process error bus message: {e}")
            except zmq.error.ZMQError as e:
                logger.error(f"ZMQ error on error bus: {e}")
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in error bus listener: {e}")
                time.sleep(1)

if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = SystemHealthManager()  # Fixed: Use SystemHealthManager instead of DummyArgs
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