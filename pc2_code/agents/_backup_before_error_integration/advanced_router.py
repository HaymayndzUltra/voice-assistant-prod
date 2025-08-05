#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
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
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import time
import os
import sys
import threading
from datetime import datetime
# TODO: web_automation.py not found. Feature disabled.
# from web_automation import GLOBAL_TASK_MEMORY  # Unified adaptive memory
from typing import Dict, Any, List, Set, Tuple, Optional, Union
from pathlib import Path


# Import path manager for containerization-friendly paths
import sys
import os
from common.utils.path_manager import PathManager

# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    

from common.core.base_agent import BaseAgent
from pc2_code.agents.utils.config_loader import Config

# Standard imports for PC2 agents
from pc2_code.utils.config_loader import load_config, parse_agent_args
# ✅ MODERNIZED: Using BaseAgent's UnifiedErrorHandler instead of custom error bus
# Removed: from pc2_code.agents.error_bus_template import setup_error_reporting, report_error
# Now using: self.report_error() method from BaseAgent

# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = Path(PathManager.get_project_root()) / "config" / "network_config.yaml"
    try:
        with open(config_path, "r") as f:
            import yaml
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": get_mainpc_ip()),
            "pc2_ip": get_pc2_ip()),
            "bind_address": os.environ.get("BIND_ADDRESS", "0.0.0.0"),
            "secure_zmq": False,
            "ports": {
                "advanced_router": int(os.environ.get("ADVANCED_ROUTER_PORT", 5555)),
                "advanced_router_health": int(os.environ.get("ADVANCED_ROUTER_HEALTH_PORT", 5556)),
                "error_bus": int(os.environ.get("ERROR_BUS_PORT", 7150))
            }
        }

# Setup logging
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("AdvancedRouter")

# Load configuration at the module level
config = Config().get_config()

# Load network configuration
network_config = load_network_config()

# Get machine IPs from config
MAIN_PC_IP = get_mainpc_ip()))
PC2_IP = network_config.get("pc2_ip", get_pc2_ip()))
BIND_ADDRESS = network_config.get("bind_address", os.environ.get("BIND_ADDRESS", "0.0.0.0"))

# Get port configuration
ADVANCED_ROUTER_PORT = network_config.get("ports", {}).get("advanced_router", int(os.environ.get("ADVANCED_ROUTER_PORT", 5555)))
ADVANCED_ROUTER_HEALTH_PORT = network_config.get("ports", {}).get("advanced_router_health", int(os.environ.get("ADVANCED_ROUTER_HEALTH_PORT", 5556)))
ERROR_BUS_PORT = network_config.get("ports", {}).get("error_bus", int(os.environ.get("ERROR_BUS_PORT", 7150)))

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
    r"function\s+\w+\s*\(.*?\)", # JavaScript function
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
    """Advanced Router Agent for task classification and routing."""
    
    # Parse agent arguments
    _agent_args = parse_agent_args()
    
    def __init__(self, port=None):
        # Initialize state before BaseAgent
        self.start_time = time.time()
        self.running = True
        self.request_count = 0
        self.task_type_counts = {
            TASK_TYPE_CODE: 0,
            TASK_TYPE_REASONING: 0,
            TASK_TYPE_CHAT: 0,
            TASK_TYPE_CREATIVE: 0,
            TASK_TYPE_FACTUAL: 0,
            TASK_TYPE_MATH: 0,
            TASK_TYPE_GENERAL: 0
        }
        
        # Initialize BaseAgent with proper parameters
        super().__init__(
            name="AdvancedRouterAgent", 
            port=port if port is not None else ADVANCED_ROUTER_PORT,
            health_check_port=ADVANCED_ROUTER_HEALTH_PORT
        )
        
        # Setup error reporting
        self.setup_error_reporting()
        
        # Start health check thread
        self._start_health_check_thread()
        
        logger.info(f"AdvancedRouterAgent initialized on port {self.port}")
    
    def setup_error_reporting(self):
        """Set up error reporting to the central Error Bus."""
        try:
            self.error_bus_host = PC2_IP
            self.error_bus_port = ERROR_BUS_PORT
            self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
            self.error_bus_pub = self.context.socket(zmq.PUB)
            self.error_bus_pub.connect(self.error_bus_endpoint)
            logger.info(f"Connected to Error Bus at {self.error_bus_endpoint}")
        except Exception as e:
            logger.error(f"Failed to set up error reporting: {e}")
    
    def report_error(self, error_type, message, severity="ERROR"):
        """Report an error to the central Error Bus."""
        try:
            if hasattr(self, 'error_bus_pub'):
                error_report = {
                    "timestamp": datetime.now().isoformat(),
                    "agent": self.name,
                    "type": error_type,
                    "message": message,
                    "severity": severity
                }
                self.error_bus_pub.send_multipart([
                    b"ERROR",
                    json.dumps(error_report).encode('utf-8')
                ])
                logger.info(f"Reported error: {error_type} - {message}")
        except Exception as e:
            logger.error(f"Failed to report error: {e}")
    
    def _start_health_check_thread(self):
        """Start health check thread."""
        self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_thread.start()
        logger.info("Health check thread started")
    
    def _health_check(self) -> Dict[str, Any]:
        """Legacy health check method for backward compatibility."""
        return self._get_health_status()
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        base_status = super()._get_health_status()
        
        # Add AdvancedRouterAgent specific health info
        base_status.update({
            'status': 'ok',
            'uptime': time.time() - self.start_time,
            'request_count': self.request_count,
            'task_type_counts': self.task_type_counts
        })
        
        return base_status
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming routing requests."""
        try:
            self.request_count += 1
            
            if not isinstance(request, dict):
                logger.error(f"Invalid request format: {type(request)}")
                self.report_error("REQUEST_FORMAT_ERROR", f"Invalid request format: {type(request)}")
                return {
                    "status": "error",
                    "error": "Invalid request format",
                    "timestamp": datetime.now().isoformat()
                }
            
            action = request.get('action', '')
            
            if action == 'health_check':
                return self._get_health_status()
            
            elif action == 'detect_task_type':
                prompt = request.get('prompt', '')
                if not prompt:
                    logger.warning("Empty prompt received")
                    self.report_error("EMPTY_PROMPT", "Empty prompt received", "WARNING")
                    return {
                        "status": "error",
                        "error": "Empty prompt",
                        "timestamp": datetime.now().isoformat()
                    }
                
                task_type = detect_task_type(prompt)
                self.task_type_counts[task_type] += 1
                
                capabilities = map_task_to_model_capabilities(task_type)
                
                return {
                    "status": "success",
                    "task_type": task_type,
                    "capabilities": capabilities,
                    "confidence": 0.8,  # TODO: Implement confidence scoring
                    "timestamp": datetime.now().isoformat(),
                    "request_id": self.request_count
                }
            
            elif action == 'get_model_capabilities':
                task_type = request.get('task_type', TASK_TYPE_GENERAL)
                capabilities = map_task_to_model_capabilities(task_type)
                
                return {
                    "status": "success",
                    "capabilities": capabilities,
                    "timestamp": datetime.now().isoformat()
                }
            
            elif action == 'get_task_type_stats':
                return {
                    "status": "success",
                    "task_type_counts": self.task_type_counts,
                    "total_requests": self.request_count,
                    "timestamp": datetime.now().isoformat()
                }
            
            else:
                logger.warning(f"Unknown action requested: {action}")
                self.report_error("UNKNOWN_ACTION", f"Unknown action requested: {action}", "WARNING")
                return {
                    "status": "error",
                    "error": f"Unknown action: {action}",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            self.report_error("REQUEST_HANDLING_ERROR", str(e))
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def run(self):
        """Main execution loop for the agent."""
        logger.info(f"AdvancedRouterAgent starting on port {self.port}")
        
        try:
            import threading
            
            while self.running:
                try:
                    # Wait for a request with timeout
                    if self.socket.poll(timeout=1000) != 0:  # 1 second timeout
                        # Receive and parse request
                        message = self.socket.recv_json()
                        
                        # Process request
                        response = self.handle_request(message)
                        
                        # Send response
                        self.socket.send_json(response)
                    
                except zmq.error.ZMQError as e:
                    logger.error(f"ZMQ error in main loop: {e}")
                    self.report_error("ZMQ_ERROR", str(e))
                    try:
                        self.socket.send_json({
                            'status': 'error',
                            'message': f'ZMQ communication error: {str(e)}'
                        })
                    except:
                        pass
                    time.sleep(1)  # Avoid tight loop on error
                    
                except Exception as e:
                    logger.error(f"Unexpected error in main loop: {e}")
                    self.report_error("RUNTIME_ERROR", str(e))
                    try:
                        self.socket.send_json({
                            'status': 'error',
                            'message': f'Internal server error: {str(e)}'
                        })
                    except:
                        pass
                    time.sleep(1)  # Avoid tight loop on error
                    
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received, stopping AdvancedRouterAgent")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            self.report_error("FATAL_ERROR", str(e))
        finally:
            self.running = False
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info("Cleaning up resources...")
        
        # Close all sockets
        if hasattr(self, 'socket'):
            try:
                self.socket.close()
                logger.info("Closed main socket")
            except Exception as e:
                logger.error(f"Error closing main socket: {e}")
        
        # Close health socket
        if hasattr(self, 'health_socket'):
            try:
                self.health_socket.close()
                logger.info("Closed health socket")
            except Exception as e:
                logger.error(f"Error closing health socket: {e}")
        
        # Close error bus socket
        if hasattr(self, 'error_bus_pub'):
            try:
                self.error_bus_pub.close()
                logger.info("Closed error bus socket")
            except Exception as e:
                logger.error(f"Error closing error bus socket: {e}")
        
        # Call parent cleanup
        try:
            super().cleanup()
            logger.info("Called parent cleanup")
        except Exception as e:
            logger.error(f"Error in parent cleanup: {e}")
        
        logger.info("Cleanup complete")


if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = AdvancedRouterAgent()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'} on PC2...")
    except Exception as e:
        import traceback

# Standardized environment variables (Blueprint.md Step 4)
from common.utils.env_standardizer import get_mainpc_ip, get_pc2_ip, get_current_machine, get_env
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'} on PC2: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name} on PC2...")
            agent.cleanup()
