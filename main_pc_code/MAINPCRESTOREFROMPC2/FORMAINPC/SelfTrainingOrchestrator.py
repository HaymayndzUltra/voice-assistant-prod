"""
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
from datetime import datetime
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
from queue import PriorityQueue

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/self_training.log'
)
logger = logging.getLogger(__name__)

class TrainingStatus(Enum):
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

class SelfTrainingOrchestrator:
    def __init__(self, port: int = 5644):
        """Initialize the Self Training Orchestrator."""
        # ZMQ setup
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.port = port
        self.socket.bind(f"tcp://*:{self.port}")
        
        # Health status
        self.health_status = {
            "status": "ok",
            "service": "self_training_orchestrator",
            "port": self.port,
            "start_time": time.time(),
            "last_check": time.time(),
            "active_cycles": 0,
            "database_status": "ok"
        }
        
        # Setup health check socket
        self.health_port = self.port + 1
        try:
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            self.health_socket.bind(f"tcp://0.0.0.0:{self.health_port}")
            logger.info(f"Health check socket bound to port {self.health_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind health check socket: {e}")
            # Continue even if health check socket fails
        
        # Database setup
        self.db_path = "data/self_training.db"
        self._init_db()
        
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
        self.is_running = True
        
        # Start health check thread
        self._start_health_check()
        
        logger.info(f"Self Training Orchestrator initialized on port {self.port}")

    def _start_health_check(self):
        """Start health check thread."""
        self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_thread.start()
        logger.info("Health check thread started")
    
    def _health_check_loop(self):
        """Background loop to handle health check requests."""
        logger.info("Health check loop started")
        
        while self.is_running:
            try:
                # Check for health check requests with timeout
                if hasattr(self, 'health_socket') and self.health_socket.poll(100, zmq.POLLIN):
                    # Receive request (don't care about content)
                    _ = self.health_socket.recv()
                    
                    # Update health status
                    self._update_health_status()
                    
                    # Send response
                    self.health_socket.send_json(self.health_status)
                    
                time.sleep(0.1)  # Small sleep to prevent CPU hogging
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(1)  # Sleep longer on error

    def _update_health_status(self):
        """Update health status with current information."""
        try:
            # Update active cycles count
            active_cycles_count = len(self.active_cycles)
            self.health_status.update({
                "last_check": time.time(),
                "active_cycles": active_cycles_count,
                "uptime": time.time() - self.health_status["start_time"]
            })
        except Exception as e:
            logger.error(f"Error updating health status: {e}")

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
            self.health_status["database_status"] = "ok"
            logger.info("Database initialized successfully")
        except Exception as e:
            self.health_status["database_status"] = "error"
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
        self.is_running = True
        
        while self.is_running:
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
            self._update_health_status()
            
            if action == "health_check":
                return {
                    "status": "ok",
                    "service": "self_training_orchestrator",
                    "ready": True,
                    "initialized": True,
                    "message": "SelfTrainingOrchestrator is healthy",
                    "timestamp": datetime.now().isoformat(),
                    "uptime": self.health_status["uptime"],
                    "active_cycles": self.health_status["active_cycles"],
                    "database_status": self.health_status["database_status"]
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
        logger.info(f"Starting Self Training Orchestrator on port {self.port}")
        
        while self.is_running:
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
        self.is_running = False
        
        # Wait for threads to finish
        if self.cycle_thread:
            self.cycle_thread.join(timeout=2.0)
            logger.info("Cycle thread joined")
            
        if hasattr(self, 'health_thread') and self.health_thread.is_alive():
            self.health_thread.join(timeout=2.0)
            logger.info("Health thread joined")
        
        # Close sockets
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
            logger.info("Main socket closed")
            
        if hasattr(self, 'health_socket') and self.health_socket:
            self.health_socket.close()
            logger.info("Health socket closed")
        
        # Terminate context
        if hasattr(self, 'context') and self.context:
            self.context.term()
            logger.info("ZMQ context terminated")
        
        logger.info("Self Training Orchestrator stopped")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Self Training Orchestrator")
    parser.add_argument("--port", type=int, default=5644, help="Port to listen on")
    args = parser.parse_args()

    orchestrator = SelfTrainingOrchestrator(args.port)
    try:
        orchestrator.run()
    except KeyboardInterrupt:
        orchestrator.stop() 