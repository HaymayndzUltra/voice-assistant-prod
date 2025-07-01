import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
MAIN_PC_CODE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if MAIN_PC_CODE not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE)

from src.core.base_agent import BaseAgent
import zmq
import json
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from threading import Thread
from main_pc_code.utils.config_parser import parse_agent_args
from utils.service_discovery_client import discover_service, register_service, get_service_address
from utils.env_loader import get_env
from src.network.secure_zmq import is_secure_zmq_enabled, configure_secure_client, configure_secure_server

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Remove argparse and use dynamic argument parser
_agent_args = parse_agent_args()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('goal_orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Get bind address from environment variables with default to 0.0.0.0 for Docker compatibility
BIND_ADDRESS = get_env('BIND_ADDRESS', '0.0.0.0')

# Secure ZMQ configuration
SECURE_ZMQ = is_secure_zmq_enabled()

class GoalOrchestratorAgent(BaseAgent):
    def __init__(self, **kwargs):
        """Initialize the GoalOrchestratorAgent with ZMQ sockets."""
        super().__init__()
        self.zmq_timeout = self.config.getint('goal_orchestrator.zmq_timeout_ms', 5000)
        bind_address_ip = self.config.get('network.bind_address', '0.0.0.0')
        self.fallback_ports = {
            "UnifiedPlanningAgent": self.config.getint('dependencies.unified_planning_agent_port', 5625),
            "PerformanceLoggerAgent": self.config.getint('dependencies.performance_logger_agent_port', 5632)
        }
        self.port = self.config.getint('goal_orchestrator.port', 7000)
        
        # Initialize ZMQ context
        self.context = zmq.Context()
        
        # Main REP socket for handling requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, self.zmq_timeout)
        self.socket.setsockopt(zmq.SNDTIMEO, self.zmq_timeout)
        
        # Apply secure ZMQ if enabled
        if SECURE_ZMQ:
            self.socket = configure_secure_server(self.socket)
            logger.info("Secure ZMQ enabled for GoalOrchestratorAgent")
        
        # Bind to address using BIND_ADDRESS for Docker compatibility
        bind_address = f"tcp://{bind_address_ip}:{self.port}"
        self.socket.bind(bind_address)
        logger.info(f"GoalOrchestratorAgent socket bound to {bind_address}")
        
        # Register with service discovery
        self._register_service()
        
        # Connect to required services using service discovery
        self.planning_socket = self._create_service_socket("UnifiedPlanningAgent")
        self.performance_socket = self._create_service_socket("PerformanceLoggerAgent")
        
        # Store active goals and their tasks
        self.active_goals = {}
        
        # Start monitoring thread
        self.running = True
        self.start_time = time.time()
        self.monitor_thread = Thread(target=self._monitor_goals)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info(f"GoalOrchestratorAgent initialized on port {self.port}")
    
    def _get_health_status(self):
        # Basic health check.
        return {'status': 'ok', 'active_goals': len(self.active_goals)}
    
    def _register_service(self):
        """Register this agent with the service discovery system"""
        try:
            register_result = register_service(
                name="GoalOrchestratorAgent",
                port=self.port,
                additional_info={
                    "capabilities": ["goal_management", "task_orchestration"],
                    "status": "running"
                }
            )
            if register_result and register_result.get("status") == "SUCCESS":
                logger.info("Successfully registered with service discovery")
            else:
                logger.warning(f"Service registration failed: {register_result.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error registering service: {e}")
    
    def _create_service_socket(self, service_name):
        """Create a socket connected to a service using service discovery"""
        try:
            socket = self.context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, self.zmq_timeout)
            socket.setsockopt(zmq.SNDTIMEO, self.zmq_timeout)
            
            # Apply secure ZMQ if enabled
            if SECURE_ZMQ:
                socket = configure_secure_client(socket)
            
            # Get service address from service discovery
            service_address = get_service_address(service_name)
            if service_address:
                socket.connect(service_address)
                logger.info(f"Connected to {service_name} at {service_address}")
                return socket
            else:
                # Fallback to default ports if service discovery fails
                fallback_port = self.fallback_ports.get(service_name)
                if fallback_port:
                    fallback_address = f"tcp://{bind_address_ip}:{fallback_port}"
                    socket.connect(fallback_address)
                    logger.warning(f"Could not discover {service_name}, using fallback address: {fallback_address}")
                    return socket
                else:
                    logger.error(f"Failed to connect to {service_name}: No service discovery or fallback available")
                    return None
        except Exception as e:
            logger.error(f"Error creating socket for {service_name}: {str(e)}")
            return None
    
    def _log_performance(self, action: str, duration: float, metadata: Dict[str, Any] = None):
        """Log performance metrics to PerformanceLoggerAgent."""
        try:
            if not self.performance_socket:
                logger.warning("Performance socket not available, skipping performance logging")
                return
                
            self.performance_socket.send_json({
                'action': 'log_metric',
                'agent': 'GoalOrchestratorAgent',
                'metric': {
                    'action': action,
                    'duration': duration,
                    'timestamp': datetime.now().isoformat(),
                    'metadata': metadata or {}
                }
            })
            _ = self.performance_socket.recv_json()
        except Exception as e:
            logger.error(f"Error logging performance: {str(e)}")
    
    def _break_down_goal(self, goal: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Request task breakdown from UnifiedPlanningAgent."""
        try:
            if not self.planning_socket:
                logger.error("Planning socket not available, cannot break down goal")
                return []
                
            start_time = time.time()
            
            self.planning_socket.send_json({
                'action': 'break_down_goal',
                'goal': goal
            })
            
            response = self.planning_socket.recv_json()
            
            duration = time.time() - start_time
            self._log_performance('break_down_goal', duration, {'goal_id': goal.get('id')})
            
            if response['status'] == 'success':
                return response['tasks']
            else:
                logger.error(f"Failed to break down goal: {response.get('message', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"Error breaking down goal: {str(e)}")
            return []
    
    def _track_goal_progress(self, goal_id: str):
        """Update goal and task status based on progress."""
        if goal_id not in self.active_goals:
            return
        
        goal = self.active_goals[goal_id]
        total_tasks = len(goal['tasks'])
        completed_tasks = sum(1 for task in goal['tasks'] if task['status'] == 'completed')
        
        # Update goal status
        if completed_tasks == total_tasks:
            goal['status'] = 'completed'
            goal['completion_time'] = datetime.now().isoformat()
        elif completed_tasks > 0:
            goal['status'] = 'in_progress'
        
        # Calculate progress percentage
        goal['progress'] = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
    
    def _monitor_goals(self):
        """Periodically monitor active goals and their progress."""
        while self.running:
            try:
                for goal_id in list(self.active_goals.keys()):
                    self._track_goal_progress(goal_id)
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error monitoring goals: {str(e)}")
                time.sleep(300)  # Wait 5 minutes before retrying
    
    def set_goal(self, goal: Dict[str, Any]) -> Dict[str, Any]:
        """Set a new high-level goal and break it down into tasks."""
        try:
            start_time = time.time()
            
            # Generate goal ID if not provided
            if 'id' not in goal:
                goal['id'] = f"goal_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Break down goal into tasks
            tasks = self._break_down_goal(goal)
            
            if not tasks:
                return {
                    'status': 'error',
                    'message': 'Failed to break down goal into tasks'
                }
            
            # Store goal and tasks
            self.active_goals[goal['id']] = {
                'goal': goal,
                'tasks': tasks,
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'progress': 0
            }
            
            duration = time.time() - start_time
            self._log_performance('set_goal', duration, {'goal_id': goal['id']})
            
            return {
                'status': 'success',
                'goal_id': goal['id'],
                'tasks': tasks
            }
            
        except Exception as e:
            logger.error(f"Error setting goal: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_goal_status(self, goal_id: str) -> Dict[str, Any]:
        """Get the current status of a goal and its tasks."""
        if goal_id not in self.active_goals:
            return {
                'status': 'error',
                'message': 'Goal not found'
            }
        
        goal_data = self.active_goals[goal_id]
        self._track_goal_progress(goal_id)
        
        return {
            'status': 'success',
            'goal': goal_data['goal'],
            'tasks': goal_data['tasks'],
            'progress': goal_data['progress'],
            'status': goal_data['status']
        }
    
    def update_task_status(self, goal_id: str, task_id: str, status: str) -> Dict[str, Any]:
        """Update the status of a specific task within a goal."""
        if goal_id not in self.active_goals:
            return {
                'status': 'error',
                'message': 'Goal not found'
            }
        
        goal_data = self.active_goals[goal_id]
        task_found = False
        
        for task in goal_data['tasks']:
            if task['id'] == task_id:
                task['status'] = status
                task['updated_at'] = datetime.now().isoformat()
                task_found = True
                break
        
        if not task_found:
            return {
                'status': 'error',
                'message': 'Task not found'
            }
        
        self._track_goal_progress(goal_id)
        
        return {
            'status': 'success',
            'message': 'Task status updated'
        }
    
    def list_active_goals(self) -> Dict[str, Any]:
        """List all active goals and their current status."""
        return {
            'status': 'success',
            'goals': [
                {
                    'id': goal_id,
                    'goal': data['goal'],
                    'status': data['status'],
                    'progress': data['progress']
                }
                for goal_id, data in self.active_goals.items()
            ]
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action')
        
        # Respond to orchestrator health checks
        if action in ('health_check', 'health', 'ping'):
            return {
                'status': 'ok',
                'message': 'GoalOrchestratorAgent healthy',
                'timestamp': datetime.now().isoformat()
            }

        if action == 'set_goal':
            return self.set_goal(request['goal'])
            
        elif action == 'get_goal_status':
            return self.get_goal_status(request['goal_id'])
            
        elif action == 'update_task_status':
            return self.update_task_status(
                request['goal_id'],
                request['task_id'],
                request['status']
            )
            
        elif action == 'list_active_goals':
            return self.list_active_goals()
            
        else:
            return {
                'status': 'error',
                'message': f'Unknown action: {action}'
            }
    
    def run(self):
        """Main loop for handling requests."""
        logger.info("GoalOrchestratorAgent started")
        
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
        logger.info("Stopping GoalOrchestratorAgent...")
        self.running = False
        
        # Join the monitor thread with timeout to avoid hanging
        if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
            if self.monitor_thread.is_alive():
                logger.warning("Monitor thread did not terminate gracefully")
        
        # Close sockets in a try-finally block to ensure they're all closed
        try:
            if hasattr(self, 'socket'):
                self.socket.close()
                logger.debug("Closed main socket")
            
            if hasattr(self, 'planning_socket') and self.planning_socket:
                self.planning_socket.close()
                logger.debug("Closed planning socket")
            
            if hasattr(self, 'performance_socket') and self.performance_socket:
                self.performance_socket.close()
                logger.debug("Closed performance socket")
        except Exception as e:
            logger.error(f"Error during socket cleanup: {e}")
        finally:
            # Terminate ZMQ context
            if hasattr(self, 'context'):
                self.context.term()
                logger.debug("Terminated ZMQ context")
        
        logger.info("GoalOrchestratorAgent stopped successfully")

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = GoalOrchestratorAgent()
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