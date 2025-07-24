"""
from common.config_manager import get_service_ip, get_service_url, get_redis_url
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


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("pc2_code", ".."))))
from common.utils.path_manager import PathManager
# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import config module
try:
from pc2_code.agents.utils.config_loader import Config
    except ImportError as e:
        print(f"Import error: {e}")
    config = Config()  # Instantiate the global config object
except ImportError:
    # Fallback if config not available
    config = None

# Import system_config for per-machine settings
try:
from pc2_code.config import system_config
except ImportError:
    system_config = {}

try:
from pc2_code.agents.utils.config_parser import parse_agent_args
    except ImportError as e:
        print(f"Import error: {e}")
    _agent_args 
from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config
from common.env_helpers import get_env

# Load configuration at the module level
config = load_config()= parse_agent_args()
except ImportError:
    # Fallback if config parser not available
    class DummyArgs(BaseAgent):
        host = 'localhost'
    _agent_args = DummyArgs()

# Configure logging
log_file_path = PathManager.join_path("logs", str(PathManager.get_logs_dir() / "authentication_agent.log"))
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

class AuthenticationAgent:
    """Authentication Agent for system-wide authentication and authorization."""
    
    def __init__(self, port: int = None, health_check_port: int = None, **kwargs):
         super().__init__(name="DummyArgs", port=None)
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
    # Standardized main execution block
    agent = None
    try:
        agent = DummyArgs()
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