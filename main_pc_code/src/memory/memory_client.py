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
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

# Add project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("MemoryClient")

# Load configuration at module level
config = load_config()

class MemoryClient(BaseAgent):
    """Client for interacting with the Memory Orchestrator"""
    
    def __init__(self, port=None):
        # Get configuration values with fallbacks
        agent_port = config.get("port", 5644) if port is None else port
        agent_name = config.get("name", "MemoryClient")
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=agent_name, port=agent_port)
        
        # Get orchestrator connection details
        self.host = config.get("host", "localhost") 
        self.orchestrator_port = int(config.get("orchestrator_port", 5576))
        
        # Connect to the orchestrator
        self.orchestrator_socket = self.context.socket(zmq.REQ)
        self.orchestrator_socket.connect(f"tcp://{self.host}:{self.orchestrator_port}")
        logger.info(f"Connected to Memory Orchestrator on port {self.orchestrator_port}")
        
        # Initialize metrics
        self.requests_sent = 0
        self.orchestrator_connection_status = "connected"
        self.start_time = time.time()

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

    def run(self):
        """Start the memory client service"""
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

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = MemoryClient()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup() 