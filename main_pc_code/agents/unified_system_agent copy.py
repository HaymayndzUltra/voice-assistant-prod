from src.core.base_agent import BaseAgent
"""
Unified System Agent
Manages system-wide operations, health monitoring, and agent coordination.
"""

import os
import json
import logging
import time
import threading
import zmq
from pathlib import Path
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(Path(__file__).parent.parent, 'logs', 'unified_system_agent.log'))
    ]
)
logger = logging.getLogger("UnifiedSystemAgent")

class UnifiedSystemAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="UnifiedSystemAgent copy")
        """Initialize the Unified System Agent."""
        self.agent_status = {}
        self.agent_ports = {}
        self.health_subscribers = []
        self._load_config()
        
        # Initialize ZMQ
        self.context = zmq.Context()
        self.health_socket = self.context.socket(zmq.PUB)
        self.health_socket.bind("tcp://*:5569")
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitor_agents, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("Unified System Agent initialized")
    
    def _load_config(self):
        """Load system configuration."""
        config_path = os.path.join(Path(__file__).parent.parent, 'config', 'system_config.json')
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Loaded system configuration from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load system configuration: {e}")
            self.config = {"agents": {}}
    
    def register_agent(self, agent_id: str, port: int):
        """Register a new agent with the system."""
        self.agent_ports[agent_id] = port
        self.agent_status[agent_id] = {
            "status": "registered",
            "last_heartbeat": time.time(),
            "port": port
        }
        logger.info(f"Registered agent {agent_id} on port {port}")
    
    def update_agent_status(self, agent_id: str, status: str):
        """Update the status of a registered agent."""
        if agent_id in self.agent_status:
            self.agent_status[agent_id]["status"] = status
            self.agent_status[agent_id]["last_heartbeat"] = time.time()
            logger.info(f"Updated status for agent {agent_id}: {status}")
    
    def _monitor_agents(self):
        """Monitor agent health and send updates."""
        while True:
            try:
                current_time = time.time()
                for agent_id, status in self.agent_status.items():
                    # Check for stale agents
                    if current_time - status["last_heartbeat"] > 30:  # 30 second timeout
                        status["status"] = "stale"
                        logger.warning(f"Agent {agent_id} is stale")
                
                # Broadcast system status
                system_status = {
                    "timestamp": current_time,
                    "agents": self.agent_status,
                    "system_status": "healthy" if all(s["status"] == "healthy" for s in self.agent_status.values()) else "degraded"
                }
                self.health_socket.send_json(system_status)
                
                time.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring thread: {e}")
                time.sleep(1)
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict]:
        """Get the current status of a specific agent."""
        return self.agent_status.get(agent_id)
    
    def get_system_status(self) -> Dict:
        """Get the current status of the entire system."""
        return {
            "timestamp": time.time(),
            "agents": self.agent_status,
            "system_status": "healthy" if all(s["status"] == "healthy" for s in self.agent_status.values()) else "degraded"
        }
    
    def run(self):
        """Run the Unified System Agent server."""
        logger.info("Starting Unified System Agent server...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down Unified System Agent...")
        finally:
            self.context.term()

if __name__ == "__main__":
    agent = UnifiedSystemAgent()
    agent.run() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
