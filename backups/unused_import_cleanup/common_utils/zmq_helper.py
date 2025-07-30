"""
ZMQ Helper Functions
-------------------
Utility functions for ZMQ socket creation and management.
"""

import zmq
import logging
import time
import os
from typing import Dict, Any, Optional, Union, Tuple

logger = logging.getLogger(__name__)

def create_socket(context: zmq.Context, socket_type: int, server: bool = False) -> zmq.Socket:
    """
    Create a ZMQ socket with standard options.
    
    Args:
        context: ZMQ context
        socket_type: ZMQ socket type (e.g., zmq.REQ, zmq.REP)
        server: Whether this is a server socket
        
    Returns:
        zmq.Socket: Configured ZMQ socket
    """
    socket = context.socket(socket_type)
    
    # Set common socket options
    socket.setsockopt(zmq.LINGER, 0)  # Don't wait for unsent messages on close
    
    if socket_type in (zmq.REQ, zmq.REP, zmq.DEALER, zmq.ROUTER):
        socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second receive timeout
        socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 second send timeout
    
    # For server sockets, set TCP keepalive options
    if server:
        socket.setsockopt(zmq.TCP_KEEPALIVE, 1)
        socket.setsockopt(zmq.TCP_KEEPALIVE_IDLE, 60)
        socket.setsockopt(zmq.TCP_KEEPALIVE_INTVL, 30)
    
    return socket

def safe_socket_send(socket: zmq.Socket, message: Union[dict, str, bytes], timeout: int = 5000) -> bool:
    """
    Safely send a message on a ZMQ socket with timeout.
    
    Args:
        socket: ZMQ socket
        message: Message to send (dict will be JSON-encoded)
        timeout: Send timeout in milliseconds
        
    Returns:
        bool: True if send was successful, False otherwise
    """
    try:
        # Save original timeout
        original_timeout = socket.getsockopt(zmq.SNDTIMEO)
        
        # Set new timeout
        socket.setsockopt(zmq.SNDTIMEO, timeout)
        
        # Send message based on type
        if isinstance(message, dict):
            socket.send_json(message)
        elif isinstance(message, str):
            socket.send_string(message)
        else:
            socket.send(message)
            
        # Restore original timeout
        socket.setsockopt(zmq.SNDTIMEO, original_timeout)
        
        return True
    except zmq.Again:
        logger.warning("Socket send timed out")
        return False
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False

def safe_socket_recv(socket: zmq.Socket, timeout: int = 5000) -> Tuple[bool, Any]:
    """
    Safely receive a message from a ZMQ socket with timeout.
    
    Args:
        socket: ZMQ socket
        timeout: Receive timeout in milliseconds
        
    Returns:
        Tuple[bool, Any]: (success, message)
    """
    try:
        # Save original timeout
        original_timeout = socket.getsockopt(zmq.RCVTIMEO)
        
        # Set new timeout
        socket.setsockopt(zmq.RCVTIMEO, timeout)
        
        # Receive message
        message = socket.recv_json()
        
        # Restore original timeout
        socket.setsockopt(zmq.RCVTIMEO, original_timeout)
        
        return True, message
    except zmq.Again:
        logger.warning("Socket receive timed out")
        return False, None
    except Exception as e:
        logger.error(f"Error receiving message: {e}")
        return False, None

def bind_to_random_port(socket: zmq.Socket, address: str = "tcp://0.0.0.0", 
                        min_port: int = 5000, max_port: int = 10000, max_tries: int = 100) -> int:
    """
    Bind a socket to a random available port.
    
    Args:
        socket: ZMQ socket
        address: Address to bind to
        min_port: Minimum port number
        max_port: Maximum port number
        max_tries: Maximum number of binding attempts
        
    Returns:
        int: Port number or -1 if binding failed
    """
    try:
        return socket.bind_to_random_port(address, min_port, max_port, max_tries)
    except zmq.ZMQError as e:
        logger.error(f"Failed to bind to random port: {e}")
        return -1

def get_bind_address() -> str:
    """
    Get the bind address from environment variables.
    
    Returns:
        str: Bind address (defaults to 0.0.0.0 for Docker compatibility)
    """
    return os.environ.get("BIND_ADDRESS", "0.0.0.0")

def create_health_check_socket(context: zmq.Context, port: int) -> Optional[zmq.Socket]:
    """
    Create a health check socket.
    
    Args:
        context: ZMQ context
        port: Port to bind to
        
    Returns:
        Optional[zmq.Socket]: Health check socket or None if binding failed
    """
    try:
        socket = create_socket(context, zmq.REP, server=True)
        bind_address = f"tcp://{get_bind_address()}:{port}"
        socket.bind(bind_address)
        logger.info(f"Health check socket bound to {bind_address}")
        return socket
    except zmq.ZMQError as e:
        logger.error(f"Failed to create health check socket: {e}")
        return None

def run_health_check_loop(socket: zmq.Socket, health_check_func, running_flag, poll_interval: int = 100) -> None:
    """
    Run a health check loop.
    
    Args:
        socket: Health check socket
        health_check_func: Function that returns health check data
        running_flag: Flag indicating whether the agent is running
        poll_interval: Poll interval in milliseconds
    """
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)
    
    while running_flag:
        try:
            if dict(poller.poll(poll_interval)):
                # Receive request
                _ = socket.recv()
                
                # Get health data
                health_data = health_check_func()
                
                # Send response
                socket.send_json(health_data)
        except Exception as e:
            logger.error(f"Error in health check loop: {e}")
            time.sleep(1)  # Prevent tight loop on error 