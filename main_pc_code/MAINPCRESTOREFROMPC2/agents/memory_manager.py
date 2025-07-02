from src.core.base_agent import BaseAgent
"""
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
from utils.config_parser import parse_agent_args
_agent_args = parse_agent_args()

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

class MemoryManager(BaseAgent):
    def _get_default_port(self) -> int:
        """Override default port to use the configured port."""
        return 5712  # Using a new port that's not in use
        
    def __init__(self, port: int = 5712, memory_size: int = 1000, **kwargs):
        super().__init__(port=port, name="MemoryManager")
        """Initialize the Memory Manager.
        
        Args:
            port: Port to listen on
            memory_size: Maximum number of interactions to store in short-term memory
        """
        self.memory_size = memory_size
        
        # Initialize short-term memory as a fixed-size deque
        self.memory: Deque[Dict[str, Any]] = collections.deque(maxlen=memory_size)
        
        # Start health check thread
        self.health_check_thread = threading.Thread(target=self._health_check_loop)
        self.health_check_thread.daemon = True
        self.health_check_thread.start()
        
        logger.info(f"Memory Manager initialized on port {self.port} with memory size {memory_size}")
        
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
            
    def stop(self):
        """Stop the agent and clean up resources."""
        self.socket.close()
        self.context.term()
        logger.info("Memory Manager stopped")

if __name__ == '__main__':
    agent = MemoryManager()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
