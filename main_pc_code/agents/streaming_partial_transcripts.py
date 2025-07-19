from common.core.base_agent import BaseAgent
"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

Streaming Partial Transcripts Module
Processes audio chunks and provides partial transcripts before full processing
"""
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import pickle
import numpy as np
import whisper
import time
from main_pc_code.agents.error_publisher import ErrorPublisher
import threading
import logging
import hashlib
from collections import deque
import yaml
from main_pc_code.utils.config_loader import load_config
import psutil
from datetime import datetime


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", "..")))
from common.utils.path_env import get_path, join_path, get_file_path
from common.env_helpers import get_env
# Try to import ModelClient, with fallback if not available
try:
    from main_pc_code.utils.model_client import ModelClient
    model_client = ModelClient()
except ImportError:
    logging.warning("ModelClient import failed, will use direct model loading if enabled")
    model_client = None

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StreamingPartialTranscripts")

# Load configuration
config = load_config()

# Load LLM configuration to check for ENABLE_LEGACY_MODELS flag
llm_config_path = get_file_path("main_pc_config", "llm_config.yaml")
try:
    with open(llm_config_path, 'r') as f:
        llm_config = yaml.safe_load(f)
    ENABLE_LEGACY_MODELS = llm_config.get('global_flags', {}).get('ENABLE_LEGACY_MODELS', False)
    logger.info(f"ENABLE_LEGACY_MODELS flag set to: {ENABLE_LEGACY_MODELS}")
except Exception as e:
    logger.error(f"Error loading llm_config.yaml: {e}")
    ENABLE_LEGACY_MODELS = False
    logger.info("Defaulting ENABLE_LEGACY_MODELS to False")

# ZMQ Configuration
ZMQ_SUB_PORT = 5570  # Subscribe to audio capture
ZMQ_PUB_PORT = 5575  # Publish partial transcripts
SAMPLE_RATE = 48000
CHUNK_DURATION = 0.5  # seconds per chunk
PARTIAL_BUFFER_SECONDS = 1.0  # Process partials every 1 second
MODEL_SIZE = "base"  # Use smaller model for partials to reduce latency

class StreamingPartialTranscripts(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="StreamingPartialTranscripts")
        self.context = None  # Using pool
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://localhost:{ZMQ_SUB_PORT}")
        self.sub_socket.setsockopt(zmq.SUBSCRIBE, b"")
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind(f"tcp://*:{ZMQ_PUB_PORT}")
        logger.info(f"Connected to audio stream on port {ZMQ_SUB_PORT}, publishing partials to {ZMQ_PUB_PORT}")
        
        # Initialize model
        self.model = None
        self._initialize_model()
        
        self.buffer = deque()
        self.buffer_times = deque()
        self.running = True
        # Initialise error publisher
        self.error_publisher = ErrorPublisher(self.name)
        self.lock = threading.Lock()
        self.last_chunk_hash = None
        self.start_time = time.time()
        
    def _initialize_model(self):
        """Initialize the model based on the ENABLE_LEGACY_MODELS flag"""
        if ENABLE_LEGACY_MODELS:
            # Legacy direct model loading path
            logger.info(f"Legacy mode: Loading Whisper model: {MODEL_SIZE} for partial transcripts")
            try:
                self.model = whisper.load_model(MODEL_SIZE, device="cuda")
                logger.info(f"Loaded Whisper model: {MODEL_SIZE} on GPU (CUDA)")
            except Exception as e:
                logger.error(f"Error loading Whisper model: {e}")
                self.model = None
        else:
            # New centralized model loading path
            logger.info("Using centralized model management for partial transcripts")
            # We don't need to load the model here, we'll use model_client for inference
            self.model = None
            logger.info("Model will be loaded through ModelManagerAgent when needed")
        
    def receive_audio(self):
        while self.running:
            try:
                msg = self.sub_socket.recv(flags=zmq.NOBLOCK)
                data = pickle.loads(msg)
                chunk = data['audio_chunk']
                timestamp = data['timestamp']
                with self.lock:
                    self.buffer.append(chunk)
                    self.buffer_times.append(timestamp)
            except zmq.Again:
                # No message available yet
                pass
            except Exception as e:
                logger.error(f"Audio receive error: {e}")
                self.error_publisher.publish_error(error_type="receive_audio", severity="medium", details=str(e))
                time.sleep(0.01)
    
    def process_partials(self):
        last_processed = 0
        while self.running:
            try:
                with self.lock:
                    if len(self.buffer) == 0:
                        pass
                    else:
                        total_seconds = len(self.buffer) * CHUNK_DURATION
                        # Process partials when we have enough buffer
                        if total_seconds >= PARTIAL_BUFFER_SECONDS:
                            try:
                                # Get audio from buffer but don't clear it
                                # The main transcription will handle clearing
                                audio = np.concatenate(list(self.buffer))
                                
                                # Generate a hash of the audio to avoid processing duplicates
                                audio_hash = hashlib.md5(audio.tobytes()).hexdigest()
                                if audio_hash == self.last_chunk_hash:
                                    # Skip if we've already processed this exact audio
                                    time.sleep(0.1)
                                    continue
                                
                                self.last_chunk_hash = audio_hash
                                logger.info(f"Processing {len(audio)/SAMPLE_RATE:.2f}s for partial transcript...")
                                
                                # Resample audio if needed (Whisper expects 16kHz)
                                if SAMPLE_RATE != 16000:
                                    try:
                                        # Ensure consistent data types (float32)
                                        audio = audio.astype(np.float32)
                                        target_length = int(len(audio) * 16000 / SAMPLE_RATE)
                                        # Use scipy's resample
                                        from scipy import signal
                                        audio_resampled = signal.resample(audio, target_length)
                                    except ImportError:
                                        # Fallback if scipy not available
                                        audio = audio.astype(np.float32)
                                        target_length = int(len(audio) * 16000 / SAMPLE_RATE)
                                        indices = np.linspace(0, len(audio) - 1, target_length, dtype=np.float32)
                                        positions = np.arange(len(audio), dtype=np.float32)
                                        audio_resampled = np.interp(indices, positions, audio)
                                else:
                                    audio_resampled = audio.astype(np.float32)
                                
                                # Process audio based on model loading strategy
                                partial_transcription = ""
                                detected_language = "unknown"
                                
                                if ENABLE_LEGACY_MODELS and self.model:
                                    # Legacy direct model inference
                                    try:
                                        result = self.model.transcribe(
                                            audio_resampled, 
                                            language=None, 
                                            fp16=True, 
                                            task='transcribe',
                                            verbose=False
                                        )
                                        partial_transcription = result['text'].strip()
                                        detected_language = result.get('language', 'unknown')
                                    except Exception as e:
                                        logger.error(f"Error in direct model inference: {e}")
                                else:
                                    # Use centralized model management
                                    if model_client:
                                        try:
                                            # Convert audio to list for JSON serialization
                                            audio_list = audio_resampled.tolist()
                                            
                                            # Request transcription from ModelManagerAgent via model_client
                                            response = model_client.transcribe(
                                                audio_data=audio_list,
                                                model_pref="fast"  # Use fast model for partials
                                            )
                                            
                                            if response and response.get("status") == "ok":
                                                partial_transcription = response.get("text", "").strip()
                                                detected_language = response.get("language", "unknown")
                                            else:
                                                error_msg = response.get('message', 'Unknown error') if response else "No response"
                                                logger.error(f"Error in model_client transcription: {error_msg}")
                                        except Exception as e:
                                            logger.error(f"Error using model_client for transcription: {e}")
                                    else:
                                        logger.error("No model available for transcription")
                                
                                if partial_transcription:
                                    logger.info(f"Partial: {partial_transcription}")
                                    
                                    # Publish partial transcript
                                    msg = pickle.dumps({
                                        'type': 'partial_transcription',
                                        'text': partial_transcription,
                                        'detected_language': detected_language,
                                        'is_partial': True,
                                        'timestamp': time.time()
                                    })
                                    self.pub_socket.send(msg)
                            except Exception as e:
                                logger.error(f"Error in partial transcription: {str(e)}")
                                self.error_publisher.publish_error(error_type="partial_transcription", severity="medium", details=str(e))
                                # Don't clear buffer, let main transcription handle it
            except Exception as e:
                logger.error(f"Error in partial processing loop: {str(e)}")
                self.error_publisher.publish_error(error_type="process_partials_loop", severity="high", details=str(e))
            
            # Sleep longer between partials to reduce CPU usage
            time.sleep(0.2)
    
    def run(self):
        recv_thread = threading.Thread(target=self.receive_audio, daemon=True)
        process_thread = threading.Thread(target=self.process_partials, daemon=True)
        recv_thread.start()
        process_thread.start()
        if not hasattr(self, "_background_threads"):
            self._background_threads = []
        self._background_threads.extend([recv_thread, process_thread])
        logger.info("Streaming partial transcripts running...")
        try:
            while self.running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.running = False
            logger.info("Streaming partial transcripts stopped by user.")


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
    print("=== Streaming Partial Transcripts Module ===")
    print("Processes audio chunks and provides partial transcripts")
    print(f"Subscribing to audio on port {ZMQ_SUB_PORT}")
    print(f"Publishing partials to port {ZMQ_PUB_PORT}")
    
    processor = StreamingPartialTranscripts()
    processor.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise