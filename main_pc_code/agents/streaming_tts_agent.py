from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader i

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

mport load_config

"""

Ultimate TTS Agent
Provides advanced text-to-speech capabilities with 4-tier fallback system:
Tier 1: XTTS v2 (Primary) - High-quality multilingual speech synthesis
Tier 2: Windows SAPI (Secondary) - Reliable system-level TTS
Tier 3: pyttsx3 (Tertiary) - Cross-platform TTS fallback
Tier 4: Console Print (Final) - Text output as last resort
"""
import zmq
import json
import time
import logging
import sys
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info(f"[{__name__}] Initial sys.path: {sys.path}")
import os
import threading
import queue
import numpy as np
import sounddevice as sd
from pathlib import Path
import hashlib
import tempfile
import re
from main_pc_code.utils.service_discovery_client import register_service, get_service_address
from main_pc_code.utils.env_loader import get_env
import pickle
from main_pc_code.src.network.secure_zmq import configure_secure_client, configure_secure_server
from collections import OrderedDict

# Load configuration at module level
config = load_config()

# Add the parent directory to sys.path

# Configure logging
log_dir = os.path.join(os.path.dirname(__file__), '../../logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'streaming_tts_agent.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger("UltimateTTSAgent")

# Add custom XTTS path
xtts_path = r'C:\Users\haymayndz\Desktop\xtts-local'
if os.path.exists(xtts_path):
    logger.info(f"Added custom XTTS path: {xtts_path}")

# ZMQ Configuration
SAMPLE_RATE = int(config.get("sample_rate", 24000))
CHANNELS = int(config.get("channels", 1))
BUFFER_SIZE = int(config.get("buffer_size", 1024))
MAX_CACHE_SIZE = int(config.get("max_cache_size", 50))

INTERRUPT_PORT = int(config.get("streaming_interrupt_handler_port", 5576))

class UltimateTTSAgent(BaseAgent):
    def __init__(self, port=None):
        # Get configuration values with fallbacks
        agent_port = int(config.get("port", 5562)) if port is None else port
        agent_name = config.get("name", "UltimateTTSAgent")
        bind_address = config.get("bind_address", get_env('BIND_ADDRESS', '<BIND_ADDR>'))
        zmq_timeout = int(config.get("zmq_request_timeout", 5000))
        
        # Additional configuration values
        self.unified_system_port = int(config.get("unifiedsystemagent_port", 5569))
        self.interrupt_port = int(config.get("streaming_interrupt_handler_port", 5576))
        self.sample_rate = int(config.get("sample_rate", 24000))
        self.channels = int(config.get("channels", 1))
        self.buffer_size = int(config.get("buffer_size", 1024))
        self.max_cache_size = int(config.get("max_cache_size", 50))
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=agent_name, port=agent_port)
        
        # Store important attributes
        self.bind_address = bind_address
        self.zmq_timeout = zmq_timeout
        
        """Initialize the Ultimate TTS agent with 4-tier fallback system"""
        logger.info("Initializing Ultimate TTS Agent")
        self.language = config.get("language", 'en')
        
        # Voice customization settings
        self.speaker_wav = None
        self.temperature = 0.7  # Voice variability
        self.speed = 1.0  # Voice speed multiplier
        self.volume = 1.0  # Volume level
        self.use_filipino_accent = False
        
        # Initialize ZMQ
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
        
        if self.secure_zmq:
            self.socket = configure_secure_server(self.socket)
        
        # Bind to address using self.bind_address for Docker compatibility
        bind_address = f"tcp://{self.bind_address}:{self.port}"
        self.socket.bind(bind_address)
        logger.info(f"TTS socket bound to {bind_address}")
        
        # Connect to UnifiedSystemAgent for health monitoring using service discovery
        self.system_socket = self.context.socket(zmq.PUB)
        if self.secure_zmq:
            self.system_socket = configure_secure_client(self.system_socket)
        
        # Try to get the UnifiedSystemAgent address from service discovery
        usa_address = get_service_address("UnifiedSystemAgent")
        if not usa_address:
            # Fall back to configured port
            usa_address = f"tcp://localhost:{self.unified_system_port}"
        
        self.system_socket.connect(usa_address)
        logger.info(f"Connected to UnifiedSystemAgent at {usa_address}")
        
        # Initialize audio cache (OrderedDict maintains insertion order)
        self.cache = OrderedDict()
        
        # Queue for streaming audio chunks
        self.audio_queue = queue.Queue()
        self.is_speaking = False
        self.stop_speaking = False
        
        # Set up voice samples directory
        self.voice_samples_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "voice_samples"
        )
        if not os.path.exists(self.voice_samples_dir):
            os.makedirs(self.voice_samples_dir)
            logger.info(f"Created voice samples directory at {self.voice_samples_dir}")
            
        # Check for Tetey voice sample (from deprecated version)
        tetey_voice_path = "C:/Users/haymayndz/Desktop/Voice assistant/tetey1.wav"
        if os.path.exists(tetey_voice_path):
            self.speaker_wav = tetey_voice_path
            logger.info(f"Found Tetey voice sample at {tetey_voice_path}")
        else:
            # Look for any wav files in the voice samples directory
            voice_samples = [f for f in os.listdir(self.voice_samples_dir) 
                            if f.endswith(".wav")]
            if voice_samples:
                self.speaker_wav = os.path.join(self.voice_samples_dir, voice_samples[0])
                logger.info(f"Using voice sample: {self.speaker_wav}")
        
        # Initialize TTS engines in a background thread
        self.tts_engines = {}
        self.initialization_status = {
            "is_initialized": False,
            "error": None,
            "progress": 0.0,
            "engines_ready": {
                "xtts": False,
                "sapi": False,
                "pyttsx3": False,
                "console": True  # Console is always available
            }
        }
        self.init_thread = threading.Thread(target=self._async_initialize_tts_engines, daemon=True)
        self.init_thread.start()
        
        # Start audio playback thread
        self.playback_thread = threading.Thread(target=self.audio_playback_loop, daemon=True)
        self.playback_thread.start()
        
        # Start health monitoring thread
        self.health_thread = threading.Thread(target=self._send_health_updates, daemon=True)
        self.health_thread.start()
        
        # Interrupt SUB socket - use service discovery
        self.interrupt_socket = self.context.socket(zmq.SUB)
        if self.secure_zmq:
            self.interrupt_socket = configure_secure_client(self.interrupt_socket)
        
        # Try to get the interrupt handler address from service discovery
        interrupt_address = get_service_address("StreamingInterruptHandler")
        if not interrupt_address:
            # Fall back to configured port
            interrupt_address = f"tcp://localhost:{self.interrupt_port}"
        
        self.interrupt_socket.connect(interrupt_address)
        self.interrupt_socket.setsockopt(zmq.SUBSCRIBE, b"")
        logger.info(f"Connected to interrupt handler at {interrupt_address}")
        
        self.interrupt_flag = threading.Event()
        self._start_interrupt_thread()
        
        # Register with service discovery
        self._register_service()
        
        # Set running flag and start_time
        self.running = True
        self.start_time = time.time()
        
        logger.info("TTS Agent basic initialization complete")

    def _register_service(self):
        """Register this agent with the service discovery system"""
        try:
            register_result = register_service(
                name="StreamingTtsAgent",
                port=self.port,
                additional_info={
                    "capabilities": ["tts", "streaming", "multilingual"],
                    "status": "initializing"
                }
            )
            if register_result and register_result.get("status") == "SUCCESS":
                logger.info("Successfully registered with service discovery")
            else:
                logger.warning(f"Service registration failed: {register_result.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error registering service: {e}")

    def _initialize_tts_engines(self):
        """Initialize all TTS engines in order of preference"""
        try:
            # --- Start of XTTS Initialization Block ---
            print("\n==== XTTS INITIALIZATION DEBUG ====")
            
            # Set up voice sample
            tetey_voice_path = "C:/Users/haymayndz/Desktop/Voice assistant/tetey1.wav"
            untitled_voice_path = "C:/Users/haymayndz/Desktop/Voice assistant/untitled1.wav"
            
            # Check which voice samples exist
            print("Checking available voice samples:")
            if os.path.exists(tetey_voice_path):
                print(f"  - Found tetey1.wav at: {tetey_voice_path}")
                self.speaker_wav = tetey_voice_path
            
            if os.path.exists(untitled_voice_path):
                print(f"  - Found untitled1.wav at: {untitled_voice_path}")
                self.speaker_wav = untitled_voice_path  # Prefer this one if both exist
            
            # Look for any wav files in the voice samples directory
            voice_samples = [f for f in os.listdir(self.voice_samples_dir) 
                            if f.endswith(".wav")]
            if voice_samples:
                sample_path = os.path.join(self.voice_samples_dir, voice_samples[0])
                print(f"  - Found sample in voice_samples dir: {sample_path}")
                # Only use if no other samples found
                if not self.speaker_wav:
                    self.speaker_wav = sample_path
            
            if not self.speaker_wav:
                print("  - No voice samples found!")
            else:
                print(f"Using voice sample: {self.speaker_wav}")
            
            try:
                from TTS.api import TTS
                import torch
                
                # Check for CUDA
                cuda_available = torch.cuda.is_available()
                print(f"CUDA available: {cuda_available}")
                device = "cuda" if cuda_available else "cpu"
                
                print(f"Loading predefined XTTS model...")
                # Use the predefined model which we know works
                
                # Initialize XTTS without speaker_wav parameter
                try:
                    print("Initializing XTTS model without voice sample")
                    self.tts_engines["xtts"] = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
                    self.initialization_status["engines_ready"]["xtts"] = True
                    print("SUCCESS: XTTS model loaded successfully!")
                except Exception as e:
                    print(f"Failed to initialize XTTS: {e}")
                    import traceback
                    print("--- DETAILED XTTS INITIALIZATION ERROR ---")
                    traceback.print_exc()
                    print("------------------------------------------")
                
                logger.info("Tier 1: XTTS v2 model loaded successfully.")
                print("XTTS initialization complete. Model is ready to use.")
                
            except ImportError as e:
                print(f"Import error: {e}")
                logger.error(f"Tier 1 (XTTS) failed during initialization: {e}")
                print(f"CRITICAL ERROR in XTTS initialization: {e}")
                import traceback
                print("--- DETAILED XTTS INITIALIZATION ERROR ---")
                traceback.print_exc()
                print("------------------------------------------")

            print("==== END XTTS INITIALIZATION DEBUG ====\n")
            # --- End of XTTS Initialization Block ---
            
            # Tier 2: Windows SAPI
            try:
                import win32com.client
                self.tts_engines["sapi"] = win32com.client.Dispatch("SAPI.SpVoice")
                self.initialization_status["engines_ready"]["sapi"] = True
                logger.info("Tier 2: Windows SAPI initialized")
            except ImportError as e:
                print(f"Import error: {e}")
                logger.warning("Windows SAPI not available")
            except Exception as e:
                logger.warning(f"Tier 2: Windows SAPI initialization failed: {e}")
            
            # Tier 3: pyttsx3
            try:
                import pyttsx3
                self.tts_engines["pyttsx3"] = pyttsx3.init()
                self.initialization_status["engines_ready"]["pyttsx3"] = True
                logger.info("Tier 3: pyttsx3 initialized")
            except ImportError as e:
                print(f"Import error: {e}")
                logger.warning("pyttsx3 not available")
            except Exception as e:
                logger.warning(f"Tier 3: pyttsx3 initialization failed: {e}")
            
            # Tier 4: Console Print (always available)
            self.tts_engines["console"] = True
            
            # Mark initialization as complete
            self.initialization_status.update({
                "is_initialized": True,
                "progress": 1.0
            })
            logger.info("TTS engines initialization complete")
            
        except Exception as e:
            self.initialization_status.update({
                "error": str(e),
                "progress": 0.0
            })
            logger.error(f"TTS engines initialization failed: {e}")

    def _async_initialize_tts_engines(self):
        """Background thread to load TTS engines."""
        try:
            self._initialize_tts_engines()
        except Exception as e:
            logger.error(f"Error in TTS initialization thread: {e}")
            self.initialization_status.update({
                "error": str(e),
                "progress": 0.0
            })
    
    def _add_to_cache(self, key, audio):
        """Add audio to cache with size limit"""
        if len(self.cache) >= MAX_CACHE_SIZE:
            # Remove oldest item
            self.cache.popitem(last=False)
        self.cache[key] = audio
    
    def split_into_sentences(self, text):
        """Split text into sentences for streaming"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s for s in sentences if s.strip()]
    
    def speak(self, text):
        """Speak text using the best available TTS engine"""
        if not self.initialization_status["is_initialized"]:
            logger.warning("TTS engines not yet initialized, using console fallback")
            self._speak_with_console(text)
            return
            
        if self.interrupt_flag.is_set():
            logger.info("Interrupt flag detected. Stopping TTS generation.")
            self.audio_queue.queue.clear()
            self.interrupt_flag.clear()
            return {"status": "error", "message": "Interrupted"}
            
        # Try engines in order of preference
        if self.initialization_status["engines_ready"]["xtts"]:
            self._speak_with_xtts(text)
        elif self.initialization_status["engines_ready"]["sapi"]:
            self._speak_with_sapi(text)
        elif self.initialization_status["engines_ready"]["pyttsx3"]:
            self._speak_with_pyttsx3(text)
        else:
            self._speak_with_console(text)
    
    def _speak_with_xtts(self, text):
        """Speak using XTTS v2"""
        # Make sure numpy is imported
        import numpy as np
        
        print(f"\n==== XTTS SPEAK ATTEMPT ====")
        print(f"Attempting to speak with XTTS: '{text[:50]}...'")
        
        # Map Tagalog/Filipino to English since XTTS doesn't support 'tl' directly
        # The voice sample will still give it Filipino characteristics
        actual_language = self.language
        tts_language = self.language
        
        # List of supported languages from the error message
        supported_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'pl', 'tr', 'ru', 'nl', 'cs', 'ar', 'zh-cn', 'hu', 'ko', 'ja', 'hi']
        
        # If language is not supported, fall back to English
        if tts_language not in supported_languages:
            print(f"Language '{tts_language}' not directly supported, using 'en' with voice sample instead")
            tts_language = 'en'
        
        print(f"Voice settings: language={actual_language} (using {tts_language}), temperature={self.temperature}, speed={self.speed}, volume={self.volume}")
        
        # DETAILED VOICE SAMPLE VERIFICATION
        voice_sample = self.speaker_wav
        print(f"Voice sample path: {voice_sample}")
        if voice_sample:
            if os.path.exists(voice_sample):
                try:
                    import soundfile as sf
                    info = sf.info(voice_sample)
                    print(f"VOICE SAMPLE VERIFIED: {voice_sample}")
                    print(f"  - File exists: YES")
                    print(f"  - Duration: {info.duration:.2f} seconds")
                    print(f"  - Sample rate: {info.samplerate} Hz")
                    print(f"  - Channels: {info.channels}")
                except ImportError as e:
                    print(f"Import error: {e}")
                    print(f"  - Cannot verify voice sample details: soundfile not available")
                except Exception as e:
                    print(f"  - Error reading voice sample: {e}")
            else:
                print(f"  - File exists: NO - VOICE SAMPLE NOT FOUND!")
                print(f"  - Will fall back to default voice")
        else:
            print("  - No voice sample specified")
        
        # Check cache first - include all voice parameters in the cache key
        cache_key = hashlib.md5(f"{text}_{actual_language}_{self.speaker_wav}_{self.temperature}_{self.speed}_{self.volume}".encode()).hexdigest()
        cached_audio = self.cache.get(cache_key)
        audio = None  # Initialize audio variable
        
        if cached_audio:
            print("Using cached XTTS audio")
            logger.info(f"Using cached XTTS audio for: {text[:30]}...")
            audio = cached_audio
        else:
            print("Generating new XTTS audio - no cache hit")
            logger.info(f"Generating XTTS audio for: {text[:30]}...")
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Generate audio using XTTS
            try:
                print(f"Generating new XTTS audio...")
                
                # Ensure we have a valid speaker_wav
                if not self.speaker_wav or not os.path.exists(self.speaker_wav):
                    print("WARNING: No valid speaker_wav found for XTTS!")
                    # Try to find any available voice sample
                    tetey_voice_path = "C:/Users/haymayndz/Desktop/Voice assistant/tetey1.wav"
                    untitled_voice_path = "C:/Users/haymayndz/Desktop/Voice assistant/untitled1.wav"
                    
                    if os.path.exists(untitled_voice_path):
                        self.speaker_wav = untitled_voice_path
                        print(f"Found and using untitled1.wav: {untitled_voice_path}")
                    elif os.path.exists(tetey_voice_path):
                        self.speaker_wav = tetey_voice_path
                        print(f"Found and using tetey1.wav: {tetey_voice_path}")
                
                # Double check we have a valid speaker_wav before proceeding
                if not self.speaker_wav or not os.path.exists(self.speaker_wav):
                    print("ERROR: Still no valid speaker_wav found! Will likely use default voice.")
                
                # Explicitly load the voice sample for this generation
                print(f"Generating with voice sample: {self.speaker_wav}")
                
                # Use the TTS model to generate audio
                wav = self.tts_engines["xtts"].tts(
                    text=text,
                    speaker_wav=self.speaker_wav,
                    language=tts_language,
                    temperature=self.temperature
                )
                
                print("XTTS generation successful!")
                
                # Handle the case where wav is a list (newer XTTS versions return a list)
                if isinstance(wav, list):
                    print("Converting list output to numpy array...")
                    # If it's a list of sentences, concatenate them
                    if len(wav) > 0:
                        if isinstance(wav[0], np.ndarray):
                            wav = np.concatenate(wav)
                        else:
                            # If it's a list of floats, convert directly to numpy array
                            wav = np.array(wav)
                
                # Apply speed adjustment if needed
                if self.speed != 1.0:
                    print(f"Adjusting speed to {self.speed}x")
                    import librosa
                    wav = librosa.effects.time_stretch(wav, rate=self.speed)
                
                # Apply volume adjustment if needed
                if self.volume != 1.0:
                    print(f"Adjusting volume to {self.volume}x")
                    wav = wav * self.volume
                
                # Keep audio as float32 for compatibility with sounddevice
                # Make sure values are between -1 and 1
                audio = wav.astype(np.float32)
                
                # Cache the result
                self.cache[cache_key] = audio
                
            except Exception as e:
                print(f"XTTS generation failed: {e}")
                import traceback
                traceback.print_exc()
                # Fall back to SAPI
                return self._speak_with_sapi(text)
        
        # Stream audio in chunks
        if audio is not None:
            print(f"Streaming XTTS audio in chunks: {len(audio)} samples")
            chunk_size = BUFFER_SIZE
            for i in range(0, len(audio), chunk_size):
                if self.stop_speaking:
                    print("Streaming interrupted by stop command")
                    break
                chunk = audio[i:i+chunk_size]
                self.audio_queue.put(chunk)
            
            print("==== END XTTS SPEAK ATTEMPT (SUCCESS) ====\n")
            return True
        else:
            print("==== END XTTS SPEAK ATTEMPT (FAILED - NO AUDIO) ====\n")
            return self._speak_with_sapi(text)
    
    def _speak_with_sapi(self, text):
        """Speak using Windows SAPI"""
        logger.info(f"Speaking with SAPI: {text[:30]}...")
        self.tts_engines["sapi"].Speak(text)
        return True
    
    def _speak_with_pyttsx3(self, text):
        """Speak using pyttsx3"""
        logger.info(f"Speaking with pyttsx3: {text[:30]}...")
        engine = self.tts_engines["pyttsx3"]
        engine.say(text)
        engine.runAndWait()
        return True
    
    def _speak_with_console(self, text):
        """Print text to console"""
        logger.info(f"Console output: {text}")
        print(f"[TTS] {text}")
        return True
    
    def audio_playback_loop(self):
        """Background thread for audio playback"""
        logger.info("Starting audio playback thread")
        
        try:
            with sd.OutputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype='float32',  # Always use float32 for output
                blocksize=BUFFER_SIZE
            ) as stream:
                while True:
                    try:
                        # Get audio chunk from queue with timeout
                        try:
                            chunk = self.audio_queue.get(timeout=0.2)
                        except queue.Empty:
                            continue
                        
                        # Convert chunk to float32 if it's not already
                        if chunk.dtype != np.float32:
                            if chunk.dtype == np.int16:
                                # Convert from int16 to float32
                                chunk = chunk.astype(np.float32) / 32767.0
                            else:
                                # For any other type, try to convert to float32
                                chunk = chunk.astype(np.float32)
                        
                        # Make sure values are between -1 and 1
                        if np.max(np.abs(chunk)) > 1.0:
                            chunk = chunk / np.max(np.abs(chunk))
                        
                        # Play audio chunk
                        if len(chunk) > 0:
                            stream.write(chunk)
                        
                        # Mark task as done
                        self.audio_queue.task_done()
                        
                    except Exception as e:
                        logger.error(f"Error in audio playback: {e}")
                        time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error setting up audio stream: {e}")
    
    def _send_health_updates(self):
        """Send health updates to UnifiedSystemAgent."""
        while True:
            try:
                health_status = {
                    "status": "success",
                    "agent": "StreamingTTSAgent",
                    "timestamp": time.time(),
                    "initialization_status": self.initialization_status,
                    "is_speaking": self.is_speaking,
                    "queue_size": self.audio_queue.qsize()
                }
                self.system_socket.send_json(health_status)
                time.sleep(5)  # Send updates every 5 seconds
            except Exception as e:
                logger.error(f"Error sending health update: {e}")
                time.sleep(1)
    
    def _interrupt_listener(self):
        """Listen for interrupt signals"""
        logger.info("Starting interrupt listener thread")
        while True:
            try:
                msg = self.interrupt_socket.recv(flags=zmq.NOBLOCK)
                data = pickle.loads(msg)
                if data.get('type') == 'interrupt':
                    logger.info("Received interrupt signal")
                    self.interrupt_flag.set()
                    self.stop_speaking = True
                    # Clear audio queue
                    while not self.audio_queue.empty():
                        try:
                            self.audio_queue.get_nowait()
                        except queue.Empty:
                            break
            except zmq.Again:
                time.sleep(0.05)  # Small sleep to avoid tight loop
            except Exception as e:
                logger.error(f"Error in interrupt listener: {e}")
                time.sleep(1)  # Longer sleep on error

    def _start_interrupt_thread(self):
        """Start the interrupt listener thread"""
        self.interrupt_thread = threading.Thread(target=self._interrupt_listener, daemon=True)
        self.interrupt_thread.start()
        logger.info("Interrupt listener thread started")

    def _get_health_status(self):
        # Default health status: Agent is running if its main loop is active.
        # This can be expanded with more specific checks later.
        status = "HEALTHY" if self.running else "UNHEALTHY"
        details = {
            "status_message": "Agent is operational.",
            "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else 0
        }
        return {"status": status, "details": details}

    def run(self):
        """Main loop to handle TTS requests"""
        logger.info("Starting TTS agent main loop")
        
        try:
            # Update service status to running
            self._update_service_status("running")
            
            while True:
                try:
                    # Check for interrupt before processing new request
                    if self.interrupt_flag.is_set():
                        self.stop_speaking = True
                        self.interrupt_flag.clear()
                        logger.info("Cleared interrupt flag")
                    
                    # Receive request with timeout to allow checking interrupt flag
                    poller = zmq.Poller()
                    poller.register(self.socket, zmq.POLLIN)
                    
                    if poller.poll(100):  # 100ms timeout
                        request = self.socket.recv_json()
                        logger.info(f"Received request: {request}")
                        
                        # Extract request data
                        text = request.get("text", "")
                        emotion = request.get("emotion")
                        language = request.get("language")
                        command = request.get("command")
                        
                        # Check for special commands
                        if command == "stop":
                            logger.info("Received stop command")
                            self.stop_speaking = True
                            # Clear audio queue
                            while not self.audio_queue.empty():
                                try:
                                    self.audio_queue.get_nowait()
                                except queue.Empty:
                                    break
                            self.socket.send_json({"status": "success", "message": "Speech stopped"})
                            continue
                        
                        # Skip empty text
                        if not text:
                            error_msg = "Empty text received"
                            logger.warning(error_msg)
                            self.socket.send_json({
                                "status": "error", 
                                "message": error_msg,
                                "error_type": "invalid_input"
                            })
                            continue
                        
                        # Check if TTS engines are initialized
                        if not self.initialization_status["is_initialized"]:
                            if self.initialization_status["error"]:
                                error_msg = f"TTS initialization failed: {self.initialization_status['error']}"
                                logger.error(error_msg)
                                self.socket.send_json({
                                    "status": "error", 
                                    "message": error_msg,
                                    "error_type": "initialization_error",
                                    "initialization_status": self.initialization_status
                                })
                            else:
                                progress = self.initialization_status["progress"]
                                logger.info(f"TTS still initializing ({progress*100:.0f}%)")
                                self.socket.send_json({
                                    "status": "error", 
                                    "message": f"TTS still initializing ({progress*100:.0f}%)",
                                    "error_type": "not_ready",
                                    "initialization_status": self.initialization_status
                                })
                            continue
                        
                        # Process the text
                        try:
                            success = self.speak(text)
                            if success:
                                self.socket.send_json({"status": "success"})
                            else:
                                self.socket.send_json({
                                    "status": "error", 
                                    "message": "Failed to generate speech",
                                    "error_type": "generation_failed"
                                })
                        except Exception as e:
                            error_msg = f"Error generating speech: {str(e)}"
                            logger.error(error_msg)
                            self.socket.send_json({
                                "status": "error", 
                                "message": error_msg,
                                "error_type": "processing_error"
                            })
                    
                except zmq.Again:
                    # Timeout on receive, just continue the loop
                    pass
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    self.socket.send_json({
                        "status": "error", 
                        "message": f"Invalid JSON: {str(e)}",
                        "error_type": "invalid_request"
                    })
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    try:
                        self.socket.send_json({
                            "status": "error", 
                            "message": f"Internal error: {str(e)}",
                            "error_type": "internal_error"
                        })
                    except zmq.ZMQError:
                        pass  # Socket might be closed
                        
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        finally:
            self._shutdown()
    
    def _update_service_status(self, status):
        """Update the service status in the service registry"""
        try:
            register_service(
                name="StreamingTtsAgent",
                port=self.port,
                additional_info={
                    "capabilities": ["tts", "streaming", "multilingual"],
                    "status": status
                }
            )
            logger.info(f"Updated service status to '{status}'")
        except Exception as e:
            logger.error(f"Error updating service status: {e}")
    
    def _shutdown(self):
        """Clean up resources"""
        logger.info("Shutting down StreamingTtsAgent")
        
        # Update service status
        self._update_service_status("stopping")
        
        # Stop flag for threads
        self.stop_speaking = True
        
        # Clear audio queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        
        # Close all sockets
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
            logger.info("Closed main socket")
            
        if hasattr(self, 'system_socket') and self.system_socket:
            self.system_socket.close()
            logger.info("Closed system socket")
            
        if hasattr(self, 'interrupt_socket') and self.interrupt_socket:
            self.interrupt_socket.close()
            logger.info("Closed interrupt socket")
        
        # Terminate ZMQ context
        if hasattr(self, 'context') and self.context:
            self.context.term()
            logger.info("Terminated ZMQ context")
        
        logger.info("StreamingTtsAgent shut down successfully")


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
    # Standardized main execution block
    agent = None
    try:
        logger.info("Starting UltimateTTSAgent...")
        agent = UltimateTTSAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        logger.error(f"An unexpected error occurred in {agent.name if agent else 'UltimateTTSAgent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            logger.info(f"Cleaning up {agent.name}...")
            agent.cleanup()