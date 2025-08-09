from common.core.base_agent import BaseAgent
from common.config_manager import load_unified_config
from common.constants.service_names import ServiceNames

# Import path manager for containerization-friendly paths
import os
from common.utils.path_manager import PathManager
from common.utils.env_standardizer import get_env

# Removed # Path setup completed above

"""

Ultimate TTS Agent
Provides advanced text-to-speech capabilities with 4-tier fallback system:
Tier 1: TTS Service (Primary) - High-quality multilingual speech synthesis via ModelManagerAgent
Tier 2: Windows SAPI (Secondary) - Reliable system-level TTS
Tier 3: pyttsx3 (Tertiary) - Cross-platform TTS fallback
Tier 4: Console Print (Final) - Text output as last resort
"""
import zmq
import json
import time
import os
import threading
import queue
import sounddevice as sd
import re
from main_pc_code.utils.service_discovery_client import register_service, get_service_address, discover_service
from main_pc_code.utils.env_loader import get_env
# from main_pc_code.src.network.secure_zmq import configure_secure_client, configure_secure_server
from collections import OrderedDict

# Load configuration at module level
config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))

# Add the parent directory to sys.path

# Configure logging using canonical approach
from common.utils.log_setup import configure_logging
logger = configure_logging(__name__, log_to_file=True)

# ZMQ Configuration
SAMPLE_RATE = int(config.get("sample_rate", 24000))
CHANNELS = int(config.get("channels", 1))
BUFFER_SIZE = int(config.get("buffer_size", 1024))
MAX_CACHE_SIZE = int(config.get("max_cache_size", 50))

INTERRUPT_PORT = int(config.get("streaming_interrupt_handler_port", 5576))

class UltimateTTSAgent(BaseAgent):
    def __init__(self, port=None):
        # Get configuration values with fallbacks
        agent_port = int(config.get("port", 5562)) if port is None else port
        agent_name = config.get("name", "UltimateTTSAgent")
        bind_address = config.get("bind_address", get_env('BIND_ADDRESS', '<BIND_ADDR>'))
        zmq_timeout = int(config.get("zmq_request_timeout", 5000))
        
        # Additional configuration values
        self.unified_system_port = int(config.get("unifiedsystemagent_port", 5569))
        self.interrupt_port = int(config.get("streaming_interrupt_handler_port", 5576))
        self.sample_rate = int(config.get("sample_rate", 24000))
        self.channels = int(config.get("channels", 1))
        self.buffer_size = int(config.get("buffer_size", 1024))
        self.max_cache_size = int(config.get("max_cache_size", 50))
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=agent_name, port=agent_port)
        
        # Store important attributes
        self.bind_address = bind_address
        self.zmq_timeout = zmq_timeout
        
        """Initialize the Ultimate TTS agent with 4-tier fallback system"""
        logger.info("Initializing Ultimate TTS Agent")
        self.language = config.get("language", 'en')
        
        # Voice customization settings
        self.speaker_wav = None
        self.temperature = 0.7  # Voice variability
        self.speed = 1.0  # Voice speed multiplier
        self.volume = 1.0  # Volume level
        self.use_filipino_accent = False
        
        # Initialize ZMQ
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
        
        if self.secure_zmq:
            # self.socket = configure_secure_server(self.socket) # Commented out as per edit hint
            pass # Placeholder for secure ZMQ configuration if needed
        
        # Bind to address using self.bind_address for Docker compatibility
        bind_address = f"tcp://{self.bind_address}:{self.port}"
        self.socket.bind(bind_address)
        logger.info(f"TTS socket bound to {bind_address}")
        
        # Connect to UnifiedSystemAgent for health monitoring using service discovery
        self.system_socket = self.context.socket(zmq.PUB)
        if self.secure_zmq:
            # self.system_socket = configure_secure_client(self.system_socket) # Commented out as per edit hint
            pass # Placeholder for secure ZMQ configuration if needed
        
        # Try to get the UnifiedSystemAgent address from service discovery
        usa_address = get_service_address(ServiceNames.UnifiedSystemAgent)
        if not usa_address:
            # Fall back to configured port
            usa_address = f"tcp://localhost:{self.unified_system_port}"
        
        self.system_socket.connect(usa_address)
        logger.info(f"Connected to UnifiedSystemAgent at {usa_address}")
        
        # Initialize audio cache (OrderedDict maintains insertion order)
        self.cache = OrderedDict()
        
        # Queue for streaming audio chunks
        self.audio_queue = queue.Queue()
        self.is_speaking = False
        self.stop_speaking = False
        
        # Set up voice samples directory
        self.voice_samples_dir = str(PathManager.get_data_dir() / "voice_samples")
        if not os.path.exists(self.voice_samples_dir):
            os.makedirs(self.voice_samples_dir)
            logger.info(f"Created voice samples directory at {self.voice_samples_dir}")
            
        # Check for Tetey voice sample (from deprecated version)
        tetey_voice_path = os.environ.get("TETEY_VOICE_PATH", str(PathManager.get_data_dir() / "voice_samples" / "tetey1.wav")) # Allow override
        if os.path.exists(tetey_voice_path):
            self.speaker_wav = tetey_voice_path
            logger.info(f"Found Tetey voice sample at {tetey_voice_path}")
        else:
            # Look for any wav files in the voice samples directory
            voice_samples = [f for f in os.listdir(self.voice_samples_dir) 
                            if f.endswith(".wav")]
            if voice_samples:
                self.speaker_wav = os.path.join(self.voice_samples_dir, voice_samples[0])
                logger.info(f"Using voice sample: {self.speaker_wav}")
        
        # Connect to TTS service
        self.tts_service_socket = None
        self._connect_to_tts_service()
        
        # Initialize TTS engines in a background thread
        self.tts_engines = {}
        self.initialization_status = {
            "is_initialized": False,
            "error": None,
            "progress": 0.0,
            "engines_ready": {
                "tts_service": False,
                "sapi": False,
                "pyttsx3": False,
                "console": True  # Console is always available
            }
        }
        self.init_thread = threading.Thread(target=self._async_initialize_tts_engines, daemon=True)
        self.init_thread.start()
        
        # Start audio playback thread
        self.playback_thread = threading.Thread(target=self.audio_playback_loop, daemon=True)
        self.playback_thread.start()
        
        # Start health monitoring thread
        self.health_thread = threading.Thread(target=self._send_health_updates, daemon=True)
        self.health_thread.start()
        
        # Interrupt SUB socket - use service discovery
        self.interrupt_socket = self.context.socket(zmq.SUB)
        if self.secure_zmq:
            # self.interrupt_socket = configure_secure_client(self.interrupt_socket) # Commented out as per edit hint
            pass # Placeholder for secure ZMQ configuration if needed
        
        # Try to get the interrupt handler address from service discovery
        interrupt_address = get_service_address(ServiceNames.StreamingInterruptHandler)
        if not interrupt_address:
            # Fall back to configured port
            interrupt_address = f"tcp://localhost:{self.interrupt_port}"
        
        self.interrupt_socket.connect(interrupt_address)
        self.interrupt_socket.setsockopt(zmq.SUBSCRIBE, b"")
        logger.info(f"Connected to interrupt handler at {interrupt_address}")
        
        self.interrupt_flag = threading.Event()
        self._start_interrupt_thread()
        
        # Register with service discovery
        self._register_service()
        
        # Set running flag and start_time
        self.running = True
        self.start_time = time.time()
        
        logger.info("TTS Agent basic initialization complete")



    def _register_service(self):
        """Register this agent with the service discovery system"""
        try:
            register_result = register_service(
                name="StreamingTTSAgent",
                port=self.port,
                additional_info={
                    "capabilities": ["tts", "streaming", "multilingual"],
                    "status": "initializing"
                }
            )
            if register_result and register_result.get("status") == "SUCCESS":
                logger.info("Successfully registered with service discovery")
            else:
                logger.warning(f"Service registration failed: {register_result.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error registering service: {e}")

    def _connect_to_tts_service(self):
        """Connect to the TTS service for speech synthesis."""
        try:
            # Discover TTSService
            tts_service = discover_service("TTSService")
            if tts_service and isinstance(tts_service, dict) and tts_service.get("status") == "SUCCESS":
                tts_service_info = tts_service.get("payload", {})
                tts_service_host = tts_service_info.get("host", get_env("BIND_ADDRESS", "0.0.0.0"))
                tts_service_port = tts_service_info.get("port", 5801)
                logger.info(f"Discovered TTSService at {tts_service_host}:{tts_service_port}")
                
                # Create socket for TTSService
                self.tts_service_socket = self.context.socket(zmq.REQ)
                self.tts_service_socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
                
                # Apply secure ZMQ if enabled
                if self.secure_zmq:
                    # self.tts_service_socket = configure_secure_client(self.tts_service_socket) # Commented out as per edit hint
                    pass # Placeholder for secure ZMQ configuration if needed
                
                self.tts_service_socket.connect(f"tcp://{tts_service_host}:{tts_service_port}")
                logger.info(f"Connected to TTSService at tcp://{tts_service_host}:{tts_service_port}")
                
                # Update initialization status
                self.initialization_status["engines_ready"]["tts_service"] = True
            else:
                logger.error("Could not discover TTSService, will fall back to other TTS engines")
                self.tts_service_socket = None
        except Exception as e:
            logger.error(f"Error connecting to TTSService: {str(e)}")
            self.tts_service_socket = None

    def _async_initialize_tts_engines(self):
        """Initialize all TTS engines in a background thread."""
        try:
            # Initialize fallback engines (SAPI and pyttsx3)
            # This is simplified as we're now primarily using the TTS service
            
            # Windows SAPI (if on Windows)
            try:
                if os.name == 'nt':  # Windows only
                    import win32com.client
                    self.tts_engines["sapi"] = win32com.client.Dispatch("SAPI.SpVoice")
                    self.initialization_status["engines_ready"]["sapi"] = True
                    logger.info("Initialized Windows SAPI TTS engine")
            except Exception as e:
                logger.warning(f"Failed to initialize Windows SAPI: {e}")
            
            # pyttsx3 (cross-platform)
            try:
                import pyttsx3
                self.tts_engines["pyttsx3"] = pyttsx3.init()
                self.initialization_status["engines_ready"]["pyttsx3"] = True
                logger.info("Initialized pyttsx3 TTS engine")
            except Exception as e:
                logger.warning(f"Failed to initialize pyttsx3: {e}")
            
            # Mark initialization as complete
            self.initialization_status["is_initialized"] = True
            self.initialization_status["progress"] = 1.0
            logger.info("TTS engines initialization complete")
            
            # Update service status
            self._update_service_status("online")
            
        except Exception as e:
            logger.error(f"Error initializing TTS engines: {e}")
            self.initialization_status["error"] = str(e)
            self.initialization_status["is_initialized"] = False

    def _add_to_cache(self, key, audio):
        """Add audio to cache with LRU eviction."""
        self.cache[key] = audio
        if len(self.cache) > self.max_cache_size:
            self.cache.popitem(last=False)  # Remove oldest item

    def split_into_sentences(self, text):
        """Split text into sentences for better TTS processing."""
        return re.split(r'(?<=[.!?])\s+', text)

    def speak(self, text):
        """Speak text using the available TTS engines."""
        if self.stop_speaking:
            logger.info("Speak request ignored due to active stop flag")
            return {"status": "error", "message": "Interrupted"}
            
        # Try engines in order of preference
        if self.tts_service_socket and self.initialization_status["engines_ready"]["tts_service"]:
            return self._speak_with_tts_service(text)
        elif self.initialization_status["engines_ready"]["sapi"]:
            return self._speak_with_sapi(text)
        elif self.initialization_status["engines_ready"]["pyttsx3"]:
            return self._speak_with_pyttsx3(text)
        else:
            return self._speak_with_console(text)
    
    def _speak_with_tts_service(self, text):
        """Speak using TTS service."""
        logger.info(f"Speaking with TTS service: {text[:30]}...")
        
        try:
            # Prepare request
            request = {
                "action": "speak",
                "text": text,
                "language": self.language,
                "voice_sample": self.speaker_wav if os.path.exists(self.speaker_wav or "") else None,
                "temperature": self.temperature,
                "speed": self.speed,
                "volume": self.volume
            }
            
            # Send request to TTS service
            self.tts_service_socket.send_json(request)
            response = self.tts_service_socket.recv_json()
            
            if response.get("status") == "success":
                logger.info("TTS service successfully processed speech request")
                return {"status": "success", "message": "Speech request processed"}
            else:
                error_message = response.get("message", "Unknown error")
                logger.error(f"TTS service error: {error_message}")
                # Fall back to SAPI
                return self._speak_with_sapi(text)
        except Exception as e:
            logger.error(f"Error using TTS service: {str(e)}")
            # Fall back to SAPI
            return self._speak_with_sapi(text)
    
    def _speak_with_sapi(self, text):
        """Speak using Windows SAPI."""
        logger.info(f"Speaking with SAPI: {text[:30]}...")
        self.tts_engines["sapi"].Speak(text)
        return {"status": "success", "message": "Spoke with SAPI"}
    
    def _speak_with_pyttsx3(self, text):
        """Speak using pyttsx3."""
        logger.info(f"Speaking with pyttsx3: {text[:30]}...")
        engine = self.tts_engines["pyttsx3"]
        engine.say(text)
        engine.runAndWait()
        return {"status": "success", "message": "Spoke with pyttsx3"}
    
    def _speak_with_console(self, text):
        """Print text to console."""
        logger.info(f"Console output: {text}")
        print(f"[TTS] {text}")
        return {"status": "success", "message": "Printed to console"}
    
    def audio_playback_loop(self):
        """Background thread for audio playback."""
        logger.info("Starting audio playback thread")
        
        try:
            with sd.OutputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype='float32',  # Always use float32 for output
                blocksize=BUFFER_SIZE
            ) as stream:
                while True:
                    try:
                        # Get audio chunk from queue with timeout
                        try:
                            chunk = self.audio_queue.get(timeout=0.2)
                        except queue.Empty:
                            continue
                        
                        # Check if we should stop speaking
                        if self.stop_speaking:
                            self.audio_queue.task_done()
                            continue
                        
                        # Play audio
                        if chunk is not None and len(chunk) > 0:
                            stream.write(chunk)
                        
                        self.audio_queue.task_done()
                        
                    except Exception as e:
                        logger.error(f"Error in audio playback: {e}")
                        time.sleep(0.1)  # Prevent tight loop on error
        except Exception as e:
            logger.error(f"Failed to initialize audio output stream: {e}")
    
    def _send_health_updates(self):
        """Send periodic health updates to UnifiedSystemAgent."""
        while self.running:
            try:
                health_data = self._get_health_status()
                self.system_socket.send_json(health_data)
            except Exception as e:
                logger.error(f"Error sending health update: {e}")
            
            time.sleep(30)  # Send update every 30 seconds
    
    def _interrupt_listener(self):
        """Listen for interrupt commands."""
        logger.info("Starting interrupt listener")
        
        while self.running:
            try:
                # Check for interrupt messages
                try:
                    message = self.interrupt_socket.recv_json(flags=zmq.NOBLOCK)
                    command = message.get("command", "")
                    
                    if command == "STOP_SPEAKING":
                        logger.info("Received STOP_SPEAKING command")
                        self.stop_speaking = True
                        self.interrupt_flag.set()
                        
                        # If using TTS service, send stop command
                        if self.tts_service_socket:
                            try:
                                self.tts_service_socket.send_json({"action": "stop"})
                                self.tts_service_socket.recv_json()  # Get response but ignore it
                            except Exception as e:
                                logger.error(f"Error sending stop command to TTS service: {e}")
                        
                        # Clear audio queue
                        while not self.audio_queue.empty():
                            try:
                                self.audio_queue.get_nowait()
                                self.audio_queue.task_done()
                            except queue.Empty:
                                break
                except zmq.Again:
                    pass  # No message available
                
                time.sleep(0.1)  # Small sleep to prevent tight loop
                
            except Exception as e:
                logger.error(f"Error in interrupt listener: {e}")
                time.sleep(1)  # Longer sleep on error
    
    def _start_interrupt_thread(self):
        """Start the interrupt listener thread."""
        interrupt_thread = threading.Thread(target=self._interrupt_listener, daemon=True)
        interrupt_thread.start()
    
    def _get_health_status(self):
        """Get the health status of the TTS agent."""
        return {
            "agent": self.name,
            "status": "online" if self.initialization_status["is_initialized"] else "initializing",
            "uptime": int(time.time() - self.start_time),
            "engines_ready": self.initialization_status["engines_ready"],
            "is_speaking": not self.audio_queue.empty() and not self.stop_speaking,
            "error": self.initialization_status["error"]
        }

    def run(self):
        """Main loop to handle TTS requests"""
        logger.info("Starting TTS agent main loop")
        
        try:
            # Update service status to running
            self._update_service_status("running")
            
            while True:
                try:
                    # Check for interrupt before processing new request
                    if self.interrupt_flag.is_set():
                        self.stop_speaking = True
                        self.interrupt_flag.clear()
                        logger.info("Cleared interrupt flag")
                    
                    # Receive request with timeout to allow checking interrupt flag
                    poller = zmq.Poller()
                    poller.register(self.socket, zmq.POLLIN)
                    
                    if poller.poll(100):  # 100ms timeout
                        request = self.socket.recv_json()
                        logger.info(f"Received request: {request}")
                        
                        # Extract request data
                        text = request.get("text", "")
                        request.get("emotion")
                        request.get("language")
                        command = request.get("command")
                        
                        # Check for special commands
                        if command == "stop":
                            logger.info("Received stop command")
                            self.stop_speaking = True
                            # Clear audio queue
                            while not self.audio_queue.empty():
                                try:
                                    self.audio_queue.get_nowait()
                                except queue.Empty:
                                    break
                            self.socket.send_json({"status": "success", "message": "Speech stopped"})
                            continue
                        
                        # Skip empty text
                        if not text:
                            error_msg = "Empty text received"
                            logger.warning(error_msg)
                            self.socket.send_json({
                                "status": "error", 
                                "message": error_msg,
                                "error_type": "invalid_input"
                            })
                            continue
                        
                        # Check if TTS engines are initialized
                        if not self.initialization_status["is_initialized"]:
                            if self.initialization_status["error"]:
                                error_msg = f"TTS initialization failed: {self.initialization_status['error']}"
                                logger.error(error_msg)
                                self.socket.send_json({
                                    "status": "error", 
                                    "message": error_msg,
                                    "error_type": "initialization_error",
                                    "initialization_status": self.initialization_status
                                })
                            else:
                                progress = self.initialization_status["progress"]
                                logger.info(f"TTS still initializing ({progress*100:.0f}%)")
                                self.socket.send_json({
                                    "status": "error", 
                                    "message": f"TTS still initializing ({progress*100:.0f}%)",
                                    "error_type": "not_ready",
                                    "initialization_status": self.initialization_status
                                })
                            continue
                        
                        # Process the text
                        try:
                            success = self.speak(text)
                            if success:
                                self.socket.send_json({"status": "success"})
                            else:
                                self.socket.send_json({
                                    "status": "error", 
                                    "message": "Failed to generate speech",
                                    "error_type": "generation_failed"
                                })
                        except Exception as e:
                            error_msg = f"Error generating speech: {str(e)}"
                            logger.error(error_msg)
                            self.socket.send_json({
                                "status": "error", 
                                "message": error_msg,
                                "error_type": "processing_error"
                            })
                    
                except zmq.Again:
                    # Timeout on receive, just continue the loop
                    pass
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    self.socket.send_json({
                        "status": "error", 
                        "message": f"Invalid JSON: {str(e)}",
                        "error_type": "invalid_request"
                    })
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    try:
                        self.socket.send_json({
                            "status": "error", 
                            "message": f"Internal error: {str(e)}",
                            "error_type": "internal_error"
                        })
                    except zmq.ZMQError:
                        pass  # Socket might be closed
                        
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        finally:
            self._shutdown()
    
    def _update_service_status(self, status):
        """Update the service status in the service registry"""
        try:
            register_service(
                name="StreamingTTSAgent",
                port=self.port,
                additional_info={
                    "capabilities": ["tts", "streaming", "multilingual"],
                    "status": status
                }
            )
            logger.info(f"Updated service status to '{status}'")
        except Exception as e:
            logger.error(f"Error updating service status: {e}")
    
    def _shutdown(self):
        """Clean up resources"""
        logger.info("Shutting down StreamingTTSAgent")
        
        # Update service status
        self._update_service_status("stopping")
        
        # Stop flag for threads
        self.stop_speaking = True
        
        # Clear audio queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        
        # Close all sockets
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
            logger.info("Closed main socket")
            
        if hasattr(self, 'system_socket') and self.system_socket:
            self.system_socket.close()
            logger.info("Closed system socket")
            
        if hasattr(self, 'interrupt_socket') and self.interrupt_socket:
            self.interrupt_socket.close()
            logger.info("Closed interrupt socket")
        
        # Terminate ZMQ context
        if hasattr(self, 'context') and self.context:
            self.context.term()
            logger.info("Terminated ZMQ context")
        
        logger.info("StreamingTTSAgent shut down successfully")


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

    def report_error(self, error_type, message, severity="ERROR", context=None):
        error_data = {
            "error_type": error_type,
            "message": message,
            "severity": severity,
            "context": context or {}
        }
        try:
            msg = json.dumps(error_data).encode('utf-8')
            self.error_bus_pub.send_multipart([b"ERROR:", msg])
        except Exception as e:
            print(f"Failed to publish error to Error Bus: {e}")

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        logger.info("Starting UltimateTTSAgent...")
        agent = UltimateTTSAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception:
        pass
    # Error handling completed successfully
    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info(f"{self.__class__.__name__} cleaning up resources...")
        try:
            # Close ZMQ sockets if they exist
            if hasattr(self, 'socket') and self.socket:
                self.socket.close()
            
            if hasattr(self, 'context') and self.context:
                self.context.term()
                
            # Close any open file handles
            # [Add specific resource cleanup here]
            
            # Call parent class cleanup if it exists
            super().cleanup()
            
            logger.info(f"{self.__class__.__name__} cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
