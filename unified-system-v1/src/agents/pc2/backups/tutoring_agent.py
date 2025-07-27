import logging
import time
import json
import zmq
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from port_config import ENHANCED_MODEL_ROUTER_PORT
from common.config_manager import get_service_ip, get_service_url, get_redis_url

# Add project root to Python path for common_utils import
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import common utilities if available
try:
    from common_utils.zmq_helper import create_socket
    except ImportError as e:
        print(f"Import error: {e}")
    USE_COMMON_UTILS = True
except ImportError:
    USE_COMMON_UTILS = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TutoringAgent")

class AdvancedTutoringAgent(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()def __init__(self, user_profile: Dict[str, Any], port: int = 5650):
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

# Standard imports for PC2 agents
from pc2_code.utils.config_loader import load_config, parse_agent_args
from src.agents.pc2.error_bus_template import setup_error_reporting, report_error
from common.env_helpers import get_env


# Load configuration at the module level
config = load_config()= re.search(r'({.*})', response["content"], re.DOTALL)
                            if json_match:
                                lesson_data = json.loads(json_match.group(1))
                            else:
                                lesson_data = json.loads(response["content"])
                        else:
                            lesson_data = response["content"]
                        
                        # Validate the lesson structure
                        if "title" in lesson_data and "content" in lesson_data and "exercises" in lesson_data:
                            # Cache the successful result
                            self.lesson_cache[cache_key] = lesson_data
                            return lesson_data
                        else:
                            logger.warning("LLM response missing required fields")
                            return self._generate_fallback_lesson(topic, difficulty)
                    except Exception as e:
                        logger.error(f"Failed to parse LLM response: {e}")
                        return self._generate_fallback_lesson(topic, difficulty)
                else:
                    logger.warning(f"LLM request failed: {response.get('message', 'Unknown error')}")
                    return self._generate_fallback_lesson(topic, difficulty)
            else:
                logger.error("Timeout waiting for LLM response")
                return self._generate_fallback_lesson(topic, difficulty)
                
        except zmq.error.ZMQError as e:
            logger.error(f"ZMQ error in LLM request: {e}")
            return self._generate_fallback_lesson(topic, difficulty)
        except Exception as e:
            logger.error(f"Unexpected error in LLM request: {e}")
            return self._generate_fallback_lesson(topic, difficulty)
    
    def _generate_fallback_lesson(self, topic: str, difficulty: str) -> Dict[str, Any]:
        """Generate a fallback lesson when LLM is unavailable"""
        logger.info(f"Generating fallback lesson for {topic}")
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
        logger.info(f"Generating lesson for topic: {self.current_topic}")
        
        if not self.current_topic or self.current_topic == "None":
            return {
                "status": "error",
                "message": "No topic specified for lesson generation"
            }
        
        try:
            # Generate lesson using LLM
            lesson = self._generate_lesson_with_llm(self.current_topic, self.difficulty_level)
            
            # Add to lesson history
            self.lesson_history.append(lesson)
            
            return {
                "status": "success",
                "lesson": lesson
            }
        except Exception as e:
            logger.error(f"Error generating lesson: {e}")
            return {
                "status": "error",
                "message": f"Failed to generate lesson: {str(e)}"
            }

    def submit_feedback(self, engagement_score: float) -> Dict[str, Any]:
        """Process feedback on lesson engagement"""
        logger.info(f"Feedback received: {engagement_score}")
        
        # Adjust difficulty based on engagement
        if engagement_score < 0.3:
            self.difficulty_level = "easy"
        elif engagement_score > 0.7:
            self.difficulty_level = "hard"
        else:
            self.difficulty_level = "medium"
            
        logger.info(f"Adjusted difficulty to {self.difficulty_level} based on feedback")
        
        return {
            "status": "success",
            "message": "Feedback processed.",
            "new_difficulty": self.difficulty_level
        }

    def get_history(self) -> Dict[str, Any]:
        """Retrieve session history"""
        logger.info("Retrieving session history.")
        return {
            "status": "success",
            "history": self.lesson_history
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action', '')
        
        if action == 'health_check' or action == 'ping':
            return self._get_health_status()
        
        if action == 'get_lesson':
            return self.get_lesson()
        
        if action == 'submit_feedback':
            engagement_score = request.get('engagement_score')
            if engagement_score is None:
                return {
                    'status': 'error',
                    'message': 'Missing engagement_score parameter'
                }
            return self.submit_feedback(float(engagement_score))
        
        if action == 'get_history':
            return self.get_history()
        
        if action == 'set_topic':
            topic = request.get('topic')
            if not topic:
                return {
                    'status': 'error',
                    'message': 'Missing topic parameter'
                }
            self.current_topic = topic
            return {
                'status': 'success',
                'message': f'Topic set to {topic}'
            }
        
        return {
            'status': 'error',
            'message': f'Unknown action: {action}'
        }
    
    def run(self):
        """Main run loop."""
        logger.info("AdvancedTutoringAgent starting main loop")
        
        try:
            while self.running:
                try:
                    # Use poller to avoid blocking indefinitely
                    poller = zmq.Poller()
                    poller.register(self.socket, zmq.POLLIN)
                    
                    # Poll with timeout to allow for clean shutdown
                    if dict(poller.poll(1000)):
                        # Receive and process message
                        message_data = self.socket.recv()
                        
                        try:
                            request = json.loads(message_data)
                            logger.debug(f"Received request: {request}")
                            
                            response = self.handle_request(request)
                            
                            self.socket.send_json(response)
                            logger.debug(f"Sent response: {response}")
                        except json.JSONDecodeError:
                            logger.error(f"Received invalid JSON: {message_data}")
                            self.socket.send_json({
                                'status': 'error',
                                'message': 'Invalid JSON request'
                            })
                        except Exception as e:
                            logger.error(f"Error processing request: {str(e)}")
                            self.socket.send_json({
                                'status': 'error',
                                'message': f'Error processing request: {str(e)}'
                            })
                except zmq.error.ZMQError as e:
                    logger.error(f"ZMQ error in main loop: {str(e)}")
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Error in main loop: {str(e)}")
                    time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.stop()


    def cleanup(self):

        """Clean up resources before shutdown."""

        logger.info("Cleaning up resources...")

        # Add specific cleanup code here

        super().cleanup()
        
    def stop(self):
        """Clean up ZMQ resources"""
        logger.info("Stopping AdvancedTutoringAgent")
        
        # Set running flag to false to stop all threads
        self.running = False
        
        # Wait for threads to finish
        if hasattr(self, 'health_thread') and self.health_thread.is_alive():
            self.health_thread.join(timeout=2.0)
        
        try:
            # Close all sockets
            for socket_attr in ['socket', 'health_socket', 'llm_socket']:
                if hasattr(self, socket_attr) and getattr(self, socket_attr):
                    getattr(self, socket_attr).close()
                    logger.info(f"Closed {socket_attr}")
            
            # Terminate context
            if hasattr(self, 'context'):
                self.context.term()
                logger.info("ZMQ context terminated")
        except Exception as e:
            logger.error(f"Error cleaning up ZMQ resources: {e}")
        
        logger.info("AdvancedTutoringAgent stopped")



if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = AdvancedTutoringAgent()
        agent.run()
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