"""
from common.config_manager import get_service_ip, get_service_url, get_redis_url
Self Training Orchestrator
Purpose: Manages training cycles and resource allocation for PC2 agents
Features: Cycle management, progress tracking, resource allocation
"""

import zmq
import json
import logging
import sqlite3
import threading
import time
import argparse
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum
from queue import PriorityQueue
from common.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root())
from common.utils.path_env import get_path, join_path, get_file_path
# Load configuration at the module level
config = load_config()

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=join_path("logs", "self_training.log")
)
logger = logging.getLogger(__name__)

class TrainingStatus(Enum):
    """
    TrainingStatus:  Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class ResourceType(Enum):
    CPU = "cpu"
    GPU = "gpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"

@dataclass
class TrainingCycle:
    id: str
    agent_id: str
    config: Dict
    status: TrainingStatus
    priority: int
    resources: Dict[ResourceType, float]
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    progress: float = 0.0
    error: Optional[str] = None

class SelfTrainingOrchestrator(BaseAgent):
    """Orchestrator for managing AI agent self-training cycles"""
    
    def __init__(self, config=None, **kwargs):
        """Initialize the Self Training Orchestrator."""
        # Ensure config is a dictionary
        config = config or {}
        
        # Get name and port from config or environment
        agent_name = kwargs.get('name', os.environ.get("AGENT_NAME", "SelfTrainingOrchestrator"))
        agent_port = int(kwargs.get('port', os.environ.get("AGENT_PORT", config.get("port", 5644))))
        health_port = int(os.environ.get("HEALTH_CHECK_PORT", str(agent_port + 1)))
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=agent_name, port=agent_port)
        
        # Project root setup
        self.project_root = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.abspath(__file__)))
        if self.project_root not in sys.path:
            sys.path.insert(0, self.project_root)
        
        self.port = agent_port
        self.health_port = health_port
        self.name = agent_name
        self.running = True
        self.start_time = time.time()
        
        # Database setup
        self.db_path = join_path("data", "self_training.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Training cycle management
        self.active_cycles = {}
        self.cycle_queue = PriorityQueue()
        self.resource_limits = {
            ResourceType.CPU: 100.0,  # CPU percentage
            ResourceType.GPU: 100.0,  # GPU percentage
            ResourceType.MEMORY: 16.0,  # GB
            ResourceType.STORAGE: 100.0,  # GB
            ResourceType.NETWORK: 1000.0  # Mbps
        }
        self.available_resources = self.resource_limits.copy()
        
        # Thread management
        self.cycle_thread = None
        self.context = None
        self.socket = None
        self.health_socket = None
        
        # Setup ZMQ
        self.setup_zmq()
        
        # Initialize the database
        self._init_db()
        
        # Start health check thread
        self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_thread.start()
        
        logger.info(f"{self.name} initialized on port {self.port} (health: {self.health_port})")

    

        self.error_bus_port = 7150

        self.error_bus_host = get_service_ip("pc2")

        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"

        self.context = zmq.Context()
        self.error_bus_pub = self.context.socket(zmq.PUB)

        self.error_bus_pub.connect(self.error_bus_endpoint)

    def setup_zmq(self):
        """Set up ZMQ sockets with proper error handling"""
        try:
            
            # Main socket
            self.socket = self.context.socket(zmq.REP)
            self.socket.setsockopt(zmq.LINGER, 0)
            self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            
            # Health socket
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.setsockopt(zmq.LINGER, 0)
            self.health_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            
            # Bind sockets with retry logic
            self._bind_socket_with_retry(self.socket, self.port)
            self._bind_socket_with_retry(self.health_socket, self.health_port)
            
            logger.info(f"Successfully set up ZMQ sockets on ports {self.port} and {self.health_port}")
            return True
        except Exception as e:
            logger.error(f"Error setting up ZMQ: {e}")
            self.cleanup()
            return False
    
    def _bind_socket_with_retry(self, socket, port, max_retries=5):
        """Bind a socket with retry logic"""
        retries = 0
        while retries < max_retries:
            try:
                socket.bind(f"tcp://*:{port}")
                logger.info(f"Successfully bound to port {port}")
                return True
            except zmq.error.ZMQError as e:
                retries += 1
                logger.warning(f"Failed to bind to port {port} (attempt {retries}/{max_retries}): {e}")
                if retries >= max_retries:
                    logger.error(f"Failed to bind to port {port} after {max_retries} attempts")
                    raise
                time.sleep(1)  # Wait before retrying
        return False

    def _health_check_loop(self):
        """Health check loop with proper error handling"""
        logger.info("Starting health check loop")
        
        while self.running:
            try:
                # Check for health check requests with timeout
                if self.health_socket.poll(100) != 0:
                    # Receive request (don't care about content)
                    message = self.health_socket.recv()
                    logger.debug(f"Received health check request: {message}")
                    
                    # Send response
                    response = self._get_health_status()
                    self.health_socket.send_json(response)
                    logger.debug("Sent health check response")
            except zmq.error.Again:
                # Timeout on receive, this is normal
                pass
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
            
            time.sleep(0.1)
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        return {
            'status': 'ok',
            'name': self.name,
            'uptime': time.time() - self.start_time,
            'service': 'self_training_orchestrator',
            'port': self.port,
            'active_cycles': len(self.active_cycles),
            'database_status': 'ok'
        }

    def _init_db(self):
        """Initialize the SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Create tables
            c.execute('''
                CREATE TABLE IF NOT EXISTS training_cycles (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    config TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    resources TEXT NOT NULL,
                    start_time DATETIME,
                    end_time DATETIME,
                    progress REAL DEFAULT 0.0,
                    error TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS resource_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_id TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    usage REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cycle_id) REFERENCES training_cycles (id)
                )
            ''')
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS cycle_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cycle_id) REFERENCES training_cycles (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            # self.health_status["database_status"] = "ok" # This line was removed as per new_code
            logger.info("Database initialized successfully")
        except Exception as e:
            # self.health_status["database_status"] = "error" # This line was removed as per new_code
            logger.error(f"Database initialization error: {e}")

    def create_training_cycle(self, agent_id: str, config: Dict, priority: int = 1) -> Dict:
        """Create a new training cycle."""
        try:
            cycle_id = f"cycle_{int(time.time())}_{agent_id}"
            
            # Validate resource requirements
            required_resources = self._validate_resources(config.get("resources", {}))
            if not required_resources:
                return {
                    "status": "error",
                    "message": "Invalid resource requirements"
                }
            
            # Create cycle
            cycle = TrainingCycle(
                id=cycle_id,
                agent_id=agent_id,
                config=config,
                status=TrainingStatus.PENDING,
                priority=priority,
                resources=required_resources
            )
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''
                INSERT INTO training_cycles 
                (id, agent_id, config, status, priority, resources)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                cycle.id,
                cycle.agent_id,
                json.dumps(cycle.config),
                cycle.status.value,
                cycle.priority,
                json.dumps({k.value: v for k, v in cycle.resources.items()})
            ))
            
            conn.commit()
            conn.close()
            
            # Add to queue
            self.cycle_queue.put((-priority, cycle))
            
            logger.info(f"Created training cycle: {cycle_id}")
            return {
                "status": "success",
                "cycle_id": cycle_id
            }
            
        except Exception as e:
            logger.error(f"Error creating training cycle: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def _validate_resources(self, resources: Dict) -> Optional[Dict[ResourceType, float]]:
        """Validate and convert resource requirements."""
        try:
            validated = {}
            for resource_type, value in resources.items():
                try:
                    rt = ResourceType(resource_type)
                    if value <= 0 or value > self.resource_limits[rt]:
                        return None
                    validated[rt] = float(value)
                except ValueError:
                    return None
            return validated
        except Exception:
            return None

    def start_training_cycle(self, cycle_id: str) -> Dict:
        """Start a training cycle."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Get cycle
            c.execute('SELECT * FROM training_cycles WHERE id = ?', (cycle_id,))
            cycle_data = c.fetchone()
            
            if not cycle_data:
                return {
                    "status": "error",
                    "message": "Cycle not found"
                }
            
            # Check if resources are available
            resources = json.loads(cycle_data[5])
            if not self._check_resource_availability(resources):
                return {
                    "status": "error",
                    "message": "Insufficient resources"
                }
            
            # Update status
            c.execute('''
                UPDATE training_cycles 
                SET status = ?, start_time = ? 
                WHERE id = ?
            ''', (TrainingStatus.RUNNING.value, datetime.now(), cycle_id))
            
            conn.commit()
            conn.close()
            
            # Allocate resources
            self._allocate_resources(resources)
            
            # Start cycle thread
            cycle = self._create_cycle_from_db(cycle_data)
            self.active_cycles[cycle_id] = cycle
            
            if not self.cycle_thread or not self.cycle_thread.is_alive():
                self.cycle_thread = threading.Thread(target=self._run_cycle_manager)
                self.cycle_thread.start()
            
            logger.info(f"Started training cycle: {cycle_id}")
            return {
                "status": "success",
                "message": "Cycle started"
            }
            
        except Exception as e:
            logger.error(f"Error starting training cycle: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def _check_resource_availability(self, resources: Dict) -> bool:
        """Check if required resources are available."""
        try:
            for resource_type, value in resources.items():
                rt = ResourceType(resource_type)
                if self.available_resources[rt] < value:
                    return False
            return True
        except Exception:
            return False

    def _allocate_resources(self, resources: Dict):
        """Allocate resources for a cycle."""
        for resource_type, value in resources.items():
            rt = ResourceType(resource_type)
            self.available_resources[rt] -= value

    def _release_resources(self, resources: Dict):
        """Release resources after cycle completion."""
        for resource_type, value in resources.items():
            rt = ResourceType(resource_type)
            self.available_resources[rt] += value

    def _create_cycle_from_db(self, cycle_data) -> TrainingCycle:
        """Create a TrainingCycle object from database row."""
        return TrainingCycle(
            id=cycle_data[0],
            agent_id=cycle_data[1],
            config=json.loads(cycle_data[2]),
            status=TrainingStatus(cycle_data[3]),
            priority=cycle_data[4],
            resources={ResourceType(k): v for k, v in json.loads(cycle_data[5]).items()},
            start_time=datetime.fromisoformat(cycle_data[6]) if cycle_data[6] else None,
            end_time=datetime.fromisoformat(cycle_data[7]) if cycle_data[7] else None,
            progress=cycle_data[8],
            error=cycle_data[9]
        )

    def _run_cycle_manager(self):
        """Run the cycle management thread."""
        self.running = True
        
        while self.running:
            try:
                # Process active cycles
                for cycle_id, cycle in list(self.active_cycles.items()):
                    if cycle.status == TrainingStatus.RUNNING:
                        # Update progress
                        progress = self._update_cycle_progress(cycle)
                        
                        # Check for completion
                        if progress >= 1.0:
                            self._complete_cycle(cycle_id)
                    
                    elif cycle.status == TrainingStatus.FAILED:
                        self._cleanup_cycle(cycle_id)
                
                # Start new cycles if resources available
                while not self.cycle_queue.empty():
                    priority, cycle = self.cycle_queue.get()
                    
                    if self._check_resource_availability(cycle.resources):
                        self.start_training_cycle(cycle.id)
                    else:
                        self.cycle_queue.put((priority, cycle))
                        break
                
                time.sleep(1)  # Prevent busy waiting
                
            except Exception as e:
                logger.error(f"Error in cycle manager: {e}")

    def _update_cycle_progress(self, cycle: TrainingCycle) -> float:
        """Update cycle progress."""
        try:
            # Get current metrics
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''
                SELECT value 
                FROM cycle_metrics 
                WHERE cycle_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (cycle.id,))
            
            result = c.fetchone()
            conn.close()
            
            if result:
                progress = float(result[0])
                
                # Update progress
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                
                c.execute('''
                    UPDATE training_cycles 
                    SET progress = ? 
                    WHERE id = ?
                ''', (progress, cycle.id))
                
                conn.commit()
                conn.close()
                
                return progress
            
            return cycle.progress
            
        except Exception as e:
            logger.error(f"Error updating cycle progress: {e}")
            return cycle.progress

    def _complete_cycle(self, cycle_id: str):
        """Complete a training cycle."""
        try:
            cycle = self.active_cycles[cycle_id]
            
            # Update database
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''
                UPDATE training_cycles 
                SET status = ?, end_time = ?, progress = 1.0 
                WHERE id = ?
            ''', (TrainingStatus.COMPLETED.value, datetime.now(), cycle_id))
            
            conn.commit()
            conn.close()
            
            # Release resources
            self._release_resources(cycle.resources)
            
            # Remove from active cycles
            del self.active_cycles[cycle_id]
            
            logger.info(f"Completed training cycle: {cycle_id}")
            
        except Exception as e:
            logger.error(f"Error completing cycle: {e}")

    def _cleanup_cycle(self, cycle_id: str):
        """Clean up a failed cycle."""
        try:
            cycle = self.active_cycles[cycle_id]
            
            # Release resources
            self._release_resources(cycle.resources)
            
            # Remove from active cycles
            del self.active_cycles[cycle_id]
            
            logger.info(f"Cleaned up failed cycle: {cycle_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up cycle: {e}")

    def get_cycle_status(self, cycle_id: str) -> Dict:
        """Get status of a training cycle."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('SELECT * FROM training_cycles WHERE id = ?', (cycle_id,))
            cycle_data = c.fetchone()
            
            if not cycle_data:
                return {
                    "status": "error",
                    "message": "Cycle not found"
                }
            
            cycle = self._create_cycle_from_db(cycle_data)
            
            # Get latest metrics
            c.execute('''
                SELECT metric_name, value 
                FROM cycle_metrics 
                WHERE cycle_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 10
            ''', (cycle_id,))
            
            metrics = {row[0]: row[1] for row in c.fetchall()}
            
            conn.close()
            
            return {
                "status": "success",
                "cycle": {
                    "id": cycle.id,
                    "agent_id": cycle.agent_id,
                    "status": cycle.status.value,
                    "progress": cycle.progress,
                    "start_time": cycle.start_time.isoformat() if cycle.start_time else None,
                    "end_time": cycle.end_time.isoformat() if cycle.end_time else None,
                    "error": cycle.error,
                    "metrics": metrics
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting cycle status: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def handle_request(self, request: Dict) -> Dict:
        """Handle incoming requests."""
        try:
            action = request.get("action")
            
            # Update health status
            # self._update_health_status() # This line was removed as per new_code
            
            if action == "health_check":
                return {
                    "status": "ok",
                    "service": "self_training_orchestrator",
                    "ready": True,
                    "initialized": True,
                    "message": "SelfTrainingOrchestrator is healthy",
                    "timestamp": datetime.now().isoformat(),
                    "uptime": self._get_health_status()["uptime"], # Changed to use _get_health_status
                    "active_cycles": self._get_health_status()["active_cycles"], # Changed to use _get_health_status
                    "database_status": self._get_health_status()["database_status"] # Changed to use _get_health_status
                }
            
            elif action == "create_cycle":
                return self.create_training_cycle(
                    request["agent_id"],
                    request["config"],
                    request.get("priority", 1)
                )
                
            elif action == "start_cycle":
                return self.start_training_cycle(request["cycle_id"])
                
            elif action == "get_status":
                return self.get_cycle_status(request["cycle_id"])
                
            else:
                return {
                    "status": "error",
                    "message": "Unknown action"
                }
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def run(self):
        """Run the orchestrator's main loop."""
        logger.info(f"Starting {self.name} on port {self.port}")
        
        while self.running:
            try:
                # Wait for request
                request = json.loads(self.socket.recv_string())
                
                # Process request
                response = self.handle_request(request)
                
                # Send response
                self.socket.send_string(json.dumps(response))
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.socket.send_string(json.dumps({
                    "status": "error",
                    "message": str(e)
                }))

    def stop(self):
        """Stop the orchestrator."""
        logger.info("Stopping Self Training Orchestrator")
        self.running = False
        
        # Wait for threads to finish
        if self.cycle_thread:
            self.cycle_thread.join(timeout=2.0)
            logger.info("Cycle thread joined")
        
        # Close sockets
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
            logger.info("Main socket closed")
        
        # Terminate context
        if hasattr(self, 'context') and self.context:
            self.context.term()
            logger.info("ZMQ context terminated")
        
        logger.info("Self Training Orchestrator stopped")

    def cleanup(self):
        """Clean up resources with proper error handling"""
        logger.info("Cleaning up resources")
        self.running = False
        
        # Close sockets
        if hasattr(self, 'socket') and self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"Error closing main socket: {e}")
        
        if hasattr(self, 'health_socket') and self.health_socket:
            try:
                self.health_socket.close()
            except Exception as e:
                logger.error(f"Error closing health socket: {e}")
        
        # Terminate context
        if hasattr(self, 'context') and self.context:
            try:
                self.context.term()
            except Exception as e:
                logger.error(f"Error terminating ZMQ context: {e}")
        
        logger.info(f"{self.name} stopped")

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = SelfTrainingOrchestrator()
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