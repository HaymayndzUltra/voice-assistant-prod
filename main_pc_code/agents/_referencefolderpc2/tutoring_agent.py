import logging
import time
import json
import zmq
from typing import Dict, Any, Optional
from port_config import ENHANCED_MODEL_ROUTER_PORT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class AdvancedTutoringAgent:
    def __init__(self, user_profile: Dict[str, Any]):
        self.user_profile = user_profile
        self.lesson_history = []
        self.current_topic = user_profile.get('subject', 'General Knowledge')
        self.difficulty_level = user_profile.get('difficulty', 'medium')
        self.lesson_cache = {}  # Simple cache for lessons
        
        # Initialize ZMQ connection to EnhancedModelRouter
        try:
            logging.info("Initializing ZMQ connection to EnhancedModelRouter")
            self.context = zmq.Context()
            self.llm_socket = self.context.socket(zmq.REQ)
            self.llm_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.llm_socket.setsockopt(zmq.LINGER, 0)  # Don't wait on close
            self.llm_socket.setsockopt(zmq.RCVTIMEO, 15000)  # 15 second timeout
            self.llm_socket.connect(f"tcp://localhost:{ENHANCED_MODEL_ROUTER_PORT}")
            logging.info(f"Successfully connected to EnhancedModelRouter at tcp://localhost:{ENHANCED_MODEL_ROUTER_PORT}")
            self.llm_available = True
        except Exception as e:
            logging.error(f"Failed to connect to EnhancedModelRouter: {e}")
            self.llm_available = False
        
        logging.info(f"AdvancedTutoringAgent initialized for topic: {self.current_topic}")

    def _generate_lesson_with_llm(self, topic: str, difficulty: str) -> Dict[str, Any]:
        """Generate a lesson using the LLM via EnhancedModelRouter"""
        cache_key = f"{topic}_{difficulty}"
        
        # Check cache first
        if cache_key in self.lesson_cache:
            logging.info(f"Using cached lesson for {topic} ({difficulty})")
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
            logging.info(f"Requesting lesson from LLM for topic: {topic}, difficulty: {difficulty}")
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
                            json_match = re.search(r'({.*})', response["content"], re.DOTALL)
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
                            logging.warning("LLM response missing required fields")
                            return self._generate_fallback_lesson(topic, difficulty)
                    except Exception as e:
                        logging.error(f"Failed to parse LLM response: {e}")
                        return self._generate_fallback_lesson(topic, difficulty)
                else:
                    logging.warning(f"LLM request failed: {response.get('message', 'Unknown error')}")
                    return self._generate_fallback_lesson(topic, difficulty)
            else:
                logging.error("Timeout waiting for LLM response")
                return self._generate_fallback_lesson(topic, difficulty)
                
        except zmq.error.ZMQError as e:
            logging.error(f"ZMQ error in LLM request: {e}")
            return self._generate_fallback_lesson(topic, difficulty)
        except Exception as e:
            logging.error(f"Unexpected error in LLM request: {e}")
            return self._generate_fallback_lesson(topic, difficulty)
    
    def _generate_fallback_lesson(self, topic: str, difficulty: str) -> Dict[str, Any]:
        """Generate a fallback lesson when LLM is unavailable"""
        logging.info(f"Generating fallback lesson for {topic}")
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
        logging.info(f"Generating lesson for topic: {self.current_topic}")
        
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
            logging.error(f"Error generating lesson: {e}")
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