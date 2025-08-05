#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
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
import yaml
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path


# Import path manager for containerization-friendly paths
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[2]

from common.utils.path_manager import PathManager
# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    

# Import necessary modules
try:
    from common.core.base_agent import BaseAgent
    from pc2_code.agents.utils.config_loader import Config
    # Config is loaded at the module level
    config = Config().get_config()
except ImportError as e:
    print(f"Import error: {e}")
    config = None

# Configure logging
log_directory = os.path.join('logs')
os.makedirs(log_directory, exist_ok=True)
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('ProactiveContextMonitor')

# Load network configuration at the module level
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = Path(PathManager.get_project_root() / "config" / "network_config.yaml"
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": get_mainpc_ip(),
            "pc2_ip": get_pc2_ip(),
            "bind_address": os.environ.get("BIND_ADDRESS", "0.0.0.0"),
            "secure_zmq": False,
            "ports": {
                "proactive_monitor": int(os.environ.get("PROACTIVE_MONITOR_PORT", 7119),
                "proactive_health": int(os.environ.get("PROACTIVE_MONITOR_HEALTH_PORT", 8119),
                "error_bus": int(os.environ.get("ERROR_BUS_PORT", 7150)
            }
        }

# Load network configuration
network_config = load_network_config()

# Get configuration values
MAIN_PC_IP = get_mainpc_ip()
PC2_IP = network_config.get("pc2_ip", get_pc2_ip()
BIND_ADDRESS = network_config.get("bind_address", os.environ.get("BIND_ADDRESS", "0.0.0.0")
PROACTIVE_MONITOR_PORT = network_config.get("ports", {}).get("proactive_monitor", int(os.environ.get("PROACTIVE_MONITOR_PORT", 7119))
PROACTIVE_MONITOR_HEALTH_PORT = network_config.get("ports", {}).get("proactive_health", int(os.environ.get("PROACTIVE_MONITOR_HEALTH_PORT", 8119))
ERROR_BUS_PORT = network_config.get("ports", {}).get("error_bus", int(os.environ.get("ERROR_BUS_PORT", 7150))

class ProactiveContextMonitor(BaseAgent):
    """Proactive Context Monitor Agent for analyzing context and triggering proactive actions."""
    
    def __init__(self, port=None, health_check_port=None):
        # Initialize agent state before BaseAgent
        self.running = True
        self.request_count = 0
        self.main_pc_connections = {}
        self.start_time = time.time()
        self.context_history = []
        
        # Initialize BaseAgent with proper name and port
        super().__init__(
            name="ProactiveContextMonitor", 
            port=port if port is not None else PROACTIVE_MONITOR_PORT,
            health_check_port=health_check_port if health_check_port is not None else PROACTIVE_MONITOR_HEALTH_PORT
        )
        
        # Set up error reporting
        self.setup_error_reporting()
        
        # Start background processing threads
        self._start_background_threads()
        
        logger.info(f"Proactive Context Monitor initialized on port {self.port}")
    
    def setup_error_reporting(self):
        """Set up error reporting to the central Error Bus."""
        try:
            self.error_bus_host = PC2_IP
            self.error_bus_port = ERROR_BUS_PORT
            self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
            self.error_bus_pub = self.context.socket(zmq.PUB)
            self.error_bus_pub.connect(self.error_bus_endpoint)
            logger.info(f"Connected to Error Bus at {self.error_bus_endpoint}")
        except Exception as e:
            logger.error(f"Failed to set up error reporting: {e}")
    
        # PC2 Error Bus Integration (Phase 1.3)
        self.error_publisher = create_pc2_error_publisher("proactive_context_monitor")
    def report_error(self, error_type, message, severity="ERROR"):
        """Report an error to the central Error Bus."""
        try:
            if hasattr(self, 'error_bus_pub'):
                error_report = {
                    "timestamp": datetime.now().isoformat(),
                    "agent": self.name,
                    "type": error_type,
                    "message": message,
                    "severity": severity
                }
                self.error_bus_pub.send_multipart([
                    b"ERROR",
                    json.dumps(error_report).encode('utf-8')
                ])
                logger.info(f"Reported error: {error_type} - {message}")
        except Exception as e:
            logger.error(f"Failed to report error: {e}")
    
    def _start_background_threads(self):
        """Start background processing threads."""
        # Context analysis thread
        self.analysis_thread = threading.Thread(target=self._context_analysis_loop)
        self.analysis_thread.daemon = True
        self.analysis_thread.start()
        logger.info("Started background analysis thread")
    
    def _context_analysis_loop(self):
        """Background thread for analyzing context and triggering proactive actions."""
        while self.running:
            try:
                # Analyze context and trigger actions if needed
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Error in context analysis loop: {e}")
                self.report_error("ANALYSIS_ERROR", f"Error in context analysis: {e}")
    
    def _get_health_status(self):
        """Return health status information."""
        base_status = super()._get_health_status()
        base_status.update({
            'status': 'ok',
            'service': 'ProactiveContextMonitor',
            'uptime': time.time() - self.start_time,
            'context_history_length': len(self.context_history) if hasattr(self, 'context_history') else 0,
            'request_count': self.request_count
        })
        return base_status
    
    def handle_request(self, request):
        """Handle incoming requests."""
        try:
            action = request.get('action', '')
            
            if action == 'add_context':
                return self._handle_add_context(request)
            elif action == 'get_context_history':
                return self._handle_get_context_history(request)
            elif action == 'clear_context_history':
                return self._handle_clear_context_history(request)
            elif action == 'health_check':
                return self._get_health_status()
            else:
                return {'status': 'error', 'message': f'Unknown action: {action}'}
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            self.report_error("REQUEST_ERROR", f"Error handling request: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _handle_add_context(self, request):
        """Handle adding context to history."""
        try:
            context = request.get('context')
            if not context:
                return {'status': 'error', 'message': 'Missing context data'}
            
            # Add timestamp to context
            context_entry = {
                'timestamp': datetime.now().isoformat(),
                'data': context
            }
            
            # Add to history
            self.context_history.append(context_entry)
            
            # Trim history if too long
            max_history = 100
            if len(self.context_history) > max_history:
                self.context_history = self.context_history[-max_history:]
            
            return {'status': 'success', 'message': 'Context added'}
        except Exception as e:
            logger.error(f"Error adding context: {e}")
            self.report_error("CONTEXT_ERROR", f"Error adding context: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _handle_get_context_history(self, request):
        """Handle getting context history."""
        try:
            limit = request.get('limit', 10)
            try:
                limit = int(limit)
            except (ValueError, TypeError):
                limit = 10
            
            history = self.context_history[-limit:] if self.context_history else []
            
            return {
                'status': 'success',
                'history': history,
                'count': len(history),
                'total': len(self.context_history)
            }
        except Exception as e:
            logger.error(f"Error getting context history: {e}")
            self.report_error("HISTORY_ERROR", f"Error getting context history: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _handle_clear_context_history(self, request):
        """Handle clearing context history."""
        try:
            self.context_history = []
            return {'status': 'success', 'message': 'Context history cleared'}
        except Exception as e:
            logger.error(f"Error clearing context history: {e}")
            self.report_error("CLEAR_ERROR", f"Error clearing context history: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def run(self):
        """Main run loop."""
        logger.info(f"Proactive Context Monitor starting on port {self.port}")
        
        try:
            while self.running:
                try:
                    # Use non-blocking recv with timeout
                    if self.socket.poll(timeout=1000) != 0:  # 1 second timeout
                        message = self.socket.recv_json()
                        logger.debug(f"Received message: {message}")
                        
                        # Process message
                        response = self.handle_request(message)
                        
                        # Send response
                        self.socket.send_json(response)
                        self.request_count += 1
                        
                except zmq.error.ZMQError as e:
                    logger.error(f"ZMQ error: {e}")
                    self.report_error("ZMQ_ERROR", str(e)
                    time.sleep(1)  # Sleep to avoid tight loop on error
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    self.report_error("PROCESSING_ERROR", str(e)
                    # Try to send error response
                    try:
                        self.socket.send_json({
                            'status': 'error',
                            'message': f'Internal server error: {str(e)}'
                        })
                    except:
                        pass
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("Proactive Context Monitor interrupted")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up Proactive Context Monitor resources")
        self.running = False
        
        # Close ZMQ sockets
        if hasattr(self, 'socket'):
            try:
                self.socket.close()
                logger.info("Closed main socket")
            except Exception as e:
                logger.error(f"Error closing main socket: {e}")
        
        # Close error bus socket
        if hasattr(self, 'error_bus_pub'):
            try:
                self.error_bus_pub.close()
                logger.info("Closed error bus socket")
            except Exception as e:
                logger.error(f"Error closing error bus socket: {e}")
        
        # Close any connections to other services
        for service_name, socket in self.main_pc_connections.items():
            try:
                socket.close()
                logger.info(f"Closed connection to {service_name}")
            except Exception as e:
                logger.error(f"Error closing connection to {service_name}: {e}")
        
        # Join threads
        if hasattr(self, 'analysis_thread'):
            try:
                self.analysis_thread.join(timeout=2.0)
                logger.info("Joined analysis thread")
            except Exception as e:
                logger.error(f"Error joining analysis thread: {e}")
        
        # Call parent cleanup
        try:
            super().cleanup()
            logger.info("Called parent cleanup")
        except Exception as e:
            logger.error(f"Error in parent cleanup: {e}")
        
        logger.info("Proactive Context Monitor cleanup complete")
    
    def connect_to_main_pc_service(self, service_name: str):
        """Connect to a service on the main PC."""
        try:
            # Get service details from config
            service_ports = network_config.get('ports', {})
            if service_name not in service_ports:
                logger.error(f"Service '{service_name}' not found in network configuration")
                return False
            
            # Create socket
            socket = self.context.socket(zmq.REQ)
            
            # Connect to service
            port = service_ports[service_name]
            socket.connect(f"tcp://{MAIN_PC_IP}:{port}")
            logger.info(f"Connected to {service_name} at {MAIN_PC_IP}:{port}")
            
            # Store socket
            self.main_pc_connections[service_name] = socket
            
            return True
        except Exception as e:
            logger.error(f"Error connecting to service '{service_name}': {e}")
            self.report_error("CONNECTION_ERROR", f"Failed to connect to {service_name}: {e}")
            return False

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