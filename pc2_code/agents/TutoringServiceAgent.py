import os
import zmq
import json
import logging
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import BaseAgent
from common.core.base_agent import BaseAgent

# Import config loader
from pc2_code.agents.utils.config_loader import Config

# Standard imports for PC2 agents
from pc2_code.utils.config_loader import load_config, parse_agent_args
from pc2_code.agents.error_bus_template import setup_error_reporting, report_error


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration at the module level
try:
    config = Config().get_config()
except Exception as e:
    logger.error(f"Failed to load config: {e}")
    config = {}

class TutoringServiceAgent(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()
    
    def __init__(self):
        # Get host and port from config
        self.host = config.get('services', {}).get('tutoring_service', {}).get('host', '0.0.0.0')
        self.port = config.get('services', {}).get('tutoring_service', {}).get('port', 5604)
        
        # Initialize BaseAgent with name and port
        super().__init__(name="TutoringServiceAgent", port=self.port)
        
        self.name = "TutoringServiceAgent"
        self.start_time = time.time()
        
        # Initialize service state
        self.service_state = {}
        
        logger.info(f"Tutoring Service Agent initialized on {self.host}:{self.port}")
        
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        # Call parent implementation
        status = super()._get_health_status()
        
        # Add agent-specific health information
        status.update({
            "agent_type": "tutoring_service",
            "service_state": len(self.service_state)
        })
        
        return status
        
    def handle_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        # Handle health check requests
        if message.get('action') in ["health_check", "health", "ping"]:
            return self._get_health_status()
            
        # Process message and return response
        return {"status": "success", "message": "Tutoring service updated"}
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up Tutoring Service Agent resources")
        self.running = False
        
        # Call parent cleanup
        super().cleanup()
        
        logger.info("Tutoring Service Agent cleanup complete")
    
    def stop(self):
        """Stop the agent."""
        self.running = False
            
if __name__ == "__main__":
    agent = TutoringServiceAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop() 