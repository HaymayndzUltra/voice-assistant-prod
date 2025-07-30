import zmq
import yaml
import sys
import os
import json
import time
import logging
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from common.config_manager import get_service_ip, get_service_url, get_redis_url


# Import path manager for containerization-friendly paths
import sys
import os
from common.utils.path_manager import PathManager
sys.path.insert(0, str(PathManager.get_project_root()))
# Add the project's pc2_code directory to the Python path
PC2_CODE_DIR = PathManager.get_project_root()
if str(PC2_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(PC2_CODE_DIR))

# Import required modules
from common.core.base_agent import BaseAgent
from pc2_code.agents.utils.config_loader import Config

# Load configuration at the module level
config = Config().get_config()

# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = Path(PathManager.get_project_root()) / "config" / "network_config.yaml"
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": get_mainpc_ip(),
            "pc2_ip": get_pc2_ip()),
            "bind_address": os.environ.get("BIND_ADDRESS", "0.0.0.0"),
            "secure_zmq": False,
            "ports": {
                "agent_trust_scorer": int(os.environ.get("AGENT_TRUST_SCORER_PORT", 5626)),
                "error_bus": int(os.environ.get("ERROR_BUS_PORT", 7150))
            }
        }

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load network configuration
network_config = load_network_config()

# Get configuration values
MAIN_PC_IP = get_mainpc_ip())
PC2_IP = network_config.get("pc2_ip", get_pc2_ip()))
BIND_ADDRESS = network_config.get("bind_address", os.environ.get("BIND_ADDRESS", "0.0.0.0"))
AGENT_TRUST_SCORER_PORT = network_config.get("ports", {}).get("agent_trust_scorer", int(os.environ.get("AGENT_TRUST_SCORER_PORT", 5626)))
ERROR_BUS_PORT = network_config.get("ports", {}).get("error_bus", int(os.environ.get("ERROR_BUS_PORT", 7150)))

class AgentTrustScorer(BaseAgent):
    """
    AgentTrustScorer: Tracks and scores the reliability of AI models based on performance metrics.
    """
    def __init__(self, port: int = None):
        # Initialize state before BaseAgent
        self.running = True
        self.request_count = 0
        self.main_pc_connections = {}
        self.start_time = time.time()
        
        # Initialize BaseAgent with proper parameters
        super().__init__(
            name="AgentTrustScorer", 
            port=port if port is not None else AGENT_TRUST_SCORER_PORT
        )
        
        # Initialize database
        self.db_path = PathManager.get_project_root() / "cache" / str(PathManager.get_data_dir() / "agent_trust_scores.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_database()
        
        # ✅ Using BaseAgent's built-in error reporting (UnifiedErrorHandler)
        
        logger.info(f"AgentTrustScorer initialized on port {self.port}")
    
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
    
        # PC2 Error Bus Integration (Phase 1.3)
        self.error_publisher = create_pc2_error_publisher("AgentTrustScorer")
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
            
        elif action == 'health_check':
            return self._get_health_status()
            
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
            'status': 'ok',
            'service': 'AgentTrustScorer',
            'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,
            'additional_info': {}
        })

        return base_status

    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info("Cleaning up resources...")
        
        # Close all connections
        if hasattr(self, 'socket'):
            try:
                self.socket.close()
                logger.info("Closed main socket")
            except Exception as e:
                logger.error(f"Error closing main socket: {e}")
        
        # ✅ BaseAgent handles error bus cleanup automatically
        
        # Close any connections to other services
        for service_name, socket in self.main_pc_connections.items():
            try:
                socket.close()
                logger.info(f"Closed connection to {service_name}")
            except Exception as e:
                logger.error(f"Error closing connection to {service_name}: {e}")
        
        # Call parent cleanup
        try:
            super().cleanup()
            logger.info("Called parent cleanup")
        except Exception as e:
            logger.error(f"Error in parent cleanup: {e}")
        
        logger.info("Cleanup complete")
    
    def run(self):
        """Main loop for handling requests."""
        logger.info("AgentTrustScorer started")
        
        while self.running:
            try:
                # Wait for next request with timeout
                if self.socket.poll(timeout=1000) != 0:  # 1 second timeout
                    message = self.socket.recv_json()
                    logger.debug(f"Received request: {message}")
                    
                    # Process request
                    response = self.handle_request(message)
                    
                    # Send response
                    self.socket.send_json(response)
                    logger.info(f"Sent response: {response}")
                    self.request_count += 1
                    
            except zmq.error.ZMQError as e:
                logger.error(f"ZMQ error: {e}")
                self.report_error("ZMQ_ERROR", str(e))
                try:
                    self.socket.send_json({
                        'status': 'error',
                        'message': str(e)
                    })
                except:
                    pass
                time.sleep(1)  # Avoid tight loop on error
                
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                self.report_error("PROCESSING_ERROR", str(e))
                try:
                    self.socket.send_json({
                        'status': 'error',
                        'message': str(e)
                    })
                except:
                    pass
                time.sleep(1)  # Avoid tight loop on error

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

# Standardized environment variables (Blueprint.md Step 4)
from common.utils.env_standardizer import get_mainpc_ip, get_pc2_ip, get_current_machine, get_env
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'} on PC2: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name} on PC2...")
            agent.cleanup()
