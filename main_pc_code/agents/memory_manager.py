from main_pc_code.src.core.base_agent import BaseAgent
"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

Memory Manager Agent
Manages and coordinates memory operations across the system
"""

import zmq
import json
import logging
import threading
import time
import collections
from datetime import datetime
from typing import Dict, Any, Optional, List, Deque, Union
from main_pc_code.utils.config_loader import load_config
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('memory_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MemoryManager')

# Load configuration at module level
config = load_config()

class MemoryManager(BaseAgent):
    def _get_default_port(self) -> int:
        """Override default port to use the configured port."""
        return 5712  # Using a new port that's not in use
        
    def __init__(self, port=None):
        # Get configuration values with fallbacks
        agent_port = config.get("port", 5712) if port is None else port
        agent_name = config.get("name", "MemoryManager")
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=agent_name, port=agent_port)
        
        """Initialize the Memory Manager.
        
        Args:
            port: Port to listen on
            memory_size: Maximum number of interactions to store in short-term memory
        """
        self.memory_size = config.get("memory_size", 1000)
        
        # Initialize short-term memory as a fixed-size deque
        self.memory: Deque[Dict[str, Any]] = collections.deque(maxlen=self.memory_size)
        
        # Record start time for uptime calculation
        self.start_time = time.time()
        
        # Start health check thread
        self.health_check_thread = threading.Thread(target=self._health_check_loop)
        self.health_check_thread.daemon = True
        self.health_check_thread.start()
        
        # Initialize metrics
        self.processed_items = 0
        self.memory_operations = 0
        
        logger.info(f"Memory Manager initialized on port {self.port} with memory size {self.memory_size}")
        
    def _health_check_loop(self):
        """Continuously check the health of the agent."""
        while True:
            try:
                # Update uptime
                self.uptime = time.time() - self.start_time
                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                
    def get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        return {
            'status': 'success',
            'uptime': time.time() - self.start_time,
            'components': {
                'memory_store': True,
                'memory_retrieval': True,
                'memory_cleanup': True
            },
            'memory_usage': len(self.memory),
            'memory_capacity': self.memory_size
        }
    
    def add_interaction(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """Add an interaction to short-term memory.
        
        Args:
            interaction: Dictionary containing the interaction data.
                Must include 'timestamp', 'content', and 'source' keys.
                
        Returns:
            Dictionary with status and message.
        """
        try:
            # Validate required fields
            required_fields = ['content', 'source']
            for field in required_fields:
                if field not in interaction:
                    return {
                        'status': 'error',
                        'message': f"Missing required field: {field}"
                    }
            
            # Add timestamp if not present
            if 'timestamp' not in interaction:
                interaction['timestamp'] = time.time()
                
            # Add to memory
            self.memory.append(interaction)
            
            # Update metrics
            self.memory_operations += 1
            self.processed_items += 1
            
            logger.info(f"Added interaction from {interaction['source']}")
            
            return {
                'status': 'success',
                'message': 'Interaction added to memory',
                'memory_size': len(self.memory)
            }
        except Exception as e:
            logger.error(f"Error adding interaction: {e}")
            return {
                'status': 'error',
                'message': f"Failed to add interaction: {str(e)}"
            }
    
    def get_recent_context(self, limit: Optional[int] = None, filter_source: Optional[str] = None) -> Dict[str, Any]:
        """Get recent interactions from memory.
        
        Args:
            limit: Maximum number of interactions to return (None for all)
            filter_source: Only return interactions from this source
            
        Returns:
            Dictionary with status and interactions.
        """
        try:
            # Convert deque to list for easier manipulation
            memory_list = list(self.memory)
            
            # Apply source filter if specified
            if filter_source:
                memory_list = [item for item in memory_list if item.get('source') == filter_source]
            
            # Apply limit if specified
            if limit and limit > 0:
                memory_list = memory_list[-limit:]
            
            # Update metrics
            self.memory_operations += 1
            
            logger.info(f"Retrieved {len(memory_list)} recent interactions")
            
            return {
                'status': 'success',
                'interactions': memory_list,
                'count': len(memory_list)
            }
        except Exception as e:
            logger.error(f"Error retrieving recent context: {e}")
            return {
                'status': 'error',
                'message': f"Failed to retrieve recent context: {str(e)}"
            }
    
    def clear_memory(self) -> Dict[str, Any]:
        """Clear all interactions from memory.
        
        Returns:
            Dictionary with status and message.
        """
        try:
            # Get current memory size for reporting
            previous_size = len(self.memory)
            
            # Clear memory
            self.memory.clear()
            
            # Update metrics
            self.memory_operations += 1
            
            logger.info(f"Cleared {previous_size} interactions from memory")
            
            return {
                'status': 'success',
                'message': f"Cleared {previous_size} interactions from memory"
            }
        except Exception as e:
            logger.error(f"Error clearing memory: {e}")
            return {
                'status': 'error',
                'message': f"Failed to clear memory: {str(e)}"
            }
        
    def run(self):
        """Run the main agent loop."""
        logger.info("Starting Memory Manager main loop")
        
        while True:
            try:
                # Wait for next request
                message = self.socket.recv_json()
                logger.info(f"Received request: {message}")
                
                # Process request
                response = self._handle_request(message)
                
                # Send response
                self.socket.send_json(response)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                try:
                    self.socket.send_json({
                        'status': 'error',
                        'message': str(e)
                    })
                except zmq.error.ZMQError as zmq_err:
                    logger.error(f"ZMQ error sending response: {zmq_err}")
                
    def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action')
        
        if action == 'ping':
            return {'status': 'success', 'message': 'pong'}
            
        elif action == 'get_health':
            return self.get_health_status()
            
        elif action == 'add_interaction':
            return self.add_interaction(request.get('interaction', {}))
            
        elif action == 'get_recent_context':
            return self.get_recent_context(
                limit=request.get('limit'),
                filter_source=request.get('filter_source')
            )
            
        elif action == 'clear_memory':
            return self.clear_memory()
            
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}
            
    def cleanup(self):
        """Stop the agent and clean up resources."""
        self.socket.close()
        self.context.term()
        logger.info("Memory Manager stopped")
        super().cleanup()

    def _get_health_status(self):
        """Overrides the base method to add agent-specific health metrics."""
        base_status = super()._get_health_status()
        specific_metrics = {
            "status_detail": "active",
            "processed_items": getattr(self, 'processed_items', 0),
            "memory_operations": getattr(self, 'memory_operations', 0)
        }
        base_status.update(specific_metrics)
        return base_status
    
    def _perform_initialization(self):
        """Initialize agent components."""
        # For future implementation
        pass


        
    def stop(self):

        
            """Stop the agent and clean up resources."""

        
            self.socket.close()

        
            self.context.term()

        
            logger.info("Memory Manager stopped")

    def health_check(self):
        """Perform health check and return status."""
        try:
            return {
                "status": "healthy",
                "agent": self.name,
                "uptime": time.time() - self.start_time,
                "memory_usage": len(self.memory),
                "memory_capacity": self.memory_size,
                "memory_operations": getattr(self, 'memory_operations', 0)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = MemoryManager()
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