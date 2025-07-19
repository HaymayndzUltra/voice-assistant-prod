from main_pc_code.src.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
#!/usr/bin/env python3
"""
Model Voting Manager
-------------------
Integrates the LazyVoting system with the Enhanced Model Router
to enable efficient model selection and resource management.

This module serves as the bridge between the existing routing infrastructure
and the new lazy voting capabilities.
"""

import zmq
import json
import logging
import threading
import time
import os
from pathlib import Path
from typing import Dict, Any, List, Optional


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", ".."))))
from common.utils.path_env import get_path, join_path, get_file_path
# Import the LazyVoting system
from lazy_voting import LazyVotingSystem
from common.env_helpers import get_env

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
LOG_PATH = join_path("logs", "model_voting_manager.log")
Path(LOG_PATH).parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

class ModelVotingManager(BaseAgent):
    """
    Manages model voting and selection using the LazyVoting system.
    Acts as an interface between the Enhanced Model Router and LLM backends.
    """
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ModelVotingManager")
        """
        Initialize the Model Voting Manager
        
        Args:
            zmq_port: Port to listen for voting requests
        """
        # Initialize the LazyVoting system
        self.voting_system = LazyVotingSystem()
        
        # Custom model configurations can be loaded from a config file
        self.load_model_config()
        
        # Setup ZMQ communication
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://127.0.0.1:{zmq_port}")
        
        # Connect to the model execution backend
        # This could be a direct connection to model servers or Ollama
        self.model_backend_socket = self.context.socket(zmq.REQ)
        self.model_backend_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.model_backend_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.model_backend_socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5556")  # Model Manager port
        
        self.running = True
        self.request_count = 0
        
        logging.info(f"[ModelVotingManager] Started on port {zmq_port}")
    
    def load_model_config(self):
        """Load model configuration from config file if available"""
        config_path = Path(join_path("config", "model_voting_config.json"))
        
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                
                # Update the voting system with the loaded config
                self.voting_system = LazyVotingSystem(config.get("models", None))
                logging.info(f"[ModelVotingManager] Loaded configuration from {config_path}")
            except Exception as e:
                logging.error(f"[ModelVotingManager] Error loading config: {str(e)}")
    
    def execute_model(self, model: str, prompt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a specific model through the model backend
        
        Args:
            model: Name of the model to execute
            prompt: Prompt to send to the model
            params: Additional parameters for the model
            
        Returns:
            Model response
        """
        try:
            request = {
                "model": model,
                "prompt": prompt,
                **params
            }
            
            # Send request to model backend
            self.model_backend_socket.send_string(json.dumps(request))
            response = self.model_backend_socket.recv_string()
            result = json.loads(response)
            
            # Extract the actual model response
            if "response" in result:
                return {
                    "model": model,
                    "response": result["response"],
                    "confidence": result.get("confidence", 0.8)
                }
            else:
                logging.error(f"[ModelVotingManager] Error executing model {model}: {result.get('error', 'Unknown error')}")
                return {
                    "model": model,
                    "response": f"Error: {result.get('error', 'Unknown error')}",
                    "confidence": 0.1
                }
        except Exception as e:
            logging.error(f"[ModelVotingManager] Error executing model {model}: {str(e)}")
            return {
                "model": model,
                "response": f"Error: {str(e)}",
                "confidence": 0.1
            }
    
    def _monkey_patch_voting_system(self):
        """
        Monkey patch the LazyVoting system to use our execute_model method
        instead of its simulated version
        """
        original_execute = self.voting_system.execute_model
        
        def patched_execute(model, prompt, task_data=None):
            # Use original for tracking and stats
            original_execute(model, prompt, task_data)
            
            # Actually execute the model
            return self.execute_model(model, prompt, task_data or {})
        
        self.voting_system.execute_model = patched_execute
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a model voting request
        
        Args:
            request: Request data including prompt and task info
            
        Returns:
            Result with the winning model response and metadata
        """
        self.request_count += 1
        request_id = f"req_{self.request_count}"
        
        prompt = request.get("prompt", "")
        if not prompt:
            return {"error": "No prompt provided"}
        
        # Extract task data for model selection
        task_data = {
            "type": request.get("type", "general"),
            "agent": request.get("agent"),
            "max_tokens": request.get("max_tokens"),
            "temperature": request.get("temperature", 0.7),
            "request_id": request_id
        }
        
        # Log request
        logging.info(f"[ModelVotingManager] Request {request_id}: {task_data['type']} from {task_data['agent'] or 'unknown'}")
        
        # Use lazy voting to get the best response
        start_time = time.time()
        result = self.voting_system.lazy_vote(prompt, task_data)
        elapsed = time.time() - start_time
        
        # Add timing information
        result["timing"] = {
            "total_seconds": elapsed,
            "request_id": request_id
        }
        
        # Log result
        logging.info(f"[ModelVotingManager] Request {request_id} completed in {elapsed:.2f}s using models: {', '.join(result.get('models_consulted', []))}")
        
        return result
    
    def run(self):
        """Run the Model Voting Manager service loop"""
        # Patch the voting system to use real model execution
        self._monkey_patch_voting_system()
        
        # Main service loop
        logging.info("[ModelVotingManager] Starting service loop")
        while self.running:
            try:
                # Wait for request
                request_data = self.socket.recv_string()
                request = json.loads(request_data)
                
                # Process request
                result = self.handle_request(request)
                
                # Send response
                self.socket.send_string(json.dumps(result))
            except Exception as e:
                logging.error(f"[ModelVotingManager] Error processing request: {str(e)}")
                # Send error response
                try:
                    self.socket.send_string(json.dumps({"error": str(e)}))
                except:
                    pass
    
    def stop(self):
        """Stop the service"""
        self.running = False
        logging.info("[ModelVotingManager] Service stopped")


def main():
    """Main entry point"""
    manager = ModelVotingManager()
    
    # Start in a background thread
    thread = threading.Thread(target=manager.run)
    thread.daemon = True
    thread.start()
    
    logging.info("[ModelVotingManager] Service started in background thread")
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("[ModelVotingManager] Received shutdown signal")
        manager.stop()


if __name__ == "__main__":
    main()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise