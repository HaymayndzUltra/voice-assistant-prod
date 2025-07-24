from main_pc_code.src.core.base_agent import BaseAgent
"""
Integrated Listener - Combines working components from our tests
"""

import os
import sys
import time
import json
import logging
import numpy as np
import sounddevice as sd
import zmq
from datetime import datetime


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("main_pc_code", ".."))))
from common.utils.path_manager import PathManager
# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("IntegratedListener")

# Constants
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 100  # Lowered threshold to detect softer speech
SILENCE_TIMEOUT = 30
RECORD_SECONDS = 5
DEBUG_AUDIO = True  # Print debug info for audio

# Create logs directory if it doesn't exist
LOG_DIR = get_path("logs")
os.makedirs(LOG_DIR, exist_ok=True)

# ZMQ Configuration
ZMQ_PUB_PORT = 5557

# Device selection
DEVICE_INDEX = 4  # SteelSeries Sonar - Microphone (MME API)
print(f"Using device index: {DEVICE_INDEX} (SteelSeries Sonar - Microphone via MME API)")

# Try to import whisper
try:
    print("Importing whisper module...")
    import whisper
    print("Successfully imported whisper module")
except ImportError:
    print("Failed to import whisper. Please install it with 'pip install openai-whisper'")
    sys.exit(1)

# Try to import googletrans
try:
    print("Importing googletrans module...")
    from googletrans import Translator
    print("Successfully imported googletrans module")
    translator = Translator()
except ImportError:
    print("WARNING: googletrans not installed, translation will be skipped.")
    translator = None

# Get device info
try:
    device_info = sd.query_devices(DEVICE_INDEX)
    print(f"Device info: {json.dumps(device_info, indent=2)}")
    
    if device_info['max_input_channels'] <= 0:
        print(f"WARNING: Device {DEVICE_INDEX} has no input channels! Please check selection.")
        sys.exit(1)
    else:
        print(f"Using Device: {DEVICE_INDEX} - {device_info['name']} (Input Channels: {device_info['max_input_channels']}, Default SR: {device_info['default_samplerate']})")
except Exception as e:
    print(f"Error getting device info: {e}")
    sys.exit(1)

class IntegratedListenerAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ListenerNew")
        print(f"Initializing IntegratedListenerAgent with device_index={device_index}")
        self.language = language
        self.model_size = model_size
        self.device_index = device_index
        
        # Initialize ZMQ
        print("Setting up ZMQ socket")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        
        try:
            print(f"Binding socket to tcp://*:{ZMQ_PUB_PORT}")
            self.socket.bind(f"tcp://*:{ZMQ_PUB_PORT}")
            print(f"[ZMQ] Publisher socket bound to tcp://*:{ZMQ_PUB_PORT}")
        except Exception as e:
            print(f"Error binding socket: {e}")
            sys.exit(1)
        
        # Load Whisper model
        print(f"Loading Whisper model '{model_size}'")
        try:
            print("Initializing Whisper model...")
            self.model = whisper.load_model(model_size)
            print(f"Whisper model '{model_size}' loaded successfully")
        except Exception as e:
            print(f"Error loading Whisper model: {e}")
            sys.exit(1)
    
    def transcribe_audio(self, audio_data):
        """Transcribe audio using Whisper model"""
        print("Starting transcription")
        try:
            # Convert audio to float32 if needed
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32) / 32768.0
            
            # Transcribe with Whisper
            print("Running Whisper inference")
            result = self.model.transcribe(audio_data, language=self.language)
            transcription = result["text"].strip()
            print(f"Transcription result: '{transcription}'")
            
            # Translate if needed and translator is available
            if self.language != "en" and translator:
                print(f"Translating from {self.language} to English")
                try:
                    translation = translator.translate(transcription, src=self.language, dest='en')
                    translated_text = translation.text
                    print(f"Translation result: '{translated_text}'")
                    return transcription, translated_text
                except Exception as e:
                    print(f"Translation error: {e}")
                    return transcription, None
            
            return transcription, None
        
        except Exception as e:
            print(f"Transcription error: {e}")
            return None, None

    def handle_transcription(self, transcription, translation=None):
        """Process and publish transcription results"""
        print(f"Handling transcription: '{transcription}'")
        
        if not transcription:
            print("Empty transcription, nothing to handle")
            return
        
        # Prepare message
        message = {
            "type": "transcription",
            "text": transcription,
            "language": self.language,
            "timestamp": datetime.now().isoformat()
        }
        
        if translation:
            message["translation"] = translation
            print(f"Added translation: '{translation}'")
        
        # Publish via ZMQ
        try:
            print(f"Publishing message to ZMQ: {json.dumps(message)}")
            self.socket.send_string(json.dumps(message))
            print(f"[ZMQ] Published: {message['text'][:30]}...")
        except Exception as e:
            print(f"Error publishing to ZMQ: {e}")
    
    def run(self):
        """Main listening loop"""
        print("Starting main listening loop")
        
        try:
            # Get device info
            device_info = sd.query_devices(self.device_index)
            samplerate = int(device_info["default_samplerate"])
            channels = min(1, device_info["max_input_channels"])
            
            # Calculate frames per buffer (100ms chunks)
            frames_per_buffer = int(samplerate * 0.1)
            
            # Open audio stream
            print("Opening audio stream")
            stream = sd.InputStream(
                samplerate=samplerate,
                device=self.device_index,
                channels=channels,
                callback=None,
                blocksize=frames_per_buffer
            )
            
            print("Audio stream created, starting stream")
            stream.start()
            print(f"Listener Agent started. Mode: speech, Device: {self.device_index}")
            
            # Variables for audio processing
            audio_buffer = []
            is_speech = False
            speech_timeout = 0
            
            print("Entering main loop")
            while True:
                # Read audio data
                try:
                    audio_data, overflowed = stream.read(frames_per_buffer)
                    if overflowed:
                        print("WARNING: Audio buffer overflow")
                    
                    # Convert to mono and calculate RMS
                    audio_mono = audio_data.mean(axis=1) if audio_data.ndim > 1 else audio_data
                    rms = np.sqrt(np.mean(audio_mono**2)) * 32768  # Scale to int16 range
                    
                    # Print RMS value for debugging
                    if DEBUG_AUDIO:
                        print(f"Current RMS: {rms:.2f} (Threshold: {SILENCE_THRESHOLD})")
                    
                    # Detect speech based on RMS
                    if rms > SILENCE_THRESHOLD:
                        if not is_speech:
                            print("Speech detected!")
                            is_speech = True
                            audio_buffer = []  # Clear buffer for new speech
                        
                        speech_timeout = 0
                        audio_buffer.append(audio_mono)
                    elif is_speech:
                        speech_timeout += 1
                        audio_buffer.append(audio_mono)
                        
                        if speech_timeout > SILENCE_TIMEOUT:
                            print("Speech ended, processing audio")
                            is_speech = False
                            
                            # Process collected audio
                            if audio_buffer:
                                full_audio = np.concatenate(audio_buffer)
                                print(f"Processing audio of length {len(full_audio)}")
                                
                                # Resample to 16kHz for Whisper if needed
                                if samplerate != SAMPLE_RATE:
                                    print(f"Resampling from {samplerate}Hz to {SAMPLE_RATE}Hz")
                                    # Use numpy's interp function for simple resampling
                                    # Note: This is a simple approach, a proper library would be better
                                    x_old = np.linspace(0, 1, len(full_audio))
                                    x_new = np.linspace(0, 1, int(len(full_audio) * SAMPLE_RATE / samplerate))
                                    full_audio = np.interp(x_new, x_old, full_audio)
                                
                                # Transcribe and handle
                                transcription, translation = self.transcribe_audio(full_audio)
                                self.handle_transcription(transcription, translation)
                            
                            audio_buffer = []
                    
                    # Force processing every 3 seconds for testing
                    if len(audio_buffer) > 30:  # ~3 seconds of audio
                        print("Forced processing for testing")
                        full_audio = np.concatenate(audio_buffer)
                        
                        # Resample if needed
                        if samplerate != SAMPLE_RATE:
                            print(f"Resampling from {samplerate}Hz to {SAMPLE_RATE}Hz")
                            x_old = np.linspace(0, 1, len(full_audio))
                            x_new = np.linspace(0, 1, int(len(full_audio) * SAMPLE_RATE / samplerate))
                            full_audio = np.interp(x_new, x_old, full_audio)
                        
                        # Transcribe and handle
                        transcription, translation = self.transcribe_audio(full_audio)
                        self.handle_transcription(transcription, translation)
                        audio_buffer = []
                    
                    # Sleep a bit to reduce CPU usage
                    time.sleep(0.01)
                    
                except KeyboardInterrupt:
                    print("Keyboard interrupt detected, stopping")
                    break
                except Exception as e:
                    print(f"Error in main loop: {e}")
                    break
            
        except Exception as e:
            print(f"Error setting up audio stream: {e}")
        
        finally:
            print("Cleaning up resources")
            if 'stream' in locals() and stream.active:
                stream.stop()
                stream.close()
            print("Audio stream closed")

if __name__ == "__main__":
    print("=== Integrated Listener ===")
    agent = IntegratedListenerAgent(language="tl", device_index=DEVICE_INDEX)
    agent.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
