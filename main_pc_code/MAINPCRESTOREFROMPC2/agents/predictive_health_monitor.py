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

class PredictiveHealthMonitor:
    """Predictive health monitoring system for AI agents"""
    
    def __init__(self, port=None):
        """Initialize the predictive health monitor"""
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
        
        # Socket for health checks
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        try:
            self.health_socket.bind(f"tcp://*:{self.health_port}")
            logger.info(f"Health check socket bound to port {self.health_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind health check socket: {e}")
            if "Address already in use" in str(e):
                try:
                    alt_port = self.health_port + 10
                    self.health_socket.bind(f"tcp://*:{alt_port}")
                    self.health_port = alt_port
                    logger.info(f"Health check socket bound to alternative port {alt_port}")
                except zmq.error.ZMQError as e2:
                    logger.error(f"Failed to bind to alternative health port: {e2}")
            else:
                logger.warning("Health check functionality will be limited")
        
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
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        # Start health check thread
        self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_thread.start()
        
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

    def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Starting monitoring loop")
        while self.running:
            try:
                # Check agent health
                self._check_agent_health()
                
                # Check system resources
                self._check_system_resources()
                
                # Sleep for a bit
                time.sleep(30)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)

    def _health_check_loop(self):
        """Health check loop to respond to health check requests"""
        logger.info("Starting health check loop")
        while self.running:
            try:
                if self.health_socket.poll(1000, zmq.POLLIN):
                    message = self.health_socket.recv_json()
                    if message.get('action') == 'health_check':
                        response = {
                            'status': 'ok',
                            'timestamp': datetime.now().isoformat(),
                            'agent': 'PredictiveHealthMonitor'
                        }
                        self.health_socket.send_json(response)
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(1)

    def _check_agent_health(self):
        """Check the health of all agents"""
        for agent_name, config in self.agent_configs.items():
            try:
                # Create a socket to check the agent
                agent_socket = self.context.socket(zmq.REQ)
                agent_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
                agent_socket.setsockopt(zmq.LINGER, 0)
                agent_socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2 second timeout
                
                # Connect to the agent
                agent_host = config.get('host', 'localhost')
                agent_port = config.get('port')
                if not agent_port:
                    continue
                    
                agent_socket.connect(f"tcp://{agent_host}:{agent_port}")
                
                # Send health check request
                agent_socket.send_json({'action': 'health_check'})
                
                # Wait for response
                response = agent_socket.recv_json()
                
                # Update agent health status
                self.agent_health[agent_name] = {
                    'status': 'healthy',
                    'last_check': datetime.now().isoformat(),
                    'response': response
                }
                
                # Clean up
                agent_socket.close()
                
            except Exception as e:
                # Update agent health status
                self.agent_health[agent_name] = {
                    'status': 'unhealthy',
                    'last_check': datetime.now().isoformat(),
                    'error': str(e)
                }
                logger.warning(f"Agent {agent_name} health check failed: {e}")

    def _check_system_resources(self):
        """Check system resources"""
        try:
            # Basic system info
            system_info = {
                'hostname': self.hostname,
                'timestamp': datetime.now().isoformat()
            }
            
            # Try to get CPU and memory info if psutil is available
            try:
                import psutil
    except ImportError as e:
        print(f"Import error: {e}")
                system_info['cpu_percent'] = psutil.cpu_percent(interval=1)
                system_info['memory_percent'] = psutil.virtual_memory().percent
                system_info['disk_percent'] = psutil.disk_usage('/').percent
            except ImportError:
                system_info['cpu_percent'] = None
                system_info['memory_percent'] = None
                system_info['disk_percent'] = None
                
            # Log system info
            logger.debug(f"System resources: {system_info}")
            
        except Exception as e:
            logger.error(f"Error checking system resources: {e}")

    def run(self):
        """Main run loop"""
        logger.info("Starting main loop")
        while self.running:
            try:
                # Poll for messages with timeout
                if self.socket.poll(1000, zmq.POLLIN):
                    # Receive message
                    message = self.socket.recv_json()
                    logger.debug(f"Received message: {message}")
                    
                    # Process message
                    response = self._process_message(message)
                    
                    # Send response
                    self.socket.send_json(response)
                
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received, shutting down")
                self.running = False
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                # Try to send error response
                try:
                    self.socket.send_json({
                        'status': 'error',
                        'error': str(e),
                        'traceback': traceback.format_exc()
                    })
                except:
                    pass
                time.sleep(1)

    def _process_message(self, message):
        """Process incoming message"""
        action = message.get('action', '')
        
        if action == 'health_check':
            return {
                'status': 'ok',
                'timestamp': datetime.now().isoformat(),
                'agent': 'PredictiveHealthMonitor'
            }
        
        elif action == 'get_agent_health':
            agent_name = message.get('agent_name')
            if agent_name:
                return {
                    'status': 'ok',
                    'agent_name': agent_name,
                    'health': self.agent_health.get(agent_name, {'status': 'unknown'})
                }
            else:
                return {
                    'status': 'ok',
                    'agents': self.agent_health
                }
        
        elif action == 'get_system_health':
            return {
                'status': 'ok',
                'system': self._get_system_health(),
                'agents': self.agent_health
            }
        
        else:
            return {
                'status': 'error',
                'error': f"Unknown action: {action}"
            }

    def _get_system_health(self):
        """Get system health information"""
        system_health = {
            'hostname': self.hostname,
            'timestamp': datetime.now().isoformat()
        }
        
        # Try to get CPU and memory info if psutil is available
        try:
            import psutil
    except ImportError as e:
        print(f"Import error: {e}")
            system_health['cpu_percent'] = psutil.cpu_percent(interval=1)
            system_health['memory_percent'] = psutil.virtual_memory().percent
            system_health['disk_percent'] = psutil.disk_usage('/').percent
            system_health['boot_time'] = datetime.fromtimestamp(psutil.boot_time()).isoformat()
            
            # Network info
            net_io = psutil.net_io_counters()
            system_health['network'] = {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            }
            
        except ImportError:
            system_health['cpu_percent'] = None
            system_health['memory_percent'] = None
            system_health['disk_percent'] = None
            
        return system_health

    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources")
        self.running = False
        
        # Close ZMQ sockets
        if hasattr(self, 'socket'):
            self.socket.close()
        
        if hasattr(self, 'health_socket'):
            self.health_socket.close()
        
        # Close ZMQ context
        if hasattr(self, 'context'):
            self.context.term()
            
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