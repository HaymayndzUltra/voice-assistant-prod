"""
Fused Audio Preprocessor
-----------------------
Optimized audio preprocessing agent that combines noise reduction and voice activity detection:
- Subscribes to raw audio stream from streaming_audio_capture
- Applies noise reduction algorithms to clean the audio
- Performs voice activity detection on the cleaned audio
- Publishes both cleaned audio and VAD events to downstream components
- Reduces latency by processing in a single agent with no inter-agent communication
"""

import zmq
import pickle
import numpy as np
import time
import threading
import logging
import os
import sys
import json
import torch
from pathlib import Path
from datetime import datetime
from collections import deque
import noisereduce as nr
from scipy import signal
from src.core.http_server import setup_health_check_server
from utils.config_parser import parse_agent_args
_agent_args = parse_agent_args()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fused_audio_preprocessor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ZMQ Configuration - Keep the same ports as the original agents for compatibility
ZMQ_SUB_PORT = 6575  # Raw audio from streaming_audio_capture.py
ZMQ_CLEAN_AUDIO_PUB_PORT = 6578  # Clean audio (same as old NoiseReductionAgent)
ZMQ_VAD_PUB_PORT = 6579  # Voice activity events (same as old VADAgent)
ZMQ_HEALTH_PORT = int(getattr(_agent_args, 'port', 6581))  # Health check port (as configured in startup_config.yaml)

# Noise Reduction Settings
NOISE_REDUCTION_STRENGTH = 0.5  # Strength of noise reduction (0.0-1.0)
NOISE_SAMPLE_DURATION = 0.5  # Duration in seconds to sample for noise profile
USE_STATIONARY_NOISE = True  # Use stationary noise reduction algorithm
USE_SPECTRAL_GATING = True  # Use spectral gating noise reduction
PROP_DECREASE = 0.8  # Proportion to decrease the noise by
SPECTRAL_SMOOTHING_MS = 150  # Spectral smoothing in ms

# VAD Settings
VAD_THRESHOLD = 0.5  # Voice detection threshold (0.0-1.0)
VAD_WINDOW_SIZE_MS = 96  # Window size in milliseconds
VAD_SAMPLE_RATE = 16000  # Sample rate expected by the model
VAD_MIN_SPEECH_DURATION_MS = 250  # Minimum speech duration to trigger (ms)
VAD_MIN_SILENCE_DURATION_MS = 100  # Minimum silence duration to reset (ms)
VAD_SPEECH_PAD_MS = 30  # Padding around speech segments (ms)
VAD_USE_ADAPTIVE_THRESHOLD = True  # Dynamically adjust threshold based on ambient noise

class FusedAudioPreprocessor:
    def __init__(self):
        """Initialize the fused audio preprocessor."""
        self._running = False
        self._thread = None
        self.health_thread = None
        
        # Initialize ZMQ context
        self.zmq_context = zmq.Context()
        
        # Initialize sockets
        self._init_sockets()
        
        # Initialize noise reduction components
        self.noise_profile = None
        self.noise_samples = []
        self.is_collecting_noise = True
        self.noise_sample_count = 0
        self.noise_sample_target = 10  # Number of audio chunks to collect for noise profile
        
        # Initialize VAD components
        self._init_vad_model()
        self.speech_active = False
        self.speech_start_time = None
        self.last_speech_end_time = None
        self.audio_buffer = deque(maxlen=int(VAD_SAMPLE_RATE * 1.0))  # 1 second buffer
        self.speech_prob_history = deque(maxlen=50)  # Store recent speech probabilities
        self.adaptive_threshold = VAD_THRESHOLD
        
        logger.info("Fused Audio Preprocessor initialized")
    
    def _init_sockets(self):
        """Initialize all ZMQ sockets."""
        try:
            # Subscribe to raw audio
            self.sub_socket = self.zmq_context.socket(zmq.SUB)
            self.sub_socket.connect(f"tcp://{_agent_args.host}:{ZMQ_SUB_PORT}")
            self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            
            # Publish cleaned audio (same port as old NoiseReductionAgent)
            self.clean_audio_pub_socket = self.zmq_context.socket(zmq.PUB)
            self.clean_audio_pub_socket.bind(f"tcp://*:{ZMQ_CLEAN_AUDIO_PUB_PORT}")
            
            # Publish VAD events (same port as old VADAgent)
            self.vad_pub_socket = self.zmq_context.socket(zmq.PUB)
            self.vad_pub_socket.bind(f"tcp://*:{ZMQ_VAD_PUB_PORT}")
            
            # Health status
            self.health_socket = self.zmq_context.socket(zmq.PUB)
            self.health_socket.bind(f"tcp://*:{ZMQ_HEALTH_PORT}")
            
            logger.info(f"ZMQ sockets initialized - Raw Audio SUB: {ZMQ_SUB_PORT}, Clean Audio PUB: {ZMQ_CLEAN_AUDIO_PUB_PORT}, VAD Events PUB: {ZMQ_VAD_PUB_PORT}, Health: {ZMQ_HEALTH_PORT}")
        except Exception as e:
            logger.error(f"Error initializing ZMQ sockets: {str(e)}")
            raise
    
    def _init_vad_model(self):
        """Initialize the Silero VAD model."""
        try:
            # Check if CUDA is available
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            logger.info(f"Using device: {self.device}")
            
            # Create model directory if it doesn't exist
            model_dir = Path("models/vad")
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Download and load the model
            model_path = model_dir / "silero_vad.jit"
            if not model_path.exists():
                logger.info("Downloading Silero VAD model...")
                torch.hub.download_url_to_file(
                    'https://github.com/snakers4/silero-vad/raw/master/files/silero_vad.jit',
                    str(model_path)
                )
            
            # Load the model
            self.model = torch.jit.load(str(model_path)).to(self.device)
            
            # Initialize VAD pipeline
            vad_model = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=True,
                onnx=False,
                verbose=False
            )
            
            self.get_speech_timestamps = vad_model['get_speech_timestamps']
            self.vad = vad_model['vad']
            
            logger.info("Silero VAD model loaded successfully")
        except Exception as e:
            logger.error(f"Error initializing VAD model: {str(e)}")
            
            # Fallback to a simple energy-based VAD
            self.model = None
            logger.warning("Falling back to simple energy-based VAD")
    
    def apply_noise_reduction(self, audio_data, sample_rate):
        """Apply noise reduction to audio data."""
        try:
            # Start timing for performance metrics
            start_time = time.time()
            
            # If we're still collecting noise samples
            if self.is_collecting_noise:
                self.noise_samples.append(audio_data.copy())
                self.noise_sample_count += 1
                
                if self.noise_sample_count >= self.noise_sample_target:
                    # Create noise profile from collected samples
                    self.noise_profile = np.concatenate(self.noise_samples)
                    self.is_collecting_noise = False
                    logger.info(f"Noise profile created from {self.noise_sample_count} samples")
                
                # During collection phase, pass through audio unchanged
                result = audio_data
            else:
                # Apply noise reduction using the noise profile
                if self.noise_profile is not None:
                    # Convert to float32 if needed
                    if audio_data.dtype != np.float32:
                        audio_data = audio_data.astype(np.float32)
                    
                    # Apply noise reduction
                    reduced_noise = nr.reduce_noise(
                        y=audio_data,
                        sr=sample_rate,
                        y_noise=self.noise_profile,
                        stationary=USE_STATIONARY_NOISE,
                        prop_decrease=PROP_DECREASE
                    )
                    
                    # Apply spectral gating if enabled
                    if USE_SPECTRAL_GATING:
                        reduced_noise = nr.reduce_noise(
                            y=reduced_noise,
                            sr=sample_rate,
                            stationary=False,
                            prop_decrease=PROP_DECREASE,
                            n_std_thresh_stationary=1.5,
                            n_fft=1024,
                            win_length=512,
                            hop_length=128,
                            time_constant_s=SPECTRAL_SMOOTHING_MS / 1000
                        )
                    
                    result = reduced_noise
                else:
                    result = audio_data
            
            # Calculate and log the duration
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"PERF_METRIC: [FusedAudioPreprocessor] - [NoiseReduction] - Duration: {duration_ms:.2f}ms")
            
            return result
        except Exception as e:
            logger.error(f"Error in noise reduction: {str(e)}")
            return audio_data  # Return original audio on error
    
    def _resample_audio(self, audio_data, original_sample_rate):
        """Resample audio to the required sample rate for VAD model."""
        if original_sample_rate == VAD_SAMPLE_RATE:
            return audio_data
            
        try:
            # Calculate resampling ratio
            ratio = VAD_SAMPLE_RATE / original_sample_rate
            
            # Calculate new length
            new_length = int(len(audio_data) * ratio)
            
            # Use numpy's resample function
            resampled = np.interp(
                np.linspace(0, len(audio_data) - 1, new_length),
                np.arange(len(audio_data)),
                audio_data
            )
            
            return resampled
        except Exception as e:
            logger.error(f"Error resampling audio: {str(e)}")
            return audio_data  # Return original audio on error
    
    def _update_adaptive_threshold(self, speech_prob):
        """Update adaptive threshold based on recent speech probabilities."""
        if not VAD_USE_ADAPTIVE_THRESHOLD:
            return
            
        # Add current probability to history
        self.speech_prob_history.append(speech_prob)
        
        # Calculate statistics
        if len(self.speech_prob_history) > 10:
            mean_prob = np.mean(self.speech_prob_history)
            std_prob = np.std(self.speech_prob_history)
            
            # Adjust threshold - higher when noisy, lower when quiet
            noise_level = mean_prob
            if noise_level < 0.1:
                # Very quiet environment
                self.adaptive_threshold = max(0.3, VAD_THRESHOLD - 0.1)
            elif noise_level > 0.3:
                # Noisy environment
                self.adaptive_threshold = min(0.7, VAD_THRESHOLD + 0.1)
            else:
                # Normal environment
                self.adaptive_threshold = VAD_THRESHOLD
    
    def detect_speech(self, audio_data, sample_rate):
        """Detect speech using Silero VAD model."""
        try:
            # Start timing for performance metrics
            start_time = time.time()
            
            # Ensure the audio is the right sample rate for the VAD model
            if sample_rate != VAD_SAMPLE_RATE:
                audio_data = self._resample_audio(audio_data, sample_rate)
            
            # Ensure audio is float32 and scaled to [-1, 1]
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            if np.max(np.abs(audio_data)) > 1.0:
                audio_data = audio_data / np.max(np.abs(audio_data))
            
            # If Silero model is available, use it
            if self.model is not None:
                # Convert to tensor
                tensor = torch.from_numpy(audio_data).to(self.device)
                
                # Get speech probability
                speech_prob = self.vad(tensor, VAD_SAMPLE_RATE).item()
                
                # Update adaptive threshold
                self._update_adaptive_threshold(speech_prob)
                
                # Determine if this is speech based on threshold
                threshold = self.adaptive_threshold if VAD_USE_ADAPTIVE_THRESHOLD else VAD_THRESHOLD
                is_speech = speech_prob >= threshold
                
                # Handle state transitions
                current_time = time.time()
                
                if is_speech and not self.speech_active:
                    # Speech start
                    self.speech_active = True
                    self.speech_start_time = current_time
                    
                    # Publish speech start event
                    self._publish_vad_event("speech_start", speech_prob)
                    
                elif not is_speech and self.speech_active:
                    # Check if speech has been active for minimum duration
                    if self.speech_start_time and (current_time - self.speech_start_time) * 1000 >= VAD_MIN_SPEECH_DURATION_MS:
                        # Speech end
                        self.speech_active = False
                        self.last_speech_end_time = current_time
                        
                        # Publish speech end event
                        self._publish_vad_event("speech_end")
                
                # Always publish the speech probability
                self._publish_vad_event("speech_prob", speech_prob)
            else:
                # Fallback to simple energy-based VAD
                energy = np.mean(np.abs(audio_data))
                is_speech = energy > 0.02  # Simple energy threshold
                speech_prob = energy * 5  # Scale energy to 0-1 range approximation
                
                # Update state
                current_time = time.time()
                
                if is_speech and not self.speech_active:
                    self.speech_active = True
                    self.speech_start_time = current_time
                    self._publish_vad_event("speech_start", speech_prob)
                elif not is_speech and self.speech_active:
                    self.speech_active = False
                    self.last_speech_end_time = current_time
                    self._publish_vad_event("speech_end")
                
                # Always publish the speech probability
                self._publish_vad_event("speech_prob", speech_prob)
            
            # Calculate and log the duration
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"PERF_METRIC: [FusedAudioPreprocessor] - [SpeechDetection] - Duration: {duration_ms:.2f}ms")
            
            return is_speech, speech_prob
            
        except Exception as e:
            logger.error(f"Error in speech detection: {str(e)}")
            return False, 0.0
    
    def _publish_vad_event(self, event_type, speech_prob=None):
        """Publish a VAD event to the VAD events PUB socket."""
        try:
            event = {
                "event": event_type,
                "timestamp": datetime.now().isoformat()
            }
            
            if event_type == "speech_start" or event_type == "speech_prob":
                event["confidence"] = float(speech_prob) if speech_prob is not None else 0.0
            
            if event_type == "speech_start":
                event["is_speech"] = True
                event["speech_prob"] = float(speech_prob) if speech_prob is not None else 0.0
            elif event_type == "speech_end":
                event["is_speech"] = False
            elif event_type == "speech_prob":
                event["is_speech"] = self.speech_active
                event["speech_prob"] = float(speech_prob) if speech_prob is not None else 0.0
            
            # Send the event
            self.vad_pub_socket.send_json(event)
            
        except Exception as e:
            logger.error(f"Error publishing VAD event: {str(e)}")
    
    def process_audio_loop(self):
        """Main processing loop for audio data."""
        logger.info("Starting audio processing loop")
        
        while self._running:
            try:
                # Try to receive audio data
                try:
                    message = self.sub_socket.recv(flags=zmq.NOBLOCK)
                    data = pickle.loads(message)
                    audio_chunk = data.get('audio_chunk')
                    sample_rate = data.get('sample_rate', 16000)
                    
                    if audio_chunk is None:
                        logger.warning("Received empty audio chunk")
                        time.sleep(0.01)
                        continue
                    
                    # Step 1: Apply noise reduction to get cleaned audio
                    start_time = time.time()
                    cleaned_audio = self.apply_noise_reduction(audio_chunk, sample_rate)
                    nr_time = time.time() - start_time
                    
                    # Step 2: Perform VAD on the cleaned audio (in the same process)
                    start_time = time.time()
                    is_speech, speech_prob = self.detect_speech(cleaned_audio, sample_rate)
                    vad_time = time.time() - start_time
                    
                    # Step 3: Publish cleaned audio
                    clean_data = {
                        'audio_chunk': cleaned_audio,
                        'sample_rate': sample_rate,
                        'timestamp': data.get('timestamp', datetime.now().isoformat()),
                        'is_cleaned': True,
                        'original_energy': np.mean(np.abs(audio_chunk)),
                        'cleaned_energy': np.mean(np.abs(cleaned_audio))
                    }
                    self.clean_audio_pub_socket.send(pickle.dumps(clean_data))
                    
                    # Log the total processing time (with breakdown)
                    total_time = nr_time + vad_time
                    logger.info(f"PERF_METRIC: [FusedAudioPreprocessor] - [TotalProcessing] - Duration: {total_time*1000:.2f}ms (NR: {nr_time*1000:.2f}ms, VAD: {vad_time*1000:.2f}ms)")
                    
                except zmq.Again:
                    time.sleep(0.01)  # Small sleep when no messages
                    continue
                except pickle.UnpicklingError as pe:
                    logger.error(f"Unpickling error: {str(pe)}")
                    time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in audio processing loop: {str(e)}")
                time.sleep(0.1)  # Sleep on error to prevent tight loop
    
    def health_broadcast_loop(self):
        """Send health status updates periodically."""
        logger.info("Starting health broadcast loop")
        
        while self._running:
            try:
                # Create health status message
                health_status = {
                    'timestamp': datetime.now().isoformat(),
                    'component': 'FusedAudioPreprocessor',
                    'status': 'healthy',
                    'metrics': {
                        'noise_profile_samples': self.noise_sample_count,
                        'is_collecting_noise': self.is_collecting_noise,
                        'speech_active': self.speech_active,
                        'vad_threshold': self.adaptive_threshold if VAD_USE_ADAPTIVE_THRESHOLD else VAD_THRESHOLD,
                        'device': str(self.device) if hasattr(self, 'device') else 'unknown'
                    }
                }
                
                # Send health status
                self.health_socket.send_json(health_status)
                
                # Sleep for 1 second
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in health broadcast loop: {str(e)}")
                time.sleep(1)
    
    def start(self):
        """Start the fused audio preprocessor."""
        if self._running:
            logger.warning("Fused Audio Preprocessor is already running")
            return
        
        # Set running flag
        self._running = True
        
        # Start processing thread
        self._thread = threading.Thread(target=self.process_audio_loop)
        self._thread.daemon = True
        self._thread.start()
        
        # Start health broadcast thread
        self.health_thread = threading.Thread(target=self.health_broadcast_loop)
        self.health_thread.daemon = True
        self.health_thread.start()
        
        logger.info("Fused Audio Preprocessor started")
    
    def stop(self):
        """Stop the fused audio preprocessor."""
        if not self._running:
            logger.warning("Fused Audio Preprocessor is not running")
            return
        
        # Clear running flag
        self._running = False
        
        # Wait for threads to complete
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        
        if self.health_thread and self.health_thread.is_alive():
            self.health_thread.join(timeout=2.0)
        
        # Close ZMQ sockets
        self.sub_socket.close()
        self.clean_audio_pub_socket.close()
        self.vad_pub_socket.close()
        self.health_socket.close()
        
        logger.info("Fused Audio Preprocessor stopped")
    
    def run(self):
        """Run the fused audio preprocessor."""
        try:
            # Start the preprocessor
            self.start()
            
            # Keep the main thread alive
            while self._running:
                try:
                    time.sleep(0.1)
                except KeyboardInterrupt:
                    logger.info("Keyboard interrupt received, stopping...")
                    break
                
        finally:
            # Stop the preprocessor
            self.stop()


if __name__ == "__main__":
    try:
        # Create and run the fused audio preprocessor
        preprocessor = FusedAudioPreprocessor()
        preprocessor.run()
    except Exception as e:
        logger.error(f"Error running fused audio preprocessor: {str(e)}")
        sys.exit(1) 