#!/usr/bin/env python3
"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

NLU Agent
---------
Natural Language Understanding agent that analyzes user input and extracts intents and entities. Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
"""

from common.core.base_agent import BaseAgent
import os
import zmq
import json
import time
import logging
from main_pc_code.agents.error_publisher import ErrorPublisher
import re
import threading
import traceback
from typing import Dict, Any, List, Tuple
from main_pc_code.utils.config_loader import load_config

# Load configuration at module level
config = load_config()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/nlu_agent.log")
    ]
)
logger = logging.getLogger("NLUAgent")

# Constants
ZMQ_REQUEST_TIMEOUT = 5000  # ms

class NLUAgent(BaseAgent):
    """Natural Language Understanding agent that analyzes user input and extracts intents and entities. Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:')."""
    
    def __init__(self, port: int = None, name: str = None, **kwargs):
        """Initialize the NLU Agent."""
        # Get port and name from config with fallbacks
        agent_port = int(config.get("port", 5558)) if port is None else int(port)
        agent_name = str(config.get("name", 'NLUAgent')) if name is None else str(name)
        super().__init__(port=agent_port, name=agent_name)
        
        # Initialize basic state
        self.running = True
        
        # Define intent patterns
        self.intent_patterns = [
            # Vision intents
            (r"what (do you see|can you see|is on my screen|is visible)", "[Vision] Describe"),
            (r"describe (my screen|what you see|this|the screen|the image)", "[Vision] Describe"),
            (r"show me what you (see|can see)", "[Vision] Describe"),
            (r"analyze (my screen|what you see|this|the screen|the image)", "[Vision] Analyze"),
            (r"identify (objects|items|things|elements) (on|in) (my screen|the screen|this image)", "[Vision] Identify"),
            (r"take a (screenshot|picture|photo|snapshot)", "[Vision] Capture"),
            (r"capture (my screen|the screen|a screenshot)", "[Vision] Capture"),
            
            # PC2 intents (complex processing)
            (r"(calculate|compute|solve|evaluate)", "[PC2] Calculate"),
            (r"(search|find|look up|google)", "[PC2] Search"),
            (r"(summarize|summarise|summary)", "[PC2] Summarize"),
            
            # Regular intents
            (r"(hello|hi|hey|greetings)", "[Greeting]"),
            (r"(goodbye|bye|see you|farewell)", "[Farewell]"),
            (r"(thank you|thanks)", "[Thanks]"),
            (r"(help|assist|support)", "[Help]"),
            (r"(what time|current time|what is the time)", "[Time]"),
            (r"(what day|what date|current date)", "[Date]"),
            (r"(weather|temperature|forecast)", "[Weather]"),
            (r"(play music|play song|play audio)", "[PlayMusic]"),
            (r"(stop music|pause music|stop audio|pause audio)", "[StopMusic]"),
            (r"(volume up|increase volume|louder)", "[VolumeUp]"),
            (r"(volume down|decrease volume|quieter)", "[VolumeDown]"),
            (r"(set timer|start timer|countdown)", "[Timer]"),
            (r"(set alarm|wake me up)", "[Alarm]"),
            (r"(remind me|set reminder|create reminder)", "[Reminder]"),
            (r"(what can you do|your capabilities|your functions)", "[Capabilities]"),
        ]
        
        # Initialize ZMQ in background
        self.initialization_status = {
            "is_initialized": False,
            "error": None,
            "progress": 0.0
        }
        self.init_thread = threading.Thread(target=self._perform_initialization, daemon=True)
        self.init_thread.start()
        if not hasattr(self, "_background_threads"):
            self._background_threads = []
        self._background_threads.append(self.init_thread)
        
        # Record start time for uptime calculation
        self.start_time = time.time()
        
        logger.info("NLUAgent basic initialization complete")
        self.error_publisher = ErrorPublisher(self.name)
    
    

        self.error_bus_port = 7150
        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
    def _perform_initialization(self):
        """Perform ZMQ initialization in background."""
        try:
            # Create ZMQ context and socket
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REP)
            self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.socket.bind(f"tcp://*:{self.port}")
            # Initialize Error Bus publisher after context creation
            self.error_bus_pub = self.context.socket(zmq.PUB)
            self.error_bus_pub.connect(self.error_bus_endpoint)
            
            # Mark as initialized
            self.initialization_status.update({
                "is_initialized": True,
                "progress": 1.0
            })
            logger.info(f"NLUAgent ZMQ initialization complete on port {self.port}")
            
        except Exception as e:
            self.initialization_status.update({
                "error": str(e),
                "progress": 0.0
            })
            logger.error(f"ZMQ initialization failed: {e}")
            self.error_publisher.publish_error(error_type="initialization", severity="critical", details=str(e))
    
    def start(self):
        """Start the NLU Agent."""
        logger.info("Starting NLUAgent")
        
        try:
            self._handle_requests()
        except KeyboardInterrupt:
            logger.info("NLUAgent interrupted by user")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the NLU Agent."""
        logger.info("Stopping NLUAgent")
        self.running = False
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'context'):
            self.context.term()
    
    def _handle_requests(self):
        """Handle incoming ZMQ requests."""
        while self.running:
            try:
                # Only process requests if initialized
                if not self.initialization_status["is_initialized"]:
                    time.sleep(0.1)
                    continue
                    
                # Wait for a request
                request = self.socket.recv_json()
                logger.info(f"Received request: {request.get('action', 'unknown')}")
                
                # Process the request
                response = self._process_request(request)
                
                # Send the response
                self.socket.send_json(response)
                
            except zmq.ZMQError as e:
                logger.error(f"ZMQ error: {e}")
            except Exception as e:
                logger.error(f"Error handling request: {e}")
                # Try to send an error response
                try:
                    self.socket.send_json({"status": "error", "error": str(e)})
                except:
                    pass
    
    def _process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request and return a response."""
        action = request.get("action", "")
        
        if action == "analyze":
            return self._analyze_text(request)
        elif action == "health_check":
            return {
                "status": "ok",
                "message": "NLUAgent is running",
                "initialization_status": self.initialization_status
            }
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}
    
    def _analyze_text(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze text to extract intent and entities."""
        try:
            # Check if initialized
            if not self.initialization_status["is_initialized"]:
                return {
                    "status": "error",
                    "error": "NLUAgent is still initializing",
                    "initialization_status": self.initialization_status
                }
            
            # Extract text data
            text = request.get("text", "").lower().strip()
            if not text:
                return {"status": "error", "error": "No text provided"}
            
            # Extract intent
            intent, confidence = self._extract_intent(text)
            
            # Extract entities
            entities = self._extract_entities(text, intent)
            
            # Return the analysis
            return {
                "status": "ok",
                "text": text,
                "intent": intent,
                "entities": entities,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"Error analyzing text: {e}")
            return {"status": "error", "error": f"Failed to analyze text: {str(e)}"}
    
    def _extract_intent(self, text: str) -> Tuple[str, float]:
        """Extract intent from text."""
        # Check each pattern
        for pattern, intent in self.intent_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # Calculate a simple confidence score
                match_length = len(re.search(pattern, text, re.IGNORECASE).group(0))
                confidence = min(0.9, match_length / len(text) * 0.9)
                return intent, confidence
        
        # Default to unknown intent with low confidence
        return "[Unknown]", 0.3
    
    def _extract_entities(self, text: str, intent: str) -> List[Dict[str, Any]]:
        """Extract entities from text based on intent."""
        entities = []
        
        # Extract entities based on intent
        if intent == "[Vision] Describe" or intent == "[Vision] Analyze":
            # No specific entities needed for these intents
            pass
        
        elif intent == "[Vision] Identify":
            # Try to extract what to identify
            match = re.search(r"identify ([\w\s]+) (on|in)", text, re.IGNORECASE)
            if match:
                entities.append({
                    "entity": "target",
                    "value": match.group(1).strip(),
                    "confidence": 0.8
                })
        
        elif intent.startswith("[PC2]"):
            # Extract query for PC2
            if intent == "[PC2] Calculate":
                # Extract the mathematical expression
                pattern = r"(?:calculate|compute|solve|evaluate)\s+(.*?)(?:$|\?)"
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    entities.append({
                        "entity": "expression",
                        "value": match.group(1).strip(),
                        "confidence": 0.9
                    })
            
            elif intent == "[PC2] Search":
                # Extract the search query
                pattern = r"(?:search|find|look up|google)\s+(.*?)(?:$|\?)"
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    entities.append({
                        "entity": "query",
                        "value": match.group(1).strip(),
                        "confidence": 0.9
                    })
            
            elif intent == "[PC2] Summarize":
                # Extract the text to summarize
                pattern = r"(?:summarize|summarise|summary)\s+(.*?)(?:$|\?)"
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    entities.append({
                        "entity": "content",
                        "value": match.group(1).strip(),
                        "confidence": 0.9
                    })
        
        elif intent == "[Timer]":
            # Extract time duration
            pattern = r"(?:set timer|start timer|countdown)\s+(?:for)?\s*(\d+)\s*(second|minute|hour|day)s?"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities.append({
                    "entity": "duration",
                    "value": {
                        "amount": int(match.group(1)),
                        "unit": match.group(2).lower()
                    },
                    "confidence": 0.9
                })
        
        return entities

    def _get_health_status(self):
        """Return detailed health status information."""
        return {
            "status": "ok" if self.initialization_status["is_initialized"] else "initializing",
            "message": "NLUAgent is running",
            "initialization": self.initialization_status,
            "uptime_seconds": time.time() - self.start_time
        }
    
    def health_check(self):
        """Perform a health check and return status."""
        try:
            is_healthy = self.initialization_status["is_initialized"]
            
            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "uptime_seconds": time.time() - self.start_time,
                "initialization_status": self.initialization_status,
                "system_metrics": {
                    "cpu_percent": os.getloadavg()[0],  # 1 minute load average
                    "memory_usage_mb": int(os.popen('ps -p %d -o rss | tail -1' % os.getpid()).read()) / 1024
                }
            }
            return status_report
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "error": f"Health check failed: {str(e)}"
            }
    
    def cleanup(self):
        """Clean up resources before shutdown."""
        self.stop()

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = NLUAgent()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()