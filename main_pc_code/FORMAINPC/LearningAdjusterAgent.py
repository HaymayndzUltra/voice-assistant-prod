"""
Learning Adjuster Agent
Purpose: Manages and optimizes learning parameters for PC2 agents
Features: Learning rate adjustment, parameter optimization, performance monitoring
"""

import zmq
import json
import logging
import sqlite3
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import time
import threading
from typing import Dict, Any
from main_pc_code.src.core.base_agent import BaseAgent

# Add project root to Python path for common_utils import
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import common utilities if available
try:
    from common_utils.zmq_helper import create_socket
import psutil
from datetime import datetime
from main_pc_code.utils.config_parser import parse_agent_args
_agent_args = parse_agent_args()

    USE_COMMON_UTILS = True
except ImportError:
    USE_COMMON_UTILS = False

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/learning_adjuster.log'
)
logger = logging.getLogger(__name__)

class ParameterType(Enum):
    LEARNING_RATE = "learning_rate"
    BATCH_SIZE = "batch_size"
    OPTIMIZER = "optimizer"
    REGULARIZATION = "regularization"
    CUSTOM = "custom"

@dataclass
class ParameterConfig:
    name: str
    type: ParameterType
    min_value: float
    max_value: float
    current_value: float
    step_size: float
    description: str
    metadata: Optional[Dict] = None

def __init__(self, port: int = None, name: str = None, **kwargs):
    agent_port = _agent_args.get('port', 5000) if port is None else port
    agent_name = _agent_args.get('name', 'LearningAdjusterAgent') if name is None else name
    super().__init__(port=agent_port, name=agent_name)
    def __init__(self, port: int = 5643):
        """Initialize the Learning Adjuster Agent."""
        # Call BaseAgent's __init__ first
        super().__init__(name="LearningAdjusterAgent", port=port)
        
        # ZMQ setup
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        
        # Health status
        self.health_status = {
            "status": "ok",
            "service": "learning_adjuster_agent",
            "port": self.port,
            "active_parameters": 0,
            "database_status": "ok"
        }
        
        # Database setup
        self.db_path = "data/learning_adjuster.db"
        self._init_db()
        
        # Parameter tracking
        self.parameter_history = {}
        self.performance_metrics = {}
        
        # Optimization settings
        self.optimization_window = 100  # Number of iterations to consider
        self.improvement_threshold = 0.01  # Minimum improvement to consider
        
        logger.info(f"Learning Adjuster Agent initialized on port {self.port}")

    def _init_db(self):
        """Initialize the SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Create tables
            c.execute('''
                CREATE TABLE IF NOT EXISTS parameter_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parameter_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    performance_metric REAL,
                    metadata TEXT
                )
            ''')
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS parameter_configs (
                    name TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    min_value REAL NOT NULL,
                    max_value REAL NOT NULL,
                    current_value REAL NOT NULL,
                    step_size REAL NOT NULL,
                    description TEXT,
                    metadata TEXT
                )
            ''')
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    parameters TEXT,
                    metadata TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            self.health_status["database_status"] = "ok"
            logger.info("Database initialized successfully")
        except Exception as e:
            self.health_status["database_status"] = "error"
            logger.error(f"Database initialization error: {e}")

    def _update_health_status(self):
        """Update health status with current information."""
        try:
            # Update active parameters count
            active_params = len(self._get_active_parameters())
            self.health_status.update({
                "last_check": time.time(),
                "active_parameters": active_params,
                "uptime": time.time() - self.start_time
            })
        except Exception as e:
            logger.error(f"Error updating health status: {e}")

    def register_parameter(self, config: ParameterConfig) -> bool:
        """Register a new parameter for adjustment."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''
                INSERT OR REPLACE INTO parameter_configs 
                (name, type, min_value, max_value, current_value, step_size, description, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                config.name,
                config.type.value,
                config.min_value,
                config.max_value,
                config.current_value,
                config.step_size,
                config.description,
                json.dumps(config.metadata or {})
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Registered parameter: {config.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering parameter: {e}")
            return False

    def adjust_parameter(self, parameter_name: str, new_value: float) -> bool:
        """Adjust a parameter's value."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Get current config
            c.execute('SELECT * FROM parameter_configs WHERE name = ?', (parameter_name,))
            config = c.fetchone()
            
            if not config:
                raise ValueError(f"Parameter {parameter_name} not found")
            
            # Validate new value
            if not (config[2] <= new_value <= config[3]):
                raise ValueError(f"New value {new_value} outside valid range [{config[2]}, {config[3]}]")
            
            # Update value
            c.execute('''
                UPDATE parameter_configs 
                SET current_value = ? 
                WHERE name = ?
            ''', (new_value, parameter_name))
            
            # Record in history
            c.execute('''
                INSERT INTO parameter_history 
                (parameter_name, value, timestamp)
                VALUES (?, ?, ?)
            ''', (parameter_name, new_value, datetime.now()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Adjusted parameter {parameter_name} to {new_value}")
            return True
            
        except Exception as e:
            logger.error(f"Error adjusting parameter: {e}")
            return False

    def record_performance(self, metric_name: str, value: float, parameters: Optional[Dict] = None) -> bool:
        """Record a performance metric."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''
                INSERT INTO performance_metrics 
                (metric_name, value, parameters, metadata)
                VALUES (?, ?, ?, ?)
            ''', (
                metric_name,
                value,
                json.dumps(parameters or {}),
                json.dumps({"timestamp": datetime.now().isoformat()})
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Recorded performance metric: {metric_name} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording performance: {e}")
            return False

    def optimize_parameters(self, metric_name: str) -> Dict:
        """Optimize parameters based on performance metrics."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Get recent performance history
            c.execute('''
                SELECT value, parameters, timestamp 
                FROM performance_metrics 
                WHERE metric_name = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (metric_name, self.optimization_window))
            
            history = c.fetchall()
            
            if not history:
                return {"status": "error", "message": "No performance history available"}
            
            # Analyze trends and suggest adjustments
            adjustments = {}
            for param_name in self._get_active_parameters():
                trend = self._analyze_parameter_trend(param_name, history)
                if trend:
                    adjustments[param_name] = trend
            
            conn.close()
            
            logger.info(f"Generated parameter adjustments: {adjustments}")
            return {
                "status": "success",
                "adjustments": adjustments
            }
            
        except Exception as e:
            logger.error(f"Error optimizing parameters: {e}")
            return {"status": "error", "message": str(e)}

    def _get_active_parameters(self) -> List[str]:
        """Get list of currently active parameters."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('SELECT name FROM parameter_configs')
            parameters = [row[0] for row in c.fetchall()]
            
            conn.close()
            return parameters
        except Exception as e:
            logger.error(f"Error getting active parameters: {e}")
            return []

    def _analyze_parameter_trend(self, parameter_name: str, history: List) -> Optional[Dict]:
        """Analyze trend for a parameter and suggest adjustment."""
        try:
            # Extract parameter values and performance metrics
            param_values = []
            performances = []
            
            for perf, params, _ in history:
                if params and parameter_name in params:
                    param_values.append(params[parameter_name])
                    performances.append(perf)
            
            if len(param_values) < 2:
                return None
            
            # Calculate correlation
            correlation = np.corrcoef(param_values, performances)[0, 1]
            
            # Get current config
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('SELECT * FROM parameter_configs WHERE name = ?', (parameter_name,))
            config = c.fetchone()
            conn.close()
            
            if not config:
                return None
            
            # Suggest adjustment based on correlation
            current_value = config[4]
            step_size = config[5]
            
            if abs(correlation) < 0.1:
                return None  # No clear trend
                
            adjustment = step_size if correlation > 0 else -step_size
            new_value = current_value + adjustment
            
            # Ensure within bounds
            new_value = max(config[2], min(config[3], new_value))
            
            return {
                "current_value": current_value,
                "suggested_value": new_value,
                "correlation": correlation,
                "confidence": abs(correlation)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing parameter trend: {e}")
            return None

    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        # Get base status from parent class
        base_status = super()._get_health_status()
        
        # Update health status with current information
        self._update_health_status()
        
        # Add LearningAdjuster-specific metrics
        base_status.update({
            "service": "learning_adjuster_agent",
            "active_parameters": self.health_status["active_parameters"],
            "database_status": self.health_status["database_status"]
        })
        
        return base_status

    def handle_request(self, request: Dict) -> Dict:
        """Handle incoming requests."""
        try:
            action = request.get("action")
            
            # Update health status
            self._update_health_status()
            
            if action == "health_check":
                return self._get_health_status()
            
            elif action == "register_parameter":
                config = ParameterConfig(**request["config"])
                success = self.register_parameter(config)
                return {"status": "success" if success else "error"}
                
            elif action == "adjust_parameter":
                success = self.adjust_parameter(
                    request["parameter_name"],
                    request["new_value"]
                )
                return {"status": "success" if success else "error"}
                
            elif action == "record_performance":
                success = self.record_performance(
                    request["metric_name"],
                    request["value"],
                    request.get("parameters")
                )
                return {"status": "success" if success else "error"}
                
            elif action == "optimize_parameters":
                return self.optimize_parameters(request["metric_name"])
                
            else:
                return {"status": "error", "message": "Unknown action"}
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {"status": "error", "message": str(e)}

    def run(self):
        """Run the agent's main loop."""
        logger.info(f"Starting Learning Adjuster Agent on port {self.port}")
        
        poll_timeout_ms = 1000  # 1 second
        while self.running:
            try:
                # Wait (non-blocking) for a request
                if self.socket.poll(timeout=poll_timeout_ms) == 0:
                    # No message ready; continue loop to keep checking running flag
                    continue

                # Receive request
                try:
                    request_raw = self.socket.recv_string(flags=0)
                except zmq.error.Again:
                    # recv timed out – safe to continue
                    continue

                # Decode JSON
                try:
                    request = json.loads(request_raw)
                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON: {request_raw}")
                    self.socket.send_string(json.dumps({
                        "status": "error",
                        "message": "Invalid JSON"
                    }))
                    continue

                # Process request
                response = self.handle_request(request)

                # Send response
                self.socket.send_string(json.dumps(response))

            except zmq.error.Again:
                # General ZMQ timeout; ignore and loop
                continue
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                try:
                    self.socket.send_string(json.dumps({
                        "status": "error",
                        "message": str(e)
                    }))
                except Exception:
                    pass

    def cleanup(self):
        """Stop the agent and clean up resources."""
        logger.info("Stopping Learning Adjuster Agent")
        
        # Call parent cleanup to handle BaseAgent resources
        super().cleanup()
        
        logger.info("Learning Adjuster Agent stopped")


    def health_check(self):
        '''
        Performs a health check on the agent, returning a dictionary with its status.
        '''
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
            # TODO: Add agent-specific health checks here.
            # For example, check if a required connection is alive.
            # if not self.some_service_connection.is_alive():
            #     is_healthy = False

            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else -1,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {} # Placeholder for agent-specific data
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "error": f"Health check failed with exception: {str(e)}"
            }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Learning Adjuster Agent")
    parser.add_argument("--port", type=int, default=5643, help="Port to bind to")
    args = parser.parse_args()
    
    agent = LearningAdjusterAgent(port=args.port)
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.cleanup() 