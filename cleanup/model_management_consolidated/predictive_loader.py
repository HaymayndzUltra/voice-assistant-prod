#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

Predictive Loader Agent

This agent predicts which models will be needed in the near future
and preloads them to minimize latency.
"""

import os
import sys
import time
import json
import zmq
import logging
import argparse
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from common.core.base_agent import BaseAgent

# Add project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import config parser
from main_pc_code.utils.config_loader import load_config

# Parse agent arguments
config = load_config()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("PredictiveLoader")

class PredictiveLoader(BaseAgent):
    """Predictive Loader Agent for preloading models based on usage patterns Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:')."""
    
    def __init__(self, **kwargs):
        super().__init__()

    
        self.port = port

    
        self.host = host

    
        self.request_coordinator_port = request_coordinator_port

    
        self.context = zmq.Context()

    
        self.socket = self.context.socket(zmq.REP)

    
        self.socket.bind(f"tcp://{host}:{port}")

    
        logger.info(f"Predictive Loader initialized on port {port}")

    
        # Setup connection to RequestCoordinator

    
        self.request_coordinator_socket = self.context.socket(zmq.REQ)

    
        self.request_coordinator_socket.connect(get_zmq_connection_string({request_coordinator_port}, "localhost"))

    
        logger.info(f"Connected to RequestCoordinator on port {request_coordinator_port}")

    
        # Setup health check socket

    
        self.health_port = port + 1

    
        self.health_socket = self.context.socket(zmq.REP)

    
        self.health_socket.bind(f"tcp://{host}:{self.health_port}")

    
        logger.info(f"Health check endpoint initialized on port {self.health_port}")

    
        # Initialize model usage patterns

    
        self.model_usage = {}

    
        self.prediction_window = 3600  # 1 hour

    
        self.lookahead_window = 300    # 5 minutes

    
        # Start health check thread

    
        self._start_health_check()
        self.port = self.config.getint('predictive_loader.port', 5617)
        self.request_coordinator_port = self.config.getint('dependencies.request_coordinator_port', 8571)
        self.host = self.config.get('network.bind_address', '0.0.0.0')
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://{self.host}:{self.port}")
        logger.info(f"Predictive Loader initialized on port {self.port}")
        
        # Setup connection to RequestCoordinator
        self.request_coordinator_socket = self.context.socket(zmq.REQ)
        self.request_coordinator_socket.connect(get_zmq_connection_string({self.request_coordinator_port}, "localhost")))
        logger.info(f"Connected to RequestCoordinator on port {self.request_coordinator_port}")
        
        # Setup health check socket
        self.health_port = self.port + 1
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.bind(f"tcp://{self.host}:{self.health_port}")
        logger.info(f"Health check endpoint initialized on port {self.health_port}")
        
        # Initialize model usage patterns
        self.model_usage = {}
        self.prediction_window = 3600  # 1 hour
        self.lookahead_window = 300    # 5 minutes
        
        # Add name attribute for standardized main block
        self.name = "PredictiveLoader"
        self.running = True
        self.start_time = time.time()
        
        # Start health check thread
        self._start_health_check()
    
    

        self.error_bus_port = 7150

        self.error_bus_host = get_service_ip("pc2")

        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"

        self.error_bus_pub = self.context.socket(zmq.PUB)

        self.error_bus_pub.connect(self.error_bus_endpoint)

    def _get_health_status(self):
        # Standard health check.
        return {'status': 'ok', 'running': self.running}
    
    def _start_health_check(self):
        """Start a separate thread for health checks"""
        self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_thread.start()
        # Track for graceful shutdown
        if not hasattr(self, "_background_threads"):
            self._background_threads = []
        self._background_threads.append(self.health_thread)
    
    def run(self):
        """Run the predictive loader service (standard entrypoint)"""
        self.start_time = time.time()
        logger.info("Predictive Loader starting")
        
        # Start prediction thread
        prediction_thread = threading.Thread(target=self._prediction_loop, daemon=True)
        prediction_thread.start()
        # Track prediction thread for shutdown
        self.prediction_thread = prediction_thread
        if not hasattr(self, "_background_threads"):
            self._background_threads = []
        self._background_threads.append(prediction_thread)
        
        try:
            while True:
                # Wait for requests
                message = self.socket.recv_json()
                logger.info(f"Received request: {message}")
                
                action = message.get("action")
                if action == "predict_models":
                    response = self._handle_predict_models(message)
                elif action == "record_usage":
                    response = self._handle_record_usage(message)
                elif action == "health_check":
                    response = self._handle_health_check()
                else:
                    response = {"status": "error", "message": f"Unknown action: {action}"}
                
                self.socket.send_json(response)
        except KeyboardInterrupt:
            logger.info("Shutting down Predictive Loader")
        except Exception as e:
            logger.error(f"Error in Predictive Loader: {e}")
        finally:
            self.socket.close()
            self.request_coordinator_socket.close()
            self.context.term()
    
    def _prediction_loop(self):
        """Background thread that periodically predicts model usage"""
        while True:
            try:
                predicted_models = self._predict_models()
                if predicted_models:
                    logger.info(f"Predicted models for preloading: {predicted_models}")
                    self._preload_models(predicted_models)
            except Exception as e:
                logger.error(f"Error in prediction loop: {e}")
            time.sleep(60)  # Run predictions every minute
    
    def _predict_models(self) -> List[str]:
        """Predict which models will be needed in the near future"""
        # Simple prediction algorithm based on recent usage frequency
        current_time = time.time()
        recent_usage = {}
        
        for model_id, usages in self.model_usage.items():
            # Filter to recent usage within prediction window
            recent = [u for u in usages if current_time - u < self.prediction_window]
            if recent:
                recent_usage[model_id] = len(recent)
        
        # Sort by frequency
        sorted_models = sorted(recent_usage.items(), key=lambda x: x[1], reverse=True)
        return [model_id for model_id, _ in sorted_models[:3]]  # Top 3 models
    
    def _preload_models(self, model_ids: List[str]):
        """Request model preloading from the model manager"""
        for model_id in model_ids:
            try:
                # Notify RequestCoordinator about model prediction
                message = {
                    "action": "preload_model",
                    "model_id": model_id,
                    "priority": "low",
                    "source": "PredictiveLoader"
                }
                self.request_coordinator_socket.send_json(message)
                response = self.request_coordinator_socket.recv_json()
                logger.info(f"Preload request response: {response}")
            except Exception as e:
                logger.error(f"Error requesting model preload: {e}")
    
    def _handle_predict_models(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to predict which models will be needed"""
        try:
            predicted_models = self._predict_models()
            return {
                "status": "success",
                "predicted_models": predicted_models
            }
        except Exception as e:
            logger.error(f"Error predicting models: {e}")
            return {"status": "error", "message": str(e)}
    
    def _handle_record_usage(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Record model usage for future predictions"""
        try:
            model_id = message.get("model_id")
            if not model_id:
                return {"status": "error", "message": "No model_id provided"}
            
            if model_id not in self.model_usage:
                self.model_usage[model_id] = []
            
            self.model_usage[model_id].append(time.time())
            logger.info(f"Recorded usage of model {model_id}")
            
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Error recording model usage: {e}")
            return {"status": "error", "message": str(e)}
    
    def _handle_health_check(self) -> Dict[str, Any]:
        """Handle health check request"""
        return {
            "status": "HEALTHY",
            "agent": "PredictiveLoader",
            "uptime": time.time() - self.start_time,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up PredictiveLoader resources...")
        
        # Close sockets
        if hasattr(self, 'socket'):
            self.socket.close()
            logger.info("Main socket closed")
            
        if hasattr(self, 'request_coordinator_socket'):
            self.request_coordinator_socket.close()
            logger.info("RequestCoordinator socket closed")
            
        if hasattr(self, 'health_socket'):
            self.health_socket.close()
            logger.info("Health socket closed")
            
        # Terminate ZMQ context
        if hasattr(self, 'context'):
            self.context.term()
            logger.info("ZMQ context terminated")
            
        logger.info("PredictiveLoader cleanup complete")

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = PredictiveLoader()
        agent.run() # Use .run() for standardization
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
from main_pc_code.utils.network_utils import get_zmq_connection_string, get_machine_ip
from common.env_helpers import get_env
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup() 