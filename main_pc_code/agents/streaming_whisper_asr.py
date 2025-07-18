from common.core.base_agent import BaseAgent
"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

Streaming Whisper ASR Module (CTranslate2, Real-Time)
Subscribes to audio chunks from streaming_audio_capture.py via ZMQ and transcribes in near real-time.
"""

import zmq
import pickle
import numpy as np
import time
import logging
import whisper
import os
import yaml
from queue import Queue
from threading import Thread
import json
from pathlib import Path
import sys
from main_pc_code.utils.config_loader import load_config


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", "..")))
from common.utils.path_env import get_path, join_path, get_file_path
# Try to import model_client for centralized model access
try:
    from main_pc_code.utils.model_client import ModelClient
    model_client_available = True
    model_client = ModelClient()
    logging.info("ModelClient imported successfully")
except ImportError:
    model_client_available = False
    logging.warning("ModelClient import failed, will use direct model loading if enabled")

# Add project root to sys.path to allow for modular imports
project_root = Path(__file__).resolve().parent.parent

# Load configuration
config = load_config()

# Load LLM configuration to check for ENABLE_LEGACY_MODELS flag
llm_config_path = get_file_path("main_pc_config", "llm_config.yaml")
try:
    with open(llm_config_path, 'r') as f:
        llm_config = yaml.safe_load(f)
    ENABLE_LEGACY_MODELS = llm_config.get('global_flags', {}).get('ENABLE_LEGACY_MODELS', False)
    logging.info(f"ENABLE_LEGACY_MODELS flag set to: {ENABLE_LEGACY_MODELS}")
except Exception as e:
    logging.error(f"Error loading llm_config.yaml: {e}")
    ENABLE_LEGACY_MODELS = False
    logging.info("Defaulting ENABLE_LEGACY_MODELS to False")

# Only import legacy model management if enabled
if ENABLE_LEGACY_MODELS:
    try:
        # --- Dynamic Model Management Imports ---
        from modular_system.model_manager.model_manager_agent import DynamicSTTModelManager
        import psutil
        from datetime import datetime

        # Load model config
        config_path = Path(__file__).parent.parent.parent / 'config' / 'model_config.json'
        with open(config_path, 'r') as f:
            model_config = json.load(f)

        available_models = {}
        for k, v in model_config['models'].items():
            if 'whisper' in v['name']:
                available_models[v['name']] = {
                    'language': v.get('language', 'en'),
                    'path': v['path'],
                    'quantization': v.get('quantization', 'fp16'),
                    'priority': v.get('priority', 5),
                }

        max_concurrent = model_config.get('model_loading', {}).get('max_concurrent', 2)
        idle_timeout_sec = model_config.get('model_loading', {}).get('idle_timeout_sec', 600)

        # Instantiate dynamic STT model manager
        stt_manager = DynamicSTTModelManager(available_models, default_model=list(available_models.keys())[0] if available_models else 'base')
        timestamp_last_used = {}  # model_id: last used time
        logging.info("Legacy model management initialized")
    except Exception as e:
        logging.error(f"Failed to initialize legacy model management: {e}")
        ENABLE_LEGACY_MODELS = False
else:
    logging.info("Legacy model management disabled")

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StreamingWhisperASR")

# ZMQ Configuration
ZMQ_SUB_PORT = 6575  # Aligned with streaming_audio_capture.py's ZMQ_PUB_PORT
SAMPLE_RATE = 48000
CHUNK_DURATION = 0.5  # seconds per chunk
BUFFER_SECONDS = 2.0  # How much audio to buffer for each inference

class StreamingWhisperASR(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="StreamingWhisperAsr")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(f"tcp://localhost:{ZMQ_SUB_PORT}")
        self.socket.setsockopt(zmq.SUBSCRIBE, b"")
        logger.info(f"Subscribed to ZMQ audio stream on port {ZMQ_SUB_PORT}")
        self.audio_queue = Queue()
        self.running = True
        self.buffer = []
        self.last_infer_time = time.time()
        self.buffer_size = int(BUFFER_SECONDS / CHUNK_DURATION)
        self.current_model_id = None
        self.current_model = None
        self.language = 'en'  # Default; can be set per request/context
        self.start_time = time.time()

    def audio_listener(self):
        while self.running:
            try:
                msg = self.socket.recv()
                data = pickle.loads(msg)
                chunk = data["audio_chunk"]
                self.audio_queue.put(chunk)
            except Exception as e:
                logger.error(f"Error receiving audio chunk: {e}")
                time.sleep(0.1)

    def run(self):
        listener_thread = Thread(target=self.audio_listener, daemon=True)
        listener_thread.start()
        logger.info("Starting real-time streaming ASR loop...")
        try:
            while self.running:
                # Buffer audio
                while not self.audio_queue.empty():
                    chunk = self.audio_queue.get()
                    self.buffer.append(chunk)
                    if len(self.buffer) > self.buffer_size:
                        self.buffer.pop(0)
                # Run inference every BUFFER_SECONDS
                if len(self.buffer) == self.buffer_size:
                    audio_input = np.concatenate(self.buffer).astype(np.float32)
                    audio_input = audio_input / np.max(np.abs(audio_input) + 1e-8)
                    audio_input_16k = whisper.audio.resample_audio(audio_input, SAMPLE_RATE, 16000)

                    transcript = ""
                    if ENABLE_LEGACY_MODELS and 'stt_manager' in globals():
                        # --- Legacy Direct Model Loading Path ---
                        try:
                            # Dynamic Model Selection
                            language = self.language
                            context = None
                            model, model_id = stt_manager.get_model(language=language, context=context)
                            self.current_model_id = model_id
                            self.current_model = model
                            timestamp_last_used[model_id] = time.time()

                            # Unload idle models if needed
                            if len(stt_manager.loaded_models) > max_concurrent:
                                now = time.time()
                                idle_models = [mid for mid, ts in timestamp_last_used.items() if mid != model_id and (now - ts) > idle_timeout_sec]
                                for mid in idle_models:
                                    if mid in stt_manager.loaded_models:
                                        del stt_manager.loaded_models[mid]
                                        logger.info(f"Unloaded idle STT model '{mid}' due to timeout.")
                                        if mid in timestamp_last_used:
                                            del timestamp_last_used[mid]

                            result = self.current_model.transcribe(audio_input_16k, language=language, fp16=False, verbose=False)
                            transcript = result['text']
                        except Exception as e:
                            logger.error(f"Error in legacy model inference: {e}")
                    else:
                        # --- Centralized Model Management Path ---
                        if model_client_available:
                            try:
                                # Convert audio to list for JSON serialization
                                audio_list = audio_input_16k.tolist()
                                
                                # Request transcription from ModelManagerAgent via model_client
                                response = model_client.transcribe(
                                    audio_data=audio_list,
                                    language=self.language
                                )
                                
                                if response and response.get("status") == "ok":
                                    transcript = response.get("text", "").strip()
                                else:
                                    error_msg = response.get('message', 'Unknown error') if response else "No response"
                                    logger.error(f"Error in model_client transcription: {error_msg}")
                            except Exception as e:
                                logger.error(f"Error using model_client for transcription: {e}")
                        else:
                            logger.error("No transcription method available - neither legacy models nor model_client")
                    
                    if transcript:
                        logger.info(f"[ASR] {transcript.strip()}")
                        # Publish partial transcript to hybrid coordinator (port 5580)
                        if not hasattr(self, 'pub_socket'):
                            self.pub_socket = self.context.socket(zmq.PUB)
                            self.pub_socket.bind("tcp://*:5580")
                        msg = json.dumps({"transcript": transcript.strip(), "timestamp": time.time()}).encode('utf-8')
                        self.pub_socket.send(msg)
                    # Reset buffer
                    self.buffer = []
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt detected, stopping")
        finally:
            self.running = False
            self.context.term()
            logger.info("Streaming Whisper ASR stopped.")


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

            from datetime import datetime
            import psutil

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
    logger.info("Streaming Whisper ASR Module starting...")
    asr = StreamingWhisperASR()
    asr.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise