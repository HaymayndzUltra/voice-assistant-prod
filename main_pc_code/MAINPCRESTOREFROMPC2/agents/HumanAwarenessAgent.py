from src.core.base_agent import BaseAgent
"""
Human Awareness Agent
--------------------
A ZMQ-based agent that monitors and analyzes human interaction patterns,
including tone detection and emotional analysis.
"""

import logging
import json
import time
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import zmq
import threading
import subprocess
import signal
import sys

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Setup logging
LOG_PATH = "logs/human_awareness_agent.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("HumanAwarenessAgent")

class HumanAwarenessAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="Humanawarenessagent")
        """Initialize the Human Awareness Agent"""
        # Load configuration
        config_path = os.path.join('config', 'system_config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        agent_config = config['agents']['human_awareness']
        self.port = agent_config['port']
        self.tone_detector_port = agent_config['tone_detector_port']
        
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://*:{self.port}")
        
        # Connect to tone detector
        self.tone_socket = self.context.socket(zmq.SUB)
        self.tone_socket.connect(f"tcp://localhost:{self.tone_detector_port}")
        self.tone_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # Initialize state
        self.current_tone = None
        self.tone_history = []
        self.context_window = []
        
        # Start tone detector subprocess
        self._start_tone_detector()
        
        # Start processing threads
        self.running = True
        self.process_thread = threading.Thread(target=self._process_loop)
        self.tone_thread = threading.Thread(target=self._tone_monitor_loop)
        self.process_thread.start()
        self.tone_thread.start()
        
        logger.info(f"Human Awareness Agent initialized on port {self.port}")
    
    def _start_tone_detector(self):
        """Start the tone detector subprocess"""
        try:
            # Get the path to the tone detector script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            tone_detector_path = os.path.join(script_dir, "tone_detector.py")
            
            # Start the tone detector as a subprocess
            self.tone_process = subprocess.Popen(
                [sys.executable, tone_detector_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info("Tone detector started successfully")
            
        except Exception as e:
            logger.error(f"Error starting tone detector: {str(e)}")
            self.tone_process = None
    
    def _tone_monitor_loop(self):
        """Monitor tone detector output"""
        while self.running:
            try:
                # Receive tone updates
                tone_data = self.tone_socket.recv_json()
                
                # Update current tone
                self.current_tone = tone_data.get("tone")
                
                # Add to history
                self.tone_history.append({
                    "tone": self.current_tone,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Keep only last 100 entries
                if len(self.tone_history) > 100:
                    self.tone_history = self.tone_history[-100:]
                
                logger.debug(f"Tone update: {self.current_tone}")
                
            except Exception as e:
                logger.error(f"Error in tone monitor loop: {str(e)}")
                time.sleep(1)  # Prevent tight loop on error
    
    def _process_loop(self):
        """Main processing loop"""
        while self.running:
            try:
                # Wait for request
                request_str = self.socket.recv_string()
                request = json.loads(request_str)
                
                # Process request
                response = self._handle_request(request)
                
                # Send response
                self.socket.send_string(json.dumps(response))
                
            except Exception as e:
                logger.error(f"Error in process loop: {str(e)}")
                self.socket.send_string(json.dumps({
                    "status": "error",
                    "message": str(e)
                }))
    
    def _handle_request(self, request: Dict) -> Dict:
        """Handle incoming requests"""
        try:
            action = request.get("action")
            
            if action == "get_tone":
                return {
                    "status": "ok",
                    "current_tone": self.current_tone,
                    "tone_history": self.tone_history[-10:],  # Last 10 entries
                    "timestamp": datetime.now().isoformat()
                }
            
            elif action == "get_context":
                return {
                    "status": "ok",
                    "context": self.context_window,
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "status": "error",
                "message": f"Unknown action: {action}"
            }
            
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def shutdown(self):
        """Shutdown the agent"""
        self.running = False
        
        # Stop threads
        if self.process_thread.is_alive():
            self.process_thread.join()
        if self.tone_thread.is_alive():
            self.tone_thread.join()
        
        # Stop tone detector
        if self.tone_process:
            self.tone_process.terminate()
            self.tone_process.wait()
        
        # Close sockets
        self.socket.close()
        self.tone_socket.close()
        self.context.term()
        
        logger.info("Human Awareness Agent shut down")

if __name__ == "__main__":
    agent = HumanAwarenessAgent()
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.shutdown() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise