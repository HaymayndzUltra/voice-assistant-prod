from src.core.base_agent import BaseAgent
"""
VRAM Manager Module
Handles VRAM monitoring, optimization, and model management
"""

import logging
import time
import threading
import zmq
from typing import Dict, Optional, List
import torch
import psutil
import GPUtil
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VRAMManager")

class VRAMManager(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="VramManager")
        """Initialize VRAM Manager"""
        self.vram_thresholds = {
            'critical': 0.9,  # 90% VRAM usage
            'warning': 0.75,  # 75% usage triggers warning
            'safe': 0.5       # 50% VRAM usage
        }
        
        self.model_vram_requirements = {
            'whisper-tiny': 1.0,    # 1GB
            'whisper-base': 2.0,    # 2GB
            'whisper-small': 3.0,   # 3GB
            'whisper-medium': 5.0,  # 5GB
            'whisper-large': 8.0,   # 8GB
            'whisper-large-v3': 10.0 # 10GB
        }
        
        self.loaded_models = {}
        self.lock = threading.Lock()
        self.running = True
        
        # New attributes for advanced management
        self.memory_pool = {}
        self.defragmentation_threshold = 0.70  # 70% fragmentation triggers defrag
        self.usage_patterns = defaultdict(list)
        self.prediction_window = 3600  # 1 hour window for predictions
        self.optimization_interval = 300  # 5 minutes between optimizations
        
        # Idle timeout configuration (new)
        self.idle_timeout = 900  # 15 minutes default timeout
        self.idle_check_interval = 60  # Check for idle models every minute
        
        # --- START: Digital Twin Integration ---
        try:
            # This import should be at the top of the file
            # import zmq
            self.context_dt = zmq.Context()
            self.dt_socket = self.context_dt.socket(zmq.REQ)
            self.dt_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.dt_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.dt_socket.connect("tcp://localhost:5585")
            logger.info("VRAMManager connected to SystemDigitalTwinAgent on port 5585.")
        except Exception as e:
            logger.error(f"Failed to connect to SystemDigitalTwinAgent: {e}")
            self.dt_socket = None
        # --- END: Digital Twin Integration ---
        
        # Start monitoring threads
        self.monitor_thread = threading.Thread(target=self._monitor_vram, daemon=True)
        self.optimization_thread = threading.Thread(target=self._optimize_memory, daemon=True)
        self.prediction_thread = threading.Thread(target=self._predict_usage, daemon=True)
        self.idle_monitor_thread = threading.Thread(target=self._monitor_idle_models, daemon=True)
        
        self.monitor_thread.start()
        self.optimization_thread.start()
        self.prediction_thread.start()
        self.idle_monitor_thread.start()
        
    def start_monitoring(self):
        """Start VRAM monitoring thread"""
        self.running = True
        logger.info("VRAM monitoring started")
        
    def stop_monitoring(self):
        """Stop VRAM monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join()
        if self.optimization_thread:
            self.optimization_thread.join()
        if self.prediction_thread:
            self.prediction_thread.join()
        if self.idle_monitor_thread:
            self.idle_monitor_thread.join()
        logger.info("VRAM monitoring stopped")
        
    def get_vram_usage(self) -> Dict[str, float]:
        """Get current VRAM usage statistics"""
        try:
            gpu = GPUtil.getGPUs()[0]  # Get first GPU
            return {
                'total': gpu.memoryTotal / 1024,  # Convert to GB
                'used': gpu.memoryUsed / 1024,
                'free': gpu.memoryFree / 1024,
                'utilization': gpu.load * 100  # GPU utilization percentage
            }
        except Exception as e:
            logger.error(f"Error getting VRAM usage: {e}")
            return {'total': 0, 'used': 0, 'free': 0, 'utilization': 0}
            
    def _consult_digital_twin(self, vram_request_mb: float) -> dict:
        """Consults the SystemDigitalTwin for a predictive recommendation."""
        if not self.dt_socket:
            logger.warning("Digital Twin socket not available. Proceeding without consultation.")
            return {"recommendation": "proceed"}
        
        try:
            request = {
                "action": "simulate_load",
                "load_type": "vram",
                "value_mb": vram_request_mb
            }
            self.dt_socket.send_json(request)
            
            poller = zmq.Poller()
            poller.register(self.dt_socket, zmq.POLLIN)
            if poller.poll(5000): # 5-second timeout
                response = self.dt_socket.recv_json()
                logger.info(f"Digital Twin recommendation: {response.get('recommendation')}")
                return response
            else:
                logger.error("Timeout waiting for response from SystemDigitalTwinAgent.")
                self.dt_socket.close()
                self.dt_socket = self.context_dt.socket(zmq.REQ)
                self.dt_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
                self.dt_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
                self.dt_socket.connect("tcp://localhost:5585")
                return {"recommendation": "proceed"}
        except Exception as e:
            logger.error(f"Error consulting Digital Twin: {e}")
            return {"recommendation": "proceed"}
            
    def can_load_model(self, model_id: str) -> bool:
        """Check if there's enough VRAM to load a model, after consulting the digital twin."""
        required_vram = self.model_vram_requirements.get(model_id, 0)
        
        # --- START OF NEW LOGIC ---
        # For large models (e.g., >2GB), consult the digital twin first as a pre-check
        if required_vram > 2048:
            logger.info(f"Consulting Digital Twin for large model request: {model_id} ({required_vram}MB)")
            dt_response = self._consult_digital_twin(required_vram)
            if dt_response.get("recommendation") != "proceed":
                logger.warning(f"Allocation for {model_id} denied by Digital Twin recommendation.")
                return False
        # --- END OF NEW LOGIC ---
        
        vram_usage = self.get_vram_usage()
        available_vram = vram_usage['free']
        
        return available_vram >= required_vram
        
    def register_model(self, model_id: str, model_instance: any):
        """Register a loaded model"""
        with self.lock:
            self.loaded_models[model_id] = {
                'instance': model_instance,
                'last_used': time.time(),
                'vram_usage': self.model_vram_requirements.get(model_id, 0)
            }
            logger.info(f"Registered model {model_id}")
            
    def unregister_model(self, model_id: str):
        """Unregister a model"""
        with self.lock:
            if model_id in self.loaded_models:
                del self.loaded_models[model_id]
                logger.info(f"Unregistered model {model_id}")
                
    def get_least_used_model(self) -> Optional[str]:
        """Get the least recently used model ID"""
        if not self.loaded_models:
            return None
            
        return min(self.loaded_models.items(), 
                  key=lambda x: x[1]['last_used'])[0]
                  
    def update_model_usage(self, model_id: str):
        """Update last used timestamp for a model"""
        with self.lock:
            if model_id in self.loaded_models:
                self.loaded_models[model_id]['last_used'] = time.time()
                
    def _monitor_vram(self):
        """Monitor VRAM usage and take action if needed"""
        while self.running:
            try:
                vram_usage = self.get_vram_usage()
                usage_ratio = vram_usage['used'] / vram_usage['total']
                
                if usage_ratio >= self.vram_thresholds['critical']:
                    logger.warning("Critical VRAM usage detected!")
                    self._handle_critical_vram()
                elif usage_ratio >= self.vram_thresholds['warning']:
                    logger.warning("High VRAM usage detected")
                    self._handle_high_vram()
                    
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in VRAM monitoring: {e}")
                time.sleep(5)
                
    def _handle_critical_vram(self):
        """Handle critical VRAM usage"""
        with self.lock:
            # Get models sorted by VRAM usage (largest first)
            sorted_models = self._get_models_by_vram_usage()
            
            # Unload the model with the largest VRAM footprint
            if sorted_models:
                model_to_unload = sorted_models[0]
                self._request_model_unload(model_to_unload)
                logger.info(f"Requested unload of model {model_to_unload} due to critical VRAM usage")
                
    def _handle_high_vram(self):
        """Handle high VRAM usage"""
        with self.lock:
            # Log warning but don't take action yet
            logger.warning("High VRAM usage - monitoring situation")
            
    def get_model_stats(self) -> Dict:
        """Get statistics about loaded models"""
        with self.lock:
            return {
                'total_models': len(self.loaded_models),
                'total_vram_usage': sum(m['vram_usage'] for m in self.loaded_models.values()),
                'models': {k: v['vram_usage'] for k, v in self.loaded_models.items()}
            }

    def _optimize_memory(self):
        """Advanced memory optimization loop"""
        while self.running:
            try:
                with self.lock:
                    vram_usage = self.get_vram_usage()
                    fragmentation = self._calculate_fragmentation()
                    
                    if fragmentation > self.defragmentation_threshold:
                        self._defragment_memory()
                    
                    if vram_usage['utilization'] < 50:  # Low GPU utilization
                        self._optimize_batch_sizes()
                    
                    self._apply_kernel_fusion()
                    self._optimize_memory_mapping()
                
                time.sleep(self.optimization_interval)
            except Exception as e:
                logger.error(f"Error in memory optimization: {e}")
                time.sleep(5)

    def _predict_usage(self):
        """Predict future VRAM usage based on patterns"""
        while self.running:
            try:
                with self.lock:
                    current_time = time.time()
                    # Analyze usage patterns
                    for model_id, timestamps in self.usage_patterns.items():
                        recent_usage = [t for t in timestamps if current_time - t < self.prediction_window]
                        if len(recent_usage) > 10:  # Enough data for prediction
                            usage_frequency = len(recent_usage) / self.prediction_window
                            if usage_frequency > 0.1:  # High frequency usage
                                self._preload_model(model_id)
                
                time.sleep(60)  # Check predictions every minute
            except Exception as e:
                logger.error(f"Error in usage prediction: {e}")
                time.sleep(5)

    def _defragment_memory(self):
        """Defragment GPU memory"""
        try:
            # Unload all models
            models_to_reload = list(self.loaded_models.keys())
            for model_id in models_to_reload:
                self.unregister_model(model_id)
            
            # Clear CUDA cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # Reload models in optimal order
            for model_id in models_to_reload:
                if self.can_load_model(model_id):
                    self._preload_model(model_id)
            
            logger.info("Memory defragmentation completed")
        except Exception as e:
            logger.error(f"Error during memory defragmentation: {e}")

    def _optimize_batch_sizes(self):
        """Optimize batch sizes based on available VRAM"""
        try:
            vram_usage = self.get_vram_usage()
            available_vram = vram_usage['free']
            
            for model_id, model_info in self.loaded_models.items():
                if hasattr(model_info['instance'], 'batch_size'):
                    current_batch = model_info['instance'].batch_size
                    optimal_batch = self._calculate_optimal_batch_size(
                        model_id, available_vram
                    )
                    if optimal_batch != current_batch:
                        model_info['instance'].batch_size = optimal_batch
                        logger.info(f"Optimized batch size for {model_id}: {optimal_batch}")
        except Exception as e:
            logger.error(f"Error optimizing batch sizes: {e}")

    def _apply_kernel_fusion(self):
        """Apply kernel fusion to optimize memory usage"""
        # Implementation depends on specific model architectures
        pass

    def _optimize_memory_mapping(self):
        """Optimize memory mapping for better performance"""
        # Implementation depends on specific hardware
        pass

    def _calculate_fragmentation(self) -> float:
        """Calculate memory fragmentation ratio"""
        try:
            if torch.cuda.is_available():
                # Get memory stats
                allocated = torch.cuda.memory_allocated() / (1024 * 1024)  # MB
                reserved = torch.cuda.memory_reserved() / (1024 * 1024)    # MB
                
                if reserved > 0:
                    # Fragmentation = (reserved - allocated) / reserved
                    return (reserved - allocated) / reserved
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating fragmentation: {e}")
            return 0.0

    def _calculate_optimal_batch_size(self, model_id: str, available_vram: float) -> int:
        """Calculate optimal batch size based on available VRAM"""
        try:
            # This is a simplified calculation
            # In practice, this would depend on model architecture
            base_batch_size = 1
            vram_per_sample = self.model_vram_requirements.get(model_id, 1.0) / base_batch_size
            
            if vram_per_sample > 0:
                # Leave 20% buffer
                optimal_batch = int(available_vram * 0.8 / vram_per_sample)
                return max(1, optimal_batch)  # At least batch size 1
            return 1
        except Exception as e:
            logger.error(f"Error calculating optimal batch size: {e}")
            return 1

    def _preload_model(self, model_id: str):
        """Preload a model based on usage prediction"""
        # This would connect to ModelManagerAgent to request loading
        logger.info(f"Preloading model {model_id} based on usage prediction")
        # Implementation would depend on model loading mechanism

    def get_advanced_stats(self) -> Dict:
        """Get advanced statistics about memory usage"""
        with self.lock:
            return {
                'vram_usage': self.get_vram_usage(),
                'fragmentation': self._calculate_fragmentation(),
                'models': {
                    k: {
                        'vram_usage': v['vram_usage'],
                        'last_used': time.time() - v['last_used'],
                        'idle_status': 'idle' if time.time() - v['last_used'] > self.idle_timeout else 'active'
                    } for k, v in self.loaded_models.items()
                }
            }
    
    def _monitor_idle_models(self):
        """Monitor and unload idle models based on timeout"""
        while self.running:
            try:
                idle_models = self._get_idle_models()
                
                for model_id in idle_models:
                    logger.info(f"Model {model_id} has been idle for more than {self.idle_timeout} seconds")
                    self._request_model_unload(model_id)
                    
                time.sleep(self.idle_check_interval)
            except Exception as e:
                logger.error(f"Error in idle model monitoring: {e}")
                time.sleep(5)
    
    def _get_idle_models(self) -> List[str]:
        """Get list of models that have been idle longer than the timeout"""
        with self.lock:
            current_time = time.time()
            return [
                model_id for model_id, info in self.loaded_models.items()
                if current_time - info['last_used'] > self.idle_timeout
            ]
    
    def _request_model_unload(self, model_id: str):
        """Request ModelManagerAgent to unload a model"""
        try:
            # Connect to ModelManagerAgent
            import zmq

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            socket.connect("tcp://localhost:5570")  # ModelManagerAgent port
            
            # Send unload request
            request = {
                "action": "unload_model",
                "model_id": model_id,
                "reason": "idle_timeout" if model_id in self._get_idle_models() else "vram_pressure"
            }
            
            socket.send_json(request)
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
            
            if poller.poll(5000):  # 5 second timeout
                response = socket.recv_json()
                if response.get("status") == "success":
                    logger.info(f"Successfully requested unload of model {model_id}")
                else:
                    logger.warning(f"Failed to unload model {model_id}: {response.get('message', 'Unknown error')}")
            else:
                logger.error(f"Timeout waiting for response to unload model {model_id}")
                
            socket.close()
            
        except Exception as e:
            logger.error(f"Error requesting model unload: {e}")
    
    def _get_models_by_vram_usage(self) -> List[str]:
        """Get models sorted by VRAM usage (largest first)"""
        with self.lock:
            # Sort models by VRAM usage (descending)
            sorted_models = sorted(
                self.loaded_models.items(),
                key=lambda x: x[1]['vram_usage'],
                reverse=True
            )
            return [model_id for model_id, _ in sorted_models]
    
    def set_idle_timeout(self, timeout_seconds: int):
        """Set the idle timeout for models"""
        if timeout_seconds > 0:
            self.idle_timeout = timeout_seconds
            logger.info(f"Set idle timeout to {timeout_seconds} seconds")
        else:
            logger.warning("Invalid idle timeout value, must be positive") 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise