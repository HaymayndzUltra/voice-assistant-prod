from common.core.base_agent import BaseAgent
"""
Context Bridge Agent
Connects face recognition events to the context manager for seamless context switching.
"""

import zmq
import json
import time
import logging
import threading
import os
import sys
import traceback
# from web_automation import GLOBAL_TASK_MEMORY  # Unified adaptive memory and emotion/skill tracking (commented out for PC1)

# Add parent directory to path to allow importing from agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main_pc_code.agents.context_manager import create_context_manager, add_to_context, get_context, clear_context
import psutil
from datetime import datetime
from common.env_helpers import get_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ContextBridge")

# ZMQ ports
FACE_RECOGNITION_PORT = 5595
CONTEXT_MANAGER_PORT = 5596  # Updated to match contextual_memory_agent.py
INTERPRETER_PORT = 5557

class ContextBridgeAgent(BaseAgent):
    """Bridge between face recognition and context management"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ContextBridgeAgent")
        # Initialize ZMQ context
        self.zmq_context = zmq.Context()
        
        # Create context manager
        self.context_manager = create_context_manager()
        
        # Track the current active speaker
        self.current_speaker = None
        self.last_speaker_change = 0
        self.speaker_confidence_threshold = 0.6  # Minimum confidence to switch context
        self.speaker_timeout = 30.0  # Seconds before considering a speaker inactive
        
        # Track seen speakers
        self.seen_speakers = set()
        
        # Flag to control running state
        self.running = False
        
        logger.info("[ContextBridge] Initialized")
    
    def connect_to_face_recognition(self):
        """Connect to face recognition agent via ZMQ"""
        try:
            # Socket to receive face recognition events
            self.face_socket = self.zmq_context.socket(zmq.SUB)
            self.face_socket.connect(f"tcp://localhost:{FACE_RECOGNITION_PORT}")
            self.face_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            logger.info(f"[ContextBridge] Connected to face recognition agent on port {FACE_RECOGNITION_PORT}")
            return True
        except Exception as e:
            logger.error(f"[ContextBridge] Error connecting to face recognition: {e}")
            return False
    
    def connect_to_interpreter(self):
        """Connect to interpreter agent via ZMQ"""
        try:
            # Socket to send context updates to interpreter
            self.interpreter_socket = self.zmq_context.socket(zmq.PUB)
            self.interpreter_socket.connect(f"tcp://localhost:{INTERPRETER_PORT}")
            logger.info(f"[ContextBridge] Connected to interpreter agent on port {INTERPRETER_PORT}")
            return True
        except Exception as e:
            logger.error(f"[ContextBridge] Error connecting to interpreter: {e}")
            return False
    
    def handle_face_recognition_event(self, event_data):
        """Process face recognition events and update context"""
        try:
            event_type = event_data.get("event")
            
            if event_type == "context_switch":
                speaker = event_data.get("speaker")
                confidence = event_data.get("confidence", 0.0)
                emotion = event_data.get("emotion")
                timestamp = event_data.get("timestamp", time.time())
                
                # Add speaker to seen speakers
                if speaker and speaker not in self.seen_speakers:
                    self.seen_speakers.add(speaker)
                    logger.info(f"[ContextBridge] New speaker detected: {speaker}")
                
                # Check if we should switch context
                if speaker and confidence >= self.speaker_confidence_threshold:
                    # Only switch if it's a new speaker or enough time has passed
                    current_time = time.time()
                    if (speaker != self.current_speaker or 
                        current_time - self.last_speaker_change > self.speaker_timeout):
                        
                        # Switch context to the new speaker
                        self.switch_context(speaker, confidence, emotion)
                        self.current_speaker = speaker
                        self.last_speaker_change = current_time
                        
                        # Notify interpreter about context switch
                        self.notify_interpreter(speaker, emotion)
        except Exception as e:
            logger.error(f"[ContextBridge] Error handling face recognition event: {e}")
    
    def switch_context(self, speaker, confidence, emotion=None):
        """Switch context to a new speaker"""
        try:
            # Create a context switch message
            switch_message = f"Context switched to {speaker}"
            if emotion and emotion != "neutral":
                switch_message += f" (emotion: {emotion})"
            
            # Add the context switch to the context manager
            metadata = {
                "type": "context_switch",
                "confidence": confidence,
                "emotion": emotion,
                "timestamp": time.time()
            }
            
            add_to_context(self.context_manager, switch_message, speaker=speaker, metadata=metadata)
            logger.info(f"[ContextBridge] {switch_message} (confidence: {confidence:.2f})")
            return True
        except Exception as e:
            logger.error(f"[ContextBridge] Error switching context: {e}")
            return False
    
    def notify_interpreter(self, speaker, emotion=None):
        """Notify the interpreter agent about a context switch"""
        try:
            # Create notification message
            message = {
                "event": "context_switch",
                "speaker": speaker,
                "emotion": emotion,
                "timestamp": time.time()
            }
            
            # Send to interpreter
            self.interpreter_socket.send_string(json.dumps(message))
            logger.debug(f"[ContextBridge] Notified interpreter about context switch to {speaker}")
            return True
        except Exception as e:
            logger.error(f"[ContextBridge] Error notifying interpreter: {e}")
            return False
    
    def run(self):
        """Main loop to process events"""
        self.running = True
        
        # Connect to required agents
        if not self.connect_to_face_recognition():
            logger.error("[ContextBridge] Failed to connect to face recognition agent")
            return
        
        if not self.connect_to_interpreter():
            logger.warning("[ContextBridge] Failed to connect to interpreter agent (continuing anyway)")
        
        logger.info("[ContextBridge] Agent started")
        
        try:
            while self.running:
                try:
                    # Check for face recognition events (non-blocking)
                    if self.face_socket.poll(100, zmq.POLLIN):
                        message = self.face_socket.recv_string()
                        try:
                            event_data = json.loads(message)
                            self.handle_face_recognition_event(event_data)
                        except json.JSONDecodeError:
                            logger.warning(f"[ContextBridge] Received invalid JSON: {message[:50]}...")
                    
                    # Sleep a bit to avoid high CPU usage
                    time.sleep(0.01)
                    
                except zmq.ZMQError as e:
                    logger.error(f"[ContextBridge] ZMQ error: {e}")
                    time.sleep(1)  # Wait a bit before retrying
                except Exception as e:
                    logger.error(f"[ContextBridge] Error in main loop: {e}")
                    traceback.print_exc()
                    time.sleep(1)  # Wait a bit before retrying
        
        except KeyboardInterrupt:
            logger.info("[ContextBridge] Interrupted by user")
        finally:
            # Clean up
            self.running = False
            if hasattr(self, 'face_socket'):
                self.face_socket.close()
            if hasattr(self, 'interpreter_socket'):
                self.interpreter_socket.close()
            self.zmq_context.term()
            logger.info("[ContextBridge] Agent stopped")


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

def main():
    """Run the context bridge agent"""
    agent = ContextBridgeAgent()
    agent.run()

if __name__ == "__main__":
    main()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise