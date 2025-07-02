#!/usr/bin/env python3
from typing import Dict, Any, Optional
import yaml
# -*- coding: utf-8 -*-
"""
Proactive Context Monitor Agent
- Monitors and analyzes context for proactive actions
- Maintains context history
- Triggers proactive responses
"""

import zmq
import json
import logging
import threading
import time
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from main_pc_code.src.core.base_agent import BaseAgent
from pc2_code.agents.utils.config_loader import Config

# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import dynamic CLI parser with fallback
try:
    from pc2_code.utils.config_loader import parse_agent_args
    # Config is loaded at the module level
except ImportError as e:
    print(f"Import error: {e}")
    class DummyArgs:
        host = 'localhost'
    _agent_args = DummyArgs()

# Configure logging
log_file_path = 'logs/proactive_context_monitor.log'
log_directory = os.path.dirname(log_file_path)
os.makedirs(log_directory, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ProactiveContextMonitor')

# ZMQ ports
PROACTIVE_MONITOR_PORT = 7119  # Default, will be overridden by configuration
PROACTIVE_MONITOR_HEALTH_PORT = 8119  # Default health check port
# Health check port is defined above

class ProactiveContextMonitor(BaseAgent):
    """Proactive Context Monitor Agent for analyzing context and triggering proactive actions."""
    
    def __init__(self, port=None, health_check_port=None):
        super().__init__(name="ProactiveContextMonitor", port=port)
        self.start_time = time.time()
        self.running = True
        self.request_count = 0
        self.main_pc_connections = {}
        logger.info(f"{self.__class__.__name__} initialized on PC2 (IP: {PC2_IP}) port {self.port}")
        self.main_port = port if port is not None else PROACTIVE_MONITOR_PORT
        self.health_port = health_check_port if health_check_port is not None else PROACTIVE_MONITOR_HEALTH_PORT
        self.context = zmq.Context()
        self.running = True
        self.context_history = []
        self._init_zmq()
        self._start_background_threads()
        logger.info(f"Proactive Context Monitor initialized on port {self.main_port}")
    
    def _init_zmq(self):
        """Initialize ZMQ sockets."""
        try:
            # Set up main socket
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://*:{self.main_port}")
            logger.info(f"Main socket bound to port {self.main_port}")
            
            # Set up health check server
            self._setup_health_check_server()
            logger.info(f"Health check server started on port {self.health_port}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ZMQ: {e}")
            raise
    
    def _setup_health_check_server(self):
        """Set up a simple HTTP server for health checks."""
        from http.server import HTTPServer, BaseHTTPRequestHandler
        
        class HealthCheckHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
        
        server_address = (BIND_ADDRESS, self.health_port)
        httpd = HTTPServer(server_address, HealthCheckHandler)
        logger.info(f"Health check server started on {server_address}")
        httpd.serve_forever()

    def _get_health_status(self):
        """Return health status information."""
        base_status = super()._get_health_status()
        base_status.update({
            'service': 'ProactiveContextMonitor',
            'uptime': time.time() - self.start_time,
            'context_history_length': len(self.context_history) if hasattr(self, 'context_history') else 0
        })
        return base_status

# Load configuration at the module level
config = Config().get_config()

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

if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = ProactiveContextMonitor()
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