import sys
import os


# Import path manager for containerization-friendly paths
import sys
import os
import os
import sys
from pathlib import Path
from common.utils.path_manager import PathManager

# Add the project's main_pc_code directory to the Python path
project_root = str(PathManager.get_project_root())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from common.core.base_agent import BaseAgent
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import threading
from common.config_manager import load_unified_config
from main_pc_code.utils.service_discovery_client import get_service_address, register_service
# from main_pc_code.src.network.secure_zmq import is_secure_zmq_enabled, configure_secure_client, configure_secure_server

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))

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
        # Default port and name from config
        agent_port = config.get("port", 5703) if port is None else port
        agent_name = config.get("name", 'EmpathyAgent')

        super().__init__(port=agent_port, name=agent_name)

        self.context = None  # Using pool
        self.tts_socket = None
        
        self.running = True
        self.start_time = time.time()
        
        # Profile stores the emotional state and corresponding voice settings
        self.current_profile = {
            "persona": "neutral",
            "voice_settings": {"speed": 1.0, "pitch": 1.0, "volume": 1.0}
        }
        
        self.initialization_status = {"is_initialized": False, "error": None}
        threading.Thread(target=self._initialize_connections, daemon=True).start()
        
        logger.info(f"EmpathyAgent initialized on port {self.port}")

    def _initialize_connections(self):
        """Initialize connections to dependent services."""
        try:
            # Connect to StreamingTTSAgent
            tts_address = get_service_address("StreamingTTSAgent")
            if tts_address:
                self.tts_socket = self.context.socket(zmq.REQ)
                # if is_secure_zmq_enabled():
                #     configure_secure_client(self.tts_socket)
                self.tts_socket.setsockopt(zmq.RCVTIMEO, 5000)
                self.tts_socket.setsockopt(zmq.SNDTIMEO, 5000)
                self.tts_socket.connect(tts_address)
                logger.info(f"Connected to StreamingTTSAgent at {tts_address}")
            else:
                logger.warning("StreamingTTSAgent not found in service discovery. Voice settings will not be sent.")

            self.initialization_status["is_initialized"] = True
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            self.initialization_status["error"] = str(e)
            
    def update_emotional_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Update the agent's emotional profile and forward voice settings."""
        logger.info(f"Updating emotional profile to: {profile}")
        self.current_profile = profile
        
        # Forward voice settings to TTS
        if self.tts_socket:
            return self.send_voice_settings_to_tts()
        else:
            msg = "Cannot send voice settings: StreamingTTSAgent not connected."
            logger.warning(msg)
            return {'status': 'warning', 'message': msg}

    def send_voice_settings_to_tts(self) -> Dict[str, Any]:
        """Send current voice settings to StreamingTTSAgent."""
        if not self.tts_socket:
            return {'status': 'error', 'message': 'TTS socket not available.'}
            
        try:
            request = {
                'action': 'update_voice_settings',
                'settings': self.current_profile.get('voice_settings', {})
            }
            self.tts_socket.send_json(request)
            
            response = self.tts_socket.recv_json()
            if response.get('status') == 'success':
                logger.info("Voice settings successfully sent to StreamingTTSAgent.")
            else:
                logger.warning(f"StreamingTTSAgent reported error: {response.get('message')}")
            return response
            
        except zmq.Again:
            msg = "Timeout waiting for response from StreamingTTSAgent"
            logger.warning(msg)
            return {'status': 'error', 'message': msg}
        except Exception as e:
            msg = f"Error sending voice settings to StreamingTTSAgent: {e}"
            logger.error(msg)
            return {'status': 'error', 'message': str(e)}

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
            self.current_profile['persona'] = emotional_state.get('dominant_emotion', 'neutral')
            self.current_profile['voice_settings'] = self.determine_voice_settings()
            logger.info(f"Updated emotional state: {self.current_profile}")
            
            # Send updated voice settings to TTSConnector
            self.send_voice_settings_to_tts()
    
    def determine_voice_settings(self) -> Dict[str, Any]:
        """Determine voice settings based on current emotional state.
        
        Returns:
            Dictionary of voice settings
        """
        try:
            # Extract emotional state information
            dominant_emotion = self.current_profile['persona']
            intensity = 0.5 # Placeholder, actual intensity would come from emotional_state
            
            # Get base settings for the dominant emotion
            if dominant_emotion in self.voice_settings:
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
        if not self.initialization_status["is_initialized"]:
            logger.warning("Agent not fully initialized, cannot send voice settings.")
            return

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
                    logger.info("Voice settings successfully sent to StreamingTTSAgent")
                else:
                    logger.warning(f"StreamingTTSAgent reported error: {response.get('message')}")
            else:
                # Socket timed out
                logger.warning("Timeout waiting for response from StreamingTTSAgent")
                
        except Exception as e:
            logger.error(f"Error sending voice settings to StreamingTTSAgent: {e}")
    
    def _get_health_status(self):
        # Default health status: Agent is running if its main loop is active.
        # This can be expanded with more specific checks later.
        status = "HEALTHY" if self.running else "UNHEALTHY"
        details = {
            "status_message": "Agent is operational.",
            "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else 0
        }
        return {"status": status, "details": details}
    
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
            return self._get_health_status()
        
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
        # TODO-FIXME – removed stray 'self.' (O3 Pro Max fix)
        self.emotion_sub_
        self.tts_
        # TODO-FIXME – removed stray 'self.' (O3 Pro Max fix)
        logger.info("EmpathyAgent stopped")


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
    # Standardized main execution block
    agent = None
    try:
        # Replace 'ClassName' with the actual agent class from the file.
        agent = EmpathyAgent()
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
            
def _perform_initialization(self):
    """Initialize agent components."""

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
    try:
        # Add your initialization code here
        pass
    except Exception as e:
        logger.error(f"Initialization error: {e}")
        raise

if __name__ == "__main__":
    agent = None
    try:
        agent = EmpathyAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        if agent and hasattr(agent, 'cleanup'):
            agent.cleanup()

    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info(f"{self.__class__.__name__} cleaning up resources...")
        try:
            # Close ZMQ sockets if they exist
            if hasattr(self, 'socket') and self.socket:
                self.socket.close()
            if hasattr(self, 'context') and self.context:
                self.context.term()
            # Close any open file handles
            # [Add specific resource cleanup here]
            
            # Call parent class cleanup if it exists
            super().cleanup()
            
            logger.info(f"{self.__class__.__name__} cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
