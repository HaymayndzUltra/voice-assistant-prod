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

# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import config parser utility
try:
    from pc2_code.utils.config_loader import parse_agent_args
    _agent_args = parse_agent_args()
    from main_pc_code.src.core.base_agent import BaseAgent
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

class UnifiedErrorAgent(BaseAgent):
    """Unified Error Agent for system-wide error handling and analysis."""
    
    def __init__(self, port=None, health_check_port=None, host="0.0.0.0"):
        # Call BaseAgent's constructor first
        super().__init__(name="UnifiedErrorAgent", port=port if port else ERROR_AGENT_PORT)

        # Record start time for uptime calculation
        self.start_time = time.time()

        # Initialize agent state
        self.running = True
        self.request_count = 0

        # Set up connection to main PC if needed
        self.main_pc_connections = {}

        # Set up ports - use self.port from BaseAgent
        self.main_port = self.port
        self.health_port = health_check_port if health_check_port is not None else ERROR_AGENT_HEALTH_PORT
        
        # Set up ZMQ socket - use BaseAgent's context
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
        # Start error analysis thread
        self.running = True
        self.analysis_thread = threading.Thread(target=self._analyze_errors_loop)
        self.analysis_thread.daemon = True
        self.analysis_thread.start()
        logger.info(f"Unified Error Agent initialized on port {self.main_port}")
    
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
        """Trigger an alert for exceeded error threshold."""
        alert = {
            'type': 'error_threshold',
            'error_type': error_type,
            'count': pattern['count'],
            'severity': pattern['severity'],
            'timestamp': datetime.now().isoformat()
        }
        logger.warning(f"Alert triggered: {json.dumps(alert)}")
        # TODO: Implement alert notification system
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action', '')
        
        if action == 'report_error':
            return self._handle_error_report(request)
        elif action == 'get_error_stats':
            return self._get_error_stats()
        elif action == 'health_check':
            return self._health_check()
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}
    
    def _handle_error_report(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle error report requests."""
        try:
            error_data = {
                'type': request.get('error_type', 'unknown'),
                'message': request.get('message', ''),
                'severity': request.get('severity', 'low'),
                'timestamp': datetime.now().isoformat(),
                'source': request.get('source', 'unknown'),
                'details': request.get('details', {})
            }
            
            self.error_history.append(error_data)
            # Keep only last 1000 errors
            self.error_history = self.error_history[-1000:]
            
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
            'agent': 'UnifiedErrorAgent',
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
        logger.info(f"Unified Error Agent starting on port {self.main_port}")
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
        if not hasattr(self, 'main_pc_connections'):
            self.main_pc_connections = {}
        ports = network_config.get("ports") if network_config and isinstance(network_config.get("ports"), dict) else {}
        if service_name not in ports:
            logger.error(f"Service {service_name} not found in network configuration")
            return None
        port = ports[service_name]
        socket = self.context.socket(zmq.REQ)
        socket.connect(f"tcp://{MAIN_PC_IP}:{port}")
        self.main_pc_connections[service_name] = socket
        logger.info(f"Connected to {service_name} on MainPC at {MAIN_PC_IP}:{port}")
        return socket

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