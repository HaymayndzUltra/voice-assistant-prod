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
TASK_ROUTER_PORT = 5571
TTS_CONNECTOR_PORT = 5562
PC2_AGENT_PORT = 5560
HEALTH_MONITOR_PORT = 5584
VISION_CAPTURE_PORT = 5587
VISION_PROCESSING_PORT = 5588
PROACTIVE_SUGGESTION_PORT = 5591

# PC2 address (update as needed)
PC2_ADDRESS = getattr(_agent_args, 'host', 'localhost')  # Change to PC2's actual IP if needed

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
        self.socket.bind(f"tcp://*:{self.port}")
        
        # Create sockets for communicating with other agents
        self.task_router_socket = self.context.socket(zmq.REQ)
        self.task_router_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.task_router_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.task_router_socket.connect(f"tcp://{getattr(_agent_args, 'host', 'localhost')}:{TASK_ROUTER_PORT}")
        
        self.tts_socket = self.context.socket(zmq.REQ)
        self.tts_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.tts_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.tts_socket.connect(f"tcp://{getattr(_agent_args, 'host', 'localhost')}:{TTS_CONNECTOR_PORT}")
        
        self.pc2_socket = self.context.socket(zmq.REQ)
        self.pc2_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.pc2_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.pc2_socket.connect(f"tcp://{PC2_ADDRESS}:{PC2_AGENT_PORT}")
        
        self.health_monitor_socket = self.context.socket(zmq.REQ)
        self.health_monitor_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.health_monitor_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.health_monitor_socket.connect(f"tcp://{getattr(_agent_args, 'host', 'localhost')}:{HEALTH_MONITOR_PORT}")
        
        # Create sockets for vision pipeline
        self.vision_capture_socket = self.context.socket(zmq.REQ)
        self.vision_capture_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.vision_capture_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.vision_capture_socket.connect(f"tcp://{getattr(_agent_args, 'host', 'localhost')}:{VISION_CAPTURE_PORT}")
        
        self.vision_processing_socket = self.context.socket(zmq.REQ)
        self.vision_processing_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.vision_processing_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.vision_processing_socket.connect(f"tcp://{PC2_ADDRESS}:{VISION_PROCESSING_PORT}")
        
        # Create socket for proactive suggestions (with port fallback)
        self.suggestion_socket = self.context.socket(zmq.REP)
        self.suggestion_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.suggestion_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)

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
        
        # Start the proactive suggestion handler thread
        self.suggestion_thread = threading.Thread(target=self._handle_proactive_suggestions)
        self.suggestion_thread.daemon = True
        self.suggestion_thread.start()
        
        # Start the inactivity checker thread
        self.inactivity_thread = threading.Thread(target=self._check_inactivity)
        self.inactivity_thread.daemon = True
        self.inactivity_thread.start()
        
        logger.info(f"CoordinatorAgent initialized and listening on port {self.port}")
    
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
        self.task_router_socket.close()
        self.tts_socket.close()
        self.pc2_socket.close()
        self.health_monitor_socket.close()
        self.vision_capture_socket.close()
        self.vision_processing_socket.close()
        self.suggestion_socket.close()
        self.context.term()
    
    def _handle_requests(self):
        """Handle incoming ZMQ requests."""
        while self.running:
            try:
                # Wait for a request
                request = self.socket.recv_json()
                logger.info(f"Received request: {request.get('action', 'unknown')}")
                
                # Update last interaction time
                self.last_interaction_time = time.time()
                
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
    
    def _handle_proactive_suggestions(self):
        """Handle incoming proactive suggestions in a separate thread."""
        logger.info("Starting proactive suggestion handler thread")
        
        while self.running:
            try:
                # Use poll to make this non-blocking so we can check if running flag is still True
                if self.suggestion_socket.poll(1000) == zmq.POLLIN:
                    # Receive suggestion
                    suggestion = self.suggestion_socket.recv_json()
                    logger.info(f"Received proactive suggestion: {suggestion.get('suggestion_text', '')[:50]}...")
                    
                    # Send acknowledgment
                    self.suggestion_socket.send_json({"status": "ok"})
                    
                    # Add to pending suggestions
                    self._add_pending_suggestion(suggestion)
            except zmq.ZMQError as e:
                logger.error(f"ZMQ error in suggestion handler: {e}")
            except Exception as e:
                logger.error(f"Error handling suggestion: {e}")
                # Try to send an error response
                try:
                    self.suggestion_socket.send_json({"status": "error", "error": str(e)})
                except:
                    pass
            
            # Sleep briefly to avoid CPU spinning
            time.sleep(0.1)
    
    def _check_inactivity(self):
        """Check for user inactivity and present proactive suggestions when appropriate."""
        logger.info("Starting inactivity checker thread")
        
        while self.running:
            try:
                # Check if there has been no interaction for the threshold period
                current_time = time.time()
                inactivity_time = current_time - self.last_interaction_time
                
                if inactivity_time >= INACTIVITY_THRESHOLD and self.pending_suggestions:
                    # Present the oldest suggestion
                    suggestion = self.pending_suggestions.pop(0)
                    self._present_suggestion(suggestion)
                    
                    # Wait a bit before checking again to avoid rapid-fire suggestions
                    time.sleep(10)
                else:
                    # Sleep briefly before checking again
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Error in inactivity checker: {e}")
                time.sleep(5)
    
    def _add_pending_suggestion(self, suggestion: Dict[str, Any]):
        """Add a suggestion to the pending suggestions queue."""
        # Add suggestion with timestamp
        suggestion["received_time"] = time.time()
        
        # Add to pending suggestions
        self.pending_suggestions.append(suggestion)
        
        # Trim list if needed
        if len(self.pending_suggestions) > MAX_PENDING_SUGGESTIONS:
            # Remove oldest suggestion
            self.pending_suggestions = self.pending_suggestions[-MAX_PENDING_SUGGESTIONS:]
        
        logger.info(f"Added suggestion to queue. Now have {len(self.pending_suggestions)} pending suggestions")
    
    def _present_suggestion(self, suggestion: Dict[str, Any]):
        """Present a proactive suggestion to the user."""
        try:
            suggestion_text = suggestion.get("suggestion_text", "")
            logger.info(f"Presenting proactive suggestion: {suggestion_text}")
            
            # Send suggestion to TTS Agent
            self.tts_socket.send_json({
                "action": "synthesize",
                "text": suggestion_text
            })
            tts_response = self.tts_socket.recv_json()
            
            if tts_response.get("status") != "ok":
                logger.error(f"TTS error: {tts_response.get('error')}")
                return
            
            # Log that the suggestion was presented
            logger.info(f"Proactive suggestion presented successfully: {suggestion.get('triggering_context', '')}")
            
        except Exception as e:
            logger.error(f"Error presenting suggestion: {e}")
    
    def _process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request and return a response."""
        action = request.get("action", "")
        
        if action == "process_audio":
            return self._process_audio(request)
        elif action == "process_text":
            return self._process_text(request)
        elif action == "process_vision":
            return self._process_vision(request)
        elif action == "health_check":
            return self._health_check()
        elif action == "ping":
            # Simple ping response for health checks
            return {"status": "ok", "message": "CoordinatorAgent is running"}
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}
    
    def _process_audio(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process audio input through the pipeline."""
        try:
            # Extract audio data
            audio_data = request.get("audio_data", "")
            if not audio_data:
                return {"status": "error", "error": "No audio data provided"}
            
            # Step 1: Send audio to Task Router for transcription
            logger.info("Sending audio to Task Router for transcription")
            self.task_router_socket.send_json({
                "action": "route",
                "target": "transcription",
                "data": {
                    "audio_data": audio_data
                }
            })
            stt_response = self.task_router_socket.recv_json()
            
            if stt_response.get("status") != "ok":
                logger.error(f"STT error: {stt_response.get('error')}")
                return stt_response
            
            # Extract the transcript
            transcript = stt_response.get("transcript", "")
            logger.info(f"Transcript: {transcript}")
            
            # Continue with text processing
            return self._process_text({"action": "process_text", "text": transcript})
            
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            return {"status": "error", "error": f"Failed to process audio: {str(e)}"}
    
    def _process_text(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process text input through the pipeline."""
        try:
            # Extract text data
            text = request.get("text", "")
            if not text:
                return {"status": "error", "error": "No text provided"}
            
            # Step 1: Send text to Task Router for NLU processing
            logger.info("Sending text to Task Router for NLU processing")
            self.task_router_socket.send_json({
                "action": "route",
                "target": "nlu",
                "data": {
                    "text": text
                }
            })
            nlu_response = self.task_router_socket.recv_json()
            
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
                self.pc2_socket.send_json({
                    "action": "process",
                    "text": text,
                    "intent": intent,
                    "entities": entities
                })
                pc2_response = self.pc2_socket.recv_json()
                
                if pc2_response.get("status") != "ok":
                    logger.error(f"PC2 error: {pc2_response.get('error')}")
                    return pc2_response
                
                # Extract the response text
                response_text = pc2_response.get("response", "")
                
            else:
                # Route to Task Router for dialog generation
                logger.info("Routing to Task Router for dialog generation")
                self.task_router_socket.send_json({
                    "action": "route",
                    "target": "dialog",
                    "data": {
                        "text": text,
                        "intent": intent,
                        "entities": entities
                    }
                })
                dialog_response = self.task_router_socket.recv_json()
                
                if dialog_response.get("status") != "ok":
                    logger.error(f"Dialog error: {dialog_response.get('error')}")
                    return dialog_response
                
                # Extract the response text
                response_text = dialog_response.get("response", "")
            
            # Step 3: Send response to TTS Agent
            logger.info(f"Sending response to TTS Agent: {response_text}")
            self.tts_socket.send_json({
                "action": "synthesize",
                "text": response_text
            })
            tts_response = self.tts_socket.recv_json()
            
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
            self.vision_capture_socket.send_json({
                "action": "capture_screen"
            })
            capture_response = self.vision_capture_socket.recv_json()
            
            if capture_response.get("status") != "ok":
                logger.error(f"Vision capture error: {capture_response.get('error')}")
                return capture_response
            
            # Extract the image data
            image_base64 = capture_response.get("image_base64", "")
            if not image_base64:
                return {"status": "error", "error": "No image data received from VisionCaptureAgent"}
            
            # Step 2: Process the image using VisionProcessingAgent on PC2
            logger.info("Sending image to VisionProcessingAgent for processing")
            self.vision_processing_socket.send_json({
                "action": "describe_image",
                "image_base64": image_base64,
                "prompt": text  # Use the original user text as the prompt
            })
            processing_response = self.vision_processing_socket.recv_json()
            
            if processing_response.get("status") != "ok":
                logger.error(f"Vision processing error: {processing_response.get('error')}")
                return processing_response
            
            # Extract the description
            description = processing_response.get("description", "")
            if not description:
                return {"status": "error", "error": "No description received from VisionProcessingAgent"}
            
            # Step 3: Send the description to TTS Agent
            logger.info(f"Sending vision description to TTS Agent: {description[:100]}...")
            self.tts_socket.send_json({
                "action": "synthesize",
                "text": description
            })
            tts_response = self.tts_socket.recv_json()
            
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
            self.task_router_socket.send_json({"action": "health_check"})
            response = self.task_router_socket.recv_json()
            health_status["task_router"] = "ok" if response.get("status") == "ok" else "error"
        except:
            health_status["task_router"] = "error"
        
        # Check TTS Agent
        try:
            self.tts_socket.send_json({"action": "health_check"})
            response = self.tts_socket.recv_json()
            health_status["tts"] = "ok" if response.get("status") == "ok" else "error"
        except:
            health_status["tts"] = "error"
        
        # Check PC2 Agent
        try:
            self.pc2_socket.send_json({"action": "health_check"})
            response = self.pc2_socket.recv_json()
            health_status["pc2"] = "ok" if response.get("status") == "ok" else "error"
        except:
            health_status["pc2"] = "error"
        
        # Check Health Monitor
        try:
            self.health_monitor_socket.send_json({"action": "health_check"})
            response = self.health_monitor_socket.recv_json()
            health_status["health_monitor"] = "ok" if response.get("status") == "ok" else "error"
        except:
            health_status["health_monitor"] = "error"
        
        # Check Vision Capture Agent
        try:
            self.vision_capture_socket.send_json({"action": "health_check"})
            response = self.vision_capture_socket.recv_json()
            health_status["vision_capture"] = "ok" if response.get("status") == "ok" else "error"
        except:
            health_status["vision_capture"] = "error"
        
        # Check Vision Processing Agent
        try:
            self.vision_processing_socket.send_json({"action": "health_check"})
            response = self.vision_processing_socket.recv_json()
            health_status["vision_processing"] = "ok" if response.get("status") == "ok" else "error"
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