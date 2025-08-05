"""
Authentication Agent
- Handles user authentication and authorization
- Manages user sessions and tokens
- Provides secure login/logout functionality
"""
from common.config_manager import get_service_ip, get_service_url, get_redis_url
import zmq
import json
import logging
from pathlib import Path
import threading
import time
import hashlib
import os
import sys
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

# ✅ MODERNIZED: Path management using standardized PathManager (consolidated)
from common.utils.path_manager import PathManager

# Add project root to path using PathManager (single setup)
PROJECT_ROOT = PathManager.get_project_root()
if str(PROJECT_ROOT) not in sys.path:
    

# Import config module
try:
    from common.core.base_agent import BaseAgent
    from pc2_code.agents.utils.config_loader import Config
    config = Config().get_config()
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback if config not available
    config = None

# Configure logging
log_directory = os.path.join('logs')
os.makedirs(log_directory, exist_ok=True)
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('AuthenticationAgent')

# Load configuration at the module level
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
            "main_pc_ip": get_mainpc_ip()),
            "pc2_ip": get_pc2_ip()),
            "bind_address": os.environ.get("BIND_ADDRESS", "0.0.0.0"),
            "secure_zmq": False,
            "ports": {
                "auth_agent": int(os.environ.get("AUTH_PORT", 7116)),
                "auth_health": int(os.environ.get("AUTH_HEALTH_PORT", 8116))
            }
        }

# Load network configuration
network_config = load_network_config()

# Get configuration values
MAIN_PC_IP = get_mainpc_ip()))
PC2_IP = network_config.get("pc2_ip", get_pc2_ip()))
BIND_ADDRESS = network_config.get("bind_address", os.environ.get("BIND_ADDRESS", "0.0.0.0"))
AUTH_PORT = network_config.get("ports", {}).get("auth_agent", int(os.environ.get("AUTH_PORT", 7116)))
AUTH_HEALTH_PORT = network_config.get("ports", {}).get("auth_health", int(os.environ.get("AUTH_HEALTH_PORT", 8116)))
ERROR_BUS_PORT = int(os.environ.get("ERROR_BUS_PORT", 7150))

class AuthenticationAgent(BaseAgent):
    """Authentication Agent for system-wide authentication and authorization."""
    
    def __init__(self, port: int = None, health_check_port: int = None, **kwargs):
        # Initialize agent state before BaseAgent
        self.users = {}
        self.sessions = {}
        self.token_expiry = timedelta(hours=24)
        self.request_count = 0
        self.main_pc_connections = {}
        self.running = True
        self.start_time = time.time()
        
        # Initialize BaseAgent with proper name and port
        super().__init__(
            name="AuthenticationAgent", 
            port=port if port is not None else AUTH_PORT,
            health_check_port=health_check_port if health_check_port is not None else AUTH_HEALTH_PORT,
            **kwargs
        )
        
        # Start session cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_sessions_loop)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        
        # Set up error reporting
        self.setup_error_reporting()
        
        logger.info(f"Authentication Agent initialized on port {self.port}")

    def setup_error_reporting(self):
        """Set up error reporting to the central Error Bus."""
        try:
            self.error_bus_host = PC2_IP
            self.error_bus_port = ERROR_BUS_PORT
            self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
            self.error_bus_pub = self.context.socket(zmq.PUB)
            self.error_bus_pub.connect(self.error_bus_endpoint)
            logger.info(f"Connected to Error Bus at {self.error_bus_endpoint}")
        except Exception as e:
            logger.error(f"Failed to set up error reporting: {e}")
    
    def report_error(self, error_type, message, severity="ERROR"):
        """Report an error to the central Error Bus."""
        try:
            if hasattr(self, 'error_bus_pub'):
                error_report = {
                    "timestamp": datetime.now().isoformat(),
                    "agent": self.name,
                    "type": error_type,
                    "message": message,
                    "severity": severity
                }
                self.error_bus_pub.send_multipart([
                    b"ERROR",
                    json.dumps(error_report).encode('utf-8')
                ])
                logger.info(f"Reported error: {error_type} - {message}")
        except Exception as e:
            logger.error(f"Failed to report error: {e}")
    
    def _cleanup_sessions_loop(self):
        """Background thread for cleaning up expired sessions."""
        while self.running:
            try:
                self._cleanup_expired_sessions()
                time.sleep(300)  # Clean up every 5 minutes
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                self.report_error("CLEANUP_ERROR", f"Error in session cleanup: {e}")
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions."""
        current_time = datetime.now()
        expired_sessions = [
            token for token, session in self.sessions.items()
            if current_time > session['expires_at']
        ]
        for token in expired_sessions:
            del self.sessions[token]
            logger.info(f"Cleaned up expired session: {token}")
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _generate_token(self) -> str:
        """Generate a random session token."""
        return os.urandom(32).hex()
    
    def _create_session(self, user_id: str) -> Dict[str, Any]:
        """Create a new session for a user."""
        token = self._generate_token()
        expires_at = datetime.now() + self.token_expiry
        
        session = {
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'expires_at': expires_at,
            'last_activity': datetime.now().isoformat()
        }
        
        self.sessions[token] = session
        return {'token': token, 'expires_at': expires_at.isoformat()}
    
    def _validate_token(self, token: str) -> bool:
        """Validate a session token."""
        if token not in self.sessions:
            return False
        
        session = self.sessions[token]
        if datetime.now() > session['expires_at']:
            del self.sessions[token]
            return False
        
        # Update last activity
        session['last_activity'] = datetime.now().isoformat()
        return True
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action', '')
        
        if action == 'register':
            return self._handle_registration(request)
        elif action == 'login':
            return self._handle_login(request)
        elif action == 'logout':
            return self._handle_logout(request)
        elif action == 'validate_token':
            return self._handle_token_validation(request)
        elif action == 'health_check':
            return self._get_health_status()
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}
    
    def _handle_registration(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user registration."""
        try:
            user_id = request.get('user_id')
            password = request.get('password')
            
            if not user_id or not password:
                return {'status': 'error', 'message': 'Missing user_id or password'}
            
            if user_id in self.users:
                return {'status': 'error', 'message': 'User already exists'}
            
            self.users[user_id] = {
                'password_hash': self._hash_password(password),
                'created_at': datetime.now().isoformat(),
                'last_login': None
            }
            
            return {'status': 'success', 'message': 'User registered successfully'}
        except Exception as e:
            logger.error(f"Error handling registration: {e}")
            self.report_error("REGISTRATION_ERROR", str(e))
            return {'status': 'error', 'message': str(e)}
    
    def _handle_login(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user login."""
        try:
            user_id = request.get('user_id')
            password = request.get('password')
            
            if not user_id or not password:
                return {'status': 'error', 'message': 'Missing user_id or password'}
            
            if user_id not in self.users:
                return {'status': 'error', 'message': 'User not found'}
            
            user = self.users[user_id]
            if user['password_hash'] != self._hash_password(password):
                return {'status': 'error', 'message': 'Invalid password'}
            
            # Update last login
            user['last_login'] = datetime.now().isoformat()
            
            # Create session
            session = self._create_session(user_id)
            
            return {
                'status': 'success',
                'message': 'Login successful',
                'session': session
            }
        except Exception as e:
            logger.error(f"Error handling login: {e}")
            self.report_error("LOGIN_ERROR", str(e))
            return {'status': 'error', 'message': str(e)}
    
    def _handle_logout(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user logout."""
        try:
            token = request.get('token')
            
            if not token:
                return {'status': 'error', 'message': 'Missing token'}
            
            if token in self.sessions:
                del self.sessions[token]
                return {'status': 'success', 'message': 'Logout successful'}
            else:
                return {'status': 'error', 'message': 'Invalid token'}
        except Exception as e:
            logger.error(f"Error handling logout: {e}")
            self.report_error("LOGOUT_ERROR", str(e))
            return {'status': 'error', 'message': str(e)}
    
    def _handle_token_validation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle token validation."""
        try:
            token = request.get('token')
            
            if not token:
                return {'status': 'error', 'message': 'Missing token'}
            
            valid = self._validate_token(token)
            
            if valid:
                return {'status': 'success', 'valid': True}
            else:
                return {'status': 'success', 'valid': False}
        except Exception as e:
            logger.error(f"Error handling token validation: {e}")
            self.report_error("TOKEN_VALIDATION_ERROR", str(e))
            return {'status': 'error', 'message': str(e)}
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        # Call the parent class implementation first
        status = super()._get_health_status()
        
        # Add agent-specific health information
        status.update({
            "status": "ok",
            "agent_type": "authentication",
            "active_sessions": len(self.sessions),
            "registered_users": len(self.users),
            "cleanup_thread_alive": self.cleanup_thread.is_alive() if hasattr(self, 'cleanup_thread') else False,
            "uptime_seconds": time.time() - self.start_time
        })
        
        return status
    
    def run(self):
        """Main run loop."""
        logger.info(f"Authentication Agent starting on port {self.port}")
        
        try:
            while self.running:
                try:
                    # Use non-blocking recv with timeout
                    if self.socket.poll(timeout=1000) != 0:  # 1 second timeout
                        message = self.socket.recv_json()
                        logger.debug(f"Received message: {message}")
                        
                        # Process message
                        response = self.handle_request(message)
                        
                        # Send response
                        self.socket.send_json(response)
                        self.request_count += 1
                        
                except zmq.error.ZMQError as e:
                    logger.error(f"ZMQ error: {e}")
                    self.report_error("ZMQ_ERROR", str(e))
                    time.sleep(1)  # Sleep to avoid tight loop on error
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    self.report_error("PROCESSING_ERROR", str(e))
                    # Try to send error response
                    try:
                        self.socket.send_json({
                            'status': 'error',
                            'message': f'Internal server error: {str(e)}'
                        })
                    except:
                        pass
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("Authentication Agent interrupted")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up Authentication Agent resources")
        self.running = False
        
        # Close ZMQ sockets
        if hasattr(self, 'socket'):
            try:
                self.socket.close()
                logger.info("Closed main socket")
            except Exception as e:
                logger.error(f"Error closing main socket: {e}")
        
        # Close error bus socket
        if hasattr(self, 'error_bus_pub'):
            try:
                self.error_bus_pub.close()
                logger.info("Closed error bus socket")
            except Exception as e:
                logger.error(f"Error closing error bus socket: {e}")
        
        # Close any connections to other services
        for service_name, socket in self.main_pc_connections.items():
            try:
                socket.close()
                logger.info(f"Closed connection to {service_name}")
            except Exception as e:
                logger.error(f"Error closing connection to {service_name}: {e}")
        
        # Join threads
        if hasattr(self, 'cleanup_thread'):
            try:
                self.cleanup_thread.join(timeout=2.0)
                logger.info("Joined cleanup thread")
            except Exception as e:
                logger.error(f"Error joining cleanup thread: {e}")
        
        # Call parent cleanup
        try:
            super().cleanup()
            logger.info("Called parent cleanup")
        except Exception as e:
            logger.error(f"Error in parent cleanup: {e}")
        
        logger.info("Authentication Agent cleanup complete")
    
    def stop(self):
        """Stop the agent."""
        self.running = False
        
    def connect_to_main_pc_service(self, service_name: str):
        """Connect to a service on the main PC."""
        try:
            # Get service details from config
            service_ports = network_config.get('ports', {})
            if service_name not in service_ports:
                logger.error(f"Service '{service_name}' not found in network configuration")
                return False
            
            # Create socket
            socket = self.context.socket(zmq.REQ)
            
            # Connect to service
            port = service_ports[service_name]
            socket.connect(f"tcp://{MAIN_PC_IP}:{port}")
            logger.info(f"Connected to {service_name} at {MAIN_PC_IP}:{port}")
            
            # Store socket
            self.main_pc_connections[service_name] = socket
            
            return True
        except Exception as e:
            logger.error(f"Error connecting to service '{service_name}': {e}")
            self.report_error("CONNECTION_ERROR", f"Failed to connect to {service_name}: {e}")
            return False

if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = AuthenticationAgent()
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