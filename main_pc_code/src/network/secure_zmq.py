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

# Configure logging
logger = logging.getLogger("SecureZMQ")

# Project root path
project_root = Path(__file__).resolve().parent.parent.parent

# Certificates directory
CERTIFICATES_DIR = project_root / "certificates"

class ZMQAuthenticator:
    """
    ZMQ Authenticator class to manage the ZMQ authentication thread.
    
    This class is implemented as a singleton to ensure only one authenticator
    is active at a time in the application.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ZMQAuthenticator, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.context = zmq.Context.instance()
        self.auth = None
        self._initialized = True
        logger.info("ZMQAuthenticator instance created")
    
    def start(self) -> None:
        """Start the authenticator thread."""
        if self.auth is not None:
            logger.warning("Authenticator already started")
            return
            
        # Start authentication thread
        self.auth = ThreadAuthenticator(self.context)
        self.auth.start()
        logger.info("ZMQ authentication thread started")
        
        # Configure CURVE authentication
        self.auth.configure_curve(domain='*', location=str(CERTIFICATES_DIR))
        logger.info(f"CURVE authentication configured with certificates from {CERTIFICATES_DIR}")
    
    def stop(self) -> None:
        """Stop the authenticator thread."""
        if self.auth is None:
            logger.warning("Authenticator not started")
            return
            
        self.auth.stop()
        self.auth = None
        logger.info("ZMQ authentication thread stopped")

def load_certificates() -> Dict[str, bytes]:
    """
    Load all certificates needed for secure ZMQ communication.
    
    Returns:
        A dictionary containing all certificate keys
    """
    if not CERTIFICATES_DIR.exists():
        raise FileNotFoundError(f"Certificates directory not found: {CERTIFICATES_DIR}")
    
    # Load server certificates
    server_public_file = CERTIFICATES_DIR / "server.key"
    server_secret_file = CERTIFICATES_DIR / "server.key_secret"
    
    # Load client certificates
    client_public_file = CERTIFICATES_DIR / "client.key"
    client_secret_file = CERTIFICATES_DIR / "client.key_secret"
    
    # Check if all certificate files exist
    if not all(f.exists() for f in [server_public_file, server_secret_file, 
                                   client_public_file, client_secret_file]):
        raise FileNotFoundError(f"One or more certificate files are missing in {CERTIFICATES_DIR}")
    
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
        server_secret_file = CERTIFICATES_DIR / "server.key_secret"
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
        client_secret_file = CERTIFICATES_DIR / "client.key_secret"
        client_public, client_secret = zmq.auth.load_certificate(client_secret_file)
        
        # Load server public key
        server_public_file = CERTIFICATES_DIR / "server.key"
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