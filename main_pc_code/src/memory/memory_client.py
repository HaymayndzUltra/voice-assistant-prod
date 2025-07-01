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

from main_pc_code.src.core.base_agent import BaseAgent
from utils.config_loader import parse_agent_args

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("MemoryClient")

_agent_args = parse_agent_args()

class MemoryClient(BaseAgent):
    """Client for interacting with the Memory Orchestrator"""
    
    def __init__(self):
        self.port = _agent_args.get('port')
        super().__init__(_agent_args)
        self.host = _agent_args.get('host', "<BIND_ADDR>")
        self.orchestrator_port = int(_agent_args.get('orchestrator_port', 12345))
        self.context = zmq.Context()
        self.orchestrator_socket = self.context.socket(zmq.REQ)
        self.orchestrator_socket.connect(f"tcp://localhost:{self.orchestrator_port}")
        logger.info(f"Connected to Memory Orchestrator on port {self.orchestrator_port}")
        self.requests_sent = 0
        self.orchestrator_connection_status = "connected"

    def _get_health_status(self):
        """Overrides the base method to add agent-specific health metrics."""
        base_status = super()._get_health_status()
        specific_metrics = {
            "client_status": "active",
            "orchestrator_connection": getattr(self, 'orchestrator_connection_status', 'unknown'),
            "requests_sent": getattr(self, 'requests_sent', 0)
        }
        base_status.update(specific_metrics)
        return base_status

    def start(self):
        """Start the memory client service"""
        self.start_time = time.time()
        logger.info("Memory Client starting")
        try:
            while True:
                message = self.socket.recv_json()
                if not isinstance(message, dict):
                    if isinstance(message, str):
                        try:
                            message = json.loads(message)
                        except Exception:
                            logger.error(f"Received non-dict, non-JSON message: {message}")
                            self.socket.send_json({"status": "error", "message": "Invalid request format"})
                            continue
                    else:
                        logger.error(f"Received non-dict, non-str message: {message}")
                        self.socket.send_json({"status": "error", "message": "Invalid request format"})
                        continue
                logger.info(f"Received request: {message}")
                action = message.get("action")
                if action == "store_memory":
                    response = self._handle_store_memory(message)
                elif action == "retrieve_memory":
                    response = self._handle_retrieve_memory(message)
                elif action == "health_check":
                    response = self._get_health_status()
                else:
                    response = {"status": "error", "message": f"Unknown action: {action}"}
                if not isinstance(response, dict):
                    response = {"status": "error", "message": "Invalid response format"}
                self.socket.send_json(response)
        except KeyboardInterrupt:
            logger.info("Shutting down Memory Client")
        except Exception as e:
            logger.error(f"Error in Memory Client: {e}")
        finally:
            self.cleanup()

    def _handle_store_memory(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Forward store memory request to the orchestrator"""
        try:
            self.orchestrator_socket.send_json(message)
            self.requests_sent = getattr(self, 'requests_sent', 0) + 1
            response = self.orchestrator_socket.recv_json()
            if not isinstance(response, dict):
                return {"status": "error", "message": "Invalid response from orchestrator"}
            return response
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            return {"status": "error", "message": str(e)}

    def _handle_retrieve_memory(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Forward retrieve memory request to the orchestrator"""
        try:
            self.orchestrator_socket.send_json(message)
            self.requests_sent = getattr(self, 'requests_sent', 0) + 1
            response = self.orchestrator_socket.recv_json()
            if not isinstance(response, dict):
                return {"status": "error", "message": "Invalid response from orchestrator"}
            return response
        except Exception as e:
            logger.error(f"Error retrieving memory: {e}")
            return {"status": "error", "message": str(e)}

    def cleanup(self):
        """Cleanup resources and call parent cleanup."""
        try:
            self.socket.close()
            self.orchestrator_socket.close()
            self.context.term()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        super().cleanup()

def main():
    client = MemoryClient()
    client.start()

if __name__ == "__main__":
    main() 