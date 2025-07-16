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

# Import with canonical paths
from common.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config
from main_pc_code.utils.service_discovery_client import discover_service, register_service

# Parse agent arguments at module level with canonical import
config = load_config()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ])
logger = logging.getLogger("StreamingSpeechRecognition")

# Check for secure ZMQ configuration
SECURE_ZMQ = os.environ.get("SECURE_ZMQ", "0") == "1"

# ZMQ Configuration - Use service discovery instead of hardcoded ports
ZMQ_SUB_PORT = int(config.get("sub_port", 6578))  # Subscribe to clean audio from FusedAudioPreprocessor
ZMQ_PUB_PORT = int(config.get("pub_port", 6580))  # Transcriptions to LanguageAndTranslationCoordinator
ZMQ_HEALTH_PORT = int(config.get("health_port", 6582))  # Health check port
ZMQ_WAKE_WORD_PORT = int(config.get("wake_word_port", 6577))  # Wake word events from WakeWordDetector
ZMQ_VAD_PORT = int(config.get("vad_port", 6579))  # VAD events

# Audio Settings
SAMPLE_RATE = int(config.get("sample_rate", 48000))
CHUNK_DURATION = float(config.get("chunk_duration", 0.2))  # seconds
BUFFER_SECONDS = float(config.get("buffer_seconds", 2.0))  # Audio buffer for inference
MIN_TRANSCRIBE_SECONDS = float(config.get("min_transcribe_seconds", 0.5))
MAX_BUFFER_SECONDS = float(config.get("max_buffer_seconds", 2.0))
SILENCE_THRESHOLD = float(config.get("silence_threshold", 0.02))
SILENCE_RESET_TIME = float(config.get("silence_reset_time", 0.5))

# Noise Reduction Settings
NOISE_REDUCTION_ENABLED = config.get("noise_reduction_enabled", True)
NOISE_REDUCTION_STRENGTH = float(config.get("noise_reduction_strength", 0.75))
NOISE_REDUCTION_FREQ_MIN = int(config.get("noise_reduction_freq_min", 20))
NOISE_REDUCTION_FREQ_MAX = int(config.get("noise_reduction_freq_max", 20000))

# Language Detection Settings
SUPPORTED_LANGUAGES = config.get("supported_languages", ["en", "tl", "fil"])  # English, Tagalog, Filipino
LANGUAGE_DETECTION_CONFIDENCE_THRESHOLD = float(config.get("language_detection_confidence_threshold", 0.5))

# Resource management config (should be loaded from config in production)
DEFAULT_BATCH_SIZE = int(config.get("default_batch_size", 8))
MAX_BATCH_SIZE = int(config.get("max_batch_size", 16))
ENABLE_DYNAMIC_QUANTIZATION = config.get("enable_dynamic_quantization", True)
TENSORRT_ENABLED = config.get("tensorrt_enabled", False)  # Placeholder for future TensorRT integration

class ResourceManager:
    def __init__(self):
        self.default_batch_size = DEFAULT_BATCH_SIZE
        self.max_batch_size = MAX_BATCH_SIZE
        self.enable_dynamic_quantization = ENABLE_DYNAMIC_QUANTIZATION
        self.context = zmq.Context()
        
        # Error bus connection
        self.error_bus_port = int(config.get("error_bus_port", 7150))
        self.error_bus_host = os.environ.get('PC2_IP', config.get("pc2_ip", "127.0.0.1"))
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)

    def get_system_load(self):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        try:
            import torch
            if torch.cuda.is_available():
                gpu = torch.cuda.memory_allocated() / torch.cuda.max_memory_allocated() * 100 if torch.cuda.max_memory_allocated() > 0 else 0
            else:
                gpu = 0
        except ImportError as e:
            logger.warning(f"Import error: {e}")
            gpu = 0
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
    def __init__(self):
        """Initialize the enhanced speech recognition system."""
        # Call BaseAgent's __init__ first with proper arguments
        agent_name = config.get("name", "StreamingSpeechRecognition")
        agent_port = int(config.get("port", 5707))
        super().__init__(name=agent_name, port=agent_port)

        # Initialize state variables
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

        # Connect to STT service
        self.stt_service_socket = None
        self._connect_to_stt_service()

        # Initialize state
        self.wake_word_detected = False
        self.last_wake_word_time = 0
        self.wake_word_timeout = float(config.get("wake_word_timeout", 5.0))  # seconds
        self.current_language = config.get("default_language", 'en')

        # VAD integration
        self.vad_speech_active = False
        self.vad_confidence = 0.0
        self.vad_last_update = 0

        # Initialize ResourceManager
        self.resource_manager = ResourceManager()
        
        # Initialize RequestCoordinator connection variables
        self.request_coordinator_connection = None
        self.request_coordinator_connected = False
        # Start a background thread to connect to RequestCoordinator when it becomes available
        threading.Thread(target=self._connect_to_request_coordinator, daemon=True).start()

        logger.info("Enhanced Streaming Speech Recognition initialized")
        
        # Get configuration from agent args
        self.port = int(config.get("port", 5707))
        self.bind_address = config.get("bind_address", os.environ.get('BIND_ADDRESS', '0.0.0.0'))
        self.zmq_timeout = int(config.get("zmq_request_timeout", 5000))
        
        self._running = False
        self.start_time = time.time()

    def _connect_to_request_coordinator(self):
        """Attempt to connect to the RequestCoordinator service."""
        while not self.request_coordinator_connected and self._running:
            try:
                # Use service discovery to find the RequestCoordinator
                coordinator_info = discover_service("RequestCoordinator")
                if coordinator_info and isinstance(coordinator_info, dict) and coordinator_info.get("status") == "SUCCESS":
                    host = coordinator_info.get("payload", {}).get("host")
                    port = coordinator_info.get("payload", {}).get("port")
                    
                    # Initialize connection
                    self.request_coordinator_connection = self.zmq_context.socket(zmq.REQ)
                    self.request_coordinator_connection.connect(f"tcp://{host}:{port}")
                    self.request_coordinator_connected = True
                    logger.info(f"Connected to RequestCoordinator at {host}:{port}")
                else:
                    logger.warning("RequestCoordinator not found via service discovery, retrying in 10 seconds")
                    time.sleep(10)
            except Exception as e:
                logger.error(f"Error connecting to RequestCoordinator: {str(e)}")
                time.sleep(10)

    def _init_sockets(self):
        """Initialize all ZMQ sockets."""
        try:
            # Discover FusedAudioPreprocessor for clean audio
            audio_preprocessor = discover_service("FusedAudioPreprocessor")
            if audio_preprocessor and audio_preprocessor.get("status") == "SUCCESS":
                preprocessor_info = audio_preprocessor.get("payload", {})
                preprocessor_host = preprocessor_info.get("host", config.get("host"))
                preprocessor_port = preprocessor_info.get("clean_audio_pub_port", ZMQ_SUB_PORT)
                vad_port = preprocessor_info.get("vad_port", ZMQ_VAD_PORT)
                logger.info(f"Discovered FusedAudioPreprocessor at {preprocessor_host}:{preprocessor_port}")
            else:
                logger.warning("Could not discover FusedAudioPreprocessor, using configured host and port")
                preprocessor_host = config.get("host")
                preprocessor_port = ZMQ_SUB_PORT
                vad_port = ZMQ_VAD_PORT
            
            # Discover WakeWordDetector
            wake_word_detector = discover_service("StreamingAudioCapture")
            if wake_word_detector and wake_word_detector.get("status") == "SUCCESS":
                wake_word_info = wake_word_detector.get("payload", {})
                wake_word_host = wake_word_info.get("host", config.get("host"))
                wake_word_port = wake_word_info.get("port", ZMQ_WAKE_WORD_PORT)
                logger.info(f"Discovered WakeWordDetector at {wake_word_host}:{wake_word_port}")
            else:
                logger.warning("Could not discover WakeWordDetector, using configured host and port")
                wake_word_host = config.get("host")
                wake_word_port = ZMQ_WAKE_WORD_PORT
            
            # Subscribe to cleaned audio
            self.sub_socket = self.zmq_context.socket(zmq.SUB)
            
            # Apply secure ZMQ if enabled
            if SECURE_ZMQ:
                try:
                    from main_pc_code.src.network.secure_zmq import secure_client_socket, start_auth
                except ImportError as e:
                    print(f"Import error: {e}")
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
                    from main_pc_code.src.network.secure_zmq import secure_client_socket
                except ImportError as e:
                    print(f"Import error: {e}")
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
                    from main_pc_code.src.network.secure_zmq import secure_client_socket
                except ImportError as e:
                    print(f"Import error: {e}")
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
                    from main_pc_code.src.network.secure_zmq import secure_server_socket
                except ImportError as e:
                    print(f"Import error: {e}")
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
                    from main_pc_code.src.network.secure_zmq import secure_server_socket
                except ImportError as e:
                    print(f"Import error: {e}")
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
    
    def _connect_to_stt_service(self):
        """Connect to the STT service for transcription."""
        try:
            # Discover STTService
            stt_service = discover_service("STTService")
            if stt_service and isinstance(stt_service, dict) and stt_service.get("status") == "SUCCESS":
                stt_service_info = stt_service.get("payload", {})
                stt_service_host = stt_service_info.get("host", config.get("host"))
                stt_service_port = stt_service_info.get("port", 5800)
                logger.info(f"Discovered STTService at {stt_service_host}:{stt_service_port}")
                
                # Create socket for STTService
                self.stt_service_socket = self.zmq_context.socket(zmq.REQ)
                self.stt_service_socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
                
                # Apply secure ZMQ if enabled
                if SECURE_ZMQ:
                    try:
                        from main_pc_code.src.network.secure_zmq import secure_client_socket
                        if 'secure_client_socket' in locals():
                            self.stt_service_socket = secure_client_socket(self.stt_service_socket)
                            logger.info("Applied secure ZMQ to STT service socket")
                    except Exception as e:
                        logger.error(f"Failed to apply secure ZMQ to STT service socket: {e}")
                
                self.stt_service_socket.connect(f"tcp://{stt_service_host}:{stt_service_port}")
                logger.info(f"Connected to STTService at tcp://{stt_service_host}:{stt_service_port}")
            else:
                logger.error("Could not discover STTService, speech recognition will not work properly")
                self.stt_service_socket = None
        except Exception as e:
            logger.error(f"Error connecting to STTService: {str(e)}")
            self.stt_service_socket = None
    
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
                "error_type": "LanguageDetectionError",
                "source_agent": "streaming_speech_recognition.py",
                "message": f"Failed to detect language: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            
            # Log error but don't propagate immediately as this is non-critical
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
                    "model_loaded": hasattr(self, 'model_manager_socket') and self.model_manager_socket is not None,
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
    
    def health_check(self):
        """Performs a health check on the agent, returning a dictionary with its status."""
        try:
            # Basic health check logic
            is_healthy = self._running  # Assume healthy if running
            
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
                    "wake_word_detected": self.wake_word_detected,
                    "vad_speech_active": self.vad_speech_active,
                    "current_language": self.current_language
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
        """Clean up resources when the agent is stopping."""
        self._running = False
        
        # Stop and join threads
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        
        if self.health_thread and self.health_thread.is_alive():
            self.health_thread.join(timeout=2.0)
        
        if self.process_thread and self.process_thread.is_alive():
            self.process_thread.join(timeout=2.0)
        
        # Close all ZMQ sockets
        if hasattr(self, 'pub_socket') and self.pub_socket:
            self.pub_socket.close()
        
        if hasattr(self, 'sub_socket') and self.sub_socket:
            self.sub_socket.close()
        
        if hasattr(self, 'wake_word_socket') and self.wake_word_socket:
            self.wake_word_socket.close()
        
        if hasattr(self, 'vad_socket') and self.vad_socket:
            self.vad_socket.close()
        
        if hasattr(self, 'health_socket') and self.health_socket:
            self.health_socket.close()
        
        if hasattr(self, 'model_manager_socket') and self.model_manager_socket:
            self.model_manager_socket.close()
        
        if hasattr(self, 'request_coordinator_connection') and self.request_coordinator_connection:
            self.request_coordinator_connection.close()
        
        # Terminate ZMQ context
        if self.zmq_context:
            self.zmq_context.term()
        
        logger.info("StreamingSpeechRecognition cleaned up successfully")

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
            
            # Resample to 16kHz for STT service
            try:
                from scipy import signal
                audio_input_16k = signal.resample_poly(audio_input, 16000, SAMPLE_RATE)
            except Exception as resample_error:
                logger.error(f"Error resampling audio: {str(resample_error)}")
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
            
            # Request transcription from STT service
            try:
                if not self.stt_service_socket:
                    raise RuntimeError("No connection to STT service")
                
                # Prepare transcription request
                request = {
                    "action": "transcribe",
                    "audio_data": audio_input_16k.tolist(),  # Convert to list for JSON serialization
                    "language": detected_lang
                }
                
                # Send request to STT service
                self.stt_service_socket.send_json(request)
                response = self.stt_service_socket.recv_json()
                
                if response.get("status") != "error":
                    transcript = {
                        "text": response.get("text", "").strip(),
                        "confidence": response.get("confidence", 0.0),
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

# Add standardized __main__ block
if __name__ == "__main__":
    agent = None
    try:
        agent = StreamingSpeechRecognition()
        agent.run()
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            agent.cleanup()
    def _get_health_status(self) -> dict:
        """Return health status information."""
        # Get base health status from parent class
        base_status = super()._get_health_status()
        
        # Add agent-specific health information
        base_status.update({
            'service': self.__class__.__name__,
            'uptime_seconds': int(time.time() - self.start_time) if hasattr(self, 'start_time') else 0,
            'request_count': self.request_count if hasattr(self, 'request_count') else 0,
            'status': 'HEALTHY'
        })
        
        return base_status
