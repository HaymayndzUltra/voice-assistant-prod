from main_pc_code.src.core.base_agent import BaseAgent
"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

Trigger Word Detector
- Replaces traditional wake word detection
- Uses keyword spotting in transcribed text
- More reliable than audio-based wake word detection
- Supports multiple trigger phrases in Filipino and English
"""
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import json
import os

from main_pc_code.utils.network import get_host, get_bind_address
import time
import logging
import sys
import os
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional
import re
import threading

# Add the parent directory to sys.path to import the config module
from main_pc_code.config.system_config import config

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / "trigger_word_detector.log"
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TriggerWordDetector")

# Get ZMQ ports from config
TRIGGER_DETECTOR_PORT = config.get('zmq.trigger_detector_port', 5555)
LISTENER_PORT = config.get('zmq.listener_port', 5561)
TRANSLATOR_PORT = config.get('zmq.translator_port', 8044)  # Using a port in the 8000-8100 range to avoid conflicts

class TriggerWordDetector(BaseAgent):
    """Detects trigger words/phrases in transcribed speech"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="TriggerWordDetector")
        """Initialize the trigger word detector"""
        # Initialize ZMQ
        self.context = None  # Using pool
        
        # Socket to receive transcribed speech from listener
        self.listener_sub = self.context.socket(zmq.SUB)
        listener_host = get_host("LISTENER_HOST", "zmq.listener_host")
        self.listener_sub.connect(f"tcp://{listener_host}:{LISTENER_PORT}")
        self.listener_sub.setsockopt_string(zmq.SUBSCRIBE, "")
        logger.info(f"Connected to Listener on port {LISTENER_PORT}")
        
        # Socket to publish triggered commands
        self.publisher = self.context.socket(zmq.PUB)
        bind_address = get_bind_address()
        self.publisher.bind(f"tcp://{bind_address}:{TRIGGER_DETECTOR_PORT}")
        logger.info(f"Publishing on port {TRIGGER_DETECTOR_PORT}")
        
        # Define trigger phrases (in both English and Filipino)
        self.trigger_phrases = self._load_trigger_phrases()
        
        # Passive listening mode - all speech is transcribed but only processed if it contains a trigger
        self.passive_mode = True
        
        # Active session tracking
        self.active_session = False
        self.session_timeout = 60  # seconds
        self.last_activity_time = 0
        
        # Start session timeout checker thread
        self.running = True
        self.timeout_thread = threading.Thread(target=self._check_session_timeout)
        self.timeout_thread.daemon = True
        self.timeout_thread.start()
        
        logger.info(f"Trigger Word Detector initialized with {len(self.trigger_phrases)} trigger phrases")
        logger.info(f"Passive mode: {self.passive_mode}")
    
    def _load_trigger_phrases(self) -> Dict[str, List[str]]:
        """Load trigger phrases from config or use defaults"""
        # Try to load from config
        config_triggers = config.get('trigger_words', {})
        
        if config_triggers:
            return config_triggers
        
        # Default trigger phrases if not in config
        return {
            "assistant_name": [
                "tha lim",
                "talim", 
                "thalim",
                "the lim",
                "da lim"
            ],
            "action_triggers": [
                "hey assistant",
                "hey",
                "hello assistant", 
                "hello",
                "okay assistant",
                "okay",
                "listen up",
                "excuse me",
                "attention"
            ],
            "filipino_triggers": [
                "hoy",
                "tara",
                "halika",
                "pakiusap",
                "tulungan mo ako",
                "kailangan ko ng tulong"
            ],
            "command_prefixes": [
                "can you",
                "could you",
                "please",
                "i need",
                "i want",
                "help me"
            ],
            "filipino_command_prefixes": [
                "pwede mo ba",
                "paki",
                "tulungan mo ako",
                "gusto ko",
                "kailangan ko"
            ]
        }
    
    def _check_session_timeout(self):
        """Check if the active session has timed out"""
        while self.running:
            if self.active_session:
                if time.time() - self.last_activity_time > self.session_timeout:
                    logger.info("Active session timed out")
                    self.active_session = False
            
            time.sleep(5)  # Check every 5 seconds
    
    def _contains_trigger(self, text: str) -> bool:
        """Check if the text contains any trigger phrase"""
        text_lower = text.lower()
        
        # Check all trigger categories
        for category, phrases in self.trigger_phrases.items():
            for phrase in phrases:
                if phrase.lower() in text_lower:
                    logger.info(f"Trigger detected: '{phrase}' in category '{category}'")
                    return True
        
        return False
    
    def _extract_command(self, text: str) -> str:
        """Extract the actual command from text containing a trigger phrase"""
        text_lower = text.lower()
        
        # Try to find the trigger phrase that was used
        trigger_used = None
        for category, phrases in self.trigger_phrases.items():
            for phrase in phrases:
                phrase_lower = phrase.lower()
                if phrase_lower in text_lower:
                    trigger_used = phrase_lower
                    break
            if trigger_used:
                break
        
        if not trigger_used:
            # No trigger found, return the original text
            return text
        
        # Find the trigger phrase in the text and extract everything after it
        trigger_index = text_lower.find(trigger_used)
        if trigger_index != -1:
            command_start = trigger_index + len(trigger_used)
            command = text[command_start:].strip()
            
            # If the command starts with common filler words, remove them
            filler_words = ["please", "can you", "could you", "would you", "um", "uh", ",", "."]
            for filler in filler_words:
                if command.lower().startswith(filler):
                    command = command[len(filler):].strip()
            
            return command
        
        return text
    
    def process_speech(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process transcribed speech and detect triggers"""
        try:
            # Extract text from message
            text = message.get("text", "")
            
            if not text:
                return None
            
            # Check if we're in an active session or if the text contains a trigger
            if self.active_session or self._contains_trigger(text):
                # If we have a trigger, extract the command
                if not self.active_session:
                    # New session started with a trigger
                    self.active_session = True
                    # Extract the command part (remove the trigger phrase)
                    command = self._extract_command(text)
                else:
                    # Already in an active session, use the full text as command
                    command = text
                
                # Update activity timestamp
                self.last_activity_time = time.time()
                
                # Create command message
                command_message = message.copy()
                command_message["text"] = command
                command_message["triggered"] = True
                command_message["session_active"] = True
                
                return command_message
            
            # In passive mode, we still return the message but mark it as not triggered
            elif self.passive_mode:
                passive_message = message.copy()
                passive_message["triggered"] = False
                passive_message["session_active"] = False
                
                return passive_message
            
            # Not in active session and no trigger detected
            return None
        
        except Exception as e:
            logger.error(f"Error processing speech: {str(e)}")
            traceback.print_exc()
            return None
    
    def handle_messages(self):
        """Listen for transcribed speech and detect triggers"""
        logger.info("Starting to handle messages...")
        
        while self.running:
            try:
                # Wait for message from listener with timeout
                if self.listener_sub.poll(timeout=1000) == 0:
                    continue
                
                # Receive message
                message_str = self.listener_sub.recv_string()
                
                try:
                    message = json.loads(message_str)
                    
                    # Process the message
                    processed_message = self.process_speech(message)
                    
                    # If we have a processed message, publish it
                    if processed_message:
                        self.publisher.send_string(json.dumps(processed_message))
                        
                        # Log the message
                        if processed_message.get("triggered", False):
                            logger.info(f"Published triggered command: {processed_message.get('text', '')}")
                        elif self.passive_mode:
                            logger.info(f"Published passive message: {processed_message.get('text', '')}")
                
                except json.JSONDecodeError:
                    logger.error("Invalid JSON in message from listener")
                except Exception as e:
                    logger.error(f"Error handling message: {str(e)}")
                    traceback.print_exc()
            
            except zmq.Again:
                # Timeout, continue loop
                pass
            except Exception as e:
                logger.error(f"Error in message handler: {str(e)}")
                traceback.print_exc()
    
    def run(self):
        """Run the trigger word detector"""
        try:
            logger.info("Starting Trigger Word Detector...")
            self.handle_messages()
        except KeyboardInterrupt:
            logger.info("Trigger Word Detector interrupted by user")
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            traceback.print_exc()
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        
        # Wait for timeout thread to finish
        if hasattr(self, 'timeout_thread') and self.timeout_thread.is_alive():
            self.timeout_thread.join(timeout=2)
        
        self.publisher.close()
        self.listener_sub.close()
        # TODO-FIXME – removed stray 'self.' (O3 Pro Max fix)
        logger.info("Trigger Word Detector stopped")



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
    import argparse
    import psutil
    from datetime import datetime
from common.utils.path_env import get_main_pc_code, get_project_root

    parser = argparse.ArgumentParser(description="Trigger Word Detector: Detects trigger words/phrases in transcribed speech.")
    parser.add_argument('--passive', action='store_true', help='Run in passive mode, processing all speech')
    parser.add_argument('--active', action='store_true', help='Run in active mode, only processing triggered speech')
    parser.add_argument('--timeout', type=int, default=60, help='Session timeout in seconds (default: 60)')
    args = parser.parse_args()
    
    detector = TriggerWordDetector()
    
    # Set mode based on arguments
    if args.active:
        detector.passive_mode = False
    
    # Set timeout
    if args.timeout > 0:
        detector.session_timeout = args.timeout
    
    # Run the detector
    detector.run()