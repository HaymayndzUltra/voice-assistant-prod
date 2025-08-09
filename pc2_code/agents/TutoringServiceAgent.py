import logging
import time
from typing import Dict, Any
import sys
from pathlib import Path
import yaml

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import BaseAgent
from common.core.base_agent import BaseAgent

# Standard imports for PC2 agents


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TutoringServiceAgent(BaseAgent):
    
    def __init__(self):
        # Load configuration from startup_config.yaml
        self._load_config()
        
        # Initialize BaseAgent with name and port
        super().__init__(name="TutoringServiceAgent", port=self.port)
        
        self.name = "TutoringServiceAgent"
        self.start_time = time.time()
        
        # Initialize service state
        self.service_state = {}
        
        logger.info(f"Tutoring Service Agent initialized on {self.host}:{self.port}")
        
    def _load_config(self):
        """Load configuration from startup_config.yaml"""
        try:
            config_path = project_root / "pc2_code" / "config" / "startup_config.yaml"
            with open(config_path, 'r') as file:
                startup_config = yaml.safe_load(file)
            
            # Find TutoringServiceAgent configuration in pc2_services list
            agent_config = None
            for service in startup_config.get('pc2_services', []):
                if service.get('name') == 'TutoringServiceAgent':
                    agent_config = service
                    break
            
            if agent_config:
                self.host = agent_config.get('host', '0.0.0.0')
                self.port = agent_config.get('port', 5604)
                self.health_check_port = agent_config.get('health_check_port', 8108)
                logger.info(f"Loaded configuration for TutoringServiceAgent: {self.host}:{self.port}")
            else:
                logger.warning("TutoringServiceAgent configuration not found in startup_config.yaml. Using default ports.")
                self.host = '0.0.0.0'
                self.port = 5604
                self.health_check_port = 8108
                
        except Exception as e:
            logger.error(f"Error loading configuration: {e}. Using default ports.")
            self.host = '0.0.0.0'
            self.port = 5604
            self.health_check_port = 8108
        
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