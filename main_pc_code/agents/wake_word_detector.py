from common.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config

"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

Wake Word Detector
----------------
Integrates with existing streaming pipeline:
- Uses Porcupine for wake word detection
- Publishes wake word events via ZMQ
- Coordinates with streaming_audio_capture.py
- Integrates with VAD for improved accuracy
"""

import pvporcupine
import pyaudio
import numpy as np
import json
import os
import logging
import threading
import zmq
import time
import pickle
from datetime import datetime
from typing import Optional, Dict, Any
from main_pc_code.utils.env_loader import get_env
import psutil

# Load configuration at module level
config = load_config()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wake_word_detector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ZMQ Configuration
ZMQ_PUB_PORT = int(config.get("port", 6577))
ZMQ_HEALTH_PORT = 6579
ZMQ_AUDIO_PORT = 6575  # Port for receiving audio from streaming_audio_capture.py
ZMQ_VAD_PORT = 6579    # Port for receiving VAD events

class WakeWordDetectorAgent(
    """
    WakeWordDetectorAgent:  Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
    """BaseAgent):
    def __init__(self, port=None, wake_word_path=None, sensitivity=0.5, energy_threshold=300):
        # Get configuration values with fallbacks
        agent_port = int(config.get("port", 5705)) if port is None else port
        agent_name = config.get("name", "WakeWordDetectorAgent")
        bind_address = config.get("bind_address", get_env('BIND_ADDRESS', '<BIND_ADDR>'))
        zmq_timeout = int(config.get("zmq_request_timeout", 5000))
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=agent_name, port=agent_port)
        
        # Store important attributes
        self.bind_address = bind_address
        self.zmq_timeout = zmq_timeout
        self.start_time = time.time()
        
        """
        Initialize the wake word detector.
        
        Args:
            wake_word_path: Path to the .ppn wake word model file
            sensitivity: Wake word detection sensitivity (0.0 to 1.0)
            energy_threshold: Voice activity detection energy threshold
        """
        self.wake_word_path = wake_word_path
        self.sensitivity = sensitivity
        self.energy_threshold = energy_threshold
        
        # Load API key
        self._load_api_key()
        
        # Initialize state
        self.is_running = False
        self.last_detection_time = 0
        self.detection_cooldown = 0.5  # Cooldown period in seconds
        self.vad_speech_active = False  # Track if VAD has detected speech
        self.vad_confidence = 0.0       # Current VAD confidence
        self.vad_last_update = 0        # Last time VAD status was updated
        
        # Initialize ZMQ
        self._init_zmq()
        
        # Initialize Porcupine
        self._init_porcupine()
        
        # Set running flag
        self.running = True
        
        logger.info("Wake word detector initialized")
    
    

        self.error_bus_port = 7150

        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')

        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"

        self.error_bus_pub = self.context.socket(zmq.PUB)

        self.error_bus_pub.connect(self.error_bus_endpoint)
def _load_api_key(self):
        """Load Porcupine API key from config file."""
        try:
            config_path = os.path.join('config', 'api_keys.json')
            with open(config_path, 'r') as f:
                config = json.load(f)
            self.access_key = config.get('PORCUPINE_ACCESS_KEY')
            if not self.access_key:
                raise ValueError("PORCUPINE_ACCESS_KEY not found in config")
        except Exception as e:
            logger.error(f"Error loading API key: {str(e)}")
            raise
    
    def _init_zmq(self):
        """Initialize ZMQ context and sockets."""
        try:
            self.zmq_context = zmq.Context()
            
            # Create SUB socket for audio
            self.audio_socket = self.zmq_context.socket(zmq.SUB)
            self.audio_socket.connect(f"tcp://{self.bind_address}:{ZMQ_AUDIO_PORT}")
            self.audio_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            
            # Create SUB socket for VAD events
            self.vad_socket = self.zmq_context.socket(zmq.SUB)
            self.vad_socket.connect(f"tcp://{self.bind_address}:{ZMQ_VAD_PORT}")
            self.vad_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            
            # Create PUB socket for wake word events
            self.pub_socket = self.zmq_context.socket(zmq.PUB)
            self.pub_socket.bind(f"tcp://*:{self.port}")
            
            # Create PUB socket for health status
            self.health_socket = self.zmq_context.socket(zmq.PUB)
            self.health_socket.bind(f"tcp://*:{ZMQ_HEALTH_PORT}")
            
            logger.info(f"ZMQ sockets initialized - Audio SUB: {ZMQ_AUDIO_PORT}, VAD SUB: {ZMQ_VAD_PORT}, Event PUB: {self.port}, Health: {ZMQ_HEALTH_PORT}")
        except Exception as e:
            logger.error(f"Error initializing ZMQ: {str(e)}")
            raise
    
    def _init_porcupine(self):
        """Initialize Porcupine wake word engine."""
        try:
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keyword_paths=[self.wake_word_path],
                sensitivities=[self.sensitivity]
            )
            self.frame_length = self.porcupine.frame_length
            self.sample_rate = self.porcupine.sample_rate
            logger.info(f"Porcupine initialized with frame length {self.frame_length} and sample rate {self.sample_rate}")
        except Exception as e:
            logger.error(f"Error initializing Porcupine: {str(e)}")
            raise
    
    def _calculate_energy(self, audio_data: np.ndarray) -> float:
        """Calculate audio energy level."""
        try:
            energy = np.sqrt(np.mean(np.square(audio_data)))
            return energy
        except Exception as e:
            logger.error(f"Error calculating energy: {str(e)}")
            return 0.0
    
    def _convert_audio_format(self, audio_data: np.ndarray) -> bytes:
        """Convert float32 audio data to int16 format for Porcupine."""
        try:
            # Scale float32 (-1.0 to 1.0) to int16 (-32768 to 32767)
            scaled = np.clip(audio_data * 32767, -32768, 32767)
            return scaled.astype(np.int16).tobytes()
        except Exception as e:
            logger.error(f"Error converting audio format: {str(e)}")
            return b''
    
    def _publish_wake_word_event(self, confidence: float):
        """Publish wake word detection event via ZMQ."""
        try:
            event = {
                'timestamp': datetime.now().isoformat(),
                'type': 'wake_word_detected',
                'confidence': confidence,
                'vad_active': self.vad_speech_active,
                'vad_confidence': self.vad_confidence
            }
            self.pub_socket.send_json(event)
            logger.info(f"Published wake word event: {event}")
        except Exception as e:
            logger.error(f"Error publishing wake word event: {str(e)}")
    
    def _publish_health_status(self):
        """Publish health status via ZMQ."""
        try:
            status = {
                'timestamp': datetime.now().isoformat(),
                'type': 'health_status',
                'status': 'running',
                'component': 'wake_word_detector',
                'vad_integration': True,
                'vad_speech_active': self.vad_speech_active,
                'vad_confidence': self.vad_confidence,
                'vad_last_update': self.vad_last_update
            }
            self.health_socket.send_json(status)
        except Exception as e:
            logger.error(f"Error publishing health status: {str(e)}")
    
    def _check_vad_events(self):
        """Check for VAD events from the VAD Agent."""
        try:
            # Non-blocking check for VAD events
            try:
                event = self.vad_socket.recv_json(flags=zmq.NOBLOCK)
                event_type = event.get('type')
                
                if event_type == 'speech_start':
                    self.vad_speech_active = True
                    self.vad_confidence = event.get('confidence', 0.0)
                    self.vad_last_update = time.time()
                    logger.debug(f"VAD speech start detected with confidence {self.vad_confidence:.2f}")
                    
                elif event_type == 'speech_end':
                    self.vad_speech_active = False
                    self.vad_last_update = time.time()
                    logger.debug("VAD speech end detected")
                    
                elif event_type == 'speech_prob':
                    # Update confidence but don't change speech active state
                    self.vad_confidence = event.get('confidence', 0.0)
                    self.vad_last_update = time.time()
            except zmq.Again:
                pass  # No VAD events available
        except Exception as e:
            logger.error(f"Error checking VAD events: {str(e)}")
    
    def _audio_capture_thread(self):
        """Thread for capturing audio and detecting wake word."""
        while self.is_running:
            try:
                # Check for VAD events
                self._check_vad_events()
                
                # Read audio data from ZMQ
                try:
                    message = self.audio_socket.recv(flags=zmq.NOBLOCK)
                    data = pickle.loads(message)
                    audio_data = data.get('audio_chunk')
                    if audio_data is None:
                        continue
                except zmq.Again:
                    time.sleep(0.01)  # Shorter sleep to check VAD more frequently
                    continue
                except Exception as e:
                    logger.error(f"Error receiving audio data: {str(e)}")
                    continue
                
                # Convert audio data to the format Porcupine expects
                audio_bytes = self._convert_audio_format(audio_data)
                if not audio_bytes:
                    continue
                
                energy = self._calculate_energy(audio_data)
                
                # Check cooldown period
                current_time = time.time()
                if current_time - self.last_detection_time < self.detection_cooldown:
                    continue
                
                # Process frame if energy is above threshold AND VAD indicates speech
                # Fall back to just energy threshold if VAD is not active or outdated
                vad_valid = (time.time() - self.vad_last_update) < 0.5  # VAD data is recent
                
                if (vad_valid and self.vad_speech_active) or (not vad_valid and energy > self.energy_threshold):
                    result = self.porcupine.process(audio_bytes)
                    if result >= 0:
                        # Wake word detected
                        self.last_detection_time = current_time
                        confidence = self._calculate_confidence(energy)
                        self._publish_wake_word_event(confidence)
                
            except Exception as e:
                logger.error(f"Error in audio capture: {str(e)}")
                time.sleep(0.1)
    
    def _health_broadcast_thread(self):
        """Thread for broadcasting health status."""
        while self.is_running:
            try:
                self._publish_health_status()
                time.sleep(1)  # Broadcast every second
            except Exception as e:
                logger.error(f"Error in health broadcast: {str(e)}")
                time.sleep(1)
    
    def _calculate_confidence(self, energy: float) -> float:
        """Calculate confidence score for wake word detection."""
        try:
            # Normalize energy (0-1 range)
            energy_score = min(1.0, energy / (self.energy_threshold * 2))
            
            # Add a base confidence for detected wake words
            confidence = 0.5 + (0.5 * energy_score)
            
            return confidence
        except Exception as e:
            logger.error(f"Error calculating confidence: {str(e)}")
            return 0.0
    
    def start(self):
        """Start the wake word detector."""
        if not self.is_running:
            self.is_running = True
            
            # Start threads
            self.capture_thread = threading.Thread(target=self._audio_capture_thread)
            self.health_thread = threading.Thread(target=self._health_broadcast_thread)
            
            self.capture_thread.daemon = True
            self.health_thread.daemon = True
            
            self.capture_thread.start()
            self.health_thread.start()
            
            logger.info("Wake word detector started")
    
    def stop(self):
        """Stop the wake word detector."""
        if self.is_running:
            self.is_running = False
            
            # Wait for threads to finish
            if hasattr(self, 'capture_thread'):
                self.capture_thread.join()
            if hasattr(self, 'health_thread'):
                self.health_thread.join()
            
            # Clean up resources
            self.porcupine.delete()
            
            # Close ZMQ sockets
            self.audio_socket.close()
            self.pub_socket.close()
            self.health_socket.close()
            self.zmq_context.term()
            
            logger.info("Wake word detector stopped")
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise


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


    def _get_health_status(self):
        # Default health status: Agent is running if its main loop is active.
        # This can be expanded with more specific checks later.
        status = "HEALTHY" if self.running else "UNHEALTHY"
        details = {
            "status_message": "Agent is operational.",
            "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else 0
        }
        return {"status": status, "details": details}

# -------------------- Agent Entrypoint --------------------
if __name__ == "__main__":
    # Configure basic logging
    logging.basicConfig(level=logging.INFO)
    
    # Standardized main execution block
    agent = None
    try:
        # Load configuration from config file
        wake_word_path = config.get("wake_word_path", "path/to/default_wake_word.ppn")
        sensitivity = float(config.get("sensitivity", 0.5))
        energy_threshold = int(config.get("energy_threshold", 300))
        
        logger.info("Starting WakeWordDetectorAgent...")
        agent = WakeWordDetectorAgent(
            wake_word_path=wake_word_path,
            sensitivity=sensitivity,
            energy_threshold=energy_threshold
        )
        agent.run()
    except KeyboardInterrupt:
        logger.info("WakeWordDetectorAgent interrupted by user")
    except Exception as e:
        import traceback
        logger.error(f"An unexpected error occurred in WakeWordDetectorAgent: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            logger.info("Cleaning up WakeWordDetectorAgent...")
            agent.cleanup() 