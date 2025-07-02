import logging
import yaml
import os
import time
import json
import zmq
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from port_config import ENHANCED_MODEL_ROUTER_PORT

# Add project root to Python path for common_utils import
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import common utilities if available
try:
    from common_utils.zmq_helper import create_socket
    USE_COMMON_UTILS = True
except ImportError as e:
    print(f"Import error: {e}")
    USE_COMMON_UTILS = False

from pc2_code.agents.utils.config_loader import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TutoringAgent")

class AdvancedTutoringAgent(BaseAgent):
    def __init__(self, user_profile: Dict[str, Any], port: int = 5650):
        super().__init__(name="AdvancedTutoringAgent", port=5650)
        self.user_profile = user_profile
        self.lesson_history = []
        self.current_topic = user_profile.get('subject', 'General Knowledge')
        self.difficulty_level = user_profile.get('difficulty', 'medium')
        self.lesson_cache = {}  # Simple cache for lessons
        self.name = "AdvancedTutoringAgent"
        self.port = port
        self.health_port = port + 1
        self.running = True
        self.start_time = time.time()
        
        # Initialize ZMQ context
        self.context = zmq.Context()
        
        # Initialize main socket
        try:
            logger.info(f"Initializing main socket on port {self.port}")
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://0.0.0.0:{self.port}")
            logger.info(f"Main socket bound to tcp://0.0.0.0:{self.port}")
        except Exception as e:
            logger.error(f"Failed to bind main socket: {e}")
            raise
        
        # Initialize health check socket
        try:
            logger.info(f"Initializing health check socket on port {self.health_port}")
            if USE_COMMON_UTILS:
                self.health_socket = create_socket(self.context, zmq.REP, server=True)
            else:
                self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.bind(f"tcp://0.0.0.0:{self.health_port}")
            logger.info(f"Health check socket bound to tcp://0.0.0.0:{self.health_port}")
        except Exception as e:
            logger.error(f"Failed to bind health check socket: {e}")
            raise
        
        # Initialize ZMQ connection to EnhancedModelRouter
        try:
            logger.info("Initializing ZMQ connection to EnhancedModelRouter")
            self.llm_socket = self.context.socket(zmq.REQ)
            self.llm_socket.setsockopt(zmq.LINGER, 0)  # Don't wait on close
            self.llm_socket.setsockopt(zmq.RCVTIMEO, 15000)  # 15 second timeout
            self.llm_socket.connect(f"tcp://localhost:{ENHANCED_MODEL_ROUTER_PORT}")
            logger.info(f"Successfully connected to EnhancedModelRouter at tcp://localhost:{ENHANCED_MODEL_ROUTER_PORT}")
            self.llm_available = True
        except Exception as e:
            logger.error(f"Failed to connect to EnhancedModelRouter: {e}")
            self.llm_available = False
        
        # Start health check thread
        self._start_health_check()
        
        logger.info(f"AdvancedTutoringAgent initialized for topic: {self.current_topic}")

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
            "current_topic": self.current_topic,
            "difficulty_level": self.difficulty_level,
            "llm_available": self.llm_available,
            "lessons_generated": len(self.lesson_history),
            "cache_size": len(self.lesson_cache)
        }

    def _generate_lesson_with_llm(self, topic: str, difficulty: str) -> Dict[str, Any]:
        """Generate a lesson using the LLM via EnhancedModelRouter"""
        cache_key = f"{topic}_{difficulty}"
        
        # Check cache first
        if cache_key in self.lesson_cache:
            logger.info(f"Using cached lesson for {topic} ({difficulty})")
            return self.lesson_cache[cache_key]
        
        if not self.llm_available:
            return self._generate_fallback_lesson(topic, difficulty)
        
        try:
            # Create a well-structured prompt for the LLM
            prompt = {
                "task_type": "creative",
                "model": "ollama/llama3",
                "prompt": f"""
                Create an educational lesson about {topic} at a {difficulty} level.
                
                Structure your response as a valid JSON object with the following format:
                {{
                    "title": "A clear, engaging title for the lesson",
                    "content": "A concise explanation of the topic (3-4 paragraphs)",
                    "exercises": [
                        {{"question": "First question about the topic", "answer": "Answer to first question"}},
                        {{"question": "Second question about the topic", "answer": "Answer to second question"}},
                        {{"question": "Third question about the topic", "answer": "Answer to third question"}}
                    ]
                }}
                
                Ensure your content is educational, accurate, and appropriate for the {difficulty} difficulty level.
                Return ONLY the JSON object, nothing else.
                """,
                "temperature": 0.7
            }
            
            # Send request to LLM
            logger.info(f"Requesting lesson from LLM for topic: {topic}, difficulty: {difficulty}")
            self.llm_socket.send_json(prompt)
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.llm_socket, zmq.POLLIN)
            if poller.poll(15000):  # 15 second timeout
                response = self.llm_socket.recv_json()
                
                if response.get("status") == "success" and "content" in response:
                    # Parse the LLM response - it might be a string containing JSON
                    try:
                        if isinstance(response["content"], str):
                            # Try to extract JSON from the string
                            import re
                            
from main_pc_code.src.core.base_agent import BaseAgentjson_match 
from main_pc_code.utils.config_loader import load_config

# Load configuration at the module level
config = Config().get_config()

# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "network_config.yaml")
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": "192.168.100.16",
            "pc2_ip": "192.168.100.17",
            "bind_address": "0.0.0.0",
            "secure_zmq": False
        }

# Load both configurations
network_config = load_network_config()

# Get machine IPs from config
MAIN_PC_IP = network_config.get("main_pc_ip", "192.168.100.16")
PC2_IP = network_config.get("pc2_ip", "192.168.100.17")
BIND_ADDRESS = network_config.get("bind_address", "0.0.0.0")

# ... rest of the file remains unchanged ...

if __name__ == "__main__":
    agent = AdvancedTutoringAgent()
    agent.run()
