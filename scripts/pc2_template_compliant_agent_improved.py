#!/usr/bin/env python3
"""
Improved PC2 Template Agent
--------------------------
This template demonstrates all the required elements for a fully compliant PC2 agent
using the standardized helper utilities.
"""

import time
import json
import zmq
from typing import Dict, Any, Optional

# Import PC2 agent helper utilities
from pc2_code.agents.utils.pc2_agent_helpers import (
    BaseAgent,           # Base agent class from main_pc_code
    get_pc2_config,      # Standard config loader
    setup_pc2_logging,   # PC2 logging setup
    get_pc2_health_status,  # Standard health status
    setup_zmq_socket,    # ZMQ socket setup
    standard_cleanup     # Standard cleanup procedure
)

# Load configuration at module level
config = get_pc2_config()

# Set up logging for this agent
logger = setup_pc2_logging("PC2ImprovedTemplate")

class PC2ImprovedTemplateAgent(BaseAgent):
    """PC2 template agent with improved structure using helper utilities."""
    
    def __init__(self, port: Optional[int] = None):
        """Initialize the agent.
        
        Args:
            port: The port number to use for ZMQ communication.
        """
        # Call the BaseAgent's __init__ with proper parameters
        super().__init__(name="PC2ImprovedTemplateAgent", port=port)
        
        # Record start time for uptime calculation
        self.start_time = time.time()
        
        # Agent-specific initialization
        self.port = port if port is not None else 5560
        
        # Set up ZMQ socket using standard helper
        self.context, self.socket = setup_zmq_socket(self.port)
        
        # Initialize agent state
        self.running = True
        self.request_count = 0
        self.last_health_check = time.time()
        
        logger.info(f"{self.__class__.__name__} initialized on port {self.port}")
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Return health status information.
        
        Returns:
            Dict containing health status information.
        """
        # Get base status from parent
        base_status = super()._get_health_status()
        
        # Add PC2-specific health information using helper
        status = get_pc2_health_status(self, base_status)
        
        # Add agent-specific information
        status.update({
            'request_count': self.request_count,
            'last_health_check': self.last_health_check
        })
        
        self.last_health_check = time.time()
        return status
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
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
            'message': f'PC2 Improved Template processed request #{self.request_count}',
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
                        # Receive message
                        message = self.socket.recv()
                        
                        # Parse the message safely
                        try:
                            request = json.loads(message)
                        except json.JSONDecodeError:
                            request = {"error": "Invalid JSON"}
                            
                        logger.info(f"Received request: {request}")
                        
                        # Process the request
                        response = self.handle_request(request)
                        
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
        # Use standard cleanup helper
        standard_cleanup(self, logger)


if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = PC2ImprovedTemplateAgent()
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