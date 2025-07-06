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
    from pc2_code.agents.utils.config_loader import Config
    config = Config()  # Instantiate the global config object
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback if config not available
    config = None

# Import system_config for per-machine settings
try:
    from pc2_code.config import system_config
except ImportError:
    system_config = {}

try:
    from pc2_code.utils.config_loader import parse_agent_args
    _agent_args = parse_agent_args() 
    from common.core.base_agent import BaseAgent
    from pc2_code.agents.utils.config_loader import Config

    # Load configuration at the module level
    config = Config().get_config()
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback if config parser not available
    class DummyArgs:
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

class AuthenticationAgent(BaseAgent):
    """Authentication Agent for system-wide authentication and authorization. Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:')."""
    
    def __init__(self, port: int = None, health_check_port: int = None, **kwargs):
        # Initialize BaseAgent with proper name and port
        super().__init__(name="AuthenticationAgent", port=port if port is not None else AUTH_PORT, **kwargs)

        # Record start time for uptime calculation
        self.start_time = time.time()

        # Initialize agent state
        self.running = True
        self.request_count = 0
        
        # Set up connection to main PC if needed
        self.main_pc_connections = {}
        
        logger.info(f"{self.__class__.__name__} initialized on PC2 port {self.port}")
        # Initialize authentication data
        self.users = {}
        self.sessions = {}
        self.token_expiry = timedelta(hours=24)
        
        # Start session cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_sessions_loop)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        logger.info(f"Authentication Agent initialized on port {self.port}")
    
    

        self.error_bus_port = 7150

        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')

        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"

        self.error_bus_pub = self.context.socket(zmq.PUB)

        self.error_bus_pub.connect(self.error_bus_endpoint)
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
            
            valid = self._validate_token(token)
            
            if valid:
                return {'status': 'success', 'valid': True}
            else:
                return {'status': 'success', 'valid': False}
        except Exception as e:
            logger.error(f"Error handling token validation: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _health_check(self) -> Dict[str, Any]:
        """Legacy health check method."""
        return self._get_health_status()
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        # Call the parent class implementation first
        status = super()._get_health_status()
        
        # Add agent-specific health information
        status.update({
            "agent_type": "authentication",
            "active_sessions": len(self.sessions),
            "registered_users": len(self.users),
            "cleanup_thread_alive": self.cleanup_thread.is_alive() if hasattr(self, 'cleanup_thread') else False
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
                    time.sleep(1)  # Sleep to avoid tight loop on error
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
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
            self.socket.close()
        
        # Join threads
        if hasattr(self, 'cleanup_thread'):
            self.cleanup_thread.join(timeout=2.0)
        
        # Call parent cleanup
        super().cleanup()
        
        logger.info("Authentication Agent cleanup complete")
    
    def stop(self):
        """Stop the agent."""
        self.running = False
        
    def connect_to_main_pc_service(self, service_name: str):
        """Connect to a service on the main PC."""
        try:
            # Load network configuration
            network_config = load_network_config()
            
            if not network_config:
                logger.error("Failed to load network configuration")
                return False
            
            # Get service details
            service_config = network_config.get('services', {}).get(service_name)
            if not service_config:
                logger.error(f"Service '{service_name}' not found in network configuration")
                return False
            
            # Create socket
            socket = self.context.socket(zmq.REQ)
            
            # Connect to service
            host = service_config.get('host', 'localhost')
            port = service_config.get('port')
            if not port:
                logger.error(f"No port specified for service '{service_name}'")
                return False
            
            socket.connect(f"tcp://{host}:{port}")
            logger.info(f"Connected to {service_name} at {host}:{port}")
            
            # Store socket
            self.main_pc_connections[service_name] = socket
            
            return True
        except Exception as e:
            logger.error(f"Error connecting to service '{service_name}': {e}")
            return False

def load_network_config():
    """Load network configuration from file."""
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'network_config.yaml')
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network configuration: {e}")
        return None

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