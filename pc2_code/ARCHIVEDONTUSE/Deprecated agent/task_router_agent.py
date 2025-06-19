"""
DEPRECATED: Task Router / Model Selector Agent
---------------------------------------------
NOTE: This agent is deprecated in favor of the consolidated Enhanced Model Router (port 5601).
All new development should use the Enhanced Model Router which incorporates all functionality
from this agent plus additional features.

This agent previously:
- Receives interpreted tasks
- Decides which model to use (Phi-3, Llama 3, Deepseek Coder)
- Forwards the task to the chosen model via local or remote connector
- Provides intelligent task routing based on task type and model capabilities
"""
import zmq
import json
import time
import logging
import threading
import sys
import os
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [TaskRouter] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TaskRouter")

# ZMQ ports - updated to match config.json
TASK_ROUTER_PORT = 5558
MODEL_MANAGER_PORT = PC2_AGENTS["model_manager"]["port"]  # Using centralized config
REMOTE_CONNECTOR_PORT = 5557
TRANSLATOR_PORT = 8044  # Using a port in the 8000-8100 range to avoid conflicts
INTERPRETER_PORT = 5557  # Kept for backward compatibility

# --- ADVANCED ROUTER INTEGRATION START ---
try:
    from advanced_router import detect_task_type
    has_advanced_router = True
except ImportError:
    has_advanced_router = False
    def detect_task_type(prompt):
        # Fallback: simple keyword detection
        if any(k in prompt.lower() for k in ["code", "python", "function", "class", "script", "bug", "debug", "deepseek"]):
            return "code"
        if any(k in prompt.lower() for k in ["why", "how", "explain", "reason", "llama"]):
            return "reasoning"
        return "general"
# --- ADVANCED ROUTER INTEGRATION END ---

class TaskRouterAgent:
    def __init__(self):
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Socket to receive requests from translator (previously from interpreter)
        self.receiver = self.context.socket(zmq.SUB)
        
        # Connect to the fixed translator port
        try:
            self.receiver.connect(f"tcp://localhost:{TRANSLATOR_PORT}")
            self.receiver.setsockopt_string(zmq.SUBSCRIBE, "")
            logger.info(f"Connected to Translator Agent on port {TRANSLATOR_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Translator Agent on port {TRANSLATOR_PORT}: {e}")
            raise RuntimeError(f"Cannot connect to Translator Agent: {e}") from e
        
        # Socket to communicate with model manager
        self.model_manager = self.context.socket(zmq.REQ)
        self.model_manager.connect(f"tcp://localhost:{MODEL_MANAGER_PORT}")
        
        # Socket to communicate with remote connector
        self.remote_connector = self.context.socket(zmq.REQ)
        self.remote_connector.connect(f"tcp://localhost:{REMOTE_CONNECTOR_PORT}")
        
        # Socket to publish responses
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.bind(f"tcp://*:{TASK_ROUTER_PORT}")
        
        # Running flag
        self.running = True
        
        # Task type mapping
        self.task_types = {
            "code": ["code-generation", "code-completion"],
            "reasoning": ["reasoning"],
            "chat": ["chat"],
            "general": ["text-generation"]
        }
        
        logger.info("Task Router Agent initialized")
    
    def select_model(self, task_type, context_size=None):
        """Select the best model for a given task type"""
        try:
            # Map task type to model capabilities
            capabilities = self.task_types.get(task_type, ["text-generation"])
            
            # Ask model manager for the best model
            for capability in capabilities:
                request = {
                    "request": "select_model",
                    "task_type": capability,
                    "context_size": context_size
                }
                
                logger.info(f"Requesting model for capability: {capability}")
                self.model_manager.send_string(json.dumps(request))
                
                # Wait for response with timeout
                if self.model_manager.poll(5000) == 0:
                    logger.error(f"Timeout waiting for model selection: {capability}")
                    continue
                
                response = self.model_manager.recv_string()
                response_data = json.loads(response)
                
                if response_data.get("status") == "success":
                    model = response_data.get("selected_model")
                    logger.info(f"Selected model: {model} for task: {task_type}")
                    return model
            
            # If no model found, use default
            logger.warning(f"No suitable model found for task: {task_type}, using phi3 as fallback")
            return "phi3"
            
        except Exception as e:
            logger.error(f"Error selecting model: {str(e)}")
            return "phi3"  # Default fallback
    
    def route(self, task_type, prompt, system_prompt=None, context_size=None):
        """Route a task to the appropriate model"""
        try:
            # Select the best model for this task
            model = self.select_model(task_type, context_size)
            
            # Prepare request for remote connector
            request = {
                "request_type": "generate",
                "model": model,
                "prompt": prompt,
                "system_prompt": system_prompt,
                "temperature": 0.7
            }
            
            # Send request to remote connector
            logger.info(f"Routing task to model: {model}")
            self.remote_connector.send_string(json.dumps(request))
            
            # Wait for response with timeout
            if self.remote_connector.poll(120000) == 0:  # 2 minute timeout
                error_msg = f"Timeout waiting for response from model: {model}"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "error": error_msg
                }
            
            # Get response
            response = self.remote_connector.recv_string()
            response_data = json.loads(response)
            
            logger.info(f"Received response from model: {model}")
            return response_data
            
        except Exception as e:
            error_msg = f"Error routing task: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg
            }
    
    def handle_requests(self):
        """Main loop to handle incoming requests (now with advanced_router integration)"""
        logger.info("Started request handler loop")
        
        while self.running:
            try:
                # Use poll to avoid blocking indefinitely
                if self.receiver.poll(timeout=1000) == 0:
                    continue
                
                # Receive request
                message = self.receiver.recv_string()
                try:
                    request = json.loads(message)
                    prompt = request.get("prompt")
                    system_prompt = request.get("system_prompt")
                    context_size = request.get("context_size")
                    request_id = request.get("request_id", str(time.time()))
                    
                    if not prompt:
                        logger.error("Received request without prompt")
                        continue
                    
                    # --- ADVANCED ROUTER LOGIC ---
                    if has_advanced_router:
                        task_type = detect_task_type(prompt)
                        logger.info(f"[AdvancedRouter] Detected task type: {task_type}")
                    else:
                        task_type = request.get("task_type", "general")
                        logger.info(f"[FallbackRouter] Using provided task type: {task_type}")
                    # --- END ADVANCED ROUTER LOGIC ---
                    
                    # Route the task
                    logger.info(f"Received task: {task_type}, request_id: {request_id}")
                    response_data = self.route(task_type, prompt, system_prompt, context_size)
                    
                    # Add request ID to response
                    response_data["request_id"] = request_id
                    
                    # Publish response
                    self.publisher.send_string(json.dumps(response_data))
                    logger.info(f"Published response for request_id: {request_id}")
                    
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in request: {message[:100]}...")
                except Exception as e:
                    logger.error(f"Error processing request: {str(e)}")
                    traceback.print_exc()
            
            except zmq.Again:
                # Timeout, continue loop
                pass
            except Exception as e:
                logger.error(f"Error in request handler: {str(e)}")
                traceback.print_exc()
    
    def run(self):
        """Run the task router agent"""
        try:
            # Main request handling loop
            self.handle_requests()
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            traceback.print_exc()
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        
        self.receiver.close()
        self.model_manager.close()
        self.remote_connector.close()
        self.publisher.close()
        self.context.term()
        
        logger.info("Task Router Agent stopped")


# Main entry point
if __name__ == "__main__":
    try:
        logger.info("Starting Task Router Agent...")
        agent = TaskRouterAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Task Router Agent interrupted by user")
    except Exception as e:
        logger.error(f"Error running Task Router Agent: {str(e)}")
        traceback.print_exc()
