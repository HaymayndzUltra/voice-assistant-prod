"""
Sounddevice Configuration Module
Sets the correct sounddevice settings for all modules in the Voice Assistant system
"""
import sounddevice as sd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SoundDeviceConfig")

# Correct device settings based on working microphone
DEVICE_INDEX = 1  # SteelSeries Sonar - Microphone
SAMPLE_RATE = 44100  # Correct sample rate

def configure_sounddevice():
    """Apply sounddevice configuration globally"""
    try:
        # Set the default input device
        sd.default.device = DEVICE_INDEX, None  # Set input device only, leave output device as default
        
        # Log success
        logger.info(f"Configured sounddevice to use input device {DEVICE_INDEX} at {SAMPLE_RATE} Hz")
        default_device_info = sd.query_devices(DEVICE_INDEX)
        logger.info(f"Default device: {default_device_info['name']}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to configure sounddevice: {e}")
        return False

# Configure sounddevice automatically when this module is imported
success = configure_sounddevice()
if not success:
    logger.warning("Failed to configure sounddevice automatically. Manual configuration may be required.")

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
