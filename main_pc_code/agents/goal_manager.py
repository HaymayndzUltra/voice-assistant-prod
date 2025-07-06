import sys
import os
import time
import logging
import threading
import uuid
import heapq
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, cast
import zmq
from pathlib import Path

# --- Path Setup ---
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

# --- Imports from Project ---
from src.core.base_agent import BaseAgent
from utils.service_discovery_client import get_service_address, register_service
from utils.env_loader import get_env
from src.network.secure_zmq import is_secure_zmq_enabled, configure_secure_client, configure_secure_server
# Corrected import path for data models
from main_pc_code.src.common.data_models import TaskDefinition, TaskResult, TaskStatus
from main_pc_code.agents.request_coordinator import CircuitBreaker

# --- Logging Setup ---
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'goal_manager.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('GoalManager')

# --- Constants ---
DEFAULT_PORT = 7005
ZMQ_REQUEST_TIMEOUT = 5000
BIND_ADDRESS = get_env('BIND_ADDRESS', '0.0.0.0')
SECURE_ZMQ = is_secure_zmq_enabled()

# --- GoalManager Class ---
class GoalManager(BaseAgent):
    def __init__(self, **kwargs):
        port = kwargs.get('port', DEFAULT_PORT)
        super().__init__(name="GoalManager", port=port, health_check_port=port + 1)
        self.context = zmq.Context()
        self._init_zmq_sockets()
        self.running = True
        self.goals: Dict[str, Dict[str, Any]] = {}
        self.tasks: Dict[str, TaskDefinition] = {}
        self.task_results: Dict[str, TaskResult] = {}
        self.available_agents: Dict[str, Any] = {}
        self.task_queue: List[Tuple[int, float, str]] = []  # Priority queue: (priority, timestamp, task_id)
        self.queue_lock = threading.Lock()
        
        # Initialize circuit breakers
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._init_circuit_breakers()
        
        self._register_service()
        self._start_threads()
        logger.info(f"GoalManager initialized, listening on tcp://{BIND_ADDRESS}:{self.port}")

    def _init_circuit_breakers(self):
        """Initialize circuit breakers for external services"""
        services = ["ModelOrchestrator", "AutoGenFramework"]
        for service in services:
            self.circuit_breakers[service] = CircuitBreaker(name=service)

    def _init_zmq_sockets(self):
        self.main_socket = self.context.socket(zmq.REP)
        if SECURE_ZMQ: configure_secure_server(self.main_socket)
        self.main_socket.bind(f"tcp://{BIND_ADDRESS}:{self.port}")
        self.model_orchestrator_socket = self._connect_to_service("ModelOrchestrator")
        self.autogen_socket = self._connect_to_service("AutoGenFramework")

    def _connect_to_service(self, service_name: str) -> Optional[zmq.Socket]:
        try:
            service_address = get_service_address(service_name)
            if service_address:
                socket = self.context.socket(zmq.REQ)
                if SECURE_ZMQ: configure_secure_client(socket)
                socket.connect(service_address)
                logger.info(f"Connected to {service_name} at {service_address}")
                return socket
            else:
                self.report_error("service_discovery_failure", f"Failed to discover {service_name}. Socket will be None.")
                return None
        except Exception as e:
            self.report_error("connection_failure", f"Error connecting to {service_name}: {e}")
            return None

    def _register_service(self):
        register_service(
            name=self.name,
            port=self.port,
            additional_info={"capabilities": ["goal_management", "swarm_coordination"]}
        )

    def _start_threads(self):
        threads = {
            "request_handler": self._handle_requests,
            "agent_discovery": self._discover_agents,
            "task_processor": self._process_tasks,
            "goal_monitor": self._monitor_goals,
        }
        for name, target in threads.items():
            thread = threading.Thread(target=target, daemon=True)
            thread.start()

    def _handle_requests(self):
        while self.running:
            try:
                message = self.main_socket.recv_json()
                if not isinstance(message, dict):
                    self.main_socket.send_json({"status": "error", "message": "Invalid request format, expected a JSON object."})
                    continue

                command = message.get('command')
                data = message.get('data')

                if command == 'set_goal' and isinstance(data, dict):
                    response = self.set_goal(data)
                elif command == 'get_goal_status' and isinstance(data, dict) and isinstance(data.get('goal_id'), str):
                    response = self.get_goal_status(data.get('goal_id', ''))
                elif command == 'update_task_status' and isinstance(data, dict):
                    goal_id = data.get('goal_id', '')
                    task_id = data.get('task_id', '')
                    status = data.get('status', '')
                    if isinstance(goal_id, str) and isinstance(task_id, str) and isinstance(status, str):
                        response = self.update_task_status(goal_id, task_id, status)
                    else:
                        response = {"status": "error", "message": "Invalid parameters for update_task_status"}
                elif command == 'list_goals':
                    response = self.list_active_goals()
                else:
                    response = {"status": "error", "message": f"Unknown or malformed command: {command}"}
                
                self.main_socket.send_json(response)
            except Exception as e:
                self.report_error("request_handler_error", f"Error in _handle_requests: {e}")
                if not self.main_socket.closed:
                    self.main_socket.send_json({"status": "error", "message": str(e)})

    def set_goal(self, goal_data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(goal_data, dict) or 'description' not in goal_data:
            return {"status": "error", "message": "Invalid goal format."}
        
        goal_id = str(uuid.uuid4())
        self.goals[goal_id] = {
            "id": goal_id,  # Add id to the goal info
            "goal": goal_data,
            "status": "pending",
            "progress": 0,
            "tasks": [],
            "created_at": datetime.now().isoformat()
        }
        logger.info(f"New goal set with ID: {goal_id}")
        self._break_down_goal(self.goals[goal_id])
        return {"status": "success", "goal_id": goal_id}

    def _break_down_goal(self, goal_info: Dict[str, Any]):
        # Check if ModelOrchestrator socket is available
        if not self.model_orchestrator_socket:
            self.report_error("service_unavailable", "ModelOrchestrator socket not available for goal breakdown")
            # Fallback to simulated tasks
            self._create_simulated_tasks(goal_info)
            return
            
        # Check if circuit breaker allows the request
        if not self.circuit_breakers["ModelOrchestrator"].allow_request():
            self.report_error("circuit_open", "ModelOrchestrator circuit breaker is open, using fallback")
            # Fallback to simulated tasks
            self._create_simulated_tasks(goal_info)
            return
            
        try:
            # Use BaseAgent's send_request_to_agent instead of direct socket calls
            request = {
                'action': 'break_down_goal',
                'goal': goal_info['goal']
            }
            
            # Send request using standardized helper
            response = self.send_request_to_agent("ModelOrchestrator", request)
            
            # Record success with circuit breaker
            self.circuit_breakers["ModelOrchestrator"].record_success()
            
            if response.get('status') == 'success' and isinstance(response.get('tasks'), list):
                tasks_data = response.get('tasks', [])
                for task_data in tasks_data:
                    if not isinstance(task_data, dict):
                        continue
                        
                    task_id = str(uuid.uuid4())
                    priority = task_data.get('priority', 5)  # Default priority 5 (medium)
                    
                    # Create task definition
                    task = TaskDefinition(
                        task_id=task_id,
                        goal_id=goal_info.get('id', ''),
                        agent_id="GoalManager",  # Required field
                        **task_data
                    )
                    
                    self.tasks[task_id] = task
                    goal_info['tasks'].append(task_id)
                    
                    # Use priority queue with heapq
                    with self.queue_lock:
                        heapq.heappush(self.task_queue, (priority, time.time(), task_id))
            else:
                self.report_error("invalid_response", f"Invalid response from ModelOrchestrator: {response}")
                self._create_simulated_tasks(goal_info)
                
        except Exception as e:
            # Record failure with circuit breaker
            self.circuit_breakers["ModelOrchestrator"].record_failure()
            self.report_error("goal_breakdown_error", f"Error in _break_down_goal: {e}")
            # Fallback to simulated tasks
            self._create_simulated_tasks(goal_info)

    def _create_simulated_tasks(self, goal_info: Dict[str, Any]):
        """Create simulated tasks when ModelOrchestrator is unavailable"""
        logger.info(f"Creating simulated tasks for goal: {goal_info['goal']['description']}")
        
        # Simulated tasks with priorities
        tasks_data = [
            {"task_type": "research", "description": "Research topic A", "priority": 3},
            {"task_type": "write", "description": "Write summary of topic A", "priority": 5},
        ]
        
        for task_data in tasks_data:
            task_id = str(uuid.uuid4())
            priority = task_data.pop('priority', 5)  # Extract priority and default to 5
            
            task = TaskDefinition(
                task_id=task_id, 
                goal_id=goal_info.get('id', ''), 
                agent_id="GoalManager",  # Set the agent_id field
                **task_data
            )
            
            self.tasks[task_id] = task
            goal_info['tasks'].append(task_id)
            
            # Use priority queue with heapq
            with self.queue_lock:
                heapq.heappush(self.task_queue, (priority, time.time(), task_id))

    def _discover_agents(self):
        while self.running:
            try:
                if not self.autogen_socket:
                    self.report_error("service_unavailable", "AutoGen socket not available. Agent discovery paused.")
                    time.sleep(60)  # Wait before retrying
                    continue

                # Check if circuit breaker allows the request
                if not self.circuit_breakers["AutoGenFramework"].allow_request():
                    logger.warning("AutoGenFramework circuit breaker is open, skipping agent discovery")
                    time.sleep(60)
                    continue
                    
                try:
                    # Use standardized request format
                    request = {"action": "list_agents"}
                    response = self.send_request_to_agent("AutoGenFramework", request)
                    
                    # Record success with circuit breaker
                    self.circuit_breakers["AutoGenFramework"].record_success()
                    
                    if isinstance(response, dict) and response.get('status') == 'success':
                        self.available_agents = response.get('agents', {})
                        logger.info(f"Discovered {len(self.available_agents)} agents")
                except Exception as e:
                    # Record failure with circuit breaker
                    self.circuit_breakers["AutoGenFramework"].record_failure()
                    self.report_error("agent_discovery_error", f"Error in agent discovery request: {e}")
                    
                time.sleep(300)
            except Exception as e:
                self.report_error("agent_discovery_error", f"Error in _discover_agents: {e}")
                time.sleep(60)

    def _process_tasks(self):
        while self.running:
            task_id = None
            with self.queue_lock:
                if self.task_queue:
                    # Use heapq to get highest priority task
                    _priority, _timestamp, task_id = heapq.heappop(self.task_queue)
            
            if task_id:
                self._execute_task(task_id)
            else:
                time.sleep(0.1)

    def _execute_task(self, task_id: str):
        if not self.autogen_socket:
            self.report_error("service_unavailable", f"Cannot execute task {task_id}: AutoGen socket is not connected.")
            if task_id in self.tasks:
                self.tasks[task_id].status = TaskStatus.FAILED
            return

        # Check if circuit breaker allows the request
        if not self.circuit_breakers["AutoGenFramework"].allow_request():
            logger.warning(f"AutoGenFramework circuit breaker is open, re-queueing task {task_id}")
            with self.queue_lock:
                # Re-queue with same priority but new timestamp
                task = self.tasks.get(task_id)
                if task:
                    heapq.heappush(self.task_queue, (task.priority, time.time(), task_id))
            return

        task = self.tasks.get(task_id)
        if not task: return
        
        agent_id = self._select_agent_for_task(task)
        if not agent_id:
            logger.warning(f"No suitable agent found for task {task_id}. Re-queueing.")
            with self.queue_lock:
                # Re-queue with lower priority to avoid constant retries
                heapq.heappush(self.task_queue, (task.priority + 1, time.time(), task_id))
            return

        try:
            task.status = TaskStatus.RUNNING  # Use the enum value
            
            # Use standardized request format
            request = {
                "action": "execute_task",
                "task": task.model_dump()
            }
            
            # Send request using BaseAgent helper
            response = self.send_request_to_agent("AutoGenFramework", request)
            
            # Record success with circuit breaker
            self.circuit_breakers["AutoGenFramework"].record_success()
            
            if response.get('status') == 'success' and response.get('result'):
                result = TaskResult.model_validate(response.get('result'))
                self.task_results[task_id] = result
                self.tasks[task_id].status = result.status
            else:
                self.tasks[task_id].status = TaskStatus.FAILED
                
            self._update_goal_progress(task_id)
        except Exception as e:
            # Record failure with circuit breaker
            self.circuit_breakers["AutoGenFramework"].record_failure()
            self.report_error("task_execution_error", f"Error in _execute_task: {e}")
            self.tasks[task_id].status = TaskStatus.FAILED

    def _select_agent_for_task(self, task: TaskDefinition) -> Optional[str]:
        for agent_id, meta in self.available_agents.items():
            if isinstance(meta, dict) and task.task_type in meta.get('capabilities', []):
                return agent_id
        return None

    def _update_goal_progress(self, task_id: str):
        for goal_id, goal_data in self.goals.items():
            if task_id in goal_data.get('tasks', []):
                total = len(goal_data['tasks'])
                completed = sum(1 for tid in goal_data['tasks'] if self.tasks.get(tid) and self.tasks[tid].status == TaskStatus.COMPLETED)
                goal_data['progress'] = (completed / total) * 100 if total > 0 else 0
                if completed == total:
                    goal_data['status'] = 'completed'
                logger.info(f"Goal {goal_id} progress: {goal_data['progress']:.2f}%")

    def _monitor_goals(self):
        while self.running:
            time.sleep(60)
            try:
                # Basic monitoring logic can be expanded here
                pass
            except Exception as e:
                self.report_error("goal_monitoring_error", f"Error in _monitor_goals: {e}")

    def get_goal_status(self, goal_id: str) -> Dict[str, Any]:
        if goal_id not in self.goals:
            return {"status": "error", "message": "Goal not found"}
        return {"status": "success", "goal_data": self.goals[goal_id]}

    def update_task_status(self, goal_id: str, task_id: str, status: str) -> Dict[str, Any]:
        if task_id not in self.tasks:
            return {"status": "error", "message": "Task not found"}
        try:
            self.tasks[task_id].status = TaskStatus(status)
            self._update_goal_progress(task_id)
            return {"status": "success"}
        except ValueError:
            return {"status": "error", "message": f"Invalid status: {status}"}

    def list_active_goals(self) -> Dict[str, Any]:
        return {"status": "success", "goals": self.goals}

    def health_check(self):
        circuit_status = {name: breaker.get_status() for name, breaker in self.circuit_breakers.items()}
        return {
            "status": "healthy" if self.running else "stopped",
            "uptime": time.time() - self.start_time,
            "active_goals": len(self.goals),
            "queued_tasks": len(self.task_queue),
            "circuit_breakers": circuit_status
        }

    def stop(self):
        self.running = False
        logger.info("Stopping GoalManager...")
        for sock in [self.main_socket, self.model_orchestrator_socket, self.autogen_socket]:
            if sock and not sock.closed:
                sock.close()
        self.context.term()
        logger.info("GoalManager stopped.")

    def run(self):
        self.start_time = time.time()
        logger.info("GoalManager is running...")
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='GoalManager Agent')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Port to bind to')
    args = parser.parse_args()
    agent = GoalManager(port=args.port)
    agent.run()