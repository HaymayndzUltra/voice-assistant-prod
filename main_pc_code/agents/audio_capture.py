from main_pc_code.src.core.base_agent import BaseAgent
"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

Audio Capture Module
Captures audio from microphone and saves as WAV files
"""

import os
import sys
import time
import json
import logging
import numpy as np
import sounddevice as sd
import soundfile as sf
import zmq
from datetime import datetime
from session_utils import new_session_id, DeduplicationCache

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AudioCapture")

# Constants
DEVICE_INDEX = 1  # SteelSeries Sonar - Microphone (confirmed working device)
SAMPLE_RATE = 44100  # Device's native sample rate
CHANNELS = 1
RECORD_SECONDS = 5  # Record for 5 seconds at a time
RMS_THRESHOLD = 0.01  # Threshold for silence detection

# Create logs directory if it doesn't exist
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# ZMQ Configuration
ZMQ_PUB_PORT = 5556  # Different from listener.py to avoid conflicts

# Deduplication setup
DEDUP_TTL = 30  # seconds
_dedup_cache = DeduplicationCache(ttl=DEDUP_TTL)

class AudioCaptureModule(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AudioCapture")
        """Initialize the audio capture module"""
        logger.info("Initializing Audio Capture Module")
        self.device_index = device_index
        
        # Initialize ZMQ
        logger.info("Setting up ZMQ publisher")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        
        try:
            self.socket.bind(f"tcp://*:{ZMQ_PUB_PORT}")
            logger.info(f"ZMQ publisher bound to port {ZMQ_PUB_PORT}")
        except Exception as e:
            logger.error(f"Error binding ZMQ socket: {e}")
            sys.exit(1)
        
        # Get device info
        try:
            device_info = sd.query_devices(device_index)
            logger.info(f"Using audio device: {device_info['name']} (Index: {device_index})")
            logger.info(f"Device details: {device_info['max_input_channels']} channels, {device_info['default_samplerate']}Hz")
        except Exception as e:
            logger.error(f"Error getting device info: {e}")
            sys.exit(1)
    
    def record_audio(self):
        """Record audio from the microphone and save as WAV file"""
        try:
            session_id = new_session_id()
            logger.info(f"[Session] Starting new recording session: {session_id}")
            logger.info(f"Recording {RECORD_SECONDS} seconds of audio...")
            
            # Record audio
            recording = sd.rec(
                int(RECORD_SECONDS * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype='float32',
                device=self.device_index,
                blocking=True
            )
            logger.info("Recording finished")
            # Calculate audio stats
            rms = np.sqrt(np.mean(recording**2))

            # Deduplication check
            chunk_bytes = recording.tobytes()
            if _dedup_cache.is_duplicate(chunk_bytes):
                logger.info(f"[Dedup] Duplicate chunk detected, skipping session {session_id}")
                return None
            chunk_hash = _dedup_cache.add(chunk_bytes, session_id)
            _dedup_cache.cleanup()
            logger.info(f"Audio stats: RMS={rms:.4f}")
            
            if rms < RMS_THRESHOLD:
                logger.info("Audio is mostly silence, skipping")
                return None
            
            # Save the recorded audio as a WAV file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(LOG_DIR, f"audio_{timestamp}.wav")
            
            sf.write(output_file, recording, SAMPLE_RATE)
            logger.info(f"Audio saved to {output_file}")
            
            # Publish message with audio file path, session_id, and chunk_hash
            self.publish_audio_file(output_file, rms, session_id=session_id, chunk_hash=chunk_hash)
            
            return output_file
        
        except Exception as e:
            logger.error(f"Error recording audio: {e}")
            import traceback
import psutil
from datetime import datetime
            traceback.print_exc()
            return None
    
    def publish_audio_file(self, file_path, rms, session_id=None, chunk_hash=None):
        """Publish audio file path to ZMQ with session and dedup info"""
        try:
            # Create message
            message = {
                "type": "audio_file",
                "file_path": file_path,
                "rms": float(rms),
                "sample_rate": SAMPLE_RATE,
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "chunk_hash": chunk_hash
            }
            # Send message
            json_message = json.dumps(message)
            self.socket.send_string(json_message)
            logger.info(f"Published audio file: {file_path} (session={session_id}, hash={chunk_hash})")
            return True
        except Exception as e:
            logger.error(f"Error publishing audio file: {e}")
            return False
    
    def run(self):
        """Manual trigger for audio capture: press Enter to record audio chunk"""
        logger.info("Starting manual audio capture loop (press Enter to record)")
        try:
            while True:
                logger.info("[DEBUG] Waiting for Enter key to trigger audio recording...")
                input("Press Enter to record audio...")
                logger.info("[DEBUG] Manual trigger received, starting audio recording...")
                audio_file = self.record_audio()
                if audio_file:
                    logger.info(f"[DEBUG] Audio file successfully recorded and published: {audio_file}")
                else:
                    logger.info("[DEBUG] No audio file recorded (possibly silence or error)")
                # Sleep a bit to avoid overlapping triggers
                time.sleep(0.2)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt detected, stopping")
        finally:
            logger.info("Cleaning up resources")
            self.socket.close()
            self.context.term()
            logger.info("Audio capture module stopped")


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
    print("=== Audio Capture Module ===")
    print(f"Using device index {DEVICE_INDEX} (SteelSeries Sonar - Microphone)")
    print(f"Publishing to ZMQ port {ZMQ_PUB_PORT}")
    
    # Create and run audio capture module
    module = AudioCaptureModule()
    module.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise