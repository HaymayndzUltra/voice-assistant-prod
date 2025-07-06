#!/usr/bin/env python3
"""
Advanced Router Utility
----------------------
Provides task classification and routing logic for intelligent task routing.

This module contains algorithms for detecting task types based on natural language
input, allowing agents to determine the most appropriate model or processing path.
"""

import re
import json
import logging
import zmq
import time
from datetime import datetime
# TODO: web_automation.py not found. Feature disabled.
# from web_automation import GLOBAL_TASK_MEMORY  # Unified adaptive memory
from typing import Dict, Any, List, Set, Tuple, Optional, Union
import sys
from pathlib import Path

# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from common.core.base_agent import BaseAgent
from pc2_code.agents.utils.config_loader import Config

# Load configuration at the module level
config = Config().get_config()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AdvancedRouter")

# Task type constants
TASK_TYPE_CODE = "code"
TASK_TYPE_REASONING = "reasoning"
TASK_TYPE_CHAT = "chat"
TASK_TYPE_GENERAL = "general"
TASK_TYPE_CREATIVE = "creative"
TASK_TYPE_FACTUAL = "factual"
TASK_TYPE_MATH = "math"

# Keyword mappings for task classification
TASK_KEYWORDS = {
    TASK_TYPE_CODE: [
        "code", "python", "javascript", "java", "c++", "programming",
        "function", "class", "method", "algorithm", "bug", "error", 
        "debug", "fix", "implement", "script", "module", "compile",
        "syntax", "framework", "library", "api", "database", "sql",
        "web", "html", "css", "json", "xml", "yaml", "deepseek"
    ],
    TASK_TYPE_REASONING: [
        "why", "how", "explain", "reason", "analysis", "understand", 
        "compare", "contrast", "difference", "similar", "think", 
        "consider", "evaluate", "assess", "analyze", "examine",
        "implications", "consequences", "effects", "causes", "impact",
        "llama"
    ],
    TASK_TYPE_CHAT: [
        "hello", "hi", "hey", "how are you", "what's up", "chat",
        "talk", "converse", "discuss", "conversation"
    ],
    TASK_TYPE_CREATIVE: [
        "create", "generate", "design", "story", "poem", "song",
        "creative", "imagine", "fiction", "fantasy", "invent",
        "novel", "innovative", "artistic", "write", "compose"
    ],
    TASK_TYPE_FACTUAL: [
        "what is", "who is", "when did", "where is", "fact", 
        "information", "details", "tell me about", "history", 
        "science", "define", "definition"
    ],
    TASK_TYPE_MATH: [
        "calculate", "compute", "solve", "equation", "math", 
        "mathematics", "arithmetic", "algebra", "geometry",
        "calculus", "formula", "computation", "numerical"
    ]
}

# Regular expression patterns for more precise matching
CODE_PATTERNS = [
    r"```[\w]*\n[\s\S]*?\n```",  # Code blocks
    r"def\s+\w+\s*\(.*?\):",     # Python function definitions
    r"class\s+\w+(\s*\(.*?\))?:", # Python class definitions
    r"import\s+[\w\.,\s]+",      # Import statements
    r"from\s+[\w\.]+\s+import",  # From import statements
    
"function\s+\w+\s*\(.*?\)", # JavaScript function
    r"var\s+\w+\s*=|let\s+\w+\s*=|const\s+\w+\s*=", # Variable declarations
    r"<\w+[^>]*>.*?</\w+>",      # HTML tags
    r"\[\s*[\w\s,\"\']*\s*\]",   # Array notation
    r"{\s*[\w\s,\"\':]*\s*}",    # Object/dict notation
]

def detect_task_type(prompt: str) -> str:
    """
    Detect the task type based on the prompt text.
    
    This function uses a combination of keyword matching, pattern recognition,
    and heuristics to determine the most likely task type for the given prompt.
    
    Args:
        prompt: The user's prompt text
        
    Returns:
        The detected task type (code, reasoning, chat, creative, factual, math, or general)
    """
    if not prompt or not isinstance(prompt, str):
        logger.warning("Invalid prompt provided to detect_task_type")
        return TASK_TYPE_GENERAL
    
    prompt_lower = prompt.lower()
    
    # Check for code patterns first (highest priority)
    for pattern in CODE_PATTERNS:
        if re.search(pattern, prompt):
            logger.info(f"Detected code pattern in prompt: {pattern[:20]}...")
            return TASK_TYPE_CODE
    
    # Count keyword matches for each task type
    scores = {task_type: 0 for task_type in TASK_KEYWORDS.keys()}
    
    for task_type, keywords in TASK_KEYWORDS.items():
        for keyword in keywords:
            if keyword in prompt_lower:
                # Award points based on keyword relevance
                # Exact phrases get more points
                if f" {keyword} " in f" {prompt_lower} ":
                    scores[task_type] += 2
                else:
                    scores[task_type] += 1
    
    # Check for special patterns
    
    # Math expressions
    if re.search(r'\d+\s*[\+\-\*\/\^]\s*\d+', prompt):
        scores[TASK_TYPE_MATH] += 3
    
    # Question formats
    if prompt.strip().endswith('?'):
        if any(q in prompt_lower for q in ["what is", "who is", "when", "where", "how does"]):
            scores[TASK_TYPE_FACTUAL] += 2
        elif any(q in prompt_lower for q in ["why", "how would", "explain"]):
            scores[TASK_TYPE_REASONING] += 2
    
    # Code requests often start with imperative verbs
    if re.match(r'^(write|create|implement|develop|fix|debug|optimize)\s', prompt_lower):
        scores[TASK_TYPE_CODE] += 2
    
    # Check for explicit task type mentions
    explicit_mentions = {
        "write some code": TASK_TYPE_CODE,
        "explain the reasoning": TASK_TYPE_REASONING,
        "let's chat": TASK_TYPE_CHAT,
        "creative writing": TASK_TYPE_CREATIVE,
        "factual information": TASK_TYPE_FACTUAL,
        "solve this math": TASK_TYPE_MATH
    }
    
    for phrase, task_type in explicit_mentions.items():
        if phrase in prompt_lower:
            scores[task_type] += 3
    
    # Get the task type with the highest score
    max_score = max(scores.values())
    
    # If no clear signal, default to general
    if max_score == 0:
        logger.info("No clear task type detected, defaulting to general")
        return TASK_TYPE_GENERAL
    
    # Get all task types with the max score
    top_tasks = [task for task, score in scores.items() if score == max_score]
    
    if len(top_tasks) == 1:
        logger.info(f"Detected task type: {top_tasks[0]} with score {max_score}")
        return top_tasks[0]
    else:
        # Tiebreaker - use priority order
        priority_order = [
            TASK_TYPE_CODE,
            TASK_TYPE_REASONING, 
            TASK_TYPE_MATH,
            TASK_TYPE_FACTUAL,
            TASK_TYPE_CREATIVE,
            TASK_TYPE_CHAT,
            TASK_TYPE_GENERAL
        ]
        
        for task_type in priority_order:
            if task_type in top_tasks:
                logger.info(f"Multiple potential task types detected, using priority: {task_type}")
                return task_type
    
    # Fallback
    logger.info("Falling back to general task type")
    return TASK_TYPE_GENERAL

def map_task_to_model_capabilities(task_type: str) -> List[str]:
    """
    Map a task type to model capabilities.
    
    Args:
        task_type: The detected task type
        
    Returns:
        List of model capabilities required for this task
    """
    capability_mapping = {
        TASK_TYPE_CODE: ["code-generation", "code-completion"],
        TASK_TYPE_REASONING: ["reasoning"],
        TASK_TYPE_CHAT: ["chat", "conversation"],
        TASK_TYPE_CREATIVE: ["text-generation", "creative-writing"],
        TASK_TYPE_FACTUAL: ["knowledge", "fact-checking"],
        TASK_TYPE_MATH: ["math", "calculation"],
        TASK_TYPE_GENERAL: ["text-generation"]
    }
    
    return capability_mapping.get(task_type, ["text-generation"])

class AdvancedRouterAgent(BaseAgent):
    """Advanced Router Agent for task classification and routing Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:')."""
    
    def __init__(self, port=5555):
        super().__init__(name="AdvancedRouterAgent", port=port)
        self.start_time = time.time()
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.bind(f"tcp://*:{self.port + 1}")
        self.running = True
        logger.info(f"AdvancedRouterAgent initialized on port {self.port}")
    
    

        self.error_bus_port = 7150

        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')

        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"

        self.error_bus_pub = self.context.socket(zmq.PUB)

        self.error_bus_pub.connect(self.error_bus_endpoint)
def _get_health_status(self) -> Dict[str, Any]:
        """Return health status information."""
        return {
            'status': 'success',
            'agent': 'AdvancedRouterAgent',
            'timestamp': datetime.now().isoformat(),
            'uptime': time.time() - self.start_time
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming routing requests."""
        try:
            if 'prompt' not in request:
                return {"status": "error", "message": "Missing 'prompt' field in request"}
            
            prompt = request['prompt']
            task_type = detect_task_type(prompt)
            capabilities = map_task_to_model_capabilities(task_type)
            
            return {
                "status": "success",
                "task_type": task_type,
                "capabilities": capabilities
            }
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {"status": "error", "message": str(e)}
    
    def run(self):
        """Run the agent's main loop."""
        logger.info("AdvancedRouterAgent starting...")
        
        while self.running:
            try:
                # Handle main socket requests
                if self.socket.poll(100, zmq.POLLIN):
                    request = self.socket.recv_json()
                    logger.info(f"Received request: {request}")
                    response = self.handle_request(request)
                    self.socket.send_json(response)
                
                # Handle health check requests
                if self.health_socket.poll(100, zmq.POLLIN):
                    _ = self.health_socket.recv()
                    health_data = self._get_health_status()
                    self.health_socket.send_json(health_data)
                
                time.sleep(0.01)  # Small sleep to prevent CPU hogging
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(1)  # Sleep longer on error
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up resources...")
        self.running = False
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
        if hasattr(self, 'health_socket') and self.health_socket:
            self.health_socket.close()
        if hasattr(self, 'context') and self.context:
            self.context.term()
        logger.info("Cleanup complete")

# Example usage demonstration
if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = AdvancedRouterAgent()
        agent.run()
    except KeyboardInterrupt:
        print("Agent stopped by user")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print("Cleaning up...")
            agent.cleanup()
