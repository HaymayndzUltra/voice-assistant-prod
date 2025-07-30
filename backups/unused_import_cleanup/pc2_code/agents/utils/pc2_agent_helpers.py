#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
PC2 Agent Helpers
----------------
This module provides standardized imports and initialization helpers for PC2 agents.
"""

import os
import sys
import time
import logging
import json
import zmq
from typing import Dict, Any, Optional


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("pc2_code", ".."))))
from common.utils.path_manager import PathManager
# Import the BaseAgent from main_pc_code
from common.core.base_agent import BaseAgent

# Import Config class for PC2
from pc2_code.agents.utils.config_loader import Config
from main_pc_code.utils.network_utils import get_zmq_connection_string, get_machine_ip
from common.env_helpers import get_env

# Standard PC2 configuration setup
def get_pc2_config():
    """Get configuration for PC2 agents using the standard Config class."""
    return Config().get_config()

# PC2-specific logging setup
def setup_pc2_logging(agent_name: str, log_level=logging.INFO):
    """
    Set up standardized logging for PC2 agents.
    
    Args:
        agent_name: Name of the agent for the log file
        log_level: Logging level (default: INFO)
    
    Returns:
        Logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = get_path("logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, fstr(PathManager.get_logs_dir() / "{agent_name.lower()}.log"))
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ],
        force=True  # Ensure this configuration is applied
    )
    
    return logging.getLogger(agent_name)

# Get PC2-specific health status
def get_pc2_health_status(agent_instance, base_status=None):
    """
    Add PC2-specific fields to health status.
    
    Args:
        agent_instance: The agent instance
        base_status: Base status dict from BaseAgent._get_health_status()
    
    Returns:
        Dict with PC2-specific health fields
    """
    # If base_status not provided, use empty dict
    status = base_status or {}
    
    # Add PC2-specific health information
    status.update({
        'service': agent_instance.__class__.__name__,
        'uptime': time.time() - agent_instance.start_time if hasattr(agent_instance, 'start_time') else 0,
        'machine': 'pc2',
        'environment': os.environ.get('PC2_ENV', 'development'),
        'status': 'healthy'
    })
    
    return status

# Initialize ZMQ socket with standard PC2 settings
def setup_zmq_socket(port, socket_type=zmq.REP, bind=True):
    """
    Set up a ZMQ socket with standard PC2 settings.
    
    Args:
        port: Port number to bind/connect to
        socket_type: ZMQ socket type (default: REP)
        bind: Whether to bind or connect (default: True for bind)
    
    Returns:
        Tuple of (context, socket)
    """
    context = zmq.Context()
    socket = context.socket(socket_type)
    
    if bind:
        socket.bind(f"tcp://*:{port}")
    else:
        socket.connect(get_zmq_connection_string({port}, "localhost")))
    
    return context, socket

# Standard cleanup for PC2 agents
def standard_cleanup(agent_instance, logger=None):
    """
    Perform standard cleanup for PC2 agents.
    
    Args:
        agent_instance: The agent instance
        logger: Logger to use (optional)
    """
    log = logger or logging.getLogger(__name__)
    
    log.info(f"Cleaning up {agent_instance.__class__.__name__}...")
    
    # Mark as not running
    if hasattr(agent_instance, 'running'):
        agent_instance.running = False
    
    # Close socket
    if hasattr(agent_instance, 'socket') and agent_instance.socket:
        try:
            agent_instance.socket.close()
        except Exception as e:
            log.error(f"Error closing socket: {e}")
    
    # Terminate context
    if hasattr(agent_instance, 'context') and agent_instance.context:
        try:
            agent_instance.context.term()
        except Exception as e:
            log.error(f"Error terminating ZMQ context: {e}")
    
    # Call parent cleanup if available
    if hasattr(agent_instance, 'cleanup') and callable(getattr(agent_instance, 'cleanup')):
        try:
            agent_instance.cleanup()
        except Exception as e:
            log.error(f"Error in parent cleanup: {e}") 