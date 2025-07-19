import sys
import os
import zmq
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
import threading
import psutil
import traceback

from common.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config
from main_pc_code.utils.service_discovery_client import discover_service, register_service
from main_pc_code.utils.network_utils import get_zmq_connection_string, get_machine_ip
from common.env_helpers import get_env

# Load configuration
config = load_config()

# ZMQ timeout settings from config
ZMQ_REQUEST_TIMEOUT = int(config.get("zmq_request_timeout", 5000))  # 5 seconds timeout for requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProactiveAgent(BaseAgent):
    def __init__(self, **kwargs):
        """Initialize the ProactiveAgent with ZMQ sockets."""
        # Get configuration values with fallbacks
        agent_port = kwargs.get('port') or int(config.get("port", 5624))
        agent_name = kwargs.get('name') or config.get("name", "ProactiveAgent")
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=agent_name, port=agent_port)
        
        # Initialize configuration values
        self.coordinator_address = config.get("coordinator_address", get_zmq_connection_string(26002, "localhost"))
        self.suggestion_interval = int(config.get("suggestion_interval_seconds", 60))
        self.tasks_file = config.get("tasks_file", "tasks.json")
        
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Main REP socket for handling requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://*:{self.port}")
        
        # Store tasks and reminders
        self.tasks = self._load_tasks()
        
        # Initialize coordinator socket (will be set up in async initialization)
        self.coordinator_socket = None
        
        # Error bus connection
        self.error_bus_port = int(config.get("error_bus_port", 7150))
        self.error_bus_host = os.environ.get('PC2_IP', config.get("pc2_ip", get_env("BIND_ADDRESS", "0.0.0.0")))
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)
        
        # Start monitoring thread
        self.running = True
        self.start_time = time.time()
        self.monitor_thread = threading.Thread(target=self._monitor_tasks)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        # Initialize the coordinator connection in a background thread
        threading.Thread(target=self._init_coordinator, daemon=True).start()
        
        logger.info(f"ProactiveAgent initialized on port {self.port}")
    
    def _init_coordinator(self):
        """Initialize connection to the RequestCoordinator."""
        try:
            # Try to discover coordinator via service discovery
            coordinator_info = discover_service("RequestCoordinator")
            if coordinator_info:
                host = coordinator_info.get("host", get_env("BIND_ADDRESS", "0.0.0.0"))
                port = coordinator_info.get("port", 5621)
                self.coordinator_address = f"tcp://{host}:{port}"
            
            # Set up coordinator socket
            self.coordinator_socket = self.context.socket(zmq.REQ)
            self.coordinator_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.coordinator_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.coordinator_socket.connect(self.coordinator_address)
            logger.info(f"Coordinator socket initialized at {self.coordinator_address}")
        except Exception as e:
            logger.error(f"Coordinator initialization error: {e}")
    
    def _get_health_status(self):
        """Get the current health status of the agent."""
        return {'status': 'ok', 'running': self.running}
    
    def _perform_initialization(self):
        """Initialize agent components asynchronously."""
        try:
            # Already handled in __init__ and _init_coordinator
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
    
    def _load_tasks(self) -> Dict[str, Any]:
        """Load tasks from JSON file."""
        try:
            if os.path.exists(self.tasks_file):
                with open(self.tasks_file, 'r') as f:
                    return json.load(f)
            return {'tasks': [], 'reminders': []}
        except Exception as e:
            logger.error(f"Error loading tasks: {str(e)}")
            return {'tasks': [], 'reminders': []}
    
    def _save_tasks(self):
        """Save tasks to JSON file."""
        try:
            with open(self.tasks_file, 'w') as f:
                json.dump(self.tasks, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving tasks: {str(e)}")
    
    def _monitor_tasks(self):
        """Monitor tasks and reminders in the background."""
        while self.running:
            try:
                current_time = datetime.now()
                
                # Check tasks
                for task in self.tasks['tasks']:
                    if task['status'] == 'pending':
                        scheduled_time = datetime.fromisoformat(task['scheduled_time'])
                        if current_time >= scheduled_time:
                            self._execute_task(task)
                
                # Check reminders
                for reminder in self.tasks['reminders']:
                    if reminder['status'] == 'pending':
                        scheduled_time = datetime.fromisoformat(reminder['scheduled_time'])
                        if current_time >= scheduled_time:
                            self._execute_reminder(reminder)
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error monitoring tasks: {str(e)}")
                time.sleep(300)  # Wait 5 minutes before retrying
    
    def _execute_task(self, task: Dict[str, Any]):
        """Execute a scheduled task."""
        try:
            if not self.coordinator_socket:
                logger.warning("Coordinator socket not ready, skipping task execution")
                return
                
            # Send task to RequestCoordinator
            self.coordinator_socket.send_json({
                'action': 'execute_task',
                'task': task
            })
            
            response = self.coordinator_socket.recv_json()
            
            if response['status'] == 'success':
                task['status'] = 'completed'
                task['completion_time'] = datetime.now().isoformat()
                self._save_tasks()
                logger.info(f"Task {task['id']} executed successfully")
            else:
                logger.error(f"Failed to execute task {task['id']}: {response.get('message', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error executing task {task['id']}: {str(e)}")
    
    def _execute_reminder(self, reminder: Dict[str, Any]):
        """Execute a reminder."""
        try:
            if not self.coordinator_socket:
                logger.warning("Coordinator socket not ready, skipping reminder execution")
                return
                
            # Send reminder to RequestCoordinator
            self.coordinator_socket.send_json({
                'action': 'send_reminder',
                'reminder': reminder
            })
            
            response = self.coordinator_socket.recv_json()
            
            if response['status'] == 'success':
                reminder['status'] = 'completed'
                reminder['completion_time'] = datetime.now().isoformat()
                self._save_tasks()
                logger.info(f"Reminder {reminder['id']} sent successfully")
            else:
                logger.error(f"Failed to send reminder {reminder['id']}: {response.get('message', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error sending reminder {reminder['id']}: {str(e)}")
    
    def add_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new scheduled task."""
        try:
            # Generate task ID
            task['id'] = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            task['status'] = 'pending'
            task['created_at'] = datetime.now().isoformat()
            
            self.tasks['tasks'].append(task)
            self._save_tasks()
            
            return {
                'status': 'success',
                'task_id': task['id']
            }
            
        except Exception as e:
            logger.error(f"Error adding task: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def add_reminder(self, reminder: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new reminder."""
        try:
            # Generate reminder ID
            reminder['id'] = f"reminder_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            reminder['status'] = 'pending'
            reminder['created_at'] = datetime.now().isoformat()
            
            self.tasks['reminders'].append(reminder)
            self._save_tasks()
            
            return {
                'status': 'success',
                'reminder_id': reminder['id']
            }
            
        except Exception as e:
            logger.error(f"Error adding reminder: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_tasks(self) -> Dict[str, Any]:
        """Get all tasks and reminders."""
        return {
            'status': 'success',
            'tasks': self.tasks
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action')

        # Respond to orchestrator health checks
        if action in ('health_check', 'health'):
            return {
                'status': 'ok',
                'message': 'ProactiveAgent healthy',
                'timestamp': datetime.now().isoformat()
            }
        
        if action == 'add_task':
            return self.add_task(request['task'])
            
        elif action == 'add_reminder':
            return self.add_reminder(request['reminder'])
            
        elif action == 'get_tasks':
            return self.get_tasks()
            
        else:
            return {
                'status': 'error',
                'message': f'Unknown action: {action}'
            }
    
    def run(self):
        """Main loop for handling requests."""
        logger.info("ProactiveAgent started")
        
        while self.running:
            try:
                # Wait for next request
                message = self.socket.recv_json()
                logger.debug(f"Received request: {message}")
                
                # Process request
                response = self.handle_request(message)
                
                # Send response
                self.socket.send_json(response)
                logger.debug(f"Sent response: {response}")
                
            except zmq.error.Again:
                # Socket timeout, continue loop
                continue
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                try:
                    self.socket.send_json({
                        'status': 'error',
                        'message': str(e)
                    })
                except zmq.error.Again:
                    pass  # Can't send response due to timeout
    
    def stop(self):
        """Stop the agent and clean up resources."""
        logger.info("Stopping ProactiveAgent...")
        self.running = False
        
        if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        self.cleanup()
        logger.info("ProactiveAgent stopped")

    def cleanup(self):
        """Clean up resources when the agent is stopping."""
        try:
            # Close ZMQ sockets
            if hasattr(self, 'socket') and self.socket:
                self.socket.close()
            
            if hasattr(self, 'coordinator_socket') and self.coordinator_socket:
                self.coordinator_socket.close()
            
            if hasattr(self, 'error_bus_pub') and self.error_bus_pub:
                self.error_bus_pub.close()
            
            # Terminate ZMQ context
            if hasattr(self, 'context') and self.context:
                self.context.term()
            
            logger.info("Resources cleaned up")
        except Exception as e:
            logger.error(f"Error in cleanup: {str(e)}")

    def health_check(self):
        '''
        Performs a health check on the agent, returning a dictionary with its status.
        '''
        try:
            # Basic health check logic
            is_healthy = self.running  # Assume healthy unless a check fails
            
            # Check coordinator connection if needed
            if self.coordinator_socket is None:
                logger.warning("Coordinator socket not initialized")
                # Don't mark as unhealthy, it might still be initializing

            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {
                    "tasks_count": len(self.tasks.get('tasks', [])),
                    "reminders_count": len(self.tasks.get('reminders', [])),
                    "coordinator_connected": self.coordinator_socket is not None
                }
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name,
                "error": f"Health check failed with exception: {str(e)}"
            }

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = ProactiveAgent()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()