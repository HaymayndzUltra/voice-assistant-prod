from main_pc_code.src.core.base_agent import BaseAgent
"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

Voice Activity Detection (VAD) Agent
----------------------------------
Implements state-of-the-art voice activity detection:
- Uses Silero VAD model for accurate speech detection
- Subscribes to raw or cleaned audio stream
- Publishes voice activity events to other components
- Helps improve wake word detection and speech recognition
"""

import zmq
import pickle
import numpy as np
import time
import threading
import logging
import os
import torch
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import deque
import psutil
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vad_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ZMQ Configuration
ZMQ_SUB_PORT = 6578  # Clean audio from noise_reduction_agent.py (or 6575 for raw audio)
ZMQ_PUB_PORT = 6579  # Voice activity events
ZMQ_HEALTH_PORT = 6580  # Health status

# VAD Settings
VAD_THRESHOLD = 0.5  # Voice detection threshold (0.0-1.0)
VAD_WINDOW_SIZE_MS = 96  # Window size in milliseconds
VAD_SAMPLE_RATE = 16000  # Sample rate expected by the model
VAD_MIN_SPEECH_DURATION_MS = 250  # Minimum speech duration to trigger (ms)
VAD_MIN_SILENCE_DURATION_MS = 100  # Minimum silence duration to reset (ms)
VAD_SPEECH_PAD_MS = 30  # Padding around speech segments (ms)
VAD_USE_ADAPTIVE_THRESHOLD = True  # Dynamically adjust threshold based on ambient noise

class VADAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="VadAgent")
        """Initialize the VAD agent."""
        self._running = False
        self._thread = None
        self.health_thread = None
        
        # Initialize ZMQ context
        self.zmq_context = zmq.Context()
        
        # Initialize sockets
        self._init_sockets()
        
        # Initialize VAD model
        self._init_vad_model()
        
        # Initialize state
        self.speech_active = False
        self.speech_start_time = None
        self.last_speech_end_time = None
        self.audio_buffer = deque(maxlen=int(VAD_SAMPLE_RATE * 1.0))  # 1 second buffer
        self.speech_prob_history = deque(maxlen=50)  # Store recent speech probabilities
        self.adaptive_threshold = VAD_THRESHOLD
        
        logger.info("VAD Agent initialized")
    
    def _init_sockets(self):
        """Initialize all ZMQ sockets."""
        try:
            # Subscribe to audio (clean or raw)
            self.sub_socket = self.zmq_context.socket(zmq.SUB)
            self.sub_socket.connect(f"tcp://localhost:{ZMQ_SUB_PORT}")
            self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            
            # Publish voice activity events
            self.pub_socket = self.zmq_context.socket(zmq.PUB)
            self.pub_socket.bind(f"tcp://*:{ZMQ_PUB_PORT}")
            
            # Health status
            self.health_socket = self.zmq_context.socket(zmq.PUB)
            self.health_socket.bind(f"tcp://*:{ZMQ_HEALTH_PORT}")
            
            logger.info(f"ZMQ sockets initialized - Audio SUB: {ZMQ_SUB_PORT}, VAD Events PUB: {ZMQ_PUB_PORT}, Health: {ZMQ_HEALTH_PORT}")
        except Exception as e:
            logger.error(f"Error initializing ZMQ sockets: {str(e)}")
            
            # Send standardized error message
            error_message = {
                "status": "error",
                "error_type": "AgentInitializationError",
                "source_agent": "vad_agent.py",
                "message": f"Failed to initialize ZMQ sockets: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            try:
                # If pub_socket is already initialized, try to send the error
                if hasattr(self, 'pub_socket') and self.pub_socket:
                    self.pub_socket.send_json(error_message)
            except Exception:
                pass  # If we can't send the error, we're already in a bad state
                
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
            self.get_speech_timestamps = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=True,
                onnx=False,
                verbose=False
            )['get_speech_timestamps']
            
            # Initialize the VAD processing function
            self.vad = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=True,
                onnx=False,
                verbose=False
            )['vad']
            
            logger.info("Silero VAD model loaded successfully")
        except Exception as e:
            logger.error(f"Error initializing VAD model: {str(e)}")
            
            # Send standardized error message
            error_message = {
                "status": "error",
                "error_type": "ModelLoadError",
                "source_agent": "vad_agent.py",
                "message": f"Failed to load Silero VAD model: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "device": str(self.device) if hasattr(self, 'device') else "unknown",
                    "model_path": str(model_path) if 'model_path' in locals() else "unknown"
                }
            }
            try:
                if hasattr(self, 'pub_socket') and self.pub_socket:
                    self.pub_socket.send_json(error_message)
                    logger.info("Published model load error message")
            except Exception as pub_error:
                logger.error(f"Failed to publish error message: {str(pub_error)}")
            
            # Fallback to a simple energy-based VAD
            self.model = None
            logger.warning("Falling back to simple energy-based VAD")
    
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
            
            # Send standardized error message
            error_message = {
                "status": "error",
                "error_type": "AudioProcessingError",
                "source_agent": "vad_agent.py",
                "message": f"Failed to resample audio: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "original_sample_rate": original_sample_rate,
                    "target_sample_rate": VAD_SAMPLE_RATE,
                    "audio_data_length": len(audio_data) if audio_data is not None else 0
                }
            }
            try:
                self.pub_socket.send_json(error_message)
                logger.info("Published resampling error message")
            except Exception as pub_error:
                logger.error(f"Failed to publish error message: {str(pub_error)}")
            
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
    
    def _detect_speech_silero(self, audio_data):
        """Detect speech using Silero VAD model."""
        try:
            # Convert to tensor and move to device
            tensor = torch.from_numpy(audio_data).float().to(self.device)
            
            # Get speech probability
            speech_prob = self.vad(tensor, VAD_SAMPLE_RATE).item()
            
            # Update adaptive threshold
            self._update_adaptive_threshold(speech_prob)
            
            # Determine if speech is active based on threshold
            is_speech = speech_prob > self.adaptive_threshold
            
            return is_speech, speech_prob
        except Exception as e:
            logger.error(f"Error in Silero VAD processing: {str(e)}")
            
            # Send standardized error message
            error_message = {
                "status": "error",
                "error_type": "VADError",
                "source_agent": "vad_agent.py",
                "message": f"Failed to process audio with Silero VAD: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "audio_data_length": len(audio_data) if audio_data is not None else 0,
                    "adaptive_threshold": self.adaptive_threshold
                }
            }
            try:
                self.pub_socket.send_json(error_message)
                logger.info("Published Silero VAD error message")
            except Exception as pub_error:
                logger.error(f"Failed to publish error message: {str(pub_error)}")
            
            # Fallback to energy-based detection
            return self._detect_speech_energy(audio_data)
    
    def _detect_speech_energy(self, audio_data):
        """Simple energy-based voice activity detection."""
        try:
            # Calculate audio energy
            energy = np.mean(np.abs(audio_data))
            
            # Determine if speech is active based on energy threshold
            is_speech = energy > 0.05  # Simple energy threshold
            
            return is_speech, energy
        except Exception as e:
            logger.error(f"Error in energy-based VAD: {str(e)}")
            
            # Send standardized error message
            error_message = {
                "status": "error",
                "error_type": "VADError",
                "source_agent": "vad_agent.py",
                "message": f"Failed to process audio with energy-based VAD: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "audio_data_length": len(audio_data) if audio_data is not None else 0
                }
            }
            try:
                self.pub_socket.send_json(error_message)
                logger.info("Published energy VAD error message")
            except Exception as pub_error:
                logger.error(f"Failed to publish error message: {str(pub_error)}")
            
            # Return default values as last resort
            return False, 0.0
    
    def _publish_vad_event(self, event_type, speech_prob=None):
        """Publish a voice activity detection event."""
        try:
            event = {
                'type': event_type,
                'timestamp': datetime.now().isoformat(),
                'probability': speech_prob
            }
            
            self.pub_socket.send_json(event)
            logger.debug(f"Published VAD event: {event_type}")
        except Exception as e:
            logger.error(f"Error publishing VAD event: {str(e)}")
            
            # Send standardized error message about publishing failure
            error_message = {
                "status": "error",
                "error_type": "CommunicationError",
                "source_agent": "vad_agent.py",
                "message": f"Failed to publish VAD event: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "event_type": event_type,
                    "speech_probability": speech_prob
                }
            }
            try:
                # Try again with the error message
                self.pub_socket.send_json(error_message)
            except Exception:
                # If we still can't send, log and continue
                logger.critical("Failed to publish error message, communication channel may be down")
    
    def process_audio_loop(self):
        """Main processing loop for audio data."""
        logger.info("Starting audio processing loop")
        
        while self._running:
            try:
                # Check for input message
                try:
                    message = self.sub_socket.recv(flags=zmq.NOBLOCK)
                    
                    # Check if message is a JSON (potential error message from upstream)
                    try:
                        # Try to parse as JSON first (for error messages)
                        if message.startswith(b'{"status":"error"'):
                            error_data = json.loads(message)
                            if error_data.get("status") == "error":
                                # Log received error
                                logger.warning(f"Received error from upstream component: {error_data.get('source_agent')} - {error_data.get('message')}")
                                
                                # Forward the error downstream
                                self.pub_socket.send_json(error_data)
                                continue
                    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                        # Not a JSON message, process as normal audio data
                        pass
                    
                    # Process binary data (normal audio)
                    try:
                        data = pickle.loads(message)
                        audio_chunk = data.get('audio_chunk')
                        sample_rate = data.get('sample_rate', 16000)
                        
                        if audio_chunk is None:
                            # Send standardized error for missing audio chunk
                            error_message = {
                                "status": "error",
                                "error_type": "AudioProcessingError",
                                "source_agent": "vad_agent.py",
                                "message": "Received empty audio chunk",
                                "timestamp": datetime.now().isoformat()
                            }
                            self.pub_socket.send_json(error_message)
                            logger.warning("Received empty audio chunk, sent error message")
                            continue
                        
                        # Resample if needed
                        if sample_rate != VAD_SAMPLE_RATE:
                            audio_chunk = self._resample_audio(audio_chunk, sample_rate)
                        
                        # Add to buffer (for future implementation of windowing)
                        for sample in audio_chunk:
                            self.audio_buffer.append(sample)
                        
                        # Detect speech
                        start_time = time.time()
                        if self.model is not None:
                            is_speech, speech_prob = self._detect_speech_silero(np.array(list(self.audio_buffer)))
                        else:
                            is_speech, speech_prob = self._detect_speech_energy(np.array(list(self.audio_buffer)))
                        
                        # Calculate processing time
                        processing_time = (time.time() - start_time) * 1000
                        logger.info(f"PERF_METRIC: [VADAgent] - [SpeechDetection] - Duration: {processing_time:.2f}ms")
                        
                        # Handle speech state changes
                        current_time = time.time()
                        
                        if is_speech and not self.speech_active:
                            # Speech started
                            self.speech_active = True
                            self.speech_start_time = current_time
                            self._publish_vad_event('speech_start', speech_prob)
                            logger.info(f"Speech started (prob: {speech_prob:.2f})")
                        
                        elif not is_speech and self.speech_active:
                            # Check if silence duration exceeds minimum
                            if (current_time - self.speech_start_time) > (VAD_MIN_SPEECH_DURATION_MS / 1000):
                                # Speech ended
                                self.speech_active = False
                                self.last_speech_end_time = current_time
                                self._publish_vad_event('speech_end', speech_prob)
                                logger.info(f"Speech ended (prob: {speech_prob:.2f})")
                        
                        elif is_speech and self.speech_active:
                            # Ongoing speech
                            if (current_time - self.speech_start_time) > 0.5:  # Send updates every 500ms
                                self._publish_vad_event('speech_ongoing', speech_prob)
                                self.speech_start_time = current_time  # Reset timer for next update
                    
                    except pickle.UnpicklingError as pe:
                        # Handle corrupt data with standardized error
                        error_message = {
                            "status": "error",
                            "error_type": "MessageFormatError",
                            "source_agent": "vad_agent.py",
                            "message": f"Failed to unpickle received data: {str(pe)}",
                            "timestamp": datetime.now().isoformat()
                        }
                        self.pub_socket.send_json(error_message)
                        logger.error(f"Unpickling error: {str(pe)}")
                        time.sleep(0.1)
                    
                except zmq.Again:
                    time.sleep(0.01)  # Small sleep when no messages
                    continue
                
            except Exception as e:
                logger.error(f"Error in audio processing loop: {str(e)}")
                
                # Send standardized error message
                try:
                    error_message = {
                        "status": "error",
                        "error_type": "VADError",
                        "source_agent": "vad_agent.py",
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
    
    def health_broadcast_loop(self):
        """Loop for broadcasting health status."""
        logger.info("Starting health broadcast loop")
        
        while self._running:
            try:
                # Prepare health status
                status = {
                    'component': 'VADAgent',
                    'status': 'healthy',
                    'timestamp': datetime.now().isoformat(),
                    'model_loaded': self.model is not None,
                    'speech_active': self.speech_active,
                    'adaptive_threshold': self.adaptive_threshold,
                    'device': str(self.device) if hasattr(self, 'device') else "unknown"
                }
                
                # Send health status
                self.health_socket.send_json(status)
                
                # Sleep until next update
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in health broadcast loop: {str(e)}")
                time.sleep(5)  # Sleep on error, but shorter to recover faster
    
    def start(self):
        """Start the VAD agent."""
        if self._running:
            logger.warning("VAD agent is already running")
            return
            
        self._running = True
        
        # Start audio processing thread
        self._thread = threading.Thread(target=self.process_audio_loop)
        self._thread.daemon = True
        self._thread.start()
        
        # Start health broadcast thread
        self.health_thread = threading.Thread(target=self.health_broadcast_loop)
        self.health_thread.daemon = True
        self.health_thread.start()
        
        logger.info("VAD agent started")
    
    def stop(self):
        """Stop the VAD agent."""
        logger.info("Stopping VAD agent")
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=2)
        if self.health_thread:
            self.health_thread.join(timeout=2)
            
        # Close ZMQ sockets
        self.sub_socket.close()
        self.pub_socket.close()
        self.health_socket.close()
        
        logger.info("VAD agent stopped")
    
    def run(self):
        """Run the VAD agent."""
        try:
            logger.info("Starting VAD agent")
            self.start()
            
            # Keep main thread alive
            while self._running:
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception as e:
            logger.error(f"Error in VAD agent: {str(e)}")
            
            # Send standardized error message for fatal errors
            try:
                error_message = {
                    "status": "error",
                    "error_type": "AgentShutdownError",
                    "source_agent": "vad_agent.py",
                    "message": f"Fatal error in VAD agent: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
                if hasattr(self, 'pub_socket') and self.pub_socket:
                    self.pub_socket.send_json(error_message)
            except Exception:
                pass  # If we can't send the error, we're already in a bad state
                
        finally:
            self.stop()


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
    agent = VADAgent()
    agent.run() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise