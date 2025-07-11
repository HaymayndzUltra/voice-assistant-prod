"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

Streaming Audio Capture Module
Streams audio chunks in real-time to downstream modules via ZMQ
Includes integrated wake word detection using Whisper
"""

import sounddevice as sd
import time
import pickle
import zmq
import numpy as np
import logging
import json
import threading
import sys
import queue
import wave
import os
from pathlib import Path
from collections import deque
from datetime import datetime
try:
    import pyaudio
except ImportError:
    pyaudio = None  # PyAudio may not be installed; handled via dummy mode
import socket
import psutil

# Add project root to the Python path to allow for absolute imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import with canonical path
from common.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config

# Parse agent arguments at module level with canonical import
config = load_config()

# Attempt to import health check server utility, fallback to no-op if unavailable
try:
    from main_pc_code.core.http_server import setup_health_check_server
except ModuleNotFoundError:
    def setup_health_check_server(*args, **kwargs):
        logging.warning("setup_health_check_server not found; HTTP health checks disabled for AudioCapture")
        return None

# Import service discovery client
try:
    from main_pc_code.utils.service_discovery_client import register_service
except ImportError:
    def register_service(*args, **kwargs):
        logging.warning("Service discovery client not found; service registration disabled")
        return None

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AudioCapture")

# Check for secure ZMQ configuration
SECURE_ZMQ = os.environ.get("SECURE_ZMQ", "0") == "1"

# Configuration for wake word integration
WAKE_WORD_ENABLED = False  # Set to False to disable wake word detection
WAKE_WORD_TIMEOUT = 15  # Seconds to listen after wake word detected
WAKE_WORD_LIST = ["highminds"]  # Primary wake word
WAKE_WORD_THRESHOLD = 0.7  # Increased from 0.5 to 0.7 for stricter matching

# Energy detection fallback settings
ENERGY_FALLBACK_ENABLED = True  # Enable energy-based fallback
ENERGY_THRESHOLD = 0.15  # Increased from 0.12 to 0.15
ENERGY_MIN_DURATION = 0.5  # Increased from 0.3 to 0.5 seconds
ENERGY_COOLDOWN = 5  # Increased from 3 to 5 seconds

# Audio settings
SAMPLE_RATE = 48000  # Updated by microphone_selector.py
CHANNELS = 1
CHUNK_DURATION = 0.2  # Reduced from 0.5s for faster processing
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_DURATION)
WAKE_WORD_BUFFER_SECONDS = 2  # Reduced from 3s for faster wake word detection
# Gracefully parse port argument (can be None or non-int)
_default_pub_port = 6575
_arg_port = config.get("port", None)
try:
    ZMQ_PUB_PORT = int(_arg_port) if _arg_port else _default_pub_port
except (TypeError, ValueError):
    ZMQ_PUB_PORT = _default_pub_port

ZMQ_REQUEST_TIMEOUT = 5000  # milliseconds
ZMQ_HEALTH_PORT = 6576  # Base health port; will be adjusted dynamically if occupied

def find_available_port(start_port, max_attempts=10):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find available port after {max_attempts} attempts")

class StreamingAudioCapture(BaseAgent):
    def __init__(self, config=None, **kwargs):
        """Initialize the StreamingAudioCapture agent with audio processing capabilities and robust template compliance."""
        config = config or {}
        # Standardize name and port handling
        self.name = kwargs.get('name', os.environ.get("AGENT_NAME", "StreamingAudioCapture"))
        self.port = int(kwargs.get('port', os.environ.get("AGENT_PORT", config.get("port", ZMQ_PUB_PORT))))
        self.health_port = int(os.environ.get("HEALTH_CHECK_PORT", str(self.port + 1)))
        self.running = True
        self.start_time = time.time()
        # Project root setup
        self.project_root = os.environ.get("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
        if self.project_root not in sys.path:
            sys.path.insert(0, self.project_root)
        # Call BaseAgent's __init__
        super().__init__(port=self.port, name=self.name)
        # --- Original initialization preserved below ---
        self.dummy_mode = os.getenv("USE_DUMMY_AUDIO", "false").lower() == "true"
        from collections import deque
        if self.dummy_mode:
            logger.warning("USE_DUMMY_AUDIO=true -> Running in dummy audio mode; skipping PyAudio initialization")
            self.p = None
        else:
            import pyaudio
            try:
                self.p = pyaudio.PyAudio()
                logger.info(f"PyAudio instance created in __init__: {self.p}")
            except Exception as e_pyaudio_init:
                logger.critical(f"CRITICAL_PYAUDIO_INIT_FAIL: Failed to initialize PyAudio in __init__: {e_pyaudio_init}", exc_info=True)
                raise
        self.device_index = 1
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_samples = 1024
        print("✅ DEBUG: __init__ called, parameters set")
        self.context = None
        self.pub_socket = None
        self.health_socket = None
        self.stream = None
        self.health_thread = None
        self.whisper_model = None
        self.device = None
        self.http_server = None
        self.pub_port = self.port
        self.wake_word_enabled = WAKE_WORD_ENABLED
        self.wake_words = WAKE_WORD_LIST
        self.wake_word_timeout_end_time = 0
        if self.sample_rate and WAKE_WORD_BUFFER_SECONDS:
            self.audio_buffer = deque(maxlen=int(self.sample_rate * WAKE_WORD_BUFFER_SECONDS))
        else:
            logger.warning("Sample rate or WAKE_WORD_BUFFER_SECONDS not set for audio_buffer init.")
            self.audio_buffer = deque()
        self.energy_fallback_enabled = ENERGY_FALLBACK_ENABLED
        self.energy_threshold = ENERGY_THRESHOLD
        self.energy_min_samples = int(ENERGY_MIN_DURATION * self.sample_rate) if self.sample_rate else 0
        self.energy_cooldown = ENERGY_COOLDOWN
        self.energy_buffer = deque(maxlen=self.energy_min_samples if self.energy_min_samples > 0 else 100)
        self._last_transcription = None
        self.wake_word_active = False
        self.activation_count = 0
        self.last_energy_activation = 0
        self.activation_source = None
        self.error_count = 0
        self.last_error_time = 0
        self.error_cooldown = 5
        logger.info(f"__init__ complete. Using: device_index={self.device_index}, sample_rate={self.sample_rate}, channels={self.channels}, chunk_samples={self.chunk_samples}, wake_word_enabled={self.wake_word_enabled}")
        # --- End original initialization ---
        # Robust ZMQ setup
        self.setup_zmq()
        # Start health check thread
        self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_thread.start()

    

        self.error_bus_port = 7150

        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')

        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"

        self.error_bus_pub = self.context.socket(zmq.PUB)

        self.error_bus_pub.connect(self.error_bus_endpoint)
    def setup_zmq(self):
        """Set up ZMQ sockets with proper error handling"""
        try:
            self.context = zmq.Context()
            # Main PUB socket
            self.pub_socket = self.context.socket(zmq.PUB)
            self.pub_socket.setsockopt(zmq.LINGER, 0)
            # Health socket
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.setsockopt(zmq.LINGER, 0)
            self.health_socket.setsockopt(zmq.RCVTIMEO, 1000)
            
            # Error bus setup
            self.error_bus_port = int(config.get("error_bus_port", 7150))
            self.error_bus_host = os.environ.get('PC2_IP', config.get("pc2_ip", "127.0.0.1"))
            self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
            self.error_bus_pub = self.context.socket(zmq.PUB)
            self.error_bus_pub.connect(self.error_bus_endpoint)
            
            # Bind sockets with retry logic
            self._bind_socket_with_retry(self.pub_socket, self.pub_port)
            self._bind_socket_with_retry(self.health_socket, self.health_port)
            logger.info(f"Successfully set up ZMQ sockets on ports {self.pub_port} (PUB) and {self.health_port} (health)")
            return True
        except Exception as e:
            logger.error(f"Error setting up ZMQ: {e}")
            self.cleanup()
            return False

    def _bind_socket_with_retry(self, socket, port, max_retries=5):
        retries = 0
        while retries < max_retries:
            try:
                socket.bind(f"tcp://*:{port}")
                logger.info(f"Successfully bound to port {port}")
                return True
            except zmq.error.ZMQError as e:
                retries += 1
                logger.warning(f"Failed to bind to port {port} (attempt {retries}/{max_retries}): {e}")
                if retries >= max_retries:
                    logger.error(f"Failed to bind to port {port} after {max_retries} attempts")
                    raise
                time.sleep(1)
        return False

    def _health_check_loop(self):
        logger.info("Starting health check loop")
        while self.running:
            try:
                if self.health_socket and self.health_socket.poll(100) != 0:
                    message = self.health_socket.recv() if self.health_socket else None
                    logger.debug(f"Received health check request: {message}")
                    response = self._get_health_status()
                    if self.health_socket:
                        self.health_socket.send_json(response)
                        logger.debug("Sent health check response")
            except zmq.error.Again:
                pass
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
            time.sleep(0.1)

    def _get_health_status(self):
        return {
            'status': 'ok',
            'name': self.name,
            'uptime': time.time() - self.start_time,
            'service': 'streaming_audio_capture',
            'dummy_mode': self.dummy_mode,
            'wake_word_enabled': self.wake_word_enabled
        }

    def __enter__(self):
        """Context manager entry - uses pre-initialized PyAudio and hardcoded audio parameters."""
        logger.info("DEBUG_ENTER_CALLED: __enter__ method invoked.")
        logger.info("Entering __enter__ (using pre-initialized self.p and hardcoded audio params)...")
        import zmq
        import threading
        # Import pyaudio only if not in dummy mode (avoids dependency when dummy)
        if not getattr(self, "dummy_mode", False):
            import pyaudio

        try:
            logger.info("DEBUG_ENTER_STEP1A: __enter__ main try block started.")
            self.running = True
            logger.info("DEBUG_ENTER_STEP1B: self.running set to True.")
            self.context = zmq.Context()
            logger.info("DEBUG_ENTER_STEP2: ZMQ context created.")

            # ZMQ Publisher and Health Check Responder Setup
            logger.info("DEBUG_ENTER_STEP3A: About to attempt ZMQ socket setup.")
            try:
                self.pub_port = find_available_port(ZMQ_PUB_PORT)
                self.health_port = find_available_port(ZMQ_HEALTH_PORT)

                self.pub_socket = self.context.socket(zmq.PUB)
                self.health_socket = self.context.socket(zmq.REP)
                self.health_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
                self.health_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)

                # Apply secure ZMQ if enabled
                if SECURE_ZMQ:
                    try:
                        from main_pc_code.src.network.secure_zmq import secure_server_socket, start_auth
                    except ImportError as e:
                        print(f"Import error: {e}")
                        start_auth()
                        self.pub_socket = secure_server_socket(self.pub_socket)
                        self.health_socket = secure_server_socket(self.health_socket)
                        logger.info("Applied secure ZMQ to publisher and health sockets")
                    except Exception as e:
                        logger.error(f"Failed to apply secure ZMQ: {e}")

                self.pub_socket.bind(f"tcp://*:{self.pub_port}")

                logger.info(f"DEBUG_ZMQ_BIND_SUCCESS: ZMQ Publisher bound to tcp://*:{self.pub_port}")
                
                # Register with SystemDigitalTwin
                try:
                    register_service(
                        name="StreamingAudioCapture",
                        port=self.pub_port,
                        additional_info={
                            "health_port": self.health_port,
                            "description": "Raw audio capture from microphone"
                        }
                    )
                    logger.info("Registered with SystemDigitalTwin")
                except Exception as e:
                    logger.error(f"Failed to register with SystemDigitalTwin: {e}")
            except Exception as e_zmq:
                logger.critical(f"CRITICAL ZMQ SETUP FAILED in __enter__: {e_zmq}", exc_info=True)
                raise

            logger.info("DEBUG_ENTER_ZMQ_COMPLETE: ZMQ setup complete. Proceeding to PyAudio setup...")

            # If in dummy mode, skip all audio device initialization
            if getattr(self, "dummy_mode", False):
                logger.info("Dummy audio mode enabled; skipping PyAudio and audio stream setup.")
                return self

            if self.p is None:
                logger.critical("CRITICAL_PYAUDIO_MISSING: self.p is None in __enter__! Should have been set in __init__.")
                raise RuntimeError("PyAudio instance (self.p) not available in __enter__.")

            # Device index check and fallback
            try:
                device_info = self.p.get_device_info_by_index(int(self.device_index))
                logger.info(f"DEBUG_DEVICE_INFO_SUCCESS: Using audio device (index {self.device_index}): {device_info.get('name')}")
            except Exception as e_device:
                logger.error(f"Device index {self.device_index} not found. Falling back to default input device. Error: {e_device}")
                self.device_index = int(self.p.get_default_input_device_info()['index'])
                device_info = self.p.get_device_info_by_index(int(self.device_index))
                logger.info(f"Fell back to default input device (index {self.device_index}): {device_info.get('name')}")

            logger.info(f"DEBUG_PYAUDIO_PARAMS_CHECK: Using params: device_index={self.device_index}, rate={self.sample_rate}, channels={self.channels}, frames_per_buffer={self.chunk_samples}")

            try:
                logger.info(f"DEBUG_PYAUDIO_PRE_OPEN: Attempting self.p.open() with: device_index={self.device_index}, rate={self.sample_rate}, channels={self.channels}, frames_per_buffer={self.chunk_samples}, callback_defined={self.audio_callback is not None})")
                self.stream = self.p.open(
                    format=pyaudio.paFloat32,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    input_device_index=int(self.device_index),
                    frames_per_buffer=self.chunk_samples,
                    stream_callback=self.audio_callback
                )
                logger.info(f"DEBUG_PYAUDIO_POST_OPEN: self.p.open() called. self.stream is: {self.stream}")
                if self.stream is None:
                    logger.error("CRITICAL_DEBUG_STREAM_NONE: self.p.open() returned None without raising an exception!")
                    raise RuntimeError("Audio stream initialization failed: self.p.open() returned None.")
                logger.info(f"DEBUG_STREAM_SUCCESS: Audio stream opened successfully. Stream object: {self.stream}. Stream active: {self.stream.is_active()}")
            except Exception as e_stream_open:
                logger.critical(f"CRITICAL_ERROR_TRACE_PYAUDIO_OPEN: Exception during PyAudio stream opening: {e_stream_open}", exc_info=True)
                raise

            # Start HTTP health check server
            try:
                self.http_server = setup_health_check_server(self.health_port)
                logger.info(f"HTTP health check server started on port {self.health_port}")
            except Exception as e_http:
                logger.error(f"Failed to start HTTP health check server: {e_http}")
                # Don't raise here, as the agent can still function without HTTP health checks

            if self.wake_word_enabled:
                self.initialize_wake_word_detection()
                logger.info("DEBUG_WAKE_WORD_INITIATED: Wake word detection initialization called (if enabled).")
            else:
                logger.info("DEBUG_WAKE_WORD_DISABLED: Wake word detection is disabled.")

            logger.info("DEBUG_ENTER_SUCCESS: __enter__ method completed successfully. Returning self.")
            return self

        except Exception as e_outer:
            logger.critical(f"CRITICAL EXCEPTION in __enter__ (outer try-block): {e_outer}", exc_info=True)
            # Ensure cleanup if initialization fails
            self._cleanup_resources()
            raise

    def _cleanup_resources(self):
        """Clean up all resources to prevent leaks"""
        try:
            if hasattr(self, 'stream') and self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                    logger.info("Audio stream closed during cleanup")
                except Exception as e:
                    logger.error(f"Error closing audio stream: {e}")

            if hasattr(self, 'p') and self.p:
                try:
                    self.p.terminate()
                    logger.info("PyAudio terminated during cleanup")
                except Exception as e:
                    logger.error(f"Error terminating PyAudio: {e}")

            if hasattr(self, 'pub_socket') and self.pub_socket:
                try:
                    self.pub_socket.close()
                    logger.info("Publisher socket closed during cleanup")
                except Exception as e:
                    logger.error(f"Error closing publisher socket: {e}")

            if hasattr(self, 'context') and self.context:
                try:
                    self.context.term()
                    logger.info("ZMQ context terminated during cleanup")
                except Exception as e:
                    logger.error(f"Error terminating ZMQ context: {e}")

            if hasattr(self, 'http_server') and self.http_server:
                try:
                    self.http_server.stop()
                    logger.info("HTTP server stopped during cleanup")
                except Exception as e:
                    logger.error(f"Error stopping HTTP server: {e}")
                    
        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")
        super().cleanup()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources"""
        logger.info("DEBUG_EXIT_CALLED: __exit__ method invoked.")
        self.running = False

        self._cleanup_resources()
        logger.info("DEBUG_EXIT_COMPLETE: __exit__ completed.")

    def initialize_wake_word_detection(self):
        """Initialize Whisper model for wake word detection"""
        try:
            import torch
        except ImportError as e:
            print(f"Import error: {e}")
            import whisper
            
            logger.info("Initializing Whisper model for wake word detection...")
            
            # Use small model for wake word detection (more accurate but slower than tiny)
            logger.info("Loading 'small' Whisper model (more accurate but slower than tiny)...")
            self.whisper_model = whisper.load_model("small")
            self.whisper_model.eval()
            
            # Put model on GPU if available
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.whisper_model = self.whisper_model.to(self.device)
            
            # Configure wake words with phonetic variations
            self.primary_wake_words = ["highminds"]
            
            # Add phonetic variations based on observed near misses
            self.wake_word_variations = {
                "highminds": ["highminds", "high minds", "high mind", "highminds", "high minds", "high mind"]
            }
            
            # Flatten variations into a single list
            self.wake_words = self.primary_wake_words.copy()
            for variations in self.wake_word_variations.values():
                self.wake_words.extend(variations)
            
            # Remove duplicates while preserving order
            self.wake_words = list(dict.fromkeys(self.wake_words))
            
            logger.info(f"✓ Whisper model initialized for wake words: {', '.join(self.primary_wake_words)}")
            logger.info(f"Using device: {self.device}")
            
            # Wake word detection thread
            self.detection_thread = threading.Thread(target=self.wake_word_detection_loop)
            self.detection_thread.daemon = True
            self.detection_thread.start()
            
        except ImportError:
            logger.error("Failed to import whisper. Please install it with: pip install openai-whisper")
            logger.info("Attempting to install whisper...")
            os.system("pip install openai-whisper")
            
            # Try again after installation
            try:
                import whisper
            except ImportError as e:
                print(f"Import error: {e}")
                self.whisper_model = whisper.load_model("tiny")
                self.whisper_model.eval()
                logger.info(f"✓ Whisper model successfully installed and initialized")
                
                # Wake word detection thread
                self.detection_thread = threading.Thread(target=self.wake_word_detection_loop)
                self.detection_thread.daemon = True
                self.detection_thread.start()
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize Whisper after installation: {e}")
                self.wake_word_enabled = False
        except Exception as e:
            logger.error(f"❌ Failed to initialize Whisper: {e}")
            self.wake_word_enabled = False
    
    def wake_word_detection_loop(self):
        """Background thread for wake word detection"""
        logger.info("Wake word detection thread started")
        
        while self.running:
            try:
                # Only process buffer when we have enough audio and not active
                if len(self.audio_buffer) > 0 and not self.wake_word_active:
                    # Create a temporary WAV file from the audio buffer
                    if self.process_audio_buffer_for_wake_word():
                        # Wake word detected - activate system
                        self.wake_word_active = True
                        self.wake_word_timeout = time.time() + WAKE_WORD_TIMEOUT
                        self.activation_count += 1
                        logger.info(f"🔊 Wake word detected - Activating for {WAKE_WORD_TIMEOUT} seconds (count: {self.activation_count})")
                        
                        # Publish wake word event
                        try:
                            event = {
                                "event_type": "wake_word_detected",
                                "timestamp": time.time(),
                                "activation_id": self.activation_count
                            }
                            self.pub_socket.send_string("WAKE_WORD_EVENT: " + json.dumps(event))
                        except Exception as e:
                            logger.error(f"Error publishing wake word event: {e}")
            except Exception as e:
                logger.error(f"Error in wake word detection loop: {e}")
            
            # Check if active period has expired
            if self.wake_word_active and time.time() >= self.wake_word_timeout:
                self.wake_word_active = False
                logger.info("⏱️ Wake word timeout expired - system deactivated")
            
            # Sleep to prevent CPU overuse
            time.sleep(1.0)  # Check every second
    
    def _similar_string(self, a, b, max_distance):
        """Check if two strings are similar within edit distance"""
        # First pass: quick length check
        if abs(len(a) - len(b)) > max_distance:
            return False
            
        # Second pass: character frequency similarity
        a_lower = a.lower()
        b_lower = b.lower()
        
        # If one string contains the other, likely related
        if a_lower in b_lower or b_lower in a_lower:
            return True
            
        # Improved edit distance algorithm with stricter matching
        distance_matrix = [[i + j if i == 0 or j == 0 else 0 for j in range(len(b_lower) + 1)] 
                          for i in range(len(a_lower) + 1)]
        
        for i in range(1, len(a_lower) + 1):
            for j in range(1, len(b_lower) + 1):
                # Calculate insertion, deletion, and substitution costs
                # Give lower penalty to vowel mismatches as they're often misheard
                if a_lower[i-1] == b_lower[j-1]:
                    substitution_cost = 0
                elif a_lower[i-1] in 'aeiou' and b_lower[j-1] in 'aeiou':
                    substitution_cost = 0.7  # Increased from 0.5 to 0.7
                else:
                    substitution_cost = 1.5  # Increased from 1 to 1.5
                    
                # Update distance matrix
                distance_matrix[i][j] = min(
                    distance_matrix[i-1][j] + 1.2,  # Increased from 1 to 1.2
                    distance_matrix[i][j-1] + 1.2,  # Increased from 1 to 1.2
                    distance_matrix[i-1][j-1] + substitution_cost
                )
        
        final_distance = distance_matrix[len(a_lower)][len(b_lower)]
        return final_distance <= max_distance
    
    def process_audio_buffer_for_wake_word(self):
        """Process the audio buffer to detect wake words"""
        try:
            # Convert buffer to numpy array
            buffer_array = np.array(list(self.audio_buffer), dtype=np.float32)
            
            # Debug buffer status - print every 30 seconds
            now = time.time()
            if not hasattr(self, '_last_buffer_debug') or now - self._last_buffer_debug > 30:
                print(f"\n[BUFFER STATUS] Size: {len(buffer_array)} samples, Max amplitude: {np.max(np.abs(buffer_array)):.5f}")
                self._last_buffer_debug = now
            
            # Skip if buffer is too small
            if len(buffer_array) < self.sample_rate * 1.0:  # At least 1 second
                return False
                
            # Create a temporary WAV file
            temp_filename = "temp_wake_word_audio.wav"
            with wave.open(temp_filename, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 2 bytes for int16
                wf.setframerate(self.sample_rate)
                # Convert float32 [-1.0, 1.0] to int16
                wf.writeframes((buffer_array * 32767).astype(np.int16).tobytes())
            
            # Transcribe with Whisper
            import torch
            with torch.no_grad():
                result = self.whisper_model.transcribe(temp_filename, language="en")
                
            # Check if any wake word is in the transcription
            transcription = result["text"].lower().strip()
            
            # Only log if transcription changed
            if transcription != getattr(self, '_last_transcription', None):
                print(f"\n[DEBUG] Whisper heard: '{transcription}'")
                logger.info(f"Whisper transcription: '{transcription}'")
                self._last_transcription = transcription
            
            # Clean up temporary file
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
            
            # First check for exact matches
            for primary_word in self.primary_wake_words:
                if primary_word in transcription:
                    logger.info(f"[EXACT MATCH] Detected primary wake word '{primary_word}' in: '{transcription}'")
                    return True
            
            # Then check all variations
            for wake_word in self.wake_words:
                if wake_word in transcription:
                    # Check which primary wake word this matches
                    for primary, variations in self.wake_word_variations.items():
                        if wake_word in variations:
                            logger.info(f"[VARIATION MATCH] Detected '{wake_word}' as variation of '{primary}' in: '{transcription}'")
                            return True
            
            # Check for similar words with fuzzy matching
            words = transcription.split()
            for word in words:
                # Check against primary wake words with more permissive matching
                for primary_word in self.primary_wake_words:
                    # Different similarity metrics based on word length
                    max_distance = 2 if len(primary_word) > 5 else 1
                    
                    # Check if the word is similar to a wake word
                    if self._similar_string(primary_word, word, max_distance):
                        logger.info(f"[FUZZY MATCH] '{word}' is similar to wake word '{primary_word}'")
                        print(f"\n[FUZZY MATCH] '{word}' detected as similar to '{primary_word}'")
                        return True
                        
                    # More detailed near miss debug information
                    elif len(word) >= 3 and abs(len(word) - len(primary_word)) <= 3:
                        if word[:3] == primary_word[:3] or word[-3:] == primary_word[-3:]:
                            print(f"\n[NEAR MISS] '{word}' has similar beginning/ending to wake word '{primary_word}'")
            
            # No wake word found after all checks
            return False
            
        except Exception as e:
            logger.error(f"Error processing audio for wake word: {e}")
            return False
            
    def check_wake_word(self):
        """Check if system is active due to wake word or energy detection"""
        if not self.wake_word_enabled:
            return True  # Always active if wake word is disabled
            
        # Check if we're in the active period after wake word or energy detection
        if self.wake_word_active and time.time() < self.wake_word_timeout:
            return True  # Active
            
        return False  # Not active, waiting for wake word
    
    def check_energy_levels(self, audio_data, audio_level, rms_level):
        """Check if energy levels indicate potential speech for fallback detection"""
        if not self.energy_fallback_enabled:
            return False
            
        # Check if we're in cooldown period after last energy activation
        current_time = time.time()
        if current_time - self.last_energy_activation < self.energy_cooldown:
            return False
            
        # Add current energy level to buffer
        self.energy_buffer.append(audio_level)
        
        # Check if buffer is full and calculate average energy
        if len(self.energy_buffer) >= self.energy_min_samples:
            avg_energy = sum(self.energy_buffer) / len(self.energy_buffer)
            
            # Check if average energy exceeds threshold
            if avg_energy > self.energy_threshold:
                logger.info(f"🎤 Energy-based activation detected! (avg level: {avg_energy:.4f})")
                print(f"\n[ENERGY ACTIVATION] Detected sustained speech with energy level {avg_energy:.4f}")
                
                # Set activation state
                self.wake_word_active = True
                self.wake_word_timeout = current_time + WAKE_WORD_TIMEOUT
                self.activation_count += 1
                self.last_energy_activation = current_time
                self.activation_source = "energy"
                
                # Publish energy activation event
                try:
                    event = {
                        "event_type": "energy_activation",
                        "timestamp": current_time,
                        "activation_id": self.activation_count,
                        "energy_level": avg_energy
                    }
                    self.pub_socket.send_string("WAKE_WORD_EVENT: " + json.dumps(event))
                except Exception as e:
                    logger.error(f"Error publishing energy activation event: {e}")
                    
                # Clear energy buffer
                self.energy_buffer.clear()
                return True
                
        return False
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        import pyaudio
        try:
            logger.debug(f"DEBUG_CALLBACK: audio_callback entered. Status: {status}, Frame count: {frame_count}")
            if status:
                logger.warning(f"Audio status: {status}")
                # Handle PyAudio status flags
                if status & pyaudio.paInputOverflow:
                    logger.error("Input overflow detected - audio data may be lost")
                    self._propagate_error("InputOverflowError", "Audio input buffer overflow detected")
                if status & pyaudio.paOutputUnderflow:
                    logger.warning("Output underflow detected")

            # Convert in_data (bytes) to numpy array
            try:
                audio_data = np.frombuffer(in_data, dtype=np.float32)
            except Exception as e:
                logger.error(f"Error converting audio data: {e}")
                self._propagate_error("AudioDataError", f"Failed to convert audio data: {e}")
                return (None, pyaudio.paContinue)

            # Calculate audio levels
            try:
                audio_level = np.max(np.abs(audio_data)) if len(audio_data) > 0 else 0.0
                rms_level = np.sqrt(np.mean(audio_data ** 2)) if len(audio_data) > 0 else 0.0
            except Exception as e:
                logger.error(f"Error calculating audio levels: {e}")
                self._propagate_error("AudioProcessingError", f"Failed to calculate audio levels: {e}")
                return (None, pyaudio.paContinue)

            # Add noise filtering
            if audio_level < 0.01:
                return (None, pyaudio.paContinue)

            # Add audio to buffer for wake word detection (regardless of level)
            if self.wake_word_enabled:
                try:
                    if audio_level > 0.01:
                        self.audio_buffer.extend(audio_data)
                        if audio_level > 0.1 and not hasattr(self, '_last_level_log'):
                            self._last_level_log = 0
                        if audio_level > 0.1 and time.time() - getattr(self, '_last_level_log', 0) > 10:
                            print(f"\n[AUDIO LEVEL] Peak: {audio_level:.5f}, RMS: {rms_level:.5f}")
                            self._last_level_log = time.time()
                except Exception as e:
                    logger.error(f"Error adding audio to wake word buffer: {e}")
                    # Non-critical error, continue processing

            # Check if system is active via wake word detection
            try:
                is_active = self.check_wake_word()
            except Exception as e:
                logger.error(f"Error checking wake word status: {e}")
                is_active = False  # Default to inactive on error

            # If not active via wake word, try energy-based detection as fallback
            if not is_active and self.energy_fallback_enabled:
                try:
                    is_active = self.check_energy_levels(audio_data, audio_level, rms_level)
                except Exception as e:
                    logger.error(f"Error in energy-based detection: {e}")
                    is_active = False  # Default to inactive on error

            # Skip processing if not activated through any method
            if not is_active:
                return (None, pyaudio.paContinue)

            # Skip silent audio to reduce noise when active
            if audio_level < 0.02 and rms_level < 0.01:
                return (None, pyaudio.paContinue)

            # Process the audio
            try:
                msg = pickle.dumps({
                    'audio_chunk': audio_data,
                    'sample_rate': self.sample_rate,
                    'timestamp': time.time(),
                    'wake_word_active': True,
                    'audio_level': float(audio_level),
                    'rms_level': float(rms_level),
                    'activation_source': self.activation_source
                })
                self.pub_socket.send(msg)
            except Exception as e:
                logger.error(f"Error in audio callback (publishing): {e}")
                self._propagate_error("CommunicationError", f"Failed to publish audio data: {e}")

            return (None, pyaudio.paContinue)
        except Exception as e:
            logger.error(f"Exception in audio_callback: {e}", exc_info=True)
            self._propagate_error("AudioCallbackError", f"Unhandled error in audio callback: {e}")
            return (None, pyaudio.paContinue)

    def _propagate_error(self, error_type, message):
        """Propagate error to downstream components via ZMQ"""
        # Implement error rate limiting to avoid flooding
        current_time = time.time()
        if current_time - self.last_error_time < self.error_cooldown:
            self.error_count += 1
            return  # Skip sending too many errors
        
        try:
            error_data = {
                'error': True,
                'error_type': error_type,
                'message': message,
                'timestamp': current_time,
                'source': 'StreamingAudioCapture',
                'suppressed_count': self.error_count
            }
            
            # Reset error tracking
            self.last_error_time = current_time
            self.error_count = 0
            
            # Send error message
            if hasattr(self, 'pub_socket') and self.pub_socket:
                self.pub_socket.send(pickle.dumps(error_data))
                logger.info(f"Propagated error to downstream components: {error_type}")
        except Exception as e:
            logger.error(f"Failed to propagate error: {e}")

    def run(self):
        """Main run loop for audio capture."""
        import time  # Ensure time is imported
        # Dummy mode: stay alive without audio processing
        if getattr(self, "dummy_mode", False):
            logger.info("AudioCapture running in dummy mode. Entering idle loop.")
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Dummy mode interrupted by user.")
            return

        # User requested debug prints
        print("🧪 DEBUG in run(): device_index =", self.device_index)
        print("🧪 DEBUG in run(): sample_rate =", self.sample_rate)
        print("🧪 DEBUG in run(): channels =", self.channels)
        print("🧪 DEBUG in run(): stream is set =", self.stream is not None)

        # Dynamic initial log message based on self.wake_word_enabled
        if self.wake_word_enabled:
            status_message = f"wake word detection ENABLED (listening for: {', '.join(self.wake_words)})"
        else:
            status_message = "DIRECT LIVE MICROPHONE INPUT (wake word disabled)"
        logger.info(f"Starting audio capture with {status_message}")
        
        # Corrected defensive check: stream should also not be None
        if self.device_index is None or self.sample_rate is None or self.channels is None or self.stream is None:
            logger.critical(
                f"CRITICAL: Audio stream or device parameters not initialized before run(). "
                f"Stream set: {self.stream is not None}, Device Index: {self.device_index}, "
                f"Sample Rate: {self.sample_rate}, Channels: {self.channels}. Aborting run."
            )
            # Attempt to gracefully shut down if ZMQ components were initialized
            if hasattr(self, 'pub_socket') and self.pub_socket: self.pub_socket.close()
            return

        logger.info(f"Using device {self.device_index} with {self.channels} channels at {self.sample_rate} Hz, chunk_samples: {self.chunk_samples}")
        logger.info(f"Publishing audio to port {self.pub_port}")
        
        try:
            # Start the stream if it exists and is not active
            if self.stream and not self.stream.is_active():
                self.stream.start_stream()
                logger.info("Audio stream started. Press Ctrl+C to stop.")
            elif not self.stream:
                logger.error("Run method called but stream is None even after checks. Aborting.")
                return
            elif self.stream.is_active():
                logger.info("Audio stream is already active.")
            
            # Main loop to keep thread alive
            while self.running:
                time.sleep(0.1) # Keep main thread alive; audio processing happens in callback
                
                # Optional: Log periodic status for wake word active time
                # if self.wake_word_enabled and self.wake_word_active:
                #    current_time = time.time()
                #    if self.wake_word_timeout_end_time > current_time:
                #        remaining = int(self.wake_word_timeout_end_time - current_time)
                #        if remaining % 5 == 0: # Log every 5 seconds of remaining time
                #            logger.debug(f"Wake word active: {remaining}s remaining")
                #    else:
                #        if self.wake_word_active: # Log once when it expires
                #             logger.info("Wake word active period expired.")
                #             self.wake_word_active = False # Reset status
                        
        except KeyboardInterrupt:
            logger.info("Audio capture stopped by user (KeyboardInterrupt in run).")
        except Exception as e:
            logger.error(f"Exception in run loop: {e}", exc_info=True)
        finally:
            logger.info("Exiting run method.")
            # self.running should be primarily controlled by __exit__ or an explicit stop method.
            # Stream stopping/closing and PyAudio termination are handled in __exit__.

    def health_check(self):
        """Performs a health check on the agent, returning a dictionary with its status."""
        try:
            # Basic health check logic
            is_healthy = self.running  # Assume healthy if running
            
            # Check if audio stream is active
            if not self.dummy_mode and hasattr(self, 'stream') and self.stream:
                try:
                    is_healthy = is_healthy and self.stream.is_active()
                except Exception as e:
                    logger.warning(f"Error checking stream active status: {e}")
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
                    "dummy_mode": self.dummy_mode,
                    "wake_word_enabled": self.wake_word_enabled,
                    "wake_word_active": self.wake_word_active if hasattr(self, 'wake_word_active') else False,
                    "activation_count": self.activation_count if hasattr(self, 'activation_count') else 0,
                    "error_count": self.error_count if hasattr(self, 'error_count') else 0
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
    
    def cleanup(self):
        """Clean up all resources to prevent leaks"""
        logger.info("Starting resource cleanup...")
        
        # Set running flag to False to stop any threads
        self.running = False
        
        try:
            # Stop and close the audio stream
            if hasattr(self, 'stream') and self.stream:
                try:
                    if self.stream.is_active():
                        self.stream.stop_stream()
                    self.stream.close()
                    logger.info("Audio stream closed")
                except Exception as e:
                    logger.error(f"Error closing audio stream: {e}")

            # Terminate PyAudio instance
            if hasattr(self, 'p') and self.p:
                try:
                    self.p.terminate()
                    logger.info("PyAudio terminated")
                except Exception as e:
                    logger.error(f"Error terminating PyAudio: {e}")

            # Stop HTTP server if running
            if hasattr(self, 'http_server') and self.http_server:
                try:
                    self.http_server.shutdown()
                    logger.info("HTTP server shut down")
                except Exception as e:
                    logger.error(f"Error shutting down HTTP server: {e}")

            # Close ZMQ sockets
            for socket_name in ['pub_socket', 'health_socket', 'error_bus_pub']:
                if hasattr(self, socket_name) and getattr(self, socket_name):
                    try:
                        getattr(self, socket_name).close()
                        logger.info(f"{socket_name} closed")
                    except Exception as e:
                        logger.error(f"Error closing {socket_name}: {e}")

            # Terminate ZMQ context
            if hasattr(self, 'context') and self.context:
                try:
                    self.context.term()
                    logger.info("ZMQ context terminated")
                except Exception as e:
                    logger.error(f"Error terminating ZMQ context: {e}")

            # Join any running threads
            if hasattr(self, 'health_thread') and self.health_thread and self.health_thread.is_alive():
                try:
                    self.health_thread.join(timeout=2.0)
                    logger.info("Health check thread joined")
                except Exception as e:
                    logger.error(f"Error joining health check thread: {e}")

            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            
        # Call parent cleanup method
        super().cleanup()

    def _get_health_status(self):
        """Get the current health status of the agent.
        
        This method overrides the BaseAgent._get_health_status method to add
        agent-specific health information.
        
        Returns:
            Dict[str, Any]: A dictionary containing health status information
        """
        # Get the base health status from parent class
        base_status = super()._get_health_status()
        
        # Add agent-specific health metrics
        try:
            # Check if audio stream is active
            if hasattr(self, 'stream') and self.stream:
                stream_active = self.stream.is_active() if hasattr(self.stream, 'is_active') else False
            else:
                stream_active = False
            
            # Check ZMQ socket health
            zmq_healthy = hasattr(self, 'pub_socket') and self.pub_socket is not None
            
            # Add metrics to base status
            base_status.update({
                "agent_specific_metrics": {
                    "audio_stream_active": stream_active,
                    "zmq_socket_healthy": zmq_healthy,
                    "dummy_mode": getattr(self, 'dummy_mode', False),
                    "wake_word_enabled": getattr(self, 'wake_word_enabled', False),
                    "activation_count": getattr(self, 'activation_count', 0),
                    "sample_rate": getattr(self, 'sample_rate', 0),
                    "channels": getattr(self, 'channels', 0)
                }
            })
            
        except Exception as e:
            logger.error(f"Error collecting health metrics: {e}")
            base_status.update({"health_metrics_error": str(e)})
        
        return base_status

# Add standardized __main__ block
if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = StreamingAudioCapture()
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