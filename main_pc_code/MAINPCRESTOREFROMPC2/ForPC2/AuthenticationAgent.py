from src.core.base_agent import BaseAgent
import zmq
import json
import logging
import threading
import time
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/authentication_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AuthenticationAgent')

class AuthenticationAgent(BaseAgent):
    """Authentication Agent for system-wide authentication and authorization."""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AuthenticationAgent")
        
        # Initialize authentication data
        self.users = {}
        self.sessions = {}
        self.token_expiry = timedelta(hours=24)
        
        # Initialize ZMQ context and sockets
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://*:{port if port else 5642}")
        
        # Start session cleanup thread
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_sessions_loop)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        
        logger.info("Authentication Agent initialized")
    
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
            'cleanup_thread_alive': self.cleanup_thread.is_alive()
        }
    
    def stop(self):
        """Stop the agent gracefully."""
        self.running = False
        if self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        self.socket.close()
        self.context.term()
        logger.info("Authentication Agent stopped") 