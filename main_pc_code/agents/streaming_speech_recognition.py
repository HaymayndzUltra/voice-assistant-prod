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

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Import dynamic model management
from modular_system.model_manager.model_manager_agent import DynamicSTTModelManager
from utils.config_parser import parse_agent_args
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

# ZMQ Configuration
ZMQ_RAW_AUDIO_PORT = 6575  # Raw audio from streaming_audio_capture.py
ZMQ_CLEAN_AUDIO_PORT = int(getattr(_agent_args, 'clean_audio_port', 6578))  # Clean audio from FusedAudioPreprocessor
ZMQ_SUB_PORT = int(getattr(_agent_args, 'sub_port', 6578))  # Subscribe to clean audio from FusedAudioPreprocessor
ZMQ_PUB_PORT = int(getattr(_agent_args, 'pub_port', 6580))  # Transcriptions to LanguageAndTranslationCoordinator
ZMQ_HEALTH_PORT = int(getattr(_agent_args, 'health_port', 6578))  # Health check port (same as agent port)
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

# Model Management Settings
MAX_CONCURRENT_MODELS = 2
MODEL_IDLE_TIMEOUT = 600  # seconds
model_last_used = {}

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
        
        # VRAM management now handled by VRAMOptimizerAgent

        self.model_manager = None

        self._init_model_management()
        
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
        
        logger.info("Enhanced Streaming Speech Recognition initialized")
    
    def _init_sockets(self):
        """Initialize all ZMQ sockets."""
        try:
            # Subscribe to cleaned audio (preferred)
            self.sub_socket = self.zmq_context.socket(zmq.SUB)
            self.sub_socket.connect(f"tcp://{_agent_args.host}:{ZMQ_SUB_PORT}")
            self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            
            # Subscribe to wake word events
            self.wake_word_socket = self.zmq_context.socket(zmq.SUB)
            self.wake_word_socket.connect(f"tcp://{_agent_args.host}:{ZMQ_WAKE_WORD_PORT}")
            self.wake_word_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            
            # Subscribe to VAD events
            self.vad_socket = self.zmq_context.socket(zmq.SUB)
            self.vad_socket.connect(f"tcp://{_agent_args.host}:{ZMQ_VAD_PORT}")
            self.vad_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            
            # Publish transcriptions
            self.pub_socket = self.zmq_context.socket(zmq.PUB)
            self.pub_socket.bind(f"tcp://*:{ZMQ_PUB_PORT}")  # Bind to port 6580 as configured in startup_config.yaml
            
            # Health status
            self.health_socket = self.zmq_context.socket(zmq.PUB)
            self.health_socket.bind(f"tcp://*:{ZMQ_HEALTH_PORT}")
            
            logger.info(f"ZMQ sockets initialized - Clean Audio SUB: {ZMQ_SUB_PORT}, Wake Word SUB: {ZMQ_WAKE_WORD_PORT}, VAD SUB: {ZMQ_VAD_PORT}, Transcriptions PUB: {ZMQ_PUB_PORT}, Health: {ZMQ_HEALTH_PORT}")
        except Exception as e:
            logger.error(f"Error initializing ZMQ sockets: {str(e)}")
            raise
    
    # Model unloading now handled by VRAMOptimizerAgent and ModelManagerAgent

    def _init_model_management(self):
        """Initialize dynamic model management from a config file path passed as an argument."""
        try:
            # Get model config path from command-line arguments
            config_path_str = getattr(_agent_args, 'model_config_path', None)
            if not config_path_str:
                logger.error("Model config path not provided. Please specify with --model_config_path argument.")
                self.stt_manager = None
                return

            # The path from config is relative to the main_pc_code directory, which is project_root
            config_path = project_root / config_path_str
            
            if not config_path.is_file():
                logger.error(f"Model config file not found at: {config_path}")
                self.stt_manager = None
                return

            # Load model config
            logger.info(f"Loading model configuration from: {config_path}")
            with open(config_path, 'r') as f:
                model_config = json.load(f)
            
            # Prepare available models
            available_models = {}
            for k, v in model_config['models'].items():
                if 'whisper' in v['name']:
                    available_models[v['name']] = {
                        'language': v.get('language', 'en'),
                        'path': v['path'],
                        'quantization': v.get('quantization', 'fp16'),
                        'priority': v.get('priority', 5),
                    }
            
            # Initialize model manager
            self.stt_manager = DynamicSTTModelManager(
                available_models,
                default_model='whisper-large-v3'
            )
            
            # Track model usage
            self.timestamp_last_used = {}
            
            logger.info(f"Model management initialized successfully from {config_path}")
        except Exception as e:
            logger.error(f"Error initializing model management: {str(e)}")
            self.stt_manager = None # Ensure manager is None on failure
            raise
    
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
            # Connect to ModelManagerAgent/VRAMOptimizerAgent if needed
            if not hasattr(self, 'vram_optimizer_socket'):
                # Create socket for VRAMOptimizerAgent
                self.vram_optimizer_socket = self.zmq_context.socket(zmq.REQ)
                self.vram_optimizer_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
                
                # Try to discover VRAMOptimizerAgent
                try:
                    from utils.service_discovery_client import discover_service
                    vram_optimizer_info = discover_service("VRAMOptimizerAgent")
                    if vram_optimizer_info and vram_optimizer_info.get("status") == "SUCCESS":
                        vram_info = vram_optimizer_info.get("payload", {})
                        vram_host = vram_info.get("host", "localhost") 
                        vram_port = vram_info.get("port", 5572)  # Default port
                        
                        # Apply secure ZMQ if enabled
                        from src.network.secure_zmq import is_secure_zmq_enabled, setup_curve_client
                        if is_secure_zmq_enabled():
                            setup_curve_client(self.vram_optimizer_socket)
                            
                        self.vram_optimizer_socket.connect(f"tcp://{vram_host}:{vram_port}")
                        logger.info(f"Connected to VRAMOptimizerAgent at tcp://{vram_host}:{vram_port}")
                    else:
                        logger.warning("Failed to discover VRAMOptimizerAgent, will continue with local model management")
                        return
                except Exception as e:
                    logger.warning(f"Error discovering VRAMOptimizerAgent: {e}")
                    return
            
            # Send update to VRAMOptimizerAgent about the current model being used
            # This allows VRAMOptimizerAgent to track model usage and make unloading decisions
            try:
                request = {
                    "command": "UPDATE_MODEL_USAGE",
                    "model_id": current_model_id,
                    "timestamp": time.time(),
                    "agent": "StreamingSpeechRecognition",
                    "model_type": "stt"
                }
                self.vram_optimizer_socket.send_json(request)
                
                # Try to get response, but don't block if no response
                try:
                    response = self.vram_optimizer_socket.recv_json()
                    logger.debug(f"VRAMOptimizerAgent response: {response}")
                except zmq.error.Again:
                    # Timeout is okay for this non-critical operation
                    pass
                    
            except Exception as e:
                logger.warning(f"Error sending model usage update to VRAMOptimizerAgent: {e}")
                
            # Track model usage locally
            now = time.time()
            self.timestamp_last_used[current_model_id] = now
            
        except Exception as e:
            logger.error(f"Error in delegated model management: {str(e)}")
            # Fallback to local tracking only
            now = time.time()
            self.timestamp_last_used[current_model_id] = now
    
    def health_broadcast_loop(self):
        """Broadcast health status."""
        while self._running:
            try:
                health_data = {
                    "component": "StreamingSpeechRecognition",
                    "status": "healthy",
                    "model_loaded": hasattr(self, 'stt_manager') and len(self.stt_manager.loaded_models) > 0,
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
                
            if hasattr(self, 'vram_optimizer_socket'):
                self.vram_optimizer_socket.close()
            
            # Terminate ZMQ context - do this after all sockets are closed
            if hasattr(self, 'zmq_context'):
                self.zmq_context.term()
            
            # Clear model cache - now delegated to ModelManagerAgent via VRAMOptimizerAgent
            if hasattr(self, 'stt_manager') and self.stt_manager:
                # Send notification to VRAMOptimizerAgent that we're shutting down
                try:
                    # Only attempt if we have a VRAM optimizer socket
                    if hasattr(self, 'vram_optimizer_socket') and not self.vram_optimizer_socket.closed:
                        request = {
                            "command": "AGENT_SHUTDOWN",
                            "agent": "StreamingSpeechRecognition",
                            "timestamp": time.time()
                        }
                        self.vram_optimizer_socket.send_json(request)
                        # Don't wait for response during shutdown
                except Exception as e:
                    logger.warning(f"Error notifying VRAMOptimizerAgent of shutdown: {e}")
            
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
            
            # Get appropriate model
            try:
                model, model_id = self.stt_manager.get_model(
                    language=detected_lang,
                    context=None
                )
                self.timestamp_last_used[model_id] = time.time()
            except Exception as model_error:
                logger.error(f"Error getting speech recognition model: {str(model_error)}")
                error_message = {
                    "status": "error",
                    "error_type": "ModelLoadError",
                    "source_agent": "streaming_speech_recognition.py",
                    "message": f"Failed to load speech recognition model: {str(model_error)}",
                    "timestamp": datetime.now().isoformat()
                }
                self.pub_socket.send_json(error_message)
                self.process_thread = None
                return
            
            # Unload idle models
            self._cleanup_idle_models(model_id)
            
            # Transcribe
            try:
                result = model.transcribe(
                    audio_input_16k,
                    language=detected_lang,
                    fp16=False,
                    verbose=False
                )
            except Exception as transcribe_error:
                logger.error(f"Error transcribing audio: {str(transcribe_error)}")
                error_message = {
                    "status": "error",
                    "error_type": "TranscriptionError",
                    "source_agent": "streaming_speech_recognition.py",
                    "message": f"Transcription failed: {str(transcribe_error)}",
                    "timestamp": datetime.now().isoformat(),
                    "details": {
                        "model_id": model_id,
                        "language": detected_lang,
                        "audio_length_seconds": len(audio_input_16k) / 16000
                    }
                }
                self.pub_socket.send_json(error_message)
                self.process_thread = None
                return
            
            # Process transcription
            if result['text'].strip():
                transcript = {
                    "text": result['text'].strip(),
                    "confidence": result.get('confidence', 0.0),
                    "language": detected_lang,
                    "language_confidence": confidence,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Publish transcription
                try:
                    self.pub_socket.send_string(f"TRANSCRIPTION: {json.dumps(transcript)}")
                    
                    # Log high confidence transcriptions
                    if transcript['confidence'] > 0.8:
                        logger.info(f"High confidence transcription: {transcript['text']} ({transcript['confidence']:.2f})")
                except Exception as pub_error:
                    logger.error(f"Error publishing transcription: {str(pub_error)}")
                    error_message = {
                        "status": "error",
                        "error_type": "CommunicationError",
                        "source_agent": "streaming_speech_recognition.py",
                        "message": f"Failed to publish transcription: {str(pub_error)}",
                        "timestamp": datetime.now().isoformat()
                    }
                    try:
                        self.pub_socket.send_json(error_message)
                    except Exception:
                        logger.critical("Critical communication failure: Unable to send error message")
            else:
                logger.info("Empty transcription result, nothing to publish")
            
            # Calculate and log the duration
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"PERF_METRIC: [StreamingSpeechRecognition] - [AudioProcessing] - Duration: {duration_ms:.2f}ms")
            
        except Exception as e:
            logger.error(f"Error processing audio buffer: {str(e)}")
            
            # Send standardized error message
            error_message = {
                "status": "error",
                "error_type": "TranscriptionError",
                "source_agent": "streaming_speech_recognition.py",
                "message": f"Failed to process audio buffer: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "traceback": str(sys.exc_info()[2])
                }
            }
            
            try:
                self.pub_socket.send_json(error_message)
                logger.info("Published error message about audio buffer processing failure")
            except Exception as pub_error:
                logger.error(f"Failed to publish error message: {str(pub_error)}")
                
        finally:
            self.process_thread = None

    def get_whisper_model(self, model_id):
        now = time.time()
        # Unload idle models
        for mid, last_used in list(model_last_used.items()):
            if now - last_used > MODEL_IDLE_TIMEOUT:
                self._cleanup_idle_models(mid)
                del model_last_used[mid]
        # Lazy load
        if model_id not in self.timestamp_last_used:
            self.stt_manager.get_model(
                language='en',
                context=None
            )
            self.timestamp_last_used[model_id] = now
        model_last_used[model_id] = now
        return self.stt_manager.loaded_models[model_id]

if __name__ == "__main__":
    try:
        asr = StreamingSpeechRecognition()
        asr.run()
    except Exception as e:
        logger.error(f"Speech recognition failed: {e}")
        sys.exit(1)
