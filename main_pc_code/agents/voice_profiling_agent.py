# ✅ Path patch fix for src/ and utils/ imports
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.base_agent import BaseAgent
"""
Voice Profiling Agent
Handles voice enrollment, speaker recognition, and voice profile management.
"""

import json
import uuid
import numpy as np
import zmq
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from utils.config_loader import parse_agent_args
_agent_args = parse_agent_args()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('VoiceProfilingAgent')

class VoiceProfilingAgent(BaseAgent):
    def __init__(self):
        self.port = _agent_args.get('port')
        super().__init__(_agent_args)
        """Initialize the Voice Profiling Agent"""
        # Load configuration – determine config_path safely to avoid NameError
        config_path = _agent_args.get('config_path', getattr(_agent_args, 'config_path', None))
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "..", "config", "system_config.py")
        self.config_path = config_path
        self.load_config()
        
        # Initialize voice profiles storage
        self.profile_storage_path = self.config["voice_profiling"]["profile_storage_path"]
        os.makedirs(self.profile_storage_path, exist_ok=True)
        
        # Load existing voice profiles
        self.voice_profiles = {}
        self.load_voice_profiles()
        
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
                    'profile_storage_path': 'data/voice_profiles',
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
                    'profile_storage_path': 'data/voice_profiles',
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
            # Verify minimum number of samples
            if len(audio_samples_list) < self.config["voice_profiling"]["min_enrollment_samples"]:
                logger.warning(f"Insufficient samples for enrollment. Required: {self.config['voice_profiling']['min_enrollment_samples']}, Got: {len(audio_samples_list)}")
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
                
            # TODO: Implement actual speaker identification using model
            # For now, return placeholder results
            confidence_threshold = self.config["voice_profiling"]["recognition_confidence_threshold"]
            
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
                if (self.config["voice_learning_and_adaptation"]["enable_continuous_learning"] and 
                    self.config["voice_learning_and_adaptation"]["update_profile_on_high_confidence_match"]):
                    self.update_voice_profile(best_match, audio_data)
                    
                # Handle task memory linking if enabled
                if self.config["interaction_memory_link"]["link_to_task_memory_user_id"]:
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
            
    def handle_request(self, request: Dict) -> Dict:
        """Handle incoming requests."""
        request_type = request.get('request_type')
        
        if request_type == 'ENROLL_SPEAKER':
            user_id = request.get('user_id')
            audio_samples = request.get('audio_samples')
            success = self.enroll_new_speaker(user_id, audio_samples)
            return {
                'status': 'success' if success else 'error',
                'message': 'Speaker enrolled successfully' if success else 'Failed to enroll speaker'
            }
            
        elif request_type == 'IDENTIFY_SPEAKER':
            audio_data = request.get('audio_data')
            user_id, confidence = self.identify_speaker(audio_data)
            return {
                'status': 'success',
                'user_id': user_id,
                'confidence': confidence
            }
        else:
            return super().handle_request(request)
    
    def shutdown(self):
        """Gracefully shutdown the agent"""
        logger.info("Shutting down Voice Profiling Agent")
        super().stop()

    def _get_health_status(self):
        """Overrides the base method to add agent-specific health metrics."""
        base_status = super()._get_health_status()
        specific_metrics = {
            "profiler_status": "active",
            "profiles_processed": getattr(self, 'profiles_processed', 0),
            "last_profile_time": getattr(self, 'last_profile_time', 'N/A')
        }
        base_status.update(specific_metrics)
        return base_status


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

if __name__ == "__main__":
    import argparse
import time
import psutil
from datetime import datetime
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5708)
    args = parser.parse_args()
    agent = VoiceProfilingAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("Shutting down Voice Profiling Agent")
    finally:
        agent.shutdown()