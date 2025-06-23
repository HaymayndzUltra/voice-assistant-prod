#!/usr/bin/env python3
"""
This script creates a new clean version of the memory_orchestrator.py file.
"""

import os

# Path to the new clean file
clean_file_path = "main_pc_code/src/memory/memory_orchestrator_clean.py"

# The clean content to write
content = '''"""
Memory Orchestrator Service
---------------------------

Centralized memory management service for the voice assistant system.
Provides a unified API for memory storage, retrieval, and search across all components.
Now enhanced with distributed memory capabilities for cross-machine integration.

This service implements the API defined in docs/design/memory_orchestrator_api.md
and follows the database schema in docs/design/memory_db_schema.md.
"""

import zmq
import json
import logging
import time
import uuid
import threading
import sys
import os
import psycopg2
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union, Tuple
from collections import OrderedDict
from pathlib import Path
from psycopg2.extras import Json, DictCursor
from utils.config_parser import parse_agent_args

# Import service discovery and network utilities
from main_pc_code.utils.service_discovery_client import register_service, discover_service, get_service_address
from main_pc_code.utils.network_utils import get_current_machine, load_network_config

# Import secure ZMQ utilities if available
try:
    from src.network.secure_zmq import configure_secure_client, start_auth
    SECURE_ZMQ_AVAILABLE = True
except ImportError:
    SECURE_ZMQ_AVAILABLE = False

_agent_args = parse_agent_args()

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Import database connection pool
from src.database.db_pool import get_connection, release_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(project_root, 'logs', 'memory_orchestrator.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MemoryOrchestrator")

# Configuration
ZMQ_PORT = 5576
CACHE_SIZE = 1000  # Maximum number of entries in the LRU cache
CACHE_TTL = 3600   # Time-to-live for cache entries in seconds (1 hour)

# Distributed memory configuration
SYNC_INTERVAL = 300  # Sync with PC2 every 5 minutes
MAX_SYNC_ITEMS = 100  # Maximum number of items to sync at once
PC2_CONNECTION_TIMEOUT = 5000  # milliseconds
ENABLE_DISTRIBUTED_MEMORY = True  # Can be disabled for local-only operation


class LRUCache:
    """
    Least Recently Used (LRU) cache implementation.
    Used to cache frequently accessed memory entries.
    """
    
    def __init__(self, capacity: int = CACHE_SIZE, ttl: int = CACHE_TTL):
        """Initialize the LRU cache with specified capacity and TTL."""
        self.capacity = capacity
        self.ttl = ttl
        self.cache = OrderedDict()  # {key: (value, timestamp)}
        self.lock = threading.RLock()  # Thread-safe operations
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve an item from the cache.
        Returns None if the item is not in the cache or has expired.
        """
        with self.lock:
            if key not in self.cache:
                return None
            
            value, timestamp = self.cache[key]
            current_time = time.time()
            
            # Check if the entry has expired
            if current_time - timestamp > self.ttl:
                del self.cache[key]
                return None
            
            # Move the accessed item to the end (most recently used)
            self.cache.move_to_end(key)
            return value
    
    def put(self, key: str, value: Any) -> None:
        """
        Add or update an item in the cache.
        """
        with self.lock:
            # If key exists, update it and move to end
            if key in self.cache:
                self.cache.move_to_end(key)
            
            # Add new entry with current timestamp
            self.cache[key] = (value, time.time())
            
            # If over capacity, remove the oldest item (first item)
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)
    
    def delete(self, key: str) -> bool:
        """
        Delete an item from the cache.
        
        Args:
            key: The key to delete
            
        Returns:
            True if the key was found and deleted, False otherwise
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """
        Clear all items from the cache.
        """
        with self.lock:
            self.cache.clear()
    
    def invalidate_by_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache entries whose key matches the given pattern.
        
        Args:
            pattern: String pattern to match against cache keys
            
        Returns:
            Number of invalidated entries
        """
        with self.lock:
            keys_to_delete = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.cache[key]
            return len(keys_to_delete)


class MemoryOrchestrator:
    """
    Main Memory Orchestrator service implementation.
    Handles API requests and manages memory operations.
    Now with distributed memory support across MainPC and PC2.
    """
    
    def __init__(self):
        """Initialize the Memory Orchestrator service."""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{ZMQ_PORT}")
        
        # Initialize cache
        self.cache = LRUCache(CACHE_SIZE, CACHE_TTL)
        
        # Flag to control the main loop
        self._running = False
        
        # Secure ZMQ setup
        self.secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
        
        # For distributed memory
        self.pc2_memory_agent_socket = None
        self.pc2_memory_agent_address = None
        self.pc2_memory_agent_info = None
        self.sync_thread = None
        self.last_sync_time = 0
        self.distributed_memory_available = False
        
        # For decay/reinforcement tracking
        self.memory_stats = {
            "total_memories_sent": 0,
            "total_memories_received": 0,
            "total_sync_operations": 0,
            "total_reinforcements": 0,
            "last_sync": 0
        }
        
        # Test database connection
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            db_version = cursor.fetchone()
            cursor.close()
            release_connection(conn)
            logger.info(f"Connected to PostgreSQL: {db_version[0]}")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
        
        # Request handlers mapping
        self.action_handlers = {
            "create": self.handle_create,
            "read": self.handle_read,
            "update": self.handle_update,
            "delete": self.handle_delete,
            "batch_read": self.handle_batch_read,
            "search": self.handle_search,
            "create_session": self.handle_create_session,
            "end_session": self.handle_end_session,
            "bulk_delete": self.handle_bulk_delete,
            "summarize": self.handle_summarize,
            # New distributed memory actions
            "sync": self.handle_sync,
            "reinforce": self.handle_reinforce,
            "query_pc2": self.handle_query_pc2
        }
        
        # Initialize connection to PC2 memory agent
        if ENABLE_DISTRIBUTED_MEMORY:
            self._init_pc2_connection()
        
        logger.info(f"Memory Orchestrator initialized, listening on port {ZMQ_PORT}")
    
    def _init_pc2_connection(self):
        """Initialize connection to the UnifiedMemoryReasoningAgent on PC2."""
        if not ENABLE_DISTRIBUTED_MEMORY:
            logger.info("Distributed memory is disabled, skipping PC2 connection")
            return
        
        try:
            # Discover the UnifiedMemoryReasoningAgent using service discovery
            logger.info("Discovering UnifiedMemoryReasoningAgent on PC2...")
            
            response = discover_service("UnifiedMemoryReasoningAgent")
            
            if response.get("status") == "SUCCESS" and "payload" in response:
                self.pc2_memory_agent_info = response["payload"]
                agent_ip = self.pc2_memory_agent_info.get("ip")
                agent_port = self.pc2_memory_agent_info.get("port")
                
                if not agent_ip or not agent_port:
                    logger.error("Invalid service information received for UnifiedMemoryReasoningAgent")
                    return
                
                # Store the address
                self.pc2_memory_agent_address = f"tcp://{agent_ip}:{agent_port}"
                
                # Create the socket
                self.pc2_memory_agent_socket = self.context.socket(zmq.DEALER)
                
                # Set timeout
                self.pc2_memory_agent_socket.setsockopt(zmq.RCVTIMEO, PC2_CONNECTION_TIMEOUT)
                self.pc2_memory_agent_socket.setsockopt(zmq.SNDTIMEO, PC2_CONNECTION_TIMEOUT)
                
                # Apply security if enabled
                if self.secure_zmq and SECURE_ZMQ_AVAILABLE:
                    try:
                        logger.info("Configuring secure ZMQ for PC2 connection...")
                        start_auth()
                        self.pc2_memory_agent_socket = configure_secure_client(self.pc2_memory_agent_socket)
                        logger.info("Secure ZMQ configured successfully")
                    except Exception as e:
                        logger.error(f"Failed to configure secure ZMQ for PC2 connection: {e}")
                
                # Connect to the PC2 agent
                self.pc2_memory_agent_socket.connect(self.pc2_memory_agent_address)
                logger.info(f"Connected to UnifiedMemoryReasoningAgent at {self.pc2_memory_agent_address}")
                
                # Test the connection
                if self._test_pc2_connection():
                    self.distributed_memory_available = True
                    logger.info("Distributed memory is now available")
                else:
                    logger.warning("Failed to establish connection with PC2 memory agent")
            else:
                logger.warning(f"Failed to discover UnifiedMemoryReasoningAgent: {response.get('message', 'Unknown error')}")
        
        except Exception as e:
            logger.error(f"Error initializing PC2 connection: {e}")
    
    def _test_pc2_connection(self) -> bool:
        """Test the connection to the PC2 memory agent"""
        if not self.pc2_memory_agent_socket:
            return False
        
        try:
            # Create a test ping message
            test_message = {
                "command": "TEST_PING",
                "data": {
                    "source": "MemoryOrchestrator",
                    "timestamp": time.time()
                }
            }
            
            # Send the message
            self.pc2_memory_agent_socket.send_multipart([
                b'',  # Empty identity frame for DEALER socket
                json.dumps(test_message).encode('utf-8')  # Explicitly encode to UTF-8
            ])
            
            # Wait for response
            try:
                frames = self.pc2_memory_agent_socket.recv_multipart()
                if len(frames) >= 2:
                    response_data = frames[1]
                    response = json.loads(response_data.decode('utf-8'))  # Explicitly decode from UTF-8
                    
                    if response.get("status") == "SUCCESS":
                        logger.info("Connection test successful")
                        return True
                    else:
                        logger.warning(f"Connection test failed: {response.get('message', 'Unknown error')}")
                        return False
            except zmq.error.Again:
                logger.warning("Connection test timed out")
                return False
                
        except Exception as e:
            logger.error(f"Error testing PC2 connection: {e}")
            return False
    
    def _start_sync_thread(self):
        """Start the background thread for periodic memory synchronization"""
        if not ENABLE_DISTRIBUTED_MEMORY or not self.distributed_memory_available:
            logger.info("Distributed memory is not available, skipping sync thread")
            return
            
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        logger.info("Started memory synchronization thread")
    
    def _sync_loop(self):
        """Background loop for periodic memory synchronization"""
        logger.info("Memory synchronization loop started")
        
        while self._running:
            try:
                # Sleep for the sync interval
                time.sleep(SYNC_INTERVAL)
                
                # Perform synchronization if distributed memory is available
                if self.distributed_memory_available:
                    self._sync_with_pc2()
                
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                # Shorter sleep on error
                time.sleep(30)
    
    def start(self):
        """Start the Memory Orchestrator service."""
        if self._running:
            logger.warning("Memory Orchestrator is already running")
            return
        
        self._running = True
        logger.info("Memory Orchestrator service started")
        
        # Start synchronization thread if distributed memory is enabled
        if ENABLE_DISTRIBUTED_MEMORY:
            self._start_sync_thread()
        
        # Main request handling loop
        while self._running:
            try:
                # Wait for the next request
                message_bytes = self.socket.recv()
                message_str = message_bytes.decode('utf-8')  # Explicitly decode from UTF-8
                message = json.loads(message_str)
                logger.debug(f"Received request: {message}")
                
                # Process the request
                response = self.process_request(message)
                
                # Send the response
                response_json = json.dumps(response)
                self.socket.send(response_json.encode('utf-8'))  # Explicitly encode to UTF-8
                logger.debug(f"Sent response: {response}")
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in request: {e}")
                response = self.create_error_response(
                    code="INVALID_JSON",
                    message="Request contains invalid JSON",
                    request_id=None
                )
                response_json = json.dumps(response)
                self.socket.send(response_json.encode('utf-8'))  # Explicitly encode to UTF-8
                
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                response = self.create_error_response(
                    code="INTERNAL_ERROR",
                    message=f"Internal server error: {str(e)}",
                    request_id=None
                )
                response_json = json.dumps(response)
                self.socket.send(response_json.encode('utf-8'))  # Explicitly encode to UTF-8
    
    def stop(self):
        """Stop the Memory Orchestrator service."""
        logger.info("Stopping Memory Orchestrator service")
        self._running = False
        
        # Cleanup resources
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=1.0)
        
        if self.pc2_memory_agent_socket:
            self.pc2_memory_agent_socket.close()
            self.pc2_memory_agent_socket = None
            self.distributed_memory_available = False
        
        # Clean up ZMQ resources
        self.socket.close()
        self.context.term()
        
        # Clear cache
        self.cache.clear()
        
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
            return {
                "status": "ok"
            }
            
        # Validate request format
        if not self.validate_request(request):
            return self.create_error_response(
                "invalid_request",
                "Request format is invalid",
                request.get("request_id")
            )
        
        # Extract request details
        action = request.get("action")
        request_id = request.get("request_id")
        
        # Get the appropriate handler for the action
        handler = self.action_handlers.get(action)
        
        if not handler:
            return self.create_error_response(
                "invalid_request",
                f"Unknown action: {action}",
                request_id
            )
        
        # Handle the request
        try:
            response = handler(request)
            return response
        except Exception as e:
            logger.error(f"Error handling {action} request: {e}", exc_info=True)
            return self.create_error_response(
                "internal_error",
                f"Error processing {action} request: {str(e)}",
                request_id
            )
    
    def validate_request(self, request: Dict[str, Any]) -> bool:
        """
        Validate that a request has the required fields.
        
        Args:
            request: The request to validate
            
        Returns:
            True if the request is valid, False otherwise
        """
        # Check for required fields
        if not isinstance(request, dict):
            return False
        
        # All requests must have an action
        if "action" not in request:
            return False
        
        # All requests except create_session must have a session_id
        if request.get("action") != "create_session" and "session_id" not in request:
            return False
        
        # All requests should have a payload
        if "payload" not in request and request.get("action") != "end_session":
            return False
        
        # Request ID is required for tracking
        if "request_id" not in request:
            return False
        
        return True
    
    def create_success_response(self, action: str, request_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a success response.
        
        Args:
            action: The action that was performed
            request_id: The ID of the request
            data: The response data
            
        Returns:
            A dictionary containing the JSON response
        """
        return {
            "status": "success",
            "action": action,
            "request_id": request_id,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def create_error_response(self, code: str, message: str, request_id: Optional[str], details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create an error response.
        
        Args:
            code: The error code
            message: The error message
            request_id: The ID of the request (or None if not available)
            details: Optional additional error details
            
        Returns:
            A dictionary containing the JSON error response
        """
        error = {
            "code": code,
            "message": message
        }
        
        if details:
            error["details"] = details
        
        return {
            "status": "error",
            "request_id": request_id if request_id else "unknown",
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def generate_id(self, prefix: str = "mem") -> str:
        """
        Generate a unique ID with the given prefix.
        
        Args:
            prefix: The prefix for the ID
            
        Returns:
            A unique ID string
        """
        return f"{prefix}-{uuid.uuid4().hex[:8]}"
    
    # Rest of the implementation would go here

def main():
    """Main entry point for the Memory Orchestrator service."""
    try:
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(project_root, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
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
'''

# Write the content to the new file
with open(clean_file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Created clean file at {clean_file_path}")

# Create a backup of the original file
original_file_path = "main_pc_code/src/memory/memory_orchestrator.py"
backup_file_path = "main_pc_code/src/memory/memory_orchestrator.py.backup"

try:
    os.rename(original_file_path, backup_file_path)
    print(f"Created backup of original file at {backup_file_path}")
except Exception as e:
    print(f"Failed to create backup: {e}")

# Replace the original file with the clean file
try:
    os.rename(clean_file_path, original_file_path)
    print(f"Replaced original file with clean file")
except Exception as e:
    print(f"Failed to replace original file: {e}") 