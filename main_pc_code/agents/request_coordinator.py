#!/usr/bin/env python3
import sys
import os
import json
import time
import logging
import threading
import argparse
import zmq
from common.pools.zmq_pool import get_sub_socket
from main_pc_code.utils.network import get_host
import psutil
import heapq
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Union
import pickle
from common.config_manager import load_unified_config


# Import path manager for containerization-friendly paths
import sys
import os
from pathlib import Path
from common.utils.path_manager import PathManager

# --- Path Setup ---
# Removed 
# --- Imports from Project ---
from common.core.base_agent import BaseAgent
from utils.service_discovery_client import get_service_address, register_service
from utils.env_loader import get_env
# from src.network.secure_zmq import is_secure_zmq_enabled, configure_secure_client, configure_secure_server
from common.utils.env_standardizer import get_env
from main_pc_code.agents.error_publisher import ErrorPublisher
from common.utils.data_models import (
    TaskDefinition, ErrorSeverity
)
from pydantic import BaseModel, Field

def is_secure_zmq_enabled() -> bool:
    """Simple placeholder for secure ZMQ check"""
    return False

# --- Configuration Constants ---
config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))


# --- Standardized Request/Response Models ---
class TextRequest(BaseModel):
    """Standardized model for text-based requests"""
    type: str = Field("text", description="Request type identifier")
    data: str = Field(..., description="Text content of the request")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context for the request")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about the request")
    user_id: Optional[str] = Field(default=None, description="ID of the user making the request")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the request was created")

class AudioRequest(BaseModel):
    """Standardized model for audio-based requests"""
    type: str = Field("audio", description="Request type identifier")
    audio_data: Union[str, bytes] = Field(..., description="Audio data (base64 encoded or binary)")
    format: str = Field(default="wav", description="Audio format (e.g., wav, mp3)")
    sample_rate: int = Field(default=16000, description="Audio sample rate")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context for the request")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about the request")
    user_id: Optional[str] = Field(default=None, description="ID of the user making the request")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the request was created")

class VisionRequest(BaseModel):
    """Standardized model for vision-based requests"""
    type: str = Field("vision", description="Request type identifier")
    image_data: Union[str, bytes] = Field(..., description="Image data (base64 encoded or binary)")
    format: str = Field(default="jpg", description="Image format (e.g., jpg, png)")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context for the request")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about the request")
    user_id: Optional[str] = Field(default=None, description="ID of the user making the request")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the request was created")

class AgentResponse(BaseModel):
    """Standardized model for agent responses"""
    status: str = Field(..., description="Status of the response (success, error, etc.)")
    message: Optional[str] = Field(default=None, description="Response message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Response data payload")
    speak: Optional[str] = Field(default=None, description="Text to be spoken")
    memory_entry: Optional[Dict[str, Any]] = Field(default=None, description="Data to be stored in memory")
    error: Optional[str] = Field(default=None, description="Error message if status is error")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about the response")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the response was created")

# --- Logging Setup ---
from common.utils.log_setup import configure_logging
logger = configure_logging(__name__, log_to_file=True)

# --- Constants with Port Registry Integration ---
# Port registry removed - using environment variables with startup_config.yaml defaults
DEFAULT_PORT = int(os.getenv("REQUEST_COORDINATOR_PORT", 26002))
    
PROACTIVE_SUGGESTION_PORT = 5591
INTERRUPT_PORT = 5576
ZMQ_REQUEST_TIMEOUT = 5000
BIND_ADDRESS = get_env('BIND_ADDRESS', '0.0.0.0')
SECURE_ZMQ = is_secure_zmq_enabled()

# === Circuit Breaker Class ===
class CircuitBreaker:
    CLOSED = 'closed'
    OPEN = 'open'
    HALF_OPEN = 'half_open'

    def __init__(self, name: str, failure_threshold: int = 3, reset_timeout: int = 30, half_open_timeout: int = 5):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_timeout = half_open_timeout
        self.state = self.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self._lock = threading.Lock()

    def record_success(self):
        with self._lock:
            if self.state == self.HALF_OPEN:
                logger.info(f"Circuit breaker for {self.name} reset to CLOSED.")
                self.state = self.CLOSED
            self.failure_count = 0

    def record_failure(self):
        with self._lock:
            self.last_failure_time = time.time()
            if self.state == self.HALF_OPEN:
                logger.warning(f"Circuit breaker for {self.name} remains OPEN after failed test.")
                self.state = self.OPEN
            elif self.state == self.CLOSED:
                self.failure_count += 1
                if self.failure_count >= self.failure_threshold:
                    logger.warning(f"Circuit breaker for {self.name} tripped to OPEN.")
                    self.state = self.OPEN

    def allow_request(self) -> bool:
        with self._lock:
            if self.state == self.CLOSED: return True
            if self.state == self.OPEN:
                if time.time() - self.last_failure_time >= self.reset_timeout:
                    logger.info(f"Circuit breaker for {self.name} transitioning to HALF_OPEN.")
                    self.state = self.HALF_OPEN
                    return True
                return False
            if self.state == self.HALF_OPEN:
                return time.time() - self.last_failure_time >= self.half_open_timeout
            return False

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {'name': self.name, 'state': self.state, 'failure_count': self.failure_count}

# === Main Agent Class ===
class RequestCoordinator(BaseAgent):
    """
    RequestCoordinator: Main PC agent for coordinating requests.
    Now reports errors via the distributed Error Bus (ZMQ PUB/SUB, topic 'ERROR:') to the SystemHealthManager on PC2.
    """
    def __init__(self, **kwargs):
        port = kwargs.get('port', DEFAULT_PORT)
        super().__init__(name="RequestCoordinator", port=port, health_check_port=port + 1)

        self.context = zmq.Context()  # ZMQ context for socket creation
        self._init_zmq_sockets()

        # Modern error reporting now handled by BaseAgent's UnifiedErrorHandler

        self.running = True
        self.start_time = time.time()
        self.interrupt_flag = threading.Event()

        # Get parameters from startup config
        params = kwargs.get('params', {})
        self.enable_dynamic_prioritization = params.get('enable_dynamic_prioritization', False)
        self.queue_max_size = params.get('queue_max_size', 100)
        self.default_task_timeout = params.get('default_task_timeout', ZMQ_REQUEST_TIMEOUT)
        
        self.task_queue = []
        self.queue_lock = threading.Lock()
        
        self.circuit_breakers = {}
        self._init_circuit_breakers()
        
        self.last_interaction_time = time.time()
        self.inactivity_threshold = 300
        self.pending_suggestions = []

        # --- Metrics and Monitoring ---
        self.metrics = {
            "requests_total": 0,
            "requests_by_type": {"text": 0, "audio": 0, "vision": 0},
            "success": 0,
            "failure": 0,
            "response_times": {"text": [], "audio": [], "vision": []},
            "queue_sizes": [],
            "last_updated": datetime.now().isoformat()
        }
        self.metrics_lock = threading.Lock()
        self.metrics_file = str(PathManager.get_logs_dir() / "request_coordinator_metrics.json")
        self.last_metrics_log = time.time()
        self.last_metrics_save = time.time()
        self._load_metrics()
        self.metrics_thread = threading.Thread(target=self._metrics_reporting_loop, daemon=True)
        self.metrics_thread.start()

        self._register_service()
        self._start_threads()
        logger.info(f"RequestCoordinator initialized, listening on tcp://{BIND_ADDRESS}:{self.port}")
        if self.enable_dynamic_prioritization:
            logger.info("Dynamic prioritization enabled")

    def _init_zmq_sockets(self):
        self.main_socket = self.context.socket(zmq.REP)
        if SECURE_ZMQ: configure_secure_server(self.main_socket)
        self.main_socket.bind(f"tcp://{BIND_ADDRESS}:{self.port}")

        self.suggestion_socket = self.context.socket(zmq.REP)
        if SECURE_ZMQ: configure_secure_server(self.suggestion_socket)
        self.suggestion_port = PROACTIVE_SUGGESTION_PORT
        self.suggestion_socket.bind(f"tcp://{BIND_ADDRESS}:{self.suggestion_port}")

        self.interrupt_socket = self.context.socket(zmq.SUB)
        # Try to discover the InterruptService using service discovery
        interrupt_address = get_service_address('StreamingInterruptHandler')
        if interrupt_address:
            self.interrupt_socket.connect(interrupt_address)
            logger.info(f"Connected to InterruptService at {interrupt_address}")
        else:
            # Fall back to default address if service discovery fails
            interrupt_host = get_host("INTERRUPT_HOST", "zmq.interrupt_host")
            fallback_address = f"tcp://{interrupt_host}:{INTERRUPT_PORT}"
            self.interrupt_socket.connect(fallback_address)
            logger.warning(f"InterruptService not found in discovery. Falling back to default address: {fallback_address}")
        
        # Subscribe to all messages
        self.interrupt_socket.setsockopt(zmq.SUBSCRIBE, b"")

        # Connect to all required downstream services
        self.memory_socket = self._connect_to_service("MemoryOrchestrator")
        self.tts_socket = self._connect_to_service("StreamingTTSAgent")
        self.cot_socket = self._connect_to_service("ChainOfThoughtAgent")
        self.got_tot_socket = self._connect_to_service("GOT_TOTAgent")

    def _connect_to_service(self, service_name: str) -> Optional[zmq.Socket]:
        try:
            service_address = get_service_address(service_name)
            if service_address:
                socket = self.context.socket(zmq.REQ)
                if SECURE_ZMQ: configure_secure_client(socket)
                socket.connect(service_address)
                logger.info(f"Successfully connected to {service_name} at {service_address}")
                return socket
            else:
                logger.error(f"Failed to discover {service_name}. Socket will be None.")
                return None
        except Exception as e:
            logger.error(f"Error connecting to {service_name}: {e}")
            return None

    def _init_circuit_breakers(self):
        services = ['cot', 'got_tot', 'memory', 'tts']
        for service in services:
            self.circuit_breakers[service] = CircuitBreaker(name=service)

    def _listen_for_language_analysis(self):
        """Listen for language analysis results from StreamingLanguageAnalyzer"""
        try:
            # Create subscription socket
            context = None  # Using pool
            socket = get_sub_socket(endpoint).socket
            if SECURE_ZMQ:
                socket = configure_secure_client(socket)
                
            # Try to get the StreamingLanguageAnalyzer address from service discovery
            analyzer_address = get_service_address("StreamingLanguageAnalyzer")
            if not analyzer_address:
                # Fall back to configured port
                analyzer_host = get_host("SLA_HOST", "zmq.streaming_language_analyzer_host")
                analyzer_address = f"tcp://{analyzer_host}:5577"  # Default port for StreamingLanguageAnalyzer
                
            socket.connect(analyzer_address)
            socket.setsockopt(zmq.SUBSCRIBE, b"")
            logger.info(f"Connected to StreamingLanguageAnalyzer at {analyzer_address}")
            
            while self.running:
                try:
                    # Non-blocking receive with timeout
                    if socket.poll(timeout=100, flags=zmq.POLLIN):
                        data_raw = socket.recv()
                        data = pickle.loads(data_raw)
                        
                        # Only process language_analysis messages
                        if data.get('type') == 'language_analysis':
                            logger.info(f"Received language analysis: {data.get('detected_language')} - {data.get('analysis')}")
                            
                            # Check if translated text is available and use it if present
                            text = data.get('translated_text') if data.get('translated_text') else data.get('transcription')
                            
                            # Create a TextRequest from the analysis
                            request = TextRequest(
                                type="text",
                                data=text,
                                context={
                                    "original_text": data.get('transcription'),
                                    "language_analysis": data.get('analysis'),
                                    "detected_language": data.get('detected_language')
                                },
                                metadata={
                                    "source": "speech_recognition",
                                    "was_translated": data.get('translated_text') is not None,
                                    "translation_status": data.get('translation_status'),
                                    "original_language": data.get('detected_language')
                                }
                            )
                            
                            # Process the text request
                            self._process_text(request)
                except zmq.Again:
                    # No messages available, continue loop
                    continue
                except Exception as e:
                    logger.error(f"Error processing language analysis: {e}", exc_info=True)
                    
                # Small sleep to prevent CPU spinning
                time.sleep(0.01)
                
        except Exception as e:
            logger.error(f"Error in language analysis listener: {e}", exc_info=True)
        finally:
            # Clean up socket resources
            try:
                if socket:
                    socket.close()
                if context:
                    context.term()
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up language analysis socket: {cleanup_error}")
                
    def _start_threads(self):
        """Start all required background threads"""
        # Start the dispatch thread
        self.dispatch_thread = threading.Thread(target=self._dispatch_loop, daemon=True)
        self.dispatch_thread.start()
        
        # Start the metrics reporting thread
        self.metrics_thread = threading.Thread(target=self._metrics_reporting_loop, daemon=True)
        self.metrics_thread.start()
        
        # Start inactivity check thread
        self.inactivity_thread = threading.Thread(target=self._check_inactivity, daemon=True)
        self.inactivity_thread.start()
        
        # Start proactive suggestions thread
        self.proactive_thread = threading.Thread(target=self._handle_proactive_suggestions, daemon=True)
        self.proactive_thread.start()
        
        # Start language analysis listener thread
        self.language_analysis_thread = threading.Thread(target=self._listen_for_language_analysis, daemon=True)
        self.language_analysis_thread.start()
        
        logger.info("All background threads started")

    def _register_service(self):
        """Register this agent with the service discovery system."""
        register_service(
            name=self.name, 
            port=self.port,
            additional_info={"suggestion_port": self.suggestion_port}
        )

    def _load_metrics(self):
        try:
            metrics_path = Path(self.metrics_file)
            if metrics_path.exists():
                with open(metrics_path, 'r') as f:
                    saved_metrics = json.load(f)
                    with self.metrics_lock:
                        self.metrics.update(saved_metrics)
        except Exception as e:
            logger.warning(f"Failed to load metrics: {e}")

    def _save_metrics(self):
        try:
            metrics_path = Path(self.metrics_file)
            os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
            with self.metrics_lock:
                self.metrics["last_updated"] = datetime.now().isoformat()
                metrics_to_save = dict(self.metrics)
                # Only save last 100 response times and queue sizes
                for k in ["response_times", "queue_sizes"]:
                    if k in metrics_to_save:
                        for t in metrics_to_save["response_times"]:
                            metrics_to_save["response_times"][t] = metrics_to_save["response_times"][t][-100:]
                        metrics_to_save["queue_sizes"] = metrics_to_save["queue_sizes"][-100:]
                with open(metrics_path, 'w') as f:
                    json.dump(metrics_to_save, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save metrics: {e}")

    def _metrics_reporting_loop(self):
        while True:
            current_time = time.time()
            if current_time - self.last_metrics_log >= 60:
                self._log_metrics()
                self.last_metrics_log = current_time
            if current_time - self.last_metrics_save >= 300:
                self._save_metrics()
                self.last_metrics_save = current_time
            time.sleep(5)

    def _log_metrics(self):
        with self.metrics_lock:
            logger.info(f"[Metrics] Total Requests: {self.metrics['requests_total']}, Success: {self.metrics['success']}, Failure: {self.metrics['failure']}")
            logger.info(f"[Metrics] Requests by Type: {self.metrics['requests_by_type']}")
            avg_queue = sum(self.metrics['queue_sizes']) / len(self.metrics['queue_sizes']) if self.metrics['queue_sizes'] else 0
            logger.info(f"[Metrics] Avg Queue Size: {avg_queue:.2f}")
            for t in ["text", "audio", "vision"]:
                times = self.metrics['response_times'][t]
                avg_time = sum(times) / len(times) if times else 0
                logger.info(f"[Metrics] Avg Response Time ({t}): {avg_time:.2f}s")

    def _handle_requests(self):
        """
        Main request handling loop - refactored for modularity and better maintainability.
        Receives requests, validates them, and routes them to appropriate handlers.
        """
        while self.running:
            try:
                # Step 1: Receive and validate message
                message_raw = self._receive_and_validate_message()
                if message_raw is None:
                    continue
                
                # Step 2: Process request based on type
                request_type = message_raw.get('type')
                start_time = time.time()
                with self.metrics_lock:
                    self.metrics["requests_total"] += 1
                    if request_type in self.metrics["requests_by_type"]:
                        self.metrics["requests_by_type"][request_type] += 1
                    self.metrics["queue_sizes"].append(len(self.task_queue))
                response = self._route_request_by_type(request_type, message_raw)
                elapsed = time.time() - start_time
                with self.metrics_lock:
                    if request_type in self.metrics["response_times"]:
                        self.metrics["response_times"][request_type].append(elapsed)
                
                # Step 3: Send response
                self.main_socket.send_json(response.model_dump())
                
            except Exception as e:
                logger.error(f"Error in _handle_requests: {e}", exc_info=True)
                if not self.main_socket.closed:
                    error_response = AgentResponse(
                        status="error",
                        message=str(e),
                        error=str(e)
                    )
                    self.main_socket.send_json(error_response.model_dump())
    
    def _receive_and_validate_message(self):
        """
        Receives and validates incoming messages.
        Returns validated message or None if validation fails.
        """
        try:
            message_raw = self.main_socket.recv_json()
            self.last_interaction_time = time.time()
            
            # Ensure message_raw is a dictionary
            if not isinstance(message_raw, dict):
                logger.error(f"Received non-dictionary message: {message_raw}")
                error_response = AgentResponse(
                    status="error",
                    message="Invalid message format: expected dictionary",
                    error="Invalid message format"
                )
                self.main_socket.send_json(error_response.model_dump())
                return None
            
            return message_raw
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            return None
    
    def _route_request_by_type(self, request_type, message_raw):
        """
        Routes requests to appropriate handlers based on request type.
        """
        if request_type == 'text':
            request = TextRequest.model_validate(message_raw)
            return self._process_text(request)
        elif request_type == 'audio':
            request = AudioRequest.model_validate(message_raw)
            return self._process_audio(request)
        elif request_type == 'vision':
            request = VisionRequest.model_validate(message_raw)
            return self._process_vision(request)
        else:
            return AgentResponse(
                status="error",
                message=f"Unknown request type: {request_type}"
            )

    def _calculate_priority(self, task_type, request):
        """
        Dynamically calculates task priority based on multiple factors:
        - Task type (base priority)
        - User profile (if available)
        - Urgency level (from request metadata)
        - System load
        
        Returns an integer priority value (lower is higher priority)
        """
        # Base priority by task type
        base_priority = {
            'audio_processing': 1,  # Highest priority
            'text_processing': 2,
            'vision_processing': 3,
            'background_task': 5    # Lowest priority
        }.get(task_type, 3)  # Default priority
        
        # Adjust for user profile if available
        user_id = request.user_id
        user_priority_adjustment = 0
        if user_id:
            # In a real implementation, this would query a user profile service
            # For now, we'll use a simple dictionary as placeholder
            user_profiles = {
                "admin": -2,        # Higher priority (lower number)
                "premium": -1,
                "standard": 0,
                "guest": 1          # Lower priority (higher number)
            }
            # Get user type from metadata or default to standard
            user_type = request.metadata.get("user_type", "standard")
            user_priority_adjustment = user_profiles.get(user_type, 0)
        
        # Adjust for urgency level from metadata
        urgency = request.metadata.get("urgency", "normal")
        urgency_adjustment = {
            "critical": -3,
            "high": -1,
            "normal": 0,
            "low": 1
        }.get(urgency, 0)
        
        # System load adjustment (simplified)
        # In a real implementation, this would consider CPU, memory, queue length, etc.
        system_load_adjustment = 0
        if len(self.task_queue) > self.queue_max_size * 0.8:  # If queue is 80%+ full
            system_load_adjustment = 1  # Lower priority for all tasks
        
        # Calculate final priority (lower is higher priority)
        final_priority = base_priority + user_priority_adjustment + urgency_adjustment + system_load_adjustment
        
        # Ensure priority is within reasonable bounds
        return max(1, min(10, final_priority))

    def _process_text(self, request: TextRequest) -> AgentResponse:
        """Process text requests with dynamic prioritization."""
        logger.info(f"Queueing text request: {request.data[:50]}...")
        
        # Create standardized task using TaskDefinition
        task = TaskDefinition(
            task_id=f"task_{time.time()}",
            agent_id=self.name,
            task_type='text_processing',
            priority=self._calculate_priority('text_processing', request),
            parameters={"request": request.model_dump()},
            created_at=datetime.now()
        )
        
        self.add_task_to_queue(priority=task.priority, task=task)
        return AgentResponse(
            status="success",
            message="Text request queued"
        )

    def _process_audio(self, request: AudioRequest) -> AgentResponse:
        """Process audio requests with dynamic prioritization."""
        logger.info("Queueing audio request...")
        
        # Create standardized task using TaskDefinition
        task = TaskDefinition(
            task_id=f"task_{time.time()}",
            agent_id=self.name,
            task_type='audio_processing',
            priority=self._calculate_priority('audio_processing', request),
            parameters={"request": request.model_dump()},
            created_at=datetime.now()
        )
        
        self.add_task_to_queue(priority=task.priority, task=task)
        return AgentResponse(
            status="success",
            message="Audio request queued"
        )

    def _process_vision(self, request: VisionRequest) -> AgentResponse:
        """Process vision requests with dynamic prioritization."""
        logger.info("Queueing vision request...")
        
        # Create standardized task using TaskDefinition
        task = TaskDefinition(
            task_id=f"task_{time.time()}",
            agent_id=self.name,
            task_type='vision_processing',
            priority=self._calculate_priority('vision_processing', request),
            parameters={"request": request.model_dump()},
            created_at=datetime.now()
        )
        
        self.add_task_to_queue(priority=task.priority, task=task)
        return AgentResponse(
            status="success",
            message="Vision request queued"
        )

    def add_task_to_queue(self, priority: int, task: TaskDefinition):
        with self.queue_lock:
            if len(self.task_queue) >= self.queue_max_size:
                logger.warning("Task queue full. Rejecting new task.")
                return
            heapq.heappush(self.task_queue, (priority, time.time(), task))
            logger.info(f"Task {task.task_id} added to queue. Size: {len(self.task_queue)}")

    def _dispatch_loop(self):
        while self.running:
            if self.interrupt_flag.is_set():
                time.sleep(0.1)
                continue
            
            task_item = None
            with self.queue_lock:
                if self.task_queue:
                    task_item = heapq.heappop(self.task_queue)
            
            if task_item:
                _priority, _timestamp, task = task_item
                self._process_task(task)
            else:
                time.sleep(0.05)

    def _process_task(self, task: TaskDefinition):
        task_type = task.task_type
        logger.info(f"Dispatching task {task.task_id} of type {task_type}")

        # Expanded routing logic
        if 'audio' in task_type or 'vision' in task_type:
            target_service, target_socket = 'got_tot', self.got_tot_socket
        else:
            target_service, target_socket = 'cot', self.cot_socket

        breaker = self.circuit_breakers.get(target_service)
        if not breaker or not breaker.allow_request():
            logger.warning(f"Circuit for {target_service} is open. Dropping task {task.task_id}.")
            return

        try:
            if not target_socket:
                raise ConnectionError(f"Socket for {target_service} is not available.")

            # Use BaseAgent's standardized request method instead of direct socket operations
            response_dict = self.send_request_to_agent(
                agent_name=target_service,
                request=task.model_dump(),
                timeout=ZMQ_REQUEST_TIMEOUT
            )
            
            # Convert the response dictionary to a Pydantic model
            response = AgentResponse.model_validate(response_dict)
            
            self._handle_task_response(response)
            breaker.record_success()
        except Exception as e:
            # Use Error Bus for error reporting
            error_data = {
                "error_type": "task_processing_error",
                "message": f"Failed to process task {task.task_id}: {str(e)}",
                "severity": str(ErrorSeverity.ERROR),
                "context": {"task_id": task.task_id, "service": target_service, "task_type": task_type}
            }
            self.report_error(error_data)
            logger.error(f"Failed to process task {task.task_id} with {target_service}: {e}")
            if breaker: breaker.record_failure()

    def _handle_task_response(self, response: AgentResponse):
        logger.info(f"Handling response: {response.status}")
        with self.metrics_lock:
            if response.status == "success":
                self.metrics["success"] += 1
            else:
                self.metrics["failure"] += 1
        
        # Handle TTS if needed
        if response.speak and self.tts_socket:
            try:
                self.send_request_to_agent(
                    agent_name="StreamingTTSAgent",
                    request={"text": response.speak}
                )
            except Exception as e:
                error_data = {
                    "error_type": "tts_request_error",
                    "message": f"Error sending TTS request: {str(e)}",
                    "severity": str(ErrorSeverity.WARNING)
                }
                self.report_error(error_data)
                
        # Handle memory storage if needed
        if response.memory_entry and self.memory_socket:
            try:
                self.send_request_to_agent(
                    agent_name="MemoryOrchestrator",
                    request={"action": "save", "data": response.memory_entry}
                )
            except Exception as e:
                error_data = {
                    "error_type": "memory_storage_error",
                    "message": f"Error sending memory request: {str(e)}",
                    "severity": str(ErrorSeverity.WARNING)
                }
                self.report_error(error_data)

    def _listen_for_interrupts(self):
        while self.running:
            try:
                if self.interrupt_socket.poll(100):
                    self.interrupt_socket.recv()
                    logger.warning("Interrupt signal received! Clearing task queue.")
                    self.interrupt_flag.set()
                    with self.queue_lock: self.task_queue.clear()
                    time.sleep(5)
                    self.interrupt_flag.clear()
                    logger.info("Interrupt flag cleared. Resuming operations.")
            except Exception as e:
                logger.error(f"Error in interrupt listener: {e}")

    def _check_inactivity(self):
        while self.running:
            if time.time() - self.last_interaction_time > self.inactivity_threshold:
                logger.info("Inactivity detected, triggering proactive suggestion.")
                self.pending_suggestions.append("Paalala: Huwag kalimutang i-save ang iyong trabaho.")
                self.last_interaction_time = time.time()
            time.sleep(30)

    def _handle_proactive_suggestions(self):
        while self.running:
            try:
                msg = self.suggestion_socket.recv_string()
                if msg == "get_suggestion" and self.pending_suggestions:
                    self.suggestion_socket.send_json({"suggestion": self.pending_suggestions.pop(0)})
                else:
                    self.suggestion_socket.send_json({"suggestion": None})
            except Exception as e:
                logger.error(f"Error in suggestion handler: {e}")

    def health_check(self):
        # Deep health check with dependency pings
        base = {
            "status": "healthy" if self.running else "stopped",
            "uptime": time.time() - self.start_time,
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "queue_size": len(self.task_queue),
            "circuit_breakers": {n: cb.get_status() for n, cb in self.circuit_breakers.items()}
        }

        # Probe critical downstream dependencies
        dependencies = {}
        for dep in ["ModelOrchestrator", "MemoryClient"]:
            try:
                resp = self.send_request_to_agent(dep, {"action": "health"}, timeout=2000, retries=1)
                dependencies[dep] = resp.get("status", "unknown") if isinstance(resp, dict) else "no_response"
            except Exception:
                dependencies[dep] = "unreachable"

        base["dependencies"] = dependencies

        if any(v != "ok" and v != "healthy" and v != "success" for v in dependencies.values()):
            base["status"] = "degraded"

        with self.metrics_lock:
            base["metrics"] = {
                "requests_total": self.metrics["requests_total"],
                "requests_by_type": self.metrics["requests_by_type"],
                "success": self.metrics["success"],
                "failure": self.metrics["failure"],
                "avg_queue_size": sum(self.metrics["queue_sizes"]) / len(self.metrics["queue_sizes"]) if self.metrics["queue_sizes"] else 0,
                "avg_response_time": {
                    t: (sum(self.metrics["response_times"][t]) / len(self.metrics["response_times"][t]) if self.metrics["response_times"][t] else 0)
                    for t in ["text", "audio", "vision"]
                }
            }
        return base

    def stop(self):
        self.running = False
        logger.info("Stopping RequestCoordinator...")
        for sock in [self.main_socket, self.suggestion_socket, self.interrupt_socket, self.memory_socket, self.tts_socket, self.cot_socket, self.got_tot_socket]:
            if sock and not sock.closed:
                sock.close()
        # TODO-FIXME – removed stray 'self.' (O3 Pro Max fix)
        logger.info("RequestCoordinator stopped.")

    def run(self):
        logger.info("RequestCoordinator is running...")
        try:
            while self.running:
                try:
                    # Poll for incoming ZMQ messages
                    if self.main_socket.poll(1000):  # 1 second timeout
                        message = self.main_socket.recv_json(zmq.NOBLOCK)
                        logger.info(f"Received request: {message}")
                        
                        # Process the request and send response
                        response = self._process_request(message)
                        self.main_socket.send_json(response)
                        logger.info(f"Sent response: {response}")
                    
                except zmq.Again:
                    # Timeout - continue polling
                    continue
                except Exception as e:
                    logger.error(f"Error processing request: {e}")
                    # Send error response if possible
                    try:
                        error_response = {"status": "error", "message": str(e)}
                        self.main_socket.send_json(error_response)
                    except:
                        pass
                        
        except KeyboardInterrupt:
            self.stop()

    def _process_request(self, message):
        """Process incoming request and return response"""
        try:
            action = message.get('action', 'unknown')
            
            if action == 'ping':
                return {"status": "success", "message": "pong", "service": "RequestCoordinator"}
            elif action == 'generate':
                # Mock response for now - would integrate with MMS
                return {
                    "status": "success", 
                    "action": action,
                    "prompt": message.get('prompt', ''),
                    "response": "Mock generation response",
                    "service": "RequestCoordinator"
                }
            else:
                return {"status": "error", "message": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # report_error() method now inherited from BaseAgent (UnifiedErrorHandler)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Request Coordinator Agent')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Port to bind to')
    args = parser.parse_args()
    
    agent = RequestCoordinator(port=args.port)
    agent.run()
    def _get_health_status(self) -> dict:
        """Return health status information."""
        # Get base health status from parent class
        base_status = super()._get_health_status()
        
        # Add agent-specific health information
        base_status.update({
            'service': self.__class__.__name__,
            'uptime_seconds': int(time.time() - self.start_time) if hasattr(self, 'start_time') else 0,
            'request_count': self.request_count if hasattr(self, 'request_count') else 0,
            'status': 'HEALTHY'
        })
        
        return base_status


if __name__ == "__main__":
    agent = None
    try:
        agent = RequestCoordinator()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        if agent and hasattr(agent, 'cleanup'):
            agent.cleanup()

    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info(f"{self.__class__.__name__} cleaning up resources...")
        try:
            # Close ZMQ sockets if they exist
            if hasattr(self, 'socket') and self.socket:
                self.socket.close()
                self.socket = None
            if hasattr(self, 'context') and self.context:
                self.context.term()
                self.context = None
            # Close any open file handles
            # [Add specific resource cleanup here]
            
            # Call parent class cleanup if it exists
            super().cleanup()
            
            logger.info(f"{self.__class__.__name__} cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
