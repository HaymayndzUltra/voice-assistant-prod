from main_pc_code.src.core.base_agent import BaseAgent
"""
Streaming Partial Transcripts Module
Processes audio chunks and provides partial transcripts before full processing
"""
import zmq
import pickle
import numpy as np
import whisper
import time
import threading
import logging
import hashlib
from collections import deque

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StreamingPartialTranscripts")

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
        self.context = zmq.Context()
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://localhost:{ZMQ_SUB_PORT}")
        self.sub_socket.setsockopt(zmq.SUBSCRIBE, b"")
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind(f"tcp://*:{ZMQ_PUB_PORT}")
        logger.info(f"Connected to audio stream on port {ZMQ_SUB_PORT}, publishing partials to {ZMQ_PUB_PORT}")
        
        # Use base model for partials (faster)
        logger.info(f"Loading Whisper model: {MODEL_SIZE} for partial transcripts")
        self.model = whisper.load_model(MODEL_SIZE, device="cuda")
        logger.info(f"Loaded Whisper model: {MODEL_SIZE} on GPU (CUDA)")
        
        self.buffer = deque()
        self.buffer_times = deque()
        self.running = True
        self.lock = threading.Lock()
        self.last_chunk_hash = None
        
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
                                
                                # Use faster decode-only mode for partials
                                result = self.model.transcribe(
                                    audio_resampled, 
                                    language=None, 
                                    fp16=True, 
                                    task='transcribe',
                                    verbose=False
                                )
                                
                                partial_transcription = result['text'].strip()
                                detected_language = result.get('language', 'unknown')
                                
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
                                # Don't clear buffer, let main transcription handle it
            except Exception as e:
                logger.error(f"Error in partial processing loop: {str(e)}")
            
            # Sleep longer between partials to reduce CPU usage
            time.sleep(0.2)
    
    def run(self):
        recv_thread = threading.Thread(target=self.receive_audio, daemon=True)
        process_thread = threading.Thread(target=self.process_partials, daemon=True)
        recv_thread.start()
        process_thread.start()
        logger.info("Streaming partial transcripts running...")
        try:
            while self.running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.running = False
            logger.info("Streaming partial transcripts stopped by user.")

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
