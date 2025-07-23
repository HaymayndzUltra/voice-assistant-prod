#!/usr/bin/env python3
"""
Template for Compliant PC2 Agent
--------------------------------
This template demonstrates all the required elements for a fully compliant agent:
1. BaseAgent inheritance
2. Proper super().__init__ call
3. _get_health_status implementation
4. Standard config_loader usage
5. Standardized __main__ block
"""

import time
import logging
import threading
import zmq
import json
from typing import Dict, Any, Optional, Union

# Import the BaseAgent from main_pc_code (shared)
from main_pc_code.src.core.base_agent import BaseAgent

# Import Config class for PC2
from pc2_code.agents.utils.config_loader import Config

# Load configuration at module level
config = Config().get_config()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TemplateAgent(BaseAgent):
    """Template agent that demonstrates compliance with architectural standards."""
    
    def __init__(self, port: Optional[int] = None):
        """Initialize the agent.
        
        Args:
            port: The port number to use for ZMQ communication.
        """
        # Call the BaseAgent's __init__ with proper parameters
        super().__init__(name="TemplateAgent", port=port)
        
        # Record start time for uptime calculation
        self.start_time = time.time()
        
        # Agent-specific initialization
        self.port = port if port is not None else 5000
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
        base_status = super()._get_health_status()
        
        # Add agent-specific health information
        base_status.update({
            'service': self.__class__.__name__,
            'uptime': time.time() - self.start_time,
            'request_count': self.request_count,
            'additional_info': {}
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
            'message': f'Processed request #{self.request_count}',
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
                        # Parse the message safely
                        try:
                            request = json.loads(message)
                        except json.JSONDecodeError:
                            request = {"error": "Invalid JSON"}
                            
                        logger.info(f"Received request: {request}")
                        
                        # Process the request
                        response = self.process_request(request)
                        
                        # Send the response
                        self.socket.send_json(response)
                    
                    # Periodic tasks
                    # (Add any periodic tasks here)
                    
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
        
        # Close sockets
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
        
        # Terminate context
        if hasattr(self, 'context') and self.context:
            self.context.term()
        
        super().cleanup()


if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = TemplateAgent()
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