# File: main_pc_code/agents/goal_manager.py
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

# --- Path Setup ---
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

# --- Standardized Imports ---
from common.core.base_agent import BaseAgent
from common.utils.data_models import TaskDefinition, TaskResult, TaskStatus, ErrorSeverity

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
    """

    def __init__(self, **kwargs):
        super().__init__(name="GoalManager", port=DEFAULT_PORT, **kwargs)

        # --- State Management ---
        self.goals: Dict[str, Dict[str, Any]] = {}  # goal_id -> goal data
        self.tasks: Dict[str, TaskDefinition] = {} # task_id -> task definition
        self.task_results: Dict[str, Any] = {} # task_id -> result
        self.task_queue: List[Tuple[int, float, str]] = []  # (priority, timestamp, task_id)
        self.queue_lock = threading.Lock()

        # --- Downstream Services & Resilience ---
        self.downstream_services = ["ModelOrchestrator", "AutoGenFramework"] # Pwedeng idagdag ang iba pa
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._init_circuit_breakers()

        # --- Distributed Error Reporting ---
        self.error_bus_pub = self._init_error_bus()

        # --- Background Threads ---
        self._start_background_threads()
        logger.info("Unified GoalManager initialized successfully.")

    def _init_circuit_breakers(self):
        """Initializes Circuit Breakers for all downstream services."""
        for service in self.downstream_services:
            self.circuit_breakers[service] = CircuitBreaker(name=service)

    def _init_error_bus(self) -> Optional[zmq.Socket]:
        """Initializes the ZMQ PUB socket for the distributed error bus."""
        try:
            # (Ang logic para sa error bus ay pareho sa RequestCoordinator)
            return None # Placeholder
        except Exception:
            return None

    def _start_background_threads(self):
        """Starts all background threads for the agent."""
        threads = {
            "TaskProcessor": self._process_task_queue,
            "GoalMonitor": self._monitor_goals,
        }
        for name, target in threads.items():
            thread = threading.Thread(target=target, name=f"{self.name}-{name}", daemon=True)
            thread.start()
        logger.info(f"Started {len(threads)} background threads.")

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
            "list_goals": self.list_goals
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

        goal_id = f"goal-{uuid.uuid4()}"
        goal_info = {
            "id": goal_id,
            "description": goal_desc,
            "status": "pending",
            "tasks": [],
            "created_at": datetime.now().isoformat()
        }
        self.goals[goal_id] = goal_info
        logger.info(f"New goal set: {goal_id} - '{goal_desc[:50]}...'")

        # Start the breakdown process in a new thread to not block the caller
        breakdown_thread = threading.Thread(target=self._break_down_goal, args=(goal_id,))
        breakdown_thread.start()

        return {"status": "success", "goal_id": goal_id, "message": "Goal received and is being planned."}

    def get_goal_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        goal_id = data.get("goal_id")
        if not goal_id or goal_id not in self.goals:
            return {"status": "error", "message": "Goal not found."}
        return {"status": "success", "goal": self.goals[goal_id]}

    def list_goals(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "success", "goals": list(self.goals.values())}

    # ===================================================================
    #         PLANNING & EXECUTION (Pinagsamang logic)
    # ===================================================================

    def _break_down_goal(self, goal_id: str):
        """
        Uses an LLM to break down a goal into a sequence of tasks.
        (Logic mula sa GoalOrchestrator at MultiAgentSwarmManager)
        """
        goal_info = self.goals[goal_id]
        goal_info["status"] = "planning"
        logger.info(f"Breaking down goal {goal_id}...")

        # System prompt for decomposition (mula sa MultiAgentSwarmManager)
        prompt = f"""
        You are a planning AI. Break down the following high-level goal into a sequence of specific, executable tasks.
        For each task, define 'task_type' and 'description'.
        Goal: "{goal_info['description']}"
        Respond with a JSON list of task objects.
        """
        request = {"action": "generate_text", "prompt": prompt} # I-assume na ito ang API ng ModelOrchestrator

        response = self._resilient_send_request("ModelOrchestrator", request)

        if not response or response.get("status") != "success":
            goal_info["status"] = "failed"
            self.report_error("PlanningFailed", f"ModelOrchestrator failed to break down goal {goal_id}", ErrorSeverity.ERROR, goal_id=goal_id)
            return

        try:
            tasks_data = json.loads(response.get("result", "[]"))
            if not isinstance(tasks_data, list): raise ValueError("Response is not a list")

            for task_data in tasks_data:
                task = TaskDefinition(
                    task_id=f"task-{uuid.uuid4()}",
                    agent_id=self.name,
                    task_type=task_data.get("task_type", "unknown"),
                    description=task_data.get("description", ""),
                    priority=task_data.get("priority", 5),
                    status=TaskStatus.PENDING,
                    parameters=task_data.get("parameters", {})
                )
                self.tasks[task.task_id] = task
                goal_info["tasks"].append(task.task_id)
                with self.queue_lock:
                    heapq.heappush(self.task_queue, (task.priority, time.time(), task.task_id))

            goal_info["status"] = "queued"
            logger.info(f"Goal {goal_id} planned with {len(tasks_data)} tasks.")
        except (json.JSONDecodeError, ValueError) as e:
            goal_info["status"] = "failed"
            self.report_error("PlanningParseError", f"Failed to parse plan for goal {goal_id}: {e}", ErrorSeverity.ERROR, goal_id=goal_id)

    def _process_task_queue(self):
        """Continuously processes tasks from the priority queue."""
        while self.running:
            task_id = None
            with self.queue_lock:
                if self.task_queue:
                    _priority, _timestamp, task_id = heapq.heappop(self.task_queue)

            if task_id:
                self._execute_task(task_id)
            else:
                time.sleep(0.1)

    def _execute_task(self, task_id: str):
        """
        Executes a single task by dispatching it to the AutoGenFramework.
        (Logic mula sa MultiAgentSwarmManager)
        """
        task = self.tasks.get(task_id)
        if not task: return

        logger.info(f"Executing task {task_id}: {task.description}")
        task.status = TaskStatus.RUNNING
        self._update_goal_progress(task_id)

        request = {"action": "execute_task", "task": task.model_dump()}
        response = self._resilient_send_request("AutoGenFramework", request)

        if not response or response.get("status") != "success":
            task.status = TaskStatus.FAILED
            self.report_error("ExecutionFailed", f"AutoGenFramework failed to execute task {task_id}", ErrorSeverity.ERROR, task_id=task_id)
        else:
            result_data = response.get("result", {})
            self.task_results[task_id] = result_data
            task.status = TaskStatus.COMPLETED
            logger.info(f"Task {task_id} completed successfully.")

        self._update_goal_progress(task_id)

    # ===================================================================
    #         MONITORING & UTILITIES
    # ===================================================================

    def _update_goal_progress(self, task_id: str):
        """Updates the progress of a goal based on its tasks' statuses."""
        for goal_id, goal in self.goals.items():
            if task_id in goal.get("tasks", []):
                completed_tasks = sum(1 for tid in goal["tasks"] if self.tasks.get(tid, {}).status == TaskStatus.COMPLETED)
                total_tasks = len(goal["tasks"])
                goal["progress"] = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
                if completed_tasks == total_tasks:
                    goal["status"] = "completed"
                    logger.info(f"Goal {goal_id} completed!")
                    # Dito pwedeng i-trigger ang result synthesis
                break

    def _monitor_goals(self):
        """Periodically monitors the status of all active goals."""
        while self.running:
            # Pwedeng magdagdag ng logic para sa mga goal na nag-timeout
            time.sleep(60)

    def _resilient_send_request(self, agent_name: str, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """A resilient method to send requests using Circuit Breakers."""
        cb = self.circuit_breakers[agent_name]
        if not cb.allow_request():
            logger.warning(f"Request to {agent_name} blocked by open circuit.")
            return None
        try:
            response = self.send_request_to_agent(agent_name, request, timeout=ZMQ_REQUEST_TIMEOUT)
            cb.record_success()
            return response
        except Exception as e:
            cb.record_failure()
            self.report_error("ServiceCommunicationError", f"Failed to communicate with {agent_name}: {e}", ErrorSeverity.ERROR)
            return None

    def report_error(self, error_type: str, message: str, severity: ErrorSeverity, **kwargs):
        """Reports an error to the local logger and the distributed Error Bus."""
        # (Ang logic para sa error bus ay pareho sa RequestCoordinator)
        pass

if __name__ == '__main__':
    try:
        agent = GoalManager()
        agent.run()
    except KeyboardInterrupt:
        logger.info("GoalManager shutting down.")
    except Exception as e:
        logger.critical(f"GoalManager failed to start: {e}", exc_info=True)
    finally:
        if 'agent' in locals() and agent.running:
            agent.cleanup()