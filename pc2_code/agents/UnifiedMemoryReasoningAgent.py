import os
import yaml
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
import pickle

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
from main_pc_code.utils.env_loader import get_env

# Import secure ZMQ utilities if available
try:
    from main_pc_code.src.network.secure_zmq import configure_secure_server, configure_secure_client, start_auth
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

# Get bind address from environment variables with default to 0.0.0.0 for Docker compatibility
BIND_ADDRESS = get_env('BIND_ADDRESS', '0.0.0.0')
INTERRUPT_PORT = int(os.environ.get('INTERRUPT_PORT', 5576))  # Interrupt handler port

from main_pc_code.src.core.base_agent import BaseAgent
from pc2_code.agents.utils.config_loader import Config

class UnifiedMemoryReasoningAgent(BaseAgent):

    def __init__(self, port: int = None):

        super().__init__(name="UnifiedMemoryReasoningAgent", port=port)

        self.start_time = time.time()

    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        
        # Get host and port from environment or config
        self.host = get_env('MEMORY_HOST', get_service_host('unified_memory', BIND_ADDRESS))
        self.port = int(get_env('MEMORY_PORT', get_service_port('unified_memory', 5596)))
        self.health_port = int(get_env('MEMORY_HEALTH_PORT', get_service_port('unified_memory_health', 5597)))
        
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
        
        # Bind to address using BIND_ADDRESS for Docker compatibility
        bind_address = f"tcp://{self.host}:{self.port}"
        try:
            self.socket.bind(bind_address)
            logger.info(f"Unified Memory Reasoning Agent listening on {bind_address}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind to {bind_address}: {str(e)}")
            raise
        
        # Setup health check socket
        self.health_socket = self.context.socket(zmq.REP)
        if self.secure_zmq and SECURE_ZMQ_AVAILABLE:
            self.health_socket = configure_secure_server(self.health_socket)
            
        health_bind_address = f"tcp://{BIND_ADDRESS}:{self.health_port}"
        try:
            self.health_socket.bind(health_bind_address)
            logger.info(f"Health check socket bound to {health_bind_address}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind health check socket to {health_bind_address}: {e}")
            # Continue even if health check socket fails
        
        # Setup interrupt subscription
        self.interrupt_socket = self.context.socket(zmq.SUB)
        if self.secure_zmq and SECURE_ZMQ_AVAILABLE:
            self.interrupt_socket = configure_secure_client(self.interrupt_socket)
            
        # Try to get the interrupt handler address from service discovery
        interrupt_address = get_service_address("StreamingInterruptHandler")
        if not interrupt_address:
            # Fall back to configured port
            interrupt_address = f"tcp://localhost:{INTERRUPT_PORT}"
            
        try:
            self.interrupt_socket.connect(interrupt_address)
            self.interrupt_socket.setsockopt(zmq.SUBSCRIBE, b"")
            logger.info(f"Connected to interrupt handler at {interrupt_address}")
        except Exception as e:
            logger.warning(f"Could not connect to interrupt handler: {e}")
        
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
        self.interrupted = False
        self.decay_thread = None
        self.interrupt_thread = None
        self.health_thread = None
        
        # Statistics for health monitoring
        self.start_time = time.time()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.health_check_requests = 0
        
        # Command handlers
        self.command_handlers = {
            "TEST_PING": self._handle_test_ping,
            "STORE_MEMORY": self._handle_store_memory,
            "QUERY_MEMORY": self._handle_query_memory,
            "REINFORCE_MEMORY": self._handle_reinforce_memory,
            "GET_MEMORY_STATUS": self._handle_get_memory_status,
            "SYNC_MEMORIES": self._handle_sync_memories,
            "DELETE_MEMORY": self._handle_delete_memory,
            "HEALTH_CHECK": self._handle_health_check
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
                "memory_capabilities": ["decay", "reinforcement", "cross-reference"],
                "health_check_port": self.health_port
            }
            
            # Attempt to register with retries
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"Registering with service discovery as UnifiedMemoryReasoningAgent at {my_ip}:{self.port} (attempt {attempt} of {max_retries})")
                    response = register_service(
                        name="UnifiedMemoryReasoningAgent",
                        location="PC2",
                        ip=my_ip,
                        port=self.port,
                        additional_info=additional_info
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
    
    def _start_interrupt_thread(self):
        """Start a thread to monitor for interrupt signals"""
        self.interrupt_thread = threading.Thread(target=self._interrupt_monitor_loop, daemon=True)
        self.interrupt_thread.start()
        logger.info("Started interrupt monitoring thread")
    
    def _interrupt_monitor_loop(self):
        """Background loop to monitor for interrupt signals"""
        logger.info("Interrupt monitor loop started")
        
        poller = zmq.Poller()
        poller.register(self.interrupt_socket, zmq.POLLIN)
        
        while self.running:
            try:
                # Check for interrupt signals with timeout
                if poller.poll(100):  # 100ms timeout
                    msg = self.interrupt_socket.recv()
                    data = pickle.loads(msg)
                    
                    if data.get('type') == 'interrupt':
                        logger.info("Received interrupt signal")
                        self.interrupted = True
                        
                        # Handle the interrupt
                        self._handle_interrupt()
                
                # Reset interrupt flag after a short delay
                if self.interrupted:
                    time.sleep(0.5)
                    self.interrupted = False
                    
                time.sleep(0.1)  # Small sleep to prevent CPU hogging
                
            except Exception as e:
                logger.error(f"Error in interrupt monitor loop: {e}")
                time.sleep(1)  # Sleep longer on error
    
    def _handle_interrupt(self):
        """Handle interrupt signal by stopping current operations"""
        try:
            logger.info("Handling interrupt signal")
            
            # Cancel any ongoing memory operations
            # For example, clear any pending memory operations
            
            logger.info("Interrupt handling completed")
        except Exception as e:
            logger.error(f"Error handling interrupt: {e}")
    
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
    
    def _handle_health_check(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle health check request
        
        Args:
            message: The command message
            
        Returns:
            Response message with health status
        """
        self.health_check_requests += 1
        logger.debug("Received health check request")
        
        return self._health_check()
    
    def _health_check(self) -> Dict[str, Any]:
        """
        Perform health check and return status
        
        Returns:
            Dict with health status information
        """
        uptime = time.time() - self.start_time
        
        # Check if decay thread is alive
        decay_thread_alive = self.decay_thread is not None and self.decay_thread.is_alive()
        
        # Check if interrupt thread is alive
        interrupt_thread_alive = self.interrupt_thread is not None and self.interrupt_thread.is_alive()
        
        return {
            "status": "success",
            "agent": "UnifiedMemoryReasoningAgent",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": uptime,
            "health": {
                "overall": True,  # Overall health status
                "decay_thread": decay_thread_alive,
                "interrupt_thread": interrupt_thread_alive,
                "memory_store_size": len(self.memory_store)
            },
            "metrics": {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "health_check_requests": self.health_check_requests,
                "total_memories": self.memory_stats["total_memories"],
                "total_reinforcements": self.memory_stats["total_reinforcements"],
                "total_decays": self.memory_stats["total_decays"],
                "memories_forgotten": self.memory_stats["memories_forgotten"]
            },
            "version": "1.0"
        }
    
    def _start_health_check_thread(self):
        """Start a thread to handle health check requests"""
        self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_thread.start()
        logger.info("Started health check thread")
    
    def _health_check_loop(self):
        """Background loop to handle health check requests"""
        logger.info("Health check loop started")
        
        poller = zmq.Poller()
        poller.register(self.health_socket, zmq.POLLIN)
        
        while self.running:
            try:
                # Check for health check requests with timeout
                if poller.poll(100):  # 100ms timeout
                    # Receive request (don't care about content)
                    _ = self.health_socket.recv()
                    
                    # Get health data
                    health_data = self._health_check()
                    
                    # Send response
                    self.health_socket.send_json(health_data)
                    
                time.sleep(0.1)  # Small sleep to prevent CPU hogging
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(1)  # Sleep longer on error
    
    def start(self):
        """Start the agent and its background threads"""
        logger.info("Starting UnifiedMemoryReasoningAgent")
        
        # Start background threads
        self._start_decay_thread()
        self._start_interrupt_thread()
        self._start_health_check_thread()
        
        try:
            # Main processing loop
            while self.running:
                try:
                    # Poll for incoming messages with timeout
                    poller = zmq.Poller()
                    poller.register(self.socket, zmq.POLLIN)
                    
                    # Poll with timeout to allow checking for interrupts
                    if poller.poll(100):  # 100ms timeout
                        # Receive multipart message (ROUTER socket)
                        identity, message_data = self.socket.recv_multipart()
                        
                        # Parse the message
                        try:
                            message = json.loads(message_data)
                            logger.debug(f"Received message from {identity}: {message.get('command', 'unknown')}")
                            
                            # Update request counter
                            self.total_requests += 1
                            
                            # Process the message if not interrupted
                            if not self.interrupted:
                                response = self.process_message(message)
                                if response.get("status") == "SUCCESS" or response.get("status") == "success":
                                    self.successful_requests += 1
                                else:
                                    self.failed_requests += 1
                            else:
                                response = {
                                    "status": "error", 
                                    "message": "Operation interrupted by user",
                                    "command": message.get("command")
                                }
                                self.interrupted = False
                                self.failed_requests += 1
                            
                            # Send the response back to the correct client
                            self.socket.send_multipart([identity, json.dumps(response).encode()])
                            
                        except json.JSONDecodeError:
                            logger.error(f"Received invalid JSON from {identity}")
                            error_response = {
                                "status": "error",
                                "message": "Invalid JSON message"
                            }
                            self.socket.send_multipart([identity, json.dumps(error_response).encode()])
                            self.failed_requests += 1
                            
                except zmq.ZMQError as e:
                    logger.error(f"ZMQ error: {e}")
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self._cleanup()
            
    def _cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources")
        
        # Set running flag to false to stop all threads
        self.running = False
        
        # Wait for threads to finish
        if self.decay_thread and self.decay_thread.is_alive():
            self.decay_thread.join(timeout=2.0)
            
        if self.interrupt_thread and self.interrupt_thread.is_alive():
            self.interrupt_thread.join(timeout=2.0)
            
        if self.health_thread and self.health_thread.is_alive():
            self.health_thread.join(timeout=2.0)
        
        # Close all ZMQ sockets
        try:
            for socket_attr in ['socket', 'interrupt_socket', 'health_socket']:
                if hasattr(self, socket_attr) and getattr(self, socket_attr):
                    getattr(self, socket_attr).close()
                    logger.info(f"Closed {socket_attr}")
        except Exception as e:
            logger.error(f"Error closing ZMQ sockets: {e}")
        
        # Terminate ZMQ context
        try:
            if hasattr(self, 'context') and self.context:
                self.context.term()
                logger.info("ZMQ context terminated")
        except Exception as e:
            logger.error(f"Error terminating ZMQ context: {e}")
            
        logger.info("Cleanup completed")



    def _get_health_status(self) -> dict:


        """Return health status information."""


        base_status = super()._get_health_status()


        # Add any additional health information specific to UnifiedMemoryReasoningAgent


        base_status.update({


            'service': 'UnifiedMemoryReasoningAgent',


            'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,


            'additional_info': {}


        })


        return base_status


    def run(self):


        """Run the agent's main loop."""


        logger.info(f"Starting {self.__class__.__name__} on port {self.port}")


        # Main loop implementation


        try:


            while True:


                # Your main processing logic here


                pass


        except KeyboardInterrupt:


            logger.info("Keyboard interrupt received, shutting down...")


        except Exception as e:


            logger.error(f"Error in main loop: {e}")


            raise




    def cleanup(self):


        """Clean up resources before shutdown."""


        logger.info("Cleaning up resources...")


        # Add specific cleanup code here


        super().cleanup()

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
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = UnifiedMemoryReasoningAgent()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'} on PC2...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'} on PC2: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name} on PC2...")
            agent.cleanup()

from main_pc_code.utils.config_loader import load_config



# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "network_config.yaml")
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": "192.168.100.16",
            "pc2_ip": "192.168.100.17",
            "bind_address": "0.0.0.0",
            "secure_zmq": False
        }

# Load both configurations
network_config = load_network_config()

# Get machine IPs from config
MAIN_PC_IP = network_config.get("main_pc_ip", "192.168.100.16")
PC2_IP = network_config.get("pc2_ip", "192.168.100.17")
BIND_ADDRESS = network_config.get("bind_address", "0.0.0.0")
# Load configuration at the module level
config = Config().get_config()

























































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































import os
import yaml
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
import pickle

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
from main_pc_code.utils.env_loader import get_env

# Import secure ZMQ utilities if available
try:
    from main_pc_code.src.network.secure_zmq import configure_secure_server, configure_secure_client, start_auth
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

# Get bind address from environment variables with default to 0.0.0.0 for Docker compatibility
BIND_ADDRESS = get_env('BIND_ADDRESS', '0.0.0.0')
INTERRUPT_PORT = int(os.environ.get('INTERRUPT_PORT', 5576))  # Interrupt handler port

class UnifiedMemoryReasoningAgent(BaseAgent):

    def __init__(self, port: int = None):

        super().__init__(name="UnifiedMemoryReasoningAgent", port=port)

        self.start_time = time.time()

    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        
        # Get host and port from environment or config
        self.host = get_env('MEMORY_HOST', get_service_host('unified_memory', BIND_ADDRESS))
        self.port = int(get_env('MEMORY_PORT', get_service_port('unified_memory', 5596)))
        self.health_port = int(get_env('MEMORY_HEALTH_PORT', get_service_port('unified_memory_health', 5597)))
        
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
        
        # Bind to address using BIND_ADDRESS for Docker compatibility
        bind_address = f"tcp://{self.host}:{self.port}"
        try:
            self.socket.bind(bind_address)
            logger.info(f"Unified Memory Reasoning Agent listening on {bind_address}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind to {bind_address}: {str(e)}")
            raise
        
        # Setup health check socket
        self.health_socket = self.context.socket(zmq.REP)
        if self.secure_zmq and SECURE_ZMQ_AVAILABLE:
            self.health_socket = configure_secure_server(self.health_socket)
            
        health_bind_address = f"tcp://{BIND_ADDRESS}:{self.health_port}"
        try:
            self.health_socket.bind(health_bind_address)
            logger.info(f"Health check socket bound to {health_bind_address}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind health check socket to {health_bind_address}: {e}")
            # Continue even if health check socket fails
        
        # Setup interrupt subscription
        self.interrupt_socket = self.context.socket(zmq.SUB)
        if self.secure_zmq and SECURE_ZMQ_AVAILABLE:
            self.interrupt_socket = configure_secure_client(self.interrupt_socket)
            
        # Try to get the interrupt handler address from service discovery
        interrupt_address = get_service_address("StreamingInterruptHandler")
        if not interrupt_address:
            # Fall back to configured port
            interrupt_address = f"tcp://localhost:{INTERRUPT_PORT}"
            
        try:
            self.interrupt_socket.connect(interrupt_address)
            self.interrupt_socket.setsockopt(zmq.SUBSCRIBE, b"")
            logger.info(f"Connected to interrupt handler at {interrupt_address}")
        except Exception as e:
            logger.warning(f"Could not connect to interrupt handler: {e}")
        
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
        self.interrupted = False
        self.decay_thread = None
        self.interrupt_thread = None
        self.health_thread = None
        
        # Statistics for health monitoring
        self.start_time = time.time()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.health_check_requests = 0
        
        # Command handlers
        self.command_handlers = {
            "TEST_PING": self._handle_test_ping,
            "STORE_MEMORY": self._handle_store_memory,
            "QUERY_MEMORY": self._handle_query_memory,
            "REINFORCE_MEMORY": self._handle_reinforce_memory,
            "GET_MEMORY_STATUS": self._handle_get_memory_status,
            "SYNC_MEMORIES": self._handle_sync_memories,
            "DELETE_MEMORY": self._handle_delete_memory,
            "HEALTH_CHECK": self._handle_health_check
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
                "memory_capabilities": ["decay", "reinforcement", "cross-reference"],
                "health_check_port": self.health_port
            }
            
            # Attempt to register with retries
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"Registering with service discovery as UnifiedMemoryReasoningAgent at {my_ip}:{self.port} (attempt {attempt} of {max_retries})")
                    response = register_service(
                        name="UnifiedMemoryReasoningAgent",
                        location="PC2",
                        ip=my_ip,
                        port=self.port,
                        additional_info=additional_info
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
    
    def _start_interrupt_thread(self):
        """Start a thread to monitor for interrupt signals"""
        self.interrupt_thread = threading.Thread(target=self._interrupt_monitor_loop, daemon=True)
        self.interrupt_thread.start()
        logger.info("Started interrupt monitoring thread")
    
    def _interrupt_monitor_loop(self):
        """Background loop to monitor for interrupt signals"""
        logger.info("Interrupt monitor loop started")
        
        poller = zmq.Poller()
        poller.register(self.interrupt_socket, zmq.POLLIN)
        
        while self.running:
            try:
                # Check for interrupt signals with timeout
                if poller.poll(100):  # 100ms timeout
                    msg = self.interrupt_socket.recv()
                    data = pickle.loads(msg)
                    
                    if data.get('type') == 'interrupt':
                        logger.info("Received interrupt signal")
                        self.interrupted = True
                        
                        # Handle the interrupt
                        self._handle_interrupt()
                
                # Reset interrupt flag after a short delay
                if self.interrupted:
                    time.sleep(0.5)
                    self.interrupted = False
                    
                time.sleep(0.1)  # Small sleep to prevent CPU hogging
                
            except Exception as e:
                logger.error(f"Error in interrupt monitor loop: {e}")
                time.sleep(1)  # Sleep longer on error
    
    def _handle_interrupt(self):
        """Handle interrupt signal by stopping current operations"""
        try:
            logger.info("Handling interrupt signal")
            
            # Cancel any ongoing memory operations
            # For example, clear any pending memory operations
            
            logger.info("Interrupt handling completed")
        except Exception as e:
            logger.error(f"Error handling interrupt: {e}")
    
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
    
    def _handle_health_check(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle health check request
        
        Args:
            message: The command message
            
        Returns:
            Response message with health status
        """
        self.health_check_requests += 1
        logger.debug("Received health check request")
        
        return self._health_check()
    
    def _health_check(self) -> Dict[str, Any]:
        """
        Perform health check and return status
        
        Returns:
            Dict with health status information
        """
        uptime = time.time() - self.start_time
        
        # Check if decay thread is alive
        decay_thread_alive = self.decay_thread is not None and self.decay_thread.is_alive()
        
        # Check if interrupt thread is alive
        interrupt_thread_alive = self.interrupt_thread is not None and self.interrupt_thread.is_alive()
        
        return {
            "status": "success",
            "agent": "UnifiedMemoryReasoningAgent",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": uptime,
            "health": {
                "overall": True,  # Overall health status
                "decay_thread": decay_thread_alive,
                "interrupt_thread": interrupt_thread_alive,
                "memory_store_size": len(self.memory_store)
            },
            "metrics": {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "health_check_requests": self.health_check_requests,
                "total_memories": self.memory_stats["total_memories"],
                "total_reinforcements": self.memory_stats["total_reinforcements"],
                "total_decays": self.memory_stats["total_decays"],
                "memories_forgotten": self.memory_stats["memories_forgotten"]
            },
            "version": "1.0"
        }
    
    def _start_health_check_thread(self):
        """Start a thread to handle health check requests"""
        self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_thread.start()
        logger.info("Started health check thread")
    
    def _health_check_loop(self):
        """Background loop to handle health check requests"""
        logger.info("Health check loop started")
        
        poller = zmq.Poller()
        poller.register(self.health_socket, zmq.POLLIN)
        
        while self.running:
            try:
                # Check for health check requests with timeout
                if poller.poll(100):  # 100ms timeout
                    # Receive request (don't care about content)
                    _ = self.health_socket.recv()
                    
                    # Get health data
                    health_data = self._health_check()
                    
                    # Send response
                    self.health_socket.send_json(health_data)
                    
                time.sleep(0.1)  # Small sleep to prevent CPU hogging
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(1)  # Sleep longer on error
    
    def start(self):
        """Start the agent and its background threads"""
        logger.info("Starting UnifiedMemoryReasoningAgent")
        
        # Start background threads
        self._start_decay_thread()
        self._start_interrupt_thread()
        self._start_health_check_thread()
        
        try:
            # Main processing loop
            while self.running:
                try:
                    # Poll for incoming messages with timeout
                    poller = zmq.Poller()
                    poller.register(self.socket, zmq.POLLIN)
                    
                    # Poll with timeout to allow checking for interrupts
                    if poller.poll(100):  # 100ms timeout
                        # Receive multipart message (ROUTER socket)
                        identity, message_data = self.socket.recv_multipart()
                        
                        # Parse the message
                        try:
                            message = json.loads(message_data)
                            logger.debug(f"Received message from {identity}: {message.get('command', 'unknown')}")
                            
                            # Update request counter
                            self.total_requests += 1
                            
                            # Process the message if not interrupted
                            if not self.interrupted:
                                response = self.process_message(message)
                                if response.get("status") == "SUCCESS" or response.get("status") == "success":
                                    self.successful_requests += 1
                                else:
                                    self.failed_requests += 1
                            else:
                                response = {
                                    "status": "error", 
                                    "message": "Operation interrupted by user",
                                    "command": message.get("command")
                                }
                                self.interrupted = False
                                self.failed_requests += 1
                            
                            # Send the response back to the correct client
                            self.socket.send_multipart([identity, json.dumps(response).encode()])
                            
                        except json.JSONDecodeError:
                            logger.error(f"Received invalid JSON from {identity}")
                            error_response = {
                                "status": "error",
                                "message": "Invalid JSON message"
                            }
                            self.socket.send_multipart([identity, json.dumps(error_response).encode()])
                            self.failed_requests += 1
                            
                except zmq.ZMQError as e:
                    logger.error(f"ZMQ error: {e}")
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self._cleanup()
            
    def _cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources")
        
        # Set running flag to false to stop all threads
        self.running = False
        
        # Wait for threads to finish
        if self.decay_thread and self.decay_thread.is_alive():
            self.decay_thread.join(timeout=2.0)
            
        if self.interrupt_thread and self.interrupt_thread.is_alive():
            self.interrupt_thread.join(timeout=2.0)
            
        if self.health_thread and self.health_thread.is_alive():
            self.health_thread.join(timeout=2.0)
        
        # Close all ZMQ sockets
        try:
            for socket_attr in ['socket', 'interrupt_socket', 'health_socket']:
                if hasattr(self, socket_attr) and getattr(self, socket_attr):
                    getattr(self, socket_attr).close()
                    logger.info(f"Closed {socket_attr}")
        except Exception as e:
            logger.error(f"Error closing ZMQ sockets: {e}")
        
        # Terminate ZMQ context
        try:
            if hasattr(self, 'context') and self.context:
                self.context.term()
                logger.info("ZMQ context terminated")
        except Exception as e:
            logger.error(f"Error terminating ZMQ context: {e}")
            
        logger.info("Cleanup completed")



    def _get_health_status(self) -> dict:


        """Return health status information."""


        base_status = super()._get_health_status()


        # Add any additional health information specific to UnifiedMemoryReasoningAgent


        base_status.update({


            'service': 'UnifiedMemoryReasoningAgent',


            'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,


            'additional_info': {}


        })


        return base_status


    def run(self):


        """Run the agent's main loop."""


        logger.info(f"Starting {self.__class__.__name__} on port {self.port}")


        # Main loop implementation


        try:


            while True:


                # Your main processing logic here


                pass


        except KeyboardInterrupt:


            logger.info("Keyboard interrupt received, shutting down...")


        except Exception as e:


            logger.error(f"Error in main loop: {e}")


            raise




    def cleanup(self):


        """Clean up resources before shutdown."""


        logger.info("Cleaning up resources...")


        # Add specific cleanup code here


        super().cleanup()

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
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = UnifiedMemoryReasoningAgent()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'} on PC2...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'} on PC2: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name} on PC2...")
            agent.cleanup()

from main_pc_code.src.core.base_agent import BaseAgentlogger.error
from main_pc_code.utils.config_loader import load_config



# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "network_config.yaml")
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": "192.168.100.16",
            "pc2_ip": "192.168.100.17",
            "bind_address": "0.0.0.0",
            "secure_zmq": False
        }

# Load both configurations
network_config = load_network_config()

# Get machine IPs from config
MAIN_PC_IP = network_config.get("main_pc_ip", "192.168.100.16")
PC2_IP = network_config.get("pc2_ip", "192.168.100.17")
BIND_ADDRESS = network_config.get("bind_address", "0.0.0.0")
# Load configuration at the module level
config = load_config()(traceback.format_exc())
    finally:
        # Make sure we clean up even if there's an error
        if 'agent' in locals():
            agent._cleanup() 


    def connect_to_main_pc_service(self, service_name: str):


        """


        Connect to a service on the main PC using the network configuration.


        


        Args:


            service_name: Name of the service in the network config ports section


        


        Returns:


            ZMQ socket connected to the service


        """


        if not hasattr(self, 'main_pc_connections'):


            self.main_pc_connections = {}


            


        if service_name not in network_config.get("ports", {}):


            logger.error(f"Service {service_name} not found in network configuration")


            return None


            


        port = network_config["ports"][service_name]


        


        # Create a new socket for this connection


        socket = self.context.socket(zmq.REQ)


        


        # Connect to the service


        socket.connect(f"tcp://{MAIN_PC_IP}:{port}")


        


        # Store the connection


        self.main_pc_connections[service_name] = socket


        


        logger.info(f"Connected to {service_name} on MainPC at {MAIN_PC_IP}:{port}")


        return socket
