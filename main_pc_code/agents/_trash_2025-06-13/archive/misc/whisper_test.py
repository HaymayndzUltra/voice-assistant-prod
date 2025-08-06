"""
Whisper Test - Test if Whisper model loading is working
"""

import sys
import time
import logging
from common.utils.log_setup import configure_logging

# Set up basic logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WhisperTest")

print("=== Whisper Model Loading Test ===")

# Try to import whisper
try:
    print("Attempting to import whisper module...")
    import whisper
    print("Successfully imported whisper module")
except ImportError as e:
    print(f"Failed to import whisper: {e}")
    print("Please install it with 'pip install openai-whisper'")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error importing whisper: {e}")
    sys.exit(1)

# Try to load the model
try:
    print("Attempting to load Whisper 'base' model...")
    print("This may take some time if the model needs to be downloaded...")
    
    start_time = time.time()
    model = whisper.load_model("base")
    end_time = time.time()
    
    print(f"Successfully loaded Whisper 'base' model in {end_time - start_time:.2f} seconds")
    print(f"Model type: {type(model)}")
    
    # Try a simple transcription
    print("\nTesting transcription with a dummy audio array...")
    import numpy as np
    
    # Create a dummy audio array (1 second of silence)
    dummy_audio = np.zeros(16000, dtype=np.float32)
    
    # Try to transcribe
    result = model.transcribe(dummy_audio)
    print(f"Transcription result: {result['text']}")
    
    print("\nWhisper model test completed successfully!")
    
except Exception as e:
    print(f"Error loading or using Whisper model: {e}")
    print("Whisper model test failed.")
    sys.exit(1)

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
