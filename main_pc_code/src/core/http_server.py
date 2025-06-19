"""
Base HTTP Server for Agent Health Checks
Provides a simple HTTP server that all agents can use for health checks
"""

import http.server
import socketserver
import threading
import logging
import os
import signal
import sys
import socket
from typing import Optional, Tuple, Type, cast, Any

logger = logging.getLogger(__name__)

class HealthCheckHandler(http.server.BaseHTTPRequestHandler):
    """Simple handler for health check requests."""
    
    def do_GET(self):
        """Handle GET requests by returning 200 OK."""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"OK")
        
    def log_message(self, format: str, *args) -> None:
        """Override to use our logger instead of printing to stderr."""
        logger.debug(f"{self.address_string()} - {format%args}")

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Threaded TCP Server with address reuse"""
    allow_reuse_address = True
    daemon_threads = True

class AgentHTTPServer:
    """HTTP server for agent health checks"""
    
    def __init__(self, port: int, handler_class: Optional[Type[http.server.BaseHTTPRequestHandler]] = None):
        """Initialize the HTTP server
        
        Args:
            port: Port to listen on
            handler_class: Optional custom handler class
        """
        self.port = port
        self.handler_class = handler_class or HealthCheckHandler
        self.server: Optional[ThreadedTCPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.running = False

    def _find_available_port(self, start_port: int) -> int:
        """Find an available port starting from start_port
        
        Args:
            start_port: Port to start searching from
            
        Returns:
            Available port number
        """
        port = start_port
        while port < 65535:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('127.0.0.1', port))
                    return port
            except OSError:
                port += 1
        raise RuntimeError("No available ports found")

    def start(self):
        """Start the HTTP server in a background thread"""
        if self.running:
            logger.warning("HTTP server already running")
            return

        try:
            # Try to find an available port
            self.port = self._find_available_port(self.port)
            
            # Create and start the server
            self.server = ThreadedTCPServer(('127.0.0.1', self.port), cast(Any, self.handler_class))
            self.running = True
            
            # Start server in background thread
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            logger.info(f"HTTP server started on port {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
            self.running = False
            return False

    def stop(self):
        """Stop the HTTP server"""
        if not self.running:
            return

        try:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
            self.running = False
            logger.info(f"HTTP server stopped on port {self.port}")
        except Exception as e:
            logger.error(f"Error stopping HTTP server: {e}")

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()

def setup_health_check_server(port: int) -> Optional[AgentHTTPServer]:
    """Set up a health check server on the specified port.
    
    Args:
        port: Port to listen on
        
    Returns:
        AgentHTTPServer instance if successful, None otherwise
    """
    try:
        server = AgentHTTPServer(port)
        if server.start():
            return server
        return None
    except Exception as e:
        logger.error(f"Failed to set up health check server: {e}")
        return None 