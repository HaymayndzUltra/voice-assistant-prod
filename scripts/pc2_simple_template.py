#!/usr/bin/env python3
"""
Simple PC2 Agent Template
------------------------
A clean, simple template for PC2 agents that directly imports from main_pc_code.
"""

import time
import logging
import zmq
import json
import os
from typing import Dict, Any, Optional

# Direct import of BaseAgent from main_pc_code
from main_pc_code.src.core.base_agent import BaseAgent

# Direct import of Config from PC2
from pc2_code.agents.utils.config_loader import Config
from common.utils.log_setup import configure_logging

# Load configuration
config = Config().get_config()

# Set up logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "pc2_simple_agent.log")

logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PC2SimpleAgent(BaseAgent):
    """Simple PC2 agent template with direct imports."""
    
    def __init__(self, port: Optional[int] = None):
        """Initialize the agent.
        
        Args:
            port: The port number to use for ZMQ communication.
        """
        # Call the BaseAgent's __init__ with proper parameters
        super().__init__(name="PC2SimpleAgent", port=port)
        
        # Record start time for uptime calculation
        self.start_time = time.time()
        
        # Agent-specific initialization
        self.port = port if port is not None else 5570
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        
        # Initialize agent state
        self.running = True
        self.request_count = 0
        
        logger.info(f"{self.__class__.__name__} initialized on port {self.port}")
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Return health status information.
        
        Returns:
            Dict containing health status information.
        """
        # Get base status from parent
        base_status = super()._get_health_status()
        
        # Add PC2-specific health information
        base_status.update({
            'service': self.__class__.__name__,
            'uptime': time.time() - self.start_time,
            'request_count': self.request_count,
            'machine': 'pc2',
            'status': 'healthy'
        })
        
        return base_status
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming request.
        
        Args:
            request: The request to process
            
        Returns:
            Response dictionary
        """
        # Handle health check requests
        if request.get('action') == 'health_check':
            return self._get_health_status()
        
        # Handle other request types
        self.request_count += 1
        return {
            'status': 'success',
            'message': f'Simple PC2 agent processed request #{self.request_count}',
            'timestamp': time.time()
        }
    
    def run(self):
        """Run the agent's main loop."""
        logger.info(f"Starting {self.__class__.__name__} on port {self.port}")
        
        try:
            while self.running:
                try:
                    # Wait for request with timeout
                    if self.socket.poll(1000, zmq.POLLIN):
                        message = self.socket.recv()
                        
                        # Parse message safely
                        try:
                            request = json.loads(message)
                        except json.JSONDecodeError:
                            request = {"error": "Invalid JSON"}
                            
                        logger.info(f"Received request: {request}")
                        
                        # Process the request
                        response = self.process_request(request)
                        
                        # Send the response
                        self.socket.send_json(response)
                    
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    # Send error response if socket is in a valid state
                    try:
                        self.socket.send_json({
                            'status': 'error',
                            'error': str(e)
                        })
                    except zmq.ZMQError:
                        pass
        
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            raise
        finally:
            logger.info("Exiting main loop")
    
    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info(f"Cleaning up {self.__class__.__name__}...")
        self.running = False
        
        # Close socket
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
        
        # Terminate context
        if hasattr(self, 'context') and self.context:
            self.context.term()
        
        # Call parent cleanup
        super().cleanup()


if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = PC2SimpleAgent()
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