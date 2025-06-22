"""
Edge Router Agent
---------------
Lightweight router for direct communication between mainPC and PC2.
Uses msgpack for efficient serialization to reduce latency.
"""

import zmq
import msgpack
import time
import threading
import logging
import argparse
import traceback
import sys
import socket
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('edge_router.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("EdgeRouter")

# Default configuration
DEFAULT_LISTEN_PORT = 5555  # Main listening port for mainPC clients
DEFAULT_PC2_EMR_PORT = 5598  # Enhanced Model Router on PC2
DEFAULT_PC2_TRANSLATOR_PORT = 5563  # Consolidated Translator on PC2
DEFAULT_PC2_IP = "192.168.100.17"  # PC2 IP address
ZMQ_REQUEST_TIMEOUT = 10000  # 10 seconds timeout for requests

class EdgeRouter:
    """
    Edge Router for direct communication between mainPC and PC2 services.
    Uses msgpack for efficient serialization.
    """
    def __init__(self, listen_port: int, pc2_ip: str, pc2_emr_port: int, pc2_translator_port: int):
        """
        Initialize the Edge Router.
        
        Args:
            listen_port: Port to listen for requests from mainPC agents
            pc2_ip: IP address of PC2
            pc2_emr_port: Port for Enhanced Model Router on PC2
            pc2_translator_port: Port for Consolidated Translator on PC2
        """
        self.listen_port = listen_port
        self.pc2_ip = pc2_ip
        self.pc2_emr_port = pc2_emr_port
        self.pc2_translator_port = pc2_translator_port
        self.context = zmq.Context()
        self.running = True
        self.start_time = time.time()
        
        # Service connections to PC2 (REQ sockets)
        self.service_sockets = {}
        self.service_locks = {}  # Locks for thread safety
        
        # Performance metrics
        self.metrics = {
            "requests": 0,
            "errors": 0,
            "avg_latency": 0,
            "total_latency": 0,
            "service_metrics": {}
        }
        
        logger.info(f"Edge Router initializing with configuration:")
        logger.info(f"  Listen port: {listen_port}")
        logger.info(f"  PC2 IP: {pc2_ip}")
        logger.info(f"  PC2 EMR port: {pc2_emr_port}")
        logger.info(f"  PC2 Translator port: {pc2_translator_port}")
    
    def initialize_sockets(self):
        """Initialize all sockets"""
        # Initialize frontend socket (REP) for receiving requests
        self.frontend = self.context.socket(zmq.REP)
        self.frontend.bind(f"tcp://*:{self.listen_port}")
        logger.info(f"Listening for requests on port {self.listen_port}")
        
        # Initialize service connections to PC2
        self._init_service_socket("emr", f"tcp://{self.pc2_ip}:{self.pc2_emr_port}")
        self._init_service_socket("translator", f"tcp://{self.pc2_ip}:{self.pc2_translator_port}")
        
        # Initialize metrics for each service
        for service in self.service_sockets:
            self.metrics["service_metrics"][service] = {
                "requests": 0,
                "errors": 0,
                "avg_latency": 0,
                "total_latency": 0
            }
    
    def _init_service_socket(self, service_name: str, endpoint: str):
        """Initialize a service socket connection to PC2"""
        self.service_sockets[service_name] = self.context.socket(zmq.REQ)
        self.service_sockets[service_name].setsockopt(zmq.LINGER, 0)
        self.service_sockets[service_name].setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.service_sockets[service_name].connect(endpoint)
        self.service_locks[service_name] = threading.Lock()
        logger.info(f"Connected to {service_name} service at {endpoint}")
    
    def get_service_for_request(self, request: Dict[str, Any]) -> Optional[str]:
        """
        Determine which PC2 service to route the request to.
        
        Args:
            request: The request data
        
        Returns:
            Service name or None if service can't be determined
        """
        service_type = request.get("service", "").lower()
        
        if service_type == "emr" or service_type == "model" or "model_name" in request:
            return "emr"
        elif service_type == "translator" or service_type == "translation" or "translate" in request:
            return "translator"
        
        # Try to infer from the content
        if "prompt" in request or "text" in request and "model" in request:
            return "emr"
        elif "source_lang" in request or "target_lang" in request or "text_to_translate" in request:
            return "translator"
        
        return None
    
    def forward_request(self, service: str, request_data: bytes) -> Tuple[bool, bytes]:
        """
        Forward a request to the specified PC2 service.
        
        Args:
            service: Service name
            request_data: Request data as msgpack-encoded bytes
        
        Returns:
            Tuple of (success, response data)
        """
        start_time = time.time()
        success = False
        response_data = None
        
        if service not in self.service_sockets:
            error_msg = f"Unknown service: {service}"
            logger.error(error_msg)
            return False, msgpack.packb({"status": "error", "message": error_msg})
        
        try:
            # Use lock to ensure thread safety
            with self.service_locks[service]:
                # Send request to PC2 service
                self.service_sockets[service].send(request_data)
                
                # Wait for response
                response_raw = self.service_sockets[service].recv()
                
                # Update metrics
                latency = time.time() - start_time
                metrics = self.metrics["service_metrics"][service]
                metrics["requests"] += 1
                metrics["total_latency"] += latency
                metrics["avg_latency"] = metrics["total_latency"] / metrics["requests"]
                
                success = True
                response_data = response_raw
                
                logger.info(f"Request to {service} successful (latency: {latency:.3f}s)")
                
        except zmq.Again:
            error_msg = f"Timeout connecting to {service} service on PC2"
            logger.error(error_msg)
            self.metrics["service_metrics"][service]["errors"] += 1
            response_data = msgpack.packb({"status": "error", "message": error_msg})
            
        except Exception as e:
            error_msg = f"Error forwarding request to {service}: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.metrics["service_metrics"][service]["errors"] += 1
            response_data = msgpack.packb({"status": "error", "message": error_msg})
            
        return success, response_data
    
    def handle_request(self, request_data: bytes) -> bytes:
        """
        Handle an incoming request.
        
        Args:
            request_data: Request data as msgpack-encoded bytes
        
        Returns:
            Response data as msgpack-encoded bytes
        """
        self.metrics["requests"] += 1
        start_time = time.time()
        
        try:
            # Try to decode request as msgpack
            request = msgpack.unpackb(request_data)
            
            # Special case: status request
            if request.get("action") == "status":
                return msgpack.packb({
                    "status": "ok",
                    "uptime": time.time() - self.start_time,
                    "metrics": self.metrics
                })
            
            # Determine which service to forward to
            service = self.get_service_for_request(request)
            
            if not service:
                error_msg = "Could not determine target service for request"
                logger.warning(error_msg)
                self.metrics["errors"] += 1
                return msgpack.packb({"status": "error", "message": error_msg})
            
            # Forward request to appropriate service
            success, response_data = self.forward_request(service, request_data)
            
            # Update overall metrics
            latency = time.time() - start_time
            self.metrics["total_latency"] += latency
            self.metrics["avg_latency"] = self.metrics["total_latency"] / self.metrics["requests"]
            
            return response_data
            
        except Exception as e:
            error_msg = f"Error handling request: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.metrics["errors"] += 1
            return msgpack.packb({"status": "error", "message": error_msg})
    
    def run(self):
        """Run the Edge Router"""
        try:
            self.initialize_sockets()
            
            logger.info("Edge Router started and ready to handle requests")
            
            while self.running:
                try:
                    # Wait for a request from frontend
                    request_data = self.frontend.recv()
                    
                    # Handle the request
                    response_data = self.handle_request(request_data)
                    
                    # Send response back to client
                    self.frontend.send(response_data)
                    
                except zmq.Again:
                    # Timeout waiting for request, continue loop
                    continue
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    logger.error(traceback.format_exc())
                    
                    # Try to send error response if possible
                    try:
                        self.frontend.send(msgpack.packb({"status": "error", "message": str(e)}))
                    except:
                        pass
                    
        except KeyboardInterrupt:
            logger.info("Shutting down Edge Router...")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown of the Edge Router"""
        self.running = False
        
        # Close all sockets
        try:
            if hasattr(self, 'frontend'):
                self.frontend.close()
            
            for service, socket in self.service_sockets.items():
                socket.close()
                
            self.context.term()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        logger.info("Edge Router shut down successfully")

def is_port_available(port: int) -> bool:
    """Check if a port is available for binding"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Edge Router for optimized mainPC to PC2 communication')
    parser.add_argument('--port', type=int, default=DEFAULT_LISTEN_PORT, 
                        help=f'Port to listen on (default: {DEFAULT_LISTEN_PORT})')
    parser.add_argument('--pc2-ip', type=str, default=DEFAULT_PC2_IP, 
                        help=f'PC2 IP address (default: {DEFAULT_PC2_IP})')
    parser.add_argument('--pc2-emr-port', type=int, default=DEFAULT_PC2_EMR_PORT, 
                        help=f'PC2 Enhanced Model Router port (default: {DEFAULT_PC2_EMR_PORT})')
    parser.add_argument('--pc2-translator-port', type=int, default=DEFAULT_PC2_TRANSLATOR_PORT, 
                        help=f'PC2 Consolidated Translator port (default: {DEFAULT_PC2_TRANSLATOR_PORT})')
    parser.add_argument('--debug', action='store_true', 
                        help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if port is available
    if not is_port_available(args.port):
        logger.error(f"Port {args.port} is already in use. Please choose a different port.")
        sys.exit(1)
    
    # Start the Edge Router
    router = EdgeRouter(
        args.port, 
        args.pc2_ip,
        args.pc2_emr_port,
        args.pc2_translator_port
    )
    
    router.run() 