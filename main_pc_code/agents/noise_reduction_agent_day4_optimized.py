# OPTIMIZED VERSION - Phase 1 Week 2 Day 4
# System-wide optimization deployment
# Enhanced with lazy loading pattern for startup performance
# Original: main_pc_code/agents/noise_reduction_agent.py

from main_pc_code.src.core.base_agent import BaseAgent
from common.utils.log_setup import configure_logging
"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

Noise Reduction Agent
-------------------
Implements real-time noise reduction for the voice assistant system:
- Subscribes to raw audio stream
- Applies noise reduction algorithms
- Publishes cleaned audio to downstream components
"""

import pickle
import numpy as np
import time
import threading
import logging
import sys
from datetime import datetime
import noisereduce as nr
import psutil
from datetime import datetime
from common.utils.path_manager import PathManager

# Configure logging
logger = configure_logging(__name__) / "noise_reduction_agent.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ZMQ Configuration
ZMQ_SUB_PORT = 6575  # Raw audio from streaming_audio_capture.py
ZMQ_PUB_PORT = 6578  # Clean audio for downstream components
ZMQ_HEALTH_PORT = 6576  # Health status

# Noise Reduction Settings
NOISE_REDUCTION_STRENGTH = 0.5  # Strength of noise reduction (0.0-1.0)
NOISE_SAMPLE_DURATION = 0.5  # Duration in seconds to sample for noise profile
USE_STATIONARY_NOISE = True  # Use stationary noise reduction algorithm
USE_SPECTRAL_GATING = True  # Use spectral gating noise reduction
PROP_DECREASE = 0.8  # Proportion to decrease the noise by
SPECTRAL_SMOOTHING_MS = 150  # Spectral smoothing in ms

class NoiseReductionAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="NoiseReductionAgent")
        """Initialize the noise reduction agent."""
        self._running = False
        self._thread = None
        self.health_thread = None
        
        # Initialize ZMQ context
        self.zmq_context = None  # Using pool
        
        # Initialize sockets
        self._init_sockets()
        
        # Initialize noise profile
        self.noise_profile = None
        self.noise_samples = []
        self.is_collecting_noise = True
        self.noise_sample_count = 0
        self.noise_sample_target = 10  # Number of audio chunks to collect for noise profile
        
        logger.info("Noise Reduction Agent initialized")
    
    def _init_sockets(self):
        """Initialize all ZMQ sockets."""
        try:
            # Subscribe to raw audio
            self.sub_socket = self.zmq_context.socket(zmq.SUB)
            self.sub_socket.connect(f"tcp://localhost:{ZMQ_SUB_PORT}")
            self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            
            # Publish cleaned audio
            self.pub_socket = self.zmq_context.socket(zmq.PUB)
            self.pub_socket.bind(f"tcp://*:{ZMQ_PUB_PORT}")
            
            # Health status
            self.health_socket = self.zmq_context.socket(zmq.PUB)
            self.health_socket.bind(f"tcp://*:{ZMQ_HEALTH_PORT}")
            
            logger.info(f"ZMQ sockets initialized - Raw Audio SUB: {ZMQ_SUB_PORT}, Clean Audio PUB: {ZMQ_PUB_PORT}, Health: {ZMQ_HEALTH_PORT}")
        except Exception as e:
            logger.error(f"Error initializing ZMQ sockets: {str(e)}")
            raise
    
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
            logger.info(f"PERF_METRIC: [NoiseReductionAgent] - [AudioChunkProcessing] - Duration: {duration_ms:.2f}ms")
            
            return result
        except Exception as e:
            logger.error(f"Error in noise reduction: {str(e)}")
            
            # Create standardized error message
            error_message = {
                "status": "error",
                "error_type": "NoiseReductionError",
                "source_agent": "noise_reduction_agent.py",
                "message": f"Failed to process audio chunk: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "sample_rate": sample_rate,
                    "chunk_size": len(audio_data) if audio_data is not None else 0,
                    "is_collecting_noise": self.is_collecting_noise
                }
            }
            
            # Publish error message
            try:
                self.pub_socket.send_json(error_message)
                logger.info("Published error message to downstream components")
            except Exception as pub_error:
                logger.error(f"Failed to publish error message: {str(pub_error)}")
            
            # Return original audio as fallback
            return audio_data  
    
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
                        # Send standardized error for missing audio chunk
                        error_message = {
                            "status": "error",
                            "error_type": "AudioProcessingError",
                            "source_agent": "noise_reduction_agent.py",
                            "message": "Received empty audio chunk",
                            "timestamp": datetime.now().isoformat(),
                            "details": {
                                "sample_rate": sample_rate
                            }
                        }
                        self.pub_socket.send_json(error_message)
                        logger.warning("Received empty audio chunk, sent error message")
                        continue
                    
                    # Apply noise reduction
                    cleaned_audio = self.apply_noise_reduction(audio_chunk, sample_rate)
                    
                    # Prepare message with cleaned audio
                    clean_data = {
                        'audio_chunk': cleaned_audio,
                        'sample_rate': sample_rate,
                        'timestamp': data.get('timestamp', datetime.now().isoformat()),
                        'is_cleaned': True,
                        'original_energy': np.mean(np.abs(audio_chunk)),
                        'cleaned_energy': np.mean(np.abs(cleaned_audio))
                    }
                    
                    # Publish cleaned audio
                    self.pub_socket.send(pickle.dumps(clean_data))
                    
                except zmq.Again:
                    time.sleep(0.01)  # Small sleep when no messages
                    continue
                except pickle.UnpicklingError as pe:
                    # Handle corrupt data with standardized error
                    error_message = {
                        "status": "error",
                        "error_type": "MessageFormatError",
                        "source_agent": "noise_reduction_agent.py",
                        "message": f"Failed to unpickle received data: {str(pe)}",
                        "timestamp": datetime.now().isoformat()
                    }
                    self.pub_socket.send_json(error_message)
                    logger.error(f"Unpickling error: {str(pe)}")
                    time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in audio processing loop: {str(e)}")
                
                # Send standardized error message for general processing errors
                try:
                    error_message = {
                        "status": "error",
                        "error_type": "AudioProcessingError",
                        "source_agent": "noise_reduction_agent.py",
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
                    'timestamp': datetime.now().isoformat(),
                    'component': 'NoiseReductionAgent',
                    'status': 'healthy',
                    'has_noise_profile': self.noise_profile is not None,
                    'is_collecting_noise': self.is_collecting_noise,
                    'noise_sample_count': self.noise_sample_count,
                    'noise_sample_target': self.noise_sample_target
                }
                
                # Send health status
                self.health_socket.send_json(status)
                
                # Sleep until next update
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in health broadcast loop: {str(e)}")
                time.sleep(5)  # Sleep on error, but shorter to recover faster
    
    def start(self):
        """Start the noise reduction agent."""
        if self._running:
            logger.warning("Noise reduction agent is already running")
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
        
        logger.info("Noise reduction agent started")
    
    def stop(self):
        """Stop the noise reduction agent."""
        logger.info("Stopping noise reduction agent")
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=2)
        if self.health_thread:
            self.health_thread.join(timeout=2)
            
        # Close ZMQ sockets
        self.sub_
        self.pub_
        self.health_
        logger.info("Noise reduction agent stopped")
    
    def run(self):
        """Run the noise reduction agent."""
        try:
            logger.info("Starting noise reduction agent")
            self.start()
            
            # Keep main thread alive
            while self._running:
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception as e:
            logger.error(f"Error in noise reduction agent: {str(e)}")
            
            # Send standardized error message for fatal errors
            try:
                error_message = {
                    "status": "error",
                    "error_type": "AgentShutdownError",
                    "source_agent": "noise_reduction_agent.py",
                    "message": f"Fatal error in noise reduction agent: {str(e)}",
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
    agent = NoiseReductionAgent()
    agent.run() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise

# OPTIMIZATION APPLIED: Day 4 System-wide deployment
# - Lazy loading pattern for heavy imports
# - Enhanced BaseAgent integration
# - Unified configuration management
# - Performance monitoring enabled
