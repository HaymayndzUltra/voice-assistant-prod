#!/usr/bin/env python3
import sys
import os

# Add the project's main_pc_code directory to the Python path

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

# Remove redundant path addition
# MAIN_PC_CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# if MAIN_PC_CODE_DIR not in sys.path:
#     sys.path.insert(0, MAIN_PC_CODE_DIR)

# Now we can use absolute imports from the main_pc_code directory
from main_pc_code.src.core.base_agent import BaseAgent

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
import psutil  # Add missing import for health check
from datetime import datetime  # Add missing import for health check
from typing import Dict, Any, List, Optional, Tuple, Union
from main_pc_code.utils.config_loader import load_config
from main_pc_code.utils.service_discovery_client import discover_service, register_service, get_service_address
from main_pc_code.utils.env_loader import get_env
from main_pc_code.src.network.secure_zmq import is_secure_zmq_enabled, configure_secure_client, configure_secure_server

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
config = load_config()

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
COORDINATOR_PORT = int(config.get("port", 26002))
PROACTIVE_SUGGESTION_PORT = int(config.get("proactive_suggestion_port", 5591))

# Get bind address from environment variables with default to 0.0.0.0 for Docker compatibility
BIND_ADDRESS = get_env('BIND_ADDRESS', '0.0.0.0')

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
    def __init__(self, **kwargs):
        """Initialize the Coordinator Agent."""
        # Get port from kwargs or use default
        port = kwargs.get('port', COORDINATOR_PORT)
        name = kwargs.get('name', "CoordinatorAgent")
        # Set health_check_port before calling super().__init__
        kwargs['health_check_port'] = 26003
        super().__init__(name=name, port=port, health_check_port=26003)
        
        # Create ZMQ context and socket for the coordinator
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        
        # Apply secure ZMQ if enabled
        if SECURE_ZMQ:
            self.socket = configure_secure_server(self.socket)
            logger.info("Secure ZMQ enabled for CoordinatorAgent")
        
        # Bind to address using BIND_ADDRESS for Docker compatibility
        bind_address = f"tcp://{BIND_ADDRESS}:{self.port}"
        self.socket.bind(bind_address)
        logger.info(f"Coordinator socket bound to {bind_address}")
        
        # Discover and connect to required services using service discovery
        self.service_info = {}
        self._discover_services()
        
        # Create socket for proactive suggestions (with port fallback)
        self.suggestion_socket = self.context.socket(zmq.REP)
        self.suggestion_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.suggestion_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        
        # Apply secure ZMQ to suggestion socket if enabled
        if SECURE_ZMQ:
            self.suggestion_socket = configure_secure_server(self.suggestion_socket)

        # Attempt to bind to the preferred port; fall back if it's unavailable.
        self.suggestion_port = PROACTIVE_SUGGESTION_PORT
        try:
            suggestion_bind_address = f"tcp://{BIND_ADDRESS}:{self.suggestion_port}"
            self.suggestion_socket.bind(suggestion_bind_address)
            logger.info(f"Proactive suggestion socket bound to {suggestion_bind_address}")
        except zmq.ZMQError as e:
            logger.warning(
                f"Port {self.suggestion_port} already in use (error: {e}). "
                "Searching for the next available port."
            )
            self.suggestion_port = find_available_port(self.suggestion_port + 1)
            suggestion_bind_address = f"tcp://{BIND_ADDRESS}:{self.suggestion_port}"
            self.suggestion_socket.bind(suggestion_bind_address)
            logger.info(f"Proactive suggestion socket bound to fallback port {suggestion_bind_address}")
        
        # Register with service discovery (after suggestion_port is set)
        self._register_service()
        
        # Flag to control the agent
        self.running = True
        self.start_time = time.time()
        
        # Proactive assistance state
        self.last_interaction_time = time.time()
        self.pending_suggestions = []  # Initialize as empty list
        
        # Initialize memory connection
        self._init_memory_connection()
        
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

    def _register_service(self):
        """Register this agent with the service discovery system"""
        try:
            register_result = register_service(
                name="CoordinatorAgent",
                port=self.port,
                additional_info={
                    "suggestion_port": self.suggestion_port,
                    "capabilities": ["coordination", "memory_management", "proactive_assistance"],
                    "status": "running"
                }
            )
            if register_result and register_result.get("status") == "SUCCESS":
                logger.info("Successfully registered with service discovery")
            else:
                logger.warning(f"Service registration failed: {register_result.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error registering service: {e}")
    
    def _init_memory_connection(self):
        """Initialize connection to the MemoryOrchestrator"""
        try:
            # Try to discover MemoryOrchestrator via service discovery
            memory_address = get_service_address("MemoryOrchestrator")
            if memory_address:
                # Extract host and port from the address
                # Format is typically "tcp://host:port"
                parts = memory_address.split("://")[1].split(":")
                self.memory_host = parts[0]
                self.memory_port = int(parts[1])
                logger.info(f"Discovered MemoryOrchestrator at {self.memory_host}:{self.memory_port}")
            else:
                logger.warning("Failed to discover MemoryOrchestrator, will retry later")
                # Use default values if service discovery fails
                self.memory_host = 'localhost'
                self.memory_port = 5576
        except Exception as e:
            logger.error(f"Error initializing memory connection: {str(e)}")
            # Use default values if there's an error
            self.memory_host = 'localhost'
            self.memory_port = 5576
    
    def _get_memory_connection(self):
        """Get a connection to the MemoryOrchestrator"""
        try:
            # Try to get the latest service address
            memory_address = get_service_address("MemoryOrchestrator")
            if memory_address:
                # Create a new socket for the request
                socket = self.context.socket(zmq.REQ)
                socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
                socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
                
                # Apply secure ZMQ if enabled
                if SECURE_ZMQ:
                    socket = configure_secure_client(socket)
                    
                socket.connect(memory_address)
                logger.debug(f"Connected to MemoryOrchestrator at {memory_address}")
                return socket
            else:
                # Fall back to cached values
                socket = self.context.socket(zmq.REQ)
                socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
                socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
                
                # Apply secure ZMQ if enabled
                if SECURE_ZMQ:
                    socket = configure_secure_client(socket)
                    
                socket.connect(f"tcp://{self.memory_host}:{self.memory_port}")
                logger.debug(f"Connected to MemoryOrchestrator at {self.memory_host}:{self.memory_port} (fallback)")
                return socket
        except Exception as e:
            logger.error(f"Error getting memory connection: {str(e)}")
            return None
    
    def store_memory(self, memory_type: str, content: str, tags: Optional[List[str]] = None, priority: int = 5):
        """Store a memory using the MemoryOrchestrator"""
        try:
            socket = self._get_memory_connection()
            if not socket:
                logger.error("Failed to connect to MemoryOrchestrator")
                return None
            # Ensure tags is always a list
            if tags is None:
                tags = []
            request = {
                "action": "create",
                "request_id": f"coord-{int(time.time())}",
                "payload": {
                    "memory_type": memory_type,
                    "content": content,
                    "tags": tags,
                    "priority": priority
                }
            }
            
            socket.send_string(json.dumps(request))
            response = socket.recv_string()
            socket.close()
            
            result = json.loads(response)
            if result.get("status") == "success":
                logger.info(f"Memory stored successfully with ID: {result.get('data', {}).get('memory_id')}")
                return result.get("data", {}).get("memory_id")
            else:
                logger.error(f"Failed to store memory: {result.get('error', {}).get('message')}")
                return None
        except Exception as e:
            logger.error(f"Error storing memory: {str(e)}")
            return None
    
    def retrieve_memory(self, memory_id: str):
        """Retrieve a memory by ID using the MemoryOrchestrator"""
        try:
            socket = self._get_memory_connection()
            if not socket:
                logger.error("Failed to connect to MemoryOrchestrator")
                return None
            
            request = {
                "action": "read",
                "request_id": f"coord-{int(time.time())}",
                "payload": {
                    "memory_id": memory_id
                }
            }
            
            socket.send_string(json.dumps(request))
            response = socket.recv_string()
            socket.close()
            
            result = json.loads(response)
            if result.get("status") == "success":
                return result.get("data", {}).get("memory")
            else:
                logger.error(f"Failed to retrieve memory: {result.get('error', {}).get('message')}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving memory: {str(e)}")
            return None
    
    def _discover_services(self):
        """Discover required services using service discovery"""
        try:
            # Discover all required services
            required_services = [
                "TaskRouter", "TTSConnector", "HealthMonitor", 
                "VisionCaptureAgent", "VisionProcessingAgent", "MemoryOrchestrator"
            ]
            
            for service_name in required_services:
                service_info = discover_service(service_name)
                if service_info and isinstance(service_info, dict) and service_info.get("status") == "SUCCESS":
                    service_payload = service_info.get("payload")
                    if service_payload and isinstance(service_payload, dict):
                        host = service_payload.get("ip")
                        port = service_payload.get("port")
                        if host is not None and port is not None:
                            self.service_info[service_name] = {
                                "host": host,
                                "port": port
                            }
                            logger.info(f"Discovered {service_name} at {host}:{port}")
                        else:
                            logger.warning(f"Service payload for {service_name} missing host or port.")
                    else:
                        logger.warning(f"Service payload for {service_name} is not available or not a dict.")
                else:
                    logger.warning(f"Failed to discover {service_name}, will retry later")
                    
            # Also try to discover PC2 services
            pc2_services = ["PC2Agent", "VisionProcessingAgent"]
            for service_name in pc2_services:
                service_info = discover_service(service_name)
                if service_info and isinstance(service_info, dict) and service_info.get("status") == "SUCCESS":
                    service_payload = service_info.get("payload")
                    if service_payload and isinstance(service_payload, dict):
                        host = service_payload.get("ip")
                        port = service_payload.get("port")
                        if host is not None and port is not None:
                            self.service_info[service_name] = {
                                "host": host,
                                "port": port
                            }
                            logger.info(f"Discovered PC2 service {service_name} at {host}:{port}")
                        else:
                            logger.warning(f"PC2 service payload for {service_name} missing host or port.")
                    else:
                        logger.warning(f"PC2 service payload for {service_name} is not available or not a dict.")
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
        try:
            # Get service address using service discovery
            service_address = get_service_address(service_name)
            if service_address:
                # Create a new socket for the request
                socket = self.context.socket(zmq.REQ)
                socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
                socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
                # Apply secure ZMQ if enabled
                if SECURE_ZMQ:
                    socket = configure_secure_client(socket)
                socket.connect(service_address)
                logger.debug(f"Connected to {service_name} at {service_address}")
                return socket
            elif service_name in self.service_info:
                # Fall back to cached service info
                service_info = self.service_info.get(service_name)
                if service_info is not None and isinstance(service_info, dict):
                    host = service_info.get("host")
                    port = service_info.get("port")
                    if host is not None and port is not None:
                        # Create a new socket for the request
                        socket = self.context.socket(zmq.REQ)
                        socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
                        socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
                        # Apply secure ZMQ if enabled
                        if SECURE_ZMQ:
                            socket = configure_secure_client(socket)
                        socket.connect(f"tcp://{host}:{port}")
                        logger.debug(f"Connected to {service_name} at {host}:{port} (fallback)")
                        return socket
                    else:
                        logger.error(f"Cached service_info for {service_name} is missing host or port.")
                        return None
                else:
                    logger.error(f"Cached service_info for {service_name} is not available or not a dict.")
                    return None
            else:
                logger.error(f"Failed to discover {service_name}")
                return None
        except Exception as e:
            logger.error(f"Error getting service connection for {service_name}: {str(e)}")
            return None

    def run(self):
        """
        Run the agent. This method is called by the health checker.
        Initialize the health check socket and thread, then call start().
        """
        try:
            # Add debug logging
            print("CoordinatorAgent.run() called")
            logger.info("CoordinatorAgent.run() called")
            
            # Call start() to handle requests
            self.start()
        except KeyboardInterrupt:
            logger.info(f"{self.name} interrupted by user")
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            self.stop()
            
    def start(self):
        """Start the Coordinator Agent."""
        print("Starting CoordinatorAgent...")
        logger.info("Starting CoordinatorAgent")
        
        try:
            # Add debug logging
            print("CoordinatorAgent.start() called - about to handle requests")
            logger.info("CoordinatorAgent.start() called - about to handle requests")
            
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
            # Validate suggestion has required content
            if not suggestion or 'content' not in suggestion:
                logger.error(f"Invalid suggestion format: missing 'content' key: {suggestion}")
                return
                
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
            import traceback
            logger.error(traceback.format_exc())

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
            
            # Store the interaction in memory
            self.store_memory(
                memory_type="user_interaction",
                content=json.dumps({
                    "text": text,
                    "intent": intent,
                    "entities": entities,
                    "confidence": confidence
                }),
                tags=["interaction", "user_input", intent],
                priority=7
            )
            
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
                
                # Store the response in memory
                self.store_memory(
                    memory_type="system_response",
                    content=json.dumps({
                        "text": response_text,
                        "source": "PC2Agent",
                        "intent": intent
                    }),
                    tags=["interaction", "system_response", "pc2"],
                    priority=6
                )
                
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
                
                # Store the response in memory
                self.store_memory(
                    memory_type="system_response",
                    content=json.dumps({
                        "text": response_text,
                        "source": "TaskRouter",
                        "intent": intent
                    }),
                    tags=["interaction", "system_response", "task_router"],
                    priority=6
                )
            
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
        """Perform a health check on this agent and all connected agents."""
        # Get own detailed health status
        my_health = self.health_check()

        # Aggregate dependency health checks (legacy logic preserved)
        dependency_health = {}
        # List of dependencies to check
        dependencies = [
            ("TaskRouter", "task_router"),
            ("TTSConnector", "tts"),
            ("PC2Agent", "pc2"),
            ("HealthMonitor", "health_monitor"),
            ("VisionCaptureAgent", "vision_capture"),
            ("cessingAgent", "vision_processing")
        ]
        for service_name, key in dependencies:
            try:
                socket = self._get_service_connection(service_name)
                if not socket:
                    dependency_health[key] = "error"
                    continue
                health_request = {"type": "health_check"}
                socket.send_string(json.dumps(health_request))
                response_str = socket.recv_string()
                socket.close()
                response = json.loads(response_str)
                if response.get("status") in ("ok", "healthy"):
                    dependency_health[key] = response.get("status")
                else:
                    dependency_health[key] = "error"
            except Exception as e:
                dependency_health[key] = f"error: {str(e)}"

        my_health['dependency_health_status'] = dependency_health
        return my_health


    def health_check(self):
        return {"status": "healthy", "agent_name": self.name}

    def _get_health_status(self):
        try:
            return self.health_check()
        except Exception as e:
            import traceback
            logger.error(f"Exception in _get_health_status: {e}\n{traceback.format_exc()}")
            return {
                "status": "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "error": f"Exception in _get_health_status: {str(e)}"
            }

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = CoordinatorAgent()
        agent.start()  # Call start() instead of run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()