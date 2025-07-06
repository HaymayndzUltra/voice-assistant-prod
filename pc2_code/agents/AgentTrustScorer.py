import zmq
import yaml
import sys
import os
import json
import time
import logging
import sqlit

# Add the project's pc2_code directory to the Python path
import sys
import os
from pathlib import Path
PC2_CODE_DIR = Path(__file__).resolve().parent.parent
if PC2_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, PC2_CODE_DIR.as_posix())

e3
from datetime import datetime
from typing import Dict, Any, Optional


from common.core.base_agent import BaseAgent
from pc2_code.agents.utils.config_loader import Config

# Load configuration at the module level
config = Config().get_config()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent_trust_scorer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AgentTrustScorer(BaseAgent):
    def __init__(self, port: int = 5626):
        super().__init__(name="AgentTrustScorer", port=5626)
        # Record start time for uptime calculation
        self.start_time = time.time()
        # Initialize agent state
        self.running = True
        self.request_count = 0
        # Set up connection to main PC if needed
        self.main_pc_connections = {}
        logger.info(f"{self.__class__.__name__} initialized on PC2 (IP: {{'PC2_IP' if 'PC2_IP' in globals() else 'unknown'}}) port {self.port}")
        # Initialize the AgentTrustScorer with ZMQ socket and database.
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{port}")
        # Initialize database
        self.db_path = "agent_trust_scores.db"
        self._init_database()
        logger.info(f"AgentTrustScorer initialized on port {port}")
    
    def _init_database(self):
        """Initialize SQLite database for trust scores."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_scores (
                model_id TEXT PRIMARY KEY,
                trust_score REAL DEFAULT 0.5,
                total_interactions INTEGER DEFAULT 0,
                successful_interactions INTEGER DEFAULT 0,
                last_updated TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id TEXT,
                success BOOLEAN,
                response_time REAL,
                error_message TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES model_scores(model_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _update_trust_score(self, model_id: str, success: bool, response_time: float) -> float:
        """Update trust score based on performance metrics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current score
        cursor.execute(
            "SELECT trust_score, total_interactions, successful_interactions FROM model_scores WHERE model_id = ?",
            (model_id,)
        )
        result = cursor.fetchone()
        
        if result is None:
            # New model
            trust_score = 0.5
            total_interactions = 1
            successful_interactions = 1 if success else 0
        else:
            trust_score, total_interactions, successful_interactions = result
            total_interactions += 1
            if success:
                successful_interactions += 1
        
        # Calculate new trust score
        base_score = successful_interactions / total_interactions
        
        # Adjust for response time (faster is better)
        time_factor = max(0, 1 - (response_time / 5.0))  # 5 seconds as max threshold
        
        # Combine factors
        new_trust_score = (base_score * 0.7) + (time_factor * 0.3)
        
        # Update database
        cursor.execute('''
            INSERT OR REPLACE INTO model_scores 
            (model_id, trust_score, total_interactions, successful_interactions, last_updated)
            VALUES (?, ?, ?, ?, ?)
        ''', (model_id, new_trust_score, total_interactions, successful_interactions, datetime.now()))
        
        # Log performance
        cursor.execute('''
            INSERT INTO performance_logs 
            (model_id, success, response_time, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (model_id, success, response_time, datetime.now()))
        
        conn.commit()
        conn.close()
        
        return new_trust_score
    
    def _get_trust_score(self, model_id: str) -> float:
        """Get current trust score for a model."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT trust_score FROM model_scores WHERE model_id = ?",
            (model_id,)
        )
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else 0.5  # Default score for new models
    
    def _get_performance_history(self, model_id: str, limit: int = 10) -> list:
        """Get recent performance history for a model."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT success, response_time, timestamp 
            FROM performance_logs 
            WHERE model_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (model_id, limit))
        
        history = cursor.fetchall()
        conn.close()
        
        return [
            {
                'success': bool(success),
                'response_time': response_time,
                'timestamp': timestamp
            }
            for success, response_time, timestamp in history
        ]
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action')
        
        if action == 'log_performance':
            model_id = request['model_id']
            success = request['success']
            response_time = request.get('response_time', 0.0)
            error_message = request.get('error_message', '')
            
            new_score = self._update_trust_score(model_id, success, response_time)
            
            return {
                'status': 'success',
                'new_trust_score': new_score
            }
            
        elif action == 'get_trust_score':
            model_id = request['model_id']
            score = self._get_trust_score(model_id)
            
            return {
                'status': 'success',
                'trust_score': score
            }
            
        elif action == 'get_performance_history':
            model_id = request['model_id']
            limit = request.get('limit', 10)
            history = self._get_performance_history(model_id, limit)
            
            return {
                'status': 'success',
                'history': history
            }
            
        else:
            return {
                'status': 'error',
                'message': f'Unknown action: {action}'
            }


    def _get_health_status(self) -> dict:

        """Return health status information."""

        base_status = super()._get_health_status()

        # Add any additional health information specific to AgentTrustScorer

        base_status.update({

            'service': 'AgentTrustScorer',

            'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,

            'additional_info': {}

        })

        return base_status


    def cleanup(self):

        """Clean up resources before shutdown."""

        logger.info("Cleaning up resources...")

        # Add specific cleanup code here

        super().cleanup()
    
    def run(self):
        """Main loop for handling requests."""
        logger.info("AgentTrustScorer started")
        
        while True:
            try:
                # Wait for next request
                message = self.socket.recv_json()
                logger.debug(f"Received request: {message}")
                
                # Process request
                response = self.handle_request(message)
                
                # Send response
                self.socket.send_json(response)
                logger.info(f"Sent response: {response}")
                
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                self.socket.send_json({
                    'status': 'error',
                    'message': str(e)
                })







if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = AgentTrustScorer()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'} on PC2...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'} on PC2: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name} on PC2...")
            agent.cleanup()

# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "network_config.yaml")
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": "192.168.100.16",
            "pc2_ip": "192.168.100.17",
            "bind_address": "0.0.0.0",
            "secure_zmq": False
        }

# Load both configurations
network_config = load_network_config()

# Get machine IPs from config
MAIN_PC_IP = network_config.get("main_pc_ip", "192.168.100.16")
PC2_IP = network_config.get("pc2_ip", "192.168.100.17")
BIND_ADDRESS = network_config.get("bind_address", "0.0.0.0")
