import logging
import yaml
import os
import time
import json
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import threading
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from common.config_manager import get_service_ip, get_service_url, get_redis_url


# Import path manager for containerization-friendly paths
import sys
import os
from common.utils.path_manager import PathManager
sys.path.insert(0, str(PathManager.get_project_root()))
# Add project root to Python path for common_utils import
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import common modules
from common.core.base_agent import BaseAgent
from src.agents.pc2.utils.config_loader import Config

# Import common utilities if available
try:
    from common_utils.zmq_helper import create_socket
    USE_COMMON_UTILS = True
except ImportError as e:
    print(f"Import error: {e}")
    USE_COMMON_UTILS = False

# Load configuration at the module level
config = Config().get_config()

# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = str(Path(PathManager.get_project_root()) / "config" / "network_config.yaml")
    try:
        with open(config_path, "r") as f:
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
                "tutoring_agent": int(os.environ.get("TUTORING_AGENT_PORT", 5650)),
                "tutoring_health": int(os.environ.get("TUTORING_HEALTH_PORT", 5651)),
                "model_orchestrator": int(os.environ.get("MODEL_ORCHESTRATOR_PORT", 5500)),
                "error_bus": int(os.environ.get("ERROR_BUS_PORT", 7150))
            }
        }
    
# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                   handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("TutoringAgent")

# Load network configuration
network_config = load_network_config()

# Get machine IPs from config
MAIN_PC_IP = get_mainpc_ip()))
PC2_IP = network_config.get("pc2_ip", get_pc2_ip()))
BIND_ADDRESS = network_config.get("bind_address", os.environ.get("BIND_ADDRESS", "0.0.0.0"))

# Get port configuration
TUTORING_AGENT_PORT = network_config.get("ports", {}).get("tutoring_agent", int(os.environ.get("TUTORING_AGENT_PORT", 5650)))
TUTORING_HEALTH_PORT = network_config.get("ports", {}).get("tutoring_health", int(os.environ.get("TUTORING_HEALTH_PORT", 5651)))
MODEL_ORCHESTRATOR_PORT = network_config.get("ports", {}).get("model_orchestrator", int(os.environ.get("MODEL_ORCHESTRATOR_PORT", 5500)))
ERROR_BUS_PORT = network_config.get("ports", {}).get("error_bus", int(os.environ.get("ERROR_BUS_PORT", 7150)))

# Set request timeout
ZMQ_REQUEST_TIMEOUT = 15000  # 15 seconds in milliseconds

class AdvancedTutoringAgent(BaseAgent):
    """
    AdvancedTutoringAgent: Provides personalized tutoring and lesson generation.
    """
    def __init__(self, user_profile: Dict[str, Any] = None, port: int = None):
        # Initialize state before BaseAgent
        self.user_profile = user_profile or {"subject": "General Knowledge", "difficulty": "medium"}
        self.lesson_history = []
        self.current_topic = self.user_profile.get('subject', 'General Knowledge')
        self.difficulty_level = self.user_profile.get('difficulty', 'medium')
        self.lesson_cache = {}  # Simple cache for lessons
        self.running = True
        self.start_time = time.time()
        self.llm_available = True
        
        # Initialize BaseAgent with proper parameters
        super().__init__(
            name="AdvancedTutoringAgent", 
            port=port if port is not None else TUTORING_AGENT_PORT,
            health_check_port=TUTORING_HEALTH_PORT
        )
        
        # Setup error reporting
        # ✅ Using BaseAgent's built-in error reporting (UnifiedErrorHandler)
        
        # Start health check thread
        self._start_health_check()
        
        logger.info(f"AdvancedTutoringAgent initialized for topic: {self.current_topic}")
    
    # ✅ Using BaseAgent.report_error() instead of custom methods
    
    def _start_health_check(self):
        """Start health check thread."""
        self.health_thread = threading.Thread(target=self._health_check_loop)
        self.health_thread.daemon = True
        self.health_thread.start()
        logger.info("Health check thread started")
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        base_status = super()._get_health_status()
        
        # Add tutoring-specific health information
        uptime = time.time() - self.start_time
        
        base_status.update({
            "status": "ok",
            "uptime": uptime,
            "current_topic": self.current_topic,
            "difficulty_level": self.difficulty_level,
            "llm_available": self.llm_available,
            "lessons_generated": len(self.lesson_history),
            "cache_size": len(self.lesson_cache)
        })
        
        return base_status

    def _generate_lesson(self, topic: str, difficulty: str, student_level: str) -> str:
        """Generate a lesson using the LLM via ModelOrchestrator"""
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
            self.model_socket.send_json(prompt)
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.model_socket, zmq.POLLIN)
            if poller.poll(15000):  # 15 second timeout
                response = self.model_socket.recv_json()
                
                if response.get("status") == "success" and "content" in response:
                    # Parse the LLM response - it might be a string containing JSON
                    try:
                        if isinstance(response["content"], str):
                            # Try to extract JSON from the string
                            import re
                            json_match = re.search(r'({.*})', response["content"], re.DOTALL)
                            if json_match:
                                lesson_json = json.loads(json_match.group(1))
                                # Cache the result
                                self.lesson_cache[cache_key] = lesson_json
                                return lesson_json
                        
                        # If we get here, content is already parsed or not JSON
                        if isinstance(response["content"], dict):
                            self.lesson_cache[cache_key] = response["content"]
                            return response["content"]
                        
                    except Exception as parse_error:
                        logger.error(f"Error parsing LLM response: {parse_error}")
                        self.report_error("PARSE_ERROR", f"Error parsing LLM response: {parse_error}")
            
            # If we get here, either the request timed out or parsing failed
            return self._generate_fallback_lesson(topic, difficulty)
            
        except Exception as e:
            logger.error(f"Error generating lesson: {e}")
            self.report_error("LESSON_GENERATION_ERROR", f"Error generating lesson: {e}")
            return self._generate_fallback_lesson(topic, difficulty)
    
    def _generate_fallback_lesson(self, topic: str, difficulty: str) -> Dict[str, Any]:
        """Generate a fallback lesson when LLM is unavailable"""
        logger.info(f"Generating fallback lesson for {topic}")
        return {
            "title": f"Introduction to {topic.title()}",
            "content": f"This is a basic overview of {topic} at {difficulty} level. The real lesson couldn't be generated, but this is a placeholder.",
            "exercises": [
                {"question": "What would you like to learn about this topic?", "answer": "Please specify your interests."},
                {"question": "What aspect of this topic is most relevant to you?", "answer": "Consider your goals and needs."},
                {"question": "How would you apply this knowledge?", "answer": "Think about practical applications."}
            ]
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests for lessons or tutoring"""
        action = request.get("action", "")
        
        if action == "generate_lesson":
            topic = request.get("topic", self.current_topic)
            difficulty = request.get("difficulty", self.difficulty_level)
            student_level = request.get("student_level", "intermediate")
            
            try:
                lesson = self._generate_lesson(topic, difficulty, student_level)
                # Add to history
                self.lesson_history.append({
                    "topic": topic,
                    "difficulty": difficulty,
                    "timestamp": datetime.now().isoformat(),
                    "lesson_id": len(self.lesson_history) + 1
                })
                return {
                    "status": "success",
                    "lesson": lesson,
                    "lesson_id": len(self.lesson_history)
                }
            except Exception as e:
                logger.error(f"Error handling generate_lesson request: {e}")
                self.report_error("REQUEST_ERROR", f"Error handling generate_lesson request: {e}")
                return {
                    "status": "error",
                    "message": f"Failed to generate lesson: {str(e)}"
                }
        
        elif action == "get_history":
            return {
                "status": "success",
                "history": self.lesson_history
            }
        
        elif action == "update_profile":
            # Update user profile
            try:
                for key, value in request.get("profile_updates", {}).items():
                    self.user_profile[key] = value
                
                # Update current topic and difficulty if provided
                if "subject" in request.get("profile_updates", {}):
                    self.current_topic = request["profile_updates"]["subject"]
                
                if "difficulty" in request.get("profile_updates", {}):
                    self.difficulty_level = request["profile_updates"]["difficulty"]
                
                return {
                    "status": "success",
                    "profile": self.user_profile
                }
            except Exception as e:
                logger.error(f"Error updating profile: {e}")
                self.report_error("PROFILE_UPDATE_ERROR", f"Error updating profile: {e}")
                return {
                    "status": "error",
                    "message": f"Failed to update profile: {str(e)}"
                }
        
        elif action == "health_check":
            return self._get_health_status()
        
        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}"
            }
    
    def run(self):
        """Main execution loop for the agent."""
        logger.info(f"Starting {self.name} main loop")
        
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
                
        logger.info(f"{self.name} main loop ended")
    
    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info(f"{self.name} cleaning up resources...")
        
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
                self.health_
                logger.info("Closed health socket")
            except Exception as e:
                logger.error(f"Error closing health socket: {e}")
        
        # Close model socket
        if hasattr(self, 'model_socket'):
            try:
                self.model_
                logger.info("Closed model socket")
            except Exception as e:
                logger.error(f"Error closing model socket: {e}")
        
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
        
        logger.info(f"{self.name} cleanup complete")


if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = AdvancedTutoringAgent()
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
