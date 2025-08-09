"""Kernel module - Core orchestration and initialization for ModelOps Coordinator."""

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from .schemas import Config
from .telemetry import Telemetry
from .gpu_manager import GPUManager
from .lifecycle import LifecycleModule
from .inference import InferenceModule
from .learning import LearningModule
from .goal_manager import GoalModule
from .errors import ConfigurationError
from ..adapters.event_bus_adapter import EventBusAdapter
from .vram_module import VramOptimizationModule


class Kernel:
    """
    Core kernel that initializes and connects all ModelOps Coordinator modules.
    
    The kernel acts as the central orchestrator, managing the lifecycle of all
    core components and providing a unified interface to the system.
    """
    
    def __init__(self, cfg: Config):
        """
        Initialize the ModelOps Coordinator kernel.
        
        Args:
            cfg: Configuration object containing all system settings
            
        Raises:
            ConfigurationError: If configuration is invalid or initialization fails
        """
        self.cfg = cfg
        self._initialized = False
        self._shutdown_event = threading.Event()
        
        # Initialize thread pool executor for async operations
        self.executor = ThreadPoolExecutor(
            max_workers=cfg.server.max_workers,
            thread_name_prefix='ModelOpsWorker'
        )
        
        try:
            # Initialize core modules in dependency order
            self._init_telemetry()
            self._init_gpu_manager()
            self._init_lifecycle()
            self._init_inference()
            self._init_learning()
            self._init_goals()
            # New: Event bus and VRAM optimization module
            self._init_event_bus()
            self._init_vram_module()
            
            self._initialized = True
            
            # Record successful initialization
            self.metrics.record_error("kernel_initialized", "kernel")
            
        except Exception as e:
            # Cleanup on initialization failure
            self._cleanup_on_error()
            raise ConfigurationError("kernel_initialization", f"Failed to initialize kernel: {e}")
    
    def _init_telemetry(self):
        """Initialize telemetry and metrics collection."""
        self.metrics = Telemetry()
        
        # Start background metrics collection
        def update_system_metrics():
            """Background task to update system metrics."""
            import psutil
            
            while not self._shutdown_event.is_set():
                try:
                    # Update uptime
                    self.metrics.update_uptime()
                    
                    # Update system metrics
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory = psutil.virtual_memory()
                    
                    self.metrics.update_system_metrics(
                        cpu_percent=cpu_percent,
                        memory_used=memory.used,
                        memory_total=memory.total
                    )
                    
                    # Sleep for 30 seconds between updates
                    self._shutdown_event.wait(30)
                    
                except Exception:
                    self.metrics.record_error("system_metrics_error", "kernel")
                    self._shutdown_event.wait(30)
        
        # Start metrics thread
        self._metrics_thread = threading.Thread(
            target=update_system_metrics,
            name="SystemMetrics",
            daemon=True
        )
        self._metrics_thread.start()
    
    def _init_gpu_manager(self):
        """Initialize GPU resource manager."""
        self.gpu_manager = GPUManager(self.cfg, self.metrics)
    
    def _init_lifecycle(self):
        """Initialize model lifecycle manager."""
        self.lifecycle = LifecycleModule(self.cfg, self.gpu_manager, self.metrics)
    
    def _init_inference(self):
        """Initialize inference execution engine."""
        self.inference = InferenceModule(self.cfg, self.lifecycle, self.metrics)
    
    def _init_learning(self):
        """Initialize learning and fine-tuning job manager."""
        self.learning = LearningModule(self.cfg, self.lifecycle, self.metrics)
    
    def _init_goals(self):
        """Initialize goal management system."""
        self.goals = GoalModule(self.cfg, self.learning, self.metrics)

    def _init_event_bus(self):
        """Initialize event bus adapter."""
        self.event_bus = EventBusAdapter()

    def _init_vram_module(self):
        """Initialize the event-driven VRAM optimization module (dry-run)."""
        def _apply_unload(model_name: str) -> bool:
            try:
                return self.lifecycle.unload(model_name, force=False)
            except Exception:
                return False
        self.vram_module = VramOptimizationModule(
            bus=self.event_bus,
            logger=self.metrics.logger if hasattr(self.metrics, 'logger') else None or __import__('logging').getLogger(__name__),
            dry_run=True,
            budget_pct=0.85,
            apply_unload=_apply_unload,
        )

    async def initialize(self):
        """Async initialization of modules that require event loops."""
        # Start event bus and vram module subscribers
        await self.event_bus.start()
        await self.vram_module.start()
    
    def _cleanup_on_error(self):
        """Cleanup resources when initialization fails."""
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cleanup in reverse order
        cleanup_attrs = [
            'goals', 'learning', 'inference', 'lifecycle', 
            'gpu_manager', '_metrics_thread'
        ]
        
        for attr in cleanup_attrs:
            if hasattr(self, attr):
                try:
                    component = getattr(self, attr)
                    if hasattr(component, 'shutdown'):
                        component.shutdown()
                    elif hasattr(component, 'join'):
                        component.join(timeout=1.0)
                except Exception:
                    pass  # Best effort cleanup
        
        # Shutdown executor
        if hasattr(self, 'executor'):
            try:
                self.executor.shutdown(wait=False)
            except Exception:
                pass
    
    def is_healthy(self) -> bool:
        """
        Check if the kernel and all modules are healthy.
        
        Returns:
            True if all components are operational
        """
        if not self._initialized:
            return False
        
        try:
            # Check critical components
            health_checks = [
                self.gpu_manager is not None,
                self.lifecycle is not None,
                self.inference is not None,
                self.learning is not None,
                self.goals is not None,
                not self.executor._shutdown
            ]
            
            return all(health_checks)
            
        except Exception:
            return False
    
    def get_system_status(self) -> dict:
        """
        Get comprehensive system status.
        
        Returns:
            Dictionary containing status of all components
        """
        try:
            # GPU status
            gpu_info = self.gpu_manager.get_gpu_info()
            vram_usage = self.gpu_manager.get_vram_usage()
            
            # Model status
            loaded_models = self.lifecycle.get_loaded_models()
            circuit_breakers = self.lifecycle.get_circuit_breaker_status()
            
            # Learning jobs status
            job_stats = self.learning.get_job_statistics()
            
            # Goals status
            goal_stats = self.goals.get_goal_statistics()
            
            # Metrics summary
            metrics_summary = self.metrics.get_metrics_summary()
            
            return {
                'kernel': {
                    'initialized': self._initialized,
                    'healthy': self.is_healthy(),
                    'worker_threads': self.cfg.server.max_workers
                },
                'gpu': {
                    'devices': len(gpu_info),
                    'total_vram_mb': vram_usage.get('total_vram_mb', 0),
                    'used_vram_mb': vram_usage.get('allocated_mb', 0),
                    'usage_percent': vram_usage.get('usage_percent', 0.0)
                },
                'models': {
                    'loaded_count': len(loaded_models),
                    'circuit_breakers': circuit_breakers
                },
                'learning': job_stats,
                'goals': goal_stats,
                'metrics': metrics_summary
            }
            
        except Exception as e:
            self.metrics.record_error("status_query_error", "kernel")
            return {
                'error': str(e),
                'healthy': False
            }
    
    def load_model(self, model_name: str, model_path: str, shards: int = 1, 
                   load_params: Optional[dict] = None) -> bool:
        """
        Load a model through the lifecycle manager.
        
        Args:
            model_name: Unique name for the model
            model_path: Path to the model file
            shards: Number of shards to load across
            load_params: Additional loading parameters
            
        Returns:
            True if load successful
        """
        return self.lifecycle.load(model_name, model_path, shards, load_params)
    
    def unload_model(self, model_name: str, force: bool = False) -> bool:
        """
        Unload a model through the lifecycle manager.
        
        Args:
            model_name: Name of the model to unload
            force: Force unload even if in use
            
        Returns:
            True if unload successful
        """
        return self.lifecycle.unload(model_name, force)
    
    def infer(self, model_name: str, prompt: str, parameters: Optional[dict] = None):
        """
        Run inference through the inference engine.
        
        Args:
            model_name: Name of the model to use
            prompt: Input prompt for inference
            parameters: Additional inference parameters
            
        Returns:
            Inference result
        """
        return self.inference.infer(model_name, prompt, parameters)
    
    def submit_learning_job(self, job_type: str, model_name: str, 
                           dataset_path: str, parameters: Optional[dict] = None) -> str:
        """
        Submit a learning job through the learning manager.
        
        Args:
            job_type: Type of learning job
            model_name: Target model name
            dataset_path: Path to training dataset
            parameters: Job parameters
            
        Returns:
            Job ID
        """
        return self.learning.submit_job(job_type, model_name, dataset_path, parameters)
    
    def create_goal(self, title: str, description: str, priority: str = "medium",
                   metadata: Optional[dict] = None) -> str:
        """
        Create a goal through the goal manager.
        
        Args:
            title: Goal title
            description: Goal description
            priority: Goal priority level
            metadata: Additional metadata
            
        Returns:
            Goal ID
        """
        return self.goals.create_goal(title, description, priority, metadata)
    
    def shutdown(self):
        """
        Gracefully shutdown the kernel and all modules.
        
        This will:
        1. Signal shutdown to all background threads
        2. Shutdown modules in reverse dependency order
        3. Wait for threads to complete
        4. Cleanup resources
        """
        if not self._initialized:
            return
        
        # Signal shutdown
        self._shutdown_event.set()
        
        try:
            # Shutdown modules in reverse dependency order
            if hasattr(self, 'goals'):
                self.goals.shutdown()
            
            if hasattr(self, 'learning'):
                self.learning.shutdown()
            
            if hasattr(self, 'inference'):
                self.inference.shutdown()
            
            if hasattr(self, 'lifecycle'):
                self.lifecycle.shutdown()
            
            if hasattr(self, 'gpu_manager'):
                self.gpu_manager.shutdown()
            
            # Wait for metrics thread
            if hasattr(self, '_metrics_thread') and self._metrics_thread.is_alive():
                self._metrics_thread.join(timeout=5.0)
            
            # Shutdown executor
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=True, timeout=10.0)
            
            self._initialized = False
            
        except Exception:
            # Log error but continue shutdown
            if hasattr(self, 'metrics'):
                self.metrics.record_error("shutdown_error", "kernel")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.shutdown()