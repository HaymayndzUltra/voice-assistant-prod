"""
ZMQ Cleanup Utilities
--------------------
Standard utilities for proper ZMQ socket and context cleanup.
These utilities ensure consistent cleanup patterns across all agents
and help prevent resource leaks.
"""

import zmq
import logging
import time
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

def safe_close_socket(socket: Optional[zmq.Socket]) -> bool:
    """
    Safely close a ZMQ socket with proper error handling.
    
    Args:
        socket: The ZMQ socket to close
        
    Returns:
        bool: True if successful, False otherwise
    """
    if socket is None:
        return True
        
    try:
        socket.close(linger=100)  # 100ms linger time for pending messages
        return True
    except Exception as e:
        logger.error(f"Error closing ZMQ socket: {e}")
        return False

def safe_terminate_context(context: Optional[zmq.Context], timeout: int = 1000) -> bool:
    """
    Safely terminate a ZMQ context with proper error handling.
    
    Args:
        context: The ZMQ context to terminate
        timeout: Timeout in milliseconds for pending sockets to close
        
    Returns:
        bool: True if successful, False otherwise
    """
    if context is None:
        return True
        
    try:
        context.term()
        return True
    except Exception as e:
        logger.error(f"Error terminating ZMQ context: {e}")
        
        # Try to force termination if normal termination fails
        try:
            logger.warning("Attempting to force context termination")
            context.destroy(linger=timeout)
            return True
        except Exception as e2:
            logger.error(f"Error force-terminating ZMQ context: {e2}")
            return False

def cleanup_zmq_resources(sockets: Dict[str, zmq.Socket], context: Optional[zmq.Context] = None) -> Dict[str, bool]:
    """
    Clean up multiple ZMQ sockets and optionally a context.
    
    Args:
        sockets: Dictionary of socket names to socket objects
        context: Optional ZMQ context to terminate
        
    Returns:
        Dict[str, bool]: Status of each cleanup operation
    """
    results = {}
    
    # Close all sockets first
    for name, socket in sockets.items():
        success = safe_close_socket(socket)
        results[f"socket_{name}"] = success
        if success:
            logger.info(f"Successfully closed socket: {name}")
        else:
            logger.warning(f"Failed to close socket: {name}")
    
    # Then terminate the context if provided
    if context is not None:
        success = safe_terminate_context(context)
        results["context"] = success
        if success:
            logger.info("Successfully terminated ZMQ context")
        else:
            logger.warning("Failed to terminate ZMQ context")
    
    return results

def cleanup_agent_zmq_resources(agent: Any) -> Dict[str, bool]:
    """
    Clean up ZMQ resources for an agent instance.
    Automatically detects socket attributes and context.
    
    Args:
        agent: The agent instance with ZMQ resources
        
    Returns:
        Dict[str, bool]: Status of each cleanup operation
    """
    results = {}
    sockets = {}
    context = None
    
    # Find all socket attributes
    for attr_name in dir(agent):
        if attr_name.startswith('_'):
            continue
            
        attr = getattr(agent, attr_name)
        if isinstance(attr, zmq.Socket):
            sockets[attr_name] = attr
        elif isinstance(attr, zmq.Context):
            context = attr
    
    # Close all sockets
    for name, socket in sockets.items():
        success = safe_close_socket(socket)
        results[f"socket_{name}"] = success
        if success:
            logger.info(f"Successfully closed socket: {name}")
        else:
            logger.warning(f"Failed to close socket: {name}")
    
    # Terminate context if found
    if context is not None:
        success = safe_terminate_context(context)
        results["context"] = success
        if success:
            logger.info("Successfully terminated ZMQ context")
        else:
            logger.warning("Failed to terminate ZMQ context")
    
    return results

def create_cleanup_decorator(logger_instance=None):
    """
    Create a decorator that adds standardized cleanup methods to an agent class.
    
    Args:
        logger_instance: Optional logger to use for logging
        
    Returns:
        function: A decorator function
    """
    log = logger_instance or logger
    
    def with_zmq_cleanup(cls):
        """
        Decorator that adds standardized cleanup methods to an agent class.
        
        Args:
            cls: The agent class to decorate
            
        Returns:
            cls: The decorated class
        """
        original_init = cls.__init__
        
        def new_init(self, *args, **kwargs):
            self._zmq_sockets = {}
            self._zmq_context = None
            original_init(self, *args, **kwargs)
        
        def register_socket(self, name, socket):
            """Register a ZMQ socket for automatic cleanup"""
            self._zmq_sockets[name] = socket
            return socket
            
        def register_context(self, context):
            """Register a ZMQ context for automatic cleanup"""
            self._zmq_context = context
            return context
            
        def cleanup_zmq(self):
            """Clean up all registered ZMQ resources"""
            results = {}
            
            # Close all sockets
            for name, socket in self._zmq_sockets.items():
                try:
                    socket.close(linger=100)
                    log.info(f"Closed socket: {name}")
                    results[f"socket_{name}"] = True
                except Exception as e:
                    log.error(f"Error closing socket {name}: {e}")
                    results[f"socket_{name}"] = False
            
            # Clear the sockets dictionary
            self._zmq_sockets.clear()
            
            # Terminate the context
            if self._zmq_context:
                try:
                    self._zmq_context.term()
                    log.info("Terminated ZMQ context")
                    results["context"] = True
                except Exception as e:
                    log.error(f"Error terminating ZMQ context: {e}")
                    results["context"] = False
                self._zmq_context = None
                
            return results
        
        # Add the new methods to the class
        cls.__init__ = new_init
        cls.register_socket = register_socket
        cls.register_context = register_context
        cls.cleanup_zmq = cleanup_zmq
        
        return cls
    
    return with_zmq_cleanup

# Example usage:
"""
from utils.zmq_cleanup_utils import with_zmq_cleanup

@with_zmq_cleanup
class MyAgent:
    def __init__(self):
        self.context = self.register_context(zmq.Context())
        self.socket = self.register_socket('main', self.context.socket(zmq.REP))
        
    def shutdown(self):
        self.cleanup_zmq()
""" 