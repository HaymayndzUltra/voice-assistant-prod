from src.core.base_agent import BaseAgent
"""
Voice Controller
--------------
Combines wake word detection and speech processing:
- Manages wake word detection
- Handles speech recognition
- Coordinates between components
"""

import logging
import time
from typing import Optional, Callable, Dict, Any
from .wake_word_detector import WakeWordDetector
from .speech_processor import SpeechProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('voice_controller.log'),
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
