#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Memory Client

This agent provides a client interface to the memory orchestrator,
allowing other agents to store and retrieve memories.
"""

import os
import json
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import logging
import time
from typing import Dict, Any, Optional, List, Union
from common.core.base_agent import BaseAgent

from main_pc_code.utils.config_loader import load_config

# Load configuration at the module level
config = load_config()


logger = logging.getLogger("MemoryClient")

def get_service_address(service_name: str) -> str:
    # Use environment variable if available, otherwise use PC2 default IP with correct port
    pc2_ip = os.environ.get("PC2_IP", get_service_ip("pc2"))
    memory_orchestrator_port = 7140  # Updated to correct port from PC2 config
    return os.environ.get("MEMORY_ORCHESTRATOR_ADDR", f"tcp://{pc2_ip}:{memory_orchestrator_port}")

class CircuitBreaker:
    """
    Circuit breaker pattern implementation to prevent cascading failures.
    """
    def __init__(self, failure_threshold: int = 3, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def record_success(self):
        """Record a successful operation and reset the circuit breaker if needed."""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failure_count = 0
            logger.info("Circuit breaker reset to CLOSED state after successful operation")
        
    def record_failure(self):
        """Record a failed operation and potentially open the circuit."""
        current_time = time.time()
        
        if self.state == "OPEN":
            # Check if we should try again (half-open state)
            if current_time - self.last_failure_time >= self.reset_timeout:
                logger.info("Circuit breaker entering HALF_OPEN state")
                self.state = "HALF_OPEN"
            return
            
        self.failure_count += 1
        self.last_failure_time = current_time
        
        if self.failure_count >= self.failure_threshold:
            logger.warning(f"Circuit breaker tripped after {self.failure_count} failures")
            self.state = "OPEN"
    
    def is_closed(self) -> bool:
        """Check if the circuit is closed or in half-open state."""
        current_time = time.time()
        
        # If circuit is open but reset timeout has passed, allow a trial request
        if self.state == "OPEN" and current_time - self.last_failure_time >= self.reset_timeout:
            logger.info("Circuit breaker entering HALF_OPEN state")
            self.state = "HALF_OPEN"
            
        return self.state != "OPEN"
        
    def get_state(self) -> str:
        """Get the current state of the circuit breaker."""
        return self.state

class MemoryClient(BaseAgent):
    """
    MemoryClient: Provides a thin client interface to the central MemoryOrchestratorService on PC2.
    Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
    Implements circuit breaker pattern for resilience.
    """
    def __init__(self, agent_name="MemoryClient", port=5713, **kwargs):
        super().__init__(agent_name, port, **kwargs)
        self.orchestrator_socket = None
        
        # Client identity
        self._agent_id = agent_name
        self._session_id = None
        
        # Circuit breaker for resilience
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=kwargs.get("failure_threshold", 3),
            reset_timeout=kwargs.get("reset_timeout", 60)
        )
        
        # Error bus configuration
        self.error_bus_port = 7150
        self.error_bus_host = get_service_ip("pc2")
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)
        
        # Track connection status and retry information
        self.connected = False
        self.last_connection_attempt = 0
        self.connection_retry_interval = kwargs.get("connection_retry_interval", 10)  # seconds
        self.request_timeout = kwargs.get("request_timeout", 5000)  # milliseconds
        
        # Initialize connection
        self._initialize_client_socket()
        
        logger.info(f"MemoryClient initialized, connecting to orchestrator at {get_service_address('MemoryOrchestratorService')}")

    def _initialize_client_socket(self):
        try:
            connection_str = get_service_address("MemoryOrchestratorService")
            logger.info(f"Connecting to MemoryOrchestratorService at {connection_str}")
            
            # Close existing socket if any
            if self.orchestrator_socket:
                self.orchestrator_
            self.orchestrator_socket = self.context.socket(zmq.REQ)
            self.orchestrator_socket.connect(connection_str)
            self.orchestrator_socket.setsockopt(zmq.LINGER, 0)
            self.orchestrator_socket.setsockopt(zmq.RCVTIMEO, self.request_timeout)
            self.orchestrator_socket.setsockopt(zmq.SNDTIMEO, self.request_timeout)
            self.connected = True
            logger.info("Successfully connected to MemoryOrchestratorService")
        except Exception as e:
            logger.error(f"Failed to initialize client socket: {e}", exc_info=True)
            self.orchestrator_socket = None
            self.connected = False
            self._report_error("connection_failure", f"Failed to connect to MemoryOrchestratorService: {e}")

    def _report_error(self, error_type: str, error_message: str):
        """Report errors to the central error bus"""
        try:
            error_data = {
                "timestamp": time.time(),
                "agent": self.name,
                "error_type": error_type,
                "message": error_message,
                "severity": "ERROR"
            }
            self.error_bus_pub.send_string(f"ERROR:{json.dumps(error_data)}")
        except Exception as e:
            logger.error(f"Failed to report error to error bus: {e}")

    def _send_request(self, request_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a request to the MemoryOrchestratorService with circuit breaker protection.
        """
        # Check if circuit breaker is open
        if not self.circuit_breaker.is_closed():
            logger.warning("Circuit breaker is open, refusing to send request")
            return {
                "status": "error", 
                "message": f"Circuit breaker is open due to previous failures. Try again later.",
                "circuit_state": self.circuit_breaker.get_state()
            }
        
        # Check if we need to retry connection
        current_time = time.time()
        if not self.connected and (current_time - self.last_connection_attempt > self.connection_retry_interval):
            self._initialize_client_socket()
            self.last_connection_attempt = current_time
            
        if not self.orchestrator_socket:
            logger.error("Cannot send request: Orchestrator socket is not initialized.")
            return {"status": "error", "message": "Client not connected to orchestrator."}
            
        try:
            self.orchestrator_socket.send_json(request_payload)
            response = self.orchestrator_socket.recv_json()
            
            # Record success with circuit breaker
            self.circuit_breaker.record_success()
            
            if isinstance(response, dict):
                return response
            return {"status": "error", "message": "Malformed response from orchestrator."}
        except zmq.error.Again:
            logger.error("Request to MemoryOrchestratorService timed out.")
            self.connected = False
            
            # Record failure with circuit breaker
            self.circuit_breaker.record_failure()
            
            # Try to reconnect
            self._initialize_client_socket()
            return {"status": "error", "message": "Request timed out. Reconnection attempted."}
        except Exception as e:
            logger.error(f"Error communicating with MemoryOrchestratorService: {e}", exc_info=True)
            self.connected = False
            
            # Record failure with circuit breaker
            self.circuit_breaker.record_failure()
            
            return {"status": "error", "message": str(e)}

    # --- Identity Management Methods ---
    def set_agent_id(self, agent_id: str) -> None:
        """
        Set the agent ID for tracking requests.
        
        Args:
            agent_id: The ID of the agent making requests
        """
        self._agent_id = agent_id
        logger.info(f"Agent ID set to: {agent_id}")
        
    def set_session_id(self, session_id: str) -> None:
        """
        Set the session ID for tracking requests.
        
        Args:
            session_id: The ID of the current session
        """
        self._session_id = session_id
        logger.info(f"Session ID set to: {session_id}")

    # --- Session Management Methods ---
    def create_session(self, user_id: str, session_type: str = "conversation", 
                      session_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new session in the memory system.
        
        Args:
            user_id: The ID of the user associated with the session
            session_type: Type of session (e.g., 'conversation', 'task')
            session_metadata: Additional metadata for the session
            
        Returns:
            Dict with status and session_id if successful
        """
        payload: Dict[str, Any] = {
            "action": "create_session",
            "data": {
                "user_id": user_id,
                "session_type": session_type,
                "created_by": self._agent_id
            }
        }
        
        if session_metadata is not None:
            payload["data"]["metadata"] = session_metadata
            
        response = self._send_request(payload)
        
        # If successful, store the session ID
        if response.get("status") == "success" and "session_id" in response:
            self._session_id = response["session_id"]
            
        return response

    # --- API Methods ---
    def add_memory(self, content: str, memory_type: str = "general", memory_tier: str = "short", 
                  importance: float = 0.5, metadata: Optional[Dict[str, Any]] = None, 
                  tags: Optional[List[str]] = None, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Add a new memory to the system.
        
        Args:
            content: The content of the memory
            memory_type: Type of memory (e.g., 'interaction', 'episode', 'knowledge_fact')
            memory_tier: Tier of memory ('short', 'medium', 'long')
            importance: Initial importance score (0.0 to 1.0)
            metadata: Additional metadata for the memory
            tags: List of tags for categorizing the memory
            parent_id: Optional parent memory ID for hierarchical relationships
            
        Returns:
            Dict with status and memory_id if successful
        """
        payload: Dict[str, Any] = {
            "action": "add_memory",
            "data": {
                "content": content,
                "memory_type": memory_type,
                "memory_tier": memory_tier,
                "importance": importance,
                "created_by": self._agent_id
            }
        }
        
        if metadata is not None:
            payload["data"]["metadata"] = metadata
        if tags is not None:
            payload["data"]["tags"] = tags
        if parent_id is not None:
            payload["data"]["parent_id"] = parent_id
            
        return self._send_request(payload)

    def get_memory(self, memory_id: str) -> Dict[str, Any]:
        """
        Retrieve a memory by its ID.
        
        Args:
            memory_id: The ID of the memory to retrieve
            
        Returns:
            Dict with status and memory data if successful
        """
        payload = {
            "action": "get_memory",
            "data": {"memory_id": memory_id}
        }
        return self._send_request(payload)

    def search_memory(self, query: str, memory_type: Optional[str] = None, 
                     limit: int = 10, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for memories based on text query.
        
        Args:
            query: The search query
            memory_type: Optional filter by memory type
            limit: Maximum number of results to return
            parent_id: Optional filter by parent ID
            
        Returns:
            Dict with status and search results if successful
        """
        payload: Dict[str, Any] = {
            "action": "search_memory",
            "data": {
                "query": query,
                "limit": limit
            }
        }
        if memory_type is not None:
            payload["data"]["memory_type"] = memory_type
        if parent_id is not None:
            payload["data"]["parent_id"] = parent_id
            
        return self._send_request(payload)

    def semantic_search(self, query: str, k: int = 5, 
                       filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform semantic search using vector embeddings.
        
        Args:
            query: The search query
            k: Number of results to return
            filters: Optional filters to apply to search results
            
        Returns:
            Dict with status and search results if successful
        """
        payload: Dict[str, Any] = {
            "action": "semantic_search",
            "data": {
                "query": query,
                "k": k
            }
        }
        
        if filters is not None:
            payload["data"]["filters"] = filters
            
        return self._send_request(payload)

    def update_memory(self, memory_id: str, update_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing memory.
        
        Args:
            memory_id: The ID of the memory to update
            update_payload: Dict of fields to update
            
        Returns:
            Dict with status and result
        """
        payload = {
            "action": "update_memory",
            "data": {
                "memory_id": memory_id,
                "update_data": update_payload
            }
        }
        return self._send_request(payload)

    def delete_memory(self, memory_id: str, cascade: bool = True) -> Dict[str, Any]:
        """
        Delete a memory.
        
        Args:
            memory_id: The ID of the memory to delete
            cascade: Whether to delete child memories
            
        Returns:
            Dict with status and result
        """
        payload = {
            "action": "delete_memory",
            "data": {
                "memory_id": memory_id,
                "cascade": cascade
            }
        }
        return self._send_request(payload)

    def get_children(self, parent_id: str, limit: int = 50, 
                    sort_field: str = "created_at", 
                    sort_order: str = "desc") -> Dict[str, Any]:
        """
        Get all child memories of a parent memory.
        
        Args:
            parent_id: The ID of the parent memory
            limit: Maximum number of children to return
            sort_field: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            
        Returns:
            Dict with status and children if successful
        """
        payload = {
            "action": "get_children",
            "data": {
                "parent_id": parent_id,
                "limit": limit,
                "sort_field": sort_field,
                "sort_order": sort_order
            }
        }
        return self._send_request(payload)

    def add_relationship(self, source_id: str, target_id: str, relationship_type: str, strength: float = 1.0) -> Dict[str, Any]:
        """
        Add a relationship between two memories.
        
        Args:
            source_id: The ID of the source memory
            target_id: The ID of the target memory
            relationship_type: Type of relationship
            strength: Strength of relationship (0.0 to 1.0)
            
        Returns:
            Dict with status and result
        """
        payload = {
            "action": "add_relationship",
            "data": {
                "source_id": source_id,
                "target_id": target_id,
                "relationship_type": relationship_type,
                "strength": strength
            }
        }
        return self._send_request(payload)

    def get_related_memories(self, memory_id: str, relationship_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get memories related to a specific memory.
        
        Args:
            memory_id: The ID of the memory
            relationship_type: Optional filter by relationship type
            
        Returns:
            Dict with status and related memories if successful
        """
        payload: Dict[str, Any] = {
            "action": "get_related",
            "data": {
                "memory_id": memory_id
            }
        }
        if relationship_type is not None:
            payload["data"]["relationship_type"] = relationship_type
        return self._send_request(payload)

    def reinforce_memory(self, memory_id: str, reinforcement_factor: float = 1.2) -> Dict[str, Any]:
        """
        Reinforce a memory by increasing its importance.
        
        Args:
            memory_id: The ID of the memory to reinforce
            reinforcement_factor: Factor to multiply importance by
            
        Returns:
            Dict with status and new importance if successful
        """
        payload = {
            "action": "reinforce_memory",
            "data": {
                "memory_id": memory_id,
                "reinforcement_factor": reinforcement_factor
            }
        }
        return self._send_request(payload)

    def batch_add_memories(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add multiple memories in a single batch operation.
        
        Args:
            memories: List of memory data dictionaries
            
        Returns:
            Dict with status and memory_ids if successful
        """
        payload = {
            "action": "batch_add_memories",
            "data": {
                "memories": memories
            }
        }
        return self._send_request(payload)

    def batch_get_memories(self, memory_ids: List[str]) -> Dict[str, Any]:
        """
        Retrieve multiple memories in a single batch operation.
        
        Args:
            memory_ids: List of memory IDs to retrieve
            
        Returns:
            Dict with status and memories if successful
        """
        payload = {
            "action": "batch_get_memories",
            "data": {
                "memory_ids": memory_ids
            }
        }
        return self._send_request(payload)

    def create_context_group(self, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new context group for organizing memories.
        
        Args:
            name: Name of the context group
            description: Optional description
            
        Returns:
            Dict with status and group_id if successful
        """
        payload: Dict[str, Any] = {
            "action": "create_context_group",
            "data": {
                "name": name
            }
        }
        if description is not None:
            payload["data"]["description"] = description
        return self._send_request(payload)

    def add_to_group(self, memory_id: str, group_id: int) -> Dict[str, Any]:
        """
        Add a memory to a context group.
        
        Args:
            memory_id: The ID of the memory
            group_id: The ID of the group
            
        Returns:
            Dict with status and result
        """
        payload = {
            "action": "add_to_group",
            "data": {
                "memory_id": memory_id,
                "group_id": group_id
            }
        }
        return self._send_request(payload)

    def get_memories_by_group(self, group_id: int) -> Dict[str, Any]:
        """
        Get all memories in a context group.
        
        Args:
            group_id: The ID of the group
            
        Returns:
            Dict with status and memories if successful
        """
        payload = {
            "action": "get_memories_by_group",
            "data": {
                "group_id": group_id
            }
        }
        return self._send_request(payload)

    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """
        Get the current status of the circuit breaker.
        
        Returns:
            Dict with circuit breaker state and statistics
        """
        return {
            "state": self.circuit_breaker.get_state(),
            "failure_count": self.circuit_breaker.failure_count,
            "last_failure_time": self.circuit_breaker.last_failure_time,
            "failure_threshold": self.circuit_breaker.failure_threshold,
            "reset_timeout": self.circuit_breaker.reset_timeout
        }

    def reset_circuit_breaker(self) -> Dict[str, Any]:
        """
        Manually reset the circuit breaker.
        
        Returns:
            Dict with status and result
        """
        self.circuit_breaker.state = "CLOSED"
        self.circuit_breaker.failure_count = 0
        return {
            "status": "success",
            "message": "Circuit breaker reset successfully",
            "new_state": self.circuit_breaker.get_state()
        }

    def process_request(self, request: dict) -> dict:
        """
        Process incoming requests.
        This client is primarily for outgoing requests, but can handle basic status inquiries.
        """
        if not isinstance(request, dict):
            return {"status": "error", "message": "Invalid request format"}
            
        action = request.get("action")
        
        if action == "health_check":
            return {
                "status": "success",
                "agent": self.name,
                "connected": self.connected,
                "circuit_breaker": self.get_circuit_breaker_status()
            }
        elif action == "reset_circuit_breaker":
            return self.reset_circuit_breaker()
        else:
            return {"status": "error", "message": "This client does not accept remote commands"} 
    def _get_health_status(self) -> dict:
        """Return health status information."""
        # Get base health status from parent class
        base_status = super()._get_health_status()
        
        # Add agent-specific health information
        base_status.update({
            'service': self.__class__.__name__,
            'uptime_seconds': int(time.time() - self.start_time) if hasattr(self, 'start_time') else 0,
            'request_count': self.request_count if hasattr(self, 'request_count') else 0,
            'status': 'HEALTHY'
        })
        
        return base_status


if __name__ == "__main__":
    agent = None
    try:
        agent = MemoryClient()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        if agent and hasattr(agent, 'cleanup'):
            agent.cleanup()

    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info(f"{self.__class__.__name__} cleaning up resources...")
        try:
            # Close ZMQ sockets if they exist
            if hasattr(self, 'socket') and self.socket:
        # TODO-FIXME – removed stray 'self.' (O3 Pro Max fix)
            if hasattr(self, 'context') and self.context:
        # TODO-FIXME – removed stray 'self.' (O3 Pro Max fix)
            # Close any open file handles
            # [Add specific resource cleanup here]
            
            # Call parent class cleanup if it exists
            super().cleanup()
            
            logger.info(f"{self.__class__.__name__} cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
