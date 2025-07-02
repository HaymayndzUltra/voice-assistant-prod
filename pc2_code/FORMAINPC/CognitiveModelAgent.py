import os
import zmq
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import networkx as nx
from pc2_code.config.system_config import get_service_host, get_service_port

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
    def __init__(self):
        """Initialize the Cognitive Model Agent."""
        self.context = zmq.Context()
        
        # Get host and port from environment or config
        self.host = get_service_host('cognitive_model', '0.0.0.0')
        self.port = get_service_port('cognitive_model', 5600)
        
        # REP socket for handling requests
        self.socket = self.context.socket(zmq.ROUTER)
        self.socket.bind(f"tcp://{self.host}:{self.port}")
        
        # Initialize belief system
        self.belief_system = nx.DiGraph()
        self._initialize_belief_system()
        
        logger.info(f"Cognitive Model Agent listening on {self.host}:{self.port}")
    
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
        
        if action == 'add_belief':
            belief = request.get('belief')
            belief_type = request.get('type')
            relationships = request.get('relationships', [])
            return self.add_belief(belief, belief_type, relationships)
            
        elif action == 'query_belief':
            belief = request.get('belief')
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
    agent = CognitiveModelAgent()
    try:
        agent.start()
    except KeyboardInterrupt:
        agent.stop() 