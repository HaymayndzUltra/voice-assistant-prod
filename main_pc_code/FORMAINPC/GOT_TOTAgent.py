"""
from common.config_manager import get_service_ip, get_service_url, get_redis_url

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

GoT/ToT Agent
------------
A ZMQ-based agent that implements Graph/Tree-of-Thought reasoning for complex problem-solving.
Provides multi-step, branching, and backtracking reasoning capabilities.
"""

import logging
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import zmq
import threading
import random
from collections import deque
# NOTE: direct HF loaders will be removed; keep optional torch for device detection
try:
    import torch
except ImportError:
    torch = None  # type: ignore

# Remove direct model loading; transformers now optional
# from transformers import AutoTokenizer, AutoModelForCausalLM


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root())
from common.utils.path_env import get_path, join_path, get_file_path
from main_pc_code.utils import model_client
import sys
import os

# Setup logging
LOG_PATH = join_path("logs", "got_tot_agent.log")
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
PROJECT_ROOT = get_project_root()
MAIN_PC_CODE = get_main_pc_code()
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)  # Insert project root to path
if MAIN_PC_CODE not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE)  # Insert main_pc_code to path

# Import BaseAgent for standardized agent implementation
from common.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
config = load_config()

class Node:
    """Node in the reasoning tree/graph"""
    def __init__(self, state, parent=None, step=0):
        self.state = state  # Reasoning state (e.g., partial answer, context)
        self.parent = parent
        self.children = []
        self.step = step
        self.score: float = 0.0
        
    

        # --- Removed invalid error_bus wiring lines that belonged to Agent ---
        # self.error_bus_port = 7150
        # self.error_bus_host = get_service_ip("pc2")
        # self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        # self.error_bus_pub = self.context.socket(zmq.PUB)
        # self.error_bus_pub.connect(self.error_bus_endpoint)
    def add_child(self, child):
        """Add a child node to the current node"""
        self.children.append(child)

class GoTToTAgent(BaseAgent):
    """Graph/Tree-of-Thought Agent for advanced reasoning Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:')."""
    def __init__(self, port: int = 5646, name: str = "GoTToTAgent", **kwargs):
        # Standardized config loading
        agent_port = port if port is not None else config.get("port", 5646)
        agent_name = name if name is not None else config.get("name", 'GoTToTAgent')
        super().__init__(name=agent_name, port=int(agent_port))

        self.context = zmq.Context()
        self.running = True
        self.start_time = time.time()

        # Initialize main socket
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://*:{agent_port}")

        # Load reasoning model
        self._load_reasoning_model()

        # Initialize parameters
        self.max_steps = 5
        self.max_branches = 3
        self.temperature = 0.7
        self.top_p = 0.9

        # Start processing thread
        self.process_thread = threading.Thread(target=self._process_loop)
        self.process_thread.start()

        logger.info(f"GoT/ToT Agent initialized on port {agent_port}")
    
    def _get_health_status(self):
        # Default health status: Agent is running if its main loop is active.
        # This can be expanded with more specific checks later.
        status = "HEALTHY" if self.running else "UNHEALTHY"
        details = {
            "status_message": "Agent is operational.",
            "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else 0
        }
        return {"status": status, "details": details}
    
    def _load_reasoning_model(self):
        """Stub: No local model loading. Uses centralized MMA via model_client."""
        self.model = None  # legacy placeholders retained for backwards compatibility
        self.tokenizer = None
        self.device = None
        logger.info("Reasoning model loading skipped – routed via model_client.generate() instead.")
    
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
            
            if action == "reason":
                prompt = request.get("prompt", "")  # Default to empty string if prompt is missing
                if prompt is None:
                    prompt = ""
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
        if prompt is None:
            prompt = ""  # Default to empty string if prompt is None
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
        """Generate a reasoning step using centralized LLM router."""
        try:
            prompt = self._create_reasoning_prompt(state, step, branch)

            # Call ModelManagerAgent via model_client
            response = model_client.generate(prompt, quality="fast", max_tokens=200, temperature=self.temperature, top_p=self.top_p)

            if isinstance(response, dict):
                reasoning = response.get("response_text", "")
            else:
                reasoning = str(response)

            if not reasoning:
                logger.warning("Empty reasoning response – falling back")
                return self._fallback_reasoning_step(state, step, branch)

            new_state = state.copy()
            new_state['context'] = state['context'] + [reasoning]
            new_state['last_step'] = reasoning

            return new_state

        except Exception as e:
            logger.error(f"Error via model_client.generate: {e}")
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
    
    def cleanup(self):
        """Clean up resources"""
        try:
            self.running = False
            
            # Close main socket
            if hasattr(self, "socket"):
                self.socket.close()
                logger.info("Main socket closed")
            
            # Call parent cleanup to handle health check socket and other resources
            super().cleanup()
            
            logger.info("GoT/ToT Agent shut down")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = GoTToTAgent()
        agent.run()  # If a run() method is added in the future, this will be used
        if hasattr(agent, 'process_thread') and agent.process_thread:
            agent.process_thread.join()
        else:
            print("Error: Processing thread not found. Exiting.")
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()