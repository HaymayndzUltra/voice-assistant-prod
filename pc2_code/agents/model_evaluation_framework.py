"""
Model Evaluation Framework Agent

This agent serves as the central hub for performance tracking and model evaluation.
It collects performance metrics from all agents, analyzes them, and calculates trust
scores for models. It merges functionality from PerformanceLoggerAgent and AgentTrustScorer.
"""

import zmq
import yaml
import sys
import os
import json
import time
import logging
import sqlite3
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from threading import Lock
import psutil
import uuid

# Add project root to Python path for common_utils import
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import BaseAgent
from common.core.base_agent import BaseAgent

# Import standardized data models
from common.utils.learning_models import PerformanceMetric, ModelEvaluationScore

# Import config loader
from pc2_code.agents.utils.config_loader import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('model_evaluation_framework.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load configuration at the module level
try:
    config = Config().get_config()
    if not isinstance(config, dict):
        logger.warning("Config is not a dictionary, using empty dict")
        config = {}
except Exception as e:
    logger.error(f"Error loading config: {e}")
    config = {}

class ModelEvaluationFramework(BaseAgent):
    """
    ModelEvaluationFramework: Serves as the central hub for performance tracking and model evaluation.
    Collects metrics from all agents, analyzes them, and calculates trust scores for models.
    """
    def __init__(self, port: int = 5650):
        """Initialize the Model Evaluation Framework."""
        self.name = "ModelEvaluationFramework"
        self.port = port
        self.start_time = time.time()
        self.running = True
        self.processed_items = 0
        
        # Initialize BaseAgent
        super().__init__()
        
        # Initialize database
        self.db_path = "model_evaluation.db"
        self.db_lock = Lock()
        self._init_database()
        
        # Initialize metrics buffer
        self.metrics_buffer = []
        self.buffer_lock = Lock()
        
        # Initialize error bus
        self.error_bus_port = 7150
        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')
        
        # Start background threads
        self.metrics_processor_thread = None
        self.evaluation_thread = None
        self.cleanup_thread = None
        
        logger.info(f"{self.name} initialized on port {self.port}")
    
    def _setup_sockets(self):
        """Set up ZMQ sockets for communication"""
        self.context = zmq.Context()
        
        # Main REP socket for receiving requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        
        # SUB socket for receiving performance metrics broadcasts
        self.metrics_sub = self.context.socket(zmq.SUB)
        self.metrics_sub.setsockopt_string(zmq.SUBSCRIBE, "METRIC:")
        self.metrics_sub.bind("tcp://*:5651")  # Dedicated port for metrics
        
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
            digital_twin_socket.connect(f"tcp://{self._get_main_pc_ip()}:5555")  # SystemDigitalTwin port
            
            # Prepare registration message
            registration_msg = {
                "action": "register",
                "agent_id": self.name,
                "agent_type": "evaluation",
                "host": self._get_pc2_ip(),
                "port": self.port,
                "capabilities": ["performance_tracking", "model_evaluation", "trust_scoring"],
                "dependencies": []
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
    
    def _get_main_pc_ip(self):
        """Get the IP address of the Main PC from network config"""
        try:
            network_config = self._load_network_config()
            if isinstance(network_config, dict):
                return network_config.get("main_pc_ip", "192.168.100.16")
            return "192.168.100.16"
        except Exception as e:
            logger.error(f"Error getting Main PC IP: {str(e)}")
            return "192.168.100.16"  # Default fallback
    
    def _get_pc2_ip(self):
        """Get the IP address of PC2 from network config"""
        try:
            network_config = self._load_network_config()
            if isinstance(network_config, dict):
                return network_config.get("pc2_ip", "192.168.100.17")
            return "192.168.100.17"
        except Exception as e:
            logger.error(f"Error getting PC2 IP: {str(e)}")
            return "192.168.100.17"  # Default fallback
    
    def _load_network_config(self):
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
    
    def _init_database(self):
        """Initialize SQLite database for metrics and evaluations."""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    metric_id TEXT PRIMARY KEY,
                    agent_name TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp TIMESTAMP,
                    context TEXT
                )
            ''')
            
            # Create model evaluation scores table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_evaluation_scores (
                    evaluation_id TEXT PRIMARY KEY,
                    model_name TEXT NOT NULL,
                    cycle_id TEXT,
                    trust_score REAL NOT NULL,
                    accuracy REAL,
                    f1_score REAL,
                    avg_latency_ms REAL NOT NULL,
                    evaluation_timestamp TIMESTAMP,
                    comparison_data TEXT
                )
            ''')
            
            # Create model performance table (from AgentTrustScorer)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_performance (
                    model_id TEXT PRIMARY KEY,
                    total_interactions INTEGER DEFAULT 0,
                    successful_interactions INTEGER DEFAULT 0,
                    avg_latency_ms REAL DEFAULT 0.0,
                    last_updated TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_agent ON performance_metrics(agent_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON performance_metrics(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_evaluation_model ON model_evaluation_scores(model_name)')
            
            conn.commit()
            conn.close()
            
            logger.info("Database initialized successfully")
    
    def run(self):
        """Main agent loop"""
        try:
            # Setup ZMQ sockets
            self._setup_sockets()
            
            # Register with SystemDigitalTwin
            self._register_with_digital_twin()
            
            # Start background threads
            self.metrics_processor_thread = threading.Thread(target=self._run_metrics_processor)
            self.evaluation_thread = threading.Thread(target=self._run_evaluation_scheduler)
            self.cleanup_thread = threading.Thread(target=self._run_cleanup_scheduler)
            
            self.metrics_processor_thread.daemon = True
            self.evaluation_thread.daemon = True
            self.cleanup_thread.daemon = True
            
            self.metrics_processor_thread.start()
            self.evaluation_thread.start()
            self.cleanup_thread.start()
            
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
    
    def _run_metrics_processor(self):
        """Process incoming performance metrics"""
        while self.running:
            try:
                # Check for incoming metrics with non-blocking recv
                try:
                    message = self.metrics_sub.recv_multipart(flags=zmq.NOBLOCK)
                    if len(message) == 2:
                        topic, payload = message
                        if topic == b"METRIC:":
                            metric_data = json.loads(payload.decode('utf-8'))
                            self._process_metric(metric_data)
                except zmq.ZMQError:
                    # No message available, continue
                    pass
                
                # Process buffered metrics
                with self.buffer_lock:
                    if len(self.metrics_buffer) > 0:
                        metrics_to_process = self.metrics_buffer.copy()
                        self.metrics_buffer = []
                    else:
                        metrics_to_process = []
                
                for metric in metrics_to_process:
                    self._store_metric(metric)
                
            except Exception as e:
                logger.error(f"Error processing metrics: {str(e)}")
                self.report_error("metrics_processor_error", str(e))
            
            time.sleep(0.1)  # Small sleep to prevent CPU overuse
    
    def _process_metric(self, metric_data):
        """Process an incoming performance metric"""
        try:
            # Convert to PerformanceMetric model if it's not already
            if not isinstance(metric_data, PerformanceMetric):
                metric = PerformanceMetric(**metric_data)
            else:
                metric = metric_data
            
            # Add to buffer for batch processing
            with self.buffer_lock:
                self.metrics_buffer.append(metric)
            
        except Exception as e:
            logger.error(f"Error processing metric: {str(e)}")
    
    def _store_metric(self, metric):
        """Store a performance metric in the database"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Store in performance_metrics table
                cursor.execute('''
                    INSERT OR REPLACE INTO performance_metrics 
                    (metric_id, agent_name, metric_name, value, timestamp, context)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    str(metric.metric_id),
                    metric.agent_name,
                    metric.metric_name,
                    float(metric.value),
                    metric.timestamp.isoformat(),
                    json.dumps(metric.context) if metric.context else None
                ))
                
                # If this is a model performance metric, update model_performance table
                if metric.context and 'model_id' in metric.context:
                    model_id = metric.context['model_id']
                    is_success = metric.context.get('success', True)
                    
                    # Get current performance data
                    cursor.execute(
                        "SELECT total_interactions, successful_interactions, avg_latency_ms FROM model_performance WHERE model_id = ?",
                        (model_id,)
                    )
                    result = cursor.fetchone()
                    
                    if result is None:
                        # New model
                        total_interactions = 1
                        successful_interactions = 1 if is_success else 0
                        avg_latency_ms = float(metric.value) if metric.metric_name == 'response_time_ms' else 0.0
                    else:
                        total_interactions, successful_interactions, avg_latency_ms = result
                        total_interactions += 1
                        if is_success:
                            successful_interactions += 1
                        
                        # Update average latency if this is a latency metric
                        if metric.metric_name == 'response_time_ms':
                            avg_latency_ms = ((avg_latency_ms * (total_interactions - 1)) + float(metric.value)) / total_interactions
                    
                    # Update model_performance table
                    cursor.execute('''
                        INSERT OR REPLACE INTO model_performance 
                        (model_id, total_interactions, successful_interactions, avg_latency_ms, last_updated)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        model_id,
                        total_interactions,
                        successful_interactions,
                        avg_latency_ms,
                        datetime.now().isoformat()
                    ))
                
                conn.commit()
                conn.close()
            
        except Exception as e:
            logger.error(f"Error storing metric: {str(e)}")
            self.report_error("metric_storage_error", str(e))
    
    def _run_evaluation_scheduler(self):
        """Periodically evaluate models based on collected metrics"""
        while self.running:
            try:
                # Get models that need evaluation
                models_to_evaluate = self._get_models_for_evaluation()
                
                # Evaluate each model
                for model_id in models_to_evaluate:
                    self._evaluate_model(model_id)
                
                # Wait for next evaluation cycle
                time.sleep(300)  # Every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in evaluation scheduler: {str(e)}")
                self.report_error("evaluation_scheduler_error", str(e))
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _get_models_for_evaluation(self):
        """Get list of model IDs that need evaluation"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Get models with recent activity
                cursor.execute('''
                    SELECT model_id FROM model_performance
                    WHERE last_updated > datetime('now', '-1 hour')
                ''')
                
                models = [row[0] for row in cursor.fetchall()]
                conn.close()
                
                return models
                
        except Exception as e:
            logger.error(f"Error getting models for evaluation: {str(e)}")
            return []
    
    def _evaluate_model(self, model_id):
        """Evaluate a model and generate a ModelEvaluationScore"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Get model performance data
                cursor.execute(
                    "SELECT total_interactions, successful_interactions, avg_latency_ms FROM model_performance WHERE model_id = ?",
                    (model_id,)
                )
                result = cursor.fetchone()
                
                if not result:
                    logger.warning(f"No performance data found for model {model_id}")
                    conn.close()
                    return
                
                total_interactions, successful_interactions, avg_latency_ms = result
                
                # Calculate trust score
                if total_interactions > 0:
                    base_score = successful_interactions / total_interactions
                    
                    # Adjust for latency (faster is better)
                    time_factor = max(0, 1 - (avg_latency_ms / 5000.0))  # 5 seconds as max threshold
                    
                    # Combine factors (70% accuracy, 30% speed)
                    trust_score = (base_score * 0.7) + (time_factor * 0.3)
                else:
                    trust_score = 0.5  # Default for new models
                
                # Get previous evaluation for comparison
                cursor.execute(
                    "SELECT trust_score, evaluation_timestamp FROM model_evaluation_scores WHERE model_name = ? ORDER BY evaluation_timestamp DESC LIMIT 1",
                    (model_id,)
                )
                prev_result = cursor.fetchone()
                
                comparison_data = {}
                if prev_result:
                    prev_score, prev_timestamp = prev_result
                    comparison_data = {
                        "previous_score": prev_score,
                        "score_delta": trust_score - prev_score,
                        "previous_evaluation": prev_timestamp
                    }
                
                # Create standardized ModelEvaluationScore
                # Generate a dummy cycle_id since this evaluation isn't tied to a specific training cycle
                dummy_cycle_id = uuid.uuid4()
                
                evaluation = ModelEvaluationScore(
                    model_name=model_id,
                    trust_score=trust_score,
                    avg_latency_ms=avg_latency_ms,
                    comparison_data=comparison_data,
                    cycle_id=dummy_cycle_id
                )
                
                # Store in database
                cursor.execute('''
                    INSERT INTO model_evaluation_scores 
                    (evaluation_id, model_name, trust_score, avg_latency_ms, evaluation_timestamp, comparison_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    str(evaluation.evaluation_id),
                    evaluation.model_name,
                    evaluation.trust_score,
                    evaluation.avg_latency_ms,
                    evaluation.evaluation_timestamp.isoformat(),
                    json.dumps(evaluation.comparison_data) if evaluation.comparison_data else None
                ))
                
                conn.commit()
                conn.close()
                
                logger.info(f"Evaluated model {model_id} with trust score {trust_score:.2f}")
                
        except Exception as e:
            logger.error(f"Error evaluating model {model_id}: {str(e)}")
            self.report_error("model_evaluation_error", str(e))
    
    def _run_cleanup_scheduler(self):
        """Periodically clean up old data"""
        while self.running:
            try:
                with self.db_lock:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    
                    # Delete metrics older than 30 days
                    cursor.execute('''
                        DELETE FROM performance_metrics 
                        WHERE timestamp < datetime('now', '-30 days')
                    ''')
                    
                    # Keep only the last 10 evaluations per model
                    cursor.execute('''
                        DELETE FROM model_evaluation_scores
                        WHERE evaluation_id NOT IN (
                            SELECT evaluation_id FROM model_evaluation_scores
                            GROUP BY model_name
                            ORDER BY evaluation_timestamp DESC
                            LIMIT 10
                        )
                    ''')
                    
                    conn.commit()
                    conn.close()
                
                # Wait 24 hours before next cleanup
                time.sleep(86400)
                
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
                self.report_error("cleanup_error", str(e))
                time.sleep(3600)  # Wait 1 hour before retrying
    
    def _handle_request(self, request):
        """Handle incoming requests"""
        action = request.get("action", "")
        
        if action == "health_check":
            return self._get_health_status()
        elif action == "log_metric":
            return self._handle_log_metric(request)
        elif action == "get_model_evaluation":
            return self._handle_get_model_evaluation(request)
        elif action == "get_model_metrics":
            return self._handle_get_model_metrics(request)
        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}"
            }
    
    def _handle_log_metric(self, request):
        """Handle request to log a performance metric"""
        try:
            metric_data = request.get("metric")
            if not metric_data:
                return {
                    "status": "error",
                    "message": "Missing metric data"
                }
            
            # Process and store the metric
            self._process_metric(metric_data)
            
            return {
                "status": "success",
                "message": "Metric logged successfully"
            }
        except Exception as e:
            logger.error(f"Error handling log_metric request: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _handle_get_model_evaluation(self, request):
        """Handle request to get the latest evaluation for a model"""
        try:
            model_name = request.get("model_name")
            if not model_name:
                return {
                    "status": "error",
                    "message": "Missing model_name"
                }
            
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT evaluation_id, trust_score, accuracy, f1_score, avg_latency_ms, 
                           evaluation_timestamp, comparison_data
                    FROM model_evaluation_scores
                    WHERE model_name = ?
                    ORDER BY evaluation_timestamp DESC
                    LIMIT 1
                ''', (model_name,))
                
                result = cursor.fetchone()
                conn.close()
                
                if not result:
                    return {
                        "status": "error",
                        "message": f"No evaluation found for model {model_name}"
                    }
                
                evaluation_id, trust_score, accuracy, f1_score, avg_latency_ms, timestamp, comparison_data = result
                
                return {
                    "status": "success",
                    "evaluation": {
                        "evaluation_id": evaluation_id,
                        "model_name": model_name,
                        "trust_score": trust_score,
                        "accuracy": accuracy,
                        "f1_score": f1_score,
                        "avg_latency_ms": avg_latency_ms,
                        "evaluation_timestamp": timestamp,
                        "comparison_data": json.loads(comparison_data) if comparison_data else None
                    }
                }
                
        except Exception as e:
            logger.error(f"Error handling get_model_evaluation request: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _handle_get_model_metrics(self, request):
        """Handle request to get performance metrics for a model"""
        try:
            model_name = request.get("model_name")
            limit = request.get("limit", 50)
            
            if not model_name:
                return {
                    "status": "error",
                    "message": "Missing model_name"
                }
            
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT metric_id, metric_name, value, timestamp, context
                    FROM performance_metrics
                    WHERE agent_name = ? OR (context LIKE ? AND context LIKE ?)
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (model_name, '%"model_id"%', f'%{model_name}%', limit))
                
                metrics = []
                for row in cursor.fetchall():
                    metric_id, metric_name, value, timestamp, context = row
                    metrics.append({
                        "metric_id": metric_id,
                        "metric_name": metric_name,
                        "value": value,
                        "timestamp": timestamp,
                        "context": json.loads(context) if context else None
                    })
                
                conn.close()
                
                return {
                    "status": "success",
                    "metrics": metrics
                }
                
        except Exception as e:
            logger.error(f"Error handling get_model_metrics request: {str(e)}")
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
            "metrics_buffer_size": len(self.metrics_buffer),
            "threads": {
                "metrics_processor": self.metrics_processor_thread.is_alive() if self.metrics_processor_thread else False,
                "evaluation": self.evaluation_thread.is_alive() if self.evaluation_thread else False,
                "cleanup": self.cleanup_thread.is_alive() if self.cleanup_thread else False
            },
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
        if self.metrics_processor_thread and self.metrics_processor_thread.is_alive():
            self.metrics_processor_thread.join(timeout=2.0)
        
        if self.evaluation_thread and self.evaluation_thread.is_alive():
            self.evaluation_thread.join(timeout=2.0)
        
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=2.0)
        
        # Close sockets
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
        
        if hasattr(self, 'metrics_sub') and self.metrics_sub:
            self.metrics_sub.close()
        
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
        agent = ModelEvaluationFramework()
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
