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
from utils.config_parser import parse_agent_args

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Remove argparse and use dynamic argument parser
args = parse_agent_args()

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

class GoalOrchestratorAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        """Initialize the GoalOrchestratorAgent with ZMQ sockets."""
        # Use port from command line args if not provided
        self.port = port if port is not None else getattr(args, 'port', 7000)
        if self.port is None:
            raise ValueError("Port must be provided either through constructor or command line arguments")
            
        super().__init__(port=self.port, name="Goalorchestratoragent")
        
        # BaseAgent has already created and bound the main REP socket (self.socket)
        # Reuse the existing ZMQ context from BaseAgent
        self.context = self.context  # clarity: context inherited from BaseAgent

        # Note: Removed redundant socket binding logic to avoid double-binding conflicts.
        
        # REQ socket for UnifiedPlanningAgent
        self.planning_socket = self.context.socket(zmq.REQ)
        self.planning_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.planning_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.planning_socket.connect(f"tcp://{getattr(args, 'host', 'localhost')}:5625")  # UnifiedPlanningAgent
        
        # REQ socket for PerformanceLoggerAgent
        self.performance_socket = self.context.socket(zmq.REQ)
        self.performance_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.performance_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.performance_socket.connect(f"tcp://{getattr(args, 'host', 'localhost')}:5632")  # PerformanceLoggerAgent
        
        # Store active goals and their tasks
        self.active_goals = {}
        
        # Start monitoring thread
        self.running = True
        self.monitor_thread = Thread(target=self._monitor_goals)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info(f"GoalOrchestratorAgent initialized on port {self.port}")
    
    def _log_performance(self, action: str, duration: float, metadata: Dict[str, Any] = None):
        """Log performance metrics to PerformanceLoggerAgent."""
        try:
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
        self.running = False
        self.monitor_thread.join()
        
        self.socket.close()
        self.planning_socket.close()
        self.performance_socket.close()
        self.context.term()

if __name__ == '__main__':
    agent = GoalOrchestratorAgent(port=getattr(args, 'port', 7000))
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop()