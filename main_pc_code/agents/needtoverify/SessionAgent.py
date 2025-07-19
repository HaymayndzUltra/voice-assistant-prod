from common.core.base_agent import BaseAgent
import zmq
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List
import os
import threading
import psutil
from datetime import datetime
from common.env_helpers import get_env

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('session_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SessionAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="Sessionagent")
        """Initialize the SessionAgent with ZMQ sockets."""
        self.port = port
        self.context = zmq.Context()
        
        # Main REP socket for handling requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://*:{port}")
        
        # SUB socket for CoordinatorAgent
        self.coordinator_socket = self.context.socket(zmq.SUB)
        self.coordinator_socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5621")  # CoordinatorAgent
        self.coordinator_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # Store session data
        self.current_session = None
        self.session_log = None
        self.session_events = []
        
        # Start event monitoring thread
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_events)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info(f"SessionAgent initialized on port {port}")
    
    def _create_session_folder(self) -> str:
        """Create a new session folder with timestamp."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        folder_name = f"session_{timestamp}"
        
        try:
            os.makedirs(folder_name, exist_ok=True)
            return folder_name
        except Exception as e:
            logger.error(f"Error creating session folder: {str(e)}")
            return None
    
    def _create_session_log(self, folder: str) -> str:
        """Create a new session log file."""
        log_file = os.path.join(folder, "session_log.txt")
        
        try:
            with open(log_file, 'w') as f:
                f.write(f"Session started at: {datetime.now().isoformat()}\n")
                f.write("=" * 50 + "\n\n")
            return log_file
        except Exception as e:
            logger.error(f"Error creating session log: {str(e)}")
            return None
    
    def _log_event(self, event: Dict[str, Any]):
        """Log an event to the session log file."""
        if self.session_log is None:
            return
        
        try:
            with open(self.session_log, 'a') as f:
                f.write(f"\n[{datetime.now().isoformat()}] {event['type']}\n")
                f.write(f"Details: {json.dumps(event['details'], indent=2)}\n")
                f.write("-" * 50 + "\n")
        except Exception as e:
            logger.error(f"Error logging event: {str(e)}")
    
    def _monitor_events(self):
        """Monitor events from CoordinatorAgent."""
        while self.running:
            try:
                # Receive event
                message = self.coordinator_socket.recv_json()
                
                # Log event if session is active
                if self.current_session is not None:
                    self._log_event(message)
                    self.session_events.append(message)
                
            except Exception as e:
                logger.error(f"Error monitoring events: {str(e)}")
                time.sleep(5)  # Wait before retrying
    
    def start_recording(self) -> Dict[str, Any]:
        """Start a new session recording."""
        try:
            # Create session folder
            folder = self._create_session_folder()
            if folder is None:
                return {
                    'status': 'error',
                    'message': 'Failed to create session folder'
                }
            
            # Create session log
            log_file = self._create_session_log(folder)
            if log_file is None:
                return {
                    'status': 'error',
                    'message': 'Failed to create session log'
                }
            
            # Update session data
            self.current_session = {
                'folder': folder,
                'start_time': datetime.now().isoformat(),
                'status': 'active'
            }
            self.session_log = log_file
            self.session_events = []
            
            logger.info(f"Started new session recording in {folder}")
            
            return {
                'status': 'success',
                'session_id': folder
            }
            
        except Exception as e:
            logger.error(f"Error starting recording: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def stop_recording(self) -> Dict[str, Any]:
        """Stop the current session recording."""
        if self.current_session is None:
            return {
                'status': 'error',
                'message': 'No active session'
            }
        
        try:
            # Update session data
            self.current_session['end_time'] = datetime.now().isoformat()
            self.current_session['status'] = 'completed'
            
            # Write session summary
            summary_file = os.path.join(self.current_session['folder'], "session_summary.json")
            with open(summary_file, 'w') as f:
                json.dump({
                    'session': self.current_session,
                    'event_count': len(self.session_events),
                    'events': self.session_events
                }, f, indent=2)
            
            # Reset session data
            session_id = self.current_session['folder']
            self.current_session = None
            self.session_log = None
            self.session_events = []
            
            logger.info(f"Stopped session recording: {session_id}")
            
            return {
                'status': 'success',
                'session_id': session_id
            }
            
        except Exception as e:
            logger.error(f"Error stopping recording: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_session_status(self) -> Dict[str, Any]:
        """Get the status of the current session."""
        if self.current_session is None:
            return {
                'status': 'success',
                'session': None
            }
        
        return {
            'status': 'success',
            'session': self.current_session
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action')
        
        if action == 'start_recording':
            return self.start_recording()
            
        elif action == 'stop_recording':
            return self.stop_recording()
            
        elif action == 'get_session_status':
            return self.get_session_status()
            
        else:
            return {
                'status': 'error',
                'message': f'Unknown action: {action}'
            }
    
    def run(self):
        """Main loop for handling requests."""
        logger.info("SessionAgent started")
        
        while True:
            try:
                # Wait for next request
                message = self.socket.recv_json()
                logger.debug(f"Received request: {message}")
                
                # Process request
                response = self.handle_request(message)
                
                # Send response
                self.socket.send_json(response)
                logger.debug(f"Sent response: {response}")
                
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                self.socket.send_json({
                    'status': 'error',
                    'message': str(e)
                })
    
    def stop(self):
        """Stop the agent and clean up resources."""
        self.running = False
        self.monitor_thread.join()
        
        self.socket.close()
        self.coordinator_socket.close()
        self.context.term()


    def health_check(self):
        '''
        Performs a health check on the agent, returning a dictionary with its status.
        '''
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
            # TODO: Add agent-specific health checks here.
            # For example, check if a required connection is alive.
            # if not self.some_service_connection.is_alive():
            #     is_healthy = False

            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else -1,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {} # Placeholder for agent-specific data
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "error": f"Health check failed with exception: {str(e)}"
            }

if __name__ == '__main__':
    agent = SessionAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise