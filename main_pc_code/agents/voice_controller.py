from common.core.base_agent import BaseAgent
from common.utils.path_manager import PathManager
from common.utils.log_setup import configure_logging
"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

Voice Controller
--------------
Combines wake word detection and speech processing:
- Manages wake word detection
- Handles speech recognition
- Coordinates between components
"""

import logging
import time
from typing import Dict, Any
from main_pc_code.agents.wake_word_detector import WakeWordDetector
from main_pc_code.agents.speech_processor import SpeechProcessor
import psutil
from datetime import datetime
from common.utils.path_manager import PathManager

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(PathManager.get_logs_dir() / "voice_controller.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VoiceController(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="VoiceController")
        """
        Initialize the voice controller.
        
        Args:
            on_command: Function to call when a command is detected
        """
        self.on_command = on_command
        
        # Initialize components
        self.wake_word_detector = WakeWordDetector(
            callback=self._on_wake_word
        )
        
        self.speech_processor = SpeechProcessor(
            callback=self._on_speech_processed
        )
        
        logger.info("Voice controller initialized")
    
    def _on_wake_word(self, detection: Dict[str, Any]):
        """Handle wake word detection."""
        try:
            logger.info(f"Wake word detected with confidence {detection['confidence']:.2f}")
            
            # Start listening for speech
            self.speech_processor.start_listening()
            
        except Exception as e:
            logger.error(f"Error handling wake word: {str(e)}")
    
    def _on_speech_processed(self, result: Dict[str, Any]):
        """Handle processed speech."""
        try:
            text = result['text']
            confidence = result['confidence']
            
            logger.info(f"Speech processed: {text} (confidence: {confidence:.2f})")
            
            # Call command handler if provided
            if self.on_command:
                self.on_command(text, confidence)
            
        except Exception as e:
            logger.error(f"Error handling speech: {str(e)}")
    
    def start(self):
        """Start the voice controller."""
        try:
            # Start components
            self.wake_word_detector.start()
            self.speech_processor.start()
            
            logger.info("Voice controller started")
            
        except Exception as e:
            logger.error(f"Error starting voice controller: {str(e)}")
            self.stop()
            raise
    
    def stop(self):
        """Stop the voice controller."""
        try:
            # Stop components
            self.wake_word_detector.stop()
            self.speech_processor.stop()
            
            logger.info("Voice controller stopped")
            
        except Exception as e:
            logger.error(f"Error stopping voice controller: {str(e)}")
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


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
    # Example usage
    def on_command(text: str, confidence: float):
        print(f"\nCommand detected: {text}")
        print(f"Confidence: {confidence:.2f}")
    
    controller = VoiceController(on_command=on_command)
    
    try:
        controller.start()
        print("Voice controller running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping voice controller...")
    finally:
        controller.stop() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise