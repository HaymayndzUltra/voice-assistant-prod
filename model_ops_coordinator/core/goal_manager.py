"""Goal management and priority queue operations for ModelOps Coordinator."""

import uuid
import threading
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from queue import PriorityQueue
from dataclasses import dataclass

from .errors import GoalError
from .learning import LearningModule
from .telemetry import Telemetry
from .schemas import Config, GoalPriority


@dataclass
class Goal:
    """Goal representation with priority ordering."""
    
    def __init__(self, goal_id: str, title: str, description: str, 
                 priority: GoalPriority, metadata: Optional[Dict[str, Any]] = None):
        self.goal_id = goal_id
        self.title = title
        self.description = description
        self.priority = priority
        self.metadata = metadata or {}
        self.status = "pending"
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.progress = 0.0
        self.error_message: Optional[str] = None
        self.result: Optional[Dict[str, Any]] = None
        self.learning_job_ids: List[str] = []
    
    def __lt__(self, other):
        """Priority comparison for queue ordering."""
        priority_order = {
            GoalPriority.CRITICAL: 0,
            GoalPriority.HIGH: 1,
            GoalPriority.MEDIUM: 2,
            GoalPriority.LOW: 3
        }
        
        # Primary sort by priority
        self_order = priority_order.get(self.priority, 999)
        other_order = priority_order.get(other.priority, 999)
        
        if self_order != other_order:
            return self_order < other_order
        
        # Secondary sort by creation time (earlier first)
        return self.created_at < other.created_at


class GoalModule:
    """Goal management system with priority queue and execution tracking."""
    
    def __init__(self, config: Config, learning: LearningModule, telemetry: Telemetry):
        """Initialize goal management module."""
        self.config = config
        self.learning = learning
        self.telemetry = telemetry
        self._lock = threading.RLock()
        
        # Goal storage
        self._goals: Dict[str, Goal] = {}
        self._goal_queue: PriorityQueue = PriorityQueue()
        self._active_goals: Dict[str, Goal] = {}
        
        # Execution management
        self._goal_threads: Dict[str, threading.Thread] = {}
        self._shutdown_event = threading.Event()
        
        # Start goal processor
        self._processor_thread = threading.Thread(
            target=self._goal_processor_loop,
            name="GoalProcessor",
            daemon=True
        )
        self._processor_thread.start()
    
    def create_goal(self, title: str, description: str, priority: str = "medium",
                   metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new goal and add it to the priority queue.
        
        Args:
            title: Goal title
            description: Goal description
            priority: Priority level (low, medium, high, critical)
            metadata: Additional metadata
            
        Returns:
            Goal ID
            
        Raises:
            GoalError: If goal creation fails
        """
        try:
            # Validate priority
            try:
                goal_priority = GoalPriority(priority)
            except ValueError:
                raise GoalError("invalid_priority", f"Invalid priority: {priority}")
            
            # Create goal
            goal_id = str(uuid.uuid4())
            goal = Goal(
                goal_id=goal_id,
                title=title,
                description=description,
                priority=goal_priority,
                metadata=metadata
            )
            
            with self._lock:
                self._goals[goal_id] = goal
                self._goal_queue.put(goal)
            
            # Update metrics
            self._update_goal_metrics()
            
            return goal_id
            
        except Exception as e:
            if isinstance(e, GoalError):
                raise
            else:
                raise GoalError("goal_creation_failed", str(e))
    
    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID."""
        with self._lock:
            return self._goals.get(goal_id)
    
    def list_goals(self, status_filter: Optional[str] = None) -> List[Goal]:
        """List all goals, optionally filtered by status."""
        with self._lock:
            goals = list(self._goals.values())
            
            if status_filter:
                goals = [g for g in goals if g.status == status_filter]
            
            # Sort by priority and creation time
            return sorted(goals, key=lambda g: (g.priority.value, g.created_at))
    
    def update_goal_progress(self, goal_id: str, progress: float, 
                           status: Optional[str] = None) -> bool:
        """Update goal progress and optionally status."""
        with self._lock:
            if goal_id not in self._goals:
                return False
            
            goal = self._goals[goal_id]
            goal.progress = max(0.0, min(1.0, progress))
            
            if status:
                goal.status = status
                
                if status == "completed":
                    goal.completed_at = datetime.utcnow()
                    goal.progress = 1.0
                    
                    # Record completion metrics
                    completion_time = (goal.completed_at - goal.created_at).total_seconds()
                    self.telemetry.record_goal_completion(
                        goal.priority.value, 
                        completion_time
                    )
            
            # Update metrics
            self._update_goal_metrics()
            
            return True
    
    def cancel_goal(self, goal_id: str) -> bool:
        """Cancel a goal and any associated learning jobs."""
        with self._lock:
            if goal_id not in self._goals:
                return False
            
            goal = self._goals[goal_id]
            
            if goal.status in ["completed", "cancelled", "failed"]:
                return False  # Already finished
            
            # Cancel associated learning jobs
            for job_id in goal.learning_job_ids:
                self.learning.cancel_job(job_id)
            
            # Update goal status
            goal.status = "cancelled"
            goal.completed_at = datetime.utcnow()
            goal.error_message = "Goal cancelled by user"
            
            # Remove from active goals
            if goal_id in self._active_goals:
                del self._active_goals[goal_id]
            
            # Update metrics
            self._update_goal_metrics()
            
            return True
    
    def delete_goal(self, goal_id: str) -> bool:
        """Delete a goal (only if not active)."""
        with self._lock:
            if goal_id not in self._goals:
                return False
            
            goal = self._goals[goal_id]
            
            if goal.status in ["running", "pending"]:
                # Must cancel first
                return False
            
            # Remove goal
            del self._goals[goal_id]
            
            # Update metrics
            self._update_goal_metrics()
            
            return True
    
    def _goal_processor_loop(self):
        """Main goal processing loop."""
        while not self._shutdown_event.is_set():
            try:
                # Check if we can process more goals
                with self._lock:
                    active_count = len(self._active_goals)
                    max_active = self.config.goals.max_active_goals
                
                if active_count >= max_active:
                    time.sleep(1.0)
                    continue
                
                # Get next goal from queue (blocking with timeout)
                try:
                    goal = self._goal_queue.get(timeout=1.0)
                except Exception:
                    continue  # Timeout, check shutdown
                
                # Start processing goal
                self._start_goal_execution(goal)
                
            except Exception:
                self.telemetry.record_error("goal_processor_error", "goals")
                time.sleep(1.0)
    
    def _start_goal_execution(self, goal: Goal):
        """Start executing a goal."""
        with self._lock:
            if goal.goal_id in self._active_goals:
                return  # Already active
            
            goal.status = "running"
            goal.started_at = datetime.utcnow()
            self._active_goals[goal.goal_id] = goal
        
        # Start execution thread
        goal_thread = threading.Thread(
            target=self._execute_goal,
            args=(goal,),
            name=f"Goal-{goal.goal_id[:8]}",
            daemon=True
        )
        
        self._goal_threads[goal.goal_id] = goal_thread
        goal_thread.start()
        
        # Update metrics
        self._update_goal_metrics()
    
    def _execute_goal(self, goal: Goal):
        """Execute a goal (simulation)."""
        start_time = time.time()
        
        try:
            # Simulate goal execution based on type/description
            self._simulate_goal_execution(goal)
            
            # Goal completed successfully
            goal.status = "completed"
            goal.completed_at = datetime.utcnow()
            goal.progress = 1.0
            goal.result = {
                "execution_time": time.time() - start_time,
                "success": True,
                "message": f"Goal '{goal.title}' completed successfully"
            }
            
            # Record completion metrics
            completion_time = (goal.completed_at - goal.created_at).total_seconds()
            self.telemetry.record_goal_completion(goal.priority.value, completion_time)
            
        except Exception as e:
            # Goal failed
            goal.status = "failed"
            goal.completed_at = datetime.utcnow()
            goal.error_message = str(e)
            goal.result = {
                "execution_time": time.time() - start_time,
                "success": False,
                "error": str(e)
            }
            
            self.telemetry.record_error("goal_execution_failed", "goals")
        
        finally:
            # Cleanup
            with self._lock:
                if goal.goal_id in self._active_goals:
                    del self._active_goals[goal.goal_id]
                
                if goal.goal_id in self._goal_threads:
                    del self._goal_threads[goal.goal_id]
            
            # Update metrics
            self._update_goal_metrics()
    
    def _simulate_goal_execution(self, goal: Goal):
        """
        Simulate goal execution.
        
        In production, this would:
        1. Parse goal description and metadata
        2. Determine required actions (model training, inference, etc.)
        3. Submit learning jobs if needed
        4. Monitor progress and coordinate sub-tasks
        5. Report completion or failure
        """
        # Simulate different execution patterns based on goal content
        execution_steps = self._analyze_goal_requirements(goal)
        
        for i, step in enumerate(execution_steps):
            # Check for cancellation
            if goal.status == "cancelled":
                raise Exception("Goal cancelled")
            
            # Simulate step execution
            if step["type"] == "learning_job":
                # Submit a learning job
                job_id = self.learning.submit_job(
                    step["job_type"],
                    step["model_name"],
                    step["dataset_path"],
                    step.get("parameters", {})
                )
                goal.learning_job_ids.append(job_id)
                
                # Wait for job completion (simplified)
                self._wait_for_learning_job(job_id, goal)
                
            elif step["type"] == "model_evaluation":
                # Simulate model evaluation
                time.sleep(step.get("duration", 1.0) * 0.01)  # Scaled down
                
            elif step["type"] == "data_processing":
                # Simulate data processing
                time.sleep(step.get("duration", 0.5) * 0.01)  # Scaled down
            
            # Update progress
            progress = (i + 1) / len(execution_steps)
            goal.progress = progress
            
            # Simulate occasional failures (0.5% chance per step)
            import random
            if random.random() < 0.005:
                raise Exception(f"Simulated failure in step: {step['type']}")
    
    def _analyze_goal_requirements(self, goal: Goal) -> List[Dict[str, Any]]:
        """
        Analyze goal to determine required execution steps.
        
        This is a simplified simulation. In production, this would use
        natural language processing or structured goal definitions.
        """
        steps = []
        
        # Parse goal description for keywords
        description_lower = goal.description.lower()
        
        if "train" in description_lower or "fine-tune" in description_lower:
            steps.append({
                "type": "learning_job",
                "job_type": "fine_tune",
                "model_name": goal.metadata.get("model_name", "default-model"),
                "dataset_path": goal.metadata.get("dataset_path", "/datasets/default.json"),
                "parameters": goal.metadata.get("training_params", {})
            })
        
        if "evaluate" in description_lower or "test" in description_lower:
            steps.append({
                "type": "model_evaluation",
                "duration": 2.0
            })
        
        if "process" in description_lower or "prepare" in description_lower:
            steps.append({
                "type": "data_processing",
                "duration": 1.0
            })
        
        # Default execution if no specific steps identified
        if not steps:
            steps.append({
                "type": "generic_task",
                "duration": 3.0
            })
        
        return steps
    
    def _wait_for_learning_job(self, job_id: str, goal: Goal):
        """Wait for a learning job to complete (simplified)."""
        max_wait = 300  # 5 minutes max wait
        start_time = time.time()
        
        while (time.time() - start_time) < max_wait:
            if goal.status == "cancelled":
                return
            
            job = self.learning.get_job_status(job_id)
            if job is None:
                break
            
            if job.status in ["completed", "failed", "cancelled"]:
                if job.status == "failed":
                    raise Exception(f"Learning job failed: {job.error_message}")
                break
            
            time.sleep(1.0)  # Check every second
    
    def get_goal_statistics(self) -> Dict[str, Any]:
        """Get goal statistics for metrics and monitoring."""
        with self._lock:
            status_counts = {}
            priority_counts = {}
            
            # Initialize counters
            for status in ["pending", "running", "completed", "failed", "cancelled"]:
                status_counts[status] = 0
            
            for priority in GoalPriority:
                priority_counts[priority.value] = {}
                for status in ["pending", "running", "completed", "failed", "cancelled"]:
                    priority_counts[priority.value][status] = 0
            
            # Count goals
            for goal in self._goals.values():
                status_counts[goal.status] += 1
                priority_counts[goal.priority.value][goal.status] += 1
            
            # Update telemetry
            self.telemetry.update_goals(priority_counts)
            
            return {
                'total_goals': len(self._goals),
                'active_goals': len(self._active_goals),
                'status_counts': status_counts,
                'priority_counts': priority_counts,
                'queue_size': self._goal_queue.qsize(),
                'max_active': self.config.goals.max_active_goals
            }
    
    def _update_goal_metrics(self):
        """Update goal metrics in telemetry."""
        self.get_goal_statistics()  # This updates telemetry
    
    def shutdown(self):
        """Shutdown goal management module."""
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel all active goals
        with self._lock:
            for goal in self._active_goals.values():
                goal.status = "cancelled"
                goal.error_message = "System shutdown"
        
        # Wait for processor thread
        if self._processor_thread.is_alive():
            self._processor_thread.join(timeout=5.0)
        
        # Wait for goal threads
        max_wait = 30.0  # 30 seconds
        start_time = time.time()
        
        while self._goal_threads and (time.time() - start_time) < max_wait:
            time.sleep(0.1)