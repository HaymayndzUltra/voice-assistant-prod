import zmq
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys
import os
from common.config_manager import get_service_ip, get_service_url, get_redis_url


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("pc2_code", ".."))
from common.utils.path_manager import PathManager
# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root)

# Import config parser utility
try:
from pc2_code.agents.utils.config_parser import parse_agent_args
    except ImportError as e:
        print(f"Import error: {e}")
    _agent_args 
from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config
from common.env_helpers import get_env

# Load configuration at the module level
config = load_config()= parse_agent_args()
except ImportError:
    class DummyArgs(BaseAgent):
        host = 'localhost'
    _agent_args = DummyArgs()

# Configure logging
log_file_path = PathManager.join_path("logs", str(PathManager.get_logs_dir() / "unified_error_agent.log")
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

class UnifiedErrorAgent:
    """Unified Error Agent for system-wide error handling and analysis."""
    
    def __init__(self, port=None, health_check_port=None, host="0.0.0.0"):
         super().__init__(name="DummyArgs", port=None)
self.main_port = port if port is not None else ERROR_AGENT_PORT
        self.health_port = health_check_port if health_check_port is not None else ERROR_AGENT_HEALTH_PORT
        self.context = zmq.Context()
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
            threshold = self.error_thresholds.get(pattern['severity'], float('inf')
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
    
    def _health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            'status': 'success',
            'agent': 'UnifiedErrorAgent',
            'timestamp': datetime.now().isoformat(),
            'error_count': len(self.error_history),
            'analysis_thread_alive': self.analysis_thread.is_alive(),
            'port': self.main_port
        }
    
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
        self.running = False



if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = DummyArgs()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()