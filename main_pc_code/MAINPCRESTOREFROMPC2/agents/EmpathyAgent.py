import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
MAIN_PC_CODE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if MAIN_PC_CODE not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE)

from src.core.base_agent import BaseAgent
import zmq
import json
import logging
import threading
import time
from typing import Dict, Any, Tuple, Optional
import numpy as np
from datetime import datetime
from utils.config_parser import parse_agent_args

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
_agent_args = parse_agent_args()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('empathy_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EmpathyAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="Empathyagent")
        """Initialize the EmpathyAgent with ZMQ sockets.
        
        Args:
            port: Port for receiving requests
            emotion_engine_port: Port for subscribing to EmotionEngine broadcasts
            tts_connector_port: Port for sending voice settings to TTSConnector
        """
        self.port = port if port is not None else getattr(_agent_args, 'port', 5585)
        # Retrieve ports from command-line/args or default values
        emotion_engine_port = getattr(_agent_args, 'emotionengine_port', 5582)
        tts_connector_port = getattr(_agent_args, 'ttsconnector_port', 5582)
        self.emotion_engine_port = emotion_engine_port
        self.tts_connector_port = tts_connector_port
        
        # Initialize ZMQ context and sockets
        self.context = zmq.Context()
        
        # REP socket for handling requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://*:{self.port}")
        
        # SUB socket for subscribing to EmotionEngine broadcasts
        self.emotion_sub_socket = self.context.socket(zmq.SUB)
        # Determine host from args or default
        if isinstance(_agent_args, dict):
            _host = _agent_args.get('host', 'localhost')
        else:
            _host = getattr(_agent_args, 'host', 'localhost')
        self.emotion_sub_socket.connect(f"tcp://{_host}:{emotion_engine_port}")
        self.emotion_sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all messages
        
        # REQ socket for TTSConnector
        self.tts_socket = self.context.socket(zmq.REQ)
        self.tts_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.tts_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.tts_socket.connect(f"tcp://{_host}:{tts_connector_port}")
        
        # Initialize poller for non-blocking socket operations
        self.poller = zmq.Poller()
        self.poller.register(self.emotion_sub_socket, zmq.POLLIN)
        self.poller.register(self.tts_socket, zmq.POLLIN)
        
        # Set timeout for requests (in milliseconds)
        self.request_timeout = 5000  # 5 seconds
        
        # Initialize current emotional state
        self.current_emotional_state = {
            'tone': 'neutral',
            'sentiment': 0.0,
            'intensity': 0.5,
            'dominant_emotion': 'neutral',
            'combined_emotion': 'neutral',
            'timestamp': time.time()
        }
        
        # Voice settings for different emotions
        self.voice_settings = {
            'neutral': {
                'pitch': 0.0,      # Default pitch
                'speed': 1.0,      # Default speed
                'volume': 1.0,     # Default volume
                'stability': 0.5,  # Default stability
                'clarity': 0.5     # Default clarity
            },
            'happy': {
                'pitch': 0.3,      # Higher pitch
                'speed': 1.15,     # Slightly faster
                'volume': 1.1,     # Slightly louder
                'stability': 0.6,  # More stable
                'clarity': 0.7     # More clear
            },
            'sad': {
                'pitch': -0.2,     # Lower pitch
                'speed': 0.9,      # Slower
                'volume': 0.9,     # Quieter
                'stability': 0.4,  # Less stable
                'clarity': 0.4     # Less clear
            },
            'angry': {
                'pitch': 0.1,      # Slightly higher pitch
                'speed': 1.1,      # Slightly faster
                'volume': 1.2,     # Louder
                'stability': 0.3,  # Less stable
                'clarity': 0.6     # More clear
            },
            'frustrated': {
                'pitch': 0.0,      # Normal pitch
                'speed': 1.05,     # Slightly faster
                'volume': 1.1,     # Slightly louder
                'stability': 0.4,  # Less stable
                'clarity': 0.5     # Normal clarity
            },
            'fearful': {
                'pitch': 0.2,      # Higher pitch
                'speed': 1.1,      # Faster
                'volume': 0.9,     # Quieter
                'stability': 0.3,  # Less stable
                'clarity': 0.4     # Less clear
            },
            'surprised': {
                'pitch': 0.4,      # Much higher pitch
                'speed': 1.2,      # Faster
                'volume': 1.2,     # Louder
                'stability': 0.5,  # Normal stability
                'clarity': 0.6     # More clear
            },
            'disgusted': {
                'pitch': -0.1,     # Slightly lower pitch
                'speed': 0.95,     # Slightly slower
                'volume': 1.0,     # Normal volume
                'stability': 0.4,  # Less stable
                'clarity': 0.5     # Normal clarity
            },
            'excited': {
                'pitch': 0.3,      # Higher pitch
                'speed': 1.2,      # Faster
                'volume': 1.2,     # Louder
                'stability': 0.6,  # More stable
                'clarity': 0.7     # More clear
            },
            'calm': {
                'pitch': -0.1,     # Slightly lower pitch
                'speed': 0.9,      # Slower
                'volume': 0.9,     # Quieter
                'stability': 0.7,  # More stable
                'clarity': 0.6     # More clear
            }
        }
        
        # Start emotion monitoring thread
        self.emotion_thread = threading.Thread(target=self._monitor_emotions)
        self.emotion_thread.daemon = True
        self.emotion_thread.start()
        
        # Track agent start time
        self.start_time = time.time()
        
        logger.info(f"EmpathyAgent initialized on port {port}")
        logger.info(f"Subscribed to EmotionEngine on port {emotion_engine_port}")
        logger.info(f"Connected to TTSConnector on port {tts_connector_port}")
    
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
        """Update the current emotional state and adjust voice settings.
        
        Args:
            emotional_state: New emotional state from EmotionEngine
        """
        if emotional_state:
            self.current_emotional_state = emotional_state
            logger.info(f"Updated emotional state: {self.current_emotional_state}")
            
            # Determine new voice settings based on updated emotional state
            voice_settings = self.determine_voice_settings()
            
            # Send updated voice settings to TTSConnector
            self._send_voice_settings_to_tts(voice_settings)
    
    def determine_voice_settings(self) -> Dict[str, Any]:
        """Determine voice settings based on current emotional state.
        
        Returns:
            Dictionary of voice settings
        """
        try:
            # Extract emotional state information
            dominant_emotion = self.current_emotional_state.get('dominant_emotion', 'neutral')
            combined_emotion = self.current_emotional_state.get('combined_emotion', dominant_emotion)
            intensity = self.current_emotional_state.get('intensity', 0.5)
            
            # Get base settings for the dominant emotion
            if combined_emotion in self.voice_settings:
                base_settings = self.voice_settings[combined_emotion].copy()
            elif dominant_emotion in self.voice_settings:
                base_settings = self.voice_settings[dominant_emotion].copy()
            else:
                base_settings = self.voice_settings['neutral'].copy()
            
            # Adjust settings based on intensity
            neutral_settings = self.voice_settings['neutral']
            
            # Scale adjustments based on intensity
            for param in base_settings:
                if intensity < 0.5:
                    # Blend with neutral settings if intensity is low
                    blend_factor = intensity * 2  # Scale to 0-1 range
                    base_settings[param] = np.interp(blend_factor, [0, 1], 
                                                   [neutral_settings[param], base_settings[param]])
                else:
                    # Enhance settings if intensity is high
                    enhance_factor = (intensity - 0.5) * 2  # Scale to 0-1 range
                    param_diff = base_settings[param] - neutral_settings[param]
                    base_settings[param] += param_diff * enhance_factor * 0.3  # Add up to 30% more
            
            # Ensure values are within acceptable ranges
            base_settings['pitch'] = max(-1.0, min(1.0, base_settings['pitch']))
            base_settings['speed'] = max(0.5, min(2.0, base_settings['speed']))
            base_settings['volume'] = max(0.5, min(2.0, base_settings['volume']))
            base_settings['stability'] = max(0.0, min(1.0, base_settings['stability']))
            base_settings['clarity'] = max(0.0, min(1.0, base_settings['clarity']))
            
            # Add metadata
            base_settings['emotion'] = dominant_emotion
            base_settings['combined_emotion'] = combined_emotion
            base_settings['intensity'] = intensity
            base_settings['timestamp'] = time.time()
            
            logger.info(f"Determined voice settings: {base_settings}")
            
            return base_settings
            
        except Exception as e:
            logger.error(f"Error determining voice settings: {e}")
            # Return default settings as fallback
            return self.voice_settings['neutral'].copy()
    
    def _send_voice_settings_to_tts(self, voice_settings: Dict[str, Any]):
        """Send voice settings to TTSConnector.
        
        Args:
            voice_settings: Voice settings to send
        """
        try:
            # Prepare request
            request = {
                'action': 'update_voice_settings',
                'voice_settings': voice_settings
            }
            
            # Send request
            self.tts_socket.send_json(request)
            
            # Wait for response with timeout
            socks = dict(self.poller.poll(self.request_timeout))
            if self.tts_socket in socks and socks[self.tts_socket] == zmq.POLLIN:
                response = self.tts_socket.recv_json()
                
                if response.get('status') == 'success':
                    logger.info("Voice settings successfully sent to TTSConnector")
                else:
                    logger.warning(f"TTSConnector reported error: {response.get('message')}")
            else:
                # Socket timed out
                logger.warning("Timeout waiting for response from TTSConnector")
                
        except Exception as e:
            logger.error(f"Error sending voice settings to TTSConnector: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent.
        
        Returns:
            Dictionary with health status information
        """
        return {
            'status': 'success',
            'uptime': time.time() - self.start_time,
            'components': {
                'emotion_subscription': True,
                'tts_connection': True,
                'voice_settings': True
            },
            'current_emotional_state': self.current_emotional_state
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests.
        
        Args:
            request: Request dictionary
            
        Returns:
            Response dictionary
        """
        action = request.get('action')

        # Respond to orchestrator health checks
        if action in ('health_check', 'health', 'ping'):
            return {
                'status': 'ok',
                'message': 'EmpathyAgent healthy',
                'timestamp': datetime.now().isoformat()
            }
        
        if action == 'ping':
            return {'status': 'success', 'message': 'pong'}
            
        elif action == 'get_health':
            return self.get_health_status()
        
        elif action == 'get_voice_settings':
            # Get voice settings for specific text if provided
            text = request.get('text', '')
            emotion_override = request.get('emotion', None)
            
            # If emotion override is provided, temporarily update emotional state
            if emotion_override:
                temp_state = self.current_emotional_state.copy()
                temp_state['dominant_emotion'] = emotion_override
                self._update_emotional_state(temp_state)
            
            # Determine voice settings
            voice_settings = self.determine_voice_settings()
            
            return {
                'status': 'success',
                'voice_settings': voice_settings
            }
            
        elif action == 'update_emotional_state':
            emotional_state = request.get('emotional_state', {})
            self._update_emotional_state(emotional_state)
            
            return {
                'status': 'success',
                'message': 'Emotional state updated',
                'current_emotional_state': self.current_emotional_state
            }
            
        else:
            return {
                'status': 'error',
                'message': f'Unknown action: {action}'
            }
    
    def run(self):
        """Main loop for handling requests."""
        logger.info("EmpathyAgent started")
        
        while True:
            try:
                # Wait for next request
                message = self.socket.recv_json()
                logger.debug(f"Received request: {message}")
                
                # Process request
                response = self.handle_request(message)
                
                # Send response
                self.socket.send_json(response)
                logger.debug(f"Sent response: {response}")
                
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                try:
                    self.socket.send_json({
                        'status': 'error',
                        'message': str(e)
                    })
                except zmq.error.ZMQError as zmq_err:
                    logger.error(f"ZMQ error sending response: {zmq_err}")
    
    def stop(self):
        """Stop the agent and clean up resources."""
        self.socket.close()
        self.emotion_sub_socket.close()
        self.tts_socket.close()
        self.context.term()
        logger.info("EmpathyAgent stopped")

if __name__ == '__main__':
    agent = EmpathyAgent()
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