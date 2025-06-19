import os
import zmq
import json
import logging
import time
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional
import networkx as nx

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

class CognitiveModelAgent:
    def __init__(self, port: int = 5641):
        """Initialize the Cognitive Model Agent."""
        self.context = zmq.Context()
        
        # Get host and port from environment or config
        self.host = "0.0.0.0"  # Listen on all interfaces
        self.port = port
        
        # Health status
        self.health_status = {
            "status": "ok",
            "service": "cognitive_model_agent",
            "port": self.port,
            "start_time": time.time(),
            "last_check": time.time(),
            "beliefs_count": 0,
            "remote_connection": "ok"
        }
        
        # REP socket for handling requests
        self.socket = self.context.socket(zmq.ROUTER)
        self.socket.bind(f"tcp://{self.host}:{self.port}")
        
        # Connect to Remote Connector on PC2
        self.remote_socket = self.context.socket(zmq.REQ)
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
    
    def _update_health_status(self):
        """Update health status with current information."""
        try:
            # Update beliefs count
            beliefs_count = len(self.belief_system.nodes)
            self.health_status.update({
                "last_check": time.time(),
                "beliefs_count": beliefs_count,
                "uptime": time.time() - self.health_status["start_time"]
            })
        except Exception as e:
            logger.error(f"Error updating health status: {e}")

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
        
        # Update health status
        self._update_health_status()
        
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
            
            if not belief or not belief_type:
                return {
                    'status': 'error',
                    'message': 'Missing required parameters: belief and type'
                }
            
            return self.add_belief(belief, belief_type, relationships)
            
        elif action == 'query_belief':
            belief = request.get('belief')
            
            if not belief:
                return {
                    'status': 'error',
                    'message': 'Missing required parameter: belief'
                }
            
            return self.query_belief_consistency(belief)
            
        elif action == 'get_system':
            return self.get_belief_system()
            
        else:
            return {
                'status': 'error',
                'message': f'Unknown action: {action}'
            }
    
    def start(self):
        """Run the agent's main loop."""
        logger.info("Cognitive Model Agent started")
        
        try:
            while True:
                # Receive message
                identity, _, message = self.socket.recv_multipart()
                message = json.loads(message.decode())
                
                # Process message
                response = self.process_message(message)
                
                # Send response
                self.socket.send_multipart([
                    identity,
                    b'',
                    json.dumps(response).encode()
                ])
                
        except KeyboardInterrupt:
            logger.info("Shutting down Cognitive Model Agent...")
        finally:
            self.socket.close()
            self.context.term()
            
    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        # Process message and return response
        return self.handle_request(message)
    
    def stop(self):
        """Stop the agent and clean up resources."""
        self.socket.close()
        self.context.term()
        
        logger.info("Cognitive Model Agent stopped")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Cognitive Model Agent')
    parser.add_argument('--port', type=int, default=5641, help='Port to listen on')
    args = parser.parse_args()

    agent = CognitiveModelAgent(args.port)
    try:
        agent.start()
    except KeyboardInterrupt:
        agent.stop() 