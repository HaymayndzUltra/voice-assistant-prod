from main_pc_code.src.core.base_agent import BaseAgent
import zmq
import pickle
import json
import logging
import threading
import time
import os
from main_pc_code.src.network.secure_zmq import configure_secure_client, configure_secure_server
from main_pc_code.utils.service_discovery_client import register_service, get_service_address
from main_pc_code.utils.config_loader import load_config
from main_pc_code.utils.env_loader import get_env
import psutil
from datetime import datetime

# Load configuration at module level

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

config = load_config()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TTSAgent")

# Get configuration from config or fallback to defaults
INTERRUPT_PORT = int(config.get("streaming_interrupt_handler_port", 5576))

class TTSAgent(BaseAgent):
    def __init__(self, port=None):
        # Get configuration values with fallbacks
        agent_port = int(config.get("port", 5706)) if port is None else port
        agent_name = config.get("name", "TTSAgent")
        bind_address = config.get("bind_address", get_env('BIND_ADDRESS', '<BIND_ADDR>'))
        zmq_timeout = int(config.get("zmq_request_timeout", 5000))
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=agent_name, port=agent_port)
        
        # Store important attributes
        self.bind_address = bind_address
        self.zmq_timeout = zmq_timeout
        self.start_time = time.time()
        
        # Initialize ZMQ context and socket
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
        
        if self.secure_zmq:
            self.socket = configure_secure_server(self.socket)
        
        # Bind to address using BIND_ADDRESS for Docker compatibility
        bind_address = f"tcp://{self.bind_address}:{self.port}"
        self.socket.bind(bind_address)
        logger.info(f"TTS agent listening on {bind_address}")
        
        # Interrupt SUB socket - use service discovery
        self.interrupt_socket = self.context.socket(zmq.SUB)
        if self.secure_zmq:
            self.interrupt_socket = configure_secure_client(self.interrupt_socket)
        
        # Try to get the interrupt handler address from service discovery
        interrupt_address = get_service_address("StreamingInterruptHandler")
        if not interrupt_address:
            # Fall back to configured port
            interrupt_address = f"tcp://localhost:{INTERRUPT_PORT}"
        
        self.interrupt_socket.connect(interrupt_address)
        self.interrupt_socket.setsockopt(zmq.SUBSCRIBE, b"")
        logger.info(f"Connected to interrupt handler at {interrupt_address}")
        
        self.interrupt_flag = threading.Event()
        self._start_interrupt_thread()
        
        # Register with service discovery
        self._register_service(self.port)
        
        # Running flag
        self.running = True
        
        logger.info("TTSAgent initialized")
    
    def _register_service(self, port):
        """Register this agent with the service discovery system"""
        try:
            register_result = register_service(
                name="TTSAgent",
                port=port,
                additional_info={
                    "capabilities": ["tts", "batch"],
                    "status": "running"
                }
            )
            if register_result and register_result.get("status") == "SUCCESS":
                logger.info("Successfully registered with service discovery")
            else:
                logger.warning(f"Service registration failed: {register_result.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error registering service: {e}")

    def _interrupt_listener(self):
        """Listen for interrupt signals"""
        logger.info("Starting interrupt listener thread")
        while self.running:
            try:
                msg = self.interrupt_socket.recv(flags=zmq.NOBLOCK)
                data = pickle.loads(msg)
                if data.get('type') == 'interrupt':
                    logger.info("Received interrupt signal")
                    self.interrupt_flag.set()
            except zmq.Again:
                time.sleep(0.05)  # Small sleep to avoid tight loop
            except Exception as e:
                logger.error(f"Error in interrupt listener: {e}")
                time.sleep(1)  # Longer sleep on error

    def _start_interrupt_thread(self):
        """Start the interrupt listener thread"""
        self.interrupt_thread = threading.Thread(target=self._interrupt_listener, daemon=True)
        self.interrupt_thread.start()
        logger.info("Interrupt listener thread started")

    def run(self):
        """Main loop to handle TTS requests"""
        logger.info("Starting TTS agent main loop")
        
        try:
            while self.running:
                try:
                    # Check for interrupt before processing new request
                    if self.interrupt_flag.is_set():
                        logger.info("Processing was interrupted")
                        self.interrupt_flag.clear()
                    
                    # Receive request with timeout to allow checking interrupt flag
                    poller = zmq.Poller()
                    poller.register(self.socket, zmq.POLLIN)
                    
                    if poller.poll(100):  # 100ms timeout
                        message = self.socket.recv_json()
                        logger.info(f"Received request: {message}")
                        
                        # Check if this is a stop command
                        if message.get('command') == 'stop':
                            logger.info("Received stop command")
                            self.socket.send_json({"status": "success", "message": "Stopped"})
                            continue
                        
                        # Check for interrupt flag again before processing
                        if self.interrupt_flag.is_set():
                            logger.info("Request interrupted before processing")
                            self.socket.send_json({"status": "error", "message": "Interrupted"})
                            self.interrupt_flag.clear()
                            continue
                        
                        # Process TTS request
                        text = message.get('text')
                        if not text:
                            logger.warning("Empty text received")
                            self.socket.send_json({"status": "error", "message": "Empty text"})
                            continue
                        
                        # Here would be the actual TTS processing logic
                        # For now, we'll just simulate success
                        logger.info(f"Processing text: {text[:50]}...")
                        
                        # Send success response
                        self.socket.send_json({"status": "success"})
                
                except zmq.Again:
                    # Timeout on receive, just continue the loop
                    pass
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    try:
                        self.socket.send_json({"status": "error", "message": f"Invalid JSON: {str(e)}"})
                    except zmq.ZMQError:
                        pass  # Socket might be closed
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    try:
                        self.socket.send_json({"status": "error", "message": str(e)})
                    except zmq.ZMQError:
                        pass  # Socket might be closed
        
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        logger.info("Shutting down TTSAgent")
        self.running = False
        
        # Close all sockets
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
            logger.info("Closed main socket")
            
        if hasattr(self, 'interrupt_socket') and self.interrupt_socket:
            self.interrupt_socket.close()
            logger.info("Closed interrupt socket")
        
        # Terminate ZMQ context
        if hasattr(self, 'context') and self.context:
            self.context.term()
            logger.info("Terminated ZMQ context")
        
        # Call BaseAgent's cleanup
        super().cleanup()
        
        logger.info("TTSAgent shut down successfully")

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise


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
                    "interrupt_flag": self.interrupt_flag.is_set()
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
        # Default health status: Agent is running if its main loop is active.
        # This can be expanded with more specific checks later.
        status = "HEALTHY" if self.running else "UNHEALTHY"
        details = {
            "status_message": "Agent is operational.",
            "uptime_seconds": time.time() - self.start_time
        }
        return {"status": status, "details": details}


# -------------------- Agent Entrypoint --------------------
if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        logger.info("Starting TTSAgent...")
        agent = TTSAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        logger.error(f"An unexpected error occurred in {agent.name if agent else 'TTSAgent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            logger.info(f"Cleaning up {agent.name}...")
            agent.cleanup()