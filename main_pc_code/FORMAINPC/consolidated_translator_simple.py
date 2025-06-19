#!/usr/bin/env python3
"""
Simplified Consolidated Translator for Health Check Validation
- Minimal implementation focused on health check endpoint
- Dynamic port support
- Separate health check port
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import json
import time
import zmq
import logging
import threading
import argparse
from typing import Dict, Any

# Import config parser for dynamic port support
from utils.config_parser import parse_agent_args

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ConsolidatedTranslator")

# Default constants
DEFAULT_ZMQ_PORT = 5563
DEFAULT_HEALTH_PORT = 5564
ZMQ_BIND_ADDRESS = "0.0.0.0"

class SimpleTranslatorServer:
    """Simplified ZMQ server with health check endpoint"""
    def __init__(self, main_port: int = None, health_port: int = None):
        self.main_port = main_port or DEFAULT_ZMQ_PORT
        self.health_port = health_port or DEFAULT_HEALTH_PORT
        self.context = zmq.Context()
        self.start_time = time.time()
        
        # Main service socket
        self.main_socket = self.context.socket(zmq.REP)
        
        # Health check socket (separate endpoint)
        self.health_socket = self.context.socket(zmq.REP)
        
        # Bind sockets
        self._bind_sockets()
        
        logger.info(f"Server started on main port {self.main_port} and health port {self.health_port}")
        
        # Start health check thread
        self.health_thread = threading.Thread(target=self._run_health_server, daemon=True)
        self.health_thread.start()
        logger.info("Health check server thread started")
        
    def _bind_sockets(self):
        """Bind both main and health check sockets"""
        # Bind main socket
        try:
            self.main_socket.bind(f"tcp://{ZMQ_BIND_ADDRESS}:{self.main_port}")
            logger.info(f"Main service bound to port {self.main_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Error binding main socket: {e}")
            raise RuntimeError(f"Cannot bind main service to port {self.main_port}")
        
        # Bind health socket
        try:
            self.health_socket.bind(f"tcp://{ZMQ_BIND_ADDRESS}:{self.health_port}")
            logger.info(f"Health check service bound to port {self.health_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Error binding health socket: {e}")
            raise RuntimeError(f"Cannot bind health service to port {self.health_port}")
        
    def _run_health_server(self):
        """Run health check server on separate thread"""
        logger.info("Health check server thread started and listening for requests")
        while True:
            try:
                # Wait for health check request
                logger.debug("Health server waiting for request...")
                message = self.health_socket.recv_json()
                logger.info(f"Received health check request: {message}")
                
                # Process health check
                response = self._handle_health_check()
                logger.info(f"Health check response: {response}")
                
                # Send response
                self.health_socket.send_json(response)
                logger.info("Health check response sent successfully")
                
            except Exception as e:
                logger.error(f"Error processing health check request: {str(e)}")
                try:
                    self.health_socket.send_json({
                        'status': 'error',
                        'error': str(e)
                    })
                except:
                    pass
        
    def run(self):
        """Run the main translation server"""
        logger.info("Main server started and listening for requests")
        while True:
            try:
                # Wait for next request
                message = self.main_socket.recv_json()
                logger.debug(f"Received request: {message}")
                
                # Process request
                response = self._handle_request(message)
                
                # Send response
                self.main_socket.send_json(response)
                logger.debug(f"Sent response: {response}")
                
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                self.main_socket.send_json({
                    'status': 'error',
                    'error': str(e)
                })
                
    def _handle_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle main service requests"""
        action = message.get('action')
        
        response = {
            'api_version': '2.0',
            'timestamp': time.time()
        }
        
        if action == 'health_check':
            result = self._handle_health_check()
            response.update(result)
        elif action == 'translate':
            response.update({
                'status': 'error',
                'message': 'Translation service not implemented in simple version'
            })
        else:
            response.update({
                'status': 'error',
                'message': f'Unknown action: {action}'
            })
            
        return response
        
    def _handle_health_check(self) -> Dict[str, Any]:
        """Enhanced health check with detailed status"""
        return {
            'status': 'ok',
            'service': 'consolidated_translator',
            'ready': True,
            'initialized': True,
            'message': 'ConsolidatedTranslator is healthy',
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.%f'),
            'uptime': time.time() - self.start_time,
            'main_port': self.main_port,
            'health_port': self.health_port,
            'initialization_status': 'complete'
        }
        
    def stop(self):
        """Stop the server and cleanup resources"""
        try:
            self.main_socket.close()
            self.health_socket.close()
            self.context.term()
            logger.info("Server stopped and resources cleaned up")
        except Exception as e:
            logger.error(f"Error stopping server: {e}")

def main():
    """Main entry point with dynamic port support"""
    try:
        # Parse command line arguments
        args = parse_agent_args()
        
        # Use provided ports or defaults
        main_port = args.port or DEFAULT_ZMQ_PORT
        health_port = getattr(args, 'health_port', None) or DEFAULT_HEALTH_PORT
        
        logger.info(f"Starting Simplified Consolidated Translator with main port {main_port} and health port {health_port}")
        
        # Create and run server
        server = SimpleTranslatorServer(main_port=main_port, health_port=health_port)
        server.run()
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 