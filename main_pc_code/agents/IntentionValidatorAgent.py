"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

Intention Validator Agent
- Validates user intentions and commands
- Maintains validation history
- Implements security checks
"""

import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
MAIN_PC_CODE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if MAIN_PC_CODE not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE)

import zmq
import json
import time
import logging
import sqlite3
import threading
from datetime import datetime
from typing import Dict, Any, List, Set, Tuple

from common.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config

# Parse command line arguments
config = load_config()

# Configure logging
log_dir = os.path.join(MAIN_PC_CODE, 'logs')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'intention_validator.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IntentionValidatorAgent(BaseAgent):
    def __init__(self, port: int = None, name: str = None, host="localhost", request_coordinator_host=None, request_coordinator_port=None, **kwargs):
        """Initialize the IntentionValidatorAgent.
        
        Args:
            port: Port to bind to (default from _agent_args or 5572)
            name: Agent name (default from _agent_args or "IntentionValidator")
            host: Host to bind to (default: localhost)
            request_coordinator_host: RequestCoordinator host (default: localhost)
            request_coordinator_port: RequestCoordinator port (default: 5570)
        """
        self.initialization_status = {
            "is_initialized": False,
            "error": None,
            "progress": 0.0
        }
        
        # Get port and name from _agent_args with fallbacks
        agent_port = config.get("port", 5572) if port is None else port
        agent_name = config.get("name", 'IntentionValidator') if name is None else name
        agent_port = config.get("port", 5000) if port is None else port
        agent_name = config.get("name", 'IntentionValidatorAgent') if name is None else name
        super().__init__(port=agent_port, name=agent_name)
        
        # Get RequestCoordinator connection details from command line args (lowercase)
        self.request_coordinator_host = request_coordinator_host or config.get("request_coordinator_host", None) or "localhost"
        self.request_coordinator_port = request_coordinator_port or config.get("request_coordinator_port", None) or 5570
        
        # Also check for uppercase variant for backward compatibility
        if hasattr(_agent_args, 'RequestCoordinator_host') and self.request_coordinator_host == "localhost":
            self.request_coordinator_host = config.get("RequestCoordinator_host")
        if hasattr(_agent_args, 'RequestCoordinator_port') and self.request_coordinator_port == 5570:
            self.request_coordinator_port = config.get("RequestCoordinator_port")
            
        self.db_path = os.path.join(MAIN_PC_CODE, "data", "intention_validation.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.sensitive_commands = {
            'delete_file': ['file_path'],
            'modify_system': ['component', 'action'],
            'access_credentials': ['service', 'action'],
            'execute_system_command': ['command', 'parameters'],
            'modify_permissions': ['user', 'permission'],
            'access_sensitive_data': ['data_type', 'purpose']
        }
        
        # Set start time for health status
        self.start_time = time.time()
        self.running = True
        
        # Start initialization in background
        threading.Thread(target=self._perform_initialization, daemon=True).start()
        logger.info(f"IntentionValidatorAgent initialized on port {self.port}")
        
    def _perform_initialization(self):
        """Perform agent initialization in background."""
        try:
            self._init_database()
            self.initialization_status.update({
                "is_initialized": True,
                "progress": 1.0
            })
            logger.info("IntentionValidator initialization complete")
        except Exception as e:
            self.initialization_status.update({
                "error": str(e),
                "progress": 0.0
            })
            logger.error(f"Initialization error: {e}")
            
    def _init_database(self):
        """Initialize SQLite database for validation history."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS validation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT,
                    parameters TEXT,
                    user_id TEXT,
                    profile TEXT,
                    validation_result BOOLEAN,
                    reason TEXT,
                    timestamp TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS command_patterns (
                    command TEXT PRIMARY KEY,
                    required_params TEXT,
                    risk_level INTEGER,
                    description TEXT
                )
            ''')
            
            # Insert default command patterns
            default_patterns = [
                ('delete_file', '["file_path"]', 3, 'File deletion operation'),
                ('modify_system', '["component", "action"]', 4, 'System modification'),
                ('access_credentials', '["service", "action"]', 5, 'Credential access'),
                ('execute_system_command', '["command", "parameters"]', 4, 'System command execution'),
                ('modify_permissions', '["user", "permission"]', 5, 'Permission modification'),
                ('access_sensitive_data', '["data_type", "purpose"]', 4, 'Sensitive data access')
            ]
            
            cursor.executemany('''
                INSERT OR REPLACE INTO command_patterns 
                (command, required_params, risk_level, description)
                VALUES (?, ?, ?, ?)
            ''', default_patterns)
            
            conn.commit()
            conn.close()
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
        
    def _get_health_status(self) -> dict:
        """Get detailed health status."""
        status = super()._get_health_status()
        
        # Add agent-specific metrics
        status["initialization_status"] = self.initialization_status
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get validation history count
            cursor.execute("SELECT COUNT(*) FROM validation_history")
            history_count = cursor.fetchone()[0]
            
            # Get recent validation success rate
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN validation_result = 1 THEN 1 ELSE 0 END) as successful
                FROM validation_history 
                WHERE timestamp > datetime('now', '-1 hour')
            """)
            total, successful = cursor.fetchone()
            success_rate = (successful / total * 100) if total > 0 else 0
            
            conn.close()
            
            status.update({
                "validation_history_count": history_count,
                "recent_success_rate": f"{success_rate:.1f}%",
                "sensitive_commands": list(self.sensitive_commands.keys())
            })
            
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            status.update({
                "validation_history_count": -1,
                "recent_success_rate": "unknown",
                "sensitive_commands": list(self.sensitive_commands.keys())
            })
        
        return status
        
    def handle_request(self, request: dict) -> dict:
        """Handle incoming validation requests."""
        action = request.get('action')
        
        if action == 'validate_command':
            command = request.get('command')
            parameters = request.get('parameters', {})
            user_id = request.get('user_id')
            profile = request.get('profile')
            
            # Ensure required fields are present and not None
            if not isinstance(command, str) or not isinstance(user_id, str) or not isinstance(profile, str):
                return {
                    'status': 'error',
                    'message': 'Missing or invalid required fields: command, user_id, profile'
                }
            
            # Validate command structure
            structure_valid, structure_reason = self._validate_command_structure(command, parameters)
            if not structure_valid:
                self._log_validation(command, parameters, user_id, profile, False, structure_reason)
                return {
                    'status': 'error',
                    'message': structure_reason
                }
            
            # Check command history
            history_valid, history_reason = self._check_command_history(command, user_id, profile)
            if not history_valid:
                self._log_validation(command, parameters, user_id, profile, False, history_reason)
                return {
                    'status': 'error',
                    'message': history_reason
                }
            
            # Log successful validation
            self._log_validation(command, parameters, user_id, profile, True, "Validation successful")
            
            return {
                'status': 'ok',
                'message': 'Command validated successfully'
            }
            
        elif action == 'get_validation_history':
            user_id = request.get('user_id')
            profile = request.get('profile')
            limit = request.get('limit', 10)
            
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                if user_id and profile:
                    cursor.execute('''
                        SELECT command, parameters, validation_result, reason, timestamp 
                        FROM validation_history 
                        WHERE user_id = ? AND profile = ? 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (user_id, profile, limit))
                else:
                    cursor.execute('''
                        SELECT command, parameters, validation_result, reason, timestamp 
                        FROM validation_history 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (limit,))
                
                history = cursor.fetchall()
                conn.close()
                
                return {
                    'status': 'ok',
                    'history': [
                        {
                            'command': cmd,
                            'parameters': json.loads(params),
                            'result': bool(result),
                            'reason': reason,
                            'timestamp': ts
                        }
                        for cmd, params, result, reason, ts in history
                    ]
                }
                
            except Exception as e:
                logger.error(f"Error getting validation history: {e}")
                return {
                    'status': 'error',
                    'message': f'Failed to get validation history: {str(e)}'
                }
            
        return super().handle_request(request)
    
    def _validate_command_structure(self, command: str, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate command structure and required parameters."""
        if command not in self.sensitive_commands:
            return False, f"Unknown sensitive command: {command}"
        
        required_params = self.sensitive_commands[command]
        missing_params = [param for param in required_params if param not in parameters]
        
        if missing_params:
            return False, f"Missing required parameters: {', '.join(missing_params)}"
        
        return True, "Command structure valid"
    
    def _check_command_history(self, command: str, user_id: str, profile: str) -> Tuple[bool, str]:
        """Check command history for suspicious patterns."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get recent command history
            cursor.execute('''
                SELECT COUNT(*) 
                FROM validation_history 
                WHERE command = ? AND user_id = ? AND profile = ? 
                AND timestamp > datetime('now', '-1 hour')
            ''', (command, user_id, profile))
            
            recent_count = cursor.fetchone()[0]
            
            # Get failure rate
            cursor.execute('''
                SELECT COUNT(*) 
                FROM validation_history 
                WHERE command = ? AND user_id = ? AND profile = ? 
                AND validation_result = 0
                AND timestamp > datetime('now', '-24 hours')
            ''', (command, user_id, profile))
            
            failure_count = cursor.fetchone()[0]
            
            conn.close()
            
            if recent_count > 10:  # More than 10 attempts in the last hour
                return False, "Too many recent attempts"
            
            if failure_count > 5:  # More than 5 failures in the last 24 hours
                return False, "High failure rate in recent history"
            
            return True, "Command history acceptable"
            
        except Exception as e:
            logger.error(f"Error checking command history: {e}")
            return False, f"Error checking command history: {str(e)}"
    
    def _log_validation(self, command: str, parameters: Dict[str, Any], 
                       user_id: str, profile: str, result: bool, reason: str):
        """Log validation result."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO validation_history 
                (command, parameters, user_id, profile, validation_result, reason, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                command,
                json.dumps(parameters),
                user_id,
                profile,
                result,
                reason,
                datetime.now()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error logging validation: {e}")


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
    # Standardized main execution block
    agent = None
    try:
        # Replace 'ClassName' with the actual agent class from the file.
        agent = IntentionValidatorAgent()
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