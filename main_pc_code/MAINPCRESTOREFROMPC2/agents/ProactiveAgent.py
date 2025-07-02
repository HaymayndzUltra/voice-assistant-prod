import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
MAIN_PC_CODE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if MAIN_PC_CODE not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE)

from main_pc_code.src.core.base_agent import BaseAgent
import zmq
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
import threading
from main_pc_code.utils.config_parser import parse_agent_args

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
args = parse_agent_args()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('proactive_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProactiveAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        """Initialize the ProactiveAgent with ZMQ sockets."""
        config_port = None
        # Try to load from config if needed
        try:
            config_path = os.path.join('config', 'system_config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8-sig') as f:
                    config = json.load(f)
                if 'agents' in config and 'proactive_agent' in config['agents']:
                    config_port = config['agents']['proactive_agent'].get('port')
                elif 'agents' in config and 'memory_decay' in config['agents']:
                    # fallback: use memory_decay port if that's the intended mapping
                    config_port = config['agents']['memory_decay'].get('port')
        except Exception as e:
            logger.warning(f"Could not load port from config: {e}")
        # Port selection logic
        if port is not None:
            self.port = port
        elif hasattr(args, 'port') and args.port is not None:
            self.port = int(args.port)
        elif config_port is not None:
            self.port = int(config_port)
        else:
            self.port = 5624  # fallback default
            
        super().__init__(port=self.port, name="Proactiveagent", strict_port=True)
        
        self.context = zmq.Context()
        
        # Main REP socket for handling requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://*:{self.port}")
        
        # Store tasks and reminders
        self.tasks_file = "tasks.json"
        self.tasks = self._load_tasks()
        
        # Initialize coordinator socket (will be set up in async initialization)
        self.coordinator_socket = None
        
        # Start monitoring thread
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_tasks)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info(f"ProactiveAgent initialized on port {self.port}")
    
    def _perform_initialization(self):
        """Initialize agent components asynchronously."""
        try:
            # Set up coordinator socket
            self.coordinator_socket = self.context.socket(zmq.REQ)
            self.coordinator_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.coordinator_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.coordinator_socket.connect(f"tcp://{getattr(args, 'host', 'localhost')}:5621")  # CoordinatorAgent
            logger.info("Coordinator socket initialized successfully")
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
                
            # Send task to CoordinatorAgent
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
                
            # Send reminder to CoordinatorAgent
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
        
        if self.coordinator_socket:
            self.coordinator_socket.linger = 0
            self.coordinator_socket.close()
        
        super().cleanup()

if __name__ == '__main__':
    agent = ProactiveAgent(port=args.port)
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop()