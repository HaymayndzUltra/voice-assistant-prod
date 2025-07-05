"""
Fused Audio Preprocessor
-----------------------
Optimized audio preprocessing agent tha

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

t combines noise reduction and voice activity detection:
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
import librosa
from main_pc_code.src.core.http_server import setup_health_check_server
from main_pc_code.utils.config_loader import load_config
from main_pc_code.utils.service_discovery_client import discover_service
from main_pc_code.src.core.base_agent import BaseAgent

# Load configuration at module level
config = load_config()

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

# Check for secure ZMQ configuration
SECURE_ZMQ = os.environ.get("SECURE_ZMQ", "0") == "1"

# ZMQ Configuration - Use service discovery instead of hardcoded ports
ZMQ_SUB_PORT = int(config.get("sub_port", 6575))  # Raw audio from streaming_audio_capture.py
ZMQ_CLEAN_AUDIO_PUB_PORT = int(config.get("clean_audio_pub_port", 6578))  # Clean audio (same as old NoiseReductionAgent)
ZMQ_VAD_PUB_PORT = int(config.get("vad_pub_port", 6579))  # Voice activity events (same as old VADAgent)
ZMQ_HEALTH_PORT = int(config.get("health_port", 6581))  # Health check port (as configured in startup_config.yaml)

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

# AEC Settings (Acoustic Echo Cancellation)
AEC_ENABLED = True  # Enable/disable AEC
AEC_FILTER_LENGTH = 512  # Length of the adaptive filter
AEC_STEP_SIZE = 0.05  # Step size for filter adaptation (0.01-0.1)
AEC_LEAK_FACTOR = 0.9  # Leakage factor for adaptive filter (0.9-1.0)
AEC_REFERENCE_DELAY = 0  # Delay in samples for reference signal

# AGC Settings (Automatic Gain Control)
AGC_ENABLED = True  # Enable/disable AGC
AGC_TARGET_LEVEL = 0.5  # Target level for audio normalization (0.0-1.0)
AGC_MAX_GAIN = 10.0  # Maximum gain to apply
AGC_MIN_GAIN = 0.1  # Minimum gain to apply
AGC_ATTACK_TIME = 0.01  # Attack time in seconds
AGC_RELEASE_TIME = 0.1  # Release time in seconds
AGC_FRAME_SIZE_MS = 10  # Frame size for AGC processing in milliseconds

class FusedAudioPreprocessorAgent(BaseAgent):
    def __init__(self, config=None, **kwargs):
        # Ensure config is a dictionary
        config = config or {}
        
        # Get configuration values with fallbacks
        agent_port = int(config.get("port", 5703))
        agent_name = kwargs.get('name', "FusedAudioPreprocessorAgent")
        bind_address = config.get("bind_address", '<BIND_ADDR>')
        zmq_timeout = int(config.get("zmq_request_timeout", 5000))
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(port=agent_port, **kwargs)
        
        # Store important attributes
        self.bind_address = bind_address
        self.zmq_timeout = zmq_timeout
        self.start_time = time.time()
        
        self._running = False
        self._thread = None
        
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
        
        # Initialize AEC components
        self._init_aec()
        
        # Initialize AGC components
        self._init_agc()
        
        # Load configuration
        self._load_config()
        
        logger.info("Fused Audio Preprocessor initialized")
    
    def _load_config(self):
        """Load configuration from config file if available."""
        try:
            config_path = Path("config/audio_preprocessing.json")
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                # Update AEC settings
                global AEC_ENABLED, AEC_FILTER_LENGTH, AEC_STEP_SIZE, AEC_LEAK_FACTOR, AEC_REFERENCE_DELAY
                AEC_ENABLED = config.get("AEC_ENABLED", AEC_ENABLED)
                AEC_FILTER_LENGTH = config.get("AEC_FILTER_LENGTH", AEC_FILTER_LENGTH)
                AEC_STEP_SIZE = config.get("AEC_STEP_SIZE", AEC_STEP_SIZE)
                AEC_LEAK_FACTOR = config.get("AEC_LEAK_FACTOR", AEC_LEAK_FACTOR)
                AEC_REFERENCE_DELAY = config.get("AEC_REFERENCE_DELAY", AEC_REFERENCE_DELAY)
                
                # Update AGC settings
                global AGC_ENABLED, AGC_TARGET_LEVEL, AGC_MAX_GAIN, AGC_MIN_GAIN, AGC_ATTACK_TIME, AGC_RELEASE_TIME
                AGC_ENABLED = config.get("AGC_ENABLED", AGC_ENABLED)
                AGC_TARGET_LEVEL = config.get("AGC_TARGET_LEVEL", AGC_TARGET_LEVEL)
                AGC_MAX_GAIN = config.get("AGC_MAX_GAIN", AGC_MAX_GAIN)
                AGC_MIN_GAIN = config.get("AGC_MIN_GAIN", AGC_MIN_GAIN)
                AGC_ATTACK_TIME = config.get("AGC_ATTACK_TIME", AGC_ATTACK_TIME)
                AGC_RELEASE_TIME = config.get("AGC_RELEASE_TIME", AGC_RELEASE_TIME)
                
                logger.info(f"Loaded configuration from {config_path}")
                logger.info(f"AEC enabled: {AEC_ENABLED}, AGC enabled: {AGC_ENABLED}")
        except Exception as e:
            logger.warning(f"Failed to load configuration: {e}")
            logger.info("Using default settings")
    
    def _init_aec(self):
        """Initialize Acoustic Echo Cancellation components."""
        # Initialize adaptive filter coefficients
        self.aec_filter = np.zeros(AEC_FILTER_LENGTH)
        
        # Buffer for reference signal (playback audio)
        self.reference_buffer = np.zeros(AEC_FILTER_LENGTH * 2)
        
        # For simplicity, we'll use a simulated reference signal
        # In a real implementation, this would come from the audio output
        self.simulated_reference = True
        
        # Echo estimate for the current frame
        self.echo_estimate = None
        
        # Last clean audio for reference simulation
        self.last_clean_audio = None
        
        logger.info(f"AEC initialized with filter length {AEC_FILTER_LENGTH}")
    
    def _init_agc(self):
        """Initialize Automatic Gain Control components."""
        # Current gain value
        self.current_gain = 1.0
        
        # Envelope follower state
        self.envelope = 0.0
        
        # Attack and release coefficients
        self.attack_coef = np.exp(-1.0 / (AGC_ATTACK_TIME * 100))  # Assuming 100 frames per second
        self.release_coef = np.exp(-1.0 / (AGC_RELEASE_TIME * 100))
        
        # Peak level history for dynamic adjustments
        self.peak_level_history = deque(maxlen=100)
        
        logger.info(f"AGC initialized with target level {AGC_TARGET_LEVEL}")
    
    def _init_sockets(self):
        """Initialize all ZMQ sockets."""
        try:
            # Get audio capture service info using service discovery
            audio_capture_service = None
            try:
                audio_capture_service = discover_service("StreamingAudioCapture")
                if audio_capture_service and audio_capture_service.get("status") == "SUCCESS":
                    audio_capture_info = audio_capture_service.get("payload", {})
                    audio_capture_host = audio_capture_info.get("host", config.get("host"))
                    audio_capture_port = audio_capture_info.get("port", ZMQ_SUB_PORT)
                    logger.info(f"Discovered StreamingAudioCapture at {audio_capture_host}:{audio_capture_port}")
                else:
                    logger.warning("Could not discover StreamingAudioCapture, using configured host and port")
                    audio_capture_host = config.get("host")
                    audio_capture_port = ZMQ_SUB_PORT
            except Exception as e:
                logger.error(f"Error discovering StreamingAudioCapture: {e}")
                audio_capture_host = config.get("host")
                audio_capture_port = ZMQ_SUB_PORT
            
            # Subscribe to raw audio
            self.sub_socket = self.zmq_context.socket(zmq.SUB)
            
            # Apply secure ZMQ if enabled
            if SECURE_ZMQ:
                try:
                    from main_pc_code.src.network.secure_zmq import secure_client_socket, start_auth
                    start_auth()
                    self.sub_socket = secure_client_socket(self.sub_socket)
                    logger.info("Applied secure ZMQ to subscriber socket")
                except ImportError as e:
                    print(f"Import error: {e}")
                except Exception as e:
                    logger.error(f"Failed to apply secure ZMQ to subscriber socket: {e}")
            
            self.sub_socket.connect(f"tcp://{audio_capture_host}:{audio_capture_port}")
            self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            logger.info(f"Connected to audio capture at tcp://{audio_capture_host}:{audio_capture_port}")
            
            # Publish cleaned audio (same port as old NoiseReductionAgent)
            self.clean_audio_pub_socket = self.zmq_context.socket(zmq.PUB)
            
            # Apply secure ZMQ if enabled
            if SECURE_ZMQ:
                try:
                    from main_pc_code.src.network.secure_zmq import secure_server_socket
                    self.clean_audio_pub_socket = secure_server_socket(self.clean_audio_pub_socket)
                    logger.info("Applied secure ZMQ to clean audio publisher socket")
                except ImportError as e:
                    print(f"Import error: {e}")
                except Exception as e:
                    logger.error(f"Failed to apply secure ZMQ to clean audio publisher socket: {e}")
            
            self.clean_audio_pub_socket.bind(f"tcp://*:{ZMQ_CLEAN_AUDIO_PUB_PORT}")
            logger.info(f"Publishing clean audio on port {ZMQ_CLEAN_AUDIO_PUB_PORT}")
            
            # Publish VAD events (same port as old VADAgent)
            self.vad_pub_socket = self.zmq_context.socket(zmq.PUB)
            
            # Apply secure ZMQ if enabled
            if SECURE_ZMQ:
                try:
                    from main_pc_code.src.network.secure_zmq import secure_server_socket
                    self.vad_pub_socket = secure_server_socket(self.vad_pub_socket)
                    logger.info("Applied secure ZMQ to VAD publisher socket")
                except ImportError as e:
                    print(f"Import error: {e}")
                except Exception as e:
                    logger.error(f"Failed to apply secure ZMQ to VAD publisher socket: {e}")
            
            self.vad_pub_socket.bind(f"tcp://*:{ZMQ_VAD_PUB_PORT}")
            logger.info(f"Publishing VAD events on port {ZMQ_VAD_PUB_PORT}")
            
            # Register with SystemDigitalTwin
            try:
                from main_pc_code.utils.service_discovery_client import register_service
                register_service(
                    name="FusedAudioPreprocessor",
                    port=ZMQ_CLEAN_AUDIO_PUB_PORT,
                    additional_info={
                        "vad_port": ZMQ_VAD_PUB_PORT,
                        "health_port": ZMQ_HEALTH_PORT,
                        "description": "Fused audio preprocessing with noise reduction, VAD, AEC, and AGC"
                    }
                )
                logger.info("Registered with SystemDigitalTwin")
            except ImportError as e:
                print(f"Import error: {e}")
            except Exception as e:
                logger.error(f"Failed to register with SystemDigitalTwin: {e}")
            
            logger.info(f"ZMQ sockets initialized - Raw Audio SUB: {audio_capture_port}, Clean Audio PUB: {ZMQ_CLEAN_AUDIO_PUB_PORT}, VAD Events PUB: {ZMQ_VAD_PUB_PORT}")
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
                    self.noise_profile = np.concatenate(list(self.noise_samples))
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
            mean = np.mean(list(self.speech_prob_history))
            std = np.std(list(self.speech_prob_history))
            
            # Adjust threshold - higher when noisy, lower when quiet
            noise_level = mean
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
    
    def apply_aec(self, audio_data, sample_rate):
        """Apply Acoustic Echo Cancellation to remove echo from audio data."""
        if not AEC_ENABLED:
            return audio_data
        
        try:
            # Start timing for performance metrics
            start_time = time.time()
            
            # For a real implementation, we would get the reference signal from the audio output
            # Here we simulate it by using a delayed version of the last clean audio
            if self.simulated_reference and self.last_clean_audio is not None:
                # Create simulated echo by attenuating and delaying the last clean audio
                echo_attenuation = 0.3  # Echo is typically attenuated
                echo_delay_samples = int(0.05 * sample_rate)  # 50ms delay
                
                # Pad reference signal to match current audio length
                if len(self.last_clean_audio) >= len(audio_data) + echo_delay_samples:
                    reference_signal = self.last_clean_audio[:len(audio_data)] * echo_attenuation
                else:
                    # Pad with zeros if not enough samples
                    reference_signal = np.zeros(len(audio_data))
                    reference_signal[:len(self.last_clean_audio)] = self.last_clean_audio * echo_attenuation
            else:
                # No reference signal available, use zeros
                reference_signal = np.zeros(len(audio_data))
            
            # Update reference buffer with new reference signal
            self.reference_buffer = np.roll(self.reference_buffer, -len(reference_signal))
            self.reference_buffer[-len(reference_signal):] = reference_signal
            
            # Apply Normalized Least Mean Square (NLMS) adaptive filter
            output = np.zeros(len(audio_data))
            for i in range(len(audio_data)):
                # Extract reference window
                ref_window = self.reference_buffer[i:i+AEC_FILTER_LENGTH]
                
                # Estimate echo using current filter
                echo_estimate = np.dot(self.aec_filter, ref_window)
                
                # Calculate error (desired signal - echo estimate)
                error = audio_data[i] - echo_estimate
                
                # Update filter coefficients using NLMS
                ref_power = np.dot(ref_window, ref_window)
                if ref_power > 1e-10:  # Avoid division by zero
                    adaptation = AEC_STEP_SIZE / ref_power
                    self.aec_filter = AEC_LEAK_FACTOR * self.aec_filter + adaptation * error * ref_window
                
                # Store output
                output[i] = error
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Log performance metrics periodically
            if np.random.random() < 0.01:  # Log approximately 1% of frames
                logger.debug(f"AEC processing time: {processing_time*1000:.2f}ms for {len(audio_data)} samples")
            
            return output
            
        except Exception as e:
            logger.error(f"Error in AEC processing: {str(e)}")
            return audio_data  # Return original audio on error
    
    def apply_agc(self, audio_data, sample_rate):
        """Apply Automatic Gain Control to normalize audio volume."""
        if not AGC_ENABLED:
            return audio_data
        
        try:
            # Start timing for performance metrics
            start_time = time.time()
            
            # Calculate RMS level of the current frame
            if len(audio_data) > 0:
                rms = np.sqrt(np.mean(audio_data**2))
            else:
                rms = 0.0
            
            # Update envelope with attack/release smoothing
            if rms > self.envelope:
                # Attack phase (quick increase)
                self.envelope = self.attack_coef * self.envelope + (1 - self.attack_coef) * rms
            else:
                # Release phase (slow decrease)
                self.envelope = self.release_coef * self.envelope + (1 - self.release_coef) * rms
            
            # Store peak level for statistics
            self.peak_level_history.append(self.envelope)
            
            # Calculate target gain
            if self.envelope > 1e-6:  # Avoid division by zero
                target_gain = AGC_TARGET_LEVEL / self.envelope
                
                # Limit gain to specified range
                target_gain = min(max(target_gain, AGC_MIN_GAIN), AGC_MAX_GAIN)
                
                # Smooth gain changes
                gain_change_rate = 0.1  # Adjust gain by 10% towards target per frame
                self.current_gain = (1 - gain_change_rate) * self.current_gain + gain_change_rate * target_gain
            else:
                # Very low signal, maintain current gain
                pass
            
            # Apply gain to audio
            normalized_audio = audio_data * self.current_gain
            
            # Prevent clipping
            if np.max(np.abs(normalized_audio)) > 0.99:
                scaling_factor = 0.99 / np.max(np.abs(normalized_audio))
                normalized_audio = normalized_audio * scaling_factor
                # Adjust current gain for next frame
                self.current_gain = self.current_gain * scaling_factor
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Log performance metrics periodically
            if np.random.random() < 0.01:  # Log approximately 1% of frames
                logger.debug(f"AGC processing time: {processing_time*1000:.2f}ms, current gain: {self.current_gain:.2f}")
            
            return normalized_audio
            
        except Exception as e:
            logger.error(f"Error in AGC processing: {str(e)}")
            return audio_data  # Return original audio on error
    
    def process_audio_loop(self):
        """Main audio processing loop."""
        logger.info("Starting audio processing loop")
        
        while self._running:
            try:
                # Check for new audio data with timeout
                try:
                    message = self.sub_socket.recv(flags=zmq.NOBLOCK)
                    data = pickle.loads(message)
                except zmq.Again:
                    time.sleep(0.001)  # Short sleep to avoid busy waiting
                    continue
                except Exception as e:
                    logger.error(f"Error receiving audio data: {str(e)}")
                    continue
                
                # Extract audio data and metadata
                audio_data = data.get('audio', None)
                sample_rate = data.get('sample_rate', 16000)
                timestamp = data.get('timestamp', time.time())
                
                if audio_data is None:
                    logger.warning("Received message with no audio data")
                    continue
                
                # Start timing for performance metrics
                start_time = time.time()
                
                # Resample audio if needed for VAD
                resampled_audio = self._resample_audio(audio_data, sample_rate)
                
                # Process audio with full pipeline:
                
                # 1. Apply Acoustic Echo Cancellation (AEC)
                if AEC_ENABLED:
                    echo_cancelled_audio = self.apply_aec(audio_data, sample_rate)
                else:
                    echo_cancelled_audio = audio_data
                
                # 2. Apply Noise Reduction
                if self.is_collecting_noise:
                    # Still collecting noise profile
                    self.noise_samples.append(echo_cancelled_audio)
                    self.noise_sample_count += 1
                    
                    if self.noise_sample_count >= self.noise_sample_target:
                        # Concatenate noise samples to create profile
                        self.noise_profile = np.concatenate(list(self.noise_samples))
                        logger.info(f"Noise profile collected: {len(self.noise_profile)} samples")
                        self.is_collecting_noise = False
                    
                    # Pass through audio while collecting noise
                    clean_audio = echo_cancelled_audio
                else:
                    # Apply noise reduction with collected profile
                    clean_audio = self.apply_noise_reduction(echo_cancelled_audio, sample_rate)
                
                # 3. Perform Voice Activity Detection (VAD)
                speech_prob, speech_detected = self.detect_speech(resampled_audio, VAD_SAMPLE_RATE)
                
                # 4. Apply Automatic Gain Control (AGC)
                if AGC_ENABLED:
                    # Only apply AGC to speech segments to avoid amplifying noise
                    if speech_detected or speech_prob > 0.3:  # Apply AGC even to low probability speech
                        normalized_audio = self.apply_agc(clean_audio, sample_rate)
                    else:
                        normalized_audio = clean_audio
                else:
                    normalized_audio = clean_audio
                
                # Store clean audio for AEC reference simulation
                self.last_clean_audio = normalized_audio
                
                # Calculate total processing time
                processing_time = time.time() - start_time
                
                # Publish cleaned audio
                clean_audio_message = {
                    'audio': normalized_audio,
                    'sample_rate': sample_rate,
                    'timestamp': timestamp,
                    'processing_time': processing_time,
                    'speech_probability': float(speech_prob),
                    'aec_enabled': AEC_ENABLED,
                    'agc_enabled': AGC_ENABLED,
                    'agc_gain': float(self.current_gain) if AGC_ENABLED else 1.0
                }
                self.clean_audio_pub_socket.send(pickle.dumps(clean_audio_message))
                
                # Track speech state changes and publish VAD events
                if speech_detected and not self.speech_active:
                    # Speech start
                    self.speech_active = True
                    self.speech_start_time = timestamp
                    self._publish_vad_event('speech_start', speech_prob)
                elif not speech_detected and self.speech_active:
                    # Speech end
                    self.speech_active = False
                    self.last_speech_end_time = timestamp
                    speech_duration = timestamp - self.speech_start_time if self.speech_start_time else 0
                    self._publish_vad_event('speech_end', speech_prob, speech_duration)
                
                # Log performance metrics periodically
                if np.random.random() < 0.01:  # Log approximately 1% of frames
                    logger.debug(f"Total processing time: {processing_time*1000:.2f}ms, speech prob: {speech_prob:.2f}")
                
            except Exception as e:
                logger.error(f"Error in audio processing loop: {str(e)}")
                time.sleep(0.1)  # Sleep briefly on error to avoid tight loop
    
    def _get_health_status(self):
        """Overrides the base method to add agent-specific health metrics."""
        base_status = super()._get_health_status()
        specific_metrics = {
            "processor_status": "active" if getattr(self, '_running', False) else "inactive",
            "input_buffer_fill": getattr(self, 'input_buffer_fill_rate', 'N/A'),
            "output_buffer_fill": getattr(self, 'output_buffer_fill_rate', 'N/A')
        }
        base_status.update(specific_metrics)
        return base_status
    
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
        
        # Close ZMQ sockets
        try:
            if hasattr(self, 'sub_socket'):
                self.sub_socket.close()
            if hasattr(self, 'clean_audio_pub_socket'):
                self.clean_audio_pub_socket.close()
            if hasattr(self, 'vad_pub_socket'):
                self.vad_pub_socket.close()
            
            # Terminate ZMQ context
            if hasattr(self, 'zmq_context'):
                self.zmq_context.term()
                
            logger.info("All ZMQ sockets closed and context terminated")
        except Exception as e:
            logger.error(f"Error closing ZMQ sockets: {e}")
        
        # At the end of this method, call super().cleanup()
        super().cleanup()
        
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

# -------------------- Agent Entrypoint --------------------
if __name__ == "__main__":
    # Configure basic logging
    logging.basicConfig(level=logging.INFO)
    
    # Standardized main execution block
    agent = None
    try:
        agent = FusedAudioPreprocessorAgent()
        logger.info(f"Starting FusedAudioPreprocessorAgent on port {agent.port}")
        agent.run()
    except KeyboardInterrupt:
        logger.info("FusedAudioPreprocessorAgent interrupted by user")
    except Exception as e:
        import traceback
        logger.error(f"An unexpected error occurred in FusedAudioPreprocessorAgent: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            logger.info("Cleaning up FusedAudioPreprocessorAgent...")
            agent.cleanup() 