#!/usr/bin/env python3
import sys
import os
import json
import time
import logging
import threading
import argparse
import zmq
import psutil
import heapq
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

# --- Path Setup ---
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

# --- Imports from Project ---
from src.core.base_agent import BaseAgent
from utils.service_discovery_client import get_service_address, register_service
from utils.env_loader import get_env
from src.network.secure_zmq import is_secure_zmq_enabled, configure_secure_client, configure_secure_server
from main_pc_code.src.common.data_models import (
    TaskDefinition, TaskResult, TaskStatus, SystemEvent, ErrorReport, ErrorSeverity
)
from pydantic import BaseModel, Field

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
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'request_coordinator.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('RequestCoordinator')

# --- Constants ---
DEFAULT_PORT = 26002
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
    def __init__(self, **kwargs):
        port = kwargs.get('port', DEFAULT_PORT)
        super().__init__(name="RequestCoordinator", port=port, health_check_port=port + 1)

        self.context = zmq.Context()
        self._init_zmq_sockets()

        self.running = True
        self.start_time = time.time()
        self.interrupt_flag = threading.Event()

        self.task_queue = []
        self.queue_lock = threading.Lock()
        self.queue_max_size = 100

        self.circuit_breakers = {}
        self._init_circuit_breakers()
        
        self.last_interaction_time = time.time()
        self.inactivity_threshold = 300
        self.pending_suggestions = []

        self._register_service()
        self._start_threads()
        logger.info(f"RequestCoordinator initialized, listening on tcp://{BIND_ADDRESS}:{self.port}")

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
            fallback_address = f"tcp://localhost:{INTERRUPT_PORT}"
            self.interrupt_socket.connect(fallback_address)
            logger.warning(f"InterruptService not found in discovery. Falling back to default address: {fallback_address}")
        
        # Subscribe to all messages
        self.interrupt_socket.setsockopt(zmq.SUBSCRIBE, b"")

        # Connect to all required downstream services
        self.memory_socket = self._connect_to_service("MemoryOrchestrator")
        self.tts_socket = self._connect_to_service("TTSConnector")
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

    def _start_threads(self):
        threads = {
            "request_handler": self._handle_requests,
            "suggestion_handler": self._handle_proactive_suggestions,
            "inactivity_checker": self._check_inactivity,
            "interrupt_listener": self._listen_for_interrupts,
            "task_dispatcher": self._dispatch_loop,
        }
        for name, target in threads.items():
            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            logger.info(f"Started {name} thread.")

    def _register_service(self):
        """Register this agent with the service discovery system."""
        register_service(
            name=self.name, 
            port=self.port,
            additional_info={"suggestion_port": self.suggestion_port}
        )

    def _handle_requests(self):
        while self.running:
            try:
                message_raw = self.main_socket.recv_json()
                self.last_interaction_time = time.time()
                
                # Ensure message_raw is a dictionary before accessing with .get()
                if not isinstance(message_raw, dict):
                    logger.error(f"Received non-dictionary message: {message_raw}")
                    error_response = AgentResponse(
                        status="error",
                        message="Invalid message format: expected dictionary",
                        error="Invalid message format"
                    )
                    self.main_socket.send_json(error_response.model_dump())
                    continue
                    
                request_type = message_raw.get('type')
                
                if request_type == 'text':
                    # Convert raw dict to Pydantic model
                    request = TextRequest.model_validate(message_raw)
                    response = self._process_text(request)
                elif request_type == 'audio':
                    # Convert raw dict to Pydantic model
                    request = AudioRequest.model_validate(message_raw)
                    response = self._process_audio(request)
                elif request_type == 'vision':
                    # Convert raw dict to Pydantic model
                    request = VisionRequest.model_validate(message_raw)
                    response = self._process_vision(request)
                else:
                    response = AgentResponse(
                        status="error",
                        message=f"Unknown request type: {request_type}"
                    )
                
                # Convert Pydantic model to dict for ZMQ
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

    def _process_text(self, request: TextRequest) -> AgentResponse:
        logger.info(f"Queueing text request: {request.data[:50]}...")
        
        # Create standardized task using TaskDefinition
        task = TaskDefinition(
            task_id=f"task_{time.time()}",
            agent_id=self.name,
            task_type='text_processing',
            priority=2,
            parameters={"request": request.model_dump()},
            created_at=datetime.now()
        )
        
        self.add_task_to_queue(priority=2, task=task)
        return AgentResponse(
            status="success",
            message="Text request queued"
        )

    def _process_audio(self, request: AudioRequest) -> AgentResponse:
        logger.info("Queueing audio request...")
        
        # Create standardized task using TaskDefinition
        task = TaskDefinition(
            task_id=f"task_{time.time()}",
            agent_id=self.name,
            task_type='audio_processing',
            priority=1,
            parameters={"request": request.model_dump()},
            created_at=datetime.now()
        )
        
        self.add_task_to_queue(priority=1, task=task)
        return AgentResponse(
            status="success",
            message="Audio request queued"
        )

    def _process_vision(self, request: VisionRequest) -> AgentResponse:
        logger.info("Queueing vision request...")
        
        # Create standardized task using TaskDefinition
        task = TaskDefinition(
            task_id=f"task_{time.time()}",
            agent_id=self.name,
            task_type='vision_processing',
            priority=3,
            parameters={"request": request.model_dump()},
            created_at=datetime.now()
        )
        
        self.add_task_to_queue(priority=3, task=task)
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
            # Use BaseAgent's standardized error reporting
            self.report_error(
                error_type="task_processing_error",
                message=f"Failed to process task {task.task_id}: {str(e)}",
                severity=ErrorSeverity.ERROR,
                context={"task_id": task.task_id, "service": target_service, "task_type": task_type}
            )
            logger.error(f"Failed to process task {task.task_id} with {target_service}: {e}")
            if breaker: breaker.record_failure()

    def _handle_task_response(self, response: AgentResponse):
        logger.info(f"Handling response: {response.status}")
        
        # Handle TTS if needed
        if response.speak and self.tts_socket:
            try:
                # Use BaseAgent's standardized request method
                self.send_request_to_agent(
                    agent_name="TTSConnector",
                    request={"text": response.speak}
                )
            except Exception as e:
                self.report_error(
                    error_type="tts_request_error",
                    message=f"Error sending TTS request: {str(e)}",
                    severity=ErrorSeverity.WARNING
                )
                
        # Handle memory storage if needed
        if response.memory_entry and self.memory_socket:
            try:
                # Use BaseAgent's standardized request method
                self.send_request_to_agent(
                    agent_name="MemoryOrchestrator",
                    request={"action": "save", "data": response.memory_entry}
                )
            except Exception as e:
                self.report_error(
                    error_type="memory_storage_error",
                    message=f"Error sending memory request: {str(e)}",
                    severity=ErrorSeverity.WARNING
                )

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
        return {
            "status": "healthy" if self.running else "stopped",
            "uptime": time.time() - self.start_time,
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "queue_size": len(self.task_queue),
            "circuit_breakers": {n: cb.get_status() for n, cb in self.circuit_breakers.items()}
        }

    def stop(self):
        self.running = False
        logger.info("Stopping RequestCoordinator...")
        for sock in [self.main_socket, self.suggestion_socket, self.interrupt_socket, self.memory_socket, self.tts_socket, self.cot_socket, self.got_tot_socket]:
            if sock and not sock.closed:
                sock.close()
        self.context.term()
        logger.info("RequestCoordinator stopped.")

    def run(self):
        logger.info("RequestCoordinator is running...")
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Request Coordinator Agent')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Port to bind to')
    args = parser.parse_args()
    
    agent = RequestCoordinator(port=args.port)
    agent.run()