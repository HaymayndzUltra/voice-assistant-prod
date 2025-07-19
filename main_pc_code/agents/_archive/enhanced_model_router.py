from main_pc_code.src.core.base_agent import BaseAgent
#!/usr/bin/env python3
"""
Enhanced Model Router
- Intelligently routes model requests to the appropriate model
- Integrates with Context Summarizer for context-aware prompting
- Supports Chain of Thought for complex reasoning tasks
- Maintains per-session context windows
- Supports msgpack for efficient serialization
"""
import zmq
import json
import msgpack  # Added for efficient message serialization
import os
import threading
import time
import logging
# from web_automation import GLOBAL_TASK_MEMORY  # Unified adaptive memory (commented out for PC1)
import re
from pathlib import Path


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", ".."))))
from common.utils.path_env import get_path, join_path, get_file_path
from common.env_helpers import get_env
# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

LOG_PATH = join_path("logs", "enhanced_model_router.log")
ZMQ_MODEL_ROUTER_PORT = 5601 # Enhanced version of standard model router

# Ensure log directory exists
Path(LOG_PATH).parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

class EnhancedModelRouter(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="EnhancedModelRouter")
        # Setup ZMQ context
        self.context = zmq.Context()
        
        # Main REP socket for model requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://127.0.0.1:{zmq_port}")
        
        # Task Router REP socket for MMA requests
        self.task_router_socket = self.context.socket(zmq.REP)
        self.task_router_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.task_router_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.task_router_socket.bind("tcp://0.0.0.0:5571")
        
        # Setup poller for multiple sockets
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        self.poller.register(self.task_router_socket, zmq.POLLIN)
        
        # Connect to advanced agents
        self.context_summarizer_socket = self.context.socket(zmq.REQ)
        self.context_summarizer_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.context_summarizer_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.context_summarizer_socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5610")
        
        self.chain_of_thought_socket = self.context.socket(zmq.REQ)
        self.chain_of_thought_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.chain_of_thought_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.chain_of_thought_socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5612")
        
        # Connect to original model manager
        self.model_manager_socket = self.context.socket(zmq.REQ)
        self.model_manager_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.model_manager_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.model_manager_socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5555")
        
        self.running = True
        logging.info(f"[EnhancedModelRouter] Started on ports {zmq_port} and 5571")
    
    def get_context_summary(self, user_id="default", project=None, max_tokens=500):
        """Get a context summary from the Context Summarizer Agent"""
        try:
            request = {
                "action": "get_summary",
                "user_id": user_id,
                "project": project,
                "max_tokens": max_tokens
            }
            
            self.context_summarizer_socket.send_string(json.dumps(request))
            response = self.context_summarizer_socket.recv_string()
            result = json.loads(response)
            
            if result.get("status") == "ok":
                return result.get("summary", "")
            else:
                logging.warning(f"[EnhancedModelRouter] Failed to get context summary: {result.get('message', 'Unknown error')}")
                return ""
        except Exception as e:
            logging.error(f"[EnhancedModelRouter] Error getting context summary: {str(e)}")
            return ""
    
    def record_interaction(self, interaction_type, content, user_id="default", project=None, metadata=None):
        """Record an interaction in the Context Summarizer"""
        try:
            request = {
                "action": "add_interaction",
                "user_id": user_id,
                "project": project,
                "type": interaction_type,
                "content": content,
                "metadata": metadata
            }
            
            self.context_summarizer_socket.send_string(json.dumps(request))
            response = self.context_summarizer_socket.recv_string()
            result = json.loads(response)
            
            if result.get("status") != "ok":
                logging.warning(f"[EnhancedModelRouter] Failed to record interaction: {result.get('message', 'Unknown error')}")
            
            return result.get("status") == "ok"
        except Exception as e:
            logging.error(f"[EnhancedModelRouter] Error recording interaction: {str(e)}")
            return False
    
    def use_chain_of_thought(self, prompt, code_context=None):
        """Use Chain of Thought for complex reasoning"""
        try:
            request = {
                "action": "generate",
                "request": prompt,
                "code_context": code_context
            }
            
            self.chain_of_thought_socket.send_string(json.dumps(request))
            response = self.chain_of_thought_socket.recv_string()
            result = json.loads(response)
            
            if result.get("status") == "ok":
                return result.get("result", {}).get("solution", "")
            else:
                logging.warning(f"[EnhancedModelRouter] Chain of Thought failed: {result.get('message', 'Unknown error')}")
                return None
        except Exception as e:
            logging.error(f"[EnhancedModelRouter] Error using Chain of Thought: {str(e)}")
            return None
    
    def send_to_model_manager(self, request_data):
        """Send a request to the original Model Manager"""
        try:
            self.model_manager_socket.send_string(json.dumps(request_data))
            response = self.model_manager_socket.recv_string()
            return json.loads(response)
        except Exception as e:
            logging.error(f"[EnhancedModelRouter] Error sending to Model Manager: {str(e)}")
            return {"error": str(e)}
    
    def process_request(self, request):
        """Process a model request, adding context and using appropriate processing method"""
        req_type = request.get("type", "general")
        prompt = request.get("prompt", "")
        user_id = request.get("user_id", "default")
        project = request.get("project")
        use_cot = request.get("use_chain_of_thought", False)
        model = request.get("model")
        max_tokens = request.get("max_tokens")
        
        # Complex code generation task - use Chain of Thought
        if req_type == "code" and (use_cot or "complex" in prompt.lower() or len(prompt) > 200):
            # Get context summary for Chain of Thought
            context_summary = self.get_context_summary(user_id, project)
            
            # Add context to prompt if available
            if context_summary:
                enhanced_prompt = f"{context_summary}\n\n{prompt}"
            else:
                enhanced_prompt = prompt
            
            # Use Chain of Thought for complex reasoning
            code_context = request.get("code_context")
            result = self.use_chain_of_thought(enhanced_prompt, code_context)
            
            if result:
                # Record the interaction
                self.record_interaction("user_query", prompt, user_id, project)
                self.record_interaction("system_response", result, user_id, project)
                
                return {
                    "response": result,
                    "model_used": "chain_of_thought",
                    "enhanced": True
                }
        
        # For all other cases, add context and send to model manager
        context_summary = self.get_context_summary(user_id, project, max_tokens=300)
        
        if context_summary:
            enhanced_prompt = f"{context_summary}\n\n{prompt}"
        else:
            enhanced_prompt = prompt
        
        # Prepare request for model manager
        model_request = {
            "prompt": enhanced_prompt,
            "type": req_type
        }
        
        if model:
            model_request["model"] = model
        
        if max_tokens:
            model_request["max_tokens"] = max_tokens
        
        # Send to model manager and return result
        result = self.send_to_model_manager(model_request)
        
        # Record the interaction
        self.record_interaction("user_query", prompt, user_id, project)
        self.record_interaction("system_response", result.get("response", ""), user_id, project)
        
        # Add flag indicating enhancement
        result["enhanced"] = True
        
        return result
    
    def handle_task_request(self, request):
        """Handle task routing requests from MMA"""
        try:
            task_type = request.get("task_type", "")
            task_data = request.get("data", {})
            
            # Here we would determine the appropriate model for the task
            # For now, just return a simple response
            response = {
                "status": "success",
                "task_type": task_type,
                "model_selected": "gpt-4" if "complex" in task_type else "gpt-3.5-turbo",
                "priority": "high" if "urgent" in task_type else "normal"
            }
            
            logging.info(f"[EnhancedModelRouter] Task processed successfully: {task_type}")
            return response
        except Exception as e:
            error_msg = f"Error handling task request: {str(e)}"
            logging.error(f"[EnhancedModelRouter] {error_msg}")
            return {"status": "error", "message": error_msg}
    
    def is_msgpack_request(self, message):
        """Check if a message is likely to be msgpack encoded"""
        try:
            # Try to unpack the message as msgpack
            msgpack.unpackb(message)
            return True
        except Exception:
            # If unpacking fails, it's probably not msgpack
            return False
        
    def run(self):
        """Main execution loop"""
        try:
            while self.running:
                # Poll for events
                events = dict(self.poller.poll(1000))
                
                # Check main socket
                if self.socket in events:
                    try:
                        message = self.socket.recv()
                        start_time = time.time()
                        
                        logging.info(f"[EnhancedModelRouter] Received request on main socket")
                        
                        # Check if the message is msgpack encoded
                        if self.is_msgpack_request(message):
                            # Unpack msgpack message
                            request = msgpack.unpackb(message)
                            # Process the request
                            response = self.process_request(request)
                            # Send response back as msgpack
                            self.socket.send(msgpack.packb(response))
                        else:
                            # Assume JSON message
                            request = json.loads(message.decode('utf-8'))
                            # Process the request
                            response = self.process_request(request)
                            # Send response back as JSON
                            self.socket.send_string(json.dumps(response))
                        
                        # Log performance metrics
                        duration_ms = (time.time() - start_time) * 1000
                        logging.info(f"PERF_METRIC: [EnhancedModelRouter] - [RequestHandling] - Duration: {duration_ms:.2f}ms")
                    except Exception as e:
                        error_msg = f"Error processing request: {str(e)}"
                        logging.error(error_msg)
                        try:
                            self.socket.send_string(json.dumps({"status": "error", "message": error_msg}))
                        except:
                            pass
                
                # Check task router socket
                if self.task_router_socket in events:
                    try:
                        message = self.task_router_socket.recv()
                        
                        logging.info(f"[EnhancedModelRouter] Received request on task router socket")
                        
                        # Check if the message is msgpack encoded
                        if self.is_msgpack_request(message):
                            # Unpack msgpack message
                            request = msgpack.unpackb(message)
                            # Handle the task request
                            response = self.handle_task_request(request)
                            # Send response back as msgpack
                            self.task_router_socket.send(msgpack.packb(response))
                        else:
                            # Assume JSON message
                            request = json.loads(message.decode('utf-8'))
                            # Handle the task request
                            response = self.handle_task_request(request)
                            # Send response back as JSON
                            self.task_router_socket.send_string(json.dumps(response))
                    except Exception as e:
                        error_msg = f"Error processing task request: {str(e)}"
                        logging.error(f"[EnhancedModelRouter] {error_msg}")
                        try:
                            self.task_router_socket.send_string(json.dumps({"status": "error", "message": error_msg}))
                        except:
                            pass
        except Exception as e:
            logging.error(f"[EnhancedModelRouter] Error: {str(e)}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the router and clean up resources"""
        self.running = False
        self.socket.close()
        self.task_router_socket.close()
        self.context_summarizer_socket.close()
        self.chain_of_thought_socket.close()
        self.model_manager_socket.close()
        logging.info(f"[EnhancedModelRouter] Stopping")

def main():
    try:
        router = EnhancedModelRouter()
        router.run()
    except Exception as e:
        logging.error(f"[EnhancedModelRouter] Fatal error: {str(e)}")

if __name__ == "__main__":
    main()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise