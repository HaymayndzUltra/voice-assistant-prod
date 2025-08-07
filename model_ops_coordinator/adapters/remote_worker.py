"""Remote worker adapter for ModelOps Coordinator."""

import zmq
import json
import time
import threading
import uuid
from typing import Dict, Optional, Any, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from ..core.schemas import InferenceRequest, InferenceResponse
from ..core.errors import ModelOpsError


class ConnectionState(Enum):
    """Connection state enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class RemoteWorkerInfo:
    """Remote worker information."""
    worker_id: str
    endpoint: str
    status: str
    last_seen: datetime
    capabilities: Dict[str, Any]
    active_tasks: int
    total_completed: int
    total_errors: int


class RemoteWorkerAdapter:
    """
    Remote worker adapter using ZMQ for communication.
    
    This adapter manages connections to remote ModelOps Coordinator instances,
    providing distributed computing capabilities through ZMQ messaging.
    """
    
    def __init__(self, worker_endpoints: List[str], client_id: Optional[str] = None,
                 heartbeat_interval: float = 30.0, connection_timeout: float = 10.0):
        """
        Initialize remote worker adapter.
        
        Args:
            worker_endpoints: List of ZMQ endpoints for remote workers
            client_id: Unique client identifier
            heartbeat_interval: Heartbeat frequency in seconds
            connection_timeout: Connection timeout in seconds
        """
        self.worker_endpoints = worker_endpoints
        self.client_id = client_id or f"remote-client-{uuid.uuid4().hex[:8]}"
        self.heartbeat_interval = heartbeat_interval
        self.connection_timeout = connection_timeout
        
        # ZMQ context and sockets
        self.zmq_context = zmq.Context()
        self._sockets: Dict[str, zmq.Socket] = {}
        self._socket_lock = threading.RLock()
        
        # Worker management
        self._workers: Dict[str, RemoteWorkerInfo] = {}
        self._connection_states: Dict[str, ConnectionState] = {}
        self._workers_lock = threading.RLock()
        
        # Background threads
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._discovery_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Callbacks
        self._status_callbacks: List[Callable] = []
        
        # Request tracking
        self._pending_requests: Dict[str, threading.Event] = {}
        self._request_responses: Dict[str, Dict] = {}
        self._request_lock = threading.RLock()
        
        # Initialize connections
        self._initialize_connections()
    
    def _initialize_connections(self):
        """Initialize connections to remote workers."""
        # Initialize connection states
        for endpoint in self.worker_endpoints:
            self._connection_states[endpoint] = ConnectionState.DISCONNECTED
        
        # Start background threads
        self._start_background_threads()
        
        # Initial connection attempt
        self._connect_to_workers()
    
    def _start_background_threads(self):
        """Start background threads for heartbeat and discovery."""
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name="RemoteWorkerHeartbeat",
            daemon=True
        )
        self._heartbeat_thread.start()
        
        self._discovery_thread = threading.Thread(
            target=self._discovery_loop,
            name="RemoteWorkerDiscovery",
            daemon=True
        )
        self._discovery_thread.start()
    
    def _connect_to_workers(self):
        """Connect to all remote workers."""
        for endpoint in self.worker_endpoints:
            threading.Thread(
                target=self._connect_worker,
                args=(endpoint,),
                name=f"Connect-{endpoint}",
                daemon=True
            ).start()
    
    def _connect_worker(self, endpoint: str):
        """Connect to a specific worker endpoint."""
        try:
            with self._socket_lock:
                self._connection_states[endpoint] = ConnectionState.CONNECTING
            
            # Create socket
            socket = self.zmq_context.socket(zmq.REQ)
            socket.setsockopt(zmq.LINGER, 1000)  # 1 second linger
            socket.setsockopt(zmq.RCVTIMEO, int(self.connection_timeout * 1000))
            socket.setsockopt(zmq.SNDTIMEO, int(self.connection_timeout * 1000))
            
            # Connect to endpoint
            socket.connect(endpoint)
            
            with self._socket_lock:
                self._sockets[endpoint] = socket
                self._connection_states[endpoint] = ConnectionState.CONNECTED
            
            # Send initial discovery message
            self._send_discovery_message(endpoint)
            
        except Exception as e:
            with self._socket_lock:
                self._connection_states[endpoint] = ConnectionState.ERROR
            
            self._notify_connection_error(endpoint, str(e))
    
    def _send_discovery_message(self, endpoint: str):
        """Send discovery message to worker."""
        try:
            message = {
                'type': 'discovery',
                'client_id': self.client_id,
                'timestamp': datetime.utcnow().isoformat(),
                'request_id': str(uuid.uuid4())
            }
            
            response = self._send_message(endpoint, message)
            if response and response.get('type') == 'worker_info':
                self._process_worker_info(endpoint, response)
                
        except Exception as e:
            self._notify_connection_error(endpoint, f"Discovery failed: {e}")
    
    def _send_message(self, endpoint: str, message: Dict, timeout: Optional[float] = None) -> Optional[Dict]:
        """Send message to worker and wait for response."""
        timeout = timeout or self.connection_timeout
        
        try:
            with self._socket_lock:
                socket = self._sockets.get(endpoint)
                if not socket:
                    raise ModelOpsError(f"No socket for endpoint {endpoint}", "NO_SOCKET")
                
                # Send message
                socket.send_json(message)
                
                # Wait for response
                if socket.poll(int(timeout * 1000)):
                    response = socket.recv_json()
                    return response
                else:
                    raise ModelOpsError(f"Timeout waiting for response from {endpoint}", "TIMEOUT")
                    
        except zmq.ZMQError as e:
            raise ModelOpsError(f"ZMQ error: {e}", "ZMQ_ERROR")
        except Exception as e:
            raise ModelOpsError(f"Communication error: {e}", "COMM_ERROR")
    
    def _process_worker_info(self, endpoint: str, worker_info: Dict):
        """Process worker information from discovery response."""
        with self._workers_lock:
            worker_id = worker_info.get('worker_id', endpoint)
            
            self._workers[worker_id] = RemoteWorkerInfo(
                worker_id=worker_id,
                endpoint=endpoint,
                status=worker_info.get('status', 'unknown'),
                last_seen=datetime.utcnow(),
                capabilities=worker_info.get('capabilities', {}),
                active_tasks=worker_info.get('active_tasks', 0),
                total_completed=worker_info.get('total_completed', 0),
                total_errors=worker_info.get('total_errors', 0)
            )
        
        # Notify callbacks
        self._notify_worker_discovered(worker_id, worker_info)
    
    def _heartbeat_loop(self):
        """Background heartbeat loop."""
        while not self._shutdown_event.wait(self.heartbeat_interval):
            try:
                self._send_heartbeats()
            except Exception as e:
                # Log error but continue
                pass
    
    def _send_heartbeats(self):
        """Send heartbeat to all connected workers."""
        with self._socket_lock:
            endpoints = list(self._sockets.keys())
        
        for endpoint in endpoints:
            if self._connection_states.get(endpoint) == ConnectionState.CONNECTED:
                try:
                    message = {
                        'type': 'heartbeat',
                        'client_id': self.client_id,
                        'timestamp': datetime.utcnow().isoformat(),
                        'request_id': str(uuid.uuid4())
                    }
                    
                    response = self._send_message(endpoint, message, timeout=5.0)
                    if response and response.get('type') == 'heartbeat_ack':
                        self._update_worker_from_heartbeat(endpoint, response)
                    else:
                        self._handle_heartbeat_failure(endpoint)
                        
                except Exception:
                    self._handle_heartbeat_failure(endpoint)
    
    def _update_worker_from_heartbeat(self, endpoint: str, heartbeat_response: Dict):
        """Update worker info from heartbeat response."""
        with self._workers_lock:
            for worker in self._workers.values():
                if worker.endpoint == endpoint:
                    worker.last_seen = datetime.utcnow()
                    worker.status = heartbeat_response.get('status', worker.status)
                    worker.active_tasks = heartbeat_response.get('active_tasks', worker.active_tasks)
                    break
    
    def _handle_heartbeat_failure(self, endpoint: str):
        """Handle heartbeat failure for an endpoint."""
        with self._socket_lock:
            self._connection_states[endpoint] = ConnectionState.RECONNECTING
        
        # Schedule reconnection
        threading.Thread(
            target=self._reconnect_worker,
            args=(endpoint,),
            name=f"Reconnect-{endpoint}",
            daemon=True
        ).start()
    
    def _reconnect_worker(self, endpoint: str):
        """Reconnect to a worker after failure."""
        try:
            # Close existing socket
            with self._socket_lock:
                if endpoint in self._sockets:
                    self._sockets[endpoint].close()
                    del self._sockets[endpoint]
            
            # Wait before reconnecting
            time.sleep(2.0)
            
            # Reconnect
            self._connect_worker(endpoint)
            
        except Exception as e:
            with self._socket_lock:
                self._connection_states[endpoint] = ConnectionState.ERROR
    
    def _discovery_loop(self):
        """Background discovery loop for worker capabilities."""
        while not self._shutdown_event.wait(self.heartbeat_interval * 2):
            try:
                self._cleanup_stale_workers()
                self._rediscover_workers()
            except Exception:
                pass
    
    def _cleanup_stale_workers(self):
        """Remove workers that haven't been seen recently."""
        stale_threshold = datetime.utcnow() - timedelta(seconds=self.heartbeat_interval * 3)
        
        with self._workers_lock:
            stale_workers = [
                worker_id for worker_id, worker in self._workers.items()
                if worker.last_seen < stale_threshold
            ]
            
            for worker_id in stale_workers:
                del self._workers[worker_id]
    
    def _rediscover_workers(self):
        """Rediscover worker capabilities."""
        with self._socket_lock:
            connected_endpoints = [
                endpoint for endpoint, state in self._connection_states.items()
                if state == ConnectionState.CONNECTED
            ]
        
        for endpoint in connected_endpoints:
            try:
                self._send_discovery_message(endpoint)
            except Exception:
                pass
    
    def execute_inference(self, request: InferenceRequest, 
                         preferred_worker: Optional[str] = None) -> InferenceResponse:
        """
        Execute inference request on a remote worker.
        
        Args:
            request: Inference request
            preferred_worker: Preferred worker ID (optional)
            
        Returns:
            Inference response
        """
        # Select worker
        worker = self._select_worker_for_inference(request.model_name, preferred_worker)
        if not worker:
            return InferenceResponse(
                response_text="",
                tokens_generated=0,
                inference_time_ms=0,
                status="error",
                error_message="No available workers for inference"
            )
        
        # Prepare message
        message = {
            'type': 'inference_request',
            'client_id': self.client_id,
            'request_id': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'model_name': request.model_name,
                'prompt': request.prompt,
                'max_tokens': request.max_tokens,
                'temperature': request.temperature
            }
        }
        
        try:
            response = self._send_message(worker.endpoint, message, timeout=60.0)
            
            if response and response.get('type') == 'inference_response':
                data = response.get('data', {})
                return InferenceResponse(
                    response_text=data.get('response_text', ''),
                    tokens_generated=data.get('tokens_generated', 0),
                    inference_time_ms=data.get('inference_time_ms', 0),
                    status=data.get('status', 'success'),
                    error_message=data.get('error_message')
                )
            else:
                return InferenceResponse(
                    response_text="",
                    tokens_generated=0,
                    inference_time_ms=0,
                    status="error",
                    error_message=f"Invalid response from worker {worker.worker_id}"
                )
                
        except Exception as e:
            return InferenceResponse(
                response_text="",
                tokens_generated=0,
                inference_time_ms=0,
                status="error",
                error_message=f"Communication error: {e}"
            )
    
    def _select_worker_for_inference(self, model_name: str, 
                                   preferred_worker: Optional[str] = None) -> Optional[RemoteWorkerInfo]:
        """Select best worker for inference request."""
        with self._workers_lock:
            available_workers = [
                worker for worker in self._workers.values()
                if worker.status in ['online', 'busy'] and 
                   self._worker_supports_model(worker, model_name)
            ]
            
            if not available_workers:
                return None
            
            # Prefer specific worker if requested
            if preferred_worker:
                for worker in available_workers:
                    if worker.worker_id == preferred_worker:
                        return worker
            
            # Select worker with lowest load
            return min(available_workers, key=lambda w: w.active_tasks)
    
    def _worker_supports_model(self, worker: RemoteWorkerInfo, model_name: str) -> bool:
        """Check if worker supports the specified model."""
        inference_cap = worker.capabilities.get('inference', {})
        if not inference_cap.get('supported', False):
            return False
        
        supported_models = inference_cap.get('models', [])
        return model_name in supported_models or len(supported_models) == 0
    
    def execute_model_load(self, model_name: str, model_path: str,
                          worker_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute model load on a specific worker."""
        worker = self._get_worker(worker_id) if worker_id else self._select_available_worker()
        
        if not worker:
            return {
                'success': False,
                'error': 'No available workers'
            }
        
        message = {
            'type': 'model_load_request',
            'client_id': self.client_id,
            'request_id': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'model_name': model_name,
                'model_path': model_path
            }
        }
        
        try:
            response = self._send_message(worker.endpoint, message, timeout=120.0)
            return response.get('data', {}) if response else {'success': False, 'error': 'No response'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_worker_status(self, worker_id: Optional[str] = None) -> List[RemoteWorkerInfo]:
        """Get status of workers."""
        with self._workers_lock:
            if worker_id:
                worker = self._workers.get(worker_id)
                return [worker] if worker else []
            else:
                return list(self._workers.values())
    
    def get_available_workers(self) -> List[RemoteWorkerInfo]:
        """Get list of available workers."""
        with self._workers_lock:
            return [
                worker for worker in self._workers.values()
                if worker.status in ['online', 'busy']
            ]
    
    def _get_worker(self, worker_id: str) -> Optional[RemoteWorkerInfo]:
        """Get worker by ID."""
        with self._workers_lock:
            return self._workers.get(worker_id)
    
    def _select_available_worker(self) -> Optional[RemoteWorkerInfo]:
        """Select an available worker."""
        available = self.get_available_workers()
        return min(available, key=lambda w: w.active_tasks) if available else None
    
    def register_status_callback(self, callback: Callable):
        """Register callback for status updates."""
        self._status_callbacks.append(callback)
    
    def unregister_status_callback(self, callback: Callable):
        """Unregister status callback."""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)
    
    def _notify_worker_discovered(self, worker_id: str, worker_info: Dict):
        """Notify callbacks of worker discovery."""
        for callback in self._status_callbacks:
            try:
                callback({
                    'type': 'worker_discovered',
                    'worker_id': worker_id,
                    'worker_info': worker_info
                })
            except Exception:
                pass
    
    def _notify_connection_error(self, endpoint: str, error: str):
        """Notify callbacks of connection error."""
        for callback in self._status_callbacks:
            try:
                callback({
                    'type': 'connection_error',
                    'endpoint': endpoint,
                    'error': error
                })
            except Exception:
                pass
    
    def shutdown(self):
        """Shutdown remote worker adapter."""
        # Signal shutdown
        self._shutdown_event.set()
        
        # Wait for threads
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=5.0)
        
        if self._discovery_thread and self._discovery_thread.is_alive():
            self._discovery_thread.join(timeout=5.0)
        
        # Close sockets
        with self._socket_lock:
            for socket in self._sockets.values():
                socket.close()
            self._sockets.clear()
        
        # Close context
        self.zmq_context.term()
        
        # Clear callbacks
        self._status_callbacks.clear()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()