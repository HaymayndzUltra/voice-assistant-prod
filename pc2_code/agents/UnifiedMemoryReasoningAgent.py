import os
import zmq
import json
import logging
from typing import Dict, Any, Optional, List, Tuple, Union
import sys
import time
import uuid
import threading
from datetime import datetime, timedelta
from pathlib import Path
import socket
import copy

# Add project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import PC2 configuration system
from pc2_code.config.system_config import get_service_host, get_service_port

# Import the new service discovery client
from main_pc_code.utils.service_discovery_client import register_service, discover_service, get_service_address
from main_pc_code.utils.network_utils import get_current_machine

# Import secure ZMQ utilities if available
try:
    from main_pc_code.src.network.secure_zmq import configure_secure_server, start_auth
    SECURE_ZMQ_AVAILABLE = True
except ImportError:
    SECURE_ZMQ_AVAILABLE = False

# Configure logging
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, 'unified_memory_reasoning_agent.log'))
    ]
)
logger = logging.getLogger(__name__)

# Constants for memory management
MEMORY_DECAY_INTERVAL = 60 * 5  # Check for decay every 5 minutes
MEMORY_DECAY_THRESHOLD = 60 * 60 * 24  # Decay memories not accessed in 24 hours
MEMORY_DECAY_FACTOR = 0.9  # Reduce strength by 10% on decay
MIN_MEMORY_STRENGTH = 0.1  # Minimum strength before memory is forgotten
REINFORCEMENT_FACTOR = 1.2  # Increase strength by 20% on reinforcement
MAX_MEMORY_STRENGTH = 5.0  # Maximum strength a memory can have

class UnifiedMemoryReasoningAgent:
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        
        # Get host and port from environment or config
        self.host = get_service_host('unified_memory', '0.0.0.0')
        self.port = get_service_port('unified_memory', 5596)
        
        # Apply ZMQ security if enabled
        self.secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
        if self.secure_zmq and SECURE_ZMQ_AVAILABLE:
            try:
                logger.info("Configuring secure ZMQ...")
                start_auth()
                self.socket = configure_secure_server(self.socket)
                logger.info("Secure ZMQ configured successfully")
            except Exception as e:
                logger.error(f"Failed to configure secure ZMQ: {e}")
                self.secure_zmq = False
        
        # Bind to all interfaces
        try:
            self.socket.bind(f"tcp://{self.host}:{self.port}")
            logger.info(f"Unified Memory Reasoning Agent listening on {self.host}:{self.port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind to port {self.port}: {str(e)}")
            raise
        
        # Initialize memory storage (key: memory_id, value: memory_item)
        self.memory_store = {}
        
        # For memory statistics
        self.memory_stats = {
            "total_memories": 0,
            "total_reinforcements": 0,
            "total_decays": 0,
            "memories_forgotten": 0,
            "last_decay_check": time.time(),
            "last_sync": time.time()
        }
        
        # Thread control
        self.running = True
        self.decay_thread = None
        
        # Command handlers
        self.command_handlers = {
            "TEST_PING": self._handle_test_ping,
            "STORE_MEMORY": self._handle_store_memory,
            "QUERY_MEMORY": self._handle_query_memory,
            "REINFORCE_MEMORY": self._handle_reinforce_memory,
            "GET_MEMORY_STATUS": self._handle_get_memory_status,
            "SYNC_MEMORIES": self._handle_sync_memories,
            "DELETE_MEMORY": self._handle_delete_memory
        }
        
        # Register with SystemDigitalTwin using service discovery
        self._register_with_service_discovery()
        
    def _register_with_service_discovery(self):
        """
        Register this agent with the SystemDigitalTwin service registry.
        Uses the new service discovery client.
        """
        # Retry settings
        max_retries = 3
        retry_delay = 1  # seconds
        
        try:
            # Get IP address for registration
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))  # Doesn't have to be reachable
                my_ip = s.getsockname()[0]
                s.close()
            except Exception as e:
                logger.warning(f"Failed to determine IP address: {e}, using configured host")
                my_ip = self.host if self.host != '0.0.0.0' else 'localhost'
            
            # Prepare extra service information
            additional_info = {
                "api_version": "1.0",
                "supports_secure_zmq": self.secure_zmq,
                "supports_batching": True,
                "last_started": time.strftime("%Y-%m-%d %H:%M:%S"),
                "memory_capabilities": ["decay", "reinforcement", "cross-reference"]
            }
            
            # Check if we should use localhost for SystemDigitalTwin
            manual_sdt_address = None
            if os.environ.get("FORCE_LOCAL_SDT", "0") == "1":
                manual_sdt_address = "tcp://localhost:7120"
                logger.info(f"Using forced local SDT address: {manual_sdt_address}")
            
            # Attempt to register with retries
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"Registering with service discovery as UnifiedMemoryReasoningAgent at {my_ip}:{self.port} (attempt {attempt} of {max_retries})")
                    response = register_service(
                        name="UnifiedMemoryReasoningAgent",
                        location="PC2",
                        ip=my_ip,
                        port=self.port,
                        additional_info=additional_info,
                        manual_sdt_address=manual_sdt_address
                    )
                    
                    # Check response
                    if response.get("status") == "SUCCESS":
                        logger.info("Successfully registered with service discovery")
                        return True
                    else:
                        logger.warning(f"Registration attempt {attempt} failed: {response.get('message', 'Unknown error')}")
                        
                        # If this is not the last attempt, wait and try again
                        if attempt < max_retries:
                            logger.info(f"Retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                        else:
                            logger.error(f"All registration attempts failed")
                            return False
                            
                except Exception as e:
                    # If this is not the last attempt, wait and try again
                    logger.warning(f"Error during registration attempt {attempt}: {e}")
                    if attempt < max_retries:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"All registration attempts failed")
                        return False
            
            return False  # Should not reach here, but just in case
            
        except Exception as e:
            logger.error(f"Error registering with service discovery: {e}")
            logger.warning("Agent will continue to function locally, but won't be discoverable by other agents")
            return False
    
    def _start_decay_thread(self):
        """Start the memory decay background thread"""
        self.decay_thread = threading.Thread(target=self._decay_loop, daemon=True)
        self.decay_thread.start()
        logger.info("Started memory decay background thread")
    
    def _decay_loop(self):
        """Background loop to apply memory decay periodically"""
        logger.info("Memory decay loop started")
        
        while self.running:
            try:
                # Sleep for the decay interval
                time.sleep(MEMORY_DECAY_INTERVAL)
                
                # Apply decay to all memories
                self._apply_decay()
                
            except Exception as e:
                logger.error(f"Error in decay loop: {e}")
                # Shorter sleep on error
                time.sleep(10)
    
    def _apply_decay(self):
        """Apply decay to memories based on last access time"""
        now = time.time()
        decay_count = 0
        forget_count = 0
        
        # Log before decay
        logger.info(f"Starting memory decay cycle. Current memory count: {len(self.memory_store)}")
        
        # Create a list of memories to process to avoid modifying during iteration
        memory_ids = list(self.memory_store.keys())
        
        for memory_id in memory_ids:
            try:
                memory = self.memory_store[memory_id]
                
                # Skip if accessed recently
                last_accessed = memory.get("last_accessed", 0)
                if now - last_accessed < MEMORY_DECAY_THRESHOLD:
                    continue
                
                # Apply decay to strength
                current_strength = memory.get("strength", 1.0)
                new_strength = current_strength * MEMORY_DECAY_FACTOR
                
                # Update the memory with new strength
                memory["strength"] = new_strength
                memory["last_decay"] = now
                self.memory_store[memory_id] = memory
                decay_count += 1
                
                # If strength is below threshold, forget the memory
                if new_strength < MIN_MEMORY_STRENGTH:
                    # Instead of deleting, mark as forgotten but keep for recovery
                    memory["forgotten"] = True
                    forget_count += 1
                    logger.debug(f"Memory {memory_id} forgotten due to low strength: {new_strength}")
            
            except Exception as e:
                logger.error(f"Error applying decay to memory {memory_id}: {e}")
        
        # Update stats
        self.memory_stats["total_decays"] += decay_count
        self.memory_stats["memories_forgotten"] += forget_count
        self.memory_stats["last_decay_check"] = now
        
        # Log after decay
        logger.info(f"Memory decay cycle complete. Decayed: {decay_count}, Forgotten: {forget_count}")
    
    def _apply_reinforcement(self, memory_id: str) -> bool:
        """
        Reinforce a memory by increasing its strength
        
        Args:
            memory_id: ID of the memory to reinforce
            
        Returns:
            bool: True if reinforcement was successful, False otherwise
        """
        if memory_id not in self.memory_store:
            logger.warning(f"Cannot reinforce memory {memory_id}: not found")
            return False
        
        try:
            memory = self.memory_store[memory_id]
            
            # Update last_accessed timestamp
            memory["last_accessed"] = time.time()
            
            # Increase strength
            current_strength = memory.get("strength", 1.0)
            new_strength = min(current_strength * REINFORCEMENT_FACTOR, MAX_MEMORY_STRENGTH)
            memory["strength"] = new_strength
            
            # If memory was forgotten, unmark it
            if memory.get("forgotten", False):
                memory["forgotten"] = False
                logger.info(f"Memory {memory_id} recovered from forgotten state")
            
            # Update the memory
            self.memory_store[memory_id] = memory
            
            # Update stats
            self.memory_stats["total_reinforcements"] += 1
            
            logger.info(f"Memory {memory_id} reinforced. New strength: {new_strength:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error reinforcing memory {memory_id}: {e}")
            return False
    
    def _generate_memory_id(self) -> str:
        """Generate a unique memory ID"""
        return f"mem_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    def _handle_store_memory(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle STORE_MEMORY command
        
        Args:
            message: The command message containing memory data
            
        Returns:
            Response message
        """
        try:
            # Extract memory data
            memory_data = message.get("data", {})
            if not memory_data:
                return {
                    "status": "ERROR",
                    "message": "No memory data provided"
                }
            
            # Check if memory_id is provided, otherwise generate one
            memory_id = memory_data.get("id")
            if not memory_id:
                memory_id = self._generate_memory_id()
                memory_data["id"] = memory_id
            
            # Add metadata if not present
            if "created_at" not in memory_data:
                memory_data["created_at"] = time.time()
            
            memory_data["last_accessed"] = time.time()
            memory_data["strength"] = memory_data.get("strength", 1.0)
            memory_data["source"] = memory_data.get("source", "unknown")
            memory_data["forgotten"] = False
            
            # Store the memory
            self.memory_store[memory_id] = memory_data
            
            # Update stats
            self.memory_stats["total_memories"] = len(self.memory_store)
            
            logger.info(f"Stored memory {memory_id}")
            
            return {
                "status": "SUCCESS",
                "message": "Memory stored successfully",
                "data": {
                    "memory_id": memory_id
                }
            }
            
        except Exception as e:
            logger.error(f"Error handling STORE_MEMORY: {e}")
            return {
                "status": "ERROR",
                "message": f"Failed to store memory: {str(e)}"
            }
    
    def _handle_query_memory(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle QUERY_MEMORY command
        
        Args:
            message: The command message containing query parameters
            
        Returns:
            Response message with matching memories
        """
        try:
            # Extract query parameters
            query_params = message.get("query", {})
            if not query_params:
                return {
                    "status": "ERROR",
                    "message": "No query parameters provided"
                }
            
            # Different query types
            memory_id = query_params.get("id")
            memory_ids = query_params.get("ids", [])
            keywords = query_params.get("keywords", [])
            source = query_params.get("source")
            min_strength = query_params.get("min_strength", 0.0)
            include_forgotten = query_params.get("include_forgotten", False)
            
            # If specific memory_id is provided
            if memory_id:
                if memory_id in self.memory_store:
                    memory = self.memory_store[memory_id]
                    
                    # Skip if forgotten and not explicitly included
                    if memory.get("forgotten", False) and not include_forgotten:
                        return {
                            "status": "ERROR",
                            "message": f"Memory {memory_id} is forgotten"
                        }
                    
                    # Update last_accessed timestamp
                    memory["last_accessed"] = time.time()
                    self.memory_store[memory_id] = memory
                    
                    return {
                        "status": "SUCCESS",
                        "message": "Memory found",
                        "data": {
                            "memories": [memory]
                        }
                    }
                else:
                    return {
                        "status": "ERROR",
                        "message": f"Memory {memory_id} not found"
                    }
            
            # If list of memory_ids is provided
            elif memory_ids:
                memories = []
                for mid in memory_ids:
                    if mid in self.memory_store:
                        memory = self.memory_store[mid]
                        
                        # Skip if forgotten and not explicitly included
                        if memory.get("forgotten", False) and not include_forgotten:
                            continue
                        
                        # Update last_accessed timestamp
                        memory["last_accessed"] = time.time()
                        self.memory_store[mid] = memory
                        
                        memories.append(memory)
                
                return {
                    "status": "SUCCESS",
                    "message": f"Found {len(memories)} memories",
                    "data": {
                        "memories": memories
                    }
                }
            
            # If keywords are provided, perform a search
            elif keywords:
                matching_memories = []
                
                for memory_id, memory in self.memory_store.items():
                    # Skip if forgotten and not explicitly included
                    if memory.get("forgotten", False) and not include_forgotten:
                        continue
                    
                    # Skip if below minimum strength
                    if memory.get("strength", 0.0) < min_strength:
                        continue
                    
                    # Skip if source filter doesn't match
                    if source and memory.get("source") != source:
                        continue
                    
                    # Check if any keyword matches
                    content = str(memory.get("content", "")).lower()
                    if any(keyword.lower() in content for keyword in keywords):
                        # Update last_accessed timestamp
                        memory["last_accessed"] = time.time()
                        self.memory_store[memory_id] = memory
                        
                        matching_memories.append(memory)
                
                return {
                    "status": "SUCCESS",
                    "message": f"Found {len(matching_memories)} matching memories",
                    "data": {
                        "memories": matching_memories
                    }
                }
            
            # If source filter is provided
            elif source:
                matching_memories = []
                
                for memory_id, memory in self.memory_store.items():
                    # Skip if forgotten and not explicitly included
                    if memory.get("forgotten", False) and not include_forgotten:
                        continue
                    
                    # Skip if below minimum strength
                    if memory.get("strength", 0.0) < min_strength:
                        continue
                    
                    # Check if source matches
                    if memory.get("source") == source:
                        # Update last_accessed timestamp
                        memory["last_accessed"] = time.time()
                        self.memory_store[memory_id] = memory
                        
                        matching_memories.append(memory)
                
                return {
                    "status": "SUCCESS",
                    "message": f"Found {len(matching_memories)} memories from source {source}",
                    "data": {
                        "memories": matching_memories
                    }
                }
            
            # If no specific query type is provided, return error
            return {
                "status": "ERROR",
                "message": "Invalid query parameters. Provide id, ids, keywords, or source."
            }
            
        except Exception as e:
            logger.error(f"Error handling QUERY_MEMORY: {e}")
            return {
                "status": "ERROR",
                "message": f"Failed to query memory: {str(e)}"
            }
    
    def _handle_reinforce_memory(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle REINFORCE_MEMORY command
        
        Args:
            message: The command message containing memory_id
            
        Returns:
            Response message
        """
        try:
            # Extract memory_id
            memory_id = message.get("memory_id")
            if not memory_id:
                return {
                    "status": "ERROR",
                    "message": "No memory_id provided"
                }
            
            # Apply reinforcement
            success = self._apply_reinforcement(memory_id)
            
            if success:
                return {
                    "status": "SUCCESS",
                    "message": f"Memory {memory_id} reinforced successfully",
                    "data": {
                        "memory_id": memory_id,
                        "strength": self.memory_store[memory_id].get("strength", 0.0)
                    }
                }
            else:
                return {
                    "status": "ERROR",
                    "message": f"Failed to reinforce memory {memory_id}"
                }
            
        except Exception as e:
            logger.error(f"Error handling REINFORCE_MEMORY: {e}")
            return {
                "status": "ERROR",
                "message": f"Failed to reinforce memory: {str(e)}"
            }
    
    def _handle_get_memory_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle GET_MEMORY_STATUS command
        
        Args:
            message: The command message
            
        Returns:
            Response message with memory status
        """
        try:
            # Count active (non-forgotten) memories
            active_memories = sum(1 for m in self.memory_store.values() if not m.get("forgotten", False))
            
            # Get memory stats
            status = {
                "total_memories": len(self.memory_store),
                "active_memories": active_memories,
                "forgotten_memories": len(self.memory_store) - active_memories,
                "total_reinforcements": self.memory_stats["total_reinforcements"],
                "total_decays": self.memory_stats["total_decays"],
                "last_decay_check": self.memory_stats["last_decay_check"],
                "last_sync": self.memory_stats["last_sync"],
                "timestamp": time.time()
            }
            
            return {
                "status": "SUCCESS",
                "message": "Memory status retrieved successfully",
                "data": status
            }
            
        except Exception as e:
            logger.error(f"Error handling GET_MEMORY_STATUS: {e}")
            return {
                "status": "ERROR",
                "message": f"Failed to get memory status: {str(e)}"
            }
    
    def _handle_sync_memories(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle SYNC_MEMORIES command
        
        Args:
            message: The command message containing memories to sync
            
        Returns:
            Response message
        """
        try:
            # Extract memories to sync
            memories = message.get("memories", [])
            if not memories:
                return {
                    "status": "ERROR",
                    "message": "No memories provided for synchronization"
                }
            
            # Process each memory
            synced_count = 0
            for memory in memories:
                memory_id = memory.get("id")
                if not memory_id:
                    continue
                
                # If memory exists, compare timestamps
                if memory_id in self.memory_store:
                    existing_memory = self.memory_store[memory_id]
                    
                    # Skip if local version is newer
                    if existing_memory.get("last_accessed", 0) > memory.get("last_accessed", 0):
                        continue
                    
                    # Use the stronger of the two strengths
                    memory["strength"] = max(
                        memory.get("strength", 1.0),
                        existing_memory.get("strength", 1.0)
                    )
                
                # Store or update the memory
                self.memory_store[memory_id] = memory
                synced_count += 1
            
            # Update sync timestamp
            self.memory_stats["last_sync"] = time.time()
            self.memory_stats["total_memories"] = len(self.memory_store)
            
            return {
                "status": "SUCCESS",
                "message": f"Synchronized {synced_count} memories",
                "data": {
                    "synced_count": synced_count,
                    "total_memories": len(self.memory_store)
                }
            }
            
        except Exception as e:
            logger.error(f"Error handling SYNC_MEMORIES: {e}")
            return {
                "status": "ERROR",
                "message": f"Failed to sync memories: {str(e)}"
            }
    
    def _handle_delete_memory(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle DELETE_MEMORY command
        
        Args:
            message: The command message containing memory_id
            
        Returns:
            Response message
        """
        try:
            # Extract memory_id
            memory_id = message.get("memory_id")
            if not memory_id:
                return {
                    "status": "ERROR",
                    "message": "No memory_id provided"
                }
            
            # Check if memory exists
            if memory_id not in self.memory_store:
                return {
                    "status": "ERROR",
                    "message": f"Memory {memory_id} not found"
                }
            
            # Delete the memory
            del self.memory_store[memory_id]
            
            # Update stats
            self.memory_stats["total_memories"] = len(self.memory_store)
            
            return {
                "status": "SUCCESS",
                "message": f"Memory {memory_id} deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error handling DELETE_MEMORY: {e}")
            return {
                "status": "ERROR",
                "message": f"Failed to delete memory: {str(e)}"
            }
    
    def _handle_test_ping(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle TEST_PING command
        
        Args:
            message: The command message
            
        Returns:
            Response message
        """
        logger.info("Received TEST_PING command")
        return {
            "status": "SUCCESS",
            "message": "TEST_PING received and processed",
            "data": {
                "echo": message.get("data", "No data provided"),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "agent": "UnifiedMemoryReasoningAgent",
                "location": "PC2"
            }
        }
    
    def start(self):
        """Start the UnifiedMemoryReasoningAgent"""
        try:
            logger.info("Starting Unified Memory Reasoning Agent...")
            
            # Start the decay thread
            self._start_decay_thread()
            
            # Main processing loop
            while self.running:
                try:
                    # Receive message
                    identity, _, message_data = self.socket.recv_multipart()
                    
                    # Parse the message
                    try:
                        message = json.loads(message_data.decode())
                        logger.info(f"Received message: {message.get('command', 'unknown')}")
                    except json.JSONDecodeError:
                        logger.error("Received invalid JSON")
                        response = {
                            "status": "ERROR",
                            "message": "Invalid JSON in message"
                        }
                        self.socket.send_multipart([
                            identity,
                            b'',
                            json.dumps(response).encode()
                        ])
                        continue
                    
                    # Process message based on command
                    command = message.get("command")
                    if command in self.command_handlers:
                        response = self.command_handlers[command](message)
                    else:
                        logger.warning(f"Unknown command: {command}")
                        response = {
                            "status": "ERROR",
                            "message": f"Unknown command: {command}"
                        }
                    
                    # Send response
                    self.socket.send_multipart([
                        identity,
                        b'',
                        json.dumps(response).encode()
                    ])
                    
                except zmq.error.Again:
                    # Socket timeout, continue loop
                    continue
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    # Continue the loop rather than exiting
                    continue
                
        except KeyboardInterrupt:
            logger.info("Shutting down Unified Memory Reasoning Agent...")
        finally:
            self.running = False
            if self.decay_thread and self.decay_thread.is_alive():
                self.decay_thread.join(timeout=1.0)
            self._cleanup()
            
    def _cleanup(self):
        """Clean up resources before exit"""
        logger.info("Cleaning up resources...")
        # Close main socket
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
        
        # Terminate ZMQ context
        if hasattr(self, 'context') and self.context:
            self.context.term()
    
    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process message and return response - Legacy method kept for compatibility
        
        Args:
            message: The incoming message to process
            
        Returns:
            Response message
        """
        logger.info(f"Processing message via legacy method: {message}")
        
        # Determine command and route to appropriate handler
        command = message.get("command")
        if command in self.command_handlers:
            return self.command_handlers[command](message)
        else:
            logger.warning(f"Unknown command in legacy method: {command}")
            return {
                "status": "ERROR",
                "message": f"Unknown command: {command}"
            }
        
if __name__ == "__main__":
    agent = UnifiedMemoryReasoningAgent()
    agent.start() 