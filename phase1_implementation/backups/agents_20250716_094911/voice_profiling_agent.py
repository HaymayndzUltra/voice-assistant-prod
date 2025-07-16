"""
Voice Profiling Agent
Handles voice enrollment, speaker recognition, and voice profile management.
"""

import sys
import os
import json
import uuid
import numpy as np
import zmq
import logging
import time
import psutil
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union, cast
from pathlib import Path
from main_pc_code.utils.config_loader import load_config
from common.core.base_agent import BaseAgent


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", "..")))
from common.utils.path_env import get_path, join_path, get_file_path
config = load_config()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('VoiceProfilingAgent')

class VoiceProfilingAgent(BaseAgent):
    def __init__(self):
        """Initialize the Voice Profiling Agent"""
        # Get configuration
        config_dict = load_config()
        
        # Initialize basic parameters
        agent_name = config_dict.get('name', 'VoiceProfilingAgent')
        agent_port = int(config_dict.get('port', 5600))
        
        # Call BaseAgent's __init__
        super().__init__(name=agent_name, port=agent_port)
        
        # Store configuration
        self.config = config_dict
        
        # Initialize running state
        self.running = True
        self.start_time = time.time()
        
        # Load configuration – determine config_path safely to avoid NameError
        config_path = self.config.get('config_path', None)
        if config_path is None:
            config_path = join_path("config", join_path("config", "system_config.py"))
        self.config_path = config_path
        self.load_config()
        
        # Initialize voice profiles storage
        self.profile_storage_path = self.config.get("voice_profiling", {}).get("profile_storage_path", join_path("data", "voice_profiles"))
        os.makedirs(self.profile_storage_path, exist_ok=True)
        
        # Load existing voice profiles
        self.voice_profiles = {}
        self.load_voice_profiles()
        
        # Setup error bus
        self.error_bus_port = int(config_dict.get("error_bus_port", 7150))
        self.error_bus_host = os.environ.get('PC2_IP', config_dict.get("pc2_ip", "127.0.0.1"))
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)
        
        logger.info(f"Voice Profiling Agent initialized on port {self.port}")
        
    def load_config(self):
        """Load voice personalization configuration"""
        try:
            # Attempt to import from python module
            import importlib.util, sys
            sys.path.append(os.path.dirname(self.config_path))
            spec = importlib.util.spec_from_file_location("system_config", self.config_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, 'voice_personalization_config'):
                    self.config = module.voice_personalization_config
                    logger.info("Loaded voice personalization configuration from python module")
                    return
        except Exception as e:
            logger.warning(f"Python config import failed: {e}")

        # Fallback: load JSON system_config.json and extract sections, otherwise defaults
        try:
            json_path = os.path.join(os.path.dirname(self.config_path), 'system_config.json')
            with open(json_path, 'r', encoding='utf-8-sig') as f:
                json_cfg = json.load(f)
            self.config = {
                'voice_profiling': json_cfg.get('voice_profiling', {
                    'profile_storage_path': join_path("data", "voice_profiles"),
                    'min_enrollment_samples': 3,
                    'recognition_confidence_threshold': 0.8
                }),
                'voice_learning_and_adaptation': json_cfg.get('voice_learning_and_adaptation', {
                    'enable_continuous_learning': True
                })
            }
            logger.info("Loaded voice profiling configuration from JSON fallback")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Final fallback defaults
            self.config = {
                'voice_profiling': {
                    'profile_storage_path': join_path("data", "voice_profiles"),
                    'min_enrollment_samples': 3,
                    'recognition_confidence_threshold': 0.8
                },
                'voice_learning_and_adaptation': {
                    'enable_continuous_learning': True
                }
            }
            logger.warning("Using default voice profiling configuration")
            
    def load_voice_profiles(self):
        """Load existing voice profiles from storage"""
        try:
            for profile_file in os.listdir(self.profile_storage_path):
                if profile_file.endswith('.json'):
                    with open(os.path.join(self.profile_storage_path, profile_file), 'r') as f:
                        profile = json.load(f)
                        self.voice_profiles[profile['user_id']] = profile
            logger.info(f"Loaded {len(self.voice_profiles)} voice profiles")
        except Exception as e:
            logger.error(f"Failed to load voice profiles: {e}")
            
    def save_voice_profile(self, user_id: str, profile_data: Dict[str, Any]):
        """Save a voice profile to storage"""
        try:
            profile_path = os.path.join(self.profile_storage_path, f"{user_id}.json")
            with open(profile_path, 'w') as f:
                json.dump(profile_data, f, indent=4)
            logger.info(f"Saved voice profile for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to save voice profile: {e}")
            raise
            
    def enroll_new_speaker(self, user_id: str, audio_samples_list: List[np.ndarray]) -> bool:
        """
        Enroll a new speaker using provided audio samples
        
        Args:
            user_id: Unique identifier for the speaker
            audio_samples_list: List of audio samples (numpy arrays) for enrollment
            
        Returns:
            bool: True if enrollment successful, False otherwise
        """
        try:
            # Get config value with safe access
            min_samples = self.config.get("voice_profiling", {}).get("min_enrollment_samples", 3)
            
            # Verify minimum number of samples
            if len(audio_samples_list) < min_samples:
                logger.warning(f"Insufficient samples for enrollment. Required: {min_samples}, Got: {len(audio_samples_list)}")
                return False
                
            # TODO: Implement actual voice feature extraction using speaker recognition model
            # For now, create a placeholder profile
            profile_data = {
                "user_id": user_id,
                "enrollment_date": datetime.now().isoformat(),
                "audio_samples_count": len(audio_samples_list),
                "voice_features": "PLACEHOLDER_FEATURES",  # Replace with actual extracted features
                "metadata": {
                    "sample_rate": 16000,  # Assuming standard sample rate
                    "channels": 1,
                    "duration_per_sample": 3.0  # Assuming 3-second samples
                }
            }
            
            # Save profile
            self.voice_profiles[user_id] = profile_data
            self.save_voice_profile(user_id, profile_data)
            
            logger.info(f"Successfully enrolled new speaker: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enroll new speaker: {e}")
            return False
            
    def identify_speaker(self, audio_data: np.ndarray) -> Tuple[Optional[str], float]:
        """
        Identify speaker from audio data
        
        Args:
            audio_data: Audio sample as numpy array
            
        Returns:
            Tuple[Optional[str], float]: (user_id, confidence_score) or (None, 0.0) if no match
        """
        try:
            if not self.voice_profiles:
                logger.warning("No voice profiles available for identification")
                return None, 0.0
                
            # Get config value with safe access
            confidence_threshold = self.config.get("voice_profiling", {}).get("recognition_confidence_threshold", 0.8)
            
            # Simulate identification (replace with actual model inference)
            best_match = None
            best_confidence = 0.0
            
            for user_id, profile in self.voice_profiles.items():
                # Simulate confidence score (replace with actual model output)
                confidence = 0.85  # Placeholder confidence score
                
                if confidence > best_confidence:
                    best_match = user_id
                    best_confidence = confidence
                    
            if best_confidence >= confidence_threshold:
                # Handle continuous learning if enabled
                enable_learning = self.config.get("voice_learning_and_adaptation", {}).get("enable_continuous_learning", False)
                update_profile = self.config.get("voice_learning_and_adaptation", {}).get("update_profile_on_high_confidence_match", False)
                
                # Only update profile if we have a valid user_id
                if enable_learning and update_profile and best_match is not None:
                    self.update_voice_profile(best_match, audio_data)
                    
                # Handle task memory linking if enabled
                if self.config.get("interaction_memory_link", {}).get("link_to_task_memory_user_id", False):
                    logger.info(f"User {best_match} identified. Link to Task Memory.")
                    
                return best_match, best_confidence
                
            return None, 0.0
            
        except Exception as e:
            logger.error(f"Failed to identify speaker: {e}")
            return None, 0.0
            
    def update_voice_profile(self, user_id: str, new_audio_sample: np.ndarray):
        """
        Update voice profile with new audio sample (continuous learning)
        
        Args:
            user_id: User ID to update
            new_audio_sample: New audio sample for profile update
        """
        try:
            if user_id not in self.voice_profiles:
                logger.warning(f"Cannot update non-existent profile for user {user_id}")
                return
                
            # TODO: Implement actual profile update logic
            # For now, just log the update
            logger.info(f"Updating voice profile for user {user_id} with new sample")
            
        except Exception as e:
            logger.error(f"Failed to update voice profile: {e}")
            
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        request_type = request.get('request_type')
        
        if request_type == 'ENROLL_SPEAKER':
            user_id = request.get('user_id')
            audio_samples = request.get('audio_samples')
            
            # Type checking
            if not isinstance(user_id, str):
                return {'status': 'error', 'message': 'Invalid user_id, must be a string'}
            
            if not isinstance(audio_samples, list):
                return {'status': 'error', 'message': 'Invalid audio_samples, must be a list'}
            
            # Convert to correct type for the function call
            success = self.enroll_new_speaker(user_id, audio_samples)
            return {
                'status': 'success' if success else 'error',
                'message': 'Speaker enrolled successfully' if success else 'Failed to enroll speaker'
            }
            
        elif request_type == 'IDENTIFY_SPEAKER':
            audio_data = request.get('audio_data')
            
            # Type checking
            if audio_data is None:
                return {'status': 'error', 'message': 'Missing audio_data'}
            
            # Convert to numpy array if needed
            if not isinstance(audio_data, np.ndarray):
                try:
                    audio_data = np.array(audio_data)
                except:
                    return {'status': 'error', 'message': 'Invalid audio_data format'}
            
            user_id, confidence = self.identify_speaker(audio_data)
            return {
                'status': 'success',
                'user_id': user_id,
                'confidence': confidence
            }
        else:
            return super().handle_request(request)
    
    def run(self):
        """Run the main agent loop."""
        logger.info("Starting VoiceProfilingAgent main loop")
        
        # Call parent's run method to ensure health check thread works
        super().run()
        
        # Main agent loop
        while self.running:
            try:
                # Process requests
                # ... agent-specific processing logic ...
                time.sleep(0.1)  # Prevent tight loop
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
    
    def cleanup(self):
        """Clean up resources when the agent is stopping."""
        logger.info("Cleaning up resources...")
        
        # Set running flag to False to stop threads
        self.running = False
        
        try:
            # Close all ZMQ sockets
            for socket_name in ['socket', 'error_bus_pub']:
                if hasattr(self, socket_name) and getattr(self, socket_name):
                    try:
                        getattr(self, socket_name).close()
                        logger.info(f"{socket_name} closed")
                    except Exception as e:
                        logger.error(f"Error closing {socket_name}: {e}")
            
            # Terminate ZMQ context
            if hasattr(self, 'context') and self.context:
                try:
                    self.context.term()
                    logger.info("ZMQ context terminated")
                except Exception as e:
                    logger.error(f"Error terminating ZMQ context: {e}")
            
            # Save any pending voice profile updates
            for user_id, profile in self.voice_profiles.items():
                try:
                    self.save_voice_profile(user_id, profile)
                except Exception as e:
                    logger.error(f"Error saving voice profile for {user_id}: {e}")
            
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        # Call parent cleanup method
        super().cleanup()

    def _get_health_status(self) -> Dict[str, Any]:
        """Overrides the base method to add agent-specific health metrics."""
        return {
            'status': 'ok',
            'ready': True,
            'initialized': True,
            'service': 'voice_profiler',
            'components': {
                'profiles_loaded': len(self.voice_profiles) > 0
            },
            'profiles_count': len(self.voice_profiles),
            'profiles_processed': getattr(self, 'profiles_processed', 0),
            'last_profile_time': getattr(self, 'last_profile_time', 'N/A'),
            'uptime': time.time() - self.start_time
        }

    def health_check(self):
        """Performs a health check on the agent, returning a dictionary with its status."""
        try:
            # Basic health check logic
            is_healthy = self.running  # Assume healthy if running
            
            # Check if the voice profiles are loaded
            if not hasattr(self, 'voice_profiles') or not isinstance(self.voice_profiles, dict):
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
                    "voice_profiles_count": len(self.voice_profiles),
                    "profile_storage_path": self.profile_storage_path,
                    "enable_continuous_learning": self.config.get("voice_learning_and_adaptation", {}).get("enable_continuous_learning", False)
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

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = VoiceProfilingAgent()
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