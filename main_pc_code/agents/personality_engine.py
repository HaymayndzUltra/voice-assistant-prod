from src.core.base_agent import BaseAgent
"""
Personality Engine Agent
Manages and processes personality traits and responses
"""

import zmq
import json
import logging
import threading
import time
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import psutil
from datetime import datetime

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('personality_engine.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('PersonalityEngine')

class PersonalityEngine(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="PersonalityEngine")
        """Initialize the Personality Engine.
        
        Args:
            port: Port for receiving requests
            emotion_engine_port: Port for subscribing to EmotionEngine broadcasts
            coordinator_port: Port for connecting to CoordinatorAgent for LLM access
        """
        self.port = port
        self.emotion_engine_port = emotion_engine_port
        self.coordinator_port = coordinator_port
        
        # Initialize ZMQ context and sockets
        self.context = zmq.Context()
        
        # REP socket for receiving requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://*:{port}")
        
        # SUB socket for subscribing to EmotionEngine broadcasts
        self.emotion_sub_socket = self.context.socket(zmq.SUB)
        self.emotion_sub_socket.connect(f"tcp://localhost:{emotion_engine_port}")
        self.emotion_sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all messages
        
        # REQ socket for connecting to CoordinatorAgent for LLM access
        self.coordinator_socket = self.context.socket(zmq.REQ)
        self.coordinator_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.coordinator_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.coordinator_socket.connect(f"tcp://localhost:{coordinator_port}")
        
        # Initialize poller for non-blocking socket operations
        self.poller = zmq.Poller()
        self.poller.register(self.emotion_sub_socket, zmq.POLLIN)
        self.poller.register(self.coordinator_socket, zmq.POLLIN)
        
        # Set timeout for requests (in milliseconds)
        self.request_timeout = 10000  # 10 seconds
        
        # Initialize current emotional state
        self.current_emotional_state = {
            'tone': 'neutral',
            'sentiment': 0.0,
            'intensity': 0.5,
            'dominant_emotion': 'neutral',
            'combined_emotion': 'neutral',
            'timestamp': time.time()
        }
        
        # Define personality traits
        self.personality_traits = {
            'helpfulness': 0.9,  # Very helpful
            'formality': 0.6,    # Somewhat formal
            'enthusiasm': 0.7,   # Moderately enthusiastic
            'humor': 0.5,        # Moderate humor
            'empathy': 0.8       # High empathy
        }
        
        # Define response style adjustments based on emotions
        self.style_adjustments = {
            'angry': {
                'formality': +0.2,  # More formal when user is angry
                'enthusiasm': -0.3,  # Less enthusiastic
                'humor': -0.4,      # Less humor
                'empathy': +0.3     # More empathetic
            },
            'sad': {
                'formality': -0.1,  # Less formal
                'enthusiasm': -0.2,  # Less enthusiastic
                'humor': -0.3,      # Less humor
                'empathy': +0.4     # More empathetic
            },
            'happy': {
                'formality': -0.2,  # Less formal
                'enthusiasm': +0.2,  # More enthusiastic
                'humor': +0.2,      # More humor
                'empathy': +0.1     # Slightly more empathetic
            },
            'frustrated': {
                'formality': +0.1,  # More formal
                'enthusiasm': -0.2,  # Less enthusiastic
                'humor': -0.3,      # Less humor
                'empathy': +0.3     # More empathetic
            },
            'neutral': {
                # No adjustments for neutral
            }
        }
        
        # Response templates for different emotions
        self.response_templates = {
            'angry': [
                "I understand this is frustrating. {response}",
                "I see you're upset. Let me help: {response}",
                "I apologize for the inconvenience. {response}"
            ],
            'sad': [
                "I'm sorry to hear that. {response}",
                "That must be difficult. {response}",
                "I understand how you feel. {response}"
            ],
            'happy': [
                "Great! {response}",
                "Wonderful! {response}",
                "That's excellent! {response}"
            ],
            'frustrated': [
                "Let me help resolve this for you. {response}",
                "I understand your frustration. {response}",
                "Let's work through this together. {response}"
            ],
            'neutral': [
                "{response}",
                "{response}",
                "{response}"
            ]
        }
        
        self.start_time = time.time()
        
        # Start emotion monitoring thread
        self.emotion_thread = threading.Thread(target=self._monitor_emotions)
        self.emotion_thread.daemon = True
        self.emotion_thread.start()
        
        # Start health check thread
        self.health_check_thread = threading.Thread(target=self._health_check_loop)
        self.health_check_thread.daemon = True
        self.health_check_thread.start()
        
        logger.info(f"Personality Engine initialized on port {port}")
        logger.info(f"Subscribed to EmotionEngine on port {emotion_engine_port}")
        logger.info(f"Connected to CoordinatorAgent on port {coordinator_port}")
        
    def _monitor_emotions(self):
        """Monitor emotional state updates from EmotionEngine."""
        logger.info("Starting emotion monitoring thread")
        while True:
            try:
                # Check for emotion updates with a timeout
                socks = dict(self.poller.poll(1000))  # 1 second timeout
                
                if self.emotion_sub_socket in socks and socks[self.emotion_sub_socket] == zmq.POLLIN:
                    message = self.emotion_sub_socket.recv_json()
                    
                    # Check if this is an emotional state update
                    if message.get('type') == 'emotional_state_update':
                        emotional_state = message.get('data', {})
                        self._update_emotional_state(emotional_state)
                
            except Exception as e:
                logger.error(f"Error in emotion monitoring thread: {e}")
                time.sleep(1)  # Sleep to avoid tight loop in case of error
                
    def _update_emotional_state(self, emotional_state: Dict[str, Any]):
        """Update the current emotional state.
        
        Args:
            emotional_state: New emotional state from EmotionEngine
        """
        if emotional_state:
            self.current_emotional_state = emotional_state
            logger.info(f"Updated emotional state: {self.current_emotional_state}")
        
    def _health_check_loop(self):
        """Continuously check the health of the agent."""
        while True:
            try:
                # Update uptime
                self.uptime = time.time() - self.start_time
                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                
    def get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        return {
            'status': 'success',
            'uptime': time.time() - self.start_time,
            'components': {
                'personality_traits': True,
                'personality_processing': True,
                'personality_response': True,
                'emotion_subscription': True
            },
            'current_emotional_state': self.current_emotional_state,
            'personality_traits': self.personality_traits
        }
    
    def generate_response_style(self, base_response: str, 
                               user_query: str = None,
                               use_llm: bool = True) -> Dict[str, Any]:
        """Generate a styled response based on current emotional state.
        
        Args:
            base_response: The original response to style
            user_query: The original user query (for context)
            use_llm: Whether to use LLM for more complex styling
            
        Returns:
            Dictionary with styled response and metadata
        """
        try:
            # Get current dominant emotion
            emotion = self.current_emotional_state.get('dominant_emotion', 'neutral')
            combined_emotion = self.current_emotional_state.get('combined_emotion', emotion)
            intensity = self.current_emotional_state.get('intensity', 0.5)
            
            # Apply simple template-based styling if not using LLM or as fallback
            if not use_llm or emotion == 'neutral' or intensity < 0.3:
                # Get templates for this emotion
                templates = self.response_templates.get(emotion, self.response_templates['neutral'])
                
                # Select template based on intensity
                template_idx = min(int(intensity * len(templates)), len(templates) - 1)
                template = templates[template_idx]
                
                # Apply template
                styled_response = template.format(response=base_response)
                
                return {
                    'status': 'success',
                    'original_response': base_response,
                    'styled_response': styled_response,
                    'emotion': emotion,
                    'styling_method': 'template'
                }
            
            # Use LLM for more complex styling
            return self._generate_llm_styled_response(base_response, user_query, emotion, combined_emotion, intensity)
            
        except Exception as e:
            logger.error(f"Error generating response style: {e}")
            # Return original response as fallback
            return {
                'status': 'error',
                'message': str(e),
                'original_response': base_response,
                'styled_response': base_response,
                'styling_method': 'none'
            }
    
    def _generate_llm_styled_response(self, base_response: str, 
                                     user_query: str,
                                     emotion: str,
                                     combined_emotion: str,
                                     intensity: float) -> Dict[str, Any]:
        """Use LLM to generate a styled response.
        
        Args:
            base_response: The original response to style
            user_query: The original user query
            emotion: The dominant emotion
            combined_emotion: The combined emotion (with intensity)
            intensity: The emotion intensity
            
        Returns:
            Dictionary with styled response and metadata
        """
        try:
            # Prepare system prompt for the LLM
            system_prompt = f"""
            You are an AI assistant tasked with adjusting the style of a response based on the user's emotional state.
            
            Current emotional state:
            - Dominant emotion: {emotion}
            - Combined emotion: {combined_emotion}
            - Intensity: {intensity} (0.0-1.0 scale)
            
            Personality traits to maintain:
            - Helpfulness: {self.personality_traits['helpfulness']}
            - Formality: {self.personality_traits['formality']}
            - Enthusiasm: {self.personality_traits['enthusiasm']}
            - Humor: {self.personality_traits['humor']}
            - Empathy: {self.personality_traits['empathy']}
            
            Guidelines:
            1. Maintain the same factual content and information as the original response
            2. Adjust the tone, phrasing, and style to be appropriate for the user's emotional state
            3. For high intensity negative emotions (anger, frustration), be more empathetic and formal
            4. For positive emotions, be more enthusiastic and casual
            5. Keep the response concise and to the point
            6. Do not add disclaimers or explanations about the styling process
            
            Original response to restyle:
            {base_response}
            """
            
            # Prepare user query context
            user_context = f"User query: {user_query}" if user_query else "No user query provided"
            
            # Send request to CoordinatorAgent
            self.coordinator_socket.send_json({
                'action': 'request_model_inference',
                'model_name': 'default',
                'prompt': user_context,
                'system_prompt': system_prompt,
                'temperature': 0.4,  # Lower temperature for more consistent styling
                'request_id': f"personality_style_{int(time.time())}"
            })
            
            # Wait for response with timeout
            socks = dict(self.poller.poll(self.request_timeout))
            if self.coordinator_socket in socks and socks[self.coordinator_socket] == zmq.POLLIN:
                response = self.coordinator_socket.recv_json()
                
                if response.get('status') != 'success':
                    logger.error(f"Error from CoordinatorAgent: {response.get('message')}")
                    raise Exception(f"LLM styling failed: {response.get('message')}")
                
                # Extract the styled response
                styled_response = response.get('result', base_response).strip()
                
                # Clean up any potential formatting artifacts
                styled_response = re.sub(r'^["\'`]|["\'`]$', '', styled_response)  # Remove quotes
                
                return {
                    'status': 'success',
                    'original_response': base_response,
                    'styled_response': styled_response,
                    'emotion': emotion,
                    'combined_emotion': combined_emotion,
                    'intensity': intensity,
                    'styling_method': 'llm'
                }
            else:
                # Socket timed out, fall back to template-based styling
                logger.warning("LLM request timed out, falling back to template styling")
                
                # Get templates for this emotion
                templates = self.response_templates.get(emotion, self.response_templates['neutral'])
                
                # Select template based on intensity
                template_idx = min(int(intensity * len(templates)), len(templates) - 1)
                template = templates[template_idx]
                
                # Apply template
                styled_response = template.format(response=base_response)
                
                return {
                    'status': 'success',
                    'original_response': base_response,
                    'styled_response': styled_response,
                    'emotion': emotion,
                    'styling_method': 'template_fallback'
                }
                
        except Exception as e:
            logger.error(f"Error generating LLM styled response: {e}")
            # Return original response as fallback
            return {
                'status': 'error',
                'message': str(e),
                'original_response': base_response,
                'styled_response': base_response,
                'styling_method': 'none'
            }
        
    def run(self):
        """Run the main agent loop."""
        logger.info("Starting Personality Engine main loop")
        
        while True:
            try:
                # Wait for next request
                message = self.socket.recv_json()
                logger.info(f"Received request: {message}")
                
                # Process request
                response = self._handle_request(message)
                
                # Send response
                self.socket.send_json(response)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                try:
                    self.socket.send_json({
                        'status': 'error',
                        'message': str(e)
                    })
                except zmq.error.ZMQError as zmq_err:
                    logger.error(f"ZMQ error sending response: {zmq_err}")
                
    def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action')
        
        if action == 'ping':
            return {'status': 'success', 'message': 'pong'}
            
        elif action == 'get_health':
            return self.get_health_status()
            
        elif action == 'generate_response_style':
            base_response = request.get('response', '')
            user_query = request.get('user_query', '')
            use_llm = request.get('use_llm', True)
            
            if not base_response:
                return {'status': 'error', 'message': 'Missing required parameter: response'}
                
            return self.generate_response_style(base_response, user_query, use_llm)
            
        elif action == 'get_emotional_state':
            return {
                'status': 'success',
                'emotional_state': self.current_emotional_state
            }
            
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}
            
    def stop(self):
        """Stop the agent and clean up resources."""
        self.socket.close()
        self.emotion_sub_socket.close()
        self.coordinator_socket.close()
        self.context.term()
        logger.info("Personality Engine stopped")


    def health_check(self):
        '''
        Performs a health check on the agent, returning a dictionary with its status.
        '''
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
            # TODO: Add agent-specific health checks here.
            # For example, check if a required connection is alive.
            # if not self.some_service_connection.is_alive():
            #     is_healthy = False

            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else -1,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {} # Placeholder for agent-specific data
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "error": f"Health check failed with exception: {str(e)}"
            }

if __name__ == '__main__':
    agent = PersonalityEngine()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise