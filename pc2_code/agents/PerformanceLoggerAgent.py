import zmq
from typing import Dict, Any, Optional
import yaml
import os
import json
import logging
import sqlite3
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from threading import Thread, Lock
import threading

# Add project root to Python path for common_utils import
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import common utilities if available
try:
    from common_utils.zmq_helper import create_socket
    USE_COMMON_UTILS 
from main_pc_code.src.core.base_agent import BaseAgent
from pc2_code.agents.utils.config_loader import Config

# Load configuration at the module level
config = Config().get_config()
except ImportError:
    USE_COMMON_UTILS = False



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('performance_logger.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PerformanceLoggerAgent(BaseAgent):

    def __init__(self, port: int = None):

        super().__init__(name="PerformanceLoggerAgent", port=port)

        self.start_time = time.time()

    def __init__(self, port:

        self.name = "PerformanceLoggerAgent"
        self.running = True
        self.start_time = time.time()
        self.health_port = self.port + 1
 int = 5632):
        """Initialize the PerformanceLoggerAgent with ZMQ sockets and database."""
        self.port = port
        self.context = zmq.Context()
        
        
        # Start health check thread
        self._start_health_check()

        # Main REP socket for handling requests
        self.socket = self.context.socket(zmq.REP)

        # Initialize health check socket
        try:
            if USE_COMMON_UTILS:
                self.health_socket = create_socket(self.context, zmq.REP, server=True)
            else:
                self.health_socket = self.context.socket(zmq.REP)
                self.health_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            self.health_socket.bind(f"tcp://0.0.0.0:{self.health_port}")
            logging.info(f"Health check socket bound to port {self.health_port}")
        except zmq.error.ZMQError as e:
            logging.error(f"Failed to bind health check socket: {e}")
            raise
        self.socket.bind(f"tcp://*:{port}")
        
        # Lock for thread-safe database access
        self.db_lock = Lock()
        
        # Initialize database
        self.db_path = "performance_metrics.db"
        self._init_database()
        
        # Start cleanup thread
        self.running = True
        self.cleanup_thread = Thread(target=self._cleanup_old_metrics)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        
        logger.info(f"PerformanceLoggerAgent initialized on port {port}")
    
    def _start_health_check(self):
        """Start health check thread."""
        self.health_thread = threading.Thread(target=self._health_check_loop)
        self.health_thread.daemon = True
        self.health_thread.start()
        logging.info("Health check thread started")
    
    def _health_check_loop(self):
        """Background loop to handle health check requests."""
        logging.info("Health check loop started")
        
        while self.running:
            try:
                # Check for health check requests with timeout
                if self.health_socket.poll(100, zmq.POLLIN):
                    # Receive request (don't care about content)
                    _ = self.health_socket.recv()
                    
                    # Get health data
                    health_data = self._get_health_status()
                    
                    # Send response
                    self.health_socket.send_json(health_data)
                    
                time.sleep(0.1)  # Small sleep to prevent CPU hogging
                
            except Exception as e:
                logging.error(f"Error in health check loop: {e}")
                time.sleep(1)  # Sleep longer on error
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        uptime = time.time() - self.start_time
        
        return {
            "agent": self.name,
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "uptime": uptime
        }

    def _init_database(self):
        """Initialize SQLite database for performance metrics."""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent TEXT,
                    action TEXT,
                    duration REAL,
                    timestamp TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Create resource usage table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS resource_usage (
                    usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent TEXT,
                    cpu_percent REAL,
                    memory_mb REAL,
                    timestamp TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_agent ON metrics(agent)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_resource_agent ON resource_usage(agent)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_resource_timestamp ON resource_usage(timestamp)')
            
            conn.commit()
            conn.close()
    
    def _cleanup_old_metrics(self):
        """Periodically clean up old metrics data."""
        while self.running:
            try:
                with self.db_lock:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    
                    # Delete metrics older than 30 days
                    cursor.execute('''
                        DELETE FROM metrics 
                        WHERE timestamp < datetime('now', '-30 days')
                    ''')
                    
                    # Delete resource usage data older than 7 days
                    cursor.execute('''
                        DELETE FROM resource_usage 
                        WHERE timestamp < datetime('now', '-7 days')
                    ''')
                    
                    conn.commit()
                    conn.close()
                
                # Wait 24 hours before next cleanup
                time.sleep(86400)
                
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
                time.sleep(3600)  # Wait 1 hour before retrying
    
    def _log_metric(self, metric: Dict[str, Any]):
        """Log a performance metric to the database."""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO metrics 
                (agent, action, duration, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                metric['agent'],
                metric['action'],
                metric['duration'],
                metric['timestamp'],
                json.dumps(metric['metadata'])
            ))
            
            conn.commit()
            conn.close()
    
    def _log_resource_usage(self, usage: Dict[str, Any]):
        """Log resource usage data to the database."""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO resource_usage 
                (agent, cpu_percent, memory_mb, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                usage['agent'],
                usage['cpu_percent'],
                usage['memory_mb'],
                usage['timestamp'],
                json.dumps(usage['metadata'])
            ))
            
            conn.commit()
            conn.close()
    
    def _get_agent_metrics(self, agent: str, start_time: str, end_time: str) -> List[Dict[str, Any]]:
        """Get performance metrics for a specific agent within a time range."""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT action, duration, timestamp, metadata
                FROM metrics
                WHERE agent = ? AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            ''', (agent, start_time, end_time))
            
            metrics = []
            for row in cursor.fetchall():
                metrics.append({
                    'action': row[0],
                    'duration': row[1],
                    'timestamp': row[2],
                    'metadata': json.loads(row[3])
                })
            
            conn.close()
            return metrics
    
    def _get_agent_resource_usage(self, agent: str, start_time: str, end_time: str) -> List[Dict[str, Any]]:
        """Get resource usage data for a specific agent within a time range."""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT cpu_percent, memory_mb, timestamp, metadata
                FROM resource_usage
                WHERE agent = ? AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            ''', (agent, start_time, end_time))
            
            usage = []
            for row in cursor.fetchall():
                usage.append({
                    'cpu_percent': row[0],
                    'memory_mb': row[1],
                    'timestamp': row[2],
                    'metadata': json.loads(row[3])
                })
            
            conn.close()
            return usage
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action')
        
        if action == 'log_metric':
            metric = request['metric']
            self._log_metric(metric)
            
            return {
                'status': 'success'
            }
            
        elif action == 'log_resource_usage':
            usage = request['usage']
            self._log_resource_usage(usage)
            
            return {
                'status': 'success'
            }
            
        elif action == 'get_agent_metrics':
            agent = request['agent']
            start_time = request['start_time']
            end_time = request['end_time']
            
            metrics = self._get_agent_metrics(agent, start_time, end_time)
            
            return {
                'status': 'success',
                'metrics': metrics
            }
            
        elif action == 'get_agent_resource_usage':
            agent = request['agent']
            start_time = request['start_time']
            end_time = request['end_time']
            
            usage = self._get_agent_resource_usage(agent, start_time, end_time)
            
            return {
                'status': 'success',
                'usage': usage
            }
            
        else:
            return {
                'status': 'error',
                'message': f'Unknown action: {action}'
            }
    
    def run(self):
        """Main loop for handling requests."""
        logger.info("PerformanceLoggerAgent started")
        
        while True:
            try:
                # Wait for next request
                message = self.socket.recv_json()
                logger.debug(f"Received request: {message}")
                
                # Process request
                response = self.handle_request(message)
                
                # Send response
                self.socket.send_json(response)
                logger.debug(f"Sent response: {response}")
                
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                self.socket.send_json({
                    'status': 'error',
                    'message': str(e)
                })



    def cleanup(self):


        """Clean up resources before shutdown."""


        logger.info("Cleaning up resources...")


        # Add specific cleanup code here


        super().cleanup()
    
    def stop(self):
        """Stop the agent and clean up resources."""
        self.running = False
        self.cleanup_thread.join()
        
        self.socket.close()
        self.context.term()







if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = PerformanceLoggerAgent()
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
print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()



    def connect_to_main_pc_service(self, service_name: str):


        """


        Connect to a service on the main PC using the network configuration.


        


        Args:


            service_name: Name of the service in the network config ports section


        


        Returns:


            ZMQ socket connected to the service


        """


        if not hasattr(self, 'main_pc_connections'):


            self.main_pc_connections = {}


            


        if service_name not in network_config.get("ports", {}):


            logger.error(f"Service {service_name} not found in network configuration")


            return None


            


        port = network_config["ports"][service_name]


        


        # Create a new socket for this connection


        socket = self.context.socket(zmq.REQ)


        


        # Connect to the service


        socket.connect(f"tcp://{MAIN_PC_IP}:{port}")


        


        # Store the connection


        self.main_pc_connections[service_name] = socket


        


        logger.info(f"Connected to {service_name} on MainPC at {MAIN_PC_IP}:{port}")


        return socket
