"""
GoT/ToT Agent
------------
A ZMQ-based agent that implements Graph/Tree-of-Thought reasoning for complex problem-solving.
Provides multi-step, branching, and backtracking reasoning capabilities.
"""

import logging
import json
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import zmq
import threading
import random
from collections import deque
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import sys
import os

# Setup logging
LOG_PATH = "logs/got_tot_agent.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GoTToTAgent")

# ZMQ port for this agent
GOT_TOT_PORT = 5646

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
MAIN_PC_CODE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if MAIN_PC_CODE not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE)

from utils.config_parser import parse_agent_args

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
args = parse_agent_args()

class Node:
    """Node in the reasoning tree/graph"""
    def __init__(self, state, parent=None, step=0):
        self.state = state  # Reasoning state (e.g., partial answer, context)
        self.parent = parent
        self.children = []
        self.step = step
        self.score = 0
        
    def add_child(self, child):
        self.children.append(child)

class GoTToTAgent:
    """Graph/Tree-of-Thought Agent for advanced reasoning"""
    
    def __init__(self, zmq_port=GOT_TOT_PORT):
        """Initialize the GoT/ToT Agent"""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://*:{zmq_port}")
        
        # Health check socket
        self.name = "GoTToTAgent"
        self.running = True
        self.start_time = time.time()
        self.health_port = zmq_port + 1
        
        # Initialize health check socket
        try:
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            self.health_socket.bind(f"tcp://0.0.0.0:{self.health_port}")
            logger.info(f"Health check socket bound to port {self.health_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind health check socket: {e}")
            raise
        
        # Load reasoning model
        self._load_reasoning_model()
        
        # Initialize parameters
        self.max_steps = 5
        self.max_branches = 3
        self.temperature = 0.7
        self.top_p = 0.9
        
        # Record start time for uptime tracking
        self.start_time = time.time()
        
        # Start health check thread
        self._start_health_check()
        
        # Start processing thread
        self.running = True
        self.process_thread = threading.Thread(target=self._process_loop)
        self.process_thread.start()
        
        logger.info(f"GoT/ToT Agent initialized on port {zmq_port}")
    
    def _start_health_check(self):
        """Start health check thread."""
        self.health_thread = threading.Thread(target=self._health_check_loop)
        self.health_thread.daemon = True
        self.health_thread.start()
        logger.info("Health check thread started")
    
    def _health_check_loop(self):
        """Background loop to handle health check requests."""
        logger.info("Health check loop started")
        
        while self.running:
            try:
                # Check for health check requests with timeout
                if self.health_socket.poll(100, zmq.POLLIN):
                    # Receive request (don't care about content)
                    _ = self.health_socket.recv()
                    
                    # Get health data
                    health_data = self._get_health_status()
                    
                    # Send response
                    self.health_socket.send_json(health_data)
                    
                time.sleep(0.1)  # Small sleep to prevent CPU hogging
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(1)  # Sleep longer on error
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        uptime = time.time() - self.start_time
        
        return {
            "agent": self.name,
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "uptime": uptime,
            "model_loaded": self.model is not None if hasattr(self, "model") else False,
            "device": str(self.device) if hasattr(self, "device") else "unknown"
        }
    
    def _load_reasoning_model(self):
        """Load the reasoning model"""
        try:
            logger.info("Attempting to load reasoning model...")
            # Define the path to the local HuggingFace model directory (not .gguf file)
            model_path = "/mnt/c/Users/haymayndz/Desktop/Voice assistant/models/gguf/phi-2.Q4_0.gguf"
            fallback_model = "microsoft/phi-2"

            # Try local directory (must be a directory with config.json, etc.)
            if os.path.isdir(model_path):
                logger.info(f"Trying to load local HuggingFace model directory: {model_path}")
                self.tokenizer = AutoTokenizer.from_pretrained(model_path)
                self.model = AutoModelForCausalLM.from_pretrained(model_path)
                logger.info(f"Loaded local model from {model_path}")
            else:
                logger.warning(f"Local model directory not found or not valid at {model_path}. Trying HuggingFace Hub model: {fallback_model}")
                self.tokenizer = AutoTokenizer.from_pretrained(fallback_model)
                self.model = AutoModelForCausalLM.from_pretrained(fallback_model)
                logger.info(f"Loaded HuggingFace Hub model: {fallback_model}")

            # Move to GPU if available
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            if self.model:
                self.model.to(self.device)
                logger.info(f"Reasoning model loaded on {self.device}")

        except Exception as e:
            logger.error(f"Error loading reasoning model: {str(e)}")
            self.model = None
            self.tokenizer = None
            logger.info("Fallback mode initialized - health checks will pass but model generation will be limited")
            return
    
    def _process_loop(self):
        """Main processing loop (poller-based, safe REP pattern)"""
        poller = zmq.Poller()
        poller.register(self.socket, zmq.POLLIN)

        while self.running:
            try:
                socks = dict(poller.poll(1000))  # 1-s tick
                if self.socket in socks:
                    # Receive request
                    request_str = self.socket.recv_string()
                    request = json.loads(request_str)

                    # Handle request
                    response = self._handle_request(request)

                    # Send response
                    self.socket.send_string(json.dumps(response))
            except zmq.Again:
                # No message received within poll interval
                continue
            except Exception as e:
                logger.error(f"Error in process loop: {str(e)}")
                try:
                    self.socket.send_string(json.dumps({
                        "status": "error",
                        "message": str(e)
                    }))
                except zmq.ZMQError:
                    # Socket may be in bad state; skip sending
                    pass
    
    def _handle_request(self, request: Dict) -> Dict:
        """Handle incoming requests"""
        try:
            action = request.get("action")
            
            if action in ["health_check", "health", "ping"]:
                return {
                    "status": "ok",
                    "ready": True,
                    "initialized": True,
                    "message": "GoT/ToT Agent is healthy",
                    "timestamp": datetime.now().isoformat(),
                    "uptime": time.time() - self.start_time,
                    "model_loaded": self.model is not None,
                    "device": str(self.device) if hasattr(self, "device") else "unknown"
                }
            
            elif action == "reason":
                prompt = request.get("prompt")
                context = request.get("context", [])
                
                # Generate reasoning paths
                best_path, all_paths = self.reason(prompt, context)
                
                return {
                    "status": "ok",
                    "best_path": [node.state for node in best_path],
                    "all_paths": [[node.state for node in path] for path in all_paths],
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
    
    def reason(self, prompt: str, context: Optional[List] = None) -> Tuple[List[Node], List[List[Node]]]:
        """Build a tree/graph of reasoning steps and return the best path"""
        logger.info(f"GoT/ToT reasoning started for prompt: {prompt}")
        
        # Create root node
        root = Node(state={'prompt': prompt, 'context': context or []}, step=0)
        
        # Expand tree
        all_leaves = self._expand_tree(root)
        logger.info(f"Generated {len(all_leaves)} reasoning paths")
        
        # Score and select best path
        best_leaf = max(all_leaves, key=lambda n: self._score_path(n))
        best_path = self._trace_path(best_leaf)
        all_paths = [self._trace_path(leaf) for leaf in all_leaves]
        
        logger.info(f"GoT/ToT collapse: selected path with score {best_leaf.score}")
        return best_path, all_paths
    
    def _expand_tree(self, root: Node) -> List[Node]:
        """Expand the tree/graph up to max_steps and max_branches"""
        leaves = []
        queue = deque([root])
        
        while queue:
            node = queue.popleft()
            
            if node.step >= self.max_steps:
                leaves.append(node)
                continue
            
            # Branching: generate up to max_branches children
            for b in range(self.max_branches):
                child_state = self._generate_reasoning_step(node.state, node.step, branch=b)
                child = Node(state=child_state, parent=node, step=node.step+1)
                node.add_child(child)
                queue.append(child)
        
        return leaves
    
    def _generate_reasoning_step(self, state: Dict, step: int, branch: int) -> Dict:
        """Generate a reasoning step using the model"""
        try:
            if not self.model or not self.tokenizer:
                # Fallback to simple state update
                return self._fallback_reasoning_step(state, step, branch)
            
            # Prepare prompt
            prompt = self._create_reasoning_prompt(state, step, branch)
            
            # Generate reasoning
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512).to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=200,
                    num_return_sequences=1,
                    temperature=self.temperature,
                    top_p=self.top_p
                )
            
            reasoning = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Update state
            new_state = state.copy()
            new_state['context'] = state['context'] + [reasoning]
            new_state['last_step'] = reasoning
            
            return new_state
            
        except Exception as e:
            logger.error(f"Error generating reasoning step: {str(e)}")
            return self._fallback_reasoning_step(state, step, branch)
    
    def _fallback_reasoning_step(self, state: Dict, step: int, branch: int) -> Dict:
        """Generate a simple reasoning step without using a model"""
        # Create a mock reasoning step for fallback operation
        prompt = state.get('prompt', '')
        context = state.get('context', [])
        
        # Generate simple fallback response
        fallback_reasoning = f"Step {step}, branch {branch}: Reasoning in fallback mode. "
        fallback_reasoning += f"This is a placeholder response as the model is not available."
        
        # Update state
        new_state = state.copy()
        new_state['context'] = context + [fallback_reasoning]
        new_state['last_step'] = fallback_reasoning
        new_state['is_fallback'] = True
        
        logger.info(f"Generated fallback reasoning for step {step}, branch {branch}")
        return new_state
    
    def _create_reasoning_prompt(self, state: Dict, step: int, branch: int) -> str:
        """Create a prompt for the reasoning model"""
        prompt = "Given the following information:\n\n"
        
        # Add original prompt
        prompt += f"Original prompt: {state['prompt']}\n\n"
        
        # Add context
        if state['context']:
            prompt += "Previous reasoning steps:\n"
            for i, step_text in enumerate(state['context']):
                prompt += f"Step {i+1}: {step_text}\n"
        
        # Add current step request
        prompt += f"\nPlease provide the next reasoning step (Step {step+1}, Branch {branch+1})."
        
        return prompt
    
    def _score_path(self, leaf: Node) -> float:
        """Score a path from root to leaf"""
        path = self._trace_path(leaf)
        
        # Calculate score based on:
        # 1. Path length
        # 2. Reasoning quality
        # 3. Context coherence
        score = 0.0
        
        # Length score
        score += len(path) * 0.2
        
        # Reasoning quality score
        for node in path:
            if 'last_step' in node.state:
                step_text = node.state['last_step']
                # Score based on length and complexity
                score += len(step_text.split()) * 0.1
                # Bonus for longer, more complex reasoning
                if len(step_text.split()) > 10:
                    score += 0.5
        
        # Context coherence score
        if len(path) > 1:
            coherence = 0.0
            for i in range(1, len(path)):
                prev_step = path[i-1].state.get('last_step', '')
                curr_step = path[i].state.get('last_step', '')
                # Simple coherence check based on word overlap
                prev_words = set(prev_step.lower().split())
                curr_words = set(curr_step.lower().split())
                overlap = len(prev_words.intersection(curr_words))
                coherence += overlap * 0.1
            score += coherence
        
        leaf.score = score
        return score
    
    def _trace_path(self, leaf: Node) -> List[Node]:
        """Trace back from leaf to root to get the full path"""
        path = []
        node = leaf
        while node:
            path.append(node)
            node = node.parent
        return list(reversed(path))
    
    def shutdown(self):
        """Clean up resources"""
        try:
            self.running = False
            
            # Wait for threads to finish
            if hasattr(self, 'health_thread') and self.health_thread.is_alive():
                self.health_thread.join(timeout=2.0)
                logger.info("Health thread joined")
            
            # Close health socket if it exists
            if hasattr(self, "health_socket"):
                self.health_socket.close()
                logger.info("Health socket closed")
                
            self.socket.close()
            self.context.term()
            logger.info("GoT/ToT Agent shut down")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")

if __name__ == "__main__":
    agent = GoTToTAgent()
    try:
        # Keep the main thread alive while background thread handles requests
        agent.process_thread.join()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        agent.shutdown()