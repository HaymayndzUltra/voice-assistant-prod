#!/usr/bin/env python3
import sys
import os

# Add the project's main_pc_code directory to the Python path
MAIN_PC_CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if MAIN_PC_CODE_DIR not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR)

# Now we can use absolute imports from the main_pc_code directory
from src.core.base_agent import BaseAgent

"""
Coordinator Agent
----------------
Central coordinator that manages the flow of information between all agents.
"""

import zmq
import json
import time
import logging
import threading
import base64
from typing import Dict, Any, List, Optional, Tuple, Union
from utils.config_parser import parse_agent_args
from utils.service_discovery_client import discover_service
from src.network.secure_zmq import is_secure_zmq_enabled, setup_curve_client

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
_agent_args = parse_agent_args()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/coordinator_agent.log")
    ]
)
logger = logging.getLogger("CoordinatorAgent")

# Constants for agent communication
COORDINATOR_PORT = 26002
PROACTIVE_SUGGESTION_PORT = 5591

# Secure ZMQ configuration
SECURE_ZMQ = is_secure_zmq_enabled()

# Proactive assistance settings
INACTIVITY_THRESHOLD = 30  # Seconds of inactivity before presenting a suggestion
MAX_PENDING_SUGGESTIONS = 5  # Maximum number of pending suggestions to store

# Utility -------------------------------------------------------------------

def find_available_port(start_port: int, max_attempts: int = 20) -> int:
    """Find and return an available TCP port starting from `start_port`.

    This is a lightweight helper that incrementally checks ports
    `[start_port, start_port + max_attempts)` and returns the first one that
    can be bound. Raises RuntimeError if none are available.
    """
    import socket

    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                # `SO_REUSEADDR` allows us to probe ports that are in TIME_WAIT.
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("", port))
                return port
        except OSError:
            # Port is in use, try the next one
            continue

    raise RuntimeError(
        f"CoordinatorAgent could not find an available port after {max_attempts} attempts, starting from {start_port}."
    )


class CoordinatorAgent(BaseAgent):
    """Central coordinator that manages the flow of information between all agents."""
    
    def __init__(self, port: int = COORDINATOR_PORT, **kwargs):
        """Initialize the Coordinator Agent."""
        self.port = port
        super().__init__(port=self.port, name="CoordinatorAgent")
        
        # Create ZMQ context and socket for the coordinator
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        
        # Apply secure ZMQ if enabled
        if SECURE_ZMQ:
            setup_curve_client(self.socket, server_mode=True)
            logger.info("Secure ZMQ enabled for CoordinatorAgent")
            
        self.socket.bind(f"tcp://*:{self.port}")
        
        # Discover and connect to required services using service discovery
        self.service_info = {}
        self._discover_services()
        
        # Create socket for proactive suggestions (with port fallback)
        self.suggestion_socket = self.context.socket(zmq.REP)
        self.suggestion_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.suggestion_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        
        # Apply secure ZMQ to suggestion socket if enabled
        if SECURE_ZMQ:
            setup_curve_client(self.suggestion_socket, server_mode=True)

        # Attempt to bind to the preferred port; fall back if it's unavailable.
        self.suggestion_port = PROACTIVE_SUGGESTION_PORT
        try:
            self.suggestion_socket.bind(f"tcp://*:{self.suggestion_port}")
        except zmq.ZMQError as e:
            logger.warning(
                f"Port {self.suggestion_port} already in use (error: {e}). "
                "Searching for the next available port."
            )
            self.suggestion_port = find_available_port(self.suggestion_port + 1)
            self.suggestion_socket.bind(f"tcp://*:{self.suggestion_port}")
            logger.info(f"Proactive suggestion socket bound to fallback port {self.suggestion_port}")
        
        # Flag to control the agent
        self.running = True
        
        # Proactive assistance state
        self.last_interaction_time = time.time()
        self.pending_suggestions = []
        
        # Start service discovery refresh thread
        self.discovery_thread = threading.Thread(target=self._service_discovery_refresh_loop)
        self.discovery_thread.daemon = True
        self.discovery_thread.start()
        
        # Start the proactive suggestion handler thread
        self.suggestion_thread = threading.Thread(target=self._handle_proactive_suggestions)
        self.suggestion_thread.daemon = True
        self.suggestion_thread.start()
        
        # Start the inactivity checker thread
        self.inactivity_thread = threading.Thread(target=self._check_inactivity)
        self.inactivity_thread.daemon = True
        self.inactivity_thread.start()
        
        logger.info(f"CoordinatorAgent initialized and listening on port {self.port}")
    
    def _discover_services(self):
        """Discover required services using service discovery"""
        try:
            # Discover all required services
            required_services = [
                "TaskRouter", "TTSConnector", "HealthMonitor", 
                "VisionCaptureAgent", "VisionProcessingAgent"
            ]
            
            for service_name in required_services:
                service_info = discover_service(service_name)
                if service_info:
                    self.service_info[service_name] = service_info
                    logger.info(f"Discovered {service_name} at {service_info['host']}:{service_info['port']}")
                else:
                    logger.warning(f"Failed to discover {service_name}, will retry later")
                    
            # Also try to discover PC2 services
            pc2_services = ["PC2Agent", "VisionProcessingAgent"]
            for service_name in pc2_services:
                service_info = discover_service(service_name)
                if service_info:
                    self.service_info[service_name] = service_info
                    logger.info(f"Discovered PC2 service {service_name} at {service_info['host']}:{service_info['port']}")
                else:
                    logger.warning(f"Failed to discover PC2 service {service_name}, will retry later")
        
        except Exception as e:
            logger.error(f"Error during service discovery: {str(e)}")
    
    def _service_discovery_refresh_loop(self):
        """Periodically refresh service discovery information"""
        while self.running:
            time.sleep(60)  # Refresh every minute
            self._discover_services()
    
    def _get_service_connection(self, service_name):
        """Get a connection to a service using service discovery"""
        if service_name not in self.service_info:
            # Try to discover the service
            service_info = discover_service(service_name)
            if service_info:
                self.service_info[service_name] = service_info
                logger.info(f"Discovered {service_name} at {service_info['host']}:{service_info['port']}")
            else:
                logger.error(f"Failed to discover {service_name}")
                return None
        
        # Create a new socket for the request
        socket = self.context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        
        # Apply secure ZMQ if enabled
        if SECURE_ZMQ:
            setup_curve_client(socket)
        
        # Connect to the service
        host = self.service_info[service_name]["host"]
        port = self.service_info[service_name]["port"]
        socket.connect(f"tcp://{host}:{port}")
        
        return socket
    
    def start(self):
        """Start the Coordinator Agent."""
        print("Starting CoordinatorAgent...")
        logger.info("Starting CoordinatorAgent")
        
        try:
            self._handle_requests()
        except KeyboardInterrupt:
            logger.info("CoordinatorAgent interrupted by user")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the Coordinator Agent."""
        logger.info("Stopping CoordinatorAgent")
        self.running = False
        self.socket.close()
        self.suggestion_socket.close()
        self.context.term()
    
    def _handle_requests(self):
        """Handle incoming ZMQ requests."""
        while self.running:
            try:
                # Wait for a request from the client
                request_str = self.socket.recv_string()
                request = json.loads(request_str)
                
                # Update the last interaction time
                self.last_interaction_time = time.time()
                
                # Process the request
                response = self._process_request(request)
                
                # Send the response back to the client
                self.socket.send_string(json.dumps(response))
                
            except zmq.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    # Timeout occurred, continue to next iteration
                    continue
                else:
                    # Other ZMQ error
                    logger.error(f"ZMQ error in request handling: {e}")
            
            except Exception as e:
                logger.error(f"Error handling request: {e}")
                # Try to send an error response
                try:
                    self.socket.send_string(json.dumps({
                        "status": "error",
                        "message": str(e)
                    }))
                except:
                    pass

    def _handle_proactive_suggestions(self):
        """Handle incoming proactive suggestions."""
        while self.running:
            try:
                # Wait for a suggestion from the Proactive Agent
                suggestion_str = self.suggestion_socket.recv_string()
                suggestion = json.loads(suggestion_str)
                
                # Send acknowledgment
                self.suggestion_socket.send_string(json.dumps({"status": "received"}))
                
                # Add the suggestion to the pending list
                self._add_pending_suggestion(suggestion)
                
            except zmq.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    # Timeout occurred, continue to next iteration
                    continue
                else:
                    # Other ZMQ error
                    logger.error(f"ZMQ error in suggestion handling: {e}")
            
            except Exception as e:
                logger.error(f"Error handling suggestion: {e}")
                # Try to send an error response
                try:
                    self.suggestion_socket.send_string(json.dumps({
                        "status": "error",
                        "message": str(e)
                    }))
                except:
                    pass

    def _check_inactivity(self):
        """Check for user inactivity and present proactive suggestions if available."""
        while self.running:
            try:
                current_time = time.time()
                inactive_time = current_time - self.last_interaction_time
                
                # If the user has been inactive for a while and we have pending suggestions
                if inactive_time > INACTIVITY_THRESHOLD and self.pending_suggestions:
                    # Get the most relevant suggestion (currently just the first one)
                    suggestion = self.pending_suggestions.pop(0)
                    
                    # Present the suggestion to the user
                    self._present_suggestion(suggestion)
                    
                    # Reset the inactivity timer to avoid spamming suggestions
                    self.last_interaction_time = current_time
                
                # Sleep for a bit to avoid excessive CPU usage
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error checking inactivity: {e}")
                time.sleep(1)

    def _add_pending_suggestion(self, suggestion: Dict[str, Any]):
        """Add a suggestion to the pending list, maintaining a maximum size."""
        # Add the suggestion to the list
        self.pending_suggestions.append(suggestion)
        
        # Trim the list if it exceeds the maximum size
        if len(self.pending_suggestions) > MAX_PENDING_SUGGESTIONS:
            # Remove the oldest suggestion
            self.pending_suggestions.pop(0)
        
        logger.info(f"Added suggestion to pending list (total: {len(self.pending_suggestions)})")

    def _present_suggestion(self, suggestion: Dict[str, Any]):
        """Present a proactive suggestion to the user."""
        try:
            # Log the suggestion
            logger.info(f"Presenting proactive suggestion: {suggestion['content']}")
            
            # Use TTS to speak the suggestion
            socket = self._get_service_connection("TTSConnector")
            if socket:
                tts_request = {
                    "text": suggestion["content"],
                    "voice": suggestion.get("voice", "default"),
                    "priority": "high"
                }
                
                socket.send_string(json.dumps(tts_request))
                socket.recv_string()  # Wait for acknowledgment
                socket.close()
            
        except Exception as e:
            logger.error(f"Error presenting suggestion: {e}")

    def _process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming request based on its type."""
        request_type = request.get("type", "text")
        
        if request_type == "audio":
            return self._process_audio(request)
        elif request_type == "text":
            return self._process_text(request)
        elif request_type == "vision":
            return self._process_vision(request)
        elif request_type == "health_check":
            return self._health_check()
        else:
            return {
                "status": "error",
                "message": f"Unknown request type: {request_type}"
            }

    def _process_audio(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process an audio request."""
        try:
            # Extract audio data
            audio_data = request.get("audio_data")
            if not audio_data:
                return {"status": "error", "message": "No audio data provided"}
            
            # Decode base64 audio data if needed
            if isinstance(audio_data, str):
                audio_data = base64.b64decode(audio_data)
            
            # Forward the audio to the TaskRouter for processing
            socket = self._get_service_connection("TaskRouter")
            if not socket:
                return {"status": "error", "message": "TaskRouter service not available"}
                
            task_request = {
                "type": "audio",
                "audio_data": base64.b64encode(audio_data).decode("ascii") if isinstance(audio_data, bytes) else audio_data,
                "format": request.get("format", "wav"),
                "sample_rate": request.get("sample_rate", 16000)
            }
            
            socket.send_string(json.dumps(task_request))
            response_str = socket.recv_string()
            socket.close()
            
            response = json.loads(response_str)
            return response
            
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            return {"status": "error", "message": str(e)}

    def _process_text(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process text input through the pipeline."""
        try:
            # Extract text data
            text = request.get("text", "")
            if not text:
                return {"status": "error", "error": "No text provided"}
            
            # Step 1: Send text to Task Router for NLU processing
            logger.info("Sending text to Task Router for NLU processing")
            socket = self._get_service_connection("TaskRouter")
            if not socket:
                return {"status": "error", "error": "TaskRouter service not available"}
            
            task_request = {
                "type": "text",
                "text": text
            }
            
            socket.send_string(json.dumps(task_request))
            nlu_response_str = socket.recv_string()
            socket.close()
            
            nlu_response = json.loads(nlu_response_str)
            
            if nlu_response.get("status") != "ok":
                logger.error(f"NLU error: {nlu_response.get('error')}")
                return nlu_response
            
            # Extract intent and entities
            intent = nlu_response.get("intent", "")
            entities = nlu_response.get("entities", [])
            confidence = nlu_response.get("confidence", 0.0)
            
            logger.info(f"Intent: {intent}, Confidence: {confidence}")
            logger.info(f"Entities: {entities}")
            
            # Step 2: Route based on intent
            if intent.startswith("[Vision]"):
                # Handle vision-related intents
                return self._process_vision({"action": "process_vision", "text": text, "intent": intent})
            elif intent.startswith("[PC2]"):
                # Route to PC2 for processing
                logger.info("Routing to PC2 Agent")
                socket = self._get_service_connection("PC2Agent")
                if not socket:
                    return {"status": "error", "error": "PC2Agent service not available"}
                
                pc2_request = {
                    "type": "process",
                    "text": text,
                    "intent": intent,
                    "entities": entities
                }
                
                socket.send_string(json.dumps(pc2_request))
                pc2_response_str = socket.recv_string()
                socket.close()
                
                pc2_response = json.loads(pc2_response_str)
                
                if pc2_response.get("status") != "ok":
                    logger.error(f"PC2 error: {pc2_response.get('error')}")
                    return pc2_response
                
                # Extract the response text
                response_text = pc2_response.get("response", "")
                
            else:
                # Route to Task Router for dialog generation
                logger.info("Routing to Task Router for dialog generation")
                socket = self._get_service_connection("TaskRouter")
                if not socket:
                    return {"status": "error", "error": "TaskRouter service not available"}
                
                dialog_request = {
                    "type": "dialog",
                    "text": text,
                    "intent": intent,
                    "entities": entities
                }
                
                socket.send_string(json.dumps(dialog_request))
                dialog_response_str = socket.recv_string()
                socket.close()
                
                dialog_response = json.loads(dialog_response_str)
                
                if dialog_response.get("status") != "ok":
                    logger.error(f"Dialog error: {dialog_response.get('error')}")
                    return dialog_response
                
                # Extract the response text
                response_text = dialog_response.get("response", "")
            
            # Step 3: Send response to TTS Agent
            logger.info(f"Sending response to TTS Agent: {response_text}")
            socket = self._get_service_connection("TTSConnector")
            if not socket:
                return {"status": "error", "error": "TTSConnector service not available"}
            
            tts_request = {
                "text": response_text,
                "voice": request.get("voice", "default"),
                "priority": "high"
            }
            
            socket.send_string(json.dumps(tts_request))
            tts_response_str = socket.recv_string()
            socket.close()
            
            tts_response = json.loads(tts_response_str)
            
            if tts_response.get("status") != "ok":
                logger.error(f"TTS error: {tts_response.get('error')}")
                return tts_response
            
            # Extract the audio data
            audio_data = tts_response.get("audio_data", "")
            
            # Return the final response
            return {
                "status": "ok",
                "response": response_text,
                "audio_data": audio_data
            }
            
        except Exception as e:
            logger.error(f"Error processing text: {e}")
            return {"status": "error", "error": f"Failed to process text: {str(e)}"}

    def _process_vision(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process vision-related requests through the vision pipeline."""
        try:
            # Extract text data and intent
            text = request.get("text", "")
            intent = request.get("intent", "")
            
            logger.info(f"Processing vision request: {text}")
            
            # Step 1: Capture screenshot using VisionCaptureAgent
            logger.info("Requesting screenshot from VisionCaptureAgent")
            socket = self._get_service_connection("VisionCaptureAgent")
            if not socket:
                return {"status": "error", "error": "VisionCaptureAgent service not available"}
            
            capture_request = {
                "type": "capture_screen"
            }
            
            socket.send_string(json.dumps(capture_request))
            capture_response_str = socket.recv_string()
            socket.close()
            
            capture_response = json.loads(capture_response_str)
            
            if capture_response.get("status") != "ok":
                logger.error(f"Vision capture error: {capture_response.get('error')}")
                return capture_response
            
            # Extract the image data
            image_base64 = capture_response.get("image_base64", "")
            if not image_base64:
                return {"status": "error", "error": "No image data received from VisionCaptureAgent"}
            
            # Step 2: Process the image using VisionProcessingAgent on PC2
            logger.info("Sending image to VisionProcessingAgent for processing")
            socket = self._get_service_connection("VisionProcessingAgent")
            if not socket:
                return {"status": "error", "error": "VisionProcessingAgent service not available"}
            
            processing_request = {
                "type": "describe_image",
                "image_base64": image_base64,
                "prompt": text  # Use the original user text as the prompt
            }
            
            socket.send_string(json.dumps(processing_request))
            processing_response_str = socket.recv_string()
            socket.close()
            
            processing_response = json.loads(processing_response_str)
            
            if processing_response.get("status") != "ok":
                logger.error(f"Vision processing error: {processing_response.get('error')}")
                return processing_response
            
            # Extract the description
            description = processing_response.get("description", "")
            if not description:
                return {"status": "error", "error": "No description received from VisionProcessingAgent"}
            
            # Step 3: Send the description to TTS Agent
            logger.info(f"Sending vision description to TTS Agent: {description[:100]}...")
            socket = self._get_service_connection("TTSConnector")
            if not socket:
                return {"status": "error", "error": "TTSConnector service not available"}
            
            tts_request = {
                "text": description,
                "voice": request.get("voice", "default"),
                "priority": "high"
            }
            
            socket.send_string(json.dumps(tts_request))
            tts_response_str = socket.recv_string()
            socket.close()
            
            tts_response = json.loads(tts_response_str)
            
            if tts_response.get("status") != "ok":
                logger.error(f"TTS error: {tts_response.get('error')}")
                return tts_response
            
            # Extract the audio data
            audio_data = tts_response.get("audio_data", "")
            
            # Return the final response
            return {
                "status": "ok",
                "response": description,
                "audio_data": audio_data
            }
            
        except Exception as e:
            logger.error(f"Error processing vision request: {e}")
            return {"status": "error", "error": f"Failed to process vision request: {str(e)}"}

    def _health_check(self) -> Dict[str, Any]:
        """Perform a health check on all connected agents."""
        health_status = {
            "coordinator": "ok",
            "task_router": "unknown",
            "tts": "unknown",
            "pc2": "unknown",
            "health_monitor": "unknown",
            "vision_capture": "unknown",
            "vision_processing": "unknown"
        }
        
        # Check Task Router
        try:
            socket = self._get_service_connection("TaskRouter")
            if not socket:
                health_status["task_router"] = "error"
                return {
                    "status": "ok",
                    "health_status": health_status
                }
            
            health_request = {
                "type": "health_check"
            }
            
            socket.send_string(json.dumps(health_request))
            response_str = socket.recv_string()
            socket.close()
            
            response = json.loads(response_str)
            
            if response.get("status") == "ok":
                health_status["task_router"] = "ok"
            else:
                health_status["task_router"] = "error"
        except:
            health_status["task_router"] = "error"
        
        # Check TTS Agent
        try:
            socket = self._get_service_connection("TTSConnector")
            if not socket:
                health_status["tts"] = "error"
                return {
                    "status": "ok",
                    "health_status": health_status
                }
            
            health_request = {
                "type": "health_check"
            }
            
            socket.send_string(json.dumps(health_request))
            response_str = socket.recv_string()
            socket.close()
            
            response = json.loads(response_str)
            
            if response.get("status") == "ok":
                health_status["tts"] = "ok"
            else:
                health_status["tts"] = "error"
        except:
            health_status["tts"] = "error"
        
        # Check PC2 Agent
        try:
            socket = self._get_service_connection("PC2Agent")
            if not socket:
                health_status["pc2"] = "error"
                return {
                    "status": "ok",
                    "health_status": health_status
                }
            
            health_request = {
                "type": "health_check"
            }
            
            socket.send_string(json.dumps(health_request))
            response_str = socket.recv_string()
            socket.close()
            
            response = json.loads(response_str)
            
            if response.get("status") == "ok":
                health_status["pc2"] = "ok"
            else:
                health_status["pc2"] = "error"
        except:
            health_status["pc2"] = "error"
        
        # Check Health Monitor
        try:
            socket = self._get_service_connection("HealthMonitor")
            if not socket:
                health_status["health_monitor"] = "error"
                return {
                    "status": "ok",
                    "health_status": health_status
                }
            
            health_request = {
                "type": "health_check"
            }
            
            socket.send_string(json.dumps(health_request))
            response_str = socket.recv_string()
            socket.close()
            
            response = json.loads(response_str)
            
            if response.get("status") == "ok":
                health_status["health_monitor"] = "ok"
            else:
                health_status["health_monitor"] = "error"
        except:
            health_status["health_monitor"] = "error"
        
        # Check Vision Capture Agent
        try:
            socket = self._get_service_connection("VisionCaptureAgent")
            if not socket:
                health_status["vision_capture"] = "error"
                return {
                    "status": "ok",
                    "health_status": health_status
                }
            
            health_request = {
                "type": "health_check"
            }
            
            socket.send_string(json.dumps(health_request))
            response_str = socket.recv_string()
            socket.close()
            
            response = json.loads(response_str)
            
            if response.get("status") == "ok":
                health_status["vision_capture"] = "ok"
            else:
                health_status["vision_capture"] = "error"
        except:
            health_status["vision_capture"] = "error"
        
        # Check Vision Processing Agent
        try:
            socket = self._get_service_connection("VisionProcessingAgent")
            if not socket:
                health_status["vision_processing"] = "error"
                return {
                    "status": "ok",
                    "health_status": health_status
                }
            
            health_request = {
                "type": "health_check"
            }
            
            socket.send_string(json.dumps(health_request))
            response_str = socket.recv_string()
            socket.close()
            
            response = json.loads(response_str)
            
            if response.get("status") == "ok":
                health_status["vision_processing"] = "ok"
            else:
                health_status["vision_processing"] = "error"
        except:
            health_status["vision_processing"] = "error"
        
        return {
            "status": "ok",
            "health_status": health_status
        }

if __name__ == "__main__":
    # Create and start the Coordinator Agent
    agent = CoordinatorAgent()
    print("Agent created, starting...")
    agent.start()
    print("Agent started.")