"""Inference execution module for ModelOps Coordinator."""

import time
import threading
from typing import Dict, Optional, Any
from datetime import datetime

from ..resiliency.bulkhead import Bulkhead
from .errors import InferenceError, BulkheadRejection, ModelNotFoundError
from .lifecycle import LifecycleModule
from .telemetry import Telemetry
from .schemas import Config


class InferenceResult:
    """Inference result container."""
    
    def __init__(self, response_text: str, tokens_generated: int, 
                 inference_time_ms: float, status: str = "success",
                 error_message: Optional[str] = None):
        self.response_text = response_text
        self.tokens_generated = tokens_generated
        self.inference_time_ms = inference_time_ms
        self.status = status
        self.error_message = error_message
        self.timestamp = datetime.utcnow()


class InferenceModule:
    """Inference execution engine with bulkhead protection."""
    
    def __init__(self, config: Config, lifecycle: LifecycleModule, telemetry: Telemetry):
        """Initialize inference module."""
        self.config = config
        self.lifecycle = lifecycle
        self.telemetry = telemetry
        self._lock = threading.RLock()
        
        # Bulkhead for inference requests
        self._inference_bulkhead = Bulkhead(
            max_concurrent=self.config.resilience.bulkhead.max_concurrent,
            max_queue_size=self.config.resilience.bulkhead.max_queue_size,
            name="inference"
        )
        
        # Track active requests per model
        self._active_requests: Dict[str, int] = {}
    
    def infer(self, model_name: str, prompt: str, parameters: Optional[Dict[str, Any]] = None) -> InferenceResult:
        """
        Run inference on a model with bulkhead protection.
        
        Args:
            model_name: Name of the model to use
            prompt: Input prompt for inference
            parameters: Additional inference parameters
            
        Returns:
            InferenceResult containing response and metrics
            
        Raises:
            InferenceError: If inference fails
            BulkheadRejection: If bulkhead rejects the request
            ModelNotFoundError: If model not found
        """
        # Check bulkhead capacity
        if not self._inference_bulkhead.acquire():
            self.telemetry.record_bulkhead_rejection("inference")
            raise BulkheadRejection(
                "inference",
                self._inference_bulkhead.current_load,
                self._inference_bulkhead.max_concurrent
            )
        
        try:
            # Update active request tracking
            with self._lock:
                self._active_requests[model_name] = self._active_requests.get(model_name, 0) + 1
                self.telemetry.set_active_inference_requests(
                    model_name, 
                    self._active_requests[model_name]
                )
            
            # Update bulkhead metrics
            self.telemetry.update_bulkhead_metrics(
                "inference",
                self._inference_bulkhead.current_load,
                self._inference_bulkhead.queue_size
            )
            
            # Execute inference
            return self._do_inference(model_name, prompt, parameters)
            
        finally:
            # Release bulkhead and update tracking
            self._inference_bulkhead.release()
            
            with self._lock:
                if model_name in self._active_requests:
                    self._active_requests[model_name] -= 1
                    if self._active_requests[model_name] <= 0:
                        del self._active_requests[model_name]
                    else:
                        self.telemetry.set_active_inference_requests(
                            model_name,
                            self._active_requests[model_name]
                        )
    
    def _do_inference(self, model_name: str, prompt: str, parameters: Optional[Dict[str, Any]]) -> InferenceResult:
        """Internal inference implementation."""
        start_time = time.time()
        
        try:
            # Ensure model is loaded
            loaded_models = self.lifecycle.get_loaded_models()
            if model_name not in loaded_models:
                raise ModelNotFoundError(model_name)
            
            model = loaded_models[model_name]
            
            # Update model access tracking
            self.lifecycle.gpu_manager.access_model(model_name)
            
            # Parse parameters
            max_tokens = parameters.get('max_tokens', 100) if parameters else 100
            temperature = parameters.get('temperature', 0.7) if parameters else 0.7
            
            # Simulate inference (in production, this would call the actual model)
            response_text, tokens_generated = self._simulate_inference(
                model, prompt, max_tokens, temperature
            )
            
            # Calculate metrics
            inference_time_ms = (time.time() - start_time) * 1000
            
            # Record success metrics
            self.telemetry.record_inference(
                model_name, 
                True, 
                inference_time_ms / 1000,
                tokens_generated
            )
            
            return InferenceResult(
                response_text=response_text,
                tokens_generated=tokens_generated,
                inference_time_ms=inference_time_ms,
                status="success"
            )
            
        except Exception as e:
            # Calculate error metrics
            inference_time_ms = (time.time() - start_time) * 1000
            
            # Record failure metrics
            self.telemetry.record_inference(model_name, False, inference_time_ms / 1000)
            
            if isinstance(e, (ModelNotFoundError, InferenceError)):
                raise
            else:
                raise InferenceError(model_name, str(e))
    
    def _simulate_inference(self, model, prompt: str, max_tokens: int, temperature: float) -> tuple:
        """
        Simulate model inference.
        
        In production, this would:
        1. Tokenize the input prompt
        2. Run forward pass through the model
        3. Apply sampling with temperature
        4. Decode tokens back to text
        5. Handle special tokens and stopping conditions
        """
        # Simulate processing time based on prompt length and max_tokens
        processing_time = min((len(prompt) + max_tokens) / 1000.0, 5.0)  # Max 5 seconds
        time.sleep(processing_time * 0.01)  # Scaled down for demo
        
        # Simulate potential inference errors (0.5% chance)
        import random
        if random.random() < 0.005:
            raise Exception("Simulated inference failure")
        
        # Generate mock response
        response_length = min(max_tokens, random.randint(20, 200))
        response_text = f"Generated response for prompt: '{prompt[:50]}...' (temp={temperature})"
        
        # Add some variability based on temperature
        if temperature > 0.8:
            response_text += " [High creativity mode]"
        elif temperature < 0.3:
            response_text += " [Focused mode]"
        
        return response_text, response_length
    
    def get_inference_statistics(self) -> Dict[str, Any]:
        """Get inference statistics and metrics."""
        with self._lock:
            return {
                'active_requests': dict(self._active_requests),
                'total_active': sum(self._active_requests.values()),
                'bulkhead': {
                    'current_load': self._inference_bulkhead.current_load,
                    'max_concurrent': self._inference_bulkhead.max_concurrent,
                    'queue_size': self._inference_bulkhead.queue_size,
                    'max_queue_size': self._inference_bulkhead.max_queue_size
                }
            }
    
    def shutdown(self):
        """Shutdown inference module."""
        # Wait for active requests to complete (with timeout)
        max_wait_time = 30.0  # 30 seconds
        start_time = time.time()
        
        while self._active_requests and (time.time() - start_time) < max_wait_time:
            time.sleep(0.1)
        
        # Force shutdown bulkhead
        self._inference_bulkhead.shutdown()