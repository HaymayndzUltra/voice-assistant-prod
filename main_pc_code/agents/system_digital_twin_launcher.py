#!/usr/bin/env python3
"""
SystemDigitalTwin Launcher Script

This script launches the SystemDigitalTwin agent with explicit port configuration
to avoid conflicts with any existing processes.
"""

import sys
import os
from pathlib import Path


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", ".."))))
from common.utils.path_env import get_path, join_path, get_file_path
# Add the project's main_pc_code directory to the Python path
MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

# Import required modules
import zmq
import json
import time
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, cast

# Import the agent class and base agent
from main_pc_code.agents.system_digital_twin import SystemDigitalTwinAgent
from common.core.base_agent import BaseAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(join_path("logs", "system_digital_twin_launcher.log"))
    ]
)
logger = logging.getLogger("SystemDigitalTwinLauncher")

# Override BaseAgent's __init__ to use our custom health check port
BaseAgent._original_init = BaseAgent.__init__
def custom_init(self, *args, **kwargs):
    # Call original init but save the health_check_port first
    custom_health_port = kwargs.pop('health_check_port', None)
    BaseAgent._original_init(self, *args, **kwargs)
    
    # Override the health_check_port if provided
    if custom_health_port:
        logger.info(f"Overriding health check port from {self.health_check_port} to {custom_health_port}")
        # Close the existing health socket
        if hasattr(self, 'health_socket'):
            self.health_socket.close()
        if hasattr(self, 'health_context'):
            self.health_context.term()
            
        # Create a new health socket with the custom port
        self.health_check_port = custom_health_port
        self.health_context = zmq.Context()
        self.health_socket = self.health_context.socket(zmq.REP)
        self.health_socket.setsockopt(zmq.LINGER, 0)
        try:
            self.health_socket.bind(f"tcp://*:{self.health_check_port}")
            logger.info(f"Successfully bound health check socket to port {self.health_check_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind health check socket to port {self.health_check_port}: {e}")
            raise

# Apply the monkey patch
BaseAgent.__init__ = custom_init

if __name__ == "__main__":
    logger.info("Starting SystemDigitalTwin with port 7120 and health check port 8120...")
    try:
        # Create and run the agent with custom health check port
        agent = SystemDigitalTwinAgent()
        
        # Override the health check port
        custom_init(agent, name=agent.name, port=agent.port, health_check_port=8120)
        
        # Run the agent
        agent.run()
    except KeyboardInterrupt:
        logger.info("\nShutting down SystemDigitalTwin...")
        agent.cleanup()
    except Exception as e:
        logger.error(f"Error starting SystemDigitalTwin: {e}")
        import traceback
        traceback.print_exc() 