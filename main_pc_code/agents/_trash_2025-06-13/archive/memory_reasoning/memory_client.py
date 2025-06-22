from src.core.base_agent import BaseAgent
import zmq
import json
import logging
from typing import Dict, Any, Optional

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MemoryClient(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="MemoryClient")
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.connect(f"tcp://localhost:{port}")
        logger.info(f"MemoryClient initialized, connected to port {port}")

    def _send_request(self, request: Dict) -> Dict:
        try:
            self.socket.send_json(request)
            response = self.socket.recv_json()
            return response
        except Exception as e:
            logger.error(f"Error sending request: {e}")
            return {"status": "error", "message": str(e)}

    def store_memory(self, key: str, value: Any, memory_type: str = "short_term") -> Dict:
        request = {
            "request_type": "store_memory",
            "key": key,
            "value": value,
            "memory_type": memory_type
        }
        return self._send_request(request)

    def retrieve_memory(self, key: str, memory_type: str = "short_term") -> Dict:
        request = {
            "request_type": "retrieve_memory",
            "key": key,
            "memory_type": memory_type
        }
        return self._send_request(request)

    def update_context(self, context_key: str, context_value: Any) -> Dict:
        request = {
            "request_type": "update_context",
            "context_key": context_key,
            "context_value": context_value
        }
        return self._send_request(request)

    def get_context(self, context_key: str) -> Dict:
        request = {
            "request_type": "get_context",
            "context_key": context_key
        }
        return self._send_request(request)

    def store_error_pattern(self, pattern_type: str, pattern: Dict) -> Dict:
        request = {
            "request_type": "store_error_pattern",
            "pattern_type": pattern_type,
            "pattern": pattern
        }
        return self._send_request(request)

    def get_error_patterns(self, pattern_type: str) -> Dict:
        request = {
            "request_type": "get_error_patterns",
            "pattern_type": pattern_type
        }
        return self._send_request(request)

    def health_check(self) -> Dict:
        request = {
            "request_type": "health_check"
        }
        return self._send_request(request)

    def close(self):
        self.socket.close()
        self.context.term()
        logger.info("MemoryClient connection closed")

# Example usage
if __name__ == "__main__":
    client = MemoryClient()
    
    # Test storing and retrieving memory
    client.store_memory("test_key", "test_value")
    result = client.retrieve_memory("test_key")
    print(f"Retrieved memory: {result}")
    
    # Test context operations
    client.update_context("current_user", "John")
    context = client.get_context("current_user")
    print(f"Retrieved context: {context}")
    
    # Test health check
    health = client.health_check()
    print(f"Health check: {health}")
    
    client.close() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise