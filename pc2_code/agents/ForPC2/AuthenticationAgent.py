"""
from typing import Dict, Any, Optional
import yaml
Authentication Agent
- Handles user authentication and authorization
- Manages user sessions and tokens
- Provides secure login/logout functionality
"""
import zmq
import json
import logging
import threading
import time
import hashlib
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import config module
try:
    from agents.utils.config_loader import Config
    config = Config()  # Instantiate the global config object
except ImportError:
    # Fallback if config not available
    config = None

# Import system_config for per-machine settings
try:
    from config import system_config
except ImportError:
    system_config = {}

try:
    from agents.utils.config_parser import parse_agent_args
    _agent_args 
from main_pc_code.src.core.base_agent import BaseAgent
from pc2_code.agents.utils.config_loader import Config

# Load configuration at the module level
config = Config().get_config()
except ImportError:
    # Fallback if config parser not available
    class DummyArgs(BaseAgent):
        host = 'localhost'
    _agent_args = DummyArgs()

# Configure logging
log_file_path = 'logs/authentication_agent.log'
log_directory = os.path.dirname(log_file_path)
os.makedirs(log_directory, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('AuthenticationAgent')

# Default ZMQ ports (will be overridden by configuration)
AUTH_PORT = 7116  # Default, will be overridden by configuration
AUTH_HEALTH_PORT = 8116  # Default health check port



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
class AuthenticationAgent:
    """Authentication Agent for system-wide authentication and authorization."""
    
    def __init__(self, port: int = None, health_check_port: int = None, **kwargs):
         super().__init__(name="DummyArgs", port=None)

         # Record start time for uptime calculation

         self.start_time = time.time()

         

         # Initialize agent state

         self.running = True

         self.request_count = 0

         

         # Set up connection to main PC if needed

         self.main_pc_connections = {}

         

         logger.info(f"{self.__class__.__name__} initialized on PC2 (IP: {PC2_IP}) port {self.port}")

"""Initialize the Authentication Agent.
        
        Args:
            port: Optional port override for testing
            health_check_port: Optional health check port override
        """
        # Initialize authentication data
        self.users = {}
        self.sessions = {}
        self.token_expiry = timedelta(hours=24)
        
        # Set up ports
        self.main_port = port if port is not None else AUTH_PORT
        self.health_port = health_check_port if health_check_port is not None else AUTH_HEALTH_PORT
        
        # Initialize ZMQ context and sockets
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.main_port}")
        
        # Start session cleanup thread
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_sessions_loop)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        
        logger.info(f"Authentication Agent initialized on port {self.main_port}")
    
    def _cleanup_sessions_loop(self):
        """Background thread for cleaning up expired sessions."""
        while self.running:
            try:
                self._cleanup_expired_sessions()
                time.sleep(300)  # Clean up every 5 minutes
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
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
            return self._health_check()
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
            return {'status': 'error', 'message': str(e)}
    
    def _handle_token_validation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle token validation."""
        try:
            token = request.get('token')
            
            if not token:
                return {'status': 'error', 'message': 'Missing token'}
            
            is_valid = self._validate_token(token)
            
            return {
                'status': 'success',
                'valid': is_valid,
                'message': 'Token is valid' if is_valid else 'Token is invalid'
            }
        except Exception as e:
            logger.error(f"Error handling token validation: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            'status': 'success',
            'agent': 'AuthenticationAgent',
            'timestamp': datetime.now().isoformat(),
            'active_sessions': len(self.sessions),
            'registered_users': len(self.users),
            'cleanup_thread_alive': self.cleanup_thread.is_alive(),
            'port': self.main_port
        }
    
    def run(self):
        """Main run loop for the agent."""
        logger.info(f"Authentication Agent starting on port {self.main_port}")
        
        try:
            while self.running:
                try:
                    # Receive request
                    request = self.socket.recv_json()
                    logger.debug(f"Received request: {request}")
                    
                    # Process request
                    response = self.handle_request(request)
                    
                    # Send response
                    self.socket.send_json(response)
                    
                except zmq.error.ZMQError as e:
                    logger.error(f"ZMQ error in run loop: {e}")
                    # Try to send an error response
                    try:
                        self.socket.send_json({
                            'status': 'error',
                            'error': str(e)
                        })
                    except:
                        pass
                    
                except Exception as e:
                    logger.error(f"Error in run loop: {e}")
                    # Try to send an error response
                    try:
                        self.socket.send_json({
                            'status': 'error',
                            'error': str(e)
                        })
                    except:
                        pass
                    
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up resources...")
        
        # Stop background threads
        self.running = False
        if self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        
        # Close ZMQ socket
        if hasattr(self, 'socket'):
            self.socket.close()
        
        # Close ZMQ context
        if hasattr(self, 'context'):
            self.context.term()
            
        logger.info("Cleanup complete")


    
    def _get_health_status(self) -> dict:

    
        """Return health status information."""

    
        base_status = super()._get_health_status()

    
        # Add any additional health information specific to DummyArgs

    
        base_status.update({

    
            'service': 'DummyArgs',

    
            'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,

    
            'additional_info': {}

    
        })

    
        return base_status
    
    def stop(self):
        """Stop the agent gracefully."""
        self.running = False







if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = DummyArgs()
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