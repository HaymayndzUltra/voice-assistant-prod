import os
import zmq
import json
import logging
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
import networkx as nx
from common.core.base_agent import BaseAgent
import psutil
from main_pc_code.utils.config_loader import load_config

# Module-level configuration loading
config = load_config()

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Network Configuration
PC2_IP = "192.168.100.17"  # PC2's IP address
MAIN_PC_IP = "192.168.100.16"  # Main PC's IP address
COGNITIVE_MODEL_PORT = 5600  # Cognitive Model port
REMOTE_CONNECTOR_PORT = 5557  # Remote Connector port on PC2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cognitive_model.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CognitiveModelAgent(BaseAgent):
    """
    Cognitive Model Agent for belief system management and cognitive reasoning. Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:')."""
    
    def __init__(self, port: int = 5641, name: str = None, **kwargs):
        """Initialize the Cognitive Model Agent."""
        # Get name from config with fallback
        agent_name = config.get("name", 'CognitiveModelAgent') if name is None else name
        
        # Call BaseAgent's __init__ first
        super().__init__(name=agent_name, port=port)
        
        self.host = "0.0.0.0"
        self.port = port
        self.running = True
        self.start_time = time.time()
        
        # Health status
        self.health_status = {
            "status": "ok",
            "service": "cognitive_model_agent",
            "port": self.port,
            "beliefs_count": 0,
            "remote_connection": "ok"
        }
        
        # REP socket for handling requests
        self.socket.setsockopt(zmq.ROUTER, 1)
        self.socket.bind(f"tcp://{self.host}:{self.port}")
        
        # Connect to Remote Connector on PC2
        self.remote_socket = self.context.socket(zmq.REQ)
        self.remote_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.remote_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        try:
            self.remote_socket.connect(f"tcp://{PC2_IP}:{REMOTE_CONNECTOR_PORT}")
            logger.info(f"Connected to Remote Connector on {PC2_IP}:{REMOTE_CONNECTOR_PORT}")
            self.health_status["remote_connection"] = "ok"
        except Exception as e:
            logger.warning(f"Could not connect to Remote Connector: {e}")
            self.health_status["remote_connection"] = "error"
            
        # Initialize belief system
        self.belief_system = nx.DiGraph()
        self._initialize_belief_system()
        logger.info(f"Cognitive Model Agent listening on {self.host}:{self.port}")
    
    

        self.error_bus_port = 7150

        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')

        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"

        self.error_bus_pub = self.context.socket(zmq.PUB)

        self.error_bus_pub.connect(self.error_bus_endpoint)
def _initialize_belief_system(self):
        """Initialize the belief system with core beliefs."""
        # Add core beliefs
        core_beliefs = [
            "existence",
            "consciousness",
            "learning",
            "adaptation",
            "purpose"
        ]
        
        for belief in core_beliefs:
            self.belief_system.add_node(belief, type='core_belief')
        
        # Add relationships between core beliefs
        relationships = [
            ("existence", "consciousness", "enables"),
            ("consciousness", "learning", "facilitates"),
            ("learning", "adaptation", "leads_to"),
            ("adaptation", "purpose", "supports"),
            ("purpose", "existence", "gives_meaning")
        ]
        
        for source, target, relation in relationships:
            self.belief_system.add_edge(source, target, relation=relation)
    
    def add_belief(self, belief: str, belief_type: str, relationships: List[Dict[str, str]]) -> Dict[str, Any]:
        """Add a new belief to the system."""
        try:
            # Add the belief node
            self.belief_system.add_node(belief, type=belief_type)
            
            # Add relationships
            for rel in relationships:
                source = rel.get('source')
                target = rel.get('target')
                relation = rel.get('relation')
                
                if source and target and relation:
                    self.belief_system.add_edge(source, target, relation=relation)
            
            # Check consistency
            if not self._check_belief_consistency(belief):
                # Remove the belief if it creates inconsistency
                self.belief_system.remove_node(belief)
                return {
                    'status': 'error',
                    'message': 'Belief creates inconsistency in the system'
                }
            
            return {
                'status': 'success',
                'message': 'Belief added successfully'
            }
            
        except Exception as e:
            logger.error(f"Error adding belief: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _check_belief_consistency(self, belief: str) -> bool:
        """Check if a belief is consistent with the existing system."""
        try:
            # Check for cycles in the belief graph
            if not nx.is_directed_acyclic_graph(self.belief_system):
                return False
            
            # Check for contradictory relationships
            for neighbor in self.belief_system.neighbors(belief):
                edge_data = self.belief_system.get_edge_data(belief, neighbor)
                if edge_data.get('relation') == 'contradicts':
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking belief consistency: {str(e)}")
            return False
    
    def query_belief_consistency(self, belief: str) -> Dict[str, Any]:
        """Query the consistency of a belief with the system."""
        try:
            # Check if belief exists
            if belief not in self.belief_system:
                return {
                    'status': 'error',
                    'message': 'Belief not found in system'
                }
            
            # Get belief details
            belief_data = self.belief_system.nodes[belief]
            
            # Get relationships
            relationships = []
            for neighbor in self.belief_system.neighbors(belief):
                edge_data = self.belief_system.get_edge_data(belief, neighbor)
                relationships.append({
                    'target': neighbor,
                    'relation': edge_data.get('relation')
                })
            
            return {
                'status': 'success',
                'belief': belief,
                'type': belief_data.get('type'),
                'relationships': relationships,
                'is_consistent': self._check_belief_consistency(belief)
            }
            
        except Exception as e:
            logger.error(f"Error querying belief: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_belief_system(self) -> Dict[str, Any]:
        """Get the current state of the belief system."""
        try:
            # Convert graph to dictionary format
            system_data = {
                'nodes': [],
                'edges': []
            }
            
            # Add nodes
            for node, data in self.belief_system.nodes(data=True):
                system_data['nodes'].append({
                    'id': node,
                    'type': data.get('type')
                })
            
            # Add edges
            for source, target, data in self.belief_system.edges(data=True):
                system_data['edges'].append({
                    'source': source,
                    'target': target,
                    'relation': data.get('relation')
                })
            
            return {
                'status': 'success',
                'system': system_data
            }
            
        except Exception as e:
            logger.error(f"Error getting belief system: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action')
        
        if action == 'health_check':
            return {
                'status': 'ok',
                'service': 'cognitive_model_agent',
                'ready': True,
                'initialized': True,
                'message': 'CognitiveModelAgent is healthy',
                'timestamp': datetime.now().isoformat(),
                'uptime': self.health_status['uptime'],
                'beliefs_count': self.health_status['beliefs_count'],
                'remote_connection': self.health_status['remote_connection']
            }
        
        elif action == 'add_belief':
            belief = request.get('belief')
            belief_type = request.get('type')
            relationships = request.get('relationships', [])
            return self.add_belief(belief, belief_type, relationships)
        
        elif action == 'query_belief':
            belief = request.get('belief')
            return self.query_belief_consistency(belief)
        
        elif action == 'get_belief_system':
            return self.get_belief_system()
        
        else:
            return {
                'status': 'error',
                'message': 'Unknown action'
            }
    
    def start(self):
        """Start the agent."""
        logger.info("Starting Cognitive Model Agent")
        while self.running:
            try:
                # Receive and handle requests
                message = self.socket.recv_json()
                response = self.handle_request(message)
                self.socket.send_json(response)
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                # Try to send an error response
                try:
                    self.socket.send_json({
                        'status': 'error',
                        'message': str(e)
                    })
                except:
                    pass
    
    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message and return a response."""
        return self.handle_request(message)
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get health status of the agent."""
        return {
            'status': 'ok',
            'service': 'cognitive_model_agent',
            'beliefs_count': len(self.belief_system.nodes),
            'relationships_count': len(self.belief_system.edges),
            'remote_connection': self.health_status['remote_connection']
        }
    
    def _update_health_status(self):
        """Update health status with current information."""
        self.health_status.update({
            'beliefs_count': len(self.belief_system.nodes),
            'uptime': time.time() - self.start_time
        })
    
    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info("Shutting down Cognitive Model Agent")
        self.running = False
        if hasattr(self, 'remote_socket'):
            self.remote_socket.close()
        # BaseAgent's cleanup will handle the main socket
        super().cleanup()
    
    def health_check(self):
        """Perform a health check on the agent."""
        try:
            is_healthy = self.remote_socket is not None
            
            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {
                    "beliefs_count": len(self.belief_system.nodes),
                    "relationships_count": len(self.belief_system.edges),
                    "remote_connection": self.health_status['remote_connection']
                }
            }
            return status_report
        except Exception as e:
            return {
                "status": "unhealthy",
                "agent_name": self.name,
                "error": f"Health check failed with exception: {str(e)}"
            }

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = CognitiveModelAgent()
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