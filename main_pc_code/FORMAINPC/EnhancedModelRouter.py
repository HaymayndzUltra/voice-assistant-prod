#!/usr/bin/env python3
"""
Enhanced Model Router (Consolidated)
-----------------------------------
Central intelligence hub for model routing, combining:
- Task classification (from Task Router Agent)
- Context-aware prompting (via Contextual Memory)
- Chain of Thought for complex reasoning
- Direct model management interaction

This consolidated router replaces separate Task Router and Enhanced Model Router
components to streamline the agent communication hierarchy.
"""
import zmq
import json
import os
import threading
import time
import logging
import re
import sys
import traceback
from pathlib import Path
from datetime import datetime
# Attempt to import the lightweight web_automation stub (present in main_pc_code/web_automation).
# If it is not yet importable, prepend the parent directory (main_pc_code) to sys.path and retry.
try:
    from web_automation import GLOBAL_TASK_MEMORY  # type: ignore
except ModuleNotFoundError:
    parent_main_pc = Path(__file__).resolve().parent.parent  # main_pc_code
    if str(parent_main_pc) not in sys.path:
        sys.path.insert(0, str(parent_main_pc))
    from web_automation import GLOBAL_TASK_MEMORY  # type: ignore
from typing import Dict, Tuple, Optional, List
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import functools
from utils.config_parser import parse_agent_args

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Setup logging
LOG_PATH = Path(os.path.dirname(__file__)).parent / "logs" / "enhanced_model_router.log"
LOG_PATH.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("EnhancedModelRouter")

# Default ZMQ request/response timeout in milliseconds
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds

# ZMQ port for this agent
ZMQ_MODEL_ROUTER_PORT = 5598  # Primary port for all model routing
ZMQ_MODEL_ROUTER_PUB_PORT = 5603  # Publisher port for broadcasting

# Ports for required services
TASK_ROUTER_PORT = 8570  # Updated to match TaskRouter port
TASK_ROUTER_HEALTH_PORT = 5571  # Health check port
MODEL_MANAGER_PORT = 5555
MODEL_MANAGER_HOST = "192.168.100.17"  # PC2 IP
CONTEXTUAL_MEMORY_PORT = 5596
CHAIN_OF_THOUGHT_PORT = 5612
REMOTE_CONNECTOR_PORT = 5557
UNIFIED_UTILS_PORT = 5564
WEB_ASSISTANT_PORT = 5604

# Health monitoring settings
HEALTH_CHECK_INTERVAL = 30  # seconds
HEALTH_CHECK_TIMEOUT = 5  # seconds
MAX_RETRIES = 3

CACHE_TTL = 600  # seconds
_router_cache = {}
_router_cache_lock = threading.Lock()

# Argument parsing
args = parse_agent_args()

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
MAIN_PC_CODE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if MAIN_PC_CODE not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE)

def router_cache_key(*args, **kwargs):
    return str(args) + str(kwargs)

def cache_router_result(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = router_cache_key(*args, **kwargs)
        now = time.time()
        with _router_cache_lock:
            if key in _router_cache:
                ts, value = _router_cache[key]
                if now - ts < CACHE_TTL:
                    return value
                else:
                    del _router_cache[key]
        result = func(*args, **kwargs)
        with _router_cache_lock:
            _router_cache[key] = (now, result)
        return result
    return wrapper

# --- ADVANCED ROUTER INTEGRATION START ---
# Import the advanced_router module - prefer local import first then try regular import
try:
    # Try importing from local directory first
    sys.path.insert(0, str(Path(__file__).parent))
    from advanced_router import detect_task_type, map_task_to_model_capabilities
    has_advanced_router = True
    logger.info("Advanced router module loaded successfully from local path")
    # Restore original path
    sys.path.pop(0)
except ImportError:
    try:
        # Try regular import
        from advanced_router import detect_task_type, map_task_to_model_capabilities
        has_advanced_router = True
        logger.info("Advanced router module loaded successfully")
    except ImportError:
        has_advanced_router = False
        logger.warning("Advanced router module not available, using fallback")
        
        # Fallback implementation of detect_task_type
        def detect_task_type(prompt):
            """Fallback task type detection when advanced_router is not available"""
            if not prompt:
                return "general"
                
            prompt_lower = prompt.lower()
            if any(k in prompt_lower for k in ["code", "python", "function", "class", "script", "bug", "debug", "deepseek", "javascript", "java", "programming"]):
                return "code"
            if any(k in prompt_lower for k in ["why", "how", "explain", "reason", "analyze", "compare", "contrast", "llama"]):
                return "reasoning"
            if any(k in prompt_lower for k in ["create", "generate", "story", "poem", "song", "creative"]):
                return "creative"
            if any(k in prompt_lower for k in ["what is", "who is", "when", "where", "fact", "information"]):
                return "factual"
            if any(k in prompt_lower for k in ["calculate", "compute", "solve", "equation", "math"]):
                return "math"
            if any(k in prompt_lower for k in ["hello", "hi", "hey", "how are you", "chat"]):
                return "chat"
            return "general"
        
        # Fallback implementation of map_task_to_model_capabilities
        def map_task_to_model_capabilities(task_type):
            """Fallback capability mapping when advanced_router is not available"""
            capability_mapping = {
                "code": ["code-generation", "code-completion"],
                "reasoning": ["reasoning"],
                "chat": ["chat", "conversation"],
                "creative": ["text-generation", "creative-writing"],
                "factual": ["knowledge", "fact-checking"],
                "math": ["math", "calculation"],
                "general": ["text-generation"]
            }
            return capability_mapping.get(task_type, ["text-generation"])
# --- ADVANCED ROUTER INTEGRATION END ---

class EnhancedModelRouter:
    """
    Enhanced Model Router - Consolidated central intelligence hub for model routing
    
    This router combines the functionality of the Task Router Agent and Enhanced Model Router:
    1. Receives requests from all agents (including Translator)
    2. Classifies tasks using advanced_router
    3. Integrates with Contextual Memory for context-aware prompting
    4. Uses Chain of Thought for complex reasoning tasks
    5. Selects appropriate models via Model Manager
    6. Broadcasts responses to subscribers
    """
    
    def __init__(self, zmq_port=None, pub_port=None):
        # Allow port override via --port
        if zmq_port is None:
            if hasattr(args, 'port') and args.port is not None:
                zmq_port = int(args.port)
            else:
                zmq_port = ZMQ_MODEL_ROUTER_PORT
        if pub_port is None:
            pub_port = ZMQ_MODEL_ROUTER_PUB_PORT
        self.zmq_port = zmq_port
        self.pub_port = pub_port

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://*:{self.zmq_port}")

        # Health check socket (main_port+1)
        self.health_check_port = self.zmq_port + 1
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.health_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.health_socket.bind(f"tcp://*:{self.health_check_port}")

        # Start health check thread immediately
        self.running = True
        self.health_thread = threading.Thread(target=self._health_check_loop)
        self.health_thread.daemon = True
        self.health_thread.start()

        # Start async initialization
        self.is_initialized = threading.Event()
        self.initialization_error = None
        init_thread = threading.Thread(target=self._perform_initialization)
        init_thread.daemon = True
        init_thread.start()

        logger.info(f"Enhanced Model Router initialized on port {zmq_port} (health check: {self.health_check_port})")

    def _perform_initialization(self):
        try:
            # Publisher socket for broadcasting
            self.pub_socket = self.context.socket(zmq.PUB)
            self.pub_socket.bind(f"tcp://*:{self.pub_port}")

            # Connect to TaskRouter
            self.task_router_socket = self.context.socket(zmq.REQ)
            self.task_router_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.task_router_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.task_router_socket.connect(f"tcp://localhost:{TASK_ROUTER_PORT}")
            logger.info(f"Connected to TaskRouter on port {TASK_ROUTER_PORT}")

            # Connect to other required services
            self.model_manager_socket = self.context.socket(zmq.REQ)
            self.model_manager_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.model_manager_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.model_manager_socket.connect(f"tcp://{MODEL_MANAGER_HOST}:{MODEL_MANAGER_PORT}")
            logger.info(f"Connected to ModelManagerAgent on {MODEL_MANAGER_HOST}:{MODEL_MANAGER_PORT}")

            self.contextual_memory_socket = self.context.socket(zmq.REQ)
            self.contextual_memory_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.contextual_memory_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.contextual_memory_socket.connect(f"tcp://localhost:{CONTEXTUAL_MEMORY_PORT}")

            self.chain_of_thought_socket = self.context.socket(zmq.REQ)
            self.chain_of_thought_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.chain_of_thought_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.chain_of_thought_socket.connect(f"tcp://localhost:{CHAIN_OF_THOUGHT_PORT}")

            self.remote_connector_socket = self.context.socket(zmq.REQ)
            self.remote_connector_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.remote_connector_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.remote_connector_socket.connect(f"tcp://{MODEL_MANAGER_HOST}:{REMOTE_CONNECTOR_PORT}")  # Connect to PC2

            # Connect to UnifiedUtilsAgent on Main PC
            self.utils_agent_socket = self.context.socket(zmq.REQ)
            self.utils_agent_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.utils_agent_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.utils_agent_socket.connect(f"tcp://localhost:{UNIFIED_UTILS_PORT}")
            logger.info(f"Connected to UnifiedUtilsAgent on localhost:{UNIFIED_UTILS_PORT}")

            # Connect to Web Assistant for research capabilities
            self.web_assistant_socket = self.context.socket(zmq.REQ)
            self.web_assistant_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.web_assistant_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.web_assistant_socket.connect(f"tcp://localhost:{WEB_ASSISTANT_PORT}")
            logger.info(f"Connected to Web Assistant on port {WEB_ASSISTANT_PORT}")

            # Initialize state variables
            self.lock = threading.Lock()
            self.request_count = 0
            self.error_count = 0
            self.start_time = time.time()
            self.last_request_time = None
            self.health_check_count = 0
            self.route_count = 0
            self.successful_routes = 0
            self.failed_routes = 0
            self.task_type_counts = {}
            self.model_usage_counts = {}

            # Initialize confidence thresholds
            self.confidence_threshold = 0.8
            self.min_confidence_for_response = 0.6

            # Load model
            self._load_model()

            # Health monitoring
            self.health_status = {
                "status": "ok",
                "service": "enhanced_model_router",
                "last_check": time.time(),
                "connections": {
                    "task_router": True,
                    "model_manager": True,
                    "contextual_memory": True,
                    "chain_of_thought": True,
                    "remote_connector": True,
                    "utils_agent": True,
                    "web_assistant": True
                }
            }

            self.is_initialized.set()
            logger.info("EnhancedModelRouter async initialization complete.")
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"Initialization error: {e}")
            self.is_initialized.set()

    def _health_check_loop(self):
        logger.info("EnhancedModelRouter health check loop started")
        while self.running:
            try:
                if self.health_socket.poll(timeout=1000) != 0:
                    message = self.health_socket.recv()
                    try:
                        request = json.loads(message.decode())
                        logger.debug(f"Received health check request: {request}")
                        response = self._get_health_status()
                        self.health_socket.send_json(response)
                        logger.debug(f"Sent health check response: {response}")
                    except Exception as e:
                        logger.error(f"Invalid health check request: {e}")
                        self.health_socket.send_json({
                            "status": "error",
                            "error": str(e)
                        })
            except zmq.error.ZMQError as e:
                logger.error(f"ZMQ error in health check loop: {e}")
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(1)

    def _get_health_status(self):
        status = {
            "status": "ok" if self.is_initialized.is_set() and not self.initialization_error else "error",
            "ready": self.is_initialized.is_set() and not self.initialization_error,
            "initialized": self.is_initialized.is_set(),
            "message": "EnhancedModelRouter is healthy" if self.is_initialized.is_set() and not self.initialization_error else f"Initialization error: {self.initialization_error}",
            "timestamp": datetime.now().isoformat(),
            "uptime": time.time() - getattr(self, 'start_time', time.time()),
            "active_threads": threading.active_count()
        }
        return status

    def stop(self):
        self.running = False
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'health_socket'):
            self.health_socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        if hasattr(self, 'process_thread'):
            self.process_thread.join(timeout=5)
        if hasattr(self, 'health_thread'):
            self.health_thread.join(timeout=5)
        logger.info("EnhancedModelRouter stopped.")

    def _load_model(self):
        """Load the model"""
        try:
            # Load model and tokenizer
            model_name = "microsoft/phi-2"  # or your preferred model
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(model_name)
            
            # Move to GPU if available
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            
            logger.info(f"Model loaded on {self.device}")
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            self.model = None
            self.tokenizer = None
    
    def get_context_summary(self, user_id="default", project=None, max_tokens=500):
        """Get a context summary from the Contextual Memory Agent"""
        try:
            request = {
                "action": "get_summary",
                "user_id": user_id,
                "project": project,
                "max_tokens": max_tokens
            }
            
            self.contextual_memory_socket.send_string(json.dumps(request))
            response = self.contextual_memory_socket.recv_string()
            result = json.loads(response)
            
            if result.get("status") == "ok":
                return result.get("summary", "")
            else:
                logger.warning(f"Failed to get context summary: {result.get('message', 'Unknown error')}")
                return ""
        except Exception as e:
            logger.error(f"Error getting context summary: {str(e)}")
            return ""
    
    def record_interaction(self, interaction_type, content, user_id="default", project=None, metadata=None):
        """Record an interaction in the Contextual Memory Agent"""
        try:
            request = {
                "action": "add_interaction",
                "user_id": user_id,
                "project": project,
                "type": interaction_type,
                "content": content,
                "metadata": metadata or {}
            }
            
            self.contextual_memory_socket.send_string(json.dumps(request))
            response = self.contextual_memory_socket.recv_string()
            result = json.loads(response)
            
            if result.get("status") != "ok":
                logger.warning(f"Failed to record interaction: {result.get('message', 'Unknown error')}")
            
            return result.get("status") == "ok"
        except Exception as e:
            logger.error(f"Error recording interaction: {str(e)}")
            return False
    
    def use_chain_of_thought(self, prompt, code_context=None):
        """Use Chain of Thought (CoT) for complex reasoning"""
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
                logger.info("[MODEL ROUTER] Chain of Thought (CoT) solution generated.")
                return result.get("result", {}).get("solution", "")
            else:
                logger.warning(f"Chain of Thought failed: {result.get('message', 'Unknown error')}")
                return None
        except Exception as e:
            logger.error(f"Error using Chain of Thought: {str(e)}")
            return None

    def use_tree_of_thought(self, prompt, code_context=None):
        """Use Tree of Thought (ToT) for advanced reasoning"""
        try:
            # Assume ToT agent is on a dedicated port (e.g., 5613)
            if not hasattr(self, 'tree_of_thought_socket'):
                self.tree_of_thought_socket = self.context.socket(zmq.REQ)
                self.tree_of_thought_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
                self.tree_of_thought_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
                self.tree_of_thought_socket.connect(f"tcp://{MODEL_MANAGER_HOST}:5613")
                logger.info(f"Connected to Tree of Thought Agent on {MODEL_MANAGER_HOST}:5613")
            request = {
                "action": "generate",
                "request": prompt,
                "code_context": code_context
            }
            self.tree_of_thought_socket.send_string(json.dumps(request))
            response = self.tree_of_thought_socket.recv_string()
            result = json.loads(response)
            if result.get("status") == "ok":
                logger.info("[MODEL ROUTER] Tree of Thought (ToT) solution generated.")
                return result.get("result", {}).get("solution", "")
            else:
                logger.warning(f"Tree of Thought failed: {result.get('message', 'Unknown error')}")
                return None
        except Exception as e:
            logger.error(f"Error using Tree of Thought: {str(e)}")
            return None

    
    def select_model(self, task_type, prompt=None, context_size=None):
        """Select the most appropriate model for the given task type"""
        try:
            # First, try to get a suggestion from UnifiedUtilsAgent
            utils_request = {
                "action": "select_model",
                "task_type": task_type,
                "prompt": prompt,
                "context_size": context_size
            }
            
            try:
                self.utils_agent_socket.send_json(utils_request)
                if self.utils_agent_socket.poll(2000):  # 2-second timeout
                    utils_response = self.utils_agent_socket.recv_json()
                    suggested_model = utils_response.get("model")
                    if suggested_model:
                        logger.info(f"Received suggestion from UnifiedUtilsAgent: {suggested_model}")
                        return suggested_model
                else:
                    logger.warning("Timeout waiting for UnifiedUtilsAgent. Proceeding with local logic.")
            except Exception as e:
                logger.error(f"Could not connect to UnifiedUtilsAgent: {e}. Proceeding with local logic.")
            
            # If UnifiedUtilsAgent is unavailable or times out, proceed with local logic
            # ... rest of the existing select_model logic ...
            
        except Exception as e:
            logger.error(f"Error in model selection: {e}")
            return {"status": "error", "message": str(e)}
    
    def send_to_model_manager(self, request_data):
        """Send a model selection request to the Model Manager"""
        try:
            self.model_manager_socket.send_string(json.dumps(request_data))
            response = self.model_manager_socket.recv_string()
            return json.loads(response)
        except Exception as e:
            logger.error(f"Error sending to Model Manager: {str(e)}")
            return {"error": str(e)}
            
    def send_to_remote_connector(self, request_data):
        """Send a model inference request to the Remote Connector Agent"""
        try:
            # Format the request for Remote Connector
            rc_request = {
                "request_type": "generate",
                "model": request_data.get("model"),
                "prompt": request_data.get("prompt"),
                "system_prompt": request_data.get("system_prompt"),
                "temperature": request_data.get("temperature", 0.7)
            }
            
            # Add optional parameters if present
            if "max_tokens" in request_data:
                rc_request["max_tokens"] = request_data["max_tokens"]
                
            logger.info(f"Sending inference request to Remote Connector for model {rc_request['model']}")
            self.remote_connector_socket.send_string(json.dumps(rc_request))
            
            # Wait for response with timeout
            if self.remote_connector_socket.poll(30000) == 0:  # 30 second timeout
                logger.error("Timeout waiting for Remote Connector response")
                return {"status": "error", "error": "Timeout waiting for model response"}
            
            response = self.remote_connector_socket.recv_string()
            result = json.loads(response)
            
            # Format the response to match the expected format
            if result.get("status") == "success":
                return {
                    "status": "ok",
                    "response": result.get("response"),
                    "model_used": result.get("model")
                }
            else:
                return {
                    "status": "error",
                    "error": result.get("error", "Unknown error from Remote Connector")
                }
                
        except Exception as e:
            logger.error(f"Error sending to Remote Connector: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def _check_confidence(self, response_data: Dict) -> Tuple[bool, Optional[str]]:
        """Check if the response meets confidence requirements"""
        confidence = response_data.get('confidence', 0.0)
        
        if confidence < self.min_confidence_for_response:
            return False, "Response confidence too low to proceed"
            
        if confidence < self.confidence_threshold:
            # Generate clarification request
            clarification = self._generate_clarification(response_data)
            return False, clarification
            
        return True, None

    def _generate_clarification(self, response_data: Dict) -> str:
        """Generate a clarification request based on response data"""
        task_type = response_data.get('task_type', 'unknown')
        prompt = response_data.get('prompt', '')
        
        if task_type == 'code':
            return "I'm not entirely confident about the code solution. Could you provide more context about your requirements?"
        elif task_type == 'reasoning':
            return "I need more information to provide a complete analysis. Could you elaborate on your question?"
        elif task_type == 'factual':
            return "I'm not completely sure about this information. Would you like me to verify it through web research?"
        else:
            return "I'm not entirely confident about my understanding. Could you please clarify your request?"

    def _perform_web_research(self, query: str) -> Optional[Dict]:
        """Perform web research using the Web Assistant"""
        try:
            request = {
                "action": "research",
                "query": query,
                "max_results": 3
            }
            
            self.web_assistant_socket.send_string(json.dumps(request))
            response = self.web_assistant_socket.recv_string()
            result = json.loads(response)
            
            if result.get("status") == "ok":
                return result.get("results", {})
            else:
                logger.warning(f"Web research failed: {result.get('message', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error performing web research: {str(e)}")
            return None

    def _process_loop(self):
        """Main processing loop"""
        while self.running:
            try:
                # Wait for request
                request_str = self.socket.recv_string()
                request = json.loads(request_str)
                
                # Process request
                response = self._handle_request(request)
                
                # Send response
                self.socket.send_string(json.dumps(response))
                
            except Exception as e:
                logger.error(f"Error in process loop: {str(e)}")
                self.socket.send_string(json.dumps({
                    "status": "error",
                    "message": str(e)
                }))
    
    def _handle_request(self, request: Dict) -> Dict:
        """Handle incoming requests"""
        try:
            action = request.get("action")
            
            if action == "route":
                task = request.get("task")
                context = request.get("context", [])
                use_web_research = request.get("use_web_research", False)
                
                # Get web research if requested
                web_context = ""
                if use_web_research:
                    web_context = self._perform_web_research(task)
                
                # Process request with meta-AI loop
                response = self.process_request(task, context, web_context)
                
                return {
                    "status": "ok",
                    "response": response,
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "status": "error",
                "message": f"Unknown action: {action}"
            }
            
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def process_request(self, task: str, context: List[str], web_context: str = "") -> Dict:
        """Process a request with meta-AI loop"""
        retries = 0
        best_response = None
        best_confidence = 0.0
        
        while retries < self.max_retries:
            # Prepare prompt
            prompt = self._create_prompt(task, context, web_context)
            
            # Generate response
            response = self._generate_response(prompt)
            
            # Check confidence
            confidence = self._check_confidence(response, task)
            
            if confidence > best_confidence:
                best_response = response
                best_confidence = confidence
            
            # Meta-AI loop: Check if we need clarification
            if confidence < self.target_confidence:
                clarification = self._generate_clarification(task, response)
                context.append(clarification)
                retries += 1
                continue
            
            break
        
        return {
            "response": best_response,
            "confidence": best_confidence,
            "retries": retries
        }
    
    def _create_prompt(self, task: str, context: List[str], web_context: str = "") -> str:
        """Create a prompt for the model"""
        prompt = "Given the following task and context:\n\n"
        
        # Add task
        prompt += f"Task: {task}\n\n"
        
        # Add web context if available
        if web_context:
            prompt += f"Web Research:\n{web_context}\n\n"
        
        # Add context
        if context:
            prompt += "Context:\n"
            for item in context:
                prompt += f"- {item}\n"
        
        # Add instruction
        prompt += "\nPlease provide a detailed response."
        
        return prompt
    
    def _generate_response(self, prompt: str) -> str:
        """Generate a response using the model"""
        try:
            if not self.model or not self.tokenizer:
                return "Model not available"
            
            # Generate response
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512).to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=200,
                    num_return_sequences=1,
                    temperature=0.7,
                    top_p=0.9
                )
            
            return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return "Error generating response"
    
    def _check_confidence(self, response: str, task: str) -> float:
        """Check confidence in the response"""
        try:
            if not self.model or not self.tokenizer:
                return 0.5
            
            # Prepare confidence check prompt
            prompt = f"Task: {task}\nResponse: {response}\n\nHow confident are you that this response fully addresses the task? (0-1)"
            
            # Generate confidence score
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512).to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=50,
                    num_return_sequences=1,
                    temperature=0.3,
                    top_p=0.9
                )
            
            confidence_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract confidence score
            try:
                confidence = float(confidence_text.split()[-1])
                return min(max(confidence, 0.0), 1.0)
            except:
                return 0.5
            
        except Exception as e:
            logger.error(f"Error checking confidence: {str(e)}")
            return 0.5
    
    def _generate_clarification(self, task: str, response: str) -> str:
        """Generate a clarification request"""
        try:
            if not self.model or not self.tokenizer:
                return "Could you please clarify your request?"
            
            # Prepare clarification prompt
            prompt = f"Task: {task}\nCurrent Response: {response}\n\nWhat specific aspect needs clarification to better address the task?"
            
            # Generate clarification
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512).to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=100,
                    num_return_sequences=1,
                    temperature=0.7,
                    top_p=0.9
                )
            
            return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
        except Exception as e:
            logger.error(f"Error generating clarification: {str(e)}")
            return "Could you please clarify your request?"
    
    def _perform_web_research(self, query: str) -> str:
        """Perform web research using the web assistant"""
        try:
            # Send request to web assistant
            request = {
                "action": "search",
                "query": query
            }
            self.web_assistant_socket.send_string(json.dumps(request))
            
            # Get response
            response_str = self.web_assistant_socket.recv_string()
            response = json.loads(response_str)
            
            if response.get("status") == "ok":
                return response.get("results", "")
            return ""
            
        except Exception as e:
            logger.error(f"Error performing web research: {str(e)}")
            return ""
    
    def get_status(self):
        """Get the current status of the Enhanced Model Router"""
        with self.lock:
            uptime = time.time() - self.start_time
            return {
                "status": "ok",
                "service": "enhanced_model_router",
                "timestamp": time.time(),
                "uptime_seconds": uptime,
                "request_count": self.request_count,
                "error_count": self.error_count,
                "last_request_time": self.last_request_time,
                "health_check_count": self.health_check_count,
                "route_count": self.route_count,
                "successful_routes": self.successful_routes,
                "failed_routes": self.failed_routes,
                "task_type_counts": self.task_type_counts,
                "model_usage_counts": self.model_usage_counts,
                "connections": {
                    "model_manager": f"tcp://{MODEL_MANAGER_HOST}:{MODEL_MANAGER_PORT}",
                    "contextual_memory": f"tcp://127.0.0.1:{CONTEXTUAL_MEMORY_PORT}",
                    "chain_of_thought": f"tcp://127.0.0.1:{CHAIN_OF_THOUGHT_PORT}",
                    "remote_connector": f"tcp://127.0.0.1:{REMOTE_CONNECTOR_PORT}"
                },
                "publisher": {
                    "enabled": self.pub_socket is not None,
                    "port": self.pub_socket.last_endpoint
                }
            }
    
    def run(self):
        """Start the router's main processing loop"""
        logger.info("Starting Enhanced Model Router ...")

        while self.running:
            try:
                # Attempt to receive a request. This call is non-blocking thanks to the
                # RCVTIMEO we set on the socket during __init__. If no message is ready
                # within ZMQ_REQUEST_TIMEOUT the call will raise zmq.error.Again.
                request = self.socket.recv_json()
            except zmq.error.Again:
                # No request arrived in the allotted time. Continue waiting without
                # trying to send a reply – attempting to send without a pending request
                # would put the REP socket into an inconsistent state.
                continue
            except Exception as e:
                # Any other error while receiving – log and continue the loop.
                logger.error(f"Error receiving ZMQ message: {e}")
                continue

            # We have received a valid request; handle it and send a response.
            try:
                response = self.handle_request(request)
                self.socket.send_json(response)
            except zmq.error.Again:
                # Timeout while sending response. Log and continue.
                logger.warning("Timeout while sending response to client")
                continue
            except Exception as e:
                logger.error(f"Error handling request: {e}")
                # Best-effort: attempt to inform client of error. Guard with try/except
                try:
                    self.socket.send_json({"status": "error", "message": str(e)})
                except Exception:
                    pass

    def handle_request(self, request):
        """Handle incoming requests."""
        try:
            # Handle health check requests first
            if request.get("type") == "health_check":
                logger.debug("Received health check request")
                return {
                    "status": "ok",
                    "service": "task_router",
                    "timestamp": time.time()
                }

            # Handle other request types
            if not isinstance(request, dict):
                return {"status": "error", "message": "Invalid request format"}

            # Process the request based on type
            request_type = request.get("type", "")
            
            if request_type == "route_task":
                return self._handle_request(request)
            else:
                return {"status": "error", "message": f"Unknown request type: {request_type}"}

        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _monitor_health(self):
        """Monitor health of all connections"""
        while self.running:
            try:
                # Check TaskRouter connection
                self.task_router_socket.send_json({"action": "health_check"})
                try:
                    response = self.task_router_socket.recv_json(timeout=HEALTH_CHECK_TIMEOUT)
                    self.health_status["connections"]["task_router"] = response.get("status") == "ok"
                except zmq.error.Again:
                    self.health_status["connections"]["task_router"] = False
                
                # Check ModelManager connection
                self.model_manager_socket.send_json({"action": "health_check"})
                try:
                    response = self.model_manager_socket.recv_json(timeout=HEALTH_CHECK_TIMEOUT)
                    self.health_status["connections"]["model_manager"] = response.get("status") == "ok"
                except zmq.error.Again:
                    self.health_status["connections"]["model_manager"] = False
                
                # Update last check time
                self.health_status["last_check"] = time.time()
                
                # Log health status
                if not all(self.health_status["connections"].values()):
                    logger.warning("Health check failed for some connections")
                    logger.debug(f"Health status: {self.health_status}")
                
                time.sleep(HEALTH_CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                time.sleep(HEALTH_CHECK_INTERVAL)

def main():
    """Main entry point for the Enhanced Model Router"""
    router = EnhancedModelRouter(zmq_port=args.port)
    try:
        router.run()
    except KeyboardInterrupt:
        router.stop()

if __name__ == "__main__":
    main()