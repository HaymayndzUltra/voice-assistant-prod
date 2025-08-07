"""Scheduler client adapter for ModelOps Coordinator."""

import json
import time
import threading
import uuid
from typing import Dict, Optional, Any, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import requests

from ..core.schemas import Config
from ..core.errors import ModelOpsError


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SchedulerProtocol(Enum):
    """Supported scheduler protocols."""
    HTTP_REST = "http_rest"
    KUBERNETES = "kubernetes"
    SLURM = "slurm"
    CUSTOM = "custom"


@dataclass
class ScheduledTask:
    """Scheduled task representation."""
    task_id: str
    task_type: str
    priority: int
    resource_requirements: Dict[str, Any]
    payload: Dict[str, Any]
    status: TaskStatus
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    worker_id: Optional[str] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class SchedulerClientAdapter:
    """
    Scheduler client adapter for external task scheduling coordination.
    
    This adapter enables the ModelOps Coordinator to integrate with external
    scheduling systems like Kubernetes, SLURM, or custom task schedulers.
    """
    
    def __init__(self, scheduler_endpoint: str, protocol: str = "http_rest",
                 client_id: Optional[str] = None, auth_token: Optional[str] = None,
                 poll_interval: float = 10.0):
        """
        Initialize scheduler client adapter.
        
        Args:
            scheduler_endpoint: Scheduler service endpoint
            protocol: Scheduler protocol type
            client_id: Client identifier
            auth_token: Authentication token
            poll_interval: Task status polling interval
        """
        self.scheduler_endpoint = scheduler_endpoint.rstrip('/')
        self.protocol = SchedulerProtocol(protocol)
        self.client_id = client_id or f"moc-client-{uuid.uuid4().hex[:8]}"
        self.auth_token = auth_token
        self.poll_interval = poll_interval
        
        # Task tracking
        self._tasks: Dict[str, ScheduledTask] = {}
        self._tasks_lock = threading.RLock()
        
        # Background polling
        self._poll_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Status callbacks
        self._status_callbacks: List[Callable] = []
        
        # HTTP session for REST protocol
        self._session: Optional[requests.Session] = None
        
        # Initialize client
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize scheduler client."""
        if self.protocol == SchedulerProtocol.HTTP_REST:
            self._session = requests.Session()
            
            # Set authentication headers
            if self.auth_token:
                self._session.headers.update({
                    'Authorization': f'Bearer {self.auth_token}',
                    'Content-Type': 'application/json',
                    'X-Client-ID': self.client_id
                })
            
            # Test connection
            self._test_connection()
        
        # Start background polling
        self._start_polling()
    
    def _test_connection(self):
        """Test connection to scheduler."""
        try:
            if self.protocol == SchedulerProtocol.HTTP_REST:
                response = self._session.get(
                    f"{self.scheduler_endpoint}/health",
                    timeout=10.0
                )
                response.raise_for_status()
        except Exception as e:
            raise ModelOpsError(f"Failed to connect to scheduler: {e}", "SCHEDULER_CONNECTION_ERROR")
    
    def _start_polling(self):
        """Start background task status polling."""
        self._poll_thread = threading.Thread(
            target=self._polling_loop,
            name="SchedulerPoller",
            daemon=True
        )
        self._poll_thread.start()
    
    def _polling_loop(self):
        """Background polling loop for task status updates."""
        while not self._shutdown_event.wait(self.poll_interval):
            try:
                self._poll_task_status()
            except Exception as e:
                # Log error but continue polling
                self._notify_error("polling_error", str(e))
    
    def _poll_task_status(self):
        """Poll scheduler for task status updates."""
        with self._tasks_lock:
            active_tasks = [
                task for task in self._tasks.values()
                if task.status in [TaskStatus.PENDING, TaskStatus.SCHEDULED, TaskStatus.RUNNING]
            ]
        
        for task in active_tasks:
            try:
                status_update = self._get_task_status(task.task_id)
                if status_update:
                    self._update_task_status(task.task_id, status_update)
            except Exception as e:
                # Log error for individual task but continue
                pass
    
    def submit_inference_task(self, model_name: str, prompt: str, 
                             priority: int = 5, resource_requirements: Optional[Dict] = None,
                             **kwargs) -> str:
        """
        Submit inference task to scheduler.
        
        Args:
            model_name: Name of the model
            prompt: Inference prompt
            priority: Task priority (1-10, higher is more urgent)
            resource_requirements: Required resources
            **kwargs: Additional inference parameters
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        
        payload = {
            'task_type': 'inference',
            'model_name': model_name,
            'prompt': prompt,
            'parameters': kwargs
        }
        
        resource_req = resource_requirements or {
            'cpu_cores': 1,
            'memory_mb': 2048,
            'gpu_required': True,
            'estimated_duration_minutes': 5
        }
        
        task = ScheduledTask(
            task_id=task_id,
            task_type='inference',
            priority=priority,
            resource_requirements=resource_req,
            payload=payload,
            status=TaskStatus.PENDING
        )
        
        # Submit to scheduler
        self._submit_task_to_scheduler(task)
        
        # Store locally
        with self._tasks_lock:
            self._tasks[task_id] = task
        
        return task_id
    
    def submit_model_load_task(self, model_name: str, model_path: str,
                              priority: int = 3, resource_requirements: Optional[Dict] = None) -> str:
        """
        Submit model loading task to scheduler.
        
        Args:
            model_name: Name of the model
            model_path: Path to model file
            priority: Task priority
            resource_requirements: Required resources
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        
        payload = {
            'task_type': 'model_load',
            'model_name': model_name,
            'model_path': model_path
        }
        
        resource_req = resource_requirements or {
            'cpu_cores': 2,
            'memory_mb': 4096,
            'gpu_required': True,
            'storage_gb': 10,
            'estimated_duration_minutes': 15
        }
        
        task = ScheduledTask(
            task_id=task_id,
            task_type='model_load',
            priority=priority,
            resource_requirements=resource_req,
            payload=payload,
            status=TaskStatus.PENDING
        )
        
        # Submit to scheduler
        self._submit_task_to_scheduler(task)
        
        # Store locally
        with self._tasks_lock:
            self._tasks[task_id] = task
        
        return task_id
    
    def submit_learning_task(self, job_type: str, model_name: str, dataset_path: str,
                           priority: int = 2, resource_requirements: Optional[Dict] = None,
                           parameters: Optional[Dict] = None) -> str:
        """
        Submit learning task to scheduler.
        
        Args:
            job_type: Type of learning job
            model_name: Target model name
            dataset_path: Path to training dataset
            priority: Task priority
            resource_requirements: Required resources
            parameters: Learning parameters
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        
        payload = {
            'task_type': 'learning',
            'job_type': job_type,
            'model_name': model_name,
            'dataset_path': dataset_path,
            'parameters': parameters or {}
        }
        
        resource_req = resource_requirements or {
            'cpu_cores': 4,
            'memory_mb': 8192,
            'gpu_required': True,
            'gpu_memory_mb': 16384,
            'storage_gb': 50,
            'estimated_duration_minutes': 120
        }
        
        task = ScheduledTask(
            task_id=task_id,
            task_type='learning',
            priority=priority,
            resource_requirements=resource_req,
            payload=payload,
            status=TaskStatus.PENDING
        )
        
        # Submit to scheduler
        self._submit_task_to_scheduler(task)
        
        # Store locally
        with self._tasks_lock:
            self._tasks[task_id] = task
        
        return task_id
    
    def _submit_task_to_scheduler(self, task: ScheduledTask):
        """Submit task to external scheduler."""
        if self.protocol == SchedulerProtocol.HTTP_REST:
            self._submit_via_rest(task)
        elif self.protocol == SchedulerProtocol.KUBERNETES:
            self._submit_via_kubernetes(task)
        elif self.protocol == SchedulerProtocol.SLURM:
            self._submit_via_slurm(task)
        else:
            raise ModelOpsError(f"Unsupported scheduler protocol: {self.protocol}", "UNSUPPORTED_PROTOCOL")
    
    def _submit_via_rest(self, task: ScheduledTask):
        """Submit task via REST API."""
        try:
            submission_data = {
                'task_id': task.task_id,
                'task_type': task.task_type,
                'priority': task.priority,
                'client_id': self.client_id,
                'resource_requirements': task.resource_requirements,
                'payload': task.payload,
                'submitted_at': datetime.utcnow().isoformat()
            }
            
            response = self._session.post(
                f"{self.scheduler_endpoint}/tasks",
                json=submission_data,
                timeout=30.0
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Update task status based on response
            if result.get('status') == 'accepted':
                task.status = TaskStatus.SCHEDULED
                task.scheduled_at = datetime.utcnow()
            else:
                task.status = TaskStatus.FAILED
                task.error_message = result.get('error', 'Submission failed')
                
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = f"Submission error: {e}"
            raise ModelOpsError(f"Failed to submit task via REST: {e}", "SUBMISSION_ERROR")
    
    def _submit_via_kubernetes(self, task: ScheduledTask):
        """Submit task via Kubernetes API."""
        # This would integrate with Kubernetes API to create jobs/pods
        # For now, implement as placeholder
        raise ModelOpsError("Kubernetes integration not implemented", "NOT_IMPLEMENTED")
    
    def _submit_via_slurm(self, task: ScheduledTask):
        """Submit task via SLURM scheduler."""
        # This would use SLURM REST API or command-line tools
        # For now, implement as placeholder
        raise ModelOpsError("SLURM integration not implemented", "NOT_IMPLEMENTED")
    
    def _get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get task status from scheduler."""
        if self.protocol == SchedulerProtocol.HTTP_REST:
            return self._get_status_via_rest(task_id)
        else:
            return None
    
    def _get_status_via_rest(self, task_id: str) -> Optional[Dict]:
        """Get task status via REST API."""
        try:
            response = self._session.get(
                f"{self.scheduler_endpoint}/tasks/{task_id}",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return None
    
    def _update_task_status(self, task_id: str, status_update: Dict):
        """Update local task status from scheduler response."""
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            
            # Update status
            new_status = status_update.get('status')
            if new_status:
                try:
                    task.status = TaskStatus(new_status)
                except ValueError:
                    pass  # Unknown status, keep current
            
            # Update timestamps
            if status_update.get('started_at'):
                task.started_at = datetime.fromisoformat(status_update['started_at'])
            
            if status_update.get('completed_at'):
                task.completed_at = datetime.fromisoformat(status_update['completed_at'])
            
            # Update worker assignment
            if status_update.get('worker_id'):
                task.worker_id = status_update['worker_id']
            
            # Update result or error
            if task.status == TaskStatus.COMPLETED:
                task.result = status_update.get('result', {})
            elif task.status == TaskStatus.FAILED:
                task.error_message = status_update.get('error_message', 'Task failed')
        
        # Notify callbacks
        self._notify_task_status_change(task_id, task.status)
    
    def get_task_status(self, task_id: str) -> Optional[ScheduledTask]:
        """Get status of a specific task."""
        with self._tasks_lock:
            return self._tasks.get(task_id)
    
    def list_tasks(self, status_filter: Optional[TaskStatus] = None) -> List[ScheduledTask]:
        """List all tasks, optionally filtered by status."""
        with self._tasks_lock:
            tasks = list(self._tasks.values())
            
            if status_filter:
                tasks = [task for task in tasks if task.status == status_filter]
            
            return sorted(tasks, key=lambda t: t.scheduled_at or datetime.min, reverse=True)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task."""
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if not task or task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return False
        
        try:
            # Cancel via scheduler
            if self.protocol == SchedulerProtocol.HTTP_REST:
                response = self._session.delete(
                    f"{self.scheduler_endpoint}/tasks/{task_id}",
                    timeout=10.0
                )
                response.raise_for_status()
            
            # Update local status
            with self._tasks_lock:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.utcnow()
            
            self._notify_task_status_change(task_id, TaskStatus.CANCELLED)
            return True
            
        except Exception as e:
            self._notify_error("cancel_error", f"Failed to cancel task {task_id}: {e}")
            return False
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get scheduler status and statistics."""
        try:
            if self.protocol == SchedulerProtocol.HTTP_REST:
                response = self._session.get(
                    f"{self.scheduler_endpoint}/status",
                    timeout=10.0
                )
                response.raise_for_status()
                scheduler_status = response.json()
            else:
                scheduler_status = {'status': 'unknown', 'protocol': self.protocol.value}
            
            # Add local task statistics
            with self._tasks_lock:
                status_counts = {}
                for status in TaskStatus:
                    status_counts[status.value] = len([
                        task for task in self._tasks.values() if task.status == status
                    ])
            
            return {
                'scheduler': scheduler_status,
                'local_tasks': {
                    'total': len(self._tasks),
                    'status_counts': status_counts
                },
                'connection': {
                    'protocol': self.protocol.value,
                    'endpoint': self.scheduler_endpoint,
                    'client_id': self.client_id
                }
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'connection': {
                    'protocol': self.protocol.value,
                    'endpoint': self.scheduler_endpoint,
                    'status': 'error'
                }
            }
    
    def register_status_callback(self, callback: Callable):
        """Register callback for task status updates."""
        self._status_callbacks.append(callback)
    
    def unregister_status_callback(self, callback: Callable):
        """Unregister status callback."""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)
    
    def _notify_task_status_change(self, task_id: str, new_status: TaskStatus):
        """Notify callbacks of task status change."""
        for callback in self._status_callbacks:
            try:
                callback({
                    'type': 'task_status_change',
                    'task_id': task_id,
                    'status': new_status.value,
                    'timestamp': datetime.utcnow().isoformat()
                })
            except Exception:
                pass
    
    def _notify_error(self, error_type: str, message: str):
        """Notify callbacks of errors."""
        for callback in self._status_callbacks:
            try:
                callback({
                    'type': 'error',
                    'error_type': error_type,
                    'message': message,
                    'timestamp': datetime.utcnow().isoformat()
                })
            except Exception:
                pass
    
    def shutdown(self):
        """Shutdown scheduler client."""
        # Signal shutdown
        self._shutdown_event.set()
        
        # Wait for polling thread
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=5.0)
        
        # Close HTTP session
        if self._session:
            self._session.close()
        
        # Clear callbacks
        self._status_callbacks.clear()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()