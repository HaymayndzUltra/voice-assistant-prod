from common.core.base_agent import BaseAgent
import sys
import os
from common.config_manager import get_service_ip, get_service_url, get_redis_url
# Auto-accept Coqui CPML terms for non-commercial use.
# Set the env var only if user hasn't explicitly provided one.

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
from common.utils.path_manager import PathManager
MAIN_PC_CODE_DIR = PathManager.get_main_pc_code()

# Ensure the main_pc_code directory is in sys.path
if str(MAIN_PC_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_PC_CODE_DIR))

os.environ.setdefault("COQUI_TOS_AGREED", "1")
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import json
# import os
import sounddevice as sd
import numpy as np
import threading
import queue
from TTS.api import TTS
import torch
import logging
import time
import pickle
from common.config_manager import load_unified_config
from main_pc_code.utils.service_discovery_client import discover_service, get_service_address
from main_pc_code.utils.env_loader import get_env
from common.utils.path_manager import PathManager
# from main_pc_code.src.network.secure_zmq import is_secure_zmq_enabled, configure_secure_client, configure_secure_server

# Placeholder functions for secure_zmq (module doesn't exist)
def is_secure_zmq_enabled():
    return False

def configure_secure_client(socket):
    return socket

def configure_secure_server(socket):
    return socket

# Load environment variables
config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))

# Get the directory of the current file for the log
current_dir = os.path.dirname(os.path.abspath(__file__))

# Ensure appropriate directories exist
os.makedirs(os.path.join(current_dir, "../logs"), exist_ok=True)

# Define default log path before logging setup
LOG_PATH = os.path.join(current_dir, "../logs/responder.log")

# Import common Tagalog phrases module
try:
    from main_pc_code.agents.common_tagalog_phrases import (
        translate_common_phrase,
        check_and_replace_common_phrases,
        TAGALOG_TO_ENGLISH,
        ENGLISH_TO_TAGALOG
    )
    COMMON_PHRASES_AVAILABLE = True
    logging.info("[Responder] Common Tagalog phrases module loaded successfully")
except ImportError as e:
    print(f"Import error: {e}")
    COMMON_PHRASES_AVAILABLE = False
    logging.warning("[Responder] Common Tagalog phrases module not available")


def add_all_safe_globals():
    # List of known required safe globals for XTTS
    safe_globals = [
        ('TTS.tts.configs.xtts_config', 'XttsConfig'),
        ('TTS.tts.models.xtts', 'XttsAudioConfig'),
        ('TTS.config.shared_configs', 'BaseDatasetConfig'),
        ('TTS.tts.models.xtts', 'XttsArgs'),
    ]
    for module, name in safe_globals:
        try:
            torch.serialization.add_safe_globals([
                __import__(module, fromlist=[name]).__dict__[name]
            ])
            logging.info(f"[Responder] Added safe global: {module}.{name}")
        except Exception as e:
            logging.warning(
                f"[Responder] Could not add safe global {module}.{name}: {e}")


add_all_safe_globals()

# Lazy-load TTS at runtime to avoid blocking import time
try:
    from TTS.api import TTS  # only import, do not instantiate
    TTS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    TTS_AVAILABLE = False


            

        
            

    


# Settings
# ZMQ_RESPONDER_PORT = int(config.get("port", 5637))  # Updated to match config
# ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds in milliseconds

# Get bind address from environment variables with default to a safe value for Docker compatibility
# BIND_ADDRESS = get_env('BIND_ADDRESS', '<BIND_ADDR>')

# Secure ZMQ configuration
# SECURE_ZMQ = is_secure_zmq_enabled()

# Default voice (will be overridden by config)
# VOICE = "tts_models/en/ljspeech/tacotron2-DDC"

# Health monitoring settings
# HEALTH_CHECK_INTERVAL = 30  # seconds
# HEALTH_CHECK_TIMEOUT = 5  # seconds
# MAX_RETRIES = 3

# Language-specific voice configurations
# LANGUAGE_VOICES = {
#     "en": "en",       # Default English voice
#     "tl": "tl",       # Tagalog voice
#     "mixed": "tl",    # For mixed language (Taglish), prefer Tagalog voice
#     "unknown": "en"   # Default to English for unknown
# }

# Use pre-translated responses for common phrases
# USE_PRETRANSLATED_PHRASES = True

# Emotion to voice parameter mapping with enhanced expressiveness
# EMOTION_VOICE_PARAMS = {
#     # Basic emotions with enhanced parameters
#     "joy": {"speed": 1.15, "pitch": 1.15, "energy": 1.2, "vibrato": 0.1, "breathiness": 0.1, "color": "#FFD700"},
#     "sadness": {"speed": 0.85, "pitch": 0.9, "energy": 0.8, "vibrato": 0.0, "breathiness": 0.3, "color": "#4682B4"},
#     "anger": {"speed": 1.2, "pitch": 0.85, "energy": 1.3, "vibrato": 0.2, "breathiness": 0.0, "color": "#FF4500"},
#     "fear": {"speed": 1.15, "pitch": 1.1, "energy": 0.9, "vibrato": 0.3, "breathiness": 0.2, "color": "#800080"},
#     "surprise": {"speed": 1.25, "pitch": 1.2, "energy": 1.2, "vibrato": 0.1, "breathiness": 0.1, "color": "#FF69B4"},
#     "neutral": {"speed": 1.0, "pitch": 1.0, "energy": 1.0, "vibrato": 0.0, "breathiness": 0.0, "color": "#FFFFFF"},
#     "disgust": {"speed": 1.05, "pitch": 0.9, "energy": 1.1, "vibrato": 0.1, "breathiness": 0.0, "color": "#556B2F"},
#     
#     # Nuanced emotions
#     "excitement": {"speed": 1.3, "pitch": 1.25, "energy": 1.3, "vibrato": 0.2, "breathiness": 0.1, "color": "#FFA500"},
#     "contentment": {"speed": 0.95, "pitch": 1.05, "energy": 0.95, "vibrato": 0.0, "breathiness": 0.1, "color": "#98FB98"},
#     "amusement": {"speed": 1.1, "pitch": 1.15, "energy": 1.1, "vibrato": 0.1, "breathiness": 0.0, "color": "#FFFF00"},
#     "pride": {"speed": 1.05, "pitch": 1.1, "energy": 1.15, "vibrato": 0.0, "breathiness": 0.0, "color": "#B8860B"},
#     "embarrassment": {"speed": 1.0, "pitch": 0.95, "energy": 0.85, "vibrato": 0.1, "breathiness": 0.2, "color": "#FF6347"},
#     "guilt": {"speed": 0.9, "pitch": 0.9, "energy": 0.8, "vibrato": 0.0, "breathiness": 0.2, "color": "#2F4F4F"},
#     "shame": {"speed": 0.85, "pitch": 0.85, "energy": 0.75, "vibrato": 0.0, "breathiness": 0.3, "color": "#8B4513"},
#     
#     # General sentiment categories
#     "positive": {"speed": 1.1, "pitch": 1.1, "energy": 1.15, "vibrato": 0.05, "breathiness": 0.05, "color": "#7CFC00"},
#     "negative": {"speed": 0.9, "pitch": 0.9, "energy": 0.85, "vibrato": 0.05, "breathiness": 0.15, "color": "#DC143C"},
#     "calm": {"speed": 0.85, "pitch": 1.0, "energy": 0.9, "vibrato": 0.0, "breathiness": 0.1, "color": "#87CEEB"},
#     "energetic": {"speed": 1.2, "pitch": 1.15, "energy": 1.25, "vibrato": 0.1, "breathiness": 0.0, "color": "#FF8C00"},
#     "serious": {"speed": 0.95, "pitch": 0.95, "energy": 1.0, "vibrato": 0.0, "breathiness": 0.0, "color": "#708090"},
#     "playful": {"speed": 1.15, "pitch": 1.2, "energy": 1.1, "vibrato": 0.1, "breathiness": 0.05, "color": "#FF69B4"},
# }

# Visual feedback settings
# VISUAL_FEEDBACK_ENABLED = False  # Set to True to enable visual feedback
# VISUAL_FEEDBACK_DURATION = 3.0  # How long to show visual feedback in seconds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("ResponderAgent")

# Get interrupt port from args or use default
# INTERRUPT_PORT = int(config.get("streaming_interrupt_handler_port", 5576))

class Responder(BaseAgent):
    def __init__(self):
        self.port = int(config.get('port', 5637))
        self.voice = config.get('voice', 'default')
        self.bind_address = config.get('bind_address', '0.0.0.0')
        self.ZMQ_REQUEST_TIMEOUT = int(config.get('zmq_request_timeout', 5000))
        self.VISUAL_FEEDBACK_ENABLED = bool(config.get('visual_feedback_enabled', False))
        super().__init__(name="Responder", port=self.port)
        self.context = None  # Using pool
        
        # Set up main socket for receiving TTS requests
        self.socket = get_sub_socket(self.endpoint).socket
        if is_secure_zmq_enabled():
            self.socket = configure_secure_server(self.socket)
            
        # Bind to address using BIND_ADDRESS for Docker compatibility
        bind_address = f"tcp://{self.bind_address}:{self.port}"
        self.socket.bind(bind_address)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
        logger.info(f"Responder socket bound to {bind_address}")
        
        # Interrupt SUB socket - use service discovery
        self.interrupt_socket = self.context.socket(zmq.SUB)
        if is_secure_zmq_enabled():
            self.interrupt_socket = configure_secure_client(self.interrupt_socket)
            
        # Try to get the interrupt handler address from service discovery
        interrupt_host = config.get('interrupt_host', 'localhost')
        interrupt_port = int(config.get('streaming_interrupt_handler_port', 5576))
        interrupt_address = f"tcp://{interrupt_host}:{interrupt_port}"
        self.interrupt_socket.connect(interrupt_address)
        self.interrupt_socket.setsockopt(zmq.SUBSCRIBE, b"")
        logger.info(f"Connected to interrupt handler at {interrupt_address}")
        
        self.interrupt_flag = threading.Event()
        self._start_interrupt_thread()
        
        # Connect to services using service discovery
        self._connect_to_services()
        
        # Health monitoring
        self.health_status = {
            "status": "ok",
            "service": "responder",
            "last_check": time.time(),
            "connections": {
                "tts": False,
                "tts_cache": False,
                "tts_agent": False,
                "face_recognition": False
            }
        }
        
        # Start health monitoring thread
        self.health_thread = threading.Thread(target=self._monitor_health, daemon=True)
        self.health_thread.start()
        
        # Start service discovery refresh thread
        self.discovery_refresh_thread = threading.Thread(target=self._refresh_service_connections, daemon=True)
        self.discovery_refresh_thread.start()
        
        # Defer heavy TTS model loading to a background thread
        self.tts = None
        self.tts_ready = threading.Event()
        threading.Thread(target=self._load_tts_model, daemon=True).start()
        
        # Queue for audio processing
        self.audio_queue = queue.Queue()
        self.running = True
        
        # State tracking
        self.last_text = None
        self.last_emotion = None
        self.last_language = None
        self.last_user = None
        self.history = []
        
        # Face data tracking
        self.detected_faces = {}  # Format: {name: {emotion, last_seen, confidence}}
        self.current_speaker = None
        
        # User voice profiles - can be customized per user
        self.user_voice_profiles = {}
        
        # Initialize TTS service connections as None
        self.tts_socket = None
        self.streaming_tts_socket = None
        self.tts_connector_socket = None
        self.model_manager_socket = None

        # Connect to StreamingTTSAgent
        tts_address = get_service_address("StreamingTTSAgent")
        if tts_address:
            self.tts_socket = self.context.socket(zmq.REQ)
            if is_secure_zmq_enabled():
                self.tts_socket = configure_secure_client(self.tts_socket)
            self.tts_socket.setsockopt(zmq.RCVTIMEO, self.ZMQ_REQUEST_TIMEOUT)
            self.tts_socket.connect(tts_address)
            logger.info(f"Connected to StreamingTTSAgent at {tts_address}")
            self.health_status["connections"]["tts_agent"] = True
        else:
            logger.warning("StreamingTTSAgent not found in service discovery")

        # Other sockets (if needed for more complex responses)
        self.emotion_socket = None
        
        logger.info("ResponderAgent initialized")

    

        # Modern error reporting now handled by BaseAgent's UnifiedErrorHandler
    def _connect_to_services(self):
        """Connect to required services using service discovery"""
        try:
            # Defensive: ensure health_status is a dict with 'connections' dict
            if not isinstance(self.health_status, dict) or 'connections' not in self.health_status:
                self.health_status = {
                    "status": "ok",
                    "service": "responder",
                    "last_check": time.time(),
                    "connections": {
                        "tts": False,
                        "tts_cache": False,
                        "tts_agent": False,
                        "face_recognition": False
                    }
                }
            # Connect to face recognition for emotion data
            face_service = discover_service("FaceRecognitionAgent")
            if face_service and face_service.get("status") == "SUCCESS":
                face_info = face_service.get("payload", {})
                face_host = face_info.get("ip", config.get('face_host', 'localhost'))
                face_port = face_info.get("port", 5610)  # Default port
                
                self.face_socket = self.context.socket(zmq.SUB)
                # Apply secure ZMQ if enabled
                if is_secure_zmq_enabled():
                    self.face_socket = configure_secure_client(self.face_socket)
                    
                face_address = f"tcp://{face_host}:{face_port}"
                self.face_socket.connect(face_address)
                self.face_socket.setsockopt_string(zmq.SUBSCRIBE, "")
                logger.info(f"Connected to FaceRecognitionAgent at {face_address}")
                self.health_status["connections"]["face_recognition"] = True
                
                # Start face recognition listener thread
                self.face_thread = threading.Thread(target=self.face_recognition_listener, daemon=True)
                self.face_thread.start()
            else:
                logger.warning("FaceRecognitionAgent not found in service discovery")
            
            # Connect to TTS services
            self._connect_to_tts_services()
            
        except Exception as e:
            logger.error(f"Error connecting to services: {e}")
    
    def _connect_to_tts_services(self):
        """Connect to TTS-related services using service discovery"""
        try:
            # Defensive: ensure health_status is a dict with 'connections' dict
            if not isinstance(self.health_status, dict) or 'connections' not in self.health_status:
                self.health_status = {
                    "status": "ok",
                    "service": "responder",
                    "last_check": time.time(),
                    "connections": {
                        "tts": False,
                        "tts_cache": False,
                        "tts_agent": False,
                        "face_recognition": False
                    }
                }
            # Connect to StreamingTtsAgent
            streaming_tts_address = get_service_address("StreamingTtsAgent")
            if streaming_tts_address:
                self.streaming_tts_socket = self.context.socket(zmq.REQ)
                if is_secure_zmq_enabled():
                    self.streaming_tts_socket = configure_secure_client(self.streaming_tts_socket)
                self.streaming_tts_socket.setsockopt(zmq.RCVTIMEO, self.ZMQ_REQUEST_TIMEOUT)
                self.streaming_tts_socket.connect(streaming_tts_address)
                logger.info(f"Connected to StreamingTtsAgent at {streaming_tts_address}")
                self.health_status["connections"]["tts"] = True
            else:
                logger.warning("StreamingTtsAgent not found in service discovery")
            
            # Connect to TTSCache
            tts_cache_address = get_service_address("TTSCache")
            if tts_cache_address:
                self.tts_cache_socket = self.context.socket(zmq.REQ)
                if is_secure_zmq_enabled():
                    self.tts_cache_socket = configure_secure_client(self.tts_cache_socket)
                self.tts_cache_socket.setsockopt(zmq.RCVTIMEO, self.ZMQ_REQUEST_TIMEOUT)
                self.tts_cache_socket.connect(tts_cache_address)
                logger.info(f"Connected to TTSCache at {tts_cache_address}")
                self.health_status["connections"]["tts_cache"] = True
            else:
                logger.warning("TTSCache not found in service discovery")
            
            # Connect to TTSConnector
            tts_connector_address = get_service_address("StreamingTTSAgent")
            if tts_connector_address:
                self.tts_socket = self.context.socket(zmq.REQ)
                if is_secure_zmq_enabled():
                    self.tts_socket = configure_secure_client(self.tts_socket)
                self.tts_socket.setsockopt(zmq.RCVTIMEO, self.ZMQ_REQUEST_TIMEOUT)
                self.tts_socket.connect(tts_connector_address)
                logger.info(f"Connected to StreamingTTSAgent at {tts_connector_address}")
                self.health_status["connections"]["tts_agent"] = True
            else:
                logger.warning("StreamingTTSAgent not found in service discovery")
                
        except Exception as e:
            logger.error(f"Error connecting to TTS services: {e}")

    def _refresh_service_connections(self):
        """Periodically refresh service connections to handle changes"""
        while self.running:
            try:
                time.sleep(300)  # Refresh every 5 minutes
                logger.info("Refreshing service connections")
                self._connect_to_services()
            except Exception as e:
                logger.error(f"Error refreshing service connections: {e}")
    
    def _load_tts_model(self):
        """Background loader for XTTS model."""
        if not TTS_AVAILABLE:
            logging.info("[Responder] TTS library not available; speech synthesis disabled.")
            self.tts_ready.set()
            return
        try:
            self.tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
            logging.info("[Responder] XTTS model loaded successfully.")
        except Exception as e:
            logging.error(f"[Responder] Failed to load XTTS model: {e}")
        finally:
            self.tts_ready.set()
        
    def face_recognition_listener(self):
        """Background thread to listen for face recognition events"""
        logging.info("[Responder] Face recognition listener started")
        while self.running:
            try:
                msg = self.face_socket.recv_string(flags=zmq.NOBLOCK)
                data = json.loads(msg)
                
                # Handle different event types from face recognition agent
                event_type = data.get("event")
                
                if event_type == "face_detected":
                    name = data.get("name")
                    timestamp = data.get("timestamp")
                    emotion = data.get("emotion", "neutral")
                    confidence = data.get("confidence", 0.0)
                    
                    # Update detected faces
                    self.detected_faces[name] = {
                        "last_seen": timestamp,
                        "emotion": emotion,
                        "confidence": confidence
                    }
                    
                    # If high confidence, set as current speaker
                    if confidence > 0.8 and name != "Unknown":
                        self.current_speaker = name
                    
                    logging.info(f"[Responder] Face detected: {name} with emotion {emotion}")
                    
            except zmq.Again:
                # No message available, continue
                pass
            except Exception as e:
                logging.error(f"[Responder] Error in face recognition listener: {e}")
            
            time.sleep(0.1)  # Small sleep to prevent CPU hogging

    def _interrupt_listener(self):
        """Listen for interrupt signals"""
        logger.info("Starting interrupt listener")
        while self.running:
            try:
                msg = self.interrupt_socket.recv(flags=zmq.NOBLOCK)
                data = pickle.loads(msg)
                if data.get('type') == 'interrupt':
                    logger.info("Received interrupt signal")
                    self.interrupt_flag.set()
                    # Stop any ongoing TTS processing
                    self._send_stop_to_tts_services()
            except zmq.Again:
                time.sleep(0.05)  # Small sleep to avoid tight loop
            except Exception as e:
                logger.error(f"Error in interrupt listener: {e}")
                time.sleep(1)  # Longer sleep on error

    def _send_stop_to_tts_services(self):
        """Send stop command to all TTS services"""
        stop_command = {"command": "stop"}
        
        # Try to stop StreamingTTSAgent
        if self.streaming_tts_socket:
            try:
                self.streaming_tts_socket.send_json(stop_command, flags=zmq.NOBLOCK)
                logger.info("Sent stop command to StreamingTTSAgent")
            except Exception as e:
                logger.error(f"Failed to send stop command to StreamingTTSAgent: {e}")
                
        # Try to stop TTSAgent
        if self.tts_socket:
            try:
                self.tts_socket.send_json(stop_command, flags=zmq.NOBLOCK)
                logger.info("Sent stop command to TTSAgent")
            except Exception as e:
                logger.error(f"Failed to send stop command to TTSAgent: {e}")
                
        # Try to stop TTSConnector
        if self.tts_connector_socket:
            try:
                self.tts_connector_socket.send_json(stop_command, flags=zmq.NOBLOCK)
                logger.info("Sent stop command to TTSConnector")
            except Exception as e:
                logger.error(f"Failed to send stop command to TTSConnector: {e}")

    def _start_interrupt_thread(self):
        """Start the interrupt listener thread"""
        self.interrupt_thread = threading.Thread(target=self._interrupt_listener, daemon=True)
        self.interrupt_thread.start()

    def process_message(self):
        """Process incoming messages with enhanced language handling"""
        try:
            message = self.socket.recv_string(flags=zmq.NOBLOCK)
            data = json.loads(message)

            # Extract message data
            text = data.get("text", "")
            emotion = data.get("emotion")
            language = data.get("language")
            user = data.get("user")
            original_language = data.get("original_language")  # Original language of user input
            original_text = data.get("original_text", "")    # Original text before translation
            
            # Process the message with enhanced language awareness
            self.speak(
                text, 
                emotion=emotion, 
                language=language, 
                user=user, 
                original_language=original_language
            )
            
            # Update health status
            self.last_health_check = time.time()
            self.health_status = "OK"
                
            if self.interrupt_flag.is_set():
                logger.info("Interrupt flag detected. Clearing audio queue.")
                with self.audio_queue.mutex:
                    self.audio_queue.queue.clear()
                self.interrupt_flag.clear()
                
            return True
            
        except zmq.Again:
            # No message available
            return False
        except json.JSONDecodeError:
            logging.error("[Responder] Invalid JSON received")
            self.health_status = "ERROR: Invalid JSON"
            return False
        except Exception as e:
            logging.error(f"[Responder] Error processing message: {e}")
            self.health_status = f"ERROR: {str(e)}"
            return False

    def speak(self, text, emotion=None, language=None, user=None, face_emotion=None, original_language=None):
        """Generate speech from text using the appropriate TTS service"""
        if not text:
            logger.warning("Empty text provided to speak method, ignoring")
            return False
            
        # Check for interrupt flag
        if self.interrupt_flag.is_set():
            logger.info("Interrupt flag is set, not speaking")
            self.interrupt_flag.clear()
            return False
            
        try:
            # Use service discovery to find the best available TTS service
            if self.streaming_tts_socket:
                # Prefer streaming TTS for real-time response
                tts_request = {
                    "text": text,
                    "emotion": emotion,
                    "language": language,
                    "user": user
                }
                
                # Send request to streaming TTS
                logger.info(f"Sending to StreamingTTSAgent: '{text[:50]}...' with emotion {emotion}")
                self.streaming_tts_socket.send_json(tts_request)
                
                # Set up poller for timeout
                poller = zmq.Poller()
                poller.register(self.streaming_tts_socket, zmq.POLLIN)
                
                # Wait for response with timeout
                if poller.poll(self.ZMQ_REQUEST_TIMEOUT):
                    response = self.streaming_tts_socket.recv_json()
                    if isinstance(response, dict):
                        if response.get("status") == "success":
                            logger.info("StreamingTTSAgent successfully processed request")
                            return True
                        else:
                            logger.warning(f"StreamingTTSAgent error: {response.get('message', 'Unknown error')}")
                    else:
                        logger.error(f"StreamingTTSAgent response is not a dict: {response}")
                else:
                    logger.error("Timeout waiting for StreamingTTSAgent response")
                    
                # If we get here, streaming TTS failed, try fallback
                
            # Try regular TTS agent as fallback
            if self.tts_socket:
                tts_request = {
                    "text": text,
                    "emotion": emotion,
                    "language": language,
                    "user": user
                }
                
                logger.info(f"Falling back to TTSAgent: '{text[:50]}...'")
                self.tts_socket.send_json(tts_request)
                
                # Set up poller for timeout
                poller = zmq.Poller()
                poller.register(self.tts_socket, zmq.POLLIN)
                
                # Wait for response with timeout
                if poller.poll(self.ZMQ_REQUEST_TIMEOUT):
                    response = self.tts_socket.recv_json()
                    if isinstance(response, dict):
                        if response.get("status") == "success":
                            logger.info("TTSAgent successfully processed request")
                            return True
                        else:
                            logger.warning(f"TTSAgent error: {response.get('message', 'Unknown error')}")
                    else:
                        logger.error(f"TTSAgent response is not a dict: {response}")
                else:
                    logger.error("Timeout waiting for TTSAgent response")
                    
            # If all TTS services fail, log the text as last resort
            logger.warning(f"All TTS services failed. Text was: {text}")
            return False
            
        except Exception as e:
            logger.error(f"Error in speak method: {e}")
            return False

    def _show_visual_feedback(self, text, color, duration):
        """
        Display visual feedback for the spoken text using a transient Tk window.
        Falls back gracefully if tkinter is not available or a display is not
        present (e.g. running headless).
        """
        if not self.VISUAL_FEEDBACK_ENABLED:
            return
        try:
            import tkinter as tk
            import threading

            def show_overlay():
                root = tk.Tk()
                root.overrideredirect(True)
                root.attributes("-topmost", True)
                root.attributes("-alpha", 0.8)
                screen_width = root.winfo_screenwidth()
                screen_height = root.winfo_screenheight()
                window_width = min(screen_width - 100, len(text) * 10 + 100)
                window_height = int(config.get("get")('window_height', 100))
                x = (screen_width - window_width) // 2
                y = screen_height - window_height - 50
                root.geometry(f"{window_width}x{window_height}+{x}+{y}")

                frame = tk.Frame(root, bg=color)
                frame.pack(fill=tk.BOTH, expand=True)
                label = tk.Label(
                    frame,
                    text=text,
                    font=("Arial", 14),
                    bg=color,
                    fg="#000000" if self._is_light_color(color) else "#FFFFFF",
                    wraplength=window_width - 20,
                )
                label.pack(pady=20)
                root.after(int(duration * 1000), root.destroy)
                root.mainloop()

            threading.Thread(target=show_overlay, daemon=True).start()
        except ImportError as e:
            print(f"Import error: {e}")
        except Exception as e:
            logging.error(f"[Responder] Visual feedback error: {e}")

    def _is_light_color(self, hex_color):
        """Return True if the supplied hex color is considered light."""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        brightness = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
        return brightness > 0.5

    def _modulate_audio(
        self,
        audio,
        speed=None,
        pitch=None,
        energy=None,
        vibrato=None,
        breathiness=None,
    ):
        """Simple audio post-processing placeholder.

        For now only applies a volume (energy) adjustment and clips the output.
        """
        # Use config or _agent_args for defaults if not provided
        if speed is None:
            speed = float(getattr(self, 'speed', config.get("get")('speed', 1.0)))
        if pitch is None:
            pitch = float(getattr(self, 'pitch', config.get("get")('pitch', 1.0)))
        if energy is None:
            energy = float(getattr(self, 'energy', config.get("get")('energy', 1.0)))
        if vibrato is None:
            vibrato = float(getattr(self, 'vibrato', config.get("get")('vibrato', 0.0)))
        if breathiness is None:
            breathiness = float(getattr(self, 'breathiness', config.get("get")('breathiness', 0.0)))

        # TODO: re-implement full DSP chain (speed, pitch, etc.) if necessary.
        audio = audio * energy
        return np.clip(audio, -1.0, 1.0)

    # --------------------------------------------------------------------- #
    #                        PUBLIC AGENT INTERFACE                         #
    # --------------------------------------------------------------------- #
    def generate_response(self, text, user=None, language=None, original_language=None):
        """Generate a textual response. Currently echoes the input."""
        return f"I received your message: {text}"

    def start(self):
        """Start the agent's main loop."""
        logging.info("[Responder] Agent started.")
        self.running = True
        try:
            while self.running:
                self.process_message()
                # Simple heartbeat and cleanup
                if time.time() - self.last_health_check > 60:
                    self.health_check()
                self.cleanup_old_face_data()
                time.sleep(0.05)
        except KeyboardInterrupt:
            logging.info("[Responder] KeyboardInterrupt received. Stopping...")
        finally:
            self.stop()

    def cleanup_old_face_data(self):
        now = time.time()
        expired = [
            name for name, info in self.detected_faces.items()
            if now - info.get("last_seen", 0) > 300
        ]
        for name in expired:
            self.detected_faces.pop(name, None)
        if expired:
            logging.info(f"[Responder] Cleaned up {len(expired)} expired face entries")

    def add_user_voice_profile(self, user, profile_data):
        if not user:
            logging.warning("[Responder] Cannot add voice profile without user name")
            return False
        profile = {
            "speed_modifier": 1.0,
            "pitch_modifier": 1.0,
            "energy_modifier": 1.0,
            "vibrato_modifier": 1.0,
            "breathiness_modifier": 1.0,
            "voice": None,
        }
        profile.update(profile_data or {})
        self.user_voice_profiles[user] = profile
        logging.info(f"[Responder] Updated voice profile for user {user}: {profile}")
        return True

    def stop(self):
        """Stop the agent and clean up resources"""
        logger.info("Stopping ResponderAgent")
        self.running = False
        
        # Send stop command to TTS services
        self._send_stop_to_tts_services()
        
        # Close all sockets
        sockets_to_close = [
            'socket', 'interrupt_socket', 'face_socket', 
            'streaming_tts_socket', 'tts_socket', 'tts_connector_socket'
        ]
        
        for socket_name in sockets_to_close:
            if hasattr(self, socket_name):
                socket = getattr(self, socket_name)
                if socket:
                    try:
                        logger.info(f"Closed {socket_name}")
                    except Exception as e:
                        logger.error(f"Error closing {socket_name}: {e}")
        
        # Terminate ZMQ context
        if self.context:
            try:
        # TODO-FIXME – removed stray 'self.' (O3 Pro Max fix)
                logger.info("Terminated ZMQ context")
            except Exception as e:
                logger.error(f"Error terminating ZMQ context: {e}")
        
        logger.info("ResponderAgent stopped")

    def hot_reload_watcher(self):
        last_voice = self.voice
        while self.running:
            time.sleep(5)
            try:
                if self.voice != last_voice:
                    logging.info("[Responder] Voice hot reloaded.")
                    last_voice = self.voice
            except Exception as e:
                logging.error(f"[Responder] Hot reload watcher error: {e}")

    def health_check(self):
        self.last_health_check = time.time()
        logging.debug("[Responder] Health check OK")
        return {"status": self.health_status}

    def _monitor_health(self):
        """Monitor health of all connections"""
        while self.running:
            try:
                # Check TTS service
                self.tts_socket.send_json({"action": "health_check"})
                if self.tts_socket.poll(HEALTH_CHECK_TIMEOUT * 1000):
                    response = self.tts_socket.recv_json()
                    self.health_status["connections"]["tts"] = response.get("status") == "ok"
                else:
                    self.health_status["connections"]["tts"] = False
                
                # Check TTS Cache
                self.tts_cache_socket.send_json({"action": "health_check"})
                if self.tts_cache_socket.poll(HEALTH_CHECK_TIMEOUT * 1000):
                    response = self.tts_cache_socket.recv_json()
                    self.health_status["connections"]["tts_cache"] = response.get("status") == "ok"
                else:
                    self.health_status["connections"]["tts_cache"] = False
                
                # Check TTS Connector
                self.tts_connector_socket.send_json({"action": "health_check"})
                if self.tts_connector_socket.poll(HEALTH_CHECK_TIMEOUT * 1000):
                    response = self.tts_connector_socket.recv_json()
                    self.health_status["connections"]["tts_agent"] = response.get("status") == "ok"
                else:
                    self.health_status["connections"]["tts_agent"] = False
                
                # Update overall health status
                all_healthy = all(self.health_status["connections"].values())
                self.health_status["status"] = "ok" if all_healthy else "degraded"
                self.health_status["last_check"] = time.time()
                
                # Log health status
                if not all_healthy:
                    logging.warning(f"[Responder] Health check failed: {self.health_status}")
                
                time.sleep(HEALTH_CHECK_INTERVAL)
                
            except Exception as e:
                logging.error(f"[Responder] Health monitoring error: {e}")
                time.sleep(HEALTH_CHECK_INTERVAL)

    def _get_health_status(self):
        """Overrides the base method to add agent-specific health metrics."""
        base_status = super()._get_health_status()
        specific_metrics = {
            "responder_status": "active",
            "responses_generated": getattr(self, 'responses_generated', 0),
            "last_response_time": getattr(self, 'last_response_time', 'N/A')
        }
        base_status.update(specific_metrics)
        return base_status

# ------------------------------------------------------------------------- #
#                         SCRIPT ENTRY POINT                                #
# ------------------------------------------------------------------------- #
if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = Responder()
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
