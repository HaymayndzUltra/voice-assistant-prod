#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Predictive Health Monitor
- Uses machine learning to predict potential agent failures
- Monitors system resources and agent performance
- Implements tiered recovery strategies
- Provides proactive health management
- Coordinates agent lifecycle and dependencies
- Supports distributed system deployment
"""

import logging
import socket
import zmq
import yaml
import time
import sys
import os
import signal
import threading
import subprocess
import json
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_parser import parse_agent_args

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/predictive_health_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PredictiveHealthMonitor")

# Constants
HEALTH_MONITOR_PORT = 5613
HEALTH_CHECK_PORT = 5614
# Default ZMQ send/receive timeout (milliseconds)
ZMQ_REQUEST_TIMEOUT = 2000

class PredictiveHealthMonitor(BaseAgent):
    """Predictive health monitoring system for AI agents"""
    
    def __init__(self, port=None):
        """Initialize the predictive health monitor"""
        _agent_args = parse_agent_args()
        port = port or getattr(_agent_args, 'port', None) or HEALTH_MONITOR_PORT
        name = "PredictiveHealthMonitor"
        super().__init__(name=name, port=port)
        self.port = port or HEALTH_MONITOR_PORT
        self.health_port = HEALTH_CHECK_PORT
        
        # Get machine information
        self.hostname = socket.gethostname()
        try:
            self.ip_address = socket.gethostbyname(self.hostname)
        except:
            self.ip_address = "127.0.0.1"
        logger.info(f"Running on {self.hostname} ({self.ip_address})")
        
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Socket to receive requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        try:
            self.socket.bind(f"tcp://*:{self.port}")
            logger.info(f"Predictive Health Monitor bound to port {self.port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind to port {self.port}: {e}")
            if "Address already in use" in str(e):
                logger.warning(f"Port {self.port} is in use, trying alternative port")
                try:
                    alt_port = self.port + 10
                    self.socket.bind(f"tcp://*:{alt_port}")
                    self.port = alt_port
                    logger.info(f"Successfully bound to alternative port {alt_port}")
                except zmq.error.ZMQError as e2:
                    logger.error(f"Failed to bind to alternative port: {e2}")
                    raise
            else:
                raise
        
        # Agent health status
        self.agent_health = {}
        
        # Agent processes and dependencies
        self.agent_processes = {}
        self.agent_last_restart = {}
        self.agent_dependencies = {}
        self.agent_configs = {}
        
        # Load agent configurations
        self._load_agent_configs()
        
        # Running flag
        self.running = True
        
        logger.info("Predictive Health Monitor initialized")

    def _load_agent_configs(self):
        """Load agent configurations from startup config"""
        try:
            config_path = Path("config/startup_config.yaml")
            if not config_path.exists():
                config_path = Path("../config/startup_config.yaml")
            
            if not config_path.exists():
                logger.warning("startup_config.yaml not found")
                return
                
            with open(config_path, 'r') as f:
                startup_config = yaml.safe_load(f)
            
            # Process all sections that contain agent configurations
            for section_name, section in startup_config.items():
                if isinstance(section, list) and section and isinstance(section[0], dict):
                    for agent in section:
                        name = agent.get('name')
                        if name:
                            self.agent_configs[name] = {
                                'script': agent.get('script_path'),
                                'host': agent.get('host', 'localhost'),
                                'port': agent.get('port'),
                                'dependencies': agent.get('dependencies', []),
                                'required': agent.get('required', False)
                            }
                            self.agent_dependencies[name] = agent.get('dependencies', [])
            
            logger.info(f"Loaded configurations for {len(self.agent_configs)} agents")
        except Exception as e:
            logger.error(f"Error loading agent configurations: {e}")
            self.agent_configs = {}

    def _get_health_status(self):
        """Overrides the base method to add agent-specific health metrics."""
        base_status = super()._get_health_status()
        specific_metrics = {
            "monitor_status": "active" if getattr(self, 'running', False) else "inactive",
            "monitored_systems_count": getattr(self, 'monitored_systems_count', 0),
            "prediction_accuracy": getattr(self, 'prediction_accuracy', 'N/A')
        }
        base_status.update(specific_metrics)
        return base_status

    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources")
        self.running = False
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        super().cleanup()
        logger.info("Cleanup complete")

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Predictive Health Monitor')
    parser.add_argument('--port', type=int, default=HEALTH_MONITOR_PORT, help='Port to bind to')
    args = parser.parse_args()
    
    # Create and run the monitor
    monitor = PredictiveHealthMonitor(port=args.port)
    
    try:
        monitor.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down")
    finally:
        monitor.cleanup() 