from main_pc_code.src.core.base_agent import BaseAgent
import zmq
import json
import time
import logging
import sqlite3
from datetime import datetime
from typing import Dict, Any
import psutil
from datetime import datetime

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(PathManager.get_logs_dir() / "security_policy.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SecurityPolicyAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="Securitypolicyagent")
        """Initialize the SecurityPolicyAgent with ZMQ socket and database."""
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://*:{port}")
        
        # Initialize database
        self.db_path = str(PathManager.get_data_dir() / "security_policy.db")
        self._init_database()
        
        logger.info(f"SecurityPolicyAgent initialized on port {port}")
    
    def _init_database(self):
        """Initialize SQLite database for security policies."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                profile_id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS permissions (
                permission_id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id TEXT,
                command TEXT,
                allowed BOOLEAN,
                conditions TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES profiles(profile_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id TEXT,
                command TEXT,
                parameters TEXT,
                allowed BOOLEAN,
                reason TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES profiles(profile_id)
            )
        ''')
        
        # Insert default profiles
        default_profiles = [
            ('admin', 'Administrator', 'Full system access', datetime.now(), datetime.now()),
            ('guest', 'Guest User', 'Limited access', datetime.now(), datetime.now()),
            ('standard', 'Standard User', 'Normal access', datetime.now(), datetime.now())
        ]
        
        cursor.executemany('''
            INSERT OR REPLACE INTO profiles 
            (profile_id, name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', default_profiles)
        
        # Insert default permissions
        default_permissions = [
            # Admin permissions
            ('admin', 'delete_file', True, '{"require_confirmation": true}'),
            ('admin', 'modify_system', True, '{"require_confirmation": true}'),
            ('admin', 'access_credentials', True, '{"require_confirmation": true}'),
            ('admin', 'execute_system_command', True, '{"require_confirmation": true}'),
            ('admin', 'modify_permissions', True, '{"require_confirmation": true}'),
            ('admin', 'access_sensitive_data', True, '{"require_confirmation": true}'),
            
            # Guest permissions
            ('guest', 'delete_file', False, '{}'),
            ('guest', 'modify_system', False, '{}'),
            ('guest', 'access_credentials', False, '{}'),
            ('guest', 'execute_system_command', False, '{}'),
            ('guest', 'modify_permissions', False, '{}'),
            ('guest', 'access_sensitive_data', False, '{}'),
            
            # Standard user permissions
            ('standard', 'delete_file', True, '{"require_confirmation": true, "restricted_paths": true}'),
            ('standard', 'modify_system', False, '{}'),
            ('standard', 'access_credentials', False, '{}'),
            ('standard', 'execute_system_command', True, '{"restricted_commands": true}'),
            ('standard', 'modify_permissions', False, '{}'),
            ('standard', 'access_sensitive_data', True, '{"require_confirmation": true, "restricted_data": true}')
        ]
        
        cursor.executemany('''
            INSERT OR REPLACE INTO permissions 
            (profile_id, command, allowed, conditions)
            VALUES (?, ?, ?, ?)
        ''', default_permissions)
        
        conn.commit()
        conn.close()
    
    def _check_permission(self, profile_id: str, command: str, parameters: Dict[str, Any]) -> tuple[bool, str]:
        """Check if a profile has permission to execute a command."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get permission
        cursor.execute('''
            SELECT allowed, conditions 
            FROM permissions 
            WHERE profile_id = ? AND command = ?
        ''', (profile_id, command))
        
        result = cursor.fetchone()
        
        if result is None:
            conn.close()
            return False, f"No permission defined for command: {command}"
        
        allowed, conditions = result
        conditions = json.loads(conditions)
        
        # Check conditions
        if conditions.get('require_confirmation'):
            # This would typically check with IntentionValidatorAgent
            pass
        
        if conditions.get('restricted_paths') and 'file_path' in parameters:
            # Check if path is in restricted list
            restricted_paths = ['/system/', '/config/', '/credentials/']
            if any(path in parameters['file_path'] for path in restricted_paths):
                conn.close()
                return False, "Access to restricted path denied"
        
        if conditions.get('restricted_commands') and 'command' in parameters:
            # Check if command is in restricted list
            restricted_commands = ['rm -rf', 'format', 'dd']
            if any(cmd in parameters['command'] for cmd in restricted_commands):
                conn.close()
                return False, "Restricted command denied"
        
        if conditions.get('restricted_data') and 'data_type' in parameters:
            # Check if data type is in restricted list
            restricted_data = ['passwords', 'keys', 'tokens']
            if parameters['data_type'] in restricted_data:
                conn.close()
                return False, "Access to restricted data denied"
        
        conn.close()
        return allowed, "Permission check completed"
    
    def _log_access(self, profile_id: str, command: str, parameters: Dict[str, Any], 
                    allowed: bool, reason: str):
        """Log access attempt."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO access_logs 
            (profile_id, command, parameters, allowed, reason, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            profile_id,
            command,
            json.dumps(parameters),
            allowed,
            reason,
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action')
        
        if action == 'check_permission':
            profile_id = request['profile_id']
            command = request['command']
            parameters = request.get('parameters', {})
            
            allowed, reason = self._check_permission(profile_id, command, parameters)
            self._log_access(profile_id, command, parameters, allowed, reason)
            
            return {
                'status': 'success',
                'allowed': allowed,
                'reason': reason
            }
            
        elif action == 'get_profile_permissions':
            profile_id = request['profile_id']
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT command, allowed, conditions 
                FROM permissions 
                WHERE profile_id = ?
            ''', (profile_id,))
            
            permissions = cursor.fetchall()
            conn.close()
            
            return {
                'status': 'success',
                'permissions': [
                    {
                        'command': cmd,
                        'allowed': bool(allowed),
                        'conditions': json.loads(conditions)
                    }
                    for cmd, allowed, conditions in permissions
                ]
            }
            
        elif action == 'get_access_logs':
            profile_id = request.get('profile_id')
            limit = request.get('limit', 10)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if profile_id:
                cursor.execute('''
                    SELECT command, parameters, allowed, reason, timestamp 
                    FROM access_logs 
                    WHERE profile_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (profile_id, limit))
            else:
                cursor.execute('''
                    SELECT command, parameters, allowed, reason, timestamp 
                    FROM access_logs 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
            
            logs = cursor.fetchall()
            conn.close()
            
            return {
                'status': 'success',
                'logs': [
                    {
                        'command': cmd,
                        'parameters': json.loads(params),
                        'allowed': bool(allowed),
                        'reason': reason,
                        'timestamp': ts
                    }
                    for cmd, params, allowed, reason, ts in logs
                ]
            }
            
        else:
            return {
                'status': 'error',
                'message': f'Unknown action: {action}'
            }
    
    def run(self):
        """Main loop for handling requests."""
        logger.info("SecurityPolicyAgent started")
        
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

if __name__ == '__main__':
    policy_agent = SecurityPolicyAgent()
    policy_agent.run() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise