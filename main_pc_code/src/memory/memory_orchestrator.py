"""
Memory Orchestrator Service - Minimal Version
--------------------------------------------

This is a minimal version of the Memory Orchestrator service that addresses
the null byte issues. It focuses on proper encoding/decoding for ZMQ communication.
"""

import zmq
import json
import logging
import time
import uuid
import os
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from main_pc_code.src.core.base_agent import BaseAgent
from utils.config_loader import parse_agent_args

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MemoryOrchestrator")

# Configuration
# ZMQ_PORT = 5576
HEALTH_PORT = int(_agent_args.get('health_port', ZMQ_PORT + 1))

_agent_args = parse_agent_args()

class MemoryOrchestrator(BaseAgent):
    """
    Minimal Memory Orchestrator implementation focusing on proper encoding/decoding.
    """
    
    def __init__(self):
        """Initialize the Memory Orchestrator service."""
        self.port = _agent_args.get('port')
        super().__init__(_agent_args)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        
        # Setup health check socket
        try:
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            self.health_socket.bind(f"tcp://<BIND_ADDR>:{HEALTH_PORT}")
            logger.info(f"Health check socket bound to port {HEALTH_PORT}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind health check socket: {e}")
            # Continue even if health check socket fails
        
        # In-memory storage for testing
        self.memories = {}
        
        # Flag to control the main loop
        self._running = False
        
        # Health status
        self.start_time = time.time()
        self.memory_backends_connected = 1  # Placeholder for demo
        self.total_memory_entries = 0
        
        logger.info(f"Memory Orchestrator initialized, listening on port {self.port}")
    
    def _get_health_status(self):
        """Overrides the base method to add agent-specific health metrics."""
        base_status = super()._get_health_status()
        specific_metrics = {
            "orchestrator_status": "active",
            "memory_backends_connected": getattr(self, 'memory_backends_connected', 0),
            "total_memory_entries": len(self.memories)
        }
        base_status.update(specific_metrics)
        return base_status
    
    def start(self):
        """Start the Memory Orchestrator service."""
        if self._running:
            logger.warning("Memory Orchestrator is already running")
            return
        
        self._running = True
        
        logger.info("Memory Orchestrator service started")
        
        # Main request handling loop
        while self._running:
            try:
                # Wait for the next request using explicit encoding/decoding
                message_bytes = self.socket.recv()
                message_str = message_bytes.decode('utf-8')
                message = json.loads(message_str)
                logger.debug(f"Received request: {message}")
                
                # Process the request
                response = self.process_request(message)
                
                # Send the response with explicit encoding
                response_json = json.dumps(response)
                self.socket.send(response_json.encode('utf-8'))
                logger.debug(f"Sent response: {response}")
                
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                response = self.create_error_response(
                    code="INTERNAL_ERROR",
                    message=f"Internal server error: {str(e)}",
                    request_id=None
                )
                response_json = json.dumps(response)
                self.socket.send(response_json.encode('utf-8'))
    
    def stop(self):
        """Stop the Memory Orchestrator service."""
        logger.info("Stopping Memory Orchestrator service")
        self._running = False
        
        # Close sockets
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
            logger.info("Main socket closed")
            
        if hasattr(self, 'health_socket') and self.health_socket:
            self.health_socket.close()
            logger.info("Health socket closed")
        
        # Terminate ZMQ context
        if hasattr(self, 'context') and self.context:
            self.context.term()
            logger.info("ZMQ context terminated")
        
        super().cleanup()
        logger.info("Memory Orchestrator service stopped")
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming request and generate a response.
        
        Args:
            request: The JSON request as a dictionary
            
        Returns:
            A dictionary containing the JSON response
        """
        # Quick health check bypass
        if request.get("action") in ["ping", "health", "health_check"]:
            return {"status": "ok"}
        
        # Extract request details
        action = request.get("action")
        request_id = request.get("request_id", "unknown")
        
        # Handle different actions
        if action == "create":
            return self.handle_create(request)
        elif action == "read":
            return self.handle_read(request)
        elif action == "update":
            return self.handle_update(request)
        elif action == "delete":
            return self.handle_delete(request)
        else:
            return self.create_error_response(
                "invalid_action",
                f"Unknown action: {action}",
                request_id
            )
    
    def create_success_response(self, action: str, request_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a success response."""
        return {
            "status": "success",
            "action": action,
            "request_id": request_id,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def create_error_response(self, code: str, message: str, request_id: Optional[str]) -> Dict[str, Any]:
        """Create an error response."""
        return {
            "status": "error",
            "request_id": request_id if request_id else "unknown",
            "error": {
                "code": code,
                "message": message
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def generate_id(self, prefix: str = "mem") -> str:
        """Generate a unique ID with the given prefix."""
        return f"{prefix}-{uuid.uuid4().hex[:8]}"
    
    def handle_create(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a create memory request."""
        payload = request.get("payload", {})
        request_id = request.get("request_id", "unknown")
        
        # Validate payload
        memory_type = payload.get("memory_type")
        content = payload.get("content")
        
        if not memory_type or not content:
            return self.create_error_response(
                "validation_error",
                "Memory type and content are required",
                request_id
            )
        
        # Generate a unique memory ID
        memory_id = self.generate_id("mem")
        
        # Get current timestamp
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Prepare memory entry
        memory_entry = {
            "memory_id": memory_id,
            "memory_type": memory_type,
            "content": content,
            "created_at": timestamp,
            "updated_at": timestamp,
            "tags": payload.get("tags", []),
            "priority": payload.get("priority", 5)
        }
        
        # Store in memory
        self.memories[memory_id] = memory_entry
        
        # Return success response
        return self.create_success_response(
            "create",
            request_id,
            {
                "memory_id": memory_id,
                "created_at": timestamp
            }
        )
    
    def handle_read(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a read memory request."""
        payload = request.get("payload", {})
        request_id = request.get("request_id", "unknown")
        
        # Get memory ID from payload
        memory_id = payload.get("memory_id")
        
        if not memory_id:
            return self.create_error_response(
                "validation_error",
                "Memory ID is required",
                request_id
            )
        
        # Check if memory exists
        if memory_id not in self.memories:
            return self.create_error_response(
                "memory_not_found",
                f"Memory with ID {memory_id} not found",
                request_id
            )
        
        # Return the memory
        return self.create_success_response(
            "read",
            request_id,
            self.memories[memory_id]
        )
    
    def handle_update(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an update memory request."""
        payload = request.get("payload", {})
        request_id = request.get("request_id", "unknown")
        
        # Get memory ID from payload
        memory_id = payload.get("memory_id")
        
        if not memory_id:
            return self.create_error_response(
                "validation_error",
                "Memory ID is required",
                request_id
            )
        
        # Check if memory exists
        if memory_id not in self.memories:
            return self.create_error_response(
                "memory_not_found",
                f"Memory with ID {memory_id} not found",
                request_id
            )
        
        # Update memory fields
        memory = self.memories[memory_id]
        memory.update({
            "content": payload.get("content", memory.get("content")),
            "tags": payload.get("tags", memory.get("tags")),
            "priority": payload.get("priority", memory.get("priority")),
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Return success response
        return self.create_success_response(
            "update",
            request_id,
            {
                "memory_id": memory_id,
                "updated_at": memory.get("updated_at")
            }
        )
    
    def handle_delete(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a delete memory request."""
        payload = request.get("payload", {})
        request_id = request.get("request_id", "unknown")
        
        # Get memory ID from payload
        memory_id = payload.get("memory_id")
        
        if not memory_id:
            return self.create_error_response(
                "validation_error",
                "Memory ID is required",
                request_id
            )
        
        # Check if memory exists
        if memory_id not in self.memories:
            return self.create_error_response(
                "memory_not_found",
                f"Memory with ID {memory_id} not found",
                request_id
            )
        
        # Delete the memory
        del self.memories[memory_id]
        
        # Return success response
        return self.create_success_response(
            "delete",
            request_id,
            {
                "deleted": True
            }
        )

def main():
    """Main entry point for the Memory Orchestrator service."""
    try:
        orchestrator = MemoryOrchestrator()
        logger.info("Starting Memory Orchestrator service...")
        orchestrator.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Error in Memory Orchestrator service: {e}", exc_info=True)
    finally:
        if 'orchestrator' in locals():
            orchestrator.stop()

if __name__ == "__main__":
    main()
