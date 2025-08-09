"""
Emotion Engine Agent
Manages and processes emotional states and responses
"""

# Import path manager for containerization-friendly paths
import sys
import os

# Removed # Removed 
import os
from common.pools.zmq_pool import get_rep_socket
import json
import threading
import time
import psutil
import signal
from datetime import datetime
from typing import Dict, Any
from common.core.base_agent import BaseAgent

# Configure logging using canonical approach
from common.utils.log_setup import configure_logging
logger = configure_logging(__name__, log_to_file=True)

class EmotionEngine(BaseAgent):
    def __init__(self, config=None, **kwargs):
        """Initialize the Emotion Engine with proper template compliance."""
        # Ensure config is a dictionary
        config = config or {}
        
        # Get name and port from config or environment
        agent_name = kwargs.get('name', os.environ.get("AGENT_NAME", "EmotionEngine"))
        
        # Safe port resolution with proper fallbacks
        port_value = kwargs.get('port') or os.environ.get("AGENT_PORT") or config.get("port") or 5590
        agent_port = int(port_value)
        health_port = int(os.environ.get("HEALTH_CHECK_PORT", str(agent_port + 1)))
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=agent_name, port=agent_port)
        
        # Project root setup (        self.project_root = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.abspath(__file__)))
        
        # Save core parameters
        self.port = agent_port
        self.health_port = health_port
        self.name = agent_name
        self.running = True
        self.start_time = time.time()
        
        # Additional ports
        self.pub_port = int(config.get("pub_port", agent_port + 2))
        
        # Initialize ZMQ components
        self.context = None
        self.socket = None
        self.health_socket = None
        self.pub_socket = None
        
        # Setup ZMQ
        self.setup_zmq()
        
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
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Start health check thread
        self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_thread.start()

        # Modern error reporting now handled by BaseAgent's UnifiedErrorHandler

        # Initialization complete
        logger.info(f"{self.name} initialized on port {self.port} (health: {self.health_port}, pub: {self.pub_port})")

    def _signal_handler(self, sig, frame):
        """Handle signals for graceful termination"""
        logger.info(f"Received signal {sig}, shutting down")
        self.running = False
        time.sleep(1)  # Give threads time to notice
        self.cleanup()
        sys.exit(0)

    def setup_zmq(self):
        """Set up ZMQ sockets with proper error handling"""
        try:
            self.context = None  # Using pool
            
            # Main socket
            self.socket = get_rep_socket(self.endpoint).socket
            self.socket.setsockopt(zmq.LINGER, 0)
            self.socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            
            # Health socket
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.setsockopt(zmq.LINGER, 0)
            self.health_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            
            # PUB socket for broadcasting
            self.pub_socket = self.context.socket(zmq.PUB)
            self.pub_socket.setsockopt(zmq.LINGER, 0)
            
            # Bind sockets with retry logic
            self._bind_socket_with_retry(self.socket, self.port)
            self._bind_socket_with_retry(self.health_socket, self.health_port)
            self._bind_socket_with_retry(self.pub_socket, self.pub_port)
            
            logger.info(f"Successfully set up ZMQ sockets on ports {self.port}, {self.health_port}, and {self.pub_port}")
            return True
        except Exception as e:
            logger.error(f"Error setting up ZMQ: {e}")
            self.cleanup()
            return False
    
    def _bind_socket_with_retry(self, socket, port, max_retries=5):
        """Bind a socket with retry logic"""
        retries = 0
        while retries < max_retries:
            try:
                socket.bind(f"tcp://*:{port}")
                logger.info(f"Successfully bound to port {port}")
                return True
            except zmq.error.ZMQError as e:
                retries += 1
                logger.warning(f"Failed to bind to port {port} (attempt {retries}/{max_retries}): {e}")
                if retries >= max_retries:
                    logger.error(f"Failed to bind to port {port} after {max_retries} attempts")
                    raise
                time.sleep(1)  # Wait before retrying
        return False
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        return {
            'status': 'ok',
            'name': self.name,
            'uptime': time.time() - self.start_time,
            'service': 'emotion_engine',
            'components': {
                'emotion_detection': True,
                'emotion_processing': True,
                'emotion_broadcast': True
            },
            'current_emotional_state': self.current_emotional_state
        }

    def _broadcast_emotional_state(self):
        """Broadcast the current emotional state to subscribers."""
        try:
            if hasattr(self, 'pub_socket') and self.pub_socket:
                # Format message
                message = {
                    'type': 'emotional_state_update',
                    'data': self.current_emotional_state,
                    'timestamp': time.time()
                }
                
                # Send as JSON
                self.pub_socket.send_json(message)
                logger.debug(f"Broadcasted emotional state: {self.current_emotional_state['dominant_emotion']}")
        except Exception as e:
            logger.error(f"Error broadcasting emotional state: {e}")
    
    def get_emotional_state(self) -> Dict[str, Any]:
        """Get the current emotional state."""
        return self.current_emotional_state
    
    def run(self):
        """Main run loop with proper error handling."""
        logger.info(f"Starting {self.name}")
        
        try:
            while self.running:
                try:
                    # Check for main socket messages with timeout
                    if self.socket and self.socket.poll(1000) != 0:
                        # Try to receive as JSON, fallback to decode if needed
                        from common_utils.error_handling import SafeExecutor
                        import zmq
                        
                        with SafeExecutor(logger, recoverable=(zmq.ZMQError, json.JSONDecodeError, UnicodeDecodeError)):
                            message = self.socket.recv_json()
                        
                        if not message:  # If SafeExecutor returned None due to error
                            with SafeExecutor(logger, recoverable=(zmq.ZMQError, json.JSONDecodeError, UnicodeDecodeError), default_return={}):
                                raw_message = self.socket.recv()
                                message = json.loads(raw_message.decode('utf-8'))
                            
                        if not message:  # Final fallback
                            logger.error("Failed to decode message as JSON")
                            message = {}
                        logger.info(f"Received message: {message}")
                        
                        # Process message
                        response = self.handle_request(message)
                        
                        # Send response
                        if self.socket:
                            self.socket.send_json(response)
                            logger.debug("Sent response")
                except zmq.error.Again:
                    # Timeout on receive, this is normal
                    pass
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                
                # Periodic status logging
                if int(time.time()) % 30 == 0:  # Log every 30 seconds
                    logger.info(f"{self.name} is running (uptime: {time.time() - self.start_time:.1f}s)")
                    time.sleep(1)  # Avoid multiple logs in the same second
                else:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.cleanup()
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        try:
            # Extract action
            action = request.get('action', '')
            
            if action == 'update_emotional_state':
                # Update emotional state
                emotional_cues = request.get('emotional_cues', {})
                updated_state = self.update_emotional_state(emotional_cues)
                return {
                    'status': 'ok',
                    'message': 'Emotional state updated',
                    'emotional_state': updated_state
                }
            elif action == 'get_emotional_state':
                # Return current emotional state
                return {
                    'status': 'ok',
                    'emotional_state': self.get_emotional_state()
                }
            elif action == 'health_check':
                # Return health status
                return self._get_health_status()
            else:
                # Unknown action
                return {
                    'status': 'error',
                    'message': f'Unknown action: {action}'
                }
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def update_emotional_state(self, emotional_cues: Dict[str, Any]) -> Dict[str, Any]:
        """Update the current emotional state based on new cues."""
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
            
            # Broadcast the updated emotional state
            self._broadcast_emotional_state()
            
            logger.info(f"Updated emotional state: {self.current_emotional_state}")
            
            return self.current_emotional_state
            
        except Exception as e:
            logger.error(f"Error updating emotional state: {e}")
            return self.current_emotional_state
    
    def health_check(self):
        """Performs a health check on the agent, returning a dictionary with its status."""
        try:
            # Basic health check logic
            is_healthy = self.running  # Assume healthy if running
            
            # Check if sockets are initialized
            if not hasattr(self, 'socket') or not self.socket:
                is_healthy = False
            if not hasattr(self, 'health_socket') or not self.health_socket:
                is_healthy = False
            if not hasattr(self, 'pub_socket') or not self.pub_socket:
                is_healthy = False

            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {
                    "current_emotional_state": self.current_emotional_state,
                    "emotion_thresholds": self.emotion_thresholds
                }
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            logger.error(f"Health check failed with exception: {str(e)}")
            return {
                "status": "unhealthy",
                "agent_name": self.name,
                "error": f"Health check failed with exception: {str(e)}"
            }
    
    def cleanup(self):
        """Clean up resources with proper error handling"""
        logger.info("Cleaning up resources")
        self.running = False
        
        # Close sockets
        if hasattr(self, 'socket') and self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"Error closing main socket: {e}")
        
        if hasattr(self, 'health_socket') and self.health_socket:
            try:
                self.health_socket.close()
            except Exception as e:
                logger.error(f"Error closing health socket: {e}")
        
        if hasattr(self, 'pub_socket') and self.pub_socket:
            try:
                self.pub_socket.close()
            except Exception as e:
                logger.error(f"Error closing pub socket: {e}")
        
        # Terminate context
        if hasattr(self, 'context') and self.context:
            try:
                self.context.term()
            except Exception as e:
                logger.error(f"Error terminating ZMQ context: {e}")
        
        logger.info(f"{self.name} stopped")

# If executed directly
if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Emotion Engine')
    parser.add_argument('--name', type=str, default="EmotionEngine", help='Agent name')
    parser.add_argument('--port', type=int, default=None, help='Agent port')
    args = parser.parse_args()
    
    # Create and run the agent
    agent = EmotionEngine(name=args.name, port=args.port)
    try:
        agent.run()
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup() 