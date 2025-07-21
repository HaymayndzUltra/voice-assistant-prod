# File: main_pc_code/agents/goal_manager.py
from common.config_manager import get_service_ip, get_service_url, get_redis_url
#
# Ito ang FINAL at PINAHUSAY na bersyon ng GoalManager.
# Pinagsasama nito ang goal-setting ng GoalOrchestrator at ang
# task execution/swarm logic ng MultiAgentSwarmManager.

import sys
import os
import time
import logging
import threading
import uuid
import heapq
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import zmq  # Added for error bus


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'main_pc_code')))
from common.utils.path_env import get_path, join_path, get_file_path
# --- Path Setup ---
MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

# --- Standardized Imports ---
from common.core.base_agent import BaseAgent
from common.utils.data_models import TaskDefinition, TaskResult, TaskStatus, ErrorSeverity
from main_pc_code.agents.memory_client import MemoryClient

from common.config_manager import load_unified_config

# Load configuration at the module level
config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))


# --- Shared Utilities ---
# I-assume na ang CircuitBreaker ay nasa isang shared utility file
# Halimbawa: from common.utils.resilience import CircuitBreaker
# Para sa example, ilalagay ko muna ito dito.
class CircuitBreaker:
    """Isang self-contained utility para sa resilient service connections."""
    # (Ang buong code para sa CircuitBreaker class ay ilalagay dito, gaya ng sa RequestCoordinator)
    CLOSED, OPEN, HALF_OPEN = 'closed', 'open', 'half_open'
    def __init__(self, name: str, failure_threshold: int = 3, reset_timeout: int = 30):
        self.name, self.failure_threshold, self.reset_timeout = name, failure_threshold, reset_timeout
        self.state, self.failure_count, self.last_failure_time = self.CLOSED, 0, 0
        self._lock = threading.Lock()
        logging.info(f"Circuit Breaker initialized for service: {self.name}")
    def record_success(self):
        with self._lock:
            if self.state == self.HALF_OPEN: logging.info(f"Circuit for {self.name} is now CLOSED.")
            self.state, self.failure_count = self.CLOSED, 0
    def record_failure(self):
        with self._lock:
            self.failure_count += 1; self.last_failure_time = time.time()
            if self.state == self.HALF_OPEN or self.failure_count >= self.failure_threshold:
                if self.state != self.OPEN: logging.warning(f"Circuit for {self.name} has TRIPPED and is now OPEN.")
                self.state = self.OPEN
    def allow_request(self) -> bool:
        with self._lock:
            if self.state == self.OPEN:
                if time.time() - self.last_failure_time > self.reset_timeout:
                    self.state = self.HALF_OPEN; logging.info(f"Circuit for {self.name} is now HALF-OPEN.")
                    return True
                return False
            return True

# --- Logging Setup ---
logger = logging.getLogger('GoalManager')

# --- Constants ---
DEFAULT_PORT = 7005
ZMQ_REQUEST_TIMEOUT = 15000 # Mas mahabang timeout para sa LLM calls

# ===================================================================
#         ANG BAGONG UNIFIED GOAL MANAGER
# ===================================================================
class GoalManager(BaseAgent):
    """
    Manages high-level goals from inception to completion.
    - Decomposes goals into a plan of executable tasks.
    - Dispatches tasks to a swarm of specialized agents.
    - Monitors progress and synthesizes final results.
    - Uses central memory system for persistence.
    """

    def __init__(self, **kwargs):
        super().__init__(name="GoalManager", port=DEFAULT_PORT, **kwargs)

        # --- State Management ---
        self.goals: Dict[str, Dict[str, Any]] = {}  # goal_id -> goal data (in-memory cache)
        self.tasks: Dict[str, TaskDefinition] = {} # task_id -> task definition (in-memory cache)
        self.task_results: Dict[str, Any] = {} # task_id -> result (in-memory cache)
        self.task_queue: List[Tuple[int, float, str]] = []  # (priority, timestamp, task_id)
        self.queue_lock = threading.Lock()

        # --- Memory Client for Persistence ---
        self.memory_client = MemoryClient()
        self.memory_client.set_agent_id(self.name)
        
        # --- Downstream Services & Resilience ---
        self.downstream_services = ["ModelOrchestrator", "AutoGenFramework"] # Pwedeng idagdag ang iba pa
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._init_circuit_breakers()

        # --- Distributed Error Reporting ---
        self.error_bus_port = 7150
        self.error_bus_host = get_service_ip("pc2")
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)

        # --- Background Threads ---
        self._start_background_threads()
        logger.info("Unified GoalManager initialized successfully.")

        # --- Load Active Goals from Memory ---
        self._load_active_goals()

    def _init_circuit_breakers(self):
        """Initializes Circuit Breakers for all downstream services."""
        for service in self.downstream_services:
            self.circuit_breakers[service] = CircuitBreaker(name=service)

    def _start_background_threads(self):
        """Starts all background threads for the agent."""
        threads = {
            "TaskProcessor": self._process_task_queue,
            "GoalMonitor": self._monitor_goals,
        }
        for name, target in threads.items():
            thread = threading.Thread(target=target, name=f"{self.name}-{name}", daemon=True)
            thread.start()
            # Register thread for graceful shutdown
            if not hasattr(self, "_background_threads"):
                self._background_threads = []
            self._background_threads.append(thread)
        logger.info(f"Started {len(threads)} background threads.")
        
    def _load_active_goals(self):
        """Load active goals from the memory system."""
        try:
            # Search for active goals
            response = self.memory_client.search_memory(
                query="status:active OR status:pending OR status:planning",
                memory_type="goal",
                limit=100
            )
            
            if response.get("status") == "success":
                results = response.get("results", [])
                for goal_data in results:
                    goal_id = goal_data.get("memory_id")
                    if goal_id:
                        self.goals[goal_id] = goal_data
                        
                        # Load associated tasks
                        self._load_tasks_for_goal(goal_id)
                        
                logger.info(f"Loaded {len(self.goals)} active goals from memory")
            else:
                logger.warning("Failed to load active goals from memory")
        except Exception as e:
            self.report_error("memory_load_error", f"Failed to load goals: {str(e)}", ErrorSeverity.WARNING)

    def _load_tasks_for_goal(self, goal_id: str):
        """Load tasks associated with a goal."""
        try:
            # Get all tasks for this goal
            response = self.memory_client.get_children(
                parent_id=goal_id,
                limit=100,
                sort_field="created_at",
                sort_order="asc"
            )
            
            if response.get("status") == "success":
                tasks = response.get("results", [])
                for task_data in tasks:
                    task_id = task_data.get("memory_id")
                    if task_id:
                        self.tasks[task_id] = TaskDefinition(**task_data)
                        
                        # If task is pending, add to queue
                        if task_data.get("status") == "pending":
                            priority = task_data.get("priority", 5)
                            timestamp = time.time()
                            with self.queue_lock:
                                heapq.heappush(self.task_queue, (priority, timestamp, task_id))
                
                logger.info(f"Loaded {len(tasks)} tasks for goal {goal_id}")
        except Exception as e:
            self.report_error("memory_load_error", f"Failed to load tasks for goal {goal_id}: {str(e)}", ErrorSeverity.WARNING)

    # ===================================================================
    #         CORE API (Mula sa GoalOrchestrator)
    # ===================================================================

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handles incoming requests from other agents."""
        action = request.get("action")
        data = request.get("data", {})

        handlers = {
            "set_goal": self.set_goal,
            "get_goal_status": self.get_goal_status,
            "list_goals": self.list_goals,
            "search_goals": self.search_goals
        }
        handler = handlers.get(action)

        if handler:
            return handler(data)
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    def set_goal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Receives a new goal, breaks it down, and queues the tasks."""
        goal_desc = data.get("description")
        if not goal_desc:
            return {"status": "error", "message": "Goal description is required."}

        # Create goal in memory system
        goal_metadata = {
            "description": goal_desc,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "user_id": data.get("user_id", "default"),
            "priority": data.get("priority", 5)
        }
        
        try:
            # Store goal in memory system
            response = self.memory_client.add_memory(
                content=goal_desc,
                memory_type="goal",
                memory_tier="medium",  # Goals persist longer than regular memories
                importance=0.8,        # Goals are important
                metadata=goal_metadata,
                tags=["goal", "planning"]
            )
            
            if response.get("status") == "success":
                goal_id = response.get("memory_id")
                
                # Add to local cache
                self.goals[goal_id] = {
                    "id": goal_id,
                    "description": goal_desc,
                    "status": "pending",
                    "tasks": [],
                    "created_at": datetime.now().isoformat(),
                    **goal_metadata
                }
                
                logger.info(f"New goal set: {goal_id} - '{goal_desc[:50]}...'")

                # Start the breakdown process in a new thread to not block the caller
                breakdown_thread = threading.Thread(target=self._break_down_goal, args=(goal_id,))
                breakdown_thread.start()

                return {"status": "success", "goal_id": goal_id, "message": "Goal received and is being planned."}
            else:
                error_msg = response.get("message", "Failed to store goal in memory system")
                self.report_error("goal_creation_error", error_msg, ErrorSeverity.ERROR)
                return {"status": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"Exception creating goal: {str(e)}"
            self.report_error("goal_creation_exception", error_msg, ErrorSeverity.ERROR)
            return {"status": "error", "message": error_msg}

    def get_goal_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        key = "goal_id"
        goal_id = str(data[key]) if key in data and data[key] is not None else ""
        if not goal_id:
            return {"status": "error", "message": "Goal ID is required."}
            
        # Check local cache first
        if goal_id in self.goals:
            return {"status": "success", "goal": self.goals[goal_id]}
            
        # If not in cache, try to get from memory system
        try:
            response = self.memory_client.get_memory(memory_id=goal_id)
            
            if response.get("status") == "success":
                goal_data = response.get("memory", {})
                
                # Add to local cache
                self.goals[goal_id] = goal_data
                
                # Get associated tasks
                tasks_response = self.memory_client.get_children(parent_id=goal_id)
                if tasks_response.get("status") == "success":
                    goal_data["tasks"] = tasks_response.get("results", [])
                
                return {"status": "success", "goal": goal_data}
            else:
                return {"status": "error", "message": "Goal not found."}
        except Exception as e:
            error_msg = f"Exception getting goal status: {str(e)}"
            self.report_error("goal_status_exception", error_msg, ErrorSeverity.WARNING)
            return {"status": "error", "message": error_msg}

    def list_goals(self, data: Dict[str, Any]) -> Dict[str, Any]:
        limit = data.get("limit", 20)
        status = data.get("status", None)
        
        try:
            query = ""
            if status:
                query = f"status:{status}"
                
            response = self.memory_client.search_memory(
                query=query,
                memory_type="goal",
                limit=limit
            )
            
            if response.get("status") == "success":
                goals = response.get("results", [])
                
                # Update local cache
                for goal in goals:
                    goal_id = goal.get("memory_id")
                    if goal_id:
                        self.goals[goal_id] = goal
                
                return {"status": "success", "goals": goals}
            else:
                # Fallback to local cache
                goals = list(self.goals.values())
                if status:
                    goals = [g for g in goals if g.get("status") == status]
                return {"status": "success", "goals": goals[:limit]}
        except Exception as e:
            error_msg = f"Exception listing goals: {str(e)}"
            self.report_error("list_goals_exception", error_msg, ErrorSeverity.WARNING)
            
            # Fallback to local cache
            goals = list(self.goals.values())
            if status:
                goals = [g for g in goals if g.get("status") == status]
            return {"status": "success", "goals": goals[:limit]}
            
    def search_goals(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Search goals based on query."""
        query = data.get("query", "")
        limit = data.get("limit", 10)
        
        if not query:
            return {"status": "error", "message": "Search query is required."}
            
        try:
            # Try semantic search first
            try:
                response = self.memory_client.semantic_search(
                    query=query,
                    k=limit
                )
                
                if response.get("status") == "success" and response.get("results"):
                    # Filter for goals only
                    goals = [r for r in response.get("results", []) if r.get("memory_type") == "goal"]
                    return {"status": "success", "goals": goals}
            except Exception as e:
                logger.warning(f"Semantic search failed, falling back to text search: {e}")
            
            # Fall back to text search
            response = self.memory_client.search_memory(
                query=query,
                memory_type="goal",
                limit=limit
            )
            
            if response.get("status") == "success":
                goals = response.get("results", [])
                return {"status": "success", "goals": goals}
            else:
                return {"status": "error", "message": "Search failed."}
        except Exception as e:
            error_msg = f"Exception searching goals: {str(e)}"
            self.report_error("search_goals_exception", error_msg, ErrorSeverity.WARNING)
            return {"status": "error", "message": error_msg}

    # ===================================================================
    #         PLANNING & EXECUTION (Pinagsamang logic)
    # ===================================================================

    def _break_down_goal(self, goal_id: str):
        """
        Uses an LLM to break down a goal into a sequence of tasks.
        Robust error handling, status update, and retry logic.
        """
        goal_info = self.goals[goal_id]
        goal_info["status"] = "planning"
        
        # Update goal status in memory
        self._update_goal_status(goal_id, "planning")
        
        logger.info(f"Breaking down goal {goal_id}...")

        prompt = f"""
        You are a planning AI. Break down the following high-level goal into a sequence of specific, executable tasks.
        For each task, define 'task_type' and 'description'.
        Goal: "{goal_info['description']}"
        Respond with a JSON list of task objects.
        """
        request = {"action": "generate_text", "prompt": prompt}

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                response = self._resilient_send_request("ModelOrchestrator", request)
                if not response or response.get("status") != "success":
                    raise Exception(f"Failed to get response: {response}")

                task_list = json.loads(response.get("result", "[]"))
                logger.info(f"Goal {goal_id} broken down into {len(task_list)} tasks.")

                # Create tasks in memory and queue them
                for i, task_data in enumerate(task_list):
                    task_id = f"task-{uuid.uuid4()}"
                    priority = 5  # Default priority
                    
                    task = {
                        "id": task_id,
                        "goal_id": goal_id,
                        "description": task_data.get("description", ""),
                        "task_type": task_data.get("task_type", "general"),
                        "status": TaskStatus.PENDING.value,
                        "priority": priority,
                        "sequence": i,
                        "created_at": datetime.now().isoformat()
                    }
                    
                    # Store task in memory system
                    task_response = self.memory_client.add_memory(
                        content=task_data.get("description", ""),
                        memory_type="task",
                        parent_id=goal_id,  # Link to parent goal
                        memory_tier="short",
                        importance=0.6,
                        metadata={
                            "task_type": task_data.get("task_type", "general"),
                            "status": TaskStatus.PENDING.value,
                            "priority": priority,
                            "sequence": i
                        },
                        tags=["task", task_data.get("task_type", "general")]
                    )
                    
                    if task_response.get("status") == "success":
                        task_id = task_response.get("memory_id")
                        task["id"] = task_id
                        
                        # Add to local cache
                        self.tasks[task_id] = TaskDefinition(**task)
                        goal_info["tasks"].append(task_id)
                        
                        # Add to task queue
                        with self.queue_lock:
                            heapq.heappush(self.task_queue, (priority, time.time(), task_id))
                    else:
                        logger.error(f"Failed to store task in memory: {task_response.get('message')}")

                # Update goal status
                goal_info["status"] = "active"
                self._update_goal_status(goal_id, "active")
                break
            except Exception as e:
                logger.error(f"Error breaking down goal {goal_id} (attempt {attempt+1}/{max_retries+1}): {e}")
                if attempt == max_retries:
                    goal_info["status"] = "error"
                    goal_info["error"] = str(e)
                    self._update_goal_status(goal_id, "error", {"error": str(e)})
                    self.report_error("goal_breakdown_error", f"Failed to break down goal {goal_id}: {e}", ErrorSeverity.ERROR)
                time.sleep(2 ** attempt)  # Exponential backoff

    def _update_goal_status(self, goal_id: str, status: str, additional_data: Dict[str, Any] = None):
        """Update goal status in memory system."""
        try:
            update_data = {"status": status}
            if additional_data:
                update_data.update(additional_data)
                
            response = self.memory_client.update_memory(
                memory_id=goal_id,
                update_payload={"metadata": update_data}
            )
            
            if response.get("status") != "success":
                logger.warning(f"Failed to update goal status: {response.get('message')}")
        except Exception as e:
            logger.error(f"Error updating goal status: {e}")

    def _process_task_queue(self):
        """Background thread that processes the task queue."""
        while True:
            try:
                with self.queue_lock:
                    if self.task_queue:
                        _, _, task_id = heapq.heappop(self.task_queue)
                        threading.Thread(target=self._execute_task, args=(task_id,)).start()
                time.sleep(1)  # Prevent CPU spin
            except Exception as e:
                logger.error(f"Error in task queue processing: {e}")
                time.sleep(5)  # Back off on error

    def _execute_task(self, task_id: str):
        """Executes a task by sending it to the appropriate agent."""
        if task_id not in self.tasks:
            logger.warning(f"Task {task_id} not found in tasks dict.")
            return

        task = self.tasks[task_id]
        logger.info(f"Executing task {task_id}: {task.description[:50]}...")

        # Update task status
        task.status = TaskStatus.RUNNING
        self._update_task_status(task_id, TaskStatus.RUNNING.value)

        try:
            # Determine which agent should handle this task based on task_type
            agent_map = {
                "code": "CodeGenerator",
                "research": "WebAssistant",
                "reasoning": "ModelOrchestrator",
                "general": "ModelOrchestrator"
            }
            agent = agent_map.get(task.task_type, "ModelOrchestrator")
            
            # Prepare request based on task type
            request = {
                "action": "execute_task",
                "task": task.to_dict()
            }
            
            # Send request to appropriate agent
            response = self._resilient_send_request(agent, request)
            
            if response and response.get("status") == "success":
                result = response.get("result", {})
                self.task_results[task_id] = result
                task.status = TaskStatus.COMPLETED
                self._update_task_status(task_id, TaskStatus.COMPLETED.value, {"result": result})
                logger.info(f"Task {task_id} completed successfully.")
            else:
                error_msg = "Failed to execute task" if not response else response.get("message", "Unknown error")
                task.status = TaskStatus.FAILED
                self._update_task_status(task_id, TaskStatus.FAILED.value, {"error": error_msg})
                logger.error(f"Task {task_id} failed: {error_msg}")
                self.report_error("task_execution_error", f"Task {task_id} failed: {error_msg}", ErrorSeverity.WARNING)
        except Exception as e:
            task.status = TaskStatus.FAILED
            self._update_task_status(task_id, TaskStatus.FAILED.value, {"error": str(e)})
            logger.error(f"Error executing task {task_id}: {e}")
            self.report_error("task_execution_exception", f"Error executing task {task_id}: {e}", ErrorSeverity.WARNING)
        finally:
            # Update goal progress
            self._update_goal_progress(task_id)

    def _update_task_status(self, task_id: str, status: str, additional_data: Dict[str, Any] = None):
        """Update task status in memory system."""
        try:
            update_data = {"status": status}
            if additional_data:
                update_data.update(additional_data)
                
            response = self.memory_client.update_memory(
                memory_id=task_id,
                update_payload={"metadata": update_data}
            )
            
            if response.get("status") != "success":
                logger.warning(f"Failed to update task status: {response.get('message')}")
        except Exception as e:
            logger.error(f"Error updating task status: {e}")

    def _update_goal_progress(self, task_id: str):
        """Updates the goal progress when a task is completed."""
        task = self.tasks.get(task_id)
        if not task:
            return
            
        goal_id = task.goal_id
        goal = self.goals.get(goal_id)
        if not goal:
            return
            
        # Get all tasks for this goal
        try:
            response = self.memory_client.get_children(parent_id=goal_id)
            
            if response.get("status") == "success":
                tasks = response.get("results", [])
                
                # Check if all tasks are completed
                all_completed = all(t.get("status") == TaskStatus.COMPLETED.value for t in tasks)
                any_failed = any(t.get("status") == TaskStatus.FAILED.value for t in tasks)
                
                if all_completed:
                    goal["status"] = "completed"
                    self._update_goal_status(goal_id, "completed")
                    logger.info(f"Goal {goal_id} completed successfully.")
                elif any_failed:
                    # Some tasks failed but we continue with others
                    if goal["status"] != "error":
                        goal["status"] = "partial"
                        self._update_goal_status(goal_id, "partial")
                        logger.warning(f"Goal {goal_id} has some failed tasks.")
        except Exception as e:
            logger.error(f"Error updating goal progress: {e}")

    def _monitor_goals(self):
        """Background thread that monitors goal progress."""
        while True:
            try:
                # This could be enhanced to check for stalled goals, retry failed tasks, etc.
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in goal monitoring: {e}")
                time.sleep(60)  # Back off on error

    def _resilient_send_request(self, agent_name: str, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a request to another agent with circuit breaker protection."""
        circuit = self.circuit_breakers.get(agent_name)
        if circuit and not circuit.allow_request():
            logger.warning(f"Circuit open for {agent_name}, request rejected.")
            return None

        try:
            # Implement actual request sending logic here
            # For now, this is just a placeholder
            if agent_name == "ModelOrchestrator":
                # Simulate a successful response for demonstration
                return {"status": "success", "result": '[{"task_type": "general", "description": "Analyze requirements"}]'}
            return {"status": "error", "message": "Agent not available"}
        except Exception as e:
            if circuit:
                circuit.record_failure()
            logger.error(f"Error sending request to {agent_name}: {e}")
            return None

    def _get_health_status(self) -> dict:
        """Return health status information."""
        # Get base health status from parent class
        base_status = super()._get_health_status()

        # Add GoalManager-specific health fields
        base_status.update({
            'service': self.__class__.__name__,
            'uptime_seconds': int(time.time() - self.start_time) if hasattr(self, 'start_time') else 0,
            'goal_count': len(self.goals),
            'task_queue_size': len(self.task_queue),
            'status': 'HEALTHY'
        })
        return base_status

    def report_error(self, error_type: str, message: str, severity: ErrorSeverity, **kwargs):
        """Report an error to the central error bus."""
        try:
            error_data = {
                "timestamp": time.time(),
                "agent": self.name,
                "error_type": error_type,
                "message": message,
                "severity": severity.value,
                **kwargs
            }
            self.error_bus_pub.send_string(f"ERROR:{json.dumps(error_data)}")
            logger.error(f"{error_type}: {message}")
        except Exception as e:
            logger.error(f"Failed to report error to error bus: {e}")
            
    def cleanup(self):
        """Clean up resources before shutdown."""
        if hasattr(self, 'error_bus_pub') and self.error_bus_pub:
            self.error_bus_pub.close()
        super().cleanup()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(join_path("logs", "goal_manager.log")),
            logging.StreamHandler()
        ]
    )
    
    try:
        agent = GoalManager()
        agent.run()
    except KeyboardInterrupt:
        logger.info("GoalManager shutting down")
    except Exception as e:
        logger.critical(f"GoalManager failed to start: {e}", exc_info=True)
    finally:
        if 'agent' in locals() and hasattr(agent, 'cleanup'):
            agent.cleanup()
