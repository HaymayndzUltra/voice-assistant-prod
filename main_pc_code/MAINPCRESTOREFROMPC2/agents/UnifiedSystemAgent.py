from src.core.base_agent import BaseAgent
import zmq
import json
import logging
import time
import threading
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('unified_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UnifiedSystemAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="Unifiedsystemagent")
        """Initialize the Unified System Agent."""
        self.context = zmq.Context()
        
        # REP socket for handling requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind("tcp://*:5568")
        
        # Define all known agents and their ports
        self.agents = {
            # Core Agents
            'AutonomousWebAssistant': 5630,
            'EpisodicMemoryAgent': 5631,
            'EnhancedModelRouter': 5632,
            'PerformanceLoggerAgent': 5633,
            'CoordinatorAgent': 5634,
            'EmpathyAgent': 5635,
            
            # Advanced Agents
            'DreamingModeAgent': 5640,
            'CognitiveModelAgent': 5641,
            'DreamWorldAgent': 5642,
            'MultiAgentSwarmManager': 5643,
            'DynamicIdentityAgent': 5644
        }
        
        # Agent status tracking
        self.agent_status = {}
        for agent in self.agents:
            self.agent_status[agent] = {
                'status': 'unknown',
                'last_seen': None,
                'port': self.agents[agent]
            }
        
        # Start health check thread
        self.health_check_thread = threading.Thread(target=self._health_check_loop)
        self.health_check_thread.daemon = True
        self.health_check_thread.start()
        
        logger.info("Unified System Agent initialized")
    
    def _check_agent_health(self, agent: str, port: int) -> bool:
        """Check if an agent is healthy by sending a ping request."""
        try:
            socket = self.context.socket(zmq.REQ)
            socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            socket.connect(f"tcp://localhost:{port}")
            
            socket.send_json({'action': 'ping'})
            response = socket.recv_json()
            
            socket.close()
            return response.get('status') == 'success'
            
        except Exception as e:
            logger.error(f"Error checking health of {agent}: {str(e)}")
            return False
    
    def _health_check_loop(self):
        """Continuously check the health of all agents."""
        while True:
            for agent, port in self.agents.items():
                is_healthy = self._check_agent_health(agent, port)
                
                self.agent_status[agent]['status'] = 'active' if is_healthy else 'inactive'
                self.agent_status[agent]['last_seen'] = datetime.now().isoformat() if is_healthy else None
                
                logger.info(f"Agent {agent} status: {self.agent_status[agent]['status']}")
            
            time.sleep(5)  # Check every 5 seconds
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get the current status of all agents."""
        return {
            'status': 'success',
            'agents': self.agent_status
        }
    
    def get_agent_info(self, agent: str) -> Dict[str, Any]:
        """Get detailed information about a specific agent."""
        if agent not in self.agents:
            return {
                'status': 'error',
                'message': f'Unknown agent: {agent}'
            }
        
        return {
            'status': 'success',
            'agent': {
                'name': agent,
                'port': self.agents[agent],
                'status': self.agent_status[agent]
            }
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action')
        
        if action == 'get_agent_status':
            return self.get_agent_status()
            
        elif action == 'get_agent_info':
            agent = request.get('agent')
            return self.get_agent_info(agent)
            
        else:
            return {
                'status': 'error',
                'message': f'Unknown action: {action}'
            }
    
    def run(self):
        """Run the agent's main loop."""
        logger.info("Unified System Agent started")
        
        while True:
            try:
                # Receive request
                request = self.socket.recv_json()
                
                # Handle request
                response = self.handle_request(request)
                
                # Send response
                self.socket.send_json(response)
                
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                self.socket.send_json({
                    'status': 'error',
                    'message': str(e)
                })
    
    def stop(self):
        """Stop the agent and clean up resources."""
        self.socket.close()
        self.context.term()
        
        logger.info("Unified System Agent stopped")

if __name__ == '__main__':
    agent = UnifiedSystemAgent()
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