#!/usr/bin/env python3
"""
Session Memory Agent
------------------
Maintains context memory and session awareness:
- Stores conversation history
- Provides context for LLM prompts
- Manages user sessions
- Supports semantic search of past interactions
"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import json
import logging
import time
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union


# Import path manager for containerization-friendly paths
import sys
import os
MAIN_PC_CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'main_pc_code'))
if MAIN_PC_CODE_DIR not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR)

from common.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config
from main_pc_code.agents.memory_client import MemoryClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(join_path("logs", "session_memory_agent.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SessionMemoryAgent")

# ZMQ Configuration
ZMQ_MEMORY_PORT = 5574  # Port for session memory requests
ZMQ_HEALTH_PORT = 6583  # Health status
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Memory settings
MAX_CONTEXT_TOKENS = 2000  # Maximum tokens for context
MAX_SESSIONS = 100  # Maximum number of active sessions
SESSION_TIMEOUT = 3600  # Session timeout in seconds (1 hour)

class SessionMemoryAgent(BaseAgent):
    """
    Agent for handling session memory and context management.
    Now fully integrated with the central memory system via MemoryClient.
    Also reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
    """
    
    def __init__(self, port: int = 5574, health_port: int = 6583):
        """Initialize the session memory agent."""
        super().__init__(name="SessionMemoryAgent", port=port, health_check_port=health_port)
        
        # Initialize memory client for central memory system
        self.memory_client = MemoryClient()
        self.memory_client.set_agent_id(self.name)
        
        # Error bus configuration
        self.error_bus_port = 7150
        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)
        
        # Initialize active sessions tracking
        self.active_sessions = {}
        
        logger.info("SessionMemoryAgent initialized successfully")

    def _report_error(self, error_type: str, error_message: str, severity: str = "ERROR"):
        """Report errors to the central error bus"""
        try:
            error_data = {
                "timestamp": time.time(),
                "agent": self.name,
                "error_type": error_type,
                "message": error_message,
                "severity": severity
            }
            self.error_bus_pub.send_string(f"ERROR:{json.dumps(error_data)}")
            logger.error(f"{error_type}: {error_message}")
        except Exception as e:
            logger.error(f"Failed to report error to error bus: {e}")

    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming requests based on action type"""
        if not isinstance(request, dict):
            return {"status": "error", "message": "Invalid request format"}
            
        action = request.get("action")
        
        try:
            if action == "create_session":
                return self._create_session(request)
            elif action == "add_interaction":
                return self._add_interaction(request)
            elif action == "get_context":
                return self._get_context(request)
            elif action == "delete_session":
                return self._delete_session(request)
            elif action == "search_interactions":
                return self._search_interactions(request)
            elif action == "health_check":
                return {"status": "success", "agent": self.name, "healthy": True}
            else:
                return {"status": "error", "message": f"Unknown action: {action}"}
        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            self._report_error("request_processing_error", error_msg)
            return {"status": "error", "message": error_msg}

    def _create_session(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new session in the memory system
        
        Args:
            request: Dict containing 'user_id' and optional 'metadata'
            
        Returns:
            Dict with status and session_id
        """
        user_id = request.get("user_id", "default")
        metadata = request.get("metadata", {})
        session_type = request.get("session_type", "conversation")
        
        try:
            # Create session in central memory system
            response = self.memory_client.create_session(
                user_id=user_id,
                session_type=session_type,
                session_metadata={
                    **metadata,
                    "created_at": datetime.now().isoformat(),
                    "agent": self.name
                }
            )
            
            if response.get("status") == "success":
                session_id = response.get("session_id")
                
                # Track active session
                self.active_sessions[session_id] = {
                    "user_id": user_id,
                    "created_at": datetime.now(),
                    "last_activity": datetime.now(),
                    "metadata": metadata
                }
                
                return {"status": "success", "session_id": session_id}
            else:
                error_msg = response.get("message", "Failed to create session")
                self._report_error("create_session_error", error_msg)
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception creating session: {str(e)}"
            self._report_error("create_session_exception", error_msg)
            return {"status": "error", "message": error_msg}

    def _add_interaction(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add an interaction to an existing session
        
        Args:
            request: Dict containing 'session_id', 'role', 'content', and optional 'metadata'
            
        Returns:
            Dict with status and interaction_id
        """
        session_id = request.get("session_id")
        role = request.get("role")
        content = request.get("content")
        metadata = request.get("metadata", {})
        
        if not session_id or not role or not content:
            return {"status": "error", "message": "Missing required parameters"}
            
        try:
            # Update session activity timestamp
            if session_id in self.active_sessions:
                self.active_sessions[session_id]["last_activity"] = datetime.now()
            
            # Add interaction to central memory system
            response = self.memory_client.add_memory(
                content=content,
                memory_type="interaction",
                parent_id=session_id,
                memory_tier="short",  # Interactions are typically short-term memories
                importance=0.5,       # Default importance
                metadata={
                    **metadata, 
                    "role": role,
                    "timestamp": datetime.now().isoformat()
                },
                tags=[role.lower()]
            )
            
            if response.get("status") == "success":
                return {
                    "status": "success", 
                    "message": "Interaction added",
                    "interaction_id": response.get("memory_id")
                }
            else:
                error_msg = response.get("message", "Failed to add interaction")
                self._report_error("add_interaction_error", error_msg)
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception adding interaction: {str(e)}"
            self._report_error("add_interaction_exception", error_msg)
            return {"status": "error", "message": error_msg}

    def _get_context(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get conversation context for a session
        
        Args:
            request: Dict containing 'session_id' and optional 'limit'
            
        Returns:
            Dict with status and interactions list
        """
        session_id = request.get("session_id")
        limit = request.get("limit", 20)
        
        if not session_id:
            return {"status": "error", "message": "Missing session_id"}
            
        try:
            # Update session activity timestamp
            if session_id in self.active_sessions:
                self.active_sessions[session_id]["last_activity"] = datetime.now()
            
            # Get interactions from central memory system
            response = self.memory_client.get_children(
                parent_id=session_id,
                limit=limit,
                sort_field="created_at",
                sort_order="asc"  # Chronological order
            )
            
            if response.get("status") == "success":
                interactions = response.get("results", [])
                
                # Format interactions for context
                context = []
                for interaction in interactions:
                    metadata = interaction.get("metadata", {})
                    role = metadata.get("role", "unknown")
                    content = interaction.get("content", "")
                    context.append({"role": role, "content": content})
                
                return {"status": "success", "context": context}
            else:
                error_msg = response.get("message", "Failed to get context")
                self._report_error("get_context_error", error_msg)
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception getting context: {str(e)}"
            self._report_error("get_context_exception", error_msg)
            return {"status": "error", "message": error_msg}

    def _delete_session(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delete a session and all its interactions
        
        Args:
            request: Dict containing 'session_id'
            
        Returns:
            Dict with status
        """
        session_id = request.get("session_id")
        
        if not session_id:
            return {"status": "error", "message": "Missing session_id"}
            
        try:
            # Remove from active sessions
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            # Delete from central memory system (will cascade delete all children)
            response = self.memory_client.delete_memory(memory_id=session_id)
            
            if response.get("status") == "success":
                return {"status": "success", "message": "Session deleted"}
            else:
                error_msg = response.get("message", "Failed to delete session")
                self._report_error("delete_session_error", error_msg)
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception deleting session: {str(e)}"
            self._report_error("delete_session_exception", error_msg)
            return {"status": "error", "message": error_msg}

    def _search_interactions(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for interactions matching a query
        
        Args:
            request: Dict containing 'query', optional 'session_id', and 'limit'
            
        Returns:
            Dict with status and search results
        """
        query = request.get("query", "")
        session_id = request.get("session_id")
        limit = request.get("limit", 10)
        
        if not query:
            return {"status": "error", "message": "Missing query"}
            
        try:
            # Try semantic search if available
            try:
                # If session_id provided, filter by parent_id
                filters = {}
                if session_id:
                    filters["parent_id"] = session_id
                
                response = self.memory_client.semantic_search(
                    query=query,
                    filters=filters,
                    k=limit
                )
                
                if response.get("status") == "success" and response.get("results"):
                    return {"status": "success", "results": response.get("results", [])}
            except Exception as e:
                logger.warning(f"Semantic search failed, falling back to text search: {e}")
            
            # Fall back to text search
            search_params = {
                "query": query,
                "memory_type": "interaction",
                "limit": limit
            }
            
            if session_id:
                search_params["parent_id"] = session_id
                
            response = self.memory_client.search_memory(**search_params)
            
            if response.get("status") == "success":
                return {"status": "success", "results": response.get("results", [])}
            else:
                error_msg = response.get("message", "Search failed")
                self._report_error("search_interactions_error", error_msg)
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception searching interactions: {str(e)}"
            self._report_error("search_interactions_exception", error_msg)
            return {"status": "error", "message": error_msg}
    
    def _cleanup_expired_sessions(self):
        """Clean up expired sessions based on timeout"""
        now = datetime.now()
        expired_sessions = []
        
        for session_id, session_data in self.active_sessions.items():
            last_activity = session_data.get("last_activity", session_data.get("created_at"))
            if (now - last_activity).total_seconds() > SESSION_TIMEOUT:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            logger.info(f"Cleaning up expired session: {session_id}")
            del self.active_sessions[session_id]
            
            # Mark as expired in memory system
            try:
                self.memory_client.update_memory(
                    memory_id=session_id,
                    update_payload={"metadata": {"expired": True, "expired_at": now.isoformat()}}
                )
            except Exception as e:
                logger.warning(f"Failed to mark session {session_id} as expired: {e}")
    
    def run(self):
        """Run the agent with session cleanup thread"""
        # Start session cleanup thread
        cleanup_thread = threading.Thread(target=self._run_cleanup_thread, daemon=True)
        cleanup_thread.start()
        if not hasattr(self, "_background_threads"):
            self._background_threads = []
        self._background_threads.append(cleanup_thread)
        
        # Run normal agent loop
        super().run()
    
    def _run_cleanup_thread(self):
        """Run periodic session cleanup"""
        while True:
            try:
                self._cleanup_expired_sessions()
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
            
            # Sleep for 5 minutes
            time.sleep(300)
    
    def cleanup(self):
        """Clean up resources before shutdown"""
        if hasattr(self, 'error_bus_pub') and self.error_bus_pub:
            self.error_bus_pub.close()
        super().cleanup()

# Example usage
if __name__ == "__main__":
    try:
        agent = SessionMemoryAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info("SessionMemoryAgent shutting down")
    except Exception as e:
        logger.critical(f"SessionMemoryAgent failed to start: {e}", exc_info=True)
    finally:
        if 'agent' in locals() and hasattr(agent, 'cleanup'):
            agent.cleanup()
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
