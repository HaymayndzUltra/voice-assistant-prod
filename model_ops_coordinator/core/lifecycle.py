"""Model lifecycle management for ModelOps Coordinator."""

import time
import threading
from typing import Dict, Optional, Set
from enum import Enum
from datetime import datetime
from pathlib import Path

from ..resiliency.circuit_breaker import CircuitBreaker
from .errors import ModelLoadError, ModelUnloadError, ModelNotFoundError, CircuitBreakerError
from .gpu_manager import GPUManager
from .telemetry import Telemetry
from .schemas import Config, ModelStatus


class ModelState(Enum):
    """Internal model state enumeration."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    UNLOADING = "unloading"
    FAILED = "failed"


class LoadedModel:
    """Represents a loaded model in memory."""
    
    def __init__(self, name: str, path: str, vram_mb: int, shards: int = 1):
        self.name = name
        self.path = path
        self.vram_mb = vram_mb
        self.shards = shards
        self.loaded_at = datetime.utcnow()
        self.last_accessed = datetime.utcnow()
        self.access_count = 0
        self.state = ModelState.LOADED
        # In production, this would hold the actual model object
        self.model_handle = f"mock_handle_{name}"


class LifecycleModule:
    """Model lifecycle management with circuit breaker protection."""
    
    def __init__(self, config: Config, gpu_manager: GPUManager, telemetry: Telemetry):
        """Initialize lifecycle module."""
        self.config = config
        self.gpu_manager = gpu_manager
        self.telemetry = telemetry
        self._lock = threading.RLock()
        
        # Model state tracking
        self._loaded_models: Dict[str, LoadedModel] = {}
        self._model_states: Dict[str, ModelState] = {}
        self._loading_locks: Dict[str, threading.Lock] = {}
        
        # Circuit breakers for different operations
        self._load_breaker = CircuitBreaker(
            failure_threshold=self.config.resilience.circuit_breaker.failure_threshold,
            reset_timeout=self.config.resilience.circuit_breaker.reset_timeout,
            name="model_load"
        )
        self._unload_breaker = CircuitBreaker(
            failure_threshold=self.config.resilience.circuit_breaker.failure_threshold,
            reset_timeout=self.config.resilience.circuit_breaker.reset_timeout,
            name="model_unload"
        )
        
        # Preload configured models
        self._preload_models()
    
    def _preload_models(self):
        """Preload models specified in configuration."""
        for model_config in self.config.models.preload:
            try:
                self.load(
                    model_name=model_config.name,
                    model_path=model_config.path,
                    shards=model_config.shards
                )
            except Exception as e:
                self.telemetry.record_error("preload_failed", "lifecycle")
    
    def load(self, model_name: str, model_path: str, shards: int = 1, 
             load_params: Optional[Dict] = None) -> bool:
        """
        Load a model into memory.
        
        Args:
            model_name: Unique name for the model
            model_path: Path to the model file
            shards: Number of shards to load across
            load_params: Additional loading parameters
            
        Returns:
            True if load successful
            
        Raises:
            ModelLoadError: If loading fails
            CircuitBreakerError: If circuit breaker is open
        """
        # Check circuit breaker
        if self._load_breaker.is_open():
            raise CircuitBreakerError("model_load", self._load_breaker.failure_count)
        
        # Update telemetry
        self.telemetry.update_circuit_breaker(
            "model_load", 
            1 if self._load_breaker.is_open() else 0,
            self._load_breaker.failure_count
        )
        
        # Get or create loading lock for this model
        with self._lock:
            if model_name not in self._loading_locks:
                self._loading_locks[model_name] = threading.Lock()
            model_lock = self._loading_locks[model_name]
        
        # Ensure only one thread loads a model at a time
        with model_lock:
            return self._do_load(model_name, model_path, shards, load_params)
    
    def _do_load(self, model_name: str, model_path: str, shards: int, 
                 load_params: Optional[Dict]) -> bool:
        """Internal model loading implementation."""
        start_time = time.time()
        
        try:
            # Check if already loaded
            with self._lock:
                if model_name in self._loaded_models:
                    model = self._loaded_models[model_name]
                    model.last_accessed = datetime.utcnow()
                    model.access_count += 1
                    self.gpu_manager.access_model(model_name)
                    return True
                
                # Check if currently loading
                if self._model_states.get(model_name) == ModelState.LOADING:
                    # Wait for loading to complete
                    while self._model_states.get(model_name) == ModelState.LOADING:
                        time.sleep(0.1)
                    
                    # Check result
                    if model_name in self._loaded_models:
                        return True
                    else:
                        raise ModelLoadError(model_name, "Loading by another thread failed")
                
                # Set loading state
                self._model_states[model_name] = ModelState.LOADING
            
            # Validate model path
            if not Path(model_path).exists():
                raise ModelLoadError(model_name, f"Model file not found: {model_path}")
            
            # Estimate VRAM requirements (simplified calculation)
            vram_required_mb = self._estimate_vram_requirements(model_path, shards)
            
            # Allocate VRAM
            self.gpu_manager.allocate_vram(model_name, vram_required_mb)
            
            # Simulate model loading (in production, this would use actual ML framework)
            self._simulate_model_load(model_name, model_path, vram_required_mb)
            
            # Create loaded model record
            loaded_model = LoadedModel(
                name=model_name,
                path=model_path,
                vram_mb=vram_required_mb,
                shards=shards
            )
            
            with self._lock:
                self._loaded_models[model_name] = loaded_model
                self._model_states[model_name] = ModelState.LOADED
            
            # Record metrics
            duration = time.time() - start_time
            self.telemetry.record_model_load(model_name, True, duration, vram_required_mb)
            
            # Circuit breaker success
            self._load_breaker.call_succeeded()
            
            return True
            
        except Exception as e:
            # Handle failure
            with self._lock:
                self._model_states[model_name] = ModelState.FAILED
            
            # Free any allocated VRAM
            try:
                self.gpu_manager.free_vram(model_name)
            except:
                pass
            
            # Record metrics
            duration = time.time() - start_time
            self.telemetry.record_model_load(model_name, False, duration)
            
            # Circuit breaker failure
            self._load_breaker.call_failed()
            
            if isinstance(e, ModelLoadError):
                raise
            else:
                raise ModelLoadError(model_name, str(e))
    
    def unload(self, model_name: str, force: bool = False) -> bool:
        """
        Unload a model from memory.
        
        Args:
            model_name: Name of the model to unload
            force: Force unload even if in use
            
        Returns:
            True if unload successful
            
        Raises:
            ModelUnloadError: If unloading fails
            ModelNotFoundError: If model not found
            CircuitBreakerError: If circuit breaker is open
        """
        # Check circuit breaker
        if self._unload_breaker.is_open():
            raise CircuitBreakerError("model_unload", self._unload_breaker.failure_count)
        
        # Update telemetry
        self.telemetry.update_circuit_breaker(
            "model_unload",
            1 if self._unload_breaker.is_open() else 0,
            self._unload_breaker.failure_count
        )
        
        try:
            with self._lock:
                if model_name not in self._loaded_models:
                    raise ModelNotFoundError(model_name)
                
                model = self._loaded_models[model_name]
                
                # Check if safe to unload (simplified check)
                if not force and model.access_count > 0:
                    # In production, would check for active inference requests
                    pass
                
                # Set unloading state
                self._model_states[model_name] = ModelState.UNLOADING
            
            # Simulate model unloading
            self._simulate_model_unload(model_name)
            
            # Free VRAM
            freed_mb = self.gpu_manager.free_vram(model_name)
            
            # Remove from loaded models
            with self._lock:
                del self._loaded_models[model_name]
                self._model_states[model_name] = ModelState.UNLOADED
                
                # Cleanup loading lock
                if model_name in self._loading_locks:
                    del self._loading_locks[model_name]
            
            # Record metrics
            self.telemetry.record_model_unload(model_name, True)
            
            # Circuit breaker success
            self._unload_breaker.call_succeeded()
            
            return True
            
        except Exception as e:
            # Handle failure
            with self._lock:
                if model_name in self._model_states:
                    self._model_states[model_name] = ModelState.FAILED
            
            # Record metrics
            self.telemetry.record_model_unload(model_name, False)
            
            # Circuit breaker failure
            self._unload_breaker.call_failed()
            
            if isinstance(e, (ModelUnloadError, ModelNotFoundError)):
                raise
            else:
                raise ModelUnloadError(model_name, str(e))
    
    def ensure_loaded(self, model_name: str, model_path: str, 
                     shards: int = 1) -> LoadedModel:
        """
        Ensure a model is loaded, loading it if necessary.
        
        Args:
            model_name: Name of the model
            model_path: Path to the model file
            shards: Number of shards
            
        Returns:
            LoadedModel instance
            
        Raises:
            ModelLoadError: If loading fails
        """
        with self._lock:
            if model_name in self._loaded_models:
                model = self._loaded_models[model_name]
                model.last_accessed = datetime.utcnow()
                model.access_count += 1
                self.gpu_manager.access_model(model_name)
                return model
        
        # Model not loaded, load it
        self.load(model_name, model_path, shards)
        
        with self._lock:
            return self._loaded_models[model_name]
    
    def get_loaded_models(self) -> Dict[str, LoadedModel]:
        """Get all currently loaded models."""
        with self._lock:
            return self._loaded_models.copy()
    
    def get_model_status(self, model_name: str) -> ModelStatus:
        """Get status of a specific model."""
        with self._lock:
            if model_name in self._loaded_models:
                return ModelStatus.LOADED
            
            state = self._model_states.get(model_name, ModelState.UNLOADED)
            
            status_map = {
                ModelState.UNLOADED: ModelStatus.UNKNOWN,
                ModelState.LOADING: ModelStatus.LOADING,
                ModelState.LOADED: ModelStatus.LOADED,
                ModelState.UNLOADING: ModelStatus.UNLOADING,
                ModelState.FAILED: ModelStatus.FAILED
            }
            
            return status_map.get(state, ModelStatus.UNKNOWN)
    
    def _estimate_vram_requirements(self, model_path: str, shards: int) -> int:
        """
        Estimate VRAM requirements for a model.
        
        In production, this would analyze the model file to determine
        actual memory requirements based on parameters, precision, etc.
        """
        try:
            file_size_mb = Path(model_path).stat().st_size / (1024 * 1024)
            
            # Simplified estimation: assume model needs 1.5x file size in VRAM
            # This accounts for weights + activations + overhead
            base_requirement = int(file_size_mb * 1.5)
            
            # Adjust for sharding
            per_shard_mb = max(base_requirement // shards, 1000)  # Minimum 1GB per shard
            
            return per_shard_mb
            
        except Exception:
            # Fallback estimation based on typical model sizes
            return 4000  # 4GB default
    
    def _simulate_model_load(self, model_name: str, model_path: str, vram_mb: int):
        """
        Simulate model loading process.
        
        In production, this would:
        1. Initialize the ML framework (PyTorch, TensorFlow, etc.)
        2. Load model weights from file
        3. Move model to GPU
        4. Optimize for inference (if needed)
        """
        # Simulate loading time based on model size
        load_time = min(vram_mb / 1000.0, 10.0)  # Max 10 seconds
        time.sleep(load_time * 0.01)  # Scaled down for demo
        
        # Simulate potential loading errors (1% chance)
        import random
        if random.random() < 0.01:
            raise Exception("Simulated loading failure")
    
    def _simulate_model_unload(self, model_name: str):
        """
        Simulate model unloading process.
        
        In production, this would:
        1. Clear model from GPU memory
        2. Release any cached tensors
        3. Trigger garbage collection if needed
        """
        # Simulate unloading time
        time.sleep(0.1)
    
    def get_circuit_breaker_status(self) -> Dict[str, Dict]:
        """Get status of all circuit breakers."""
        return {
            'load': {
                'state': 'open' if self._load_breaker.is_open() else 'closed',
                'failure_count': self._load_breaker.failure_count,
                'last_failure_time': self._load_breaker.last_failure_time
            },
            'unload': {
                'state': 'open' if self._unload_breaker.is_open() else 'closed',
                'failure_count': self._unload_breaker.failure_count,
                'last_failure_time': self._unload_breaker.last_failure_time
            }
        }
    
    def shutdown(self):
        """Shutdown lifecycle module and unload all models."""
        with self._lock:
            model_names = list(self._loaded_models.keys())
        
        for model_name in model_names:
            try:
                self.unload(model_name, force=True)
            except Exception:
                # Best effort cleanup
                pass