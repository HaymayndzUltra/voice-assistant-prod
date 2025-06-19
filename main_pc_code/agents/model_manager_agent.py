"""
Model Manager Agent implementation
Manages loading and unloading of AI models
"""

import os
import sys
import json
import time
import logging
import threading
import zmq
from typing import Dict, Any, Optional
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.base_agent import BaseAgent
from utils.config_parser import parse_agent_args

logger = logging.getLogger(__name__)

# Add model idle timeout (default 10 minutes)
MODEL_IDLE_TIMEOUT = 600  # seconds

class ModelManagerAgent(BaseAgent):
    def __init__(self, port: int = 5570, host: str = "localhost"):
        """Initialize Model Manager Agent.
        
        Args:
            port: Port to bind to (default: 5570)
            host: Host to bind to (default: localhost)
        """
        super().__init__(port=port, name="ModelManagerAgent")
        
        # Initialize model tracking
        self.loaded_models = {}
        self.model_queue = []
        self.model_status = {}
        self.model_configs = {}
        self.initialization_status = {
            "is_initialized": False,
            "error": None,
            "progress": 0.0
        }
        self.model_last_used_timestamp = {}
        
        # Start initialization in background
        self.init_thread = threading.Thread(target=self._perform_initialization, daemon=True)
        self.init_thread.start()
        
    def _perform_initialization(self):
        """Perform agent initialization in background."""
        try:
            # Load model configurations
            self._load_model_configs()
            
            # Mark as initialized
            self.initialization_status.update({
                "is_initialized": True,
                "progress": 1.0
            })
            logger.info("ModelManagerAgent initialization complete")
            
        except Exception as e:
            self.initialization_status.update({
                "error": str(e),
                "progress": 0.0
            })
            logger.error(f"Initialization failed: {e}")
            
    def _load_model_configs(self):
        """Load model configurations from file."""
        try:
            config_path = os.path.join("config", "model_configs.json")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    self.model_configs = json.load(f)
            else:
                logger.warning(f"Model config file not found at {config_path}")
                self.model_configs = {}
        except Exception as e:
            logger.error(f"Error loading model configs: {e}")
            self.model_configs = {}
            
    def _get_health_status(self) -> Dict[str, Any]:
        """Get detailed health status including model information."""
        base_status = super()._get_health_status()
        
        # Add model-specific metrics and initialization status
        base_status.update({
            "loaded_models": len(self.loaded_models),
            "model_queue_size": len(self.model_queue),
            "model_status": self.model_status,
            "initialization_status": self.initialization_status
        })
        
        return base_status
        
    def handle_request(self, request: Dict) -> Dict:
        """Handle incoming requests."""
        action = request.get("action")
        
        if action == "load_model":
            # Check if initialization is complete
            if not self.initialization_status["is_initialized"]:
                return {
                    "status": "error",
                    "error": "Model manager is still initializing",
                    "initialization_status": self.initialization_status
                }
                
            model_id = request.get("model_id")
            if not model_id:
                return {"status": "error", "error": "No model_id provided"}
                
            if model_id in self.loaded_models:
                return {"status": "error", "error": "Model already loaded"}
                
            if model_id not in self.model_configs:
                return {"status": "error", "error": "Model not found in configs"}
                
            # Add to queue
            self.model_queue.append(model_id)
            return {"status": "ok", "message": f"Model {model_id} queued for loading"}
            
        elif action == "get_model_status":
            model_id = request.get("model_id")
            if not model_id:
                return {"status": "error", "error": "No model_id provided"}
                
            if model_id not in self.model_status:
                return {"status": "error", "error": "Model not found"}
                
            return {
                "status": "ok",
                "model_status": self.model_status[model_id]
            }
            
        return super().handle_request(request)
        
    def run(self):
        """Main agent loop with model management."""
        logger.info("Starting ModelManagerAgent main loop...")
        
        while self.running:
            try:
                # Process model queue
                if self.model_queue and self.initialization_status["is_initialized"]:
                    model_id = self.model_queue.pop(0)
                    self._load_model(model_id)
                    
                # Handle requests
                if self.socket.poll(timeout=1000) != 0:
                    message = self.socket.recv_json()
                    response = self.handle_request(message)
                    self.socket.send_json(response)
                    
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(1)
                
    def _load_model(self, model_id: str):
        """Load a model and update its status."""
        try:
            logger.info(f"Loading model {model_id}")
            self.model_status[model_id] = {
                "status": "loading",
                "start_time": time.time()
            }
            
            # TODO: Implement actual model loading logic
            
            self.model_status[model_id].update({
                "status": "loaded",
                "load_time": time.time() - self.model_status[model_id]["start_time"]
            })
            
            logger.info(f"Model {model_id} loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading model {model_id}: {e}")
            self.model_status[model_id].update({
                "status": "error",
                "error": str(e)
            })

    def _get_model(self, model_id):
        """Get or load the model lazily. Unload if idle for too long."""
        now = time.time()
        # Unload models that have been idle for too long
        to_unload = []
        for mid, last_used in self.model_last_used_timestamp.items():
            if now - last_used > MODEL_IDLE_TIMEOUT:
                self._unload_model(mid)
                to_unload.append(mid)
        for mid in to_unload:
            del self.model_last_used_timestamp[mid]
        # Lazy load
        if model_id not in self.loaded_models:
            self._load_model(model_id)
        self.model_last_used_timestamp[model_id] = now
        return self.loaded_models.get(model_id)

if __name__ == "__main__":
    args = parse_agent_args()
    port = getattr(args, 'port', 5570)
    host = getattr(args, 'host', 'localhost')
    agent = ModelManagerAgent(port=port, host=host)
    agent.run()
    # Keep the process alive if run() returns (should not happen, but for safety)
    import time
    while True:
        time.sleep(1)