"""
MoodTrackerAgent
Tracks and analyzes user mood over time based on emotional state updates
"""
from common.utils.path_manager import PathManager

# Removed import sys
import os

import sys
import os
import logging
import threading
import time
import psutil
from datetime import datetime
from collections import deque
from typing import Dict, Any, List, Optional
from common.config_manager import load_unified_config
from common.core.base_agent import BaseAgent
from common.utils.env_standardizer import get_env
from main_pc_code.agents.error_publisher import ErrorPublisher

config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))

# Configure logging using canonical approach
from common.utils.log_setup import configure_logging
logger = configure_logging(__name__, log_to_file=True)

class MoodTrackerAgent(BaseAgent):
    def __init__(self):
        """Initialize the MoodTrackerAgent (refactored for compliance)."""
        # Standard BaseAgent initialization at the beginning
        config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))
        self.config = config
        super().__init__(
            name=config.get('name', 'MoodTrackerAgent'),
            port=int(config.get('port', 5580))
        )
        
        # All config values are loaded from config
        self.emotion_engine_port = int(config.get('emotionengine_port', 5592))
        self.history_size = int(config.get('history_size', 100))
        
        # Initialize running state
        self.running = True
        self.start_time = time.time()
        
        # SUB socket for subscribing to EmotionEngine broadcasts
        self.emotion_sub_socket = self.context.socket(zmq.SUB)
        _host = config.get('host', os.environ.get('HOST', '127.0.0.1'))
        self.emotion_sub_socket.connect(f"tcp://{_host}:{self.emotion_engine_port}")
        self.emotion_sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all messages
        
        # Initialize poller for non-blocking socket operations
        self.poller = zmq.Poller()
        self.poller.register(self.emotion_sub_socket, zmq.POLLIN)
        
        # Current mood state
        self.current_mood = {
            'emotion': 'neutral',
            'intensity': 0.5,
            'sentiment': 0.0,
            'confidence': 0.0,
            'timestamp': time.time()
        }
        
        # Mood history using deque with fixed size
        self.mood_history = deque(maxlen=self.history_size)
        
        # Emotion mapping (user emotion to AI response emotion)
        self.emotion_mapping = {
            'happy': 'happy',
            'sad': 'empathetic',
            'angry': 'calm',
            'fearful': 'calm',
            'surprised': 'curious',
            'disgusted': 'concerned',
            'neutral': 'neutral',
            'frustrated': 'helpful'
        }
        
        # Modern error reporting now handled by BaseAgent's UnifiedErrorHandler
        
        # Start monitoring threads
        self.emotion_thread = threading.Thread(target=self._monitor_emotions)
        self.emotion_thread.daemon = True
        self.emotion_thread.start()
        
        logger.info(f"MoodTrackerAgent initialized on port {self.port}")
        logger.info(f"Subscribed to EmotionEngine on port {self.emotion_engine_port}")
        logger.info(f"Mood history size: {self.history_size}")
    
    def _monitor_emotions(self):
        """Monitor emotional state updates from EmotionEngine."""
        logger.info("Starting emotion monitoring thread")
        while self.running:
            try:
                # Check for emotion updates with a timeout
                socks = dict(self.poller.poll(1000))  # 1 second timeout
                
                if self.emotion_sub_socket in socks and socks[self.emotion_sub_socket] == zmq.POLLIN:
                    message = self.emotion_sub_socket.recv_json()
                    
                    # Check if this is an emotional state update
                    if isinstance(message, dict) and message.get('type') == 'emotional_state_update':
                        emotional_state = message.get('data', {})
                        if isinstance(emotional_state, dict):
                            self._update_mood(emotional_state)
                        else:
                            logger.warning(f"Received invalid emotional state data (not a dict): {emotional_state}")
                
            except Exception as e:
                logger.error(f"Error in emotion monitoring thread: {e}")
                time.sleep(1)  # Sleep to avoid tight loop in case of error
    
    def _update_mood(self, emotional_state: Dict[str, Any]):
        """Update the current mood based on emotional state.
        
        Args:
            emotional_state: Emotional state from EmotionEngine
        """
        try:
            # Extract data from emotional state
            dominant_emotion = emotional_state.get('dominant_emotion', 'neutral')
            combined_emotion = emotional_state.get('combined_emotion', dominant_emotion)
            intensity = emotional_state.get('intensity', 0.5)
            sentiment = emotional_state.get('sentiment', 0.0)
            
            # Map user emotion to AI response emotion
            mapped_emotion = self.emotion_mapping.get(dominant_emotion, 'neutral')
            
            # Update current mood
            self.current_mood = {
                'user_emotion': dominant_emotion,
                'user_combined_emotion': combined_emotion,
                'mapped_emotion': mapped_emotion,
                'intensity': intensity,
                'sentiment': sentiment,
                'confidence': emotional_state.get('confidence', 0.8),  # Default high confidence since coming from EmotionEngine
                'timestamp': time.time()
            }
            
            # Add to history
            self.mood_history.append(self.current_mood.copy())
            
            logger.debug(f"Updated mood: {self.current_mood}")
            
        except Exception as e:
            logger.error(f"Error updating mood: {str(e)}")
    
    def _handle_queries(self):
        """Handle mood queries from other agents"""
        logger.info("Starting query handling thread")
        while self.running:
            try:
                # Wait for next request with timeout
                socks = dict(self.poller.poll(1000))  # 1 second timeout
                if self.socket in socks and socks[self.socket] == zmq.POLLIN:
                    message = self.socket.recv_json()
                    logger.debug(f"Received query: {message}")
                    
                    # Process request
                    if isinstance(message, dict):
                        response = self._process_request(message)
                    else:
                        response = {'status': 'error', 'message': 'Invalid request format, expected a dictionary'}
                    
                    # Send response
                    self.socket.send_json(response)
                    logger.debug(f"Sent response: {response}")
                
            except Exception as e:
                logger.error(f"Error handling query: {str(e)}")
                try:
                    self.socket.send_json({
                        'status': 'error',
                        'message': str(e)
                    })
                except zmq.error.ZMQError as zmq_err:
                    logger.error(f"ZMQ error sending response: {zmq_err}")
                time.sleep(0.1)  # Small sleep to avoid tight loop
    
    def _process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming requests.
        
        Args:
            request: Request dictionary
            
        Returns:
            Response dictionary
        """
        action = request.get('action')
        
        if action == 'ping':
            return {'status': 'success', 'message': 'pong'}
            
        elif action == 'get_health':
            return self._get_health_status()
            
        elif action == 'get_current_mood':
            return {
                'status': 'success',
                'mood': self.current_mood
            }
            
        elif action == 'get_mood_history':
            limit = request.get('limit')
            return {
                'status': 'success',
                'history': self.get_mood_history(limit)
            }
            
        elif action == 'get_long_term_mood':
            time_window = request.get('time_window')  # In seconds
            return {
                'status': 'success',
                'long_term_mood': self.get_long_term_mood(time_window)
            }
            
        else:
            return {
                'status': 'error',
                'message': f'Unknown action: {action}'
            }
    
    def get_current_mood(self) -> Dict[str, Any]:
        """Get the current mood state.
        
        Returns:
            Current mood state
        """
        return self.current_mood
    
    def get_mood_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get the mood history.
        
        Args:
            limit: Maximum number of history items to return (None for all)
            
        Returns:
            List of mood states
        """
        history = list(self.mood_history)
        if limit and limit > 0:
            history = history[-limit:]
        return history
    
    def get_long_term_mood(self, time_window: Optional[float] = None) -> Dict[str, Any]:
        """Analyze mood history to determine long-term mood.
        
        Args:
            time_window: Time window in seconds to consider (None for all history)
            
        Returns:
            Dictionary with long-term mood analysis
        """
        try:
            # Filter history by time window if specified
            current_time = time.time()
            if time_window and time_window > 0:
                cutoff_time = current_time - time_window
                filtered_history = [
                    mood for mood in self.mood_history 
                    if mood.get('timestamp', 0) >= cutoff_time
                ]
            else:
                filtered_history = list(self.mood_history)
            
            # If no history, return neutral mood
            if not filtered_history:
                return {
                    'dominant_emotion': 'neutral',
                    'average_sentiment': 0.0,
                    'average_intensity': 0.5,
                    'emotion_counts': {'neutral': 1},
                    'mood_stability': 1.0,
                    'time_window': time_window,
                    'sample_size': 0
                }
            
            # Count emotions
            emotion_counts = {}
            for mood in filtered_history:
                emotion = mood.get('user_emotion', 'neutral')
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            # Get dominant emotion
            dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]
            
            # Calculate average sentiment and intensity
            sentiments = [mood.get('sentiment', 0.0) for mood in filtered_history]
            intensities = [mood.get('intensity', 0.5) for mood in filtered_history]
            
            average_sentiment = sum(sentiments) / len(sentiments)
            average_intensity = sum(intensities) / len(intensities)
            
            # Calculate mood stability (lower value means more changes)
            if len(filtered_history) > 1:
                emotion_changes = 0
                prev_emotion = filtered_history[0].get('user_emotion')
                for mood in filtered_history[1:]:
                    current_emotion = mood.get('user_emotion')
                    if current_emotion != prev_emotion:
                        emotion_changes += 1
                    prev_emotion = current_emotion
                
                stability = 1.0 - (emotion_changes / (len(filtered_history) - 1))
            else:
                stability = 1.0
            
            return {
                'dominant_emotion': dominant_emotion,
                'average_sentiment': average_sentiment,
                'average_intensity': average_intensity,
                'emotion_counts': emotion_counts,
                'mood_stability': stability,
                'time_window': time_window,
                'sample_size': len(filtered_history)
            }
            
        except Exception as e:
            logger.error(f"Error calculating long-term mood: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'dominant_emotion': 'neutral',
                'average_sentiment': 0.0,
                'average_intensity': 0.5
            }
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Override BaseAgent's health status to include MoodTrackerAgent-specific info."""
        return {
            'status': 'ok',
            'ready': True,
            'initialized': True,
            'service': 'mood_tracker',
            'components': {
                'emotion_monitoring': self.emotion_thread.is_alive(),
                'mood_history': len(self.mood_history) > 0
            },
            'current_mood': self.current_mood,
            'uptime': time.time() - self.start_time
        }
    
    def health_check(self):
        """Performs a health check on the agent, returning a dictionary with its status."""
        try:
            # Basic health check logic
            is_healthy = self.running  # Assume healthy if running
            
            # Check if sockets are initialized and connected
            if not hasattr(self, 'emotion_sub_socket') or not self.emotion_sub_socket:
                is_healthy = False
            if not hasattr(self, 'socket') or not self.socket:
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
                    "current_mood": self.current_mood,
                    "mood_history_size": len(self.mood_history),
                    "most_recent_emotions": [mood.get('user_emotion') for mood in list(self.mood_history)[-3:]] if self.mood_history else []
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
    
    def run(self):
        """Run the main agent loop."""
        logger.info("Starting MoodTrackerAgent main loop")
        
        # Call parent's run method to ensure health check thread works
        super().run()
        
        # Start handling queries
        self._handle_queries()

    def cleanup(self):
        """Gracefully shutdown the agent"""
        logger.info("Shutting down MoodTrackerAgent")
        self.running = False
        time.sleep(0.5)  # Give threads time to exit
        
        self.emotion_sub_
        # Use BaseAgent's cleanup method
        super().cleanup()
        logger.info("MoodTrackerAgent shutdown complete")

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = MoodTrackerAgent()
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