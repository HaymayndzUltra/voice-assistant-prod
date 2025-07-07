"""
Learning Orchestration Service Agent

This agent manages the entire training lifecycle by consuming learning opportunities
from the LearningOpportunityDetector, creating training cycles, allocating resources,
and initiating training jobs. It combines functionality from LearningManager and
SelfTrainingOrchestrator.
"""

import os
import json
import time
import logging
import threading
import zmq
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from queue import PriorityQueue
from collections import deque
import uuid
import psutil

# Import BaseAgent
from common.core.base_agent import BaseAgent

# Import standardized data models
from common.utils.learning_models import LearningOpportunity, TrainingCycle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('learning_orchestration_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LearningOrchestrationService")

# Constants
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
DEFAULT_LEARNING_RATE = 0.01
MAX_LEARNING_SESSIONS = 10

class ResourceType(Enum):
    """Resource types for training cycles"""
    CPU = "cpu"
    GPU = "gpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"

class LearningOrchestrationService(BaseAgent):
    """
    LearningOrchestrationService: Manages the entire training lifecycle by consuming
    learning opportunities, creating training cycles, allocating resources, and
    initiating training jobs.
    """
    def __init__(self):
        """Initialize the Learning Orchestration Service."""
        self.name = "LearningOrchestrationService"
        self.port = 5720  # Choose an available port
        self.start_time = time.time()
        self.running = True
        self.processed_items = 0
        self.cycles_managed = 0
        
        # Initialize BaseAgent
        super().__init__()
        
        # Learning state (from LearningManager)
        self.learning_sessions = {}
        self.learning_history = []
        self.current_learning_rate = DEFAULT_LEARNING_RATE
        
        # Training cycle management (from SelfTrainingOrchestrator)
        self.active_cycles = {}
        self.cycle_queue = PriorityQueue()
        self.opportunity_buffer = deque(maxlen=100)  # Store last 100 opportunities
        
        # Resource management (from SelfTrainingOrchestrator)
        self.resource_limits = {
            ResourceType.CPU: 100.0,  # CPU percentage
            ResourceType.GPU: 100.0,  # GPU percentage
            ResourceType.MEMORY: 16.0,  # GB
            ResourceType.STORAGE: 100.0,  # GB
            ResourceType.NETWORK: 1000.0  # Mbps
        }
        self.available_resources = self.resource_limits.copy()
        
        # Initialize database
        self.db_path = os.path.join("data", "learning_orchestration.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        
        # Initialize threads
        self.cycle_thread = None
        self.fetch_thread = None
        
        # Initialize error bus
        self.error_bus_port = 7150
        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')
        
        logger.info(f"{self.name} initialized")
    
    def _setup_sockets(self):
        """Set up ZMQ sockets for communication"""
        self.context = zmq.Context()
        
        # Main REP socket for receiving requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        
        # REQ socket for communicating with LearningOpportunityDetector
        self.lod_socket = self.context.socket(zmq.REQ)
        self.lod_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.lod_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.lod_socket.connect("tcp://localhost:5710")  # LOD port
        
        # Error bus connection
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)
        
        logger.info("ZMQ sockets initialized")
    
    def _register_with_digital_twin(self):
        """Register with SystemDigitalTwin"""
        try:
            # Create a socket to connect to SystemDigitalTwin
            digital_twin_socket = self.context.socket(zmq.REQ)
            digital_twin_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 seconds timeout
            digital_twin_socket.connect("tcp://localhost:5555")  # SystemDigitalTwin port
            
            # Prepare registration message
            registration_msg = {
                "action": "register",
                "agent_id": self.name,
                "agent_type": "learning",
                "host": "localhost",
                "port": self.port,
                "capabilities": ["learning_orchestration", "resource_allocation", "training_management"],
                "dependencies": ["LearningOpportunityDetector"]
            }
            
            # Send registration message
            digital_twin_socket.send_json(registration_msg)
            response = digital_twin_socket.recv_json()
            
            if response.get("status") == "success":
                logger.info(f"Successfully registered with SystemDigitalTwin: {response}")
            else:
                logger.error(f"Failed to register with SystemDigitalTwin: {response}")
                
        except Exception as e:
            logger.error(f"Error registering with SystemDigitalTwin: {str(e)}")
        finally:
            if 'digital_twin_socket' in locals():
                digital_twin_socket.close()
    
    def _init_db(self):
        """Initialize the SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Create tables for training cycles
            c.execute('''
                CREATE TABLE IF NOT EXISTS training_cycles (
                    id TEXT PRIMARY KEY,
                    model_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time DATETIME,
                    end_time DATETIME,
                    resources TEXT NOT NULL,
                    hyperparameters TEXT NOT NULL,
                    training_logs TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create table for learning opportunities
            c.execute('''
                CREATE TABLE IF NOT EXISTS learning_opportunities (
                    id TEXT PRIMARY KEY,
                    source_agent TEXT NOT NULL,
                    opportunity_type TEXT NOT NULL,
                    priority_score REAL NOT NULL,
                    status TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create table for cycle-opportunity mapping
            c.execute('''
                CREATE TABLE IF NOT EXISTS cycle_opportunities (
                    cycle_id TEXT NOT NULL,
                    opportunity_id TEXT NOT NULL,
                    PRIMARY KEY (cycle_id, opportunity_id),
                    FOREIGN KEY (cycle_id) REFERENCES training_cycles (id),
                    FOREIGN KEY (opportunity_id) REFERENCES learning_opportunities (id)
                )
            ''')
            
            # Create table for performance metrics
            c.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id TEXT PRIMARY KEY,
                    cycle_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cycle_id) REFERENCES training_cycles (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    def run(self):
        """Main agent loop"""
        try:
            # Setup ZMQ sockets
            self._setup_sockets()
            
            # Register with SystemDigitalTwin
            self._register_with_digital_twin()
            
            # Start background threads
            self.cycle_thread = threading.Thread(target=self._run_cycle_manager)
            self.fetch_thread = threading.Thread(target=self._run_opportunity_fetcher)
            
            self.cycle_thread.daemon = True
            self.fetch_thread.daemon = True
            
            self.cycle_thread.start()
            self.fetch_thread.start()
            
            logger.info(f"{self.name} started and running")
            
            # Main loop - handle requests
            while self.running:
                try:
                    # Use poll to avoid blocking indefinitely
                    poller = zmq.Poller()
                    poller.register(self.socket, zmq.POLLIN)
                    
                    socks = dict(poller.poll(1000))  # 1 second timeout
                    
                    if self.socket in socks and socks[self.socket] == zmq.POLLIN:
                        message = self.socket.recv_json()
                        response = self._handle_request(message)
                        self.socket.send_json(response)
                        self.processed_items += 1
                        
                except zmq.ZMQError as e:
                    if e.errno == zmq.EAGAIN:
                        continue
                    else:
                        logger.error(f"ZMQ error in main loop: {str(e)}")
                        self.report_error("zmq_error", str(e))
                except Exception as e:
                    logger.error(f"Error in main loop: {str(e)}")
                    self.report_error("main_loop_error", str(e))
                    
                time.sleep(0.01)  # Small sleep to prevent CPU overuse
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down")
        except Exception as e:
            logger.error(f"Unexpected error in run method: {str(e)}")
            self.report_error("fatal_error", str(e))
        finally:
            self.cleanup()
    
    def _run_opportunity_fetcher(self):
        """Periodically fetch learning opportunities from LOD"""
        while self.running:
            try:
                # Fetch opportunities from LOD
                opportunities = self._fetch_opportunities()
                
                if opportunities:
                    # Store opportunities
                    for opportunity in opportunities:
                        self._store_opportunity(opportunity)
                    
                    # Create training cycles from opportunities
                    self._create_cycles_from_opportunities()
            except Exception as e:
                logger.error(f"Error fetching opportunities: {str(e)}")
                self.report_error("opportunity_fetch_error", str(e))
            
            time.sleep(30)  # Fetch every 30 seconds
    
    def _fetch_opportunities(self):
        """Fetch learning opportunities from the LearningOpportunityDetector"""
        try:
            # Send request to LOD
            request = {
                "action": "get_opportunities",
                "limit": 10  # Get up to 10 opportunities
            }
            
            self.lod_socket.send_json(request)
            response = self.lod_socket.recv_json()
            
            if response.get("status") == "success":
                return response.get("opportunities", [])
            else:
                logger.error(f"Error fetching opportunities: {response.get('message')}")
                return []
        except Exception as e:
            logger.error(f"Error communicating with LOD: {str(e)}")
            return []
    
    def _store_opportunity(self, opportunity_data):
        """Store a learning opportunity in the database"""
        try:
            # Convert to LearningOpportunity model if it's not already
            if not isinstance(opportunity_data, LearningOpportunity):
                opportunity = LearningOpportunity(**opportunity_data)
            else:
                opportunity = opportunity_data
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''
                INSERT OR REPLACE INTO learning_opportunities 
                (id, source_agent, opportunity_type, priority_score, status, data, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(opportunity.opportunity_id),
                opportunity.source_agent,
                opportunity.opportunity_type,
                opportunity.priority_score,
                opportunity.status,
                json.dumps(opportunity.interaction_data),
                opportunity.created_at.isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            # Add to buffer
            self.opportunity_buffer.append(opportunity_data)
            
            logger.info(f"Stored learning opportunity: {opportunity.opportunity_id}")
            return True
        except Exception as e:
            logger.error(f"Error storing opportunity: {str(e)}")
            return False
    
    def _create_cycles_from_opportunities(self):
        """Create training cycles from accumulated opportunities"""
        try:
            # Get pending opportunities
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''
                SELECT id, source_agent, opportunity_type, priority_score, data
                FROM learning_opportunities
                WHERE status = 'pending'
                ORDER BY priority_score DESC
                LIMIT 20
            ''')
            
            opportunities = c.fetchall()
            
            if not opportunities:
                conn.close()
                return
            
            # Group opportunities by source agent
            agent_opportunities = {}
            for opp in opportunities:
                agent = opp[1]
                if agent not in agent_opportunities:
                    agent_opportunities[agent] = []
                agent_opportunities[agent].append({
                    "id": opp[0],
                    "type": opp[2],
                    "priority": opp[3],
                    "data": json.loads(opp[4])
                })
            
            # Create cycles for each agent with sufficient opportunities
            for agent, opps in agent_opportunities.items():
                if len(opps) >= 3:  # Minimum 3 opportunities to create a cycle
                    # Create a cycle
                    cycle_id = self._create_training_cycle(
                        model_name=f"{agent}_model",
                        opportunity_ids=[o["id"] for o in opps],
                        priority=max([o["priority"] for o in opps])
                    )
                    
                    if cycle_id:
                        # Update opportunity status
                        for opp_id in [o["id"] for o in opps]:
                            c.execute('''
                                UPDATE learning_opportunities
                                SET status = 'processed'
                                WHERE id = ?
                            ''', (opp_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error creating cycles from opportunities: {str(e)}")
    
    def _create_training_cycle(self, model_name, opportunity_ids, priority=0.5):
        """Create a new training cycle"""
        try:
            # Generate cycle ID
            cycle_id = str(uuid.uuid4())
            
            # Allocate resources based on priority
            resources = self._allocate_resources_for_cycle(priority)
            if not resources:
                logger.warning(f"Insufficient resources for cycle {cycle_id}")
                return None
            
            # Set hyperparameters based on model and priority
            hyperparameters = {
                "learning_rate": self.current_learning_rate,
                "batch_size": 32,
                "epochs": max(1, int(priority * 10)),  # 1-10 epochs based on priority
                "optimizer": "adam"
            }
            
            # Create standardized TrainingCycle object
            cycle = TrainingCycle(
                model_name=model_name,
                learning_opportunities=opportunity_ids,
                resource_allocation=resources,
                hyperparameters=hyperparameters
            )
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''
                INSERT INTO training_cycles 
                (id, model_name, status, resources, hyperparameters)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                str(cycle.cycle_id),
                cycle.model_name,
                cycle.status,
                json.dumps(cycle.resource_allocation),
                json.dumps(cycle.hyperparameters)
            ))
            
            # Link opportunities to cycle
            for opp_id in opportunity_ids:
                c.execute('''
                    INSERT INTO cycle_opportunities 
                    (cycle_id, opportunity_id)
                    VALUES (?, ?)
                ''', (str(cycle.cycle_id), opp_id))
            
            conn.commit()
            conn.close()
            
            # Add to queue
            self.cycle_queue.put((-priority, cycle))
            self.cycles_managed += 1
            
            logger.info(f"Created training cycle {cycle.cycle_id} for model {model_name}")
            return cycle.cycle_id
            
        except Exception as e:
            logger.error(f"Error creating training cycle: {str(e)}")
            return None
    
    def _allocate_resources_for_cycle(self, priority):
        """Allocate resources for a training cycle based on priority"""
        # Higher priority gets more resources
        if priority >= 0.8:  # High priority
            resources = {
                "gpu_id": 0,
                "vram_mb": 8192,
                "cpu_cores": 8,
                "ram_mb": 16384
            }
        elif priority >= 0.5:  # Medium priority
            resources = {
                "gpu_id": 0,
                "vram_mb": 4096,
                "cpu_cores": 4,
                "ram_mb": 8192
            }
        else:  # Low priority
            resources = {
                "gpu_id": 0,
                "vram_mb": 2048,
                "cpu_cores": 2,
                "ram_mb": 4096
            }
        
        # Check if resources are available (simplified)
        # In a real implementation, we would check actual resource availability
        return resources
    
    def _run_cycle_manager(self):
        """Manage training cycles"""
        while self.running:
            try:
                # Check for cycles ready to start
                while not self.cycle_queue.empty():
                    priority, cycle = self.cycle_queue.get()
                    
                    # Start the cycle
                    self._start_cycle(cycle.cycle_id)
                
                # Update active cycles
                for cycle_id in list(self.active_cycles.keys()):
                    # Check cycle status
                    status = self._get_cycle_status(cycle_id)
                    
                    if status == "completed" or status == "failed":
                        self._cleanup_cycle(cycle_id)
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in cycle manager: {str(e)}")
                self.report_error("cycle_manager_error", str(e))
    
    def _start_cycle(self, cycle_id):
        """Start a training cycle"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Get cycle data
            c.execute('SELECT * FROM training_cycles WHERE id = ?', (cycle_id,))
            cycle_data = c.fetchone()
            
            if not cycle_data:
                logger.error(f"Cycle {cycle_id} not found")
                conn.close()
                return False
            
            # Update status to running
            c.execute('''
                UPDATE training_cycles 
                SET status = ?, start_time = ? 
                WHERE id = ?
            ''', ("running", datetime.now().isoformat(), cycle_id))
            
            conn.commit()
            conn.close()
            
            # Add to active cycles
            self.active_cycles[cycle_id] = {
                "id": cycle_id,
                "start_time": datetime.now(),
                "progress": 0.0
            }
            
            # Log the training initiation
            resources = json.loads(cycle_data[5])
            hyperparameters = json.loads(cycle_data[6])
            logger.info(f"Started training cycle {cycle_id} with resources {resources} and hyperparameters {hyperparameters}")
            
            # In a real implementation, we would make a call to the Training Executor on PC2
            # For now, just log that we would do this
            logger.info(f"[PLACEHOLDER] Would initiate training job for cycle {cycle_id} on Training Executor (PC2)")
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting cycle {cycle_id}: {str(e)}")
            self.report_error("cycle_start_error", str(e))
            return False
    
    def _get_cycle_status(self, cycle_id):
        """Get the status of a training cycle"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('SELECT status FROM training_cycles WHERE id = ?', (cycle_id,))
            result = c.fetchone()
            
            conn.close()
            
            if result:
                return result[0]
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting cycle status: {str(e)}")
            return None
    
    def _cleanup_cycle(self, cycle_id):
        """Clean up a completed or failed cycle"""
        try:
            # Remove from active cycles
            if cycle_id in self.active_cycles:
                del self.active_cycles[cycle_id]
                logger.info(f"Cleaned up cycle {cycle_id}")
                
        except Exception as e:
            logger.error(f"Error cleaning up cycle {cycle_id}: {str(e)}")
    
    def _handle_request(self, message):
        """Handle incoming requests"""
        action = message.get("action", "")
        
        if action == "health_check":
            return self._get_health_status()
        elif action == "get_cycle_status":
            return self._handle_get_cycle_status(message)
        elif action == "get_active_cycles":
            return self._handle_get_active_cycles(message)
        elif action == "get_opportunities":
            return self._handle_get_opportunities(message)
        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}"
            }
    
    def _handle_get_cycle_status(self, message):
        """Handle request to get cycle status"""
        cycle_id = message.get("cycle_id")
        
        if not cycle_id:
            return {
                "status": "error",
                "message": "Missing cycle_id"
            }
        
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
            
            # Get opportunities for this cycle
            c.execute('''
                SELECT o.id, o.source_agent, o.opportunity_type, o.priority_score
                FROM learning_opportunities o
                JOIN cycle_opportunities co ON o.id = co.opportunity_id
                WHERE co.cycle_id = ?
            ''', (cycle_id,))
            
            opportunities = [{
                "id": row[0],
                "source_agent": row[1],
                "type": row[2],
                "priority": row[3]
            } for row in c.fetchall()]
            
            conn.close()
            
            return {
                "status": "success",
                "cycle": {
                    "id": cycle_data[0],
                    "model_name": cycle_data[1],
                    "status": cycle_data[2],
                    "start_time": cycle_data[3],
                    "end_time": cycle_data[4],
                    "resources": json.loads(cycle_data[5]),
                    "hyperparameters": json.loads(cycle_data[6]),
                    "training_logs": cycle_data[7],
                    "opportunities": opportunities
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting cycle status: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _handle_get_active_cycles(self, message):
        """Handle request to get all active cycles"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('SELECT id, model_name, status FROM training_cycles WHERE status = "running"')
            cycles = [{
                "id": row[0],
                "model_name": row[1],
                "status": row[2]
            } for row in c.fetchall()]
            
            conn.close()
            
            return {
                "status": "success",
                "cycles": cycles
            }
            
        except Exception as e:
            logger.error(f"Error getting active cycles: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _handle_get_opportunities(self, message):
        """Handle request to get learning opportunities"""
        status = message.get("status", "pending")
        limit = message.get("limit", 10)
        
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''
                SELECT id, source_agent, opportunity_type, priority_score, created_at
                FROM learning_opportunities
                WHERE status = ?
                ORDER BY priority_score DESC
                LIMIT ?
            ''', (status, limit))
            
            opportunities = [{
                "id": row[0],
                "source_agent": row[1],
                "type": row[2],
                "priority_score": row[3],
                "created_at": row[4]
            } for row in c.fetchall()]
            
            conn.close()
            
            return {
                "status": "success",
                "opportunities": opportunities
            }
            
        except Exception as e:
            logger.error(f"Error getting opportunities: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _get_health_status(self):
        """Get the health status of the agent"""
        return {
            "status": "healthy",
            "agent_name": self.name,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": time.time() - self.start_time,
            "processed_items": self.processed_items,
            "cycles_managed": self.cycles_managed,
            "active_cycles": len(self.active_cycles),
            "current_learning_rate": self.current_learning_rate,
            "opportunity_buffer_size": len(self.opportunity_buffer),
            "system_metrics": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent
            }
        }
    
    def report_error(self, error_type, message, severity="ERROR", context=None):
        """Report error to the Error Bus"""
        error_data = {
            "error_type": error_type,
            "message": message,
            "severity": severity,
            "context": context or {}
        }
        try:
            msg = json.dumps(error_data).encode('utf-8')
            self.error_bus_pub.send_multipart([b"ERROR:", msg])
        except Exception as e:
            logger.error(f"Failed to publish error to Error Bus: {e}")
    
    def cleanup(self):
        """Clean up resources"""
        logger.info(f"Cleaning up {self.name} resources")
        
        self.running = False
        
        # Wait for threads to finish
        if self.cycle_thread and self.cycle_thread.is_alive():
            self.cycle_thread.join(timeout=2.0)
        
        if self.fetch_thread and self.fetch_thread.is_alive():
            self.fetch_thread.join(timeout=2.0)
        
        # Close sockets
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
        
        if hasattr(self, 'lod_socket') and self.lod_socket:
            self.lod_socket.close()
        
        if hasattr(self, 'error_bus_pub') and self.error_bus_pub:
            self.error_bus_pub.close()
        
        # Terminate ZMQ context
        if hasattr(self, 'context') and self.context:
            self.context.term()
        
        logger.info(f"{self.name} cleanup complete")


if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = LearningOrchestrationService()
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
