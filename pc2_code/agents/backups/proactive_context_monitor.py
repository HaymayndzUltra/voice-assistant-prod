#!/usr/bin/env python3
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


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("pc2_code", ".."))))
from common.utils.path_env import get_path, join_path, get_file_path
# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import dynamic CLI parser with fallback
try:
from pc2_code.agents.utils.config_parser import parse_agent_args
    except ImportError as e:
        print(f"Import error: {e}")
    # Config is loaded at the module level
except ImportError:
    class DummyArgs(BaseAgent):
        host = 'localhost'
    _agent_args = DummyArgs()

# Configure logging
log_file_path = join_path("logs", "proactive_context_monitor.log")
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

class ProactiveContextMonitor:
    """Proactive Context Monitor Agent for analyzing context and triggering proactive actions."""
    
    def __init__(self, port=None, health_check_port=None):
         super().__init__(name="DummyArgs", port=None)
"""Initialize the Proactive Context Monitor Agent."""
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
        
        class HealthCheckHandler
from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config
from common.env_helpers import get_env

# Load configuration at the module level
config = load_config()(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b"OK")
                
            def log_message(self, format, *args):
                logger.debug("%s - %s", self.address_string(), format % args)
        
        server = HTTPServer(('localhost', self.health_port), HealthCheckHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
    
    def _start_background_threads(self):
        """Start background processing threads."""
        self.context_thread = threading.Thread(target=self._context_processing_loop, daemon=True)
        self.context_thread.start()
        logger.info("Context processing thread started")
    
    def _context_processing_loop(self):
        """Background thread for processing context updates."""
        while self.running:
            try:
                # Process any pending context updates
                self._process_context_updates()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in context processing loop: {e}")
    
    def _process_context_updates(self):
        """Process pending context updates and trigger proactive actions."""
        try:
            # Process context history and trigger actions as needed
            if self.context_history:
                latest_context = self.context_history[-1]
                # TODO: Implement context analysis and proactive action triggers
                pass
        except Exception as e:
            logger.error(f"Error processing context updates: {e}")
    
    def _health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            'status': 'success',
            'agent': 'ProactiveContextMonitor',
            'timestamp': datetime.now().isoformat(),
            'context_history_length': len(self.context_history),
            'context_thread_alive': self.context_thread.is_alive(),
            'port': self.main_port
        }
    
    def run(self):
        """Main run loop."""
        logger.info(f"Proactive Context Monitor starting on port {self.main_port}")
        try:
            while self.running:
                try:
                    # Wait for messages with timeout
                    if self.socket.poll(1000) == 0:
                        continue
                    
                    # Receive and process message
                    message = self.socket.recv_json()
                    response = self.handle_message(message)
                    self.socket.send_json(response)
                    
                except zmq.error.ZMQError as e:
                    if e.errno == zmq.EAGAIN:
                        continue
                    logger.error(f"ZMQ error in main loop: {e}")
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            self.cleanup()
    
    def handle_message(self, message: Any) -> Dict[str, Any]:
        """Handle incoming messages.
        
        Args:
            message: The message to handle, expected to be a dictionary
            
        Returns:
            Response message dictionary
        """
        try:
            # Type check the message
            if not isinstance(message, dict):
                return {'status': 'error', 'message': 'Message must be a dictionary'}
                
            action = message.get('action', '')
            if action == 'update_context':
                # Add to context history
                self.context_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'context': message.get('context', {})
                })
                return {'status': 'success'}
            elif action == 'get_context':
                return {
                    'status': 'success',
                    'context': self.context_history[-1] if self.context_history else {}
                }
            elif action == 'health_check':
                return self._health_check()
            else:
                return {'status': 'error', 'message': f'Unknown action: {action}'}
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up...")
        self.running = False
        if hasattr(self, 'context_thread'):
            self.context_thread.join(timeout=1)
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        logger.info("Cleanup complete")


    
    def _get_health_status(self) -> dict:

    
        """Return health status information."""

    
        base_status = super()._get_health_status()

    
        # Add any additional health information specific to DummyArgs

    
        base_status.update({

    
            'service': 'DummyArgs',

    
            'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,

    
            'additional_info': {}

    
        })

    
        return base_status
    
    def stop(self):
        """Stop the agent gracefully."""
        self.running = False



if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = DummyArgs()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()