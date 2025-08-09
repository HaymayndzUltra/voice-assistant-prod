from common.core.base_agent import BaseAgent
from common.config_manager import load_unified_config
from common.utils.path_manager import PathManager
from common.utils.env_standardizer import get_env
from main_pc_code.utils.service_discovery_client import register_service
from common.env_helpers import get_env
# from main_pc_code.src.network.secure_zmq import configure_secure_client, configure_secure_server
from main_pc_code.agents.responder import configure_secure_client, configure_secure_server
import psutil
from datetime import datetime

"""

# Removed 
Streaming Interrupt Handler
Monitors partial transcripts for interruption keywords and sends interrupt signals
"""
import zmq
import pickle
import json
import json as _json_safe
import time
import logging
from common.utils.log_setup import configure_logging
import os
from main_pc_code.utils.service_discovery_client import get_service_address, register_service
from main_pc_code.utils.env_loader import get_env
# from main_pc_code.src.network.secure_zmq import configure_secure_client, configure_secure_server
from main_pc_code.utils.network_utils import get_zmq_connection_string
import psutil
from datetime import datetime
from common.constants.service_names import ServiceNames

# Load configuration at module level
config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Logging setup
logger = configure_logging(__name__)
logger = logging.getLogger("StreamingInterruptHandler")

# ZMQ Configuration - using ports from config
ZMQ_SUB_PORT = int(config.get("streaming_speech_recognition_port", 5575))  # Subscribe to partial transcripts
ZMQ_PUB_PORT = int(config.get("port", 5576))  # Publish interrupt signals
TTS_PORT = int(config.get("streaming_tts_agent_port", 5562))  # TTS agent port for sending stop commands

# Interruption keywords in different languages
INTERRUPT_KEYWORDS = {
    'en': ['stop', 'wait', 'cancel', 'enough', 'shut up', 'be quiet', 'pause'],
    'tl': ['tama', 'tama na', 'tumigil', 'hinto', 'sapat na', 'teka', 'sandali']
}

class StreamingInterruptHandler(BaseAgent):
    """
    StreamingInterruptHandler: Handles streaming interrupts. Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
    """
    def __init__(self, config=None, **kwargs):
        # Ensure config is a dictionary
        config = config or {}
        
        # Get configuration values with fallbacks
        agent_port = int(config.get("port", 5576))
        kwargs.get('name', "StreamingInterruptHandler")
        bind_address = config.get("bind_address", get_env('BIND_ADDRESS', '<BIND_ADDR>'))
        zmq_timeout = int(config.get("zmq_request_timeout", 5000))
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(port=agent_port, **kwargs)
        
        # Store important attributes
        self.bind_address = bind_address
        self.zmq_timeout = zmq_timeout
        self.start_time = time.time()
        
        self.context = zmq.Context()
        self.secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
        
        # Subscribe to partial transcripts - use service discovery
        self.sub_socket = self.context.socket(zmq.SUB)
        if self.secure_zmq:
            self.sub_socket = configure_secure_client(self.sub_socket)
            
        # Try to get the address from service discovery
        stt_address = get_service_address("StreamingSpeechRecognition")
        if not stt_address:
            # Fall back to configured port
            stt_address = get_zmq_connection_string(ZMQ_SUB_PORT, get_env("STREAMING_STT_HOST", "streaming-stt"))
            
        self.sub_socket.connect(stt_address)
        self.sub_socket.setsockopt(zmq.SUBSCRIBE, b"")
        logger.info(f"Connected to partial transcripts at {stt_address}")
        
        # Publish interrupt signals
        self.pub_socket = self.context.socket(zmq.PUB)
        if self.secure_zmq:
            self.pub_socket = configure_secure_server(self.pub_socket)
            
        bind_address = f"tcp://{self.bind_address}:{self.port}"
        self.pub_socket.bind(bind_address)
        logger.info(f"Publishing interrupt signals on {bind_address}")
        
        # Register with service discovery
        self._register_service(self.port)
        
        # TTS agent socket for direct stop commands - use service discovery
        self.tts_socket = self.context.socket(zmq.REQ)
        if self.secure_zmq:
            self.tts_socket = configure_secure_client(self.tts_socket)
            
        self.tts_socket.setsockopt(zmq.RCVTIMEO, self.zmq_timeout)
        self.tts_socket.setsockopt(zmq.SNDTIMEO, self.zmq_timeout)
        
        # Try to get the TTS address from service discovery
        tts_address = get_service_address(ServiceNames.StreamingTTSAgent)
        if not tts_address:
            # Fall back to configured port
            tts_address = get_zmq_connection_string(TTS_PORT, "localhost")
            
        self.tts_socket.connect(tts_address)
        logger.info(f"Connected to TTS agent at {tts_address}")
        
        self.running = True
        self.last_interrupt_time = 0
        self.interrupt_cooldown = 2.0  # Seconds between interrupts to prevent duplicates
        

    
    def _register_service(self, port):
        """Register this agent with the service discovery system"""
        try:
            register_result = register_service(
                name="StreamingInterruptHandler",
                port=port,
                additional_info={
                    "capabilities": ["interrupt", "streaming"],
                    "status": "running"
                }
            )
            if register_result and register_result.get("status") == "SUCCESS":
                logger.info("Successfully registered with service discovery")
            else:
                logger.warning(f"Service registration failed: {register_result.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error registering service: {e}")
    
    def detect_interruption(self, text, language='en'):
        """Check if text contains interruption keywords"""
        if not text:
            return False
            
        text = text.lower()
        
        # Check English keywords first (most common)
        for keyword in INTERRUPT_KEYWORDS['en']:
            if keyword in text:
                return True
                
        # If language is specified and not English, check that language too
        if language != 'en' and language in INTERRUPT_KEYWORDS:
            for keyword in INTERRUPT_KEYWORDS[language]:
                if keyword in text:
                    return True
                    
        return False
    
    def send_tts_stop_command(self):
        """Send stop command directly to TTS agent"""
        try:
            logger.info("Sending stop command to TTS agent")
            self.tts_socket.send_string(json.dumps({
                "command": "stop"
            }))
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.tts_socket, zmq.POLLIN)
            if poller.poll(1000):  # 1 second timeout
                response = self.tts_socket.recv_string()
                logger.info(f"TTS agent response: {response}")
                return True
            else:
                logger.warning("TTS agent did not respond to stop command")
                return False
                
        except Exception as e:
            logger.error(f"Error sending stop command to TTS agent: {e}")
            return False
    
    def publish_interrupt(self):
        """Publish interrupt signal to all modules"""
        try:
            # Check cooldown to prevent duplicate interrupts
            current_time = time.time()
            if current_time - self.last_interrupt_time < self.interrupt_cooldown:
                logger.info("Interrupt cooldown active, skipping")
                return False
                
            self.last_interrupt_time = current_time
            
            # Send interrupt signal via JSON (avoid pickle)
            interrupt_msg = {
                'type': 'interrupt',
                'timestamp': current_time
            }
            try:
                self.pub_socket.send_json(interrupt_msg)
            except Exception:
                # Fallback to string
                self.pub_socket.send_string(json.dumps(interrupt_msg))
            logger.info("Published interrupt signal")
            
            # Also send direct stop command to TTS agent
            self.send_tts_stop_command()
            
            return True
            
        except Exception as e:
            logger.error(f"Error publishing interrupt: {e}")
            return False
    
    def run(self):
        """Main loop for interrupt handler"""
        logger.info("Starting streaming interrupt handler")
        
        try:
            while self.running:
                try:
                    # Check for partial transcripts
                    msg = self.sub_socket.recv(flags=zmq.NOBLOCK)
                    # SECURITY: Avoid untrusted pickle.loads; expect JSON payloads only
                    try:
                        data = _json_safe.loads(msg.decode('utf-8'))
                    except Exception:
                        logger.error("Received non-JSON payload on transcripts topic; ignoring for safety")
                        time.sleep(0.05)
                        continue
                    
                    if data.get('type') == 'partial_transcription':
                        text = data.get('text', '')
                        language = data.get('detected_language', 'en')
                        
                        # Check for interruption keywords
                        if self.detect_interruption(text, language):
                            logger.info(f"Interruption detected in: '{text}'")
                            self.publish_interrupt()
                            
                except zmq.Again:
                    time.sleep(0.05)
                    
        except KeyboardInterrupt:
            logger.info("Interrupt handler stopped by user")
            self.running = False
        except Exception as e:
            logger.error(f"Error in interrupt handler: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up ZMQ resources to prevent leaks"""
        logger.info("Cleaning up resources")
        try:
            if hasattr(self, 'sub_socket'):
                self.sub_socket.close()
            if hasattr(self, 'pub_socket'):
                self.pub_socket.close()
            if hasattr(self, 'tts_socket'):
                self.tts_socket.close()
            if hasattr(self, 'context'):
                self.context.term()
                
            # Call BaseAgent's cleanup
            super().cleanup()
                
            logger.info("All resources cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def health_check(self):
        """Perform a health check and return status."""
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
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
                    "last_interrupt": time.time() - self.last_interrupt_time if self.last_interrupt_time > 0 else -1
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
        """Default health status implementation required by BaseAgent."""
        status = "HEALTHY" if self.running else "UNHEALTHY"
        details = {
            "status_message": "Agent is operational" if self.running else "Agent is not running",
            "uptime_seconds": time.time() - self.start_time
        }
        return {"status": status, "details": details}
    
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add initialization code here if needed
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise

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

# -------------------- Agent Entrypoint --------------------
if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        logger.info("Starting StreamingInterruptHandler...")
        agent = StreamingInterruptHandler()
        agent.run()
    except KeyboardInterrupt:
        logger.info(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception:
# Cleanup completed
            agent.cleanup()