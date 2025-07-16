from main_pc_code.src.core.base_agent import BaseAgent
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

class ChainOfThoughtClient(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ChainOfThoughtClient")
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.connect(f"tcp://localhost:{port}")
        logger.info(f"ChainOfThoughtClient initialized, connected to port {port}")

    def _send_request(self, request: Dict) -> Dict:
        try:
            self.socket.send_json(request)
            response = self.socket.recv_json()
            return response
        except Exception as e:
            logger.error(f"Error sending request: {e}")
            return {"status": "error", "message": str(e)}

    def start_reasoning(self, reasoning_type: str, context: Dict) -> Dict:
        request = {
            "request_type": "start_reasoning",
            "reasoning_type": reasoning_type,
            "context": context
        }
        return self._send_request(request)

    def continue_reasoning(self, reasoning_id: str, step_result: Dict) -> Dict:
        request = {
            "request_type": "continue_reasoning",
            "reasoning_id": reasoning_id,
            "step_result": step_result
        }
        return self._send_request(request)

    def get_reasoning_state(self, reasoning_id: str) -> Dict:
        request = {
            "request_type": "get_reasoning_state",
            "reasoning_id": reasoning_id
        }
        return self._send_request(request)

    def store_reasoning_pattern(self, pattern_name: str, steps: list) -> Dict:
        request = {
            "request_type": "store_reasoning_pattern",
            "pattern_name": pattern_name,
            "steps": steps
        }
        return self._send_request(request)

    def get_reasoning_patterns(self) -> Dict:
        request = {
            "request_type": "get_reasoning_patterns"
        }
        return self._send_request(request)

    def health_check(self) -> Dict:
        request = {
            "request_type": "health_check"
        }
        return self._send_request(request)

    def use_chain_of_thought(self, prompt: str, code_context: Optional[str] = None) -> Dict:
        request = {
            "request_type": "use_chain_of_thought",
            "prompt": prompt,
            "code_context": code_context
        }
        return self._send_request(request)

    def use_tree_of_thought(self, prompt: str, code_context: Optional[str] = None) -> Dict:
        request = {
            "request_type": "use_tree_of_thought",
            "prompt": prompt,
            "code_context": code_context
        }
        return self._send_request(request)

    def close(self):
        self.socket.close()
        self.context.term()
        logger.info("ChainOfThoughtClient closed")

# Example usage
if __name__ == "__main__":
    client = ChainOfThoughtClient()
    
    # Test problem solving reasoning
    result = client.start_reasoning("problem_solving", {
        "problem": "Optimize database queries",
        "constraints": ["Must maintain ACID properties", "Response time < 100ms"]
    })
    print(f"Started reasoning: {result}")
    
    if result["status"] == "success":
        reasoning_id = result["state"]["type"] + "_" + str(result["state"]["start_time"])
        
        # Continue with first step
        step1_result = client.continue_reasoning(reasoning_id, {
            "problem_definition": "Database queries are slow due to missing indexes",
            "impact": "High - affects user experience"
        })
        print(f"Step 1 result: {step1_result}")
        
        # Get current state
        state = client.get_reasoning_state(reasoning_id)
        print(f"Current state: {state}")
    
    # Test getting patterns
    patterns = client.get_reasoning_patterns()
    print(f"Available patterns: {patterns}")
    
    client.close() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise