#!/usr/bin/env python3
"""
Memory Client

This agent provides a client interface to the memory orchestrator,
allowing other agents to store and retrieve memories.
"""

import os
import json
import zmq
import logging
from typing import Dict, Any, Optional
from common.core.base_agent import BaseAgent

logger = logging.getLogger("MemoryClient")

def get_service_address(service_name: str) -> str:
    # Dummy implementation; replace with actual service discovery if available
    return os.environ.get("MEMORY_ORCHESTRATOR_ADDR", "tcp://192.168.1.102:7115")

class MemoryClient(
    """
    MemoryClient:  Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
    """BaseAgent):
    def __init__(self, agent_name="MemoryClient", port=5713):
        super().__init__(agent_name, port)
        self.orchestrator_socket = None
        self._initialize_client_socket()

    

        self.error_bus_port = 7150

        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')

        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"

        self.error_bus_pub = self.context.socket(zmq.PUB)

        self.error_bus_pub.connect(self.error_bus_endpoint)
def _initialize_client_socket(self):
        try:
            connection_str = get_service_address("MemoryOrchestratorService")
            logger.info(f"Connecting to MemoryOrchestratorService at {connection_str}")
            self.context = zmq.Context()
            self.orchestrator_socket = self.context.socket(zmq.REQ)
            self.orchestrator_socket.connect(connection_str)
            self.orchestrator_socket.setsockopt(zmq.LINGER, 0)
            self.orchestrator_socket.setsockopt(zmq.RCVTIMEO, 5000)
            self.orchestrator_socket.setsockopt(zmq.SNDTIMEO, 5000)
        except Exception as e:
            logger.error(f"Failed to initialize client socket: {e}", exc_info=True)
            self.orchestrator_socket = None

    def _send_request(self, request_payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.orchestrator_socket:
            logger.error("Cannot send request: Orchestrator socket is not initialized.")
            return {"status": "error", "message": "Client not connected to orchestrator."}
        try:
            self.orchestrator_socket.send_json(request_payload)
            response = self.orchestrator_socket.recv_json()
            if isinstance(response, dict):
                return response
            return {"status": "error", "message": "Malformed response from orchestrator."}
        except zmq.error.Again:
            logger.error("Request to MemoryOrchestratorService timed out.")
            self._initialize_client_socket()
            return {"status": "error", "message": "Request timed out. Reconnection attempted."}
        except Exception as e:
            logger.error(f"Error communicating with MemoryOrchestratorService: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    # --- API Methods ---
    def add_memory(self, content: str, memory_type: str, metadata: Optional[Dict[str, Any]] = None, parent_id: Optional[int] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "action": "add_memory",
            "content": content,
            "memory_type": memory_type,
        }
        if metadata is not None:
            payload["metadata"] = metadata
        if parent_id is not None:
            payload["parent_id"] = parent_id
        return self._send_request(payload)

    def get_memory(self, memory_id: int) -> Dict[str, Any]:
        payload = {
            "action": "get_memory",
            "memory_id": memory_id
        }
        return self._send_request(payload)

    def search_memory(self, query: str, memory_type: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "action": "search_memory",
            "query": query,
            "limit": limit
        }
        if memory_type is not None:
            payload["memory_type"] = memory_type
        return self._send_request(payload)

    def update_memory(self, memory_id: int, update_payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "action": "update_memory",
            "memory_id": memory_id,
            "payload": update_payload
        }
        return self._send_request(payload)

    def delete_memory(self, memory_id: int) -> Dict[str, Any]:
        payload = {
            "action": "delete_memory",
            "memory_id": memory_id
        }
        return self._send_request(payload)

    def get_children(self, parent_id: int) -> Dict[str, Any]:
        payload = {
            "action": "get_children",
            "parent_id": parent_id
        }
        return self._send_request(payload)

    def semantic_search(self, query: str, k: int = 5) -> Dict[str, Any]:
        payload = {
            "action": "semantic_search",
            "query": query,
            "k": k
        }
        return self._send_request(payload)

    def process_request(self, request: dict) -> dict:
        # This client is not intended to receive requests; method is a no-op for compliance.
        return {"status": "noop"} 