from main_pc_code.src.core.base_agent import BaseAgent
"""
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
from queue import Queue
from threading import Thread
import json
from pathlib import Path
import sys

# Add project root to sys.path to allow for modular imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# --- Dynamic Model Management Imports ---
from modular_system.model_manager.model_manager_agent import DynamicSTTModelManager
from common.env_helpers import get_env

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

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StreamingWhisperASR")

# Model paths
# WHISPER_MODEL_NAME = "large"  # Use your downloaded model name
ZMQ_SUB_PORT = 6575  # Aligned with streaming_audio_capture.py's ZMQ_PUB_PORT  # Must match streaming_audio_capture.py
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
        # Remove static model loading
        self.current_model_id = None
        self.current_model = None
        self.language = 'en'  # Default; can be set per request/context

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

                    # --- Dynamic Model Selection ---
                    # (In real use, language/context could be set externally or via VAD/language detector)
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
