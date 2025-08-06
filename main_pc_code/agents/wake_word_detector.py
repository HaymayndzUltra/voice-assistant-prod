from common.core.base_agent import BaseAgent
from common.config_manager import load_unified_config
from common.utils.path_manager import PathManager
from common.utils.env_standardizer import get_env
from main_pc_code.agents.error_publisher import ErrorPublisher

"""
Wake Word Detector
----------------
Integrates with existing streaming pipeline:
- Uses Porcupine for wake word detection
- Publishes wake word events via ZMQ
- Coordinates with streaming_audio_capture.py
- Integrates with VAD for improved accuracy
"""

import pvporcupine
import numpy as np
import json
import os
import logging
from common.utils.log_setup import configure_logging
import threading
import time
import pickle
from datetime import datetime
import psutil

# Load configuration at module level
config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))

# Configure logging
logger = configure_logging(__name__, log_to_file=True)

# ZMQ Configuration from config with fallbacks
ZMQ_PUB_PORT = int(config.get("pub_port", 6577))
ZMQ_HEALTH_PORT = int(config.get("health_port", 6579))
ZMQ_AUDIO_PORT = int(config.get("audio_port", 6575))  # Port for receiving audio from streaming_audio_capture.py
ZMQ_VAD_PORT = int(config.get("vad_port", 6579))    # Port for receiving VAD events

class WakeWordDetector(BaseAgent):
    def __init__(self, port=None, wake_word_path=None, sensitivity=0.5, energy_threshold=300):
        # Get configuration values with fallbacks
        agent_port = int(config.get("port", 5705)) if port is None else port
        agent_name = config.get("name", "WakeWordDetectorAgent")
        bind_address = config.get("bind_address", os.environ.get('BIND_ADDRESS', '0.0.0.0'))
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
        self.wake_word_path = wake_word_path or config.get("wake_word_path", "path/to/default_wake_word.ppn")
        self.sensitivity = sensitivity or float(config.get("sensitivity", 0.5))
        self.energy_threshold = energy_threshold or int(config.get("energy_threshold", 300))
        
        # Load API key
        self._load_api_key()
        
        # Initialize state
        self.is_running = False
        self.last_detection_time = 0
        self.detection_cooldown = float(config.get("detection_cooldown", 0.5))  # Cooldown period in seconds
        self.vad_speech_active = False  # Track if VAD has detected speech
        self.vad_confidence = 0.0       # Current VAD confidence
        self.vad_last_update = 0        # Last time VAD status was updated
        
        # Initialize ZMQ
        self.zmq_context = None  # Using pool
        self._init_zmq()
        
        # Initialize Porcupine
        self._init_porcupine()
        
        # Set running flag
        self.running = True
        

        
        logger.info("Wake word detector initialized")
    
    def _load_api_key(self):
        """Load Porcupine API key from config file."""
        try:
            config_path = os.path.join('config', 'api_keys.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    api_config = json.load(f)
                self.access_key = api_config.get('PORCUPINE_ACCESS_KEY')
            else:
                self.access_key = os.environ.get('PORCUPINE_ACCESS_KEY', config.get('porcupine_access_key', ''))
            
            if not self.access_key:
                logger.warning("PORCUPINE_ACCESS_KEY not found in config, using demo key")
                self.access_key = ''  # Demo key (limited functionality)
        except Exception as e:
            logger.error(f"Error loading API key: {str(e)}")
            self.access_key = ''
    
    def _init_zmq(self):
        """Initialize ZMQ context and sockets."""
        try:
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
            if hasattr(self, 'porcupine') and self.porcupine:
                self.porcupine.delete()
            
            self.cleanup()
            
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
            is_healthy = self.is_running  # Assume healthy unless a check fails
            
            # Add agent-specific health checks
            if hasattr(self, 'porcupine') and not self.porcupine:
                is_healthy = False

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
                    "vad_speech_active": self.vad_speech_active,
                    "vad_confidence": self.vad_confidence,
                    "last_detection_time": self.last_detection_time
                }
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name,
                "error": f"Health check failed with exception: {str(e)}"
            }

    def _get_health_status(self):
        """Get the current health status of the agent."""
        status = "HEALTHY" if self.running else "UNHEALTHY"
        details = {
            "status_message": "Agent is operational.",
            "uptime_seconds": time.time() - self.start_time
        }
        return {"status": status, "details": details}
    
    def cleanup(self):
        """Clean up resources when the agent is stopping."""
        try:
            # Close ZMQ sockets
            if hasattr(self, 'audio_socket') and self.audio_socket:
                self.audio_
            if hasattr(self, 'pub_socket') and self.pub_socket:
                self.pub_
            if hasattr(self, 'health_socket') and self.health_socket:
                self.health_
            if hasattr(self, 'vad_socket') and self.vad_socket:
                self.vad_
            if hasattr(self, 'error_bus_pub') and self.error_bus_pub:
                self.error_bus_pub.close()
            
            # Terminate ZMQ context after all sockets are closed
            if hasattr(self, 'zmq_context') and self.zmq_context:
                self.zmq_
            logger.info("Resources cleaned up")
        except Exception as e:
            logger.error(f"Error in cleanup: {str(e)}")

# -------------------- Agent Entrypoint --------------------
if __name__ == "__main__":
    # Configure basic logging
    logger = configure_logging(__name__, log_to_file=True)
    # Standardized main execution block
    agent = None
    try:
        # Load configuration from config file
        wake_word_path = config.get("wake_word_path", "path/to/default_wake_word.ppn")
        sensitivity = float(config.get("sensitivity", 0.5))
        energy_threshold = int(config.get("energy_threshold", 300))
        
        logger.info("Starting WakeWordDetectorAgent...")
        agent = WakeWordDetector(
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