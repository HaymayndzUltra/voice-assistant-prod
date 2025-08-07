"""Local worker adapter for ModelOps Coordinator."""

import time
import threading
from typing import Dict, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..core.kernel import Kernel
from ..core.schemas import Config, InferenceRequest, InferenceResponse
from ..core.errors import ModelOpsError


@dataclass
class WorkerStatus:
    """Worker status information."""
    worker_id: str
    status: str  # online, offline, busy, error
    last_heartbeat: datetime
    active_tasks: int
    total_completed: int
    total_errors: int
    capabilities: Dict[str, Any]
    system_info: Dict[str, Any]


class LocalWorkerAdapter:
    """
    Local worker adapter providing direct kernel integration.
    
    This adapter enables the ModelOps Coordinator to function as a worker
    in distributed scenarios while maintaining direct access to the kernel.
    """
    
    def __init__(self, kernel: Kernel, worker_id: Optional[str] = None, 
                 heartbeat_interval: float = 30.0):
        """
        Initialize local worker adapter.
        
        Args:
            kernel: ModelOps Coordinator kernel instance
            worker_id: Unique worker identifier
            heartbeat_interval: Heartbeat frequency in seconds
        """
        self.kernel = kernel
        self.worker_id = worker_id or f"local-worker-{int(time.time())}"
        self.heartbeat_interval = heartbeat_interval
        
        # Worker state
        self._status = "initializing"
        self._last_heartbeat = datetime.utcnow()
        self._active_tasks = 0
        self._total_completed = 0
        self._total_errors = 0
        self._shutdown_event = threading.Event()
        
        # Task tracking
        self._task_lock = threading.RLock()
        self._running_tasks: Dict[str, threading.Thread] = {}
        
        # Heartbeat thread
        self._heartbeat_thread: Optional[threading.Thread] = None
        
        # Status callbacks
        self._status_callbacks: list[Callable] = []
        
        # Initialize worker
        self._initialize_worker()
    
    def _initialize_worker(self):
        """Initialize worker and start background services."""
        try:
            # Verify kernel health
            if not self.kernel.is_healthy():
                raise ModelOpsError("Kernel is not healthy", "KERNEL_UNHEALTHY")
            
            # Start heartbeat
            self._start_heartbeat()
            
            # Set status to online
            self._status = "online"
            
            # Notify status change
            self._notify_status_change()
            
        except Exception as e:
            self._status = "error"
            self.kernel.metrics.record_error("worker_init_failed", "local_worker")
            raise
    
    def _start_heartbeat(self):
        """Start heartbeat thread."""
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name=f"Heartbeat-{self.worker_id}",
            daemon=True
        )
        self._heartbeat_thread.start()
    
    def _heartbeat_loop(self):
        """Heartbeat loop to maintain worker status."""
        while not self._shutdown_event.wait(self.heartbeat_interval):
            try:
                self._send_heartbeat()
            except Exception as e:
                self.kernel.metrics.record_error("heartbeat_failed", "local_worker")
                # Continue heartbeat loop even if individual heartbeat fails
    
    def _send_heartbeat(self):
        """Send heartbeat with current status."""
        self._last_heartbeat = datetime.utcnow()
        
        # Update status based on kernel health
        if not self.kernel.is_healthy():
            self._status = "error"
        elif self._active_tasks > 0:
            self._status = "busy"
        else:
            self._status = "online"
        
        # Get system status for heartbeat
        system_status = self.kernel.get_system_status()
        
        # Notify callbacks with heartbeat data
        heartbeat_data = {
            'worker_id': self.worker_id,
            'timestamp': self._last_heartbeat.isoformat(),
            'status': self._status,
            'active_tasks': self._active_tasks,
            'total_completed': self._total_completed,
            'total_errors': self._total_errors,
            'system_status': system_status
        }
        
        for callback in self._status_callbacks:
            try:
                callback(heartbeat_data)
            except Exception as e:
                self.kernel.metrics.record_error("heartbeat_callback_failed", "local_worker")
    
    def register_status_callback(self, callback: Callable[[Dict], None]):
        """Register a callback for status updates."""
        self._status_callbacks.append(callback)
    
    def unregister_status_callback(self, callback: Callable[[Dict], None]):
        """Unregister a status callback."""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)
    
    def _notify_status_change(self):
        """Notify all callbacks of status change."""
        status_data = {
            'worker_id': self.worker_id,
            'status': self._status,
            'timestamp': datetime.utcnow().isoformat(),
            'active_tasks': self._active_tasks
        }
        
        for callback in self._status_callbacks:
            try:
                callback(status_data)
            except Exception:
                pass  # Don't fail on callback errors
    
    def execute_inference(self, request: InferenceRequest) -> InferenceResponse:
        """
        Execute inference request through kernel.
        
        Args:
            request: Inference request parameters
            
        Returns:
            Inference response
        """
        task_id = f"inf-{int(time.time() * 1000)}"
        
        try:
            with self._task_lock:
                self._active_tasks += 1
                self._notify_status_change()
            
            # Execute inference through kernel
            result = self.kernel.infer(
                model_name=request.model_name,
                prompt=request.prompt,
                parameters={
                    'max_tokens': request.max_tokens,
                    'temperature': request.temperature
                }
            )
            
            # Convert to response format
            response = InferenceResponse(
                response_text=result.response_text,
                tokens_generated=result.tokens_generated,
                inference_time_ms=result.inference_time_ms,
                status="success"
            )
            
            with self._task_lock:
                self._total_completed += 1
            
            return response
            
        except Exception as e:
            with self._task_lock:
                self._total_errors += 1
            
            self.kernel.metrics.record_error("inference_task_failed", "local_worker")
            
            return InferenceResponse(
                response_text="",
                tokens_generated=0,
                inference_time_ms=0,
                status="error",
                error_message=str(e)
            )
        
        finally:
            with self._task_lock:
                self._active_tasks -= 1
                self._notify_status_change()
    
    def execute_model_load(self, model_name: str, model_path: str, 
                          shards: int = 1, load_params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute model load request through kernel.
        
        Args:
            model_name: Name of the model
            model_path: Path to the model file
            shards: Number of shards
            load_params: Additional loading parameters
            
        Returns:
            Load result dictionary
        """
        try:
            with self._task_lock:
                self._active_tasks += 1
                self._notify_status_change()
            
            success = self.kernel.load_model(model_name, model_path, shards, load_params)
            
            with self._task_lock:
                self._total_completed += 1
            
            return {
                'success': success,
                'model_name': model_name,
                'message': f'Model {model_name} loaded successfully' if success else 'Load failed'
            }
            
        except Exception as e:
            with self._task_lock:
                self._total_errors += 1
            
            self.kernel.metrics.record_error("model_load_task_failed", "local_worker")
            
            return {
                'success': False,
                'model_name': model_name,
                'error': str(e)
            }
        
        finally:
            with self._task_lock:
                self._active_tasks -= 1
                self._notify_status_change()
    
    def execute_model_unload(self, model_name: str, force: bool = False) -> Dict[str, Any]:
        """
        Execute model unload request through kernel.
        
        Args:
            model_name: Name of the model to unload
            force: Force unload even if in use
            
        Returns:
            Unload result dictionary
        """
        try:
            with self._task_lock:
                self._active_tasks += 1
                self._notify_status_change()
            
            success = self.kernel.unload_model(model_name, force)
            
            with self._task_lock:
                self._total_completed += 1
            
            return {
                'success': success,
                'model_name': model_name,
                'message': f'Model {model_name} unloaded successfully' if success else 'Unload failed'
            }
            
        except Exception as e:
            with self._task_lock:
                self._total_errors += 1
            
            self.kernel.metrics.record_error("model_unload_task_failed", "local_worker")
            
            return {
                'success': False,
                'model_name': model_name,
                'error': str(e)
            }
        
        finally:
            with self._task_lock:
                self._active_tasks -= 1
                self._notify_status_change()
    
    def submit_learning_job(self, job_type: str, model_name: str, 
                           dataset_path: str, parameters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Submit learning job through kernel.
        
        Args:
            job_type: Type of learning job
            model_name: Target model name
            dataset_path: Path to training dataset
            parameters: Job parameters
            
        Returns:
            Job submission result
        """
        try:
            job_id = self.kernel.submit_learning_job(job_type, model_name, dataset_path, parameters)
            
            with self._task_lock:
                self._total_completed += 1
            
            return {
                'success': True,
                'job_id': job_id,
                'message': f'Learning job {job_id} submitted successfully'
            }
            
        except Exception as e:
            with self._task_lock:
                self._total_errors += 1
            
            self.kernel.metrics.record_error("learning_job_submit_failed", "local_worker")
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_goal(self, title: str, description: str, priority: str = "medium",
                   metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create goal through kernel.
        
        Args:
            title: Goal title
            description: Goal description
            priority: Goal priority
            metadata: Additional metadata
            
        Returns:
            Goal creation result
        """
        try:
            goal_id = self.kernel.create_goal(title, description, priority, metadata)
            
            with self._task_lock:
                self._total_completed += 1
            
            return {
                'success': True,
                'goal_id': goal_id,
                'message': f'Goal {goal_id} created successfully'
            }
            
        except Exception as e:
            with self._task_lock:
                self._total_errors += 1
            
            self.kernel.metrics.record_error("goal_create_failed", "local_worker")
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_status(self) -> WorkerStatus:
        """Get current worker status."""
        system_status = self.kernel.get_system_status()
        
        return WorkerStatus(
            worker_id=self.worker_id,
            status=self._status,
            last_heartbeat=self._last_heartbeat,
            active_tasks=self._active_tasks,
            total_completed=self._total_completed,
            total_errors=self._total_errors,
            capabilities={
                'inference': True,
                'model_management': True,
                'learning_jobs': True,
                'goal_management': True,
                'direct_kernel_access': True
            },
            system_info={
                'kernel_healthy': self.kernel.is_healthy(),
                'loaded_models': system_status.get('models', {}).get('loaded_count', 0),
                'gpu_usage': system_status.get('gpu', {}).get('usage_percent', 0.0),
                'active_learning_jobs': system_status.get('learning', {}).get('running_jobs', 0),
                'active_goals': system_status.get('goals', {}).get('active_goals', 0)
            }
        )
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get worker capabilities."""
        return {
            'inference': {
                'supported': True,
                'models': list(self.kernel.lifecycle.get_loaded_models().keys()),
                'max_concurrent': self.kernel.cfg.resilience.bulkhead.max_concurrent
            },
            'model_management': {
                'supported': True,
                'preload_enabled': len(self.kernel.cfg.models.preload) > 0,
                'auto_eviction': True
            },
            'learning': {
                'supported': True,
                'job_types': ['fine_tune', 'rlhf', 'lora', 'distillation'],
                'max_parallel_jobs': self.kernel.cfg.learning.max_parallel_jobs
            },
            'goals': {
                'supported': True,
                'max_active': self.kernel.cfg.goals.max_active_goals,
                'priority_levels': ['low', 'medium', 'high', 'critical']
            },
            'hardware': {
                'gpu_available': len(self.kernel.gpu_manager.get_gpu_info()) > 0,
                'total_vram_mb': self.kernel.gpu_manager.get_vram_usage()['total_vram_mb'],
                'cpu_threads': self.kernel.cfg.server.max_workers
            }
        }
    
    def is_healthy(self) -> bool:
        """Check if worker is healthy."""
        # Check if heartbeat is recent
        if datetime.utcnow() - self._last_heartbeat > timedelta(seconds=self.heartbeat_interval * 2):
            return False
        
        # Check kernel health
        if not self.kernel.is_healthy():
            return False
        
        # Check status
        return self._status in ["online", "busy"]
    
    def shutdown(self):
        """Shutdown worker adapter."""
        self._status = "offline"
        self._notify_status_change()
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Wait for heartbeat thread
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=5.0)
        
        # Wait for active tasks to complete
        max_wait = 30.0  # 30 seconds
        start_time = time.time()
        
        while self._active_tasks > 0 and (time.time() - start_time) < max_wait:
            time.sleep(0.1)
        
        # Clean up
        self._status_callbacks.clear()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()