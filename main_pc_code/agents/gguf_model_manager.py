"""
GGUF Model Manager
-----------------
Handles loading, unloading, and managing GGUF models using llama-cpp-python
Provides a unified interface for model access
"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

from common.core.base_agent import BaseAgent

import gc
import uuid
import time
import json
import logging
import threading
from typing import Dict, Optional, Any, Union, List
import traceback
import torch

# Try to import Llama from llama_cpp
try:
    from llama_cpp import Llama  # type: ignore
    LLAMA_CPP_AVAILABLE = True
except ImportError as e:
    LLAMA_CPP_AVAILABLE = False
    print(f"WARNING: llama-cpp-python not available. GGUF models will not work. Error: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/gguf_model_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GGUFModelManager")

class GGUFModelManager(BaseAgent):
    """Manager for GGUF models using llama-cpp-python"""
    
    def __init__(self, port: int = 5575, models_dir: str = "models", **kwargs):
        """Initialize the GGUF model manager
        
        Args:
            port: Port to run the agent on
            models_dir: Directory where GGUF models are stored
            **kwargs: Additional arguments to pass to the BaseAgent
        """
        super().__init__(port=port, name="GgufModelManager")
        
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize model tracking
        self.loaded_models = {}
        self.last_used = {}
        
        # Initialize state tracker
        self.state_tracker = GGUFStateTracker()
        
        # Dictionary to store model metadata
        self.model_metadata = {}
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        # Load model metadata from config
        self._load_model_metadata()
        
        # Check GGUF support
        if not LLAMA_CPP_AVAILABLE:
            logger.warning("llama-cpp-python not available. GGUF models will not work.")
    
    def _load_model_metadata(self):
        """Load model metadata from config files"""
        try:
            # Add the parent directory to sys.path to import the config module
            from main_pc_code.config.system_config import Config
            
            config = Config()
            machine_config = config.get_all().get('main_pc_settings', {})
            
            # Extract model configs
            model_configs = machine_config.get('model_configs', {})
            
            # Filter for GGUF models
            for model_id, model_info in model_configs.items():
                if model_info.get('serving_method') == 'gguf_direct' and model_info.get('enabled', False):
                    self.model_metadata[model_id] = {
                        'display_name': model_info.get('display_name', model_id),
                        'model_path': model_info.get('model_path', f"{model_id}.gguf"),
                        'n_ctx': model_info.get('context_length', 2048),
                        'n_gpu_layers': model_info.get('n_gpu_layers', -1),
                        'n_threads': model_info.get('n_threads', 4),
                        'verbose': model_info.get('verbose', False),
                        'estimated_vram_mb': model_info.get('estimated_vram_mb', 0),
                        'capabilities': model_info.get('capabilities', ["code-generation"]),
                        'idle_timeout_seconds': model_info.get('idle_timeout_seconds', 300),
                    }
                    
            logger.info(f"Loaded metadata for {len(self.model_metadata)} GGUF models")
            
        except Exception as e:
            logger.error(f"Error loading model metadata: {e}")
            traceback.print_exc()
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List all available models with their status
        
        Returns:
            List of dictionaries with model information
        """
        models = []
        
        with self.lock:
            for model_id, metadata in self.model_metadata.items():
                model_info = metadata.copy()
                model_info['model_id'] = model_id
                model_info['loaded'] = model_id in self.loaded_models
                
                if model_id in self.last_used:
                    model_info['last_used'] = self.last_used[model_id]
                    model_info['idle_time'] = time.time() - self.last_used[model_id]
                
                models.append(model_info)
        
        return models
    
    def load_model(self, model_id: str) -> bool:
        """Load a GGUF model
        
        Args:
            model_id: ID of the model to load
            
        Returns:
            bool: True if model was loaded successfully
        """
        with self.lock:
            if model_id in self.loaded_models:
                logger.info(f"Model {model_id} is already loaded")
                self.state_tracker.mark_model_loaded(model_id, self.model_metadata[model_id]['estimated_vram_mb'])
                return True
                
            if model_id not in self.model_metadata:
                logger.error(f"Model {model_id} not found in metadata")
                return False
                
            model_info = self.model_metadata[model_id]
            model_path = self.models_dir / model_info['model_path']
            
            if not model_path.exists():
                logger.error(f"Model file not found: {model_path}")
                return False
                
            # Check if we have enough VRAM
            if not self.state_tracker.can_accommodate_model(model_info['estimated_vram_mb']):
                logger.error(f"Not enough VRAM to load model {model_id}")
                return False
                
            try:
                # Load the model
                model = Llama(
                    model_path=str(model_path),
                    n_ctx=model_info.get('n_ctx', 2048),
                    n_gpu_layers=model_info.get('n_gpu_layers', -1),
                    n_threads=model_info.get('n_threads', 4),
                    verbose=model_info.get('verbose', False)
                )
                
                self.loaded_models[model_id] = model
                self.state_tracker.mark_model_loaded(model_id, model_info['estimated_vram_mb'])
                logger.info(f"Successfully loaded model {model_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error loading model {model_id}: {e}")
                return False
    
    def unload_model(self, model_id: str) -> bool:
        """Unload a GGUF model
        
        Args:
            model_id: ID of the model to unload
            
        Returns:
            bool: True if model was unloaded successfully
        """
        with self.lock:
            if model_id not in self.loaded_models:
                logger.warning(f"Model {model_id} is not loaded")
                return False
                
            try:
                # Unload the model
                del self.loaded_models[model_id]
                self.state_tracker.mark_model_unloaded(model_id)
                logger.info(f"Successfully unloaded model {model_id}")
                return True
            except Exception as e:
                logger.error(f"Error unloading model {model_id}: {e}")
                return False
    
    def generate_text(self, model_id: str, prompt: str, system_prompt: Optional[str] = None,
                     max_tokens: int = 1024, temperature: float = 0.7,
                     top_p: float = 0.95, stop: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate text using a GGUF model
        
        Args:
            model_id: ID of the model to use
            prompt: The prompt to generate text from
            system_prompt: Optional system prompt for chat models
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature for sampling
            top_p: Top-p sampling parameter
            stop: Optional list of stop sequences
            
        Returns:
            Dict containing the generated text and metadata
        """
        if not LLAMA_CPP_AVAILABLE:
            return {"error": "llama-cpp-python not available"}
            
        if model_id not in self.loaded_models:
            logger.warning(f"Model {model_id} not loaded, attempting to load")
            if not self.load_model(model_id):
                return {"error": f"Failed to load model {model_id}"}
        
        # Update last used timestamp
        self.last_used[model_id] = time.time()
        
        try:
            with self.lock:
                model = self.loaded_models[model_id]
                
                # Prepare the full prompt with system prompt if provided
                full_prompt = prompt
                if system_prompt:
                    full_prompt = f"{system_prompt}\n\n{prompt}"
                
                # Generate text
                logger.debug(f"Generating text with model {model_id}, prompt: {full_prompt[:100]}...")
                
                # Use either chat_completion or completion based on the model type
                result = model.create_completion(
                    prompt=full_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    stop=stop or [],
                    stream=False
                )
                
                # Extract the generated text
                if isinstance(result, dict) and "choices" in result:
                    text = result["choices"][0]["text"]
                else:
                    text = str(result)
                
                logger.debug(f"Generated text: {text[:100]}...")
                
                return {
                    "model_id": model_id,
                    "text": text,
                    "status": "success"
                }
                
        except Exception as e:
            logger.error(f"Error generating text with model {model_id}: {e}")
            traceback.print_exc()
            return {"error": str(e), "status": "error"}
    
    def get_model_status(self, model_id: str) -> Dict[str, Any]:
        """Get the current status of a model
        
        Args:
            model_id: ID of the model to check
            
        Returns:
            Dict containing model status information
        """
        with self.lock:
            if model_id not in self.model_metadata:
                return {
                    'status': 'not_found',
                    'error': f"Model {model_id} not found in metadata"
                }
                
            model_info = self.model_metadata[model_id]
            state = self.state_tracker.get_model_status(model_id)
            
            return {
                'status': 'loaded' if state['loaded'] else 'available_not_loaded',
                'model_info': model_info,
                'state': state,
                'vram_usage': self.state_tracker.get_vram_usage()
            }
    
    def get_all_model_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all models
        
        Returns:
            Dict mapping model IDs to their status information
        """
        with self.lock:
            return {
                model_id: self.get_model_status(model_id)
                for model_id in self.model_metadata
            }
    
    def check_idle_models(self, idle_timeout_seconds: int = 300) -> List[str]:
        """Check for and unload idle models
        
        Args:
            idle_timeout_seconds: Time in seconds after which a model is considered idle
            
        Returns:
            List of model IDs that were unloaded
        """
        with self.lock:
            idle_models = self.state_tracker.check_idle_models(idle_timeout_seconds)
            unloaded_models = []
            
            for model_id in idle_models:
                if self.unload_model(model_id):
                    unloaded_models.append(model_id)
                    
            return unloaded_models
    
    def cleanup(self):
        """Clean up all loaded models"""
        with self.lock:
            for model_id in list(self.loaded_models.keys()):
                self.unload_model(model_id)
            
            # Clear dictionaries
            self.loaded_models.clear()
            
            # Run garbage collection
            gc.collect()
            
            logger.info("GGUF Model Manager cleanup complete")

    def health_check(self) -> Dict[str, Any]:
        """Perform health check for the GGUF Model Manager"""
        try:
            # Check if llama-cpp is available
            llama_available = LLAMA_CPP_AVAILABLE
            
            # Get VRAM usage
            vram_usage = self.state_tracker.get_vram_usage()
            
            # Get model status
            models_status = self.get_all_model_status()
            loaded_count = len([m for m in models_status.values() if m.get('loaded', False)])
            total_count = len(self.model_metadata)
            
            # Check for any errors in recent operations
            health_status = {
                'status': 'healthy',
                'llama_cpp_available': llama_available,
                'models_loaded': loaded_count,
                'total_models': total_count,
                'vram_usage': vram_usage,
                'timestamp': time.time()
            }
            
            # Mark as unhealthy if llama-cpp is not available
            if not llama_available:
                health_status['status'] = 'unhealthy'
                health_status['error'] = 'llama-cpp-python not available'
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': time.time()
            }

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests for the GGUF Model Manager"""
        try:
            action = request.get('action')
            
            if action == 'list_models':
                return {
                    'status': 'success',
                    'models': self.list_models()
                }
            elif action == 'load_model':
                model_id = request.get('model_id')
                if not model_id:
                    return {'status': 'error', 'error': 'model_id required'}
                success = self.load_model(model_id)
                return {
                    'status': 'success' if success else 'error',
                    'loaded': success
                }
            elif action == 'unload_model':
                model_id = request.get('model_id')
                if not model_id:
                    return {'status': 'error', 'error': 'model_id required'}
                success = self.unload_model(model_id)
                return {
                    'status': 'success' if success else 'error',
                    'unloaded': success
                }
            elif action == 'generate_text':
                model_id = request.get('model_id')
                prompt = request.get('prompt')
                if not model_id or not prompt:
                    return {'status': 'error', 'error': 'model_id and prompt required'}
                
                result = self.generate_text(
                    model_id=model_id,
                    prompt=prompt,
                    system_prompt=request.get('system_prompt'),
                    max_tokens=request.get('max_tokens', 1024),
                    temperature=request.get('temperature', 0.7)
                )
                return result
            elif action == 'health_check':
                return self.health_check()
            else:
                return {'status': 'error', 'error': f'Unknown action: {action}'}
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {'status': 'error', 'error': str(e)}

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Load model metadata
            self._load_model_metadata()
            
            # Check GGUF support
            if not LLAMA_CPP_AVAILABLE:
                logger.warning("llama-cpp-python not available. GGUF models will not work.")
            
            logger.info("GGUF Model Manager initialization complete")
            
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise

class GGUFStateTracker(BaseAgent):
    """Tracks the state and VRAM usage of GGUF models"""
    
    def __init__(self, port: int = 5576, **kwargs):
        super().__init__(port=port, name="GgufModelManager")
        self.loaded_models: Dict[str, Dict[str, Any]] = {}
        self.model_last_used: Dict[str, float] = {}
        self.total_vram_mb: float = 0
        self.used_vram_mb: float = 0
        self.lock = threading.RLock()
        
        # Initialize VRAM tracking if CUDA is available
        if torch.cuda.is_available():
            self.total_vram_mb = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)
            logger.info(f"Total GPU memory: {self.total_vram_mb:.2f} MB")
    
    def mark_model_loaded(self, model_id: str, vram_mb: float) -> None:
        """Mark a model as loaded and update VRAM tracking"""
        with self.lock:
            if model_id in self.loaded_models:
                # Already loaded, just update timestamp
                self.model_last_used[model_id] = time.time()
                return
                
            self.loaded_models[model_id] = {
                'vram_mb': vram_mb,
                'loaded_at': time.time()
            }
            self.model_last_used[model_id] = time.time()
            self.used_vram_mb += vram_mb
            
            logger.info(f"Model {model_id} marked as loaded, using {vram_mb}MB VRAM. "
                       f"Total VRAM in use: {self.used_vram_mb:.2f}MB / {self.total_vram_mb:.2f}MB")
    
    def mark_model_unloaded(self, model_id: str) -> None:
        """Mark a model as unloaded and update VRAM tracking"""
        with self.lock:
            if model_id not in self.loaded_models:
                logger.warning(f"Attempted to unload model {model_id} that was not marked as loaded")
                return
                
            vram_mb = self.loaded_models[model_id]['vram_mb']
            self.used_vram_mb -= vram_mb
            del self.loaded_models[model_id]
            del self.model_last_used[model_id]
            
            logger.info(f"Model {model_id} marked as unloaded, freed {vram_mb}MB VRAM. "
                       f"Total VRAM in use: {self.used_vram_mb:.2f}MB / {self.total_vram_mb:.2f}MB")
    
    def can_accommodate_model(self, required_vram_mb: float) -> bool:
        """Check if there's enough VRAM to load a model"""
        with self.lock:
            if not torch.cuda.is_available():
                return True  # No VRAM constraints on CPU
                
            remaining_vram = self.total_vram_mb - self.used_vram_mb
            can_fit = remaining_vram >= required_vram_mb
            
            if not can_fit:
                logger.warning(f"Cannot accommodate model requiring {required_vram_mb}MB VRAM. "
                             f"Current usage: {self.used_vram_mb:.2f}MB, "
                             f"Total: {self.total_vram_mb:.2f}MB, "
                             f"Remaining: {remaining_vram:.2f}MB")
            
            return can_fit
    
    def get_model_status(self, model_id: str) -> Dict[str, Any]:
        """Get the current status of a model"""
        with self.lock:
            if model_id not in self.loaded_models:
                return {
                    'loaded': False,
                    'vram_mb': 0,
                    'last_used': None
                }
            
            return {
                'loaded': True,
                'vram_mb': self.loaded_models[model_id]['vram_mb'],
                'loaded_at': self.loaded_models[model_id]['loaded_at'],
                'last_used': self.model_last_used[model_id]
            }
    
    def get_all_model_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all models"""
        with self.lock:
            return {
                model_id: self.get_model_status(model_id)
                for model_id in self.loaded_models
            }
    
    def get_vram_usage(self) -> Dict[str, float]:
        """Get current VRAM usage statistics"""
        with self.lock:
            return {
                'total_mb': self.total_vram_mb,
                'used_mb': self.used_vram_mb,
                'remaining_mb': self.total_vram_mb - self.used_vram_mb
            }
    
    def check_idle_models(self, idle_timeout_seconds: int = 300) -> List[str]:
        """Check for and return list of idle models"""
        with self.lock:
            current_time = time.time()
            idle_models = []
            
            for model_id, last_used in self.model_last_used.items():
                if current_time - last_used > idle_timeout_seconds:
                    idle_models.append(model_id)
            
            return idle_models

# Singleton instance
_instance = None

def get_instance() -> GGUFModelManager:
    """Get the singleton instance of the GGUF Model Manager"""
    global _instance
    if _instance is None:
        _instance = GGUFModelManager()
    return _instance

# Test code
if __name__ == "__main__":
    manager = get_instance()
    
    # List available models
    models = manager.list_models()
    print(f"Available models: {json.dumps(models, indent=2)}")
    
    # Try loading a model if any are available
    if models:
        model_id = models[0]['model_id']
        print(f"Testing model {model_id}...")
        
        # Load the model
        if manager.load_model(model_id):
            print(f"Model {model_id} loaded successfully")
            
            # Generate some text
            result = manager.generate_text(
                model_id=model_id,
                prompt="Write a Python function to reverse a string:",
                max_tokens=256
            )
            
            print(f"Generation result: {result}")
            
            # Unload the model
            if manager.unload_model(model_id):
                print(f"Model {model_id} unloaded successfully")
        else:
            print(f"Failed to load model {model_id}")
    
    # Clean up
    manager.cleanup()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
