import logging
import time
import json
import zmq
from typing import Dict, Any, Optional
import os
from port_config import ENHANCED_MODEL_ROUTER_PORT
import threading
from datetime import datetime

# Add project root to Python path for common_utils import
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import common utilities if available
try:
    from common_utils.zmq_helper import create_socket
from main_pc_code.utils.network_utils import get_zmq_connection_string, get_machine_ip
    except ImportError as e:
        print(f"Import error: {e}")
    USE_COMMON_UTILS = True
except ImportError:
    USE_COMMON_UTILS = False



# Get the absolute path of the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(current_dir, "tutoring_agent.log"), mode="a"),
        logging.StreamHandler()
    ]
)

class AdvancedTutoringAgent:
    def __init__(self, user_profile:

        self.name = "AdvancedTutoringAgent"
        self.running = True
        self.start_time = time.time()
        self.health_port = self.port + 1
 Dict[str, Any]):
        self.user_profile = user_profile
        self.lesson_history = []
        self.current_topic = user_profile.get('subject', 'General Knowledge')
        self.difficulty_level = user_profile.get('difficulty', 'medium')
        self.lesson_cache = {}  # Simple cache for lessons
        
        
        # Start health check thread
        self._start_health_check()

        # Initialize ZMQ connection to EnhancedModelRouter
        try:
            logging.info("[LLM] Initializing ZMQ connection to EnhancedModelRouter")
            self.context = zmq.Context()
            self.llm_socket = self.context.socket(zmq.REQ)
            self.llm_socket.setsockopt(zmq.LINGER, 0)  # Don't wait on close
            self.llm_socket.setsockopt(zmq.RCVTIMEO, 15000)  # 15 second timeout
            self.llm_socket.connect(get_zmq_connection_string({ENHANCED_MODEL_ROUTER_PORT}, "localhost")))
            logging.info(f"[LLM] Successfully connected to EnhancedModelRouter at tcp://localhost:{ENHANCED_MODEL_ROUTER_PORT}")
            self.llm_available = True  # FORCE TRUE FOR TESTING
        except Exception as e:
            logging.error(f"[LLM] Failed to connect to EnhancedModelRouter: {e}")
            self.llm_available = False
        
        logging.info(f"[LLM] AdvancedTutoringAgent initialized for topic: {self.current_topic}")

    def _start_health_check(self):
        """Start health check thread."""
        self.health_thread = threading.Thread(target=self._health_check_loop)
        self.health_thread.daemon = True
        self.health_thread.start()
        logging.info("Health check thread started")
    
    def _health_check_loop(self):
        """Background loop to handle health check requests."""
        logging.info("Health check loop started")
        
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
                logging.error(f"Error in health check loop: {e}")
                time.sleep(1)  # Sleep longer on error
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        uptime = time.time() - self.start_time
        
        return {
            "agent": self.name,
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "uptime": uptime
        }

    def _generate_lesson_with_llm(self, topic: str, difficulty: str) -> Dict[str, Any]:
        """Generate a lesson using the LLM via EnhancedModelRouter"""
        cache_key = f"{topic}_{difficulty}"
        
        # Check cache first
        if cache_key in self.lesson_cache:
            logging.info(f"Using cached lesson for {topic} ({difficulty})")
            return self.lesson_cache[cache_key]
        
        if not self.llm_available:
            logging.warning(f"[LLM] LLM not available, using fallback lesson for {topic}")
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
            logging.info(f"[LLM][DEBUG] Sending prompt to LLM: {json.dumps(prompt)}")
            self.llm_socket.send_json(prompt)
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.llm_socket, zmq.POLLIN)
            if poller.poll(15000):  # 15 second timeout
                response = self.llm_socket.recv_json()
                logging.info(f"[LLM][DEBUG] Raw LLM response: {response}")
                if response.get("status") == "success" and "content" in response:
                    # Parse the LLM response - it might be a string containing JSON
                    try:
                        if isinstance(response["content"], str):
                            # Try to extract JSON from the string
                            content_json = json.loads(response["content"])
                        else:
                            content_json = response["content"]
                        # Cache the successful result
                        self.lesson_cache[cache_key] = content_json
                        logging.info(f"[LLM] LLM lesson generated and cached for {topic}")
                        return content_json
                    except Exception as e:
                        logging.error(f"[LLM][DEBUG] Failed to parse LLM content as JSON: {e}")
                        return self._generate_fallback_lesson(topic, difficulty)
                else:
                    logging.warning(f"[LLM][DEBUG] LLM request failed: {response.get('message', 'Unknown error')}")
                    return self._generate_fallback_lesson(topic, difficulty)
            else:
                logging.error("[LLM][DEBUG] Timeout waiting for LLM response")
                return self._generate_fallback_lesson(topic, difficulty)
                
        except zmq.error.ZMQError as e:
            logging.error(f"[LLM][DEBUG] ZMQ error in LLM request: {e}")
            return self._generate_fallback_lesson(topic, difficulty)
        except Exception as e:
            logging.error(f"[LLM][DEBUG] Unexpected error in LLM request: {e}")
            return self._generate_fallback_lesson(topic, difficulty)
    
    def _generate_fallback_lesson(self, topic: str, difficulty: str) -> Dict[str, Any]:
        """Generate a fallback lesson when LLM is unavailable"""
        logging.warning(f"[LLM][DEBUG] Generating fallback lesson for {topic}")
        return {
            "title": f"Introduction to {topic}",
            "content": f"This is a placeholder lesson about {topic} at {difficulty} difficulty level. The LLM-based content generation was unavailable, so we're providing this basic information instead. {topic} is an important subject with many interesting aspects to explore.",
            "exercises": [
                {"question": f"What is one key concept in {topic}?", "answer": f"A key concept in {topic} is understanding its fundamental principles."},
                {"question": f"How might {topic} be applied in real life?", "answer": f"There are many practical applications of {topic} in everyday situations."}
            ]
        }

    def get_lesson(self) -> Dict[str, Any]:
        """Generate a dynamic lesson for the current topic using LLM"""
        logging.info(f"[LLM] Generating lesson for topic: {self.current_topic}")
        
        if not self.current_topic or self.current_topic == "None":
            logging.error(f"[LLM] No topic specified for lesson generation")
            return {
                "status": "error",
                "message": "No topic specified for lesson generation"
            }
        
        try:
            # Generate lesson using LLM
            lesson = self._generate_lesson_with_llm(self.current_topic, self.difficulty_level)
            logging.info(f"[LLM] Lesson generation path complete. Lesson keys: {list(lesson.keys())}")
            # Add to lesson history
            self.lesson_history.append(lesson)
            
            return {
                "status": "success",
                "lesson": lesson
            }
        except Exception as e:
            logging.error(f"[LLM] Error generating lesson: {e}")
            return {
                "status": "error",
                "message": f"Failed to generate lesson: {str(e)}"
            }

    def submit_feedback(self, engagement_score: float) -> Dict[str, Any]:
        """Process feedback on lesson engagement"""
        logging.info(f"Feedback received: {engagement_score}")
        
        # Adjust difficulty based on engagement
        if engagement_score < 0.3:
            self.difficulty_level = "easy"
        elif engagement_score > 0.7:
            self.difficulty_level = "hard"
        else:
            self.difficulty_level = "medium"
            
        logging.info(f"Adjusted difficulty to {self.difficulty_level} based on feedback")
        
        return {
            "status": "success",
            "message": "Feedback processed.",
            "new_difficulty": self.difficulty_level
        }

    def get_history(self) -> Dict[str, Any]:
        """Retrieve session history"""
        logging.info("Retrieving session history.")
        return {
            "status": "success",
            "history": self.lesson_history
        }
        
    def __del__(self):
        """Clean up ZMQ resources"""
        try:
            if hasattr(self, 'llm_socket'):
                self.llm_socket.close()
            if hasattr(self, 'context'):
                self.context.term()
        except Exception as e:
            logging.error(f"Error cleaning up ZMQ resources: {e}")
