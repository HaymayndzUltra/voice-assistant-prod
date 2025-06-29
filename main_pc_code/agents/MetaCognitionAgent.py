from base_agent import BaseAgent
import zmq
import json
import time
import logging
import sqlite3
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from threading import Thread
from collections import defaultdict
import psutil
import torch
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from utils.config_parser import parse_agent_args
from utils.service_discovery_client import discover_service, register_service, get_service_address
from utils.env_loader import get_env
from config.agent_ports import default_ports
from src.network.secure_zmq import is_secure_zmq_enabled, configure_secure_client, configure_secure_server
import threading
_agent_args = parse_agent_args()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('meta_cognition.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Get bind address from environment variables with default to 0.0.0.0 for Docker compatibility
BIND_ADDRESS = get_env('BIND_ADDRESS', '0.0.0.0')

# Secure ZMQ configuration
SECURE_ZMQ = is_secure_zmq_enabled()

class MetaCognitionAgent(BaseAgent):
    def __init__(self, port: Optional[int] = None, **kwargs):
        self.initialization_status = {
            "is_initialized": False,
            "error": None,
            "progress": 0.0,
            "components": {"core": False}
        }
        # Use configured port or default
        self.port = port if port is not None else default_ports.meta_cognition_port
        super().__init__(port=self.port, name="MetaCognitionAgent")
        self.running = True
        self.init_thread = threading.Thread(target=self._perform_initialization, daemon=True)
        self.init_thread.start()
        logger.info("MetaCognitionAgent basic init complete, async init started")

    def _perform_initialization(self):
        try:
            # Place all blocking init here
            self._init_components()
            self.initialization_status["components"]["core"] = True
            self.initialization_status["progress"] = 1.0
            self.initialization_status["is_initialized"] = True
            logger.info("MetaCognitionAgent initialization complete")
        except Exception as e:
            self.initialization_status["error"] = str(e)
            self.initialization_status["progress"] = 0.0
            logger.error(f"Initialization error: {e}")

    def _init_components(self):
        """Initialize all components of the MetaCognitionAgent."""
        self.context = zmq.Context()
        
        # Main REP socket for handling requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        
        # Apply secure ZMQ if enabled
        if SECURE_ZMQ:
            self.socket = configure_secure_server(self.socket)
            logger.info("Secure ZMQ enabled for MetaCognitionAgent")
        
        # Bind to address using BIND_ADDRESS for Docker compatibility
        bind_address = f"tcp://{BIND_ADDRESS}:{self.port}"
        self.socket.bind(bind_address)
        logger.info(f"MetaCognitionAgent socket bound to {bind_address}")
        
        # Register with service discovery
        self._register_service()
        
        # SUB sockets for observing other agents - use service discovery
        self.cot_sub = self.context.socket(zmq.SUB)
        cot_address = get_service_address("ChainOfThoughtAgent")
        if not cot_address:
            cot_address = f"tcp://localhost:{default_ports.chain_of_thought_port}"  # Fallback
            logger.warning(f"Could not discover ChainOfThoughtAgent, using fallback address: {cot_address}")
        
        # Apply secure ZMQ if enabled
        if SECURE_ZMQ:
            self.cot_sub = configure_secure_client(self.cot_sub)
        
        self.cot_sub.connect(cot_address)
        self.cot_sub.setsockopt_string(zmq.SUBSCRIBE, "reasoning")
        logger.info(f"Connected to ChainOfThoughtAgent at {cot_address}")
        
        self.voting_sub = self.context.socket(zmq.SUB)
        voting_address = get_service_address("ModelVotingManager")
        if not voting_address:
            voting_address = f"tcp://localhost:{default_ports.voting_port}"  # Fallback
            logger.warning(f"Could not discover ModelVotingManager, using fallback address: {voting_address}")
        
        # Apply secure ZMQ if enabled
        if SECURE_ZMQ:
            self.voting_sub = configure_secure_client(self.voting_sub)
        
        self.voting_sub.connect(voting_address)
        self.voting_sub.setsockopt_string(zmq.SUBSCRIBE, "voting")
        logger.info(f"Connected to ModelVotingManager at {voting_address}")
        
        # Initialize database
        self.db_path = "meta_cognition.db"
        self._init_database()
        
        # Start observation threads
        self.observation_threads = []
        
        # Connect to KnowledgeBase and CoordinatorAgent using service discovery
        self.kb_socket = self._create_service_socket("KnowledgeBase")
        self.coordinator_socket = self._create_service_socket("CoordinatorAgent")
        
        # Initialize learning analysis components
        self.learning_metrics = defaultdict(list)
        self.performance_history = []
        self.knowledge_graph = {}
        
        # Initialize memory optimization components
        self.memory_threshold = 0.8  # 80% memory usage threshold
        self.cache_size = 1000
        self.memory_cache = {}
        self.memory_stats: Dict[str, float] = {
            'total_usage': 0.0,
            'peak_usage': 0.0,
            'optimization_count': 0.0
        }
        
        # Initialize monitoring systems
        self.system_metrics = {
            'cpu_usage': [],
            'memory_usage': [],
            'response_times': [],
            'error_rates': []
        }
        self.monitoring_interval = 60  # seconds
        self.alert_thresholds = {
            'cpu': 80,  # percentage
            'memory': 80,  # percentage
            'response_time': 1.0,  # seconds
            'error_rate': 0.05  # 5%
        }
        
        logger.info(f"Enhanced MetaCognitionAgent initialized on port {self.port}")
    
    def _register_service(self):
        """Register this agent with the service discovery system"""
        try:
            register_result = register_service(
                name="MetaCognitionAgent",
                port=self.port,
                additional_info={
                    "capabilities": ["meta_cognition", "learning_analysis", "memory_optimization", "system_monitoring"],
                    "status": "running"
                }
            )
            if register_result and register_result.get("status") == "SUCCESS":
                logger.info("Successfully registered with service discovery")
            else:
                logger.warning(f"Service registration failed: {register_result.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error registering service: {e}")
    
    def _create_service_socket(self, service_name):
        """Create a socket connected to a service using service discovery"""
        try:
            socket = self.context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            
            # Apply secure ZMQ if enabled
            if SECURE_ZMQ:
                socket = configure_secure_client(socket)
            
            # Get service address from service discovery
            service_address = get_service_address(service_name)
            if service_address:
                socket.connect(service_address)
                logger.info(f"Connected to {service_name} at {service_address}")
            else:
                # Fallback to default port if service discovery fails
                fallback_port = getattr(default_ports, f"{service_name.lower()}_port", None)
                if fallback_port:
                    fallback_address = f"tcp://localhost:{fallback_port}"
                    socket.connect(fallback_address)
                    logger.warning(f"Could not discover {service_name}, using fallback address: {fallback_address}")
                else:
                    logger.error(f"Failed to connect to {service_name}: No service discovery or fallback available")
            return socket
        except Exception as e:
            logger.error(f"Error creating socket for {service_name}: {str(e)}")
            return None

    def _init_database(self):
        """Initialize SQLite database with enhanced tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Existing tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS thought_traces (
                trace_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                context TEXT,
                summary TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reasoning_steps (
                step_id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id INTEGER,
                timestamp TIMESTAMP,
                step_number INTEGER,
                thought TEXT,
                confidence REAL,
                metadata TEXT,
                FOREIGN KEY (trace_id) REFERENCES thought_traces(trace_id)
            )
        ''')
        
        # New tables for learning analysis
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                metric_type TEXT,
                value REAL,
                context TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_graph (
                node_id INTEGER PRIMARY KEY AUTOINCREMENT,
                concept TEXT,
                relationships TEXT,
                confidence REAL,
                last_updated TIMESTAMP
            )
        ''')
        
        # New tables for memory optimization
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_stats (
                stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                total_usage REAL,
                peak_usage REAL,
                optimization_count INTEGER
            )
        ''')
        
        # New tables for monitoring
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                cpu_usage REAL,
                memory_usage REAL,
                response_time REAL,
                error_rate REAL
            )
        ''')
        
        conn.commit()
        conn.close()

    def analyze_learning(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze learning patterns and update knowledge graph."""
        try:
            # Extract learning metrics
            confidence = data.get('confidence', 0.0)
            performance = data.get('performance', 0.0)
            context = data.get('context', {})
            
            # Update learning metrics
            self.learning_metrics['confidence'].append(confidence)
            self.learning_metrics['performance'].append(performance)
            
            # Calculate learning trends
            trends = {
                'confidence_trend': np.mean(self.learning_metrics['confidence'][-10:]),
                'performance_trend': np.mean(self.learning_metrics['performance'][-10:]),
                'learning_rate': self._calculate_learning_rate()
            }
            
            # Update knowledge graph
            self._update_knowledge_graph(context, confidence)
            
            # Store metrics
            self._store_learning_metrics(trends)
            
            return {
                'status': 'success',
                'trends': trends,
                'knowledge_updates': len(self.knowledge_graph)
            }
            
        except Exception as e:
            logger.error(f"Error in learning analysis: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def optimize_memory(self) -> Dict[str, Any]:
        """Optimize memory usage and cache management."""
        try:
            current_memory = psutil.Process().memory_percent()
            self.memory_stats['total_usage'] = current_memory
            self.memory_stats['peak_usage'] = max(self.memory_stats['peak_usage'], current_memory)
            
            if current_memory > self.memory_threshold:
                # Perform memory optimization
                self._clear_old_cache()
                self._compress_memory()
                self.memory_stats['optimization_count'] += 1
                
                # Store memory stats
                self._store_memory_stats()
                
                return {
                    'status': 'optimized',
                    'memory_usage': current_memory,
                    'optimization_count': self.memory_stats['optimization_count']
                }
            
            return {
                'status': 'normal',
                'memory_usage': current_memory
            }
            
        except Exception as e:
            logger.error(f"Error in memory optimization: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def monitor_system(self) -> Dict[str, Any]:
        """Monitor system metrics and performance."""
        try:
            # Collect system metrics
            cpu_usage = psutil.cpu_percent()
            memory_usage = psutil.virtual_memory().percent
            response_time = self._calculate_response_time()
            error_rate = self._calculate_error_rate()
            
            # Update metrics history
            self.system_metrics['cpu_usage'].append(cpu_usage)
            self.system_metrics['memory_usage'].append(memory_usage)
            self.system_metrics['response_times'].append(response_time)
            self.system_metrics['error_rates'].append(error_rate)
            
            # Check for alerts
            alerts = self._check_alerts()
            
            # Store metrics
            self._store_system_metrics()
            
            return {
                'status': 'success',
                'metrics': {
                    'cpu_usage': cpu_usage,
                    'memory_usage': memory_usage,
                    'response_time': response_time,
                    'error_rate': error_rate
                },
                'alerts': alerts
            }
            
        except Exception as e:
            logger.error(f"Error in system monitoring: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def _calculate_learning_rate(self) -> float:
        """Calculate the current learning rate based on performance history."""
        if len(self.performance_history) < 2:
            return 0.0
        
        recent_performance = self.performance_history[-10:]
        if len(recent_performance) < 2:
            return 0.0
            
        return np.mean(np.diff(recent_performance))

    def _update_knowledge_graph(self, context: Dict[str, Any], confidence: float):
        """Update the knowledge graph with new information."""
        for concept, relationships in context.items():
            if concept not in self.knowledge_graph:
                self.knowledge_graph[concept] = {
                    'relationships': relationships,
                    'confidence': confidence,
                    'last_updated': datetime.now()
                }
            else:
                # Update existing concept
                self.knowledge_graph[concept]['confidence'] = (
                    self.knowledge_graph[concept]['confidence'] * 0.7 + confidence * 0.3
                )
                self.knowledge_graph[concept]['last_updated'] = datetime.now()

    def _clear_old_cache(self):
        """Clear old entries from memory cache."""
        if len(self.memory_cache) > self.cache_size:
            # Sort by last access time and remove oldest entries
            sorted_cache = sorted(
                self.memory_cache.items(),
                key=lambda x: x[1]['last_access']
            )
            self.memory_cache = dict(sorted_cache[-self.cache_size:])

    def _compress_memory(self):
        """Compress memory usage by optimizing data structures."""
        # Implement memory compression strategies
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        # Clear unused variables
        import gc
        gc.collect()

    def _calculate_response_time(self) -> float:
        """Calculate average response time."""
        if not self.system_metrics['response_times']:
            return 0.0
        return np.mean(self.system_metrics['response_times'][-100:])

    def _calculate_error_rate(self) -> float:
        """Calculate current error rate."""
        if not self.system_metrics['error_rates']:
            return 0.0
        return np.mean(self.system_metrics['error_rates'][-100:])

    def _check_alerts(self) -> List[Dict[str, Any]]:
        """Check for system alerts based on thresholds."""
        alerts = []
        
        if self.system_metrics['cpu_usage'][-1] > self.alert_thresholds['cpu']:
            alerts.append({
                'type': 'cpu',
                'level': 'warning',
                'message': f'High CPU usage: {self.system_metrics["cpu_usage"][-1]}%'
            })
            
        if self.system_metrics['memory_usage'][-1] > self.alert_thresholds['memory']:
            alerts.append({
                'type': 'memory',
                'level': 'warning',
                'message': f'High memory usage: {self.system_metrics["memory_usage"][-1]}%'
            })
            
        if self._calculate_response_time() > self.alert_thresholds['response_time']:
            alerts.append({
                'type': 'performance',
                'level': 'warning',
                'message': 'High response time detected'
            })
            
        if self._calculate_error_rate() > self.alert_thresholds['error_rate']:
            alerts.append({
                'type': 'error',
                'level': 'critical',
                'message': 'High error rate detected'
            })
            
        return alerts

    def _store_learning_metrics(self, metrics: Dict[str, Any]):
        """Store learning metrics in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for metric_type, value in metrics.items():
            cursor.execute('''
                INSERT INTO learning_metrics 
                (timestamp, metric_type, value, context)
                VALUES (?, ?, ?, ?)
            ''', (
                datetime.now(),
                metric_type,
                value,
                json.dumps(self.knowledge_graph)
            ))
        
        conn.commit()
        conn.close()

    def _store_memory_stats(self):
        """Store memory statistics in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO memory_stats 
            (timestamp, total_usage, peak_usage, optimization_count)
            VALUES (?, ?, ?, ?)
        ''', (
            datetime.now(),
            self.memory_stats['total_usage'],
            self.memory_stats['peak_usage'],
            self.memory_stats['optimization_count']
        ))
        
        conn.commit()
        conn.close()

    def _store_system_metrics(self):
        """Store system metrics in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO system_metrics 
            (timestamp, cpu_usage, memory_usage, response_time, error_rate)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            datetime.now(),
            self.system_metrics['cpu_usage'][-1],
            self.system_metrics['memory_usage'][-1],
            self._calculate_response_time(),
            self._calculate_error_rate()
        ))
        
        conn.commit()
        conn.close()

    def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        try:
            action = request.get('action', '')
            
            if action == 'analyze_learning':
                data = request.get('data', {})
                return self.analyze_learning(data)
                
            elif action == 'optimize_memory':
                threshold = request.get('threshold', self.memory_threshold)
                cache_size = request.get('cache_size', self.cache_size)
                self.memory_threshold = threshold
                self.cache_size = cache_size
                return self.optimize_memory()
                
            elif action == 'monitor_system':
                return self.monitor_system()
                
            elif action == 'health_check':
                return {
                    'status': 'ok' if self.initialization_status["is_initialized"] else "initializing",
                    'initialization_status': self.initialization_status
                }
                
            else:
                return {
                    'status': 'error',
                    'message': f'Unknown action: {action}'
                }
                
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def run(self):
        logger.info("Starting MetaCognitionAgent main loop")
        while self.running:
            try:
                if hasattr(self, 'socket'):
                    if self.socket.poll(timeout=100):
                        message = self.socket.recv_json()
                        if message.get("action") == "health_check":
                            self.socket.send_json({
                                "status": "ok" if self.initialization_status["is_initialized"] else "initializing",
                                "initialization_status": self.initialization_status
                            })
                            continue
                        if not self.initialization_status["is_initialized"]:
                            self.socket.send_json({
                                "status": "error",
                                "error": "Agent is still initializing",
                                "initialization_status": self.initialization_status
                            })
                            continue
                        response = self._handle_request(message)
                        self.socket.send_json(response)
                    else:
                        time.sleep(0.05)
                else:
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                try:
                    if hasattr(self, 'socket'):
                        self.socket.send_json({'status': 'error','message': str(e)})
                except Exception as zmq_err:
                    logger.error(f"ZMQ error while sending error response: {zmq_err}")
                    time.sleep(1)

    def _monitor_system_loop(self):
        """Background thread for system monitoring."""
        while self.running:
            try:
                self.monitor_system()
                time.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Error in system monitoring loop: {str(e)}")

    def stop(self):
        """Stop the MetaCognitionAgent gracefully."""
        logger.info("Stopping MetaCognitionAgent...")
        self.running = False
        
        # Stop all threads
        for thread in self.observation_threads:
            thread.join(timeout=2.0)  # Add timeout to avoid hanging
        
        # Close sockets in a try-finally block to ensure they're all closed
        try:
            if hasattr(self, 'socket'):
                self.socket.close()
                logger.debug("Closed main socket")
            
            if hasattr(self, 'cot_sub'):
                self.cot_sub.close()
                logger.debug("Closed CoT subscription socket")
            
            if hasattr(self, 'voting_sub'):
                self.voting_sub.close()
                logger.debug("Closed voting subscription socket")
            
            if hasattr(self, 'kb_socket'):
                self.kb_socket.close()
                logger.debug("Closed knowledge base socket")
            
            if hasattr(self, 'coordinator_socket'):
                self.coordinator_socket.close()
                logger.debug("Closed coordinator socket")
        except Exception as e:
            logger.error(f"Error during socket cleanup: {e}")
        finally:
            # Terminate ZMQ context
            if hasattr(self, 'context'):
                self.context.term()
                logger.debug("Terminated ZMQ context")
        
        logger.info("MetaCognitionAgent stopped successfully")

    def _observe_chain_of_thought(self):
        """Observe and log reasoning steps from ChainOfThoughtAgent."""
        while self.running:
            try:
                topic, message = self.cot_sub.recv_multipart()
                data = json.loads(message)
                
                # Extract session ID or create new trace
                session_id = data.get('session_id')
                if not session_id:
                    session_id = f"session_{int(time.time())}"
                
                # Get or create trace
                trace_id = self._get_or_create_trace(session_id, data.get('context', {}))
                
                # Log reasoning step
                self._log_reasoning_step(
                    trace_id,
                    data.get('step_number', 0),
                    data.get('thought', ''),
                    data.get('confidence', 0.0),
                    data.get('metadata', {})
                )
                
                # Analyze learning from this step
                self.analyze_learning(data)
                
            except Exception as e:
                logger.error(f"Error observing ChainOfThought: {str(e)}")
    
    def _observe_voting(self):
        """Observe and log voting results from ModelVotingManager."""
        while self.running:
            try:
                topic, message = self.voting_sub.recv_multipart()
                data = json.loads(message)
                
                # Extract session ID
                session_id = data.get('session_id')
                if not session_id:
                    continue
                
                # Get trace
                trace_id = self._get_trace_id(session_id)
                if not trace_id:
                    continue
                
                # Log voting result
                self._log_voting_result(
                    trace_id,
                    data.get('model_id', ''),
                    data.get('vote', ''),
                    data.get('confidence', 0.0),
                    data.get('metadata', {})
                )
                
                # Optimize memory after voting
                self.optimize_memory()
                
            except Exception as e:
                logger.error(f"Error observing voting: {str(e)}")

    def _get_or_create_trace(self, session_id: str, context: Dict[str, Any]) -> int:
        """Get existing trace or create new one."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check for existing trace
        cursor.execute('''
            SELECT trace_id 
            FROM thought_traces 
            WHERE session_id = ? AND end_time IS NULL
        ''', (session_id,))
        
        result = cursor.fetchone()
        
        if result:
            trace_id = result[0]
        else:
            # Create new trace
            cursor.execute('''
                INSERT INTO thought_traces 
                (session_id, start_time, context)
                VALUES (?, ?, ?)
            ''', (
                session_id,
                datetime.now(),
                json.dumps(context)
            ))
            trace_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return trace_id
    
    def _get_trace_id(self, session_id: str) -> Optional[int]:
        """Get trace ID for a session.
        
        Args:
            session_id: The session ID to look up
            
        Returns:
            Optional[int]: The trace ID if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT trace_id FROM thought_traces WHERE session_id = ? ORDER BY start_time DESC LIMIT 1",
                (session_id,)
            )
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()
    
    def _log_reasoning_step(self, trace_id: int, step_number: int, thought: str, 
                          confidence: float, metadata: Dict[str, Any]):
        """Log a reasoning step."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO reasoning_steps 
            (trace_id, timestamp, step_number, thought, confidence, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            trace_id,
            datetime.now(),
            step_number,
            thought,
            confidence,
            json.dumps(metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def _log_voting_result(self, trace_id: int, model_id: str, vote: str, 
                          confidence: float, metadata: Dict[str, Any]):
        """Log a voting result."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO voting_results 
            (trace_id, timestamp, model_id, vote, confidence, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            trace_id,
            datetime.now(),
            model_id,
            vote,
            confidence,
            json.dumps(metadata)
        ))
        
        conn.commit()
        conn.close()

    def _get_health_status(self):
        """Overrides the base method to add agent-specific health metrics."""
        base_status = super()._get_health_status()
        specific_metrics = {
            "status_detail": "active",
            "processed_items": getattr(self, 'processed_items', 0),
            "meta_operations": getattr(self, 'meta_operations', 0)
        }
        base_status.update(specific_metrics)
        return base_status

def main():
    """Main entry point for the MetaCognitionAgent."""
    agent = MetaCognitionAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, stopping agent...")
        agent.stop()
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        agent.stop()

if __name__ == "__main__":
    main()