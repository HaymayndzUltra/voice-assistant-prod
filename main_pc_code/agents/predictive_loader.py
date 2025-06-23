#!/usr/bin/env python3
"""
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

# Add project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("PredictiveLoader")

class PredictiveLoader:
    """Predictive Loader Agent for preloading models based on usage patterns"""
    
    def __init__(self, port: int = 5617, task_router_port: int = 8571, host: str = "0.0.0.0"):
        self.port = port
        self.host = host
        self.task_router_port = task_router_port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://{host}:{port}")
        logger.info(f"Predictive Loader initialized on port {port}")
        
        # Setup connection to Task Router
        self.task_router_socket = self.context.socket(zmq.REQ)
        self.task_router_socket.connect(f"tcp://localhost:{task_router_port}")
        logger.info(f"Connected to Task Router on port {task_router_port}")
        
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
    
    def _start_health_check(self):
        """Start a separate thread for health checks"""
        self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_thread.start()
    
    def _health_check_loop(self):
        """Health check loop running in a separate thread"""
        poller = zmq.Poller()
        poller.register(self.health_socket, zmq.POLLIN)
        
        while True:
            try:
                socks = dict(poller.poll(1000))  # 1 second timeout
                if self.health_socket in socks:
                    message = self.health_socket.recv_json()
                    self.health_socket.send_json({
                        "status": "HEALTHY",
                        "agent": "PredictiveLoader",
                        "uptime": time.time() - self.start_time,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
            except Exception as e:
                logger.error(f"Health check error: {e}")
            time.sleep(0.1)
    
    def start(self):
        """Start the predictive loader service"""
        self.start_time = time.time()
        logger.info("Predictive Loader starting")
        
        # Start prediction thread
        prediction_thread = threading.Thread(target=self._prediction_loop, daemon=True)
        prediction_thread.start()
        
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
            self.task_router_socket.close()
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
                # Notify Task Router about model prediction
                message = {
                    "action": "preload_model",
                    "model_id": model_id,
                    "priority": "low",
                    "source": "PredictiveLoader"
                }
                self.task_router_socket.send_json(message)
                response = self.task_router_socket.recv_json()
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

def main():
    parser = argparse.ArgumentParser(description="Predictive Loader")
    parser.add_argument("--port", type=int, default=5617, help="Port to listen on")
    parser.add_argument("--task_router_port", type=int, default=8571, help="Task Router port")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()
    
    loader = PredictiveLoader(port=args.port, task_router_port=args.task_router_port, host=args.host)
    loader.start()

if __name__ == "__main__":
    main() 