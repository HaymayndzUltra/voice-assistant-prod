from src.core.base_agent import BaseAgent
"""
Emotion Engine Agent
Manages and processes emotional states and responses
"""

import zmq
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from utils.config_parser import parse_agent_args
_agent_args = parse_agent_args()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('emotion_engine.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('EmotionEngine')

class EmotionEngine(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        """Initialize the Emotion Engine.
        
        Args:
            port: Port for receiving requests
            pub_port: Port for publishing emotional state updates
        """
        if port is not None:
            self.port = port
        elif hasattr(_agent_args, 'port'):
            self.port = int(_agent_args.port)
        else:
            raise ValueError("Port must be provided either through constructor or agent arguments")
        if 'pub_port' in kwargs and kwargs['pub_port'] is not None:
            self.pub_port = kwargs['pub_port']
        elif hasattr(_agent_args, 'port'):
            self.pub_port = int(_agent_args.port) + 2  # Use port + 2 to avoid conflict with health check port
        else:
            self.pub_port = None
            
        # Initialize ZMQ in background
        self.initialization_status = {
            "is_initialized": False,
            "error": None,
            "progress": 0.0
        }
        
        super().__init__(port=self.port, name="EmotionEngine")
        
        # Initialize basic state
        self.current_emotional_state = {
            'tone': 'neutral',
            'sentiment': 0.0,
            'intensity': 0.5,
            'dominant_emotion': 'neutral',
            'timestamp': time.time()
        }
        
        # Define emotional state thresholds and mappings
        self.emotion_thresholds = {
            'sentiment': {
                'very_negative': -0.8,
                'negative': -0.3,
                'neutral': 0.3,
                'positive': 0.8
            },
            'intensity': {
                'low': 0.3,
                'medium': 0.7,
                'high': 1.0
            }
        }
        
        # Emotion combination mappings
        self.emotion_combinations = {
            ('angry', 'high'): 'furious',
            ('angry', 'medium'): 'annoyed',
            ('angry', 'low'): 'irritated',
            ('sad', 'high'): 'devastated',
            ('sad', 'medium'): 'unhappy',
            ('sad', 'low'): 'disappointed',
            ('happy', 'high'): 'ecstatic',
            ('happy', 'medium'): 'pleased',
            ('happy', 'low'): 'content'
        }
        
        self.start_time = time.time()
        self.last_broadcast_time = time.time()
        
        self.init_thread = threading.Thread(target=self._perform_initialization, daemon=True)
        self.init_thread.start()
        
        # Start health check thread
        self.health_check_thread = threading.Thread(target=self._health_check_loop)
        self.health_check_thread.daemon = True
        self.health_check_thread.start()
        logger.info(f"Health check thread started on port {self.port + 1}")
        
        logger.info(f"Emotion Engine basic initialization complete")
        
    def _perform_initialization(self):
        """Perform ZMQ initialization in background."""
        try:
            # BaseAgent already initialized the main socket and health socket
            # We just need to initialize the PUB socket for broadcasting emotional state updates
            if self.pub_port:
                self.pub_socket = self.context.socket(zmq.PUB)
                self.pub_socket.bind(f"tcp://*:{self.pub_port}")
                logger.info(f"Emotion Engine PUB socket initialized on port {self.pub_port}")
            
            # Mark as initialized
            self.initialization_status.update({
                "is_initialized": True,
                "progress": 1.0
            })
            logger.info(f"Emotion Engine initialization complete on port {self.port} with PUB socket on port {self.pub_port}")
            
        except Exception as e:
            self.initialization_status.update({
                "error": str(e),
                "progress": 0.0
            })
            logger.error(f"ZMQ initialization failed: {e}")
        
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
                'emotion_detection': True,
                'emotion_processing': True,
                'emotion_broadcast': self.initialization_status["is_initialized"]
            },
            'current_emotional_state': self.current_emotional_state,
            'initialization_status': self.initialization_status
        }
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Override BaseAgent's health status to include EmotionEngine-specific info."""
        base_status = super()._get_health_status()
        base_status.update({
            'service': 'emotion_engine',
            'components': {
                'emotion_detection': True,
                'emotion_processing': True,
                'emotion_broadcast': self.initialization_status["is_initialized"]
            },
            'current_emotional_state': self.current_emotional_state,
            'initialization_status': self.initialization_status
        })
        return base_status
    
    def update_emotional_state(self, emotional_cues: Dict[str, Any]) -> Dict[str, Any]:
        """Update the current emotional state based on new cues.
        
        Args:
            emotional_cues: Dictionary containing emotional cues (tone, sentiment, etc.)
            
        Returns:
            Updated emotional state
        """
        try:
            # Extract emotional cues
            tone = emotional_cues.get('tone', self.current_emotional_state['tone'])
            sentiment = emotional_cues.get('sentiment', self.current_emotional_state['sentiment'])
            intensity = emotional_cues.get('intensity', self.current_emotional_state['intensity'])
            
            # Normalize values if needed
            if isinstance(sentiment, str):
                try:
                    sentiment = float(sentiment)
                except ValueError:
                    sentiment = 0.0
                    
            if isinstance(intensity, str):
                try:
                    intensity = float(intensity)
                except ValueError:
                    intensity = 0.5
            
            # Ensure values are within proper ranges
            sentiment = max(-1.0, min(1.0, sentiment))
            intensity = max(0.0, min(1.0, intensity))
            
            # Determine intensity level
            intensity_level = 'low'
            if intensity >= self.emotion_thresholds['intensity']['high']:
                intensity_level = 'high'
            elif intensity >= self.emotion_thresholds['intensity']['medium']:
                intensity_level = 'medium'
                
            # Determine dominant emotion based on tone and sentiment
            dominant_emotion = tone
            if not tone or tone == 'neutral':
                # Determine emotion from sentiment if tone is neutral
                if sentiment <= self.emotion_thresholds['sentiment']['very_negative']:
                    dominant_emotion = 'angry'
                elif sentiment <= self.emotion_thresholds['sentiment']['negative']:
                    dominant_emotion = 'sad'
                elif sentiment >= self.emotion_thresholds['sentiment']['positive']:
                    dominant_emotion = 'happy'
                else:
                    dominant_emotion = 'neutral'
            
            # Check for special emotion combinations
            combined_emotion = self.emotion_combinations.get((dominant_emotion, intensity_level), dominant_emotion)
            
            # Update the current emotional state
            self.current_emotional_state = {
                'tone': tone,
                'sentiment': sentiment,
                'intensity': intensity,
                'intensity_level': intensity_level,
                'dominant_emotion': dominant_emotion,
                'combined_emotion': combined_emotion,
                'timestamp': time.time()
            }
            
            # Broadcast the updated emotional state if initialized
            if self.initialization_status["is_initialized"]:
                self._broadcast_emotional_state()
            
            logger.info(f"Updated emotional state: {self.current_emotional_state}")
            
            return self.current_emotional_state
            
        except Exception as e:
            logger.error(f"Error updating emotional state: {e}")
            return self.current_emotional_state
    
    def _broadcast_emotional_state(self):
        """Broadcast the current emotional state to subscribers."""
        try:
            # Only broadcast if enough time has passed since last broadcast
            current_time = time.time()
            if current_time - self.last_broadcast_time >= 1.0:  # Broadcast at most once per second
                # Prepare message
                message = {
                    'type': 'emotional_state_update',
                    'data': self.current_emotional_state,
                    'timestamp': current_time
                }
                
                # Broadcast message
                self.pub_socket.send_json(message)
                
                self.last_broadcast_time = current_time
                logger.debug(f"Broadcasted emotional state: {message}")
        except Exception as e:
            logger.error(f"Error broadcasting emotional state: {e}")
    
    def get_emotional_state(self) -> Dict[str, Any]:
        """Get the current emotional state.
        
        Returns:
            Current emotional state
        """
        return self.current_emotional_state
        
    def run(self):
        """Run the main agent loop."""
        logger.info("Starting Emotion Engine main loop")
        
        # Call parent's run method to ensure health check thread works
        super().run()
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Override BaseAgent's handle_request to handle EmotionEngine-specific requests."""
        action = request.get('action')
        
        if action == 'ping':
            return {'status': 'success', 'message': 'pong'}
            
        elif action == 'get_health':
            return self.get_health_status()
            
        elif action == 'update_emotional_state':
            emotional_cues = request.get('emotional_cues', {})
            updated_state = self.update_emotional_state(emotional_cues)
            return {
                'status': 'success',
                'emotional_state': updated_state
            }
            
        elif action == 'get_emotional_state':
            return {
                'status': 'success',
                'emotional_state': self.get_emotional_state()
            }
            
        else:
            # Call parent's handle_request for other actions
            return super().handle_request(request)
            
    def stop(self):
        """Stop the agent and clean up resources."""
        logger.info("Stopping Emotion Engine...")

        if hasattr(self, 'pub_socket'):
            self.pub_socket.close()

        # Wait for background threads to finish
        if hasattr(self, 'init_thread') and self.init_thread.is_alive():
            self.init_thread.join(timeout=2)

        if hasattr(self, 'health_check_thread') and self.health_check_thread.is_alive():
            self.health_check_thread.join(timeout=2)

        super().cleanup()
        logger.info("Emotion Engine stopped")

if __name__ == '__main__':
    import argparse
    import atexit
    import signal

    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=None)
    args = parser.parse_args()
    
    agent = EmotionEngine(port=args.port)

    def graceful_exit(*args):
        agent.stop()
        exit(0)

    # Handle Ctrl+C and termination signals
    signal.signal(signal.SIGINT, graceful_exit)
    signal.signal(signal.SIGTERM, graceful_exit)

    # Make sure cleanup runs on normal exit
    atexit.register(graceful_exit)

    try:
        agent.run()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        agent.stop() 
