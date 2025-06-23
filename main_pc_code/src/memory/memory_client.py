#!/usr/bin/env python3
"""
Memory Client

This agent provides a client interface to the memory orchestrator,
allowing other agents to store and retrieve memories.
"""

import os
import sys
import time
import json
import zmq
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

# Add project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("MemoryClient")

class MemoryClient:
    """Client for interacting with the Memory Orchestrator"""
    
    def __init__(self, port: int = 5577, orchestrator_port: int = 5576, host: str = "0.0.0.0"):
        self.port = port
        self.host = host
        self.orchestrator_port = orchestrator_port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://{host}:{port}")
        logger.info(f"Memory Client initialized on port {port}")
        
        # Setup connection to Memory Orchestrator
        self.orchestrator_socket = self.context.socket(zmq.REQ)
        self.orchestrator_socket.connect(f"tcp://localhost:{orchestrator_port}")
        logger.info(f"Connected to Memory Orchestrator on port {orchestrator_port}")
        
        # Setup health check socket
        self.health_port = port + 1
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.bind(f"tcp://{host}:{self.health_port}")
        logger.info(f"Health check endpoint initialized on port {self.health_port}")
        
        # Start health check thread
        self._start_health_check()
    
    def _start_health_check(self):
        """Start a separate thread for health checks"""
        import threading
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
                        "agent": "MemoryClient",
                        "uptime": time.time() - self.start_time,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
            except Exception as e:
                logger.error(f"Health check error: {e}")
            time.sleep(0.1)
    
    def start(self):
        """Start the memory client service"""
        self.start_time = time.time()
        logger.info("Memory Client starting")
        
        try:
            while True:
                # Wait for requests
                message = self.socket.recv_json()
                logger.info(f"Received request: {message}")
                
                action = message.get("action")
                if action == "store_memory":
                    response = self._handle_store_memory(message)
                elif action == "retrieve_memory":
                    response = self._handle_retrieve_memory(message)
                elif action == "health_check":
                    response = self._handle_health_check()
                else:
                    response = {"status": "error", "message": f"Unknown action: {action}"}
                
                self.socket.send_json(response)
        except KeyboardInterrupt:
            logger.info("Shutting down Memory Client")
        except Exception as e:
            logger.error(f"Error in Memory Client: {e}")
        finally:
            self.socket.close()
            self.orchestrator_socket.close()
            self.context.term()
    
    def _handle_store_memory(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Forward store memory request to the orchestrator"""
        try:
            self.orchestrator_socket.send_json(message)
            response = self.orchestrator_socket.recv_json()
            return response
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            return {"status": "error", "message": str(e)}
    
    def _handle_retrieve_memory(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Forward retrieve memory request to the orchestrator"""
        try:
            self.orchestrator_socket.send_json(message)
            response = self.orchestrator_socket.recv_json()
            return response
        except Exception as e:
            logger.error(f"Error retrieving memory: {e}")
            return {"status": "error", "message": str(e)}
    
    def _handle_health_check(self) -> Dict[str, Any]:
        """Handle health check request"""
        return {
            "status": "HEALTHY",
            "agent": "MemoryClient",
            "uptime": time.time() - self.start_time,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

def main():
    parser = argparse.ArgumentParser(description="Memory Client")
    parser.add_argument("--port", type=int, default=5577, help="Port to listen on")
    parser.add_argument("--orchestrator_port", type=int, default=5576, help="Memory Orchestrator port")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()
    
    client = MemoryClient(port=args.port, orchestrator_port=args.orchestrator_port, host=args.host)
    client.start()

if __name__ == "__main__":
    main() 