"""
Secure ZMQ Communication Module
------------------------------
This module provides helper functions and classes for secure ZMQ communication
using the CURVE security mechanism.
"""

import os
import zmq
import zmq.auth
from zmq.auth.thread import ThreadAuthenticator
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
import threading
from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_parser import parse_agent_args

# Parse agent arguments
_agent_args = parse_agent_args()

# Configure logging
logger = logging.getLogger("SecureZMQ")

# Project root path - go up three levels to reach the AI_System_Monorepo root
project_root = Path(__file__).resolve().parent.parent.parent.parent

# Get certificates directory from _agent_args or use default
CERTIFICATES_DIR = getattr(_agent_args, 'certificates_dir', project_root / "certificates")

logger.info(f"Using certificates directory: {CERTIFICATES_DIR}")

# Lock for thread-safe singleton initialization
_auth_lock = threading.RLock()

class ZMQAuthenticator(BaseAgent):
    """
    ZMQ Authenticator class to manage the ZMQ authentication thread.
    
    This class is implemented as a singleton to ensure only one authenticator
    is active at a time in the application.
    """
    _instance = None
    
    def __new__(cls):
        with _auth_lock:
            if cls._instance is None:
                cls._instance = super(ZMQAuthenticator, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        with _auth_lock:
            if getattr(self, '_initialized', False):
                return
                
            # Initialize with BaseAgent
            super().__init__(_agent_args)
            
            # Get configuration from _agent_args
            self.certificates_dir = getattr(_agent_args, 'certificates_dir', str(CERTIFICATES_DIR))
            self.secure_zmq_enabled = getattr(_agent_args, 'secure_zmq_enabled', os.environ.get("SECURE_ZMQ", "0") == "1")
            
            self.context = zmq.Context.instance()
            self.auth = None
            self._initialized = True
            self._auth_started = False
            logger.info("ZMQAuthenticator instance created")
    
    def start(self) -> None:
        """Start the authenticator thread."""
        with _auth_lock:
            if self._auth_started:
                logger.debug("Authenticator already started")
                return
                
            # Start authentication thread - only if not already started
            if self.auth is None:
                try:
                    self.auth = ThreadAuthenticator(self.context)
                    self.auth.start()
                    logger.info("ZMQ authentication thread started")
                    
                    # Configure CURVE authentication
                    self.auth.configure_curve(domain='*', location=self.certificates_dir)
                    logger.info(f"CURVE authentication configured with certificates from {self.certificates_dir}")
                    self._auth_started = True
                except Exception as e:
                    logger.error(f"Error starting authenticator: {e}")
                    self.auth = None
                    raise
            else:
                logger.debug("Using existing authenticator instance")
    
    def stop(self) -> None:
        """Stop the authenticator thread."""
        with _auth_lock:
            if not self._auth_started:
                logger.debug("Authenticator not started")
                return
                
            if self.auth is not None:
                try:
                    self.auth.stop()
                    self.auth = None
                    self._auth_started = False
                    logger.info("ZMQ authentication thread stopped")
                except Exception as e:
                    logger.error(f"Error stopping authenticator: {e}")

def load_certificates() -> Dict[str, bytes]:
    """
    Load all certificates needed for secure ZMQ communication.
    
    Returns:
        A dictionary containing all certificate keys
    """
    certificates_dir = getattr(_agent_args, 'certificates_dir', str(CERTIFICATES_DIR))
    cert_dir_path = Path(certificates_dir)
    
    if not cert_dir_path.exists():
        raise FileNotFoundError(f"Certificates directory not found: {cert_dir_path}")
    
    # Load server certificates
    server_public_file = cert_dir_path / "server.key"
    server_secret_file = cert_dir_path / "server.key_secret"
    
    # Load client certificates
    client_public_file = cert_dir_path / "client.key"
    client_secret_file = cert_dir_path / "client.key_secret"
    
    # Check if all certificate files exist
    if not all(f.exists() for f in [server_public_file, server_secret_file, 
                                   client_public_file, client_secret_file]):
        raise FileNotFoundError(f"One or more certificate files are missing in {cert_dir_path}")
    
    # Load the certificates
    server_public, server_secret = zmq.auth.load_certificate(server_secret_file)
    client_public, client_secret = zmq.auth.load_certificate(client_secret_file)
    
    logger.info("Successfully loaded all ZMQ CURVE certificates")
    
    return {
        "server_public": server_public,
        "server_secret": server_secret,
        "client_public": client_public,
        "client_secret": client_secret
    }

def secure_server_socket(socket: zmq.Socket) -> zmq.Socket:
    """
    Configure a socket as a secure server using CURVE.
    
    Args:
        socket: The ZMQ socket to secure
        
    Returns:
        The secured ZMQ socket
    """
    try:
        # Load server certificates
        certificates_dir = getattr(_agent_args, 'certificates_dir', str(CERTIFICATES_DIR))
        server_secret_file = Path(certificates_dir) / "server.key_secret"
        server_public, server_secret = zmq.auth.load_certificate(server_secret_file)
        
        # Configure socket for CURVE security
        socket.curve_secretkey = server_secret
        socket.curve_publickey = server_public
        socket.curve_server = True
        
        logger.debug(f"Socket {socket} configured as secure CURVE server")
        return socket
    
    except Exception as e:
        logger.error(f"Error configuring secure server socket: {e}")
        raise

def secure_client_socket(socket: zmq.Socket) -> zmq.Socket:
    """
    Configure a socket as a secure client using CURVE.
    
    Args:
        socket: The ZMQ socket to secure
        
    Returns:
        The secured ZMQ socket
    """
    try:
        # Load client certificates
        certificates_dir = getattr(_agent_args, 'certificates_dir', str(CERTIFICATES_DIR))
        cert_dir_path = Path(certificates_dir)
        
        client_secret_file = cert_dir_path / "client.key_secret"
        client_public, client_secret = zmq.auth.load_certificate(client_secret_file)
        
        # Load server public key
        server_public_file = cert_dir_path / "server.key"
        server_public, _ = zmq.auth.load_certificate(server_public_file)
        
        # Configure socket for CURVE security
        socket.curve_secretkey = client_secret
        socket.curve_publickey = client_public
        socket.curve_serverkey = server_public
        
        logger.debug(f"Socket {socket} configured as secure CURVE client")
        return socket
    
    except Exception as e:
        logger.error(f"Error configuring secure client socket: {e}")
        raise

# Global authenticator instance
authenticator = ZMQAuthenticator()

def start_auth() -> None:
    """Start the ZMQ authenticator."""
    authenticator.start()

def stop_auth() -> None:
    """Stop the ZMQ authenticator."""
    authenticator.stop()

# Alias functions to match naming conventions used in other parts of the codebase
def configure_secure_server(socket: zmq.Socket) -> zmq.Socket:
    """
    Alias for secure_server_socket to maintain compatibility with existing code.
    
    Args:
        socket: The ZMQ socket to secure
        
    Returns:
        The secured ZMQ socket
    """
    start_auth()  # Ensure authenticator is started
    return secure_server_socket(socket)

def configure_secure_client(socket: zmq.Socket) -> zmq.Socket:
    """
    Alias for secure_client_socket to maintain compatibility with existing code.
    
    Args:
        socket: The ZMQ socket to secure
        
    Returns:
        The secured ZMQ socket
    """
    start_auth()  # Ensure authenticator is started 
    return secure_client_socket(socket)

def create_secure_context() -> zmq.Context:
    """
    Create a ZMQ context with security enabled.
    
    Returns:
        A ZMQ context
    """
    # Ensure authenticator is started
    if authenticator.auth is None:
        start_auth()
    
    # Return the context
    return authenticator.context 

def is_secure_zmq_enabled() -> bool:
    """
    Returns True if secure ZMQ (CURVE) is enabled via environment variable.
    """
    secure_zmq_enabled = getattr(_agent_args, 'secure_zmq_enabled', os.environ.get("SECURE_ZMQ", "0") == "1")
    return secure_zmq_enabled 