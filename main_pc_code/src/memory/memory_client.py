"""
Memory Client Library
--------------------

Client library for communicating with the Memory Orchestrator service.
Provides a simple interface for agents to perform memory operations.

This client implements the API defined in docs/design/memory_orchestrator_api.md
"""

from utils.config_parser import parse_agent_args
_agent_args = parse_agent_args()

import zmq
import json
import uuid
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MemoryClient")

# Configuration
DEFAULT_ENDPOINT = "tcp://localhost:5576"
REQUEST_TIMEOUT = 5000  # milliseconds

class MemoryClient:
    """
    Client for interacting with the Memory Orchestrator service.
    Provides methods for creating, reading, updating, and deleting memory entries,
    as well as search and batch operations.
    """
    
    def __init__(self, endpoint: str = DEFAULT_ENDPOINT, session_id: Optional[str] = None):
        """
        Initialize the Memory Client.
        
        Args:
            endpoint: The ZMQ endpoint of the Memory Orchestrator service
            session_id: The session ID to use for requests (can be set later)
        """
        self.endpoint = endpoint
        self.session_id = session_id
        self.agent_id = None
        
        # Initialize ZMQ socket
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.setsockopt(zmq.RCVTIMEO, REQUEST_TIMEOUT)
        self.socket.connect(self.endpoint)
        
        logger.info(f"Memory Client initialized, connected to {self.endpoint}")
    
    def __del__(self):
        """Clean up ZMQ resources when the client is destroyed."""
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
        
        if hasattr(self, 'context') and self.context:
            self.context.term()
    
    def set_session_id(self, session_id: str):
        """
        Set the session ID for future requests.
        
        Args:
            session_id: The session ID to use
        """
        self.session_id = session_id
    
    def set_agent_id(self, agent_id: str):
        """
        Set the agent ID for future requests.
        
        Args:
            agent_id: The ID of the agent using this client
        """
        self.agent_id = agent_id
    
    def _generate_request_id(self) -> str:
        """
        Generate a unique request ID.
        
        Returns:
            A unique request ID
        """
        return f"req-{uuid.uuid4().hex[:8]}"
    
    def _send_request(self, action: str, payload: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a request to the Memory Orchestrator and receive the response.
        
        Args:
            action: The action to perform (create, read, update, delete, etc.)
            payload: The request payload
            session_id: Optional session ID to override the default
            
        Returns:
            The response from the Memory Orchestrator
            
        Raises:
            TimeoutError: If the request times out
            ConnectionError: If there's a connection error
            ValueError: If the response is invalid
        """
        # Use provided session ID or default
        used_session_id = session_id if session_id is not None else self.session_id
        
        # For create_session action, we don't need a session ID
        if action != "create_session" and used_session_id is None:
            raise ValueError("Session ID is required for this operation")
        
        # Prepare request
        request = {
            "action": action,
            "payload": payload,
            "request_id": self._generate_request_id(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Add session ID if needed
        if action != "create_session":
            request["session_id"] = used_session_id
        
        # Add agent ID if available
        if self.agent_id:
            # Include agent ID in payload for tracking
            if "metadata" not in payload:
                payload["metadata"] = {}
            payload["metadata"]["agent_id"] = self.agent_id
        
        # Send request
        try:
            logger.debug(f"Sending request: {action}")
            self.socket.send_json(request)
            
            # Wait for response
            response = self.socket.recv_json()
            logger.debug(f"Received response: {response.get('status', 'unknown')}")
            
            # Check for errors
            if response.get("status") == "error":
                error = response.get("error", {})
                error_message = error.get("message", "Unknown error")
                error_code = error.get("code", "unknown_error")
                logger.error(f"Request failed: {error_code} - {error_message}")
                
                # You might want to raise specific exceptions based on error code
                # For now, we'll just return the response and let the caller handle it
            
            return response
            
        except zmq.error.Again:
            logger.error(f"Request timed out after {REQUEST_TIMEOUT}ms")
            raise TimeoutError(f"Memory Orchestrator request timed out")
            
        except zmq.error.ZMQError as e:
            logger.error(f"ZMQ error: {e}")
            raise ConnectionError(f"Failed to communicate with Memory Orchestrator: {e}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            raise ValueError(f"Invalid response from Memory Orchestrator: {e}")
    
    def create_session(self, user_id: Optional[str] = None, session_metadata: Optional[Dict[str, Any]] = None, 
                       session_type: str = "conversation") -> Dict[str, Any]:
        """
        Create a new session.
        
        Args:
            user_id: Optional user ID
            session_metadata: Optional metadata about the session
            session_type: Type of session (default: conversation)
            
        Returns:
            Response containing the session ID
        """
        payload = {
            "session_type": session_type
        }
        
        if user_id:
            payload["user_id"] = user_id
            
        if session_metadata:
            payload["session_metadata"] = session_metadata
        
        response = self._send_request("create_session", payload)
        
        # If successful, update the session_id
        if response.get("status") == "success":
            self.session_id = response.get("data", {}).get("session_id")
            logger.info(f"Created session: {self.session_id}")
        
        return response
    
    def end_session(self, summary: Optional[str] = None, archive: bool = False) -> Dict[str, Any]:
        """
        End the current session.
        
        Args:
            summary: Optional summary of the session
            archive: Whether to archive the session
            
        Returns:
            Response indicating success or failure
        """
        payload = {
            "archive": archive
        }
        
        if summary:
            payload["summary"] = summary
        
        response = self._send_request("end_session", payload)
        
        if response.get("status") == "success":
            logger.info(f"Ended session: {self.session_id}")
        
        return response
    
    def create_memory(self, memory_type: str, content: Dict[str, Any], 
                      tags: Optional[List[str]] = None, ttl: Optional[int] = None, 
                      priority: int = 5) -> Dict[str, Any]:
        """
        Create a new memory entry.
        
        Args:
            memory_type: Type of memory (conversation, context, user_preference, agent_state)
            content: Content of the memory
            tags: Optional tags for categorizing the memory
            ttl: Optional time-to-live in seconds
            priority: Priority level (1-10, default: 5)
            
        Returns:
            Response containing the memory ID
        """
        payload = {
            "memory_type": memory_type,
            "content": content,
            "priority": priority
        }
        
        if tags:
            payload["tags"] = tags
            
        if ttl:
            payload["ttl"] = ttl
        
        response = self._send_request("create", payload)
        
        if response.get("status") == "success":
            memory_id = response.get("data", {}).get("memory_id")
            logger.info(f"Created memory: {memory_id} (type: {memory_type})")
        
        return response
    
    def get_memory(self, memory_id: str) -> Dict[str, Any]:
        """
        Retrieve a memory entry by ID.
        
        Args:
            memory_id: The ID of the memory to retrieve
            
        Returns:
            Response containing the memory data
        """
        payload = {
            "memory_id": memory_id
        }
        
        response = self._send_request("read", payload)
        
        if response.get("status") == "success":
            logger.info(f"Retrieved memory: {memory_id}")
        
        return response
    
    def update_memory(self, memory_id: str, content: Optional[Dict[str, Any]] = None,
                      tags: Optional[List[str]] = None, ttl: Optional[int] = None,
                      priority: Optional[int] = None) -> Dict[str, Any]:
        """
        Update an existing memory entry.
        
        Args:
            memory_id: The ID of the memory to update
            content: Optional new content
            tags: Optional new tags
            ttl: Optional new time-to-live in seconds
            priority: Optional new priority level (1-10)
            
        Returns:
            Response indicating success or failure
        """
        payload = {
            "memory_id": memory_id
        }
        
        if content:
            payload["content"] = content
            
        if tags:
            payload["tags"] = tags
            
        if ttl is not None:
            payload["ttl"] = ttl
            
        if priority is not None:
            payload["priority"] = priority
        
        response = self._send_request("update", payload)
        
        if response.get("status") == "success":
            logger.info(f"Updated memory: {memory_id}")
        
        return response
    
    def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """
        Delete a memory entry.
        
        Args:
            memory_id: The ID of the memory to delete
            
        Returns:
            Response indicating success or failure
        """
        payload = {
            "memory_id": memory_id
        }
        
        response = self._send_request("delete", payload)
        
        if response.get("status") == "success":
            logger.info(f"Deleted memory: {memory_id}")
        
        return response
    
    def batch_read(self, memory_ids: Optional[List[str]] = None, 
                   memory_type: Optional[str] = None,
                   time_range: Optional[Dict[str, str]] = None,
                   tags: Optional[List[str]] = None,
                   limit: int = 10, offset: int = 0,
                   sort_field: str = "created_at", sort_order: str = "desc") -> Dict[str, Any]:
        """
        Retrieve multiple memory entries in a single request.
        
        Args:
            memory_ids: Optional list of specific memory IDs to retrieve
            memory_type: Optional memory type to filter by
            time_range: Optional time range to filter by (dict with 'start' and 'end' keys)
            tags: Optional tags to filter by
            limit: Maximum number of memories to return (default: 10)
            offset: Offset for pagination (default: 0)
            sort_field: Field to sort by (default: created_at)
            sort_order: Sort order (asc or desc, default: desc)
            
        Returns:
            Response containing multiple memory entries
        """
        payload = {}
        
        if memory_ids:
            payload["memory_ids"] = memory_ids
        
        # Add filter parameters
        filter_params = {}
        
        if memory_type:
            filter_params["memory_type"] = memory_type
            
        if time_range:
            filter_params["time_range"] = time_range
            
        if tags:
            filter_params["tags"] = tags
            
        filter_params["limit"] = limit
        filter_params["offset"] = offset
        filter_params["sort"] = {
            "field": sort_field,
            "order": sort_order
        }
        
        payload["filter"] = filter_params
        
        response = self._send_request("batch_read", payload)
        
        if response.get("status") == "success":
            count = len(response.get("data", {}).get("memories", []))
            logger.info(f"Batch read: retrieved {count} memories")
        
        return response
    
    def search(self, query: str, search_type: str = "hybrid", 
               memory_types: Optional[List[str]] = None,
               time_range: Optional[Dict[str, str]] = None,
               tags: Optional[List[str]] = None,
               min_similarity: float = 0.7, limit: int = 5) -> Dict[str, Any]:
        """
        Search for memory entries based on semantic relevance to a query.
        
        Args:
            query: The search query
            search_type: Type of search (semantic, keyword, or hybrid)
            memory_types: Optional list of memory types to search
            time_range: Optional time range to filter by (dict with 'start' and 'end' keys)
            tags: Optional tags to filter by
            min_similarity: Minimum similarity score (0-1, default: 0.7)
            limit: Maximum number of results to return (default: 5)
            
        Returns:
            Response containing search results
        """
        payload = {
            "query": query,
            "search_type": search_type
        }
        
        # Add filter parameters
        filters = {}
        
        if memory_types:
            filters["memory_types"] = memory_types
            
        if time_range:
            filters["time_range"] = time_range
            
        if tags:
            filters["tags"] = tags
            
        filters["min_similarity"] = min_similarity
        filters["limit"] = limit
        
        payload["filters"] = filters
        
        response = self._send_request("search", payload)
        
        if response.get("status") == "success":
            count = len(response.get("data", {}).get("results", []))
            logger.info(f"Search: found {count} results for query '{query}'")
        
        return response
    
    def bulk_delete(self, memory_type: Optional[str] = None, 
                    older_than: Optional[str] = None,
                    tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Delete multiple memory entries matching filter criteria.
        
        Args:
            memory_type: Optional memory type to filter by
            older_than: Optional timestamp, delete memories older than this
            tags: Optional tags to filter by
            
        Returns:
            Response indicating the number of deleted items
        """
        filter_params = {}
        
        if memory_type:
            filter_params["memory_type"] = memory_type
            
        if older_than:
            filter_params["older_than"] = older_than
            
        if tags:
            filter_params["tags"] = tags
        
        payload = {
            "filter": filter_params
        }
        
        response = self._send_request("bulk_delete", payload)
        
        if response.get("status") == "success":
            count = response.get("data", {}).get("deleted_count", 0)
            logger.info(f"Bulk delete: removed {count} memories")
        
        return response
    
    def summarize(self, memory_type: str, 
                  time_range: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Get a summary of memories of a specific type.
        
        Args:
            memory_type: The type of memories to summarize
            time_range: Optional time range to filter by (dict with 'start' and 'end' keys)
            
        Returns:
            Response containing the summary
        """
        payload = {
            "memory_type": memory_type
        }
        
        if time_range:
            payload["time_range"] = time_range
        
        response = self._send_request("summarize", payload)
        
        if response.get("status") == "success":
            logger.info(f"Summarized {memory_type} memories")
        
        return response

# Example usage
if __name__ == "__main__":
    # Create a client
    client = MemoryClient()
    
    # Create a new session
    session_response = client.create_session(
        session_metadata={
            "device_info": "Windows PC",
            "location": "Home"
        }
    )
    
    # Check if session creation was successful
    if session_response.get("status") != "success":
        print("Failed to create session")
        exit(1)
    
    # Create a memory entry
    memory_response = client.create_memory(
        memory_type="conversation",
        content={
            "text": "User asked about the weather",
            "source_agent": "language_understanding_agent",
            "metadata": {
                "intent": "weather_query",
                "confidence": 0.95
            }
        },
        tags=["weather", "query"]
    )
    
    # Check if memory creation was successful
    if memory_response.get("status") == "success":
        # Get the memory ID
        memory_id = memory_response.get("data", {}).get("memory_id")
        
        # Read the memory back
        get_response = client.get_memory(memory_id)
        
        if get_response.get("status") == "success":
            memory_data = get_response.get("data", {})
            print(f"Memory content: {memory_data.get('content', {}).get('text')}")
            
            # Update the memory
            client.update_memory(
                memory_id,
                content={
                    "text": "User asked about the weather in Boston",
                    "source_agent": "language_understanding_agent",
                    "metadata": {
                        "intent": "weather_query",
                        "entities": ["Boston"],
                        "confidence": 0.98
                    }
                },
                tags=["weather", "location", "query"]
            )
            
            # Search for weather-related memories
            search_response = client.search(
                query="weather location",
                memory_types=["conversation"],
                tags=["weather"]
            )
            
            if search_response.get("status") == "success":
                results = search_response.get("data", {}).get("results", [])
                print(f"Found {len(results)} search results")
    
    # End the session
    client.end_session(summary="User asked about weather in Boston")

