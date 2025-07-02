from main_pc_code.src.core.base_agent import BaseAgent
import os
import sys
import time
import json
import logging
import argparse
import numpy as np
import sounddevice as sd
import zmq
import torch
from scipy.io import wavfile
from datetime import datetime

# Add debug prints
print("[DEBUG] Starting listener_debug.py")
print("[DEBUG] Importing modules completed")

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ListenerDebug")

# Constants
SAMPLE_RATE = 16000
SILENCE_THRESHOLD_SPEECH = 500  # For speech detection
SILENCE_TIMEOUT_SPEECH = 30     # Frames of silence before stopping recording
FORCED_PROCESSING = True        # Force audio processing for debugging
SAVE_DEBUG_AUDIO = True         # Save audio files for debugging

# Create logs directory if it doesn't exist
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
print(f"[DEBUG] LOG_DIR: {LOG_DIR}")

# Try to import noisereduce, but continue if not available
try:
    import noisereduce as nr
    except ImportError as e:
        print(f"Import error: {e}")
    print("[DEBUG] noisereduce imported successfully")
except ImportError:
    print("[Listener] noisereduce not installed, noise reduction will be skipped.")
    nr = None
    print("[DEBUG] Continuing without noisereduce")

# Try to import whisper, but continue if not available
try:
    import whisper
    except ImportError as e:
        print(f"Import error: {e}")
    print("[DEBUG] whisper imported successfully")
except ImportError:
    print("[ERROR] whisper not installed. Please install it with 'pip install openai-whisper'")
    whisper = None
    print("[DEBUG] Exiting due to missing whisper")
    sys.exit(1)

# Try to import googletrans, but continue if not available
try:
    from googletrans import Translator
    except ImportError as e:
        print(f"Import error: {e}")
    print("[DEBUG] googletrans imported successfully")
except ImportError:
    print("[WARNING] googletrans not installed, translation will be skipped.")
    Translator = None
    print("[DEBUG] Continuing without googletrans")

# ZMQ Configuration
ZMQ_PUB_PORT = 5556  # Temporarily using 5556 to avoid port conflict
print(f"[DEBUG] ZMQ_PUB_PORT: {ZMQ_PUB_PORT}")

LOG_PATH = os.path.join(LOG_DIR, "listener_agent_debug.log")
print(f"[DEBUG] LOG_PATH: {LOG_PATH}")

# Print all input devices for manual selection
print("[DEBUG] Listing audio devices:")
try:
    devices = sd.query_devices()
    for idx, device in enumerate(devices):
        if device["max_input_channels"] > 0:  # Only show input devices
            display_name = device["name"]
            print(f'  [{idx}] {display_name} (channels: {device["max_input_channels"]})')
except Exception as e:
    print(f"[DEBUG] Error listing devices: {e}")

# Device selection - using DirectSound API (Index 18)
DEVICE_INDEX = 18  # Testing with DirectSound: SteelSeries Sonar - Microphone (SteelSeries Sonar Virtual Audio Device)
DEVICE_NAME = "SteelSeries Sonar - Microphone (SteelSeries Sonar Virtual Audio Device)"  # Corresponds to Index 18 (DirectSound)
print(f"[DEBUG] DEVICE_INDEX selected: {DEVICE_INDEX}")

try:
    print(f"[DEBUG] Querying device info for index {DEVICE_INDEX}")
    device_info = sd.query_devices(DEVICE_INDEX)
    print(f"[DEBUG] Device info retrieved: {json.dumps(device_info, indent=2)}")
    
    if device_info['max_input_channels'] <= 0:
        print(f"[WARNING] Device {DEVICE_INDEX} has no input channels! Please check selection.")
    else:
        print(f"[INFO] Using Device: {DEVICE_INDEX} - {device_info['name']} (Input Channels: {device_info['max_input_channels']}, Default SR: {device_info['default_samplerate']})")
except Exception as e:
    print(f"[DEBUG] Error getting device info: {e}")
    print(f"[ERROR] Failed to get device info for index {DEVICE_INDEX}. Error: {e}")
    sys.exit(1)

class ListenerAgentDebug(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ListenerDebug")
        print(f"[DEBUG] Initializing ListenerAgentDebug with device_index={device_index}")
        self.language = language
        self.model_size = model_size
        self.device_name = device_name
        self.device_index = device_index
        
        # Initialize ZMQ
        print("[DEBUG] Setting up ZMQ socket")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        
        try:
            print(f"[DEBUG] Binding socket to tcp://*:{ZMQ_PUB_PORT}")
            self.socket.bind(f"tcp://*:{ZMQ_PUB_PORT}")
            print(f"[ZMQ] Publisher socket bound to tcp://*:{ZMQ_PUB_PORT}")
        except Exception as e:
            print(f"[DEBUG] Error binding socket: {e}")
            print(f"[ERROR] Failed to bind ZMQ socket: {e}")
            sys.exit(1)
        
        # Load Whisper model
        print(f"[DEBUG] Loading Whisper model '{model_size}'")
        try:
            print("[INFO] Initializing Whisper model...")
            self.model = whisper.load_model(model_size)
            print(f"[INFO] Whisper model '{model_size}' loaded successfully")
        except Exception as e:
            print(f"[DEBUG] Error loading Whisper model: {e}")
            print(f"[ERROR] Failed to load Whisper model: {e}")
            sys.exit(1)
        
        # Initialize translator if available
        if Translator:
            print("[DEBUG] Initializing translator")
            self.translator = Translator()
        else:
            self.translator = None
            print("[DEBUG] No translator available")
        
        print("[DEBUG] ListenerAgentDebug initialization complete")

    def transcribe_audio(self, audio_data):
        """Transcribe audio using Whisper model"""
        print("[DEBUG] Starting transcription")
        try:
            # Convert audio to float32 if needed
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32) / 32768.0
            
            # Apply noise reduction if available
            if nr:
                print("[DEBUG] Applying noise reduction")
                audio_data = nr.reduce_noise(y=audio_data, sr=SAMPLE_RATE)
            
            # Save debug audio if enabled
            if SAVE_DEBUG_AUDIO:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                debug_file = os.path.join(LOG_DIR, f"debug_audio_{timestamp}.wav")
                print(f"[DEBUG] Saving debug audio to {debug_file}")
                wavfile.write(debug_file, SAMPLE_RATE, (audio_data * 32768).astype(np.int16))
            
            # Transcribe with Whisper
            print("[DEBUG] Running Whisper inference")
            result = self.model.transcribe(audio_data, language=self.language)
            transcription = result["text"].strip()
            print(f"[DEBUG] Transcription result: '{transcription}'")
            
            # Translate if needed and translator is available
            if self.language != "en" and self.translator:
                print(f"[DEBUG] Translating from {self.language} to English")
                try:
                    translation = self.translator.translate(transcription, src=self.language, dest='en')
                    translated_text = translation.text
                    print(f"[DEBUG] Translation result: '{translated_text}'")
                    return transcription, translated_text
                except Exception as e:
                    print(f"[DEBUG] Translation error: {e}")
                    print(f"[ERROR] Translation failed: {e}")
                    return transcription, None
            
            return transcription, None
        
        except Exception as e:
            print(f"[DEBUG] Transcription error: {e}")
            print(f"[ERROR] Transcription failed: {e}")
            return None, None

    def handle_transcription(self, transcription, translation=None):
        """Process and publish transcription results"""
        print(f"[DEBUG] Handling transcription: '{transcription}'")
        
        if not transcription:
            print("[DEBUG] Empty transcription, nothing to handle")
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
            print(f"[DEBUG] Added translation: '{translation}'")
        
        # Publish via ZMQ
        try:
            print(f"[DEBUG] Publishing message to ZMQ: {json.dumps(message)}")
            self.socket.send_string(json.dumps(message))
            print(f"[ZMQ] Published: {message['text'][:30]}...")
        except Exception as e:
            print(f"[DEBUG] Error publishing to ZMQ: {e}")
            print(f"[ERROR] Failed to publish message: {e}")

    def run(self):
        """Main listening loop"""
        print("[DEBUG] Starting main listening loop")
        
        try:
            # Configure audio stream
            print(f"[DEBUG] Configuring audio stream with device_index={self.device_index}")
            
            # Get device info again to be sure
            device_info = sd.query_devices(self.device_index)
            print(f"[DEBUG] Device info for stream: {json.dumps(device_info, indent=2)}")
            
            # Set up audio parameters
            channels = min(1, device_info["max_input_channels"])  # Use mono for processing
            samplerate = int(device_info["default_samplerate"])
            print(f"[DEBUG] Using channels={channels}, samplerate={samplerate}")
            
            # Calculate frames per buffer
            frames_per_buffer = int(samplerate * 0.1)  # 100ms buffer
            print(f"[DEBUG] frames_per_buffer={frames_per_buffer}")
            
            # Open audio stream
            print("[DEBUG] Opening audio stream")
            stream = sd.InputStream(
                samplerate=samplerate,
                device=self.device_index,
                channels=channels,
                callback=None,
                blocksize=frames_per_buffer
            )
            
            print("[DEBUG] Audio stream created, starting stream")
            stream.start()
            print("[INFO] Listener Agent started. Mode: speech, Device: {self.device_index}")
            
            # Variables for audio processing
            audio_buffer = []
            is_speech = False
            speech_timeout = 0
            
            print("[DEBUG] Entering main loop")
            while True:
                # Read audio data
                try:
                    print("[DEBUG] Reading audio data")
                    audio_data, overflowed = stream.read(frames_per_buffer)
                    if overflowed:
                        print("[WARNING] Audio buffer overflow")
                    
                    # Convert to mono and calculate RMS
                    audio_mono = audio_data.mean(axis=1) if audio_data.ndim > 1 else audio_data
                    rms = np.sqrt(np.mean(audio_mono**2)) * 32768  # Scale to int16 range
                    print(f"[DEBUG] Audio RMS: {rms}")
                    
                    # Detect speech based on RMS
                    if rms > SILENCE_THRESHOLD_SPEECH:
                        if not is_speech:
                            print("[DEBUG] Speech detected")
                            is_speech = True
                            audio_buffer = []  # Clear buffer for new speech
                        
                        speech_timeout = 0
                        audio_buffer.append(audio_mono)
                    elif is_speech:
                        speech_timeout += 1
                        audio_buffer.append(audio_mono)
                        
                        if speech_timeout > SILENCE_TIMEOUT_SPEECH:
                            print("[DEBUG] Speech ended, processing audio")
                            is_speech = False
                            
                            # Process collected audio
                            if audio_buffer:
                                full_audio = np.concatenate(audio_buffer)
                                print(f"[DEBUG] Processing audio of length {len(full_audio)}")
                                
                                # Resample to 16kHz for Whisper if needed
                                if samplerate != SAMPLE_RATE:
                                    print(f"[DEBUG] Resampling from {samplerate}Hz to {SAMPLE_RATE}Hz")
                                    # Simple resampling - in production use a proper resampling library
                                    ratio = SAMPLE_RATE / samplerate
                                    full_audio = np.interp(
                                        np.arange(0, len(full_audio) * ratio),
                                        np.arange(0, len(full_audio) * ratio, ratio),
                                        full_audio
                                    )
                                
                                # Transcribe and handle
                                transcription, translation = self.transcribe_audio(full_audio)
                                self.handle_transcription(transcription, translation)
                            
                            audio_buffer = []
                    
                    # Force processing for debugging if enabled
                    if FORCED_PROCESSING and len(audio_buffer) > 50:  # ~5 seconds of audio
                        print("[DEBUG] Forced processing triggered")
                        full_audio = np.concatenate(audio_buffer)
                        
                        # Resample if needed
                        if samplerate != SAMPLE_RATE:
                            ratio = SAMPLE_RATE / samplerate
                            full_audio = np.interp(
                                np.arange(0, len(full_audio) * ratio),
                                np.arange(0, len(full_audio) * ratio, ratio),
                                full_audio
                            )
                        
                        # Transcribe and handle
                        transcription, translation = self.transcribe_audio(full_audio)
                        self.handle_transcription(transcription, translation)
                        audio_buffer = []
                        
                except Exception as e:
                    print(f"[DEBUG] Error in main loop: {e}")
                    print(f"[ERROR] Audio processing error: {e}")
                    break
            
        except Exception as e:
            print(f"[DEBUG] Error setting up audio stream: {e}")
            print(f"[ERROR] Failed to initialize audio stream: {e}")
        
        finally:
            print("[DEBUG] Cleaning up resources")
            if 'stream' in locals() and stream.active:
                stream.stop()
                stream.close()
            print("[DEBUG] Audio stream closed")

if __name__ == "__main__":
    print("[DEBUG] Parsing command line arguments")
    parser = argparse.ArgumentParser(description="Listener Agent Debug for Voice Assistant")
    parser.add_argument("--device", type=int, default=DEVICE_INDEX, help="Audio input device index.")
    # Add other arguments as needed, e.g., --lang, --model_size
    args = parser.parse_args()
    print(f"[DEBUG] Command line args: {args}")
    
    print("[DEBUG] Creating ListenerAgentDebug instance")
    agent = ListenerAgentDebug(device_index=args.device)
    
    print("[DEBUG] Starting agent")
    agent.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
