import os
import zmq
import json
import logging
from typing import Dict, Any, Optional
import sys
import time
from pathlib import Path
import socket

# Add project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import PC2 configuration system
from pc2_code.config.system_config import get_service_host, get_service_port

# Import the new service discovery client
from main_pc_code.utils.service_discovery_client import register_service, discover_service, get_service_address

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join('logs', 'unified_memory_reasoning_agent.log'))
    ]
)
logger = logging.getLogger(__name__)

class UnifiedMemoryReasoningAgent:
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        
        # Get host and port from environment or config
        self.host = get_service_host('unified_memory', '0.0.0.0')
        self.port = get_service_port('unified_memory', 5596)
        
        # Bind to all interfaces
        try:
            self.socket.bind(f"tcp://{self.host}:{self.port}")
            logger.info(f"Unified Memory Reasoning Agent listening on {self.host}:{self.port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind to port {self.port}: {str(e)}")
            raise
        
        # Initialize memory state
        self.memory_state = {}
        
        # Register with SystemDigitalTwin using service discovery
        self._register_with_service_discovery()
        
    def _register_with_service_discovery(self):
        """
        Register this agent with the SystemDigitalTwin service registry.
        Uses the new service discovery client.
        """
        # Retry settings
        max_retries = 3
        retry_delay = 1  # seconds
        
        try:
            # Get IP address for registration
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))  # Doesn't have to be reachable
                my_ip = s.getsockname()[0]
                s.close()
            except Exception as e:
                logger.warning(f"Failed to determine IP address: {e}, using configured host")
                my_ip = self.host if self.host != '0.0.0.0' else 'localhost'
            
            # Prepare extra service information
            additional_info = {
                "api_version": "1.0",
                "supports_secure_zmq": os.environ.get("SECURE_ZMQ", "0") == "1",
                "supports_batching": True,
                "last_started": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Check if we should use localhost for SystemDigitalTwin
            manual_sdt_address = None
            if os.environ.get("FORCE_LOCAL_SDT", "0") == "1":
                manual_sdt_address = "tcp://localhost:7120"
                logger.info(f"Using forced local SDT address: {manual_sdt_address}")
            
            # Attempt to register with retries
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"Registering with service discovery as UnifiedMemoryReasoningAgent at {my_ip}:{self.port} (attempt {attempt} of {max_retries})")
                    response = register_service(
                        name="UnifiedMemoryReasoningAgent",
                        location="PC2",
                        ip=my_ip,
                        port=self.port,
                        additional_info=additional_info,
                        manual_sdt_address=manual_sdt_address
                    )
                    
                    # Check response
                    if response.get("status") == "SUCCESS":
                        logger.info("Successfully registered with service discovery")
                        return True
                    else:
                        logger.warning(f"Registration attempt {attempt} failed: {response.get('message', 'Unknown error')}")
                        
                        # If this is not the last attempt, wait and try again
                        if attempt < max_retries:
                            logger.info(f"Retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                        else:
                            logger.error(f"All registration attempts failed")
                            return False
                            
                except Exception as e:
                    # If this is not the last attempt, wait and try again
                    logger.warning(f"Error during registration attempt {attempt}: {e}")
                    if attempt < max_retries:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"All registration attempts failed")
                        return False
            
            return False  # Should not reach here, but just in case
            
        except Exception as e:
            logger.error(f"Error registering with service discovery: {e}")
            logger.warning("Agent will continue to function locally, but won't be discoverable by other agents")
            return False
    
    def _discover_digital_twin(self):
        """
        Discover the SystemDigitalTwin service using service discovery.
        Used as an example of how to discover other services.
        """
        try:
            logger.info("Attempting to discover SystemDigitalTwin service")
            
            # Check if we should use localhost for SystemDigitalTwin
            manual_sdt_address = None
            if os.environ.get("FORCE_LOCAL_SDT", "0") == "1":
                manual_sdt_address = "tcp://localhost:7120"
                logger.info(f"Using forced local SDT address for discovery: {manual_sdt_address}")
            
            response = discover_service("SystemDigitalTwin", manual_sdt_address=manual_sdt_address)
            
            if response.get("status") == "SUCCESS" and "payload" in response:
                service_info = response["payload"]
                logger.info(f"Found SystemDigitalTwin service: {service_info}")
                return service_info
            else:
                logger.warning(f"Failed to discover SystemDigitalTwin: {response.get('message', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error discovering SystemDigitalTwin service: {e}")
            return None
        
    def start(self):
        try:
            logger.info("Starting Unified Memory Reasoning Agent...")
            
            # Example of how to discover another service
            sdt_info = self._discover_digital_twin()
            if sdt_info:
                logger.info(f"Will communicate with SystemDigitalTwin at {sdt_info.get('ip')}:{sdt_info.get('port')}")
            
            # Main processing loop
            while True:
                # Receive message
                identity, _, message = self.socket.recv_multipart()
                message = json.loads(message.decode())
                logger.info(f"Received message: {message}")
                
                # Process message
                response = self.process_message(message)
                
                # Send response
                self.socket.send_multipart([
                    identity,
                    b'',
                    json.dumps(response).encode()
                ])
                
        except KeyboardInterrupt:
            logger.info("Shutting down Unified Memory Reasoning Agent...")
        finally:
            self._cleanup()
            
    def _cleanup(self):
        """Clean up resources before exit"""
        logger.info("Cleaning up resources...")
        # Close main socket
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
        
        # Terminate ZMQ context
        if hasattr(self, 'context') and self.context:
            self.context.term()
            
    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process message and return response
        
        Args:
            message: The incoming message to process
            
        Returns:
            Response message
        """
        # Process message and return response
        return {"status": "success", "message": "Memory updated"}
        
if __name__ == "__main__":
    agent = UnifiedMemoryReasoningAgent()
    agent.start() 