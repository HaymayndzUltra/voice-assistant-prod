from src.core.base_agent import BaseAgent
"""
Enhanced Streaming Speech Recognition Module
Combines features from both streaming_speech_recognition.py and streaming_whisper_asr.py
Features:
- Wake word detection integration
- Dynamic model management
- Real-time streaming
- Noise reduction
- Language detection
- Multiple language support
"""

import zmq
import pickle
import numpy as np
import whisper
import time
import threading
import logging
import os
import tempfile
import wave
import json
from collections import deque
from datetime import datetime
import uuid
import socket
import sys
import noisereduce as nr
from scipy import signal
from pathlib import Path
from queue import Queue
import psutil
import traceback

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Import dynamic model management
from utils.config_parser import parse_agent_args
from utils.service_discovery_client import discover_service, register_service
_agent_args = parse_agent_args()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"{project_root}/logs/streaming_speech_recognition.log")
    ])
logger = logging.getLogger("StreamingSpeechRecognition")

# Check for secure ZMQ configuration
SECURE_ZMQ = os.environ.get("SECURE_ZMQ", "0") == "1"

# ZMQ Configuration - Use service discovery instead of hardcoded ports
ZMQ_SUB_PORT = int(getattr(_agent_args, 'sub_port', 6578))  # Subscribe to clean audio from FusedAudioPreprocessor
ZMQ_PUB_PORT = int(getattr(_agent_args, 'pub_port', 6580))  # Transcriptions to LanguageAndTranslationCoordinator
ZMQ_HEALTH_PORT = int(getattr(_agent_args, 'health_port', 6582))  # Health check port
ZMQ_WAKE_WORD_PORT = int(getattr(_agent_args, 'wake_word_port', 6577))  # Wake word events from WakeWordDetector
ZMQ_VAD_PORT = int(getattr(_agent_args, 'vad_port', 6579))  # VAD events

# Audio Settings
SAMPLE_RATE = 48000
CHUNK_DURATION = 0.2  # seconds
BUFFER_SECONDS = 2.0  # Audio buffer for inference
MIN_TRANSCRIBE_SECONDS = 0.5
MAX_BUFFER_SECONDS = 2.0
SILENCE_THRESHOLD = 0.02
SILENCE_RESET_TIME = 0.5

# Noise Reduction Settings
NOISE_REDUCTION_ENABLED = True
NOISE_REDUCTION_STRENGTH = 0.75
NOISE_REDUCTION_FREQ_MIN = 20
NOISE_REDUCTION_FREQ_MAX = 20000

# Language Detection Settings
SUPPORTED_LANGUAGES = ["en", "tl", "fil"]  # English, Tagalog, Filipino
LANGUAGE_DETECTION_CONFIDENCE_THRESHOLD = 0.5

# Resource management config (should be loaded from config in production)
DEFAULT_BATCH_SIZE = 8
MAX_BATCH_SIZE = 16
ENABLE_DYNAMIC_QUANTIZATION = True
TENSORRT_ENABLED = False  # Placeholder for future TensorRT integration

class ResourceManager:
    def __init__(self):
        self.default_batch_size = DEFAULT_BATCH_SIZE
        self.max_batch_size = MAX_BATCH_SIZE
        self.enable_dynamic_quantization = ENABLE_DYNAMIC_QUANTIZATION

    def get_system_load(self):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        try:
            import torch
            gpu = torch.cuda.memory_allocated() / torch.cuda.max_memory_allocated() * 100
        except Exception:
            gpu = 0
        return cpu, mem, gpu

    def get_batch_size(self):
        cpu, mem, gpu = self.get_system_load()
        if max(cpu, mem, gpu) > 80:
            return max(1, self.default_batch_size // 2)
        elif max(cpu, mem, gpu) < 40:
            return min(self.max_batch_size, self.default_batch_size * 2)
        else:
            return self.default_batch_size

    def get_quantization(self):
        if not self.enable_dynamic_quantization:
            return 'float16'
        cpu, mem, gpu = self.get_system_load()
        if max(cpu, mem, gpu) > 80:
            return 'int8'
        else:
            return 'float16'

    def use_tensorrt(self):
        return TENSORRT_ENABLED

class StreamingSpeechRecognition(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="StreamingSpeechRecognition")
        """Initialize the enhanced speech recognition system."""
        self._running = False
        self._thread = None
        self.health_thread = None
        self.process_thread = None
        
        # Initialize ZMQ context
        self.zmq_context = zmq.Context()
        
        # Initialize sockets
        self._init_sockets()
        
        # Initialize audio processing
        self.audio_queue = Queue()
        self.buffer = []
        self.buffer_size = int(BUFFER_SECONDS / CHUNK_DURATION)
        
        # Model management is now delegated to ModelManagerAgent
        self.model_manager_socket = None
        
        # Initialize state
        self.wake_word_detected = False
        self.last_wake_word_time = 0
        self.wake_word_timeout = 5.0  # seconds
        self.current_language = 'en'
        
        # VAD integration
        self.vad_speech_active = False
        self.vad_confidence = 0.0
        self.vad_last_update = 0
        
        # Initialize ResourceManager
        self.resource_manager = ResourceManager()
        
        # Initialize connection to ModelManagerAgent
        self._connect_to_model_manager()
        
        logger.info("Enhanced Streaming Speech Recognition initialized")
    
    def _init_sockets(self):
        """Initialize all ZMQ sockets."""
        try:
            # Discover FusedAudioPreprocessor for clean audio
            audio_preprocessor = discover_service("FusedAudioPreprocessor")
            if audio_preprocessor and audio_preprocessor.get("status") == "SUCCESS":
                preprocessor_info = audio_preprocessor.get("payload", {})
                preprocessor_host = preprocessor_info.get("host", _agent_args.host)
                preprocessor_port = preprocessor_info.get("clean_audio_pub_port", ZMQ_SUB_PORT)
                vad_port = preprocessor_info.get("vad_port", ZMQ_VAD_PORT)
                logger.info(f"Discovered FusedAudioPreprocessor at {preprocessor_host}:{preprocessor_port}")
            else:
                logger.warning("Could not discover FusedAudioPreprocessor, using configured host and port")
                preprocessor_host = _agent_args.host
                preprocessor_port = ZMQ_SUB_PORT
                vad_port = ZMQ_VAD_PORT
            
            # Discover WakeWordDetector
            wake_word_detector = discover_service("StreamingAudioCapture")
            if wake_word_detector and wake_word_detector.get("status") == "SUCCESS":
                wake_word_info = wake_word_detector.get("payload", {})
                wake_word_host = wake_word_info.get("host", _agent_args.host)
                wake_word_port = wake_word_info.get("port", ZMQ_WAKE_WORD_PORT)
                logger.info(f"Discovered WakeWordDetector at {wake_word_host}:{wake_word_port}")
            else:
                logger.warning("Could not discover WakeWordDetector, using configured host and port")
                wake_word_host = _agent_args.host
                wake_word_port = ZMQ_WAKE_WORD_PORT
            
            # Subscribe to cleaned audio
            self.sub_socket = self.zmq_context.socket(zmq.SUB)
            
            # Apply secure ZMQ if enabled
            if SECURE_ZMQ:
                try:
                    from src.network.secure_zmq import secure_client_socket, start_auth
                    start_auth()
                    self.sub_socket = secure_client_socket(self.sub_socket)
                    logger.info("Applied secure ZMQ to subscriber socket")
                except Exception as e:
                    logger.error(f"Failed to apply secure ZMQ to subscriber socket: {e}")
            
            self.sub_socket.connect(f"tcp://{preprocessor_host}:{preprocessor_port}")
            self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            logger.info(f"Connected to audio preprocessor at tcp://{preprocessor_host}:{preprocessor_port}")
            
            # Subscribe to wake word events
            self.wake_word_socket = self.zmq_context.socket(zmq.SUB)
            
            # Apply secure ZMQ if enabled
            if SECURE_ZMQ:
                try:
                    from src.network.secure_zmq import secure_client_socket
                    self.wake_word_socket = secure_client_socket(self.wake_word_socket)
                    logger.info("Applied secure ZMQ to wake word subscriber socket")
                except Exception as e:
                    logger.error(f"Failed to apply secure ZMQ to wake word subscriber socket: {e}")
            
            self.wake_word_socket.connect(f"tcp://{wake_word_host}:{wake_word_port}")
            self.wake_word_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            logger.info(f"Connected to wake word detector at tcp://{wake_word_host}:{wake_word_port}")
            
            # Subscribe to VAD events
            self.vad_socket = self.zmq_context.socket(zmq.SUB)
            
            # Apply secure ZMQ if enabled
            if SECURE_ZMQ:
                try:
                    from src.network.secure_zmq import secure_client_socket
                    self.vad_socket = secure_client_socket(self.vad_socket)
                    logger.info("Applied secure ZMQ to VAD subscriber socket")
                except Exception as e:
                    logger.error(f"Failed to apply secure ZMQ to VAD subscriber socket: {e}")
            
            self.vad_socket.connect(f"tcp://{preprocessor_host}:{vad_port}")
            self.vad_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            logger.info(f"Connected to VAD events at tcp://{preprocessor_host}:{vad_port}")
            
            # Publish transcriptions
            self.pub_socket = self.zmq_context.socket(zmq.PUB)
            
            # Apply secure ZMQ if enabled
            if SECURE_ZMQ:
                try:
                    from src.network.secure_zmq import secure_server_socket
                    self.pub_socket = secure_server_socket(self.pub_socket)
                    logger.info("Applied secure ZMQ to publisher socket")
                except Exception as e:
                    logger.error(f"Failed to apply secure ZMQ to publisher socket: {e}")
            
            self.pub_socket.bind(f"tcp://*:{ZMQ_PUB_PORT}")
            logger.info(f"Publishing transcriptions on port {ZMQ_PUB_PORT}")
            
            # Health status
            self.health_socket = self.zmq_context.socket(zmq.PUB)
            
            # Apply secure ZMQ if enabled
            if SECURE_ZMQ:
                try:
                    from src.network.secure_zmq import secure_server_socket
                    self.health_socket = secure_server_socket(self.health_socket)
                    logger.info("Applied secure ZMQ to health publisher socket")
                except Exception as e:
                    logger.error(f"Failed to apply secure ZMQ to health publisher socket: {e}")
            
            self.health_socket.bind(f"tcp://*:{ZMQ_HEALTH_PORT}")
            logger.info(f"Publishing health status on port {ZMQ_HEALTH_PORT}")
            
            # Register with SystemDigitalTwin
            try:
                register_service(
                    name="StreamingSpeechRecognition",
                    port=ZMQ_PUB_PORT,
                    additional_info={
                        "health_port": ZMQ_HEALTH_PORT,
                        "description": "Speech recognition service"
                    }
                )
                logger.info("Registered with SystemDigitalTwin")
            except Exception as e:
                logger.error(f"Failed to register with SystemDigitalTwin: {e}")
            
        except Exception as e:
            logger.error(f"Error initializing ZMQ sockets: {str(e)}")
            raise
    
    def _connect_to_model_manager(self):
        """Connect to the ModelManagerAgent for model management."""
        try:
            # Discover ModelManagerAgent
            model_manager = discover_service("ModelManagerAgent")
            if model_manager and model_manager.get("status") == "SUCCESS":
                model_manager_info = model_manager.get("payload", {})
                model_manager_host = model_manager_info.get("host", _agent_args.host)
                model_manager_port = model_manager_info.get("port", 5570)
                logger.info(f"Discovered ModelManagerAgent at {model_manager_host}:{model_manager_port}")
                
                # Create socket for ModelManagerAgent
                self.model_manager_socket = self.zmq_context.socket(zmq.REQ)
                self.model_manager_socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
                
                # Apply secure ZMQ if enabled
                if SECURE_ZMQ:
                    try:
                        from src.network.secure_zmq import secure_client_socket
                        self.model_manager_socket = secure_client_socket(self.model_manager_socket)
                        logger.info("Applied secure ZMQ to model manager socket")
                    except Exception as e:
                        logger.error(f"Failed to apply secure ZMQ to model manager socket: {e}")
                
                self.model_manager_socket.connect(f"tcp://{model_manager_host}:{model_manager_port}")
                logger.info(f"Connected to ModelManagerAgent at tcp://{model_manager_host}:{model_manager_port}")
                
                # Request model loading
                self._request_model_loading("whisper-large-v3", "high")
            else:
                logger.error("Could not discover ModelManagerAgent, speech recognition will not work properly")
                self.model_manager_socket = None
        except Exception as e:
            logger.error(f"Error connecting to ModelManagerAgent: {str(e)}")
            self.model_manager_socket = None
    
    def _request_model_loading(self, model_id, priority="medium"):
        """Request model loading from ModelManagerAgent."""
        if not self.model_manager_socket:
            logger.error("No connection to ModelManagerAgent, cannot load model")
            return False
        
        try:
            request = {
                "command": "LOAD_MODEL",
                "model_id": model_id,
                "priority": priority,
                "source": "StreamingSpeechRecognition"
            }
            
            self.model_manager_socket.send_json(request)
            response = self.model_manager_socket.recv_json()
            
            if response.get("status") == "success":
                logger.info(f"Successfully requested loading of model {model_id}")
                return True
            else:
                logger.error(f"Failed to load model {model_id}: {response.get('message', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"Error requesting model loading: {str(e)}")
            return False
    
    def _check_wake_word_events(self):
        """Check for wake word events."""
        try:
            # Non-blocking check for wake word events
            try:
                event = self.wake_word_socket.recv_json(flags=zmq.NOBLOCK)
                if event.get('type') == 'wake_word_detected':
                    self.wake_word_detected = True
                    self.last_wake_word_time = time.time()
                    logger.info(f"Wake word detected with confidence {event.get('confidence', 0.0):.2f}")
            except zmq.Again:
                pass  # No wake word event available
            
            # Check if wake word timeout has expired
            if self.wake_word_detected and (time.time() - self.last_wake_word_time) > self.wake_word_timeout:
                self.wake_word_detected = False
                logger.info("Wake word timeout expired")
                
        except Exception as e:
            logger.error(f"Error checking wake word events: {str(e)}")
    
    def _check_vad_events(self):
        """Check for VAD events."""
        try:
            # Non-blocking check for VAD events
            try:
                event = self.vad_socket.recv_json(flags=zmq.NOBLOCK)
                
                # Check for error message from VAD
                if event.get('status') == 'error':
                    logger.warning(f"Received error from VAD: {event.get('message')}")
                    # Log but don't propagate VAD errors unless critical
                    if event.get('error_type') in ['AgentShutdownError', 'ModelLoadError']:
                        # Forward critical errors
                        self.pub_socket.send_json(event)
                    return
                
                event_type = event.get('type')
                if event_type == 'speech_start':
                    self.vad_speech_active = True
                    self.vad_confidence = event.get('probability', 0.5)
                    self.vad_last_update = time.time()
                    logger.info(f"VAD detected speech start, confidence: {self.vad_confidence:.2f}")
                elif event_type == 'speech_end':
                    self.vad_speech_active = False
                    self.vad_confidence = event.get('probability', 0.0)
                    self.vad_last_update = time.time()
                    logger.info(f"VAD detected speech end, confidence: {self.vad_confidence:.2f}")
                elif event_type == 'speech_ongoing':
                    self.vad_confidence = event.get('probability', 0.5)
                    self.vad_last_update = time.time()
            except zmq.Again:
                pass  # No VAD event available
            
            # Check if VAD state is stale
            if (time.time() - self.vad_last_update) > 5.0:  # 5 seconds timeout
                self.vad_speech_active = False  # Reset if no updates
                
        except Exception as e:
            logger.error(f"Error checking VAD events: {str(e)}")
            # Non-critical error, don't propagate
    
    def apply_noise_reduction(self, audio_data):
        """Apply additional noise reduction if needed."""
        try:
            if not NOISE_REDUCTION_ENABLED or audio_data is None:
                return audio_data
                
            # Start timing for performance metrics
            start_time = time.time()
            
            # Apply noise reduction
            denoised = nr.reduce_noise(
                y=audio_data,
                sr=SAMPLE_RATE,
                stationary=True,
                prop_decrease=NOISE_REDUCTION_STRENGTH
            )
            
            # Apply bandpass filter
            sos = signal.butter(10, [NOISE_REDUCTION_FREQ_MIN, NOISE_REDUCTION_FREQ_MAX], 'bandpass', fs=SAMPLE_RATE, output='sos')
            filtered = signal.sosfilt(sos, denoised)
            
            # Calculate and log the duration
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"PERF_METRIC: [StreamingSpeechRecognition] - [NoiseReduction] - Duration: {duration_ms:.2f}ms")
            
            return filtered
        except Exception as e:
            logger.error(f"Error in noise reduction: {str(e)}")
            
            # Create standardized error message
            error_message = {
                "status": "error",
                "error_type": "AudioProcessingError",
                "source_agent": "streaming_speech_recognition.py",
                "message": f"Failed to apply noise reduction: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "audio_data_length": len(audio_data) if audio_data is not None else 0
                }
            }
            
            # Log error but don't propagate immediately as this is non-critical
            # Return original audio as fallback
            return audio_data
    
    def detect_language(self, audio_data):
        """Detect the language of the audio."""
        try:
            # This is a simplified language detection that would be replaced with a real model
            # For now, always return English with high confidence
            # TODO: Implement real language detection
            
            # Start timing for performance metrics
            start_time = time.time()
            
            # Placeholder for actual language detection
            # In a real implementation, this would use a language identification model
            
            # For now, we'll just return English with high confidence
            detected_lang = 'en'
            confidence = 0.95
            
            # Calculate and log the duration
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"PERF_METRIC: [StreamingSpeechRecognition] - [LanguageDetection] - Duration: {duration_ms:.2f}ms")
            
            return detected_lang, confidence
        except Exception as e:
            logger.error(f"Error in language detection: {str(e)}")
            
            # Create standardized error message
            error_message = {
                "status": "error",
                "error_type": "ModelInferenceError",
                "source_agent": "streaming_speech_recognition.py",
                "message": f"Failed to detect language: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            
            # In a critical module like language detection, we should propagate errors
            # but still provide a fallback to keep the system running
            try:
                self.pub_socket.send_json(error_message)
                logger.info("Published language detection error message")
            except Exception as pub_error:
                logger.error(f"Failed to publish error message: {str(pub_error)}")
            
            # Return English as fallback
            return 'en', 0.5
    
    def process_audio_loop(self):
        """Main processing loop for audio data."""
        logger.info("Starting audio processing loop")
        
        while self._running:
            try:
                # Start timing for performance metrics
                start_time = time.time()
                
                # Check for wake word events
                self._check_wake_word_events()
                
                # Check for VAD events
                self._check_vad_events()
                
                # Check for audio input
                try:
                    # Check for incoming message (non-blocking)
                    message = self.sub_socket.recv(flags=zmq.NOBLOCK)
                    
                    # Check if message is a JSON error message
                    try:
                        if message.startswith(b'{"status":"error"'):
                            error_data = json.loads(message)
                            if error_data.get("status") == "error":
                                # Log received error
                                logger.warning(f"Received error from upstream component: {error_data.get('source_agent')} - {error_data.get('message')}")
                                
                                # Forward the error downstream if it's critical
                                if error_data.get("error_type") in [
                                    "SystemError", "ConfigurationError", "NetworkError", 
                                    "ModelLoadError", "ModelInferenceError", "AgentShutdownError"
                                ]:
                                    # Augment the error with our information
                                    error_data["details"] = error_data.get("details", {})
                                    error_data["details"]["forwarded_by"] = "streaming_speech_recognition.py"
                                    self.pub_socket.send_json(error_data)
                                    logger.info(f"Forwarded critical error: {error_data.get('error_type')}")
                                
                                # Continue processing loop
                                continue
                    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                        # Not a JSON message, process as normal audio data
                        pass
                    
                    # Process normal audio data
                    try:
                        # Deserialize message
                        data = pickle.loads(message)
                        
                        # Extract audio chunk
                        audio_chunk = data.get('audio_chunk')
                        sample_rate = data.get('sample_rate', SAMPLE_RATE)
                        
                        # Check for empty audio
                        if audio_chunk is None or len(audio_chunk) == 0:
                            logger.warning("Received empty audio chunk, skipping")
                            error_message = {
                                "status": "error",
                                "error_type": "AudioProcessingError",
                                "source_agent": "streaming_speech_recognition.py",
                                "message": "Received empty audio chunk",
                                "timestamp": datetime.now().isoformat()
                            }
                            self.pub_socket.send_json(error_message)
                            continue
                        
                        # Apply additional noise reduction if needed
                        if NOISE_REDUCTION_ENABLED:
                            audio_chunk = self.apply_noise_reduction(audio_chunk)
                        
                        # Add to audio queue
                        self.audio_queue.put(audio_chunk)
                        
                        # Process queue when:
                        # 1. Wake word is detected
                        # 2. VAD indicates speech is active
                        # 3. Enough audio has accumulated
                        should_process = (
                            self.wake_word_detected or 
                            self.vad_speech_active or 
                            self.audio_queue.qsize() >= self.buffer_size
                        )
                        
                        if should_process and not self.process_thread:
                            # Process in separate thread to avoid blocking
                            self.process_thread = threading.Thread(target=self._process_audio_buffer)
                            self.process_thread.daemon = True
                            self.process_thread.start()
                    
                    except pickle.UnpicklingError as pe:
                        # Handle corrupt data with standardized error
                        error_message = {
                            "status": "error",
                            "error_type": "MessageFormatError",
                            "source_agent": "streaming_speech_recognition.py",
                            "message": f"Failed to unpickle received data: {str(pe)}",
                            "timestamp": datetime.now().isoformat()
                        }
                        self.pub_socket.send_json(error_message)
                        logger.error(f"Unpickling error: {str(pe)}")
                        time.sleep(0.1)
                    
                except zmq.Again:
                    time.sleep(0.01)  # Small sleep when no messages
                    continue
                    
                # Calculate and log the duration if we processed audio
                duration_ms = (time.time() - start_time) * 1000
                logger.info(f"PERF_METRIC: [StreamingSpeechRecognition] - [AudioToTranscript] - Duration: {duration_ms:.2f}ms")
                
            except Exception as e:
                logger.error(f"Error in audio processing loop: {str(e)}")
                
                # Send standardized error message
                try:
                    error_message = {
                        "status": "error",
                        "error_type": "TranscriptionError",
                        "source_agent": "streaming_speech_recognition.py",
                        "message": f"Error in audio processing loop: {str(e)}",
                        "timestamp": datetime.now().isoformat(),
                        "details": {
                            "traceback": str(sys.exc_info()[2])
                        }
                    }
                    self.pub_socket.send_json(error_message)
                except Exception as pub_error:
                    logger.error(f"Failed to publish error message: {str(pub_error)}")
                
                time.sleep(0.1)  # Sleep on error to prevent tight loop
    
    def _cleanup_idle_models(self, current_model_id):
        """
        Instead of directly unloading models, delegate to ModelManagerAgent via VRAMOptimizerAgent.
        This method now just informs the VRAMOptimizerAgent about the current model being used.
        """
        try:
            # Use the existing model manager socket
            if not self.model_manager_socket:
                logger.warning("No connection to ModelManagerAgent, cannot update model usage")
                return
            
            # Send update to ModelManagerAgent about the current model being used
            try:
                request = {
                    "command": "UPDATE_MODEL_USAGE",
                    "model_id": current_model_id,
                    "timestamp": time.time(),
                    "agent": "StreamingSpeechRecognition",
                    "model_type": "stt"
                }
                self.model_manager_socket.send_json(request)
                
                # Try to get response, but don't block if no response
                try:
                    response = self.model_manager_socket.recv_json()
                    logger.debug(f"ModelManagerAgent response: {response}")
                except zmq.error.Again:
                    # Timeout is okay for this non-critical operation
                    pass
                    
            except Exception as e:
                logger.warning(f"Error sending model usage update to ModelManagerAgent: {e}")
                
        except Exception as e:
            logger.error(f"Error in delegated model management: {str(e)}")
    
    def health_broadcast_loop(self):
        """Broadcast health status."""
        while self._running:
            try:
                health_data = {
                    "component": "StreamingSpeechRecognition",
                    "status": "healthy",
                    "model_loaded": hasattr(self, 'model_manager_socket') and len(self.model_manager_socket) > 0,
                    "timestamp": time.time(),
                    "metrics": {
                        "pub_port": ZMQ_PUB_PORT,
                        "health_port": ZMQ_HEALTH_PORT,
                        "buffer_size": len(self.buffer),
                        "current_language": self.current_language,
                        "wake_word_active": self.wake_word_detected,
                        "vad_speech_active": self.vad_speech_active,
                        "vad_confidence": self.vad_confidence,
                        "using_clean_audio": True,  # We're now using the cleaned audio stream
                        "processing_active": self._running
                    }
                }
                self.health_socket.send_json(health_data)
            except Exception as e:
                logger.error(f"Error broadcasting health status: {str(e)}")
            time.sleep(5)
    
    def start(self):
        """Start the speech recognition system."""
        if self._running:
            logger.warning("Speech recognition is already running")
            return
            
        self._running = True
        
        # Start processing thread
        self.process_thread = threading.Thread(target=self.process_audio_loop)
        self.process_thread.daemon = True
        self.process_thread.start()
        
        # Start health monitoring thread
        self.health_thread = threading.Thread(target=self.health_broadcast_loop)
        self.health_thread.daemon = True
        self.health_thread.start()
        
        logger.info("Speech recognition started")
    
    def stop(self):
        """Stop the speech recognition system."""
        self._running = False
        
        if self.process_thread:
            self.process_thread.join(timeout=5)
        if self.health_thread:
            self.health_thread.join(timeout=5)
        
        self.cleanup()
        logger.info("Speech recognition stopped")
    
    def cleanup(self):
        """Clean up resources."""
        try:
            # Close ZMQ sockets
            if hasattr(self, 'sub_socket'):
                self.sub_socket.close()
            
            if hasattr(self, 'pub_socket'):
                self.pub_socket.close()
                
            if hasattr(self, 'health_socket'):
                self.health_socket.close()
                
            if hasattr(self, 'wake_word_socket'):
                self.wake_word_socket.close()
                
            if hasattr(self, 'vad_socket'):
                self.vad_socket.close()
                
            if hasattr(self, 'model_manager_socket'):
                # Notify ModelManagerAgent that we're shutting down
                try:
                    request = {
                        "command": "AGENT_SHUTDOWN",
                        "agent": "StreamingSpeechRecognition",
                        "timestamp": time.time()
                    }
                    self.model_manager_socket.send_json(request)
                    # Don't wait for response during shutdown
                except Exception as e:
                    logger.warning(f"Error notifying ModelManagerAgent of shutdown: {e}")
                
                self.model_manager_socket.close()
            
            # Terminate ZMQ context - do this after all sockets are closed
            if hasattr(self, 'zmq_context'):
                self.zmq_context.term()
            
            logger.info("Resources cleaned up")
        except Exception as e:
            logger.error(f"Error in cleanup: {str(e)}")
            # Even if there's an error, try to terminate the context
            try:
                if hasattr(self, 'zmq_context') and not self.zmq_context.closed:
                    self.zmq_context.term()
            except Exception as term_error:
                logger.error(f"Error terminating ZMQ context: {str(term_error)}")
    
    def run(self):
        """Main run loop."""
        logger.info("Starting speech recognition system...")
        try:
            self.start()
            while self._running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Speech recognition stopped by user")
        finally:
            self.stop()

    def _process_audio_buffer(self):
        """Process the audio buffer and generate transcription."""
        try:
            # Start timing for performance metrics
            start_time = time.time()
            
            # Get audio from queue up to a certain size
            chunks = []
            while not self.audio_queue.empty() and len(chunks) < int(MAX_BUFFER_SECONDS / CHUNK_DURATION):
                chunks.append(self.audio_queue.get())
                self.audio_queue.task_done()
            
            if not chunks:
                self.process_thread = None
                return
            
            # Concatenate audio chunks
            audio_input = np.concatenate(chunks).astype(np.float32)
            
            # Normalize
            audio_input = audio_input / (np.max(np.abs(audio_input)) + 1e-8)
            
            # Resample to 16kHz for Whisper
            try:
                audio_input_16k = whisper.audio.resample_audio(audio_input, SAMPLE_RATE, 16000)
            except Exception as resample_error:
                logger.error(f"Error resampling audio for Whisper: {str(resample_error)}")
                error_message = {
                    "status": "error",
                    "error_type": "AudioProcessingError",
                    "source_agent": "streaming_speech_recognition.py",
                    "message": f"Failed to resample audio for transcription: {str(resample_error)}",
                    "timestamp": datetime.now().isoformat()
                }
                self.pub_socket.send_json(error_message)
                self.process_thread = None
                return
            
            # Detect language
            try:
                detected_lang, confidence = self.detect_language(audio_input_16k)
                self.current_language = detected_lang
            except Exception as lang_error:
                logger.error(f"Error detecting language: {str(lang_error)}")
                error_message = {
                    "status": "error",
                    "error_type": "ModelInferenceError", 
                    "source_agent": "streaming_speech_recognition.py",
                    "message": f"Language detection failed: {str(lang_error)}",
                    "timestamp": datetime.now().isoformat()
                }
                self.pub_socket.send_json(error_message)
                # Default to English
                detected_lang = 'en'
                confidence = 0.5
            
            # Request transcription from ModelManagerAgent
            try:
                if not self.model_manager_socket:
                    raise RuntimeError("No connection to ModelManagerAgent")
                
                # Create a unique request ID
                request_id = str(uuid.uuid4())
                
                # Prepare transcription request
                request = {
                    "command": "TRANSCRIBE_AUDIO",
                    "request_id": request_id,
                    "model_id": "whisper-large-v3",
                    "language": detected_lang,
                    "audio_data": audio_input_16k.tolist(),  # Convert to list for JSON serialization
                    "timestamp": time.time(),
                    "source": "StreamingSpeechRecognition"
                }
                
                # Send request to ModelManagerAgent
                self.model_manager_socket.send_json(request)
                response = self.model_manager_socket.recv_json()
                
                if response.get("status") == "success":
                    result = response.get("result", {})
                    transcript = {
                        "text": result.get("text", "").strip(),
                        "confidence": result.get("confidence", 0.0),
                        "language": detected_lang,
                        "language_confidence": confidence,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Publish transcription if not empty
                    if transcript["text"]:
                        self.pub_socket.send_string(f"TRANSCRIPTION: {json.dumps(transcript)}")
                        logger.info(f"Transcription: {transcript['text']} ({transcript['confidence']:.2f})")
                    else:
                        logger.info("Empty transcription result, nothing to publish")
                    
                    # Update model usage
                    self._cleanup_idle_models("whisper-large-v3")
                else:
                    error_message = {
                        "status": "error",
                        "error_type": "TranscriptionError",
                        "source_agent": "streaming_speech_recognition.py",
                        "message": f"Transcription failed: {response.get('message', 'Unknown error')}",
                        "timestamp": datetime.now().isoformat()
                    }
                    self.pub_socket.send_json(error_message)
            except Exception as transcribe_error:
                logger.error(f"Error transcribing audio: {str(transcribe_error)}")
                error_message = {
                    "status": "error",
                    "error_type": "TranscriptionError",
                    "source_agent": "streaming_speech_recognition.py",
                    "message": f"Transcription failed: {str(transcribe_error)}",
                    "timestamp": datetime.now().isoformat(),
                    "details": {
                        "traceback": traceback.format_exc()
                    }
                }
                self.pub_socket.send_json(error_message)
            
            # Calculate and log the duration
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"PERF_METRIC: [StreamingSpeechRecognition] - [AudioProcessing] - Duration: {duration_ms:.2f}ms")
            
        except Exception as e:
            logger.error(f"Error processing audio buffer: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Send standardized error message
            error_message = {
                "status": "error",
                "error_type": "TranscriptionError",
                "source_agent": "streaming_speech_recognition.py",
                "message": f"Failed to process audio buffer: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "traceback": traceback.format_exc()
                }
            }
            
            try:
                self.pub_socket.send_json(error_message)
                logger.info("Published error message about audio buffer processing failure")
            except Exception as pub_error:
                logger.error(f"Failed to publish error message: {str(pub_error)}")
                
        finally:
            self.process_thread = None

if __name__ == "__main__":
    try:
        asr = StreamingSpeechRecognition()
        asr.run()
    except Exception as e:
        logger.error(f"Speech recognition failed: {e}")
        sys.exit(1)
