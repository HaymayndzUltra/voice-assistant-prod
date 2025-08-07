"""ZMQ server implementation for ModelOps Coordinator."""

import zmq
import asyncio
import threading
from typing import Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import uuid

from ..core.kernel import Kernel
from ..core.schemas import InferenceRequest
from ..core.errors import ModelOpsError
from ..adapters.local_worker import LocalWorkerAdapter


@dataclass
class MessageContext:
    """Message processing context."""
    message_id: str
    client_id: str
    message_type: str
    timestamp: datetime
    data: Dict[str, Any]
    reply_address: Optional[str] = None


class ZMQMessageHandler:
    """Handler for different ZMQ message types."""
    
    def __init__(self, kernel: Kernel, worker_adapter: LocalWorkerAdapter):
        """Initialize message handler."""
        self.kernel = kernel
        self.worker_adapter = worker_adapter
        
        # Message handlers
        self._handlers = {
            'discovery': self._handle_discovery,
            'heartbeat': self._handle_heartbeat,
            'inference_request': self._handle_inference_request,
            'model_load_request': self._handle_model_load_request,
            'model_unload_request': self._handle_model_unload_request,
            'learning_job_request': self._handle_learning_job_request,
            'goal_create_request': self._handle_goal_create_request,
            'status_request': self._handle_status_request,
            'capabilities_request': self._handle_capabilities_request
        }
    
    async def handle_message(self, context: MessageContext) -> Dict[str, Any]:
        """Handle incoming message based on type."""
        handler = self._handlers.get(context.message_type)
        if not handler:
            return {
                'type': 'error',
                'message_id': context.message_id,
                'error': f'Unknown message type: {context.message_type}',
                'timestamp': datetime.utcnow().isoformat()
            }
        
        try:
            return await handler(context)
        except Exception as e:
            return {
                'type': 'error',
                'message_id': context.message_id,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def _handle_discovery(self, context: MessageContext) -> Dict[str, Any]:
        """Handle discovery request."""
        worker_status = self.worker_adapter.get_status()
        capabilities = self.worker_adapter.get_capabilities()
        
        return {
            'type': 'worker_info',
            'message_id': context.message_id,
            'worker_id': worker_status.worker_id,
            'status': worker_status.status,
            'active_tasks': worker_status.active_tasks,
            'total_completed': worker_status.total_completed,
            'total_errors': worker_status.total_errors,
            'capabilities': capabilities,
            'system_info': worker_status.system_info,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _handle_heartbeat(self, context: MessageContext) -> Dict[str, Any]:
        """Handle heartbeat request."""
        worker_status = self.worker_adapter.get_status()
        
        return {
            'type': 'heartbeat_ack',
            'message_id': context.message_id,
            'worker_id': worker_status.worker_id,
            'status': worker_status.status,
            'active_tasks': worker_status.active_tasks,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _handle_inference_request(self, context: MessageContext) -> Dict[str, Any]:
        """Handle inference request."""
        data = context.data
        
        # Create inference request
        request = InferenceRequest(
            model_name=data.get('model_name', ''),
            prompt=data.get('prompt', ''),
            max_tokens=data.get('max_tokens', 100),
            temperature=data.get('temperature', 0.7)
        )
        
        # Execute inference
        response = self.worker_adapter.execute_inference(request)
        
        return {
            'type': 'inference_response',
            'message_id': context.message_id,
            'data': {
                'response_text': response.response_text,
                'tokens_generated': response.tokens_generated,
                'inference_time_ms': response.inference_time_ms,
                'status': response.status,
                'error_message': response.error_message
            },
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _handle_model_load_request(self, context: MessageContext) -> Dict[str, Any]:
        """Handle model load request."""
        data = context.data
        
        result = self.worker_adapter.execute_model_load(
            model_name=data.get('model_name', ''),
            model_path=data.get('model_path', ''),
            shards=data.get('shards', 1),
            load_params=data.get('load_params')
        )
        
        return {
            'type': 'model_load_response',
            'message_id': context.message_id,
            'data': result,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _handle_model_unload_request(self, context: MessageContext) -> Dict[str, Any]:
        """Handle model unload request."""
        data = context.data
        
        result = self.worker_adapter.execute_model_unload(
            model_name=data.get('model_name', ''),
            force=data.get('force', False)
        )
        
        return {
            'type': 'model_unload_response',
            'message_id': context.message_id,
            'data': result,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _handle_learning_job_request(self, context: MessageContext) -> Dict[str, Any]:
        """Handle learning job submission request."""
        data = context.data
        
        result = self.worker_adapter.submit_learning_job(
            job_type=data.get('job_type', ''),
            model_name=data.get('model_name', ''),
            dataset_path=data.get('dataset_path', ''),
            parameters=data.get('parameters')
        )
        
        return {
            'type': 'learning_job_response',
            'message_id': context.message_id,
            'data': result,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _handle_goal_create_request(self, context: MessageContext) -> Dict[str, Any]:
        """Handle goal creation request."""
        data = context.data
        
        result = self.worker_adapter.create_goal(
            title=data.get('title', ''),
            description=data.get('description', ''),
            priority=data.get('priority', 'medium'),
            metadata=data.get('metadata')
        )
        
        return {
            'type': 'goal_create_response',
            'message_id': context.message_id,
            'data': result,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _handle_status_request(self, context: MessageContext) -> Dict[str, Any]:
        """Handle status request."""
        system_status = self.kernel.get_system_status()
        
        return {
            'type': 'status_response',
            'message_id': context.message_id,
            'data': system_status,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _handle_capabilities_request(self, context: MessageContext) -> Dict[str, Any]:
        """Handle capabilities request."""
        capabilities = self.worker_adapter.get_capabilities()
        
        return {
            'type': 'capabilities_response',
            'message_id': context.message_id,
            'data': capabilities,
            'timestamp': datetime.utcnow().isoformat()
        }


class ZMQServer:
    """
    ZMQ server for ModelOps Coordinator.
    
    Provides asynchronous message handling over ZMQ transport,
    supporting various ModelOps operations via message protocol.
    """
    
    def __init__(self, kernel: Kernel, bind_address: str = "tcp://*:7211",
                 max_workers: int = 10):
        """
        Initialize ZMQ server.
        
        Args:
            kernel: ModelOps Coordinator kernel
            bind_address: ZMQ bind address
            max_workers: Maximum worker threads
        """
        self.kernel = kernel
        self.bind_address = bind_address
        self.max_workers = max_workers
        
        # ZMQ context and socket
        self.zmq_context = zmq.Context()
        self.socket: Optional[zmq.Socket] = None
        
        # Worker adapter for local operations
        self.worker_adapter = LocalWorkerAdapter(kernel)
        
        # Message handler
        self.message_handler = ZMQMessageHandler(kernel, self.worker_adapter)
        
        # Server state
        self._running = False
        self._server_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Statistics
        self._stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'messages_failed': 0,
            'start_time': None,
            'active_connections': 0
        }
        self._stats_lock = threading.Lock()
        
        # Client tracking
        self._active_clients: Dict[str, datetime] = {}
        self._clients_lock = threading.Lock()
    
    def start(self):
        """Start the ZMQ server."""
        if self._running:
            return
        
        try:
            # Create and bind socket
            self.socket = self.zmq_context.socket(zmq.REP)
            self.socket.setsockopt(zmq.LINGER, 1000)  # 1 second linger
            self.socket.bind(self.bind_address)
            
            self._running = True
            self._stats['start_time'] = datetime.utcnow()
            
            # Start server thread
            self._server_thread = threading.Thread(
                target=self._server_loop,
                name="ZMQServer",
                daemon=True
            )
            self._server_thread.start()
            
            # Start cleanup thread
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                name="ZMQCleanup",
                daemon=True
            )
            self._cleanup_thread.start()
            
        except Exception as e:
            self._running = False
            if self.socket:
                self.socket.close()
                self.socket = None
            raise ModelOpsError(f"Failed to start ZMQ server: {e}", "ZMQ_START_ERROR")
    
    def _server_loop(self):
        """Main server loop."""
        while self._running and not self._shutdown_event.is_set():
            try:
                # Check for incoming messages with timeout
                if self.socket.poll(1000):  # 1 second timeout
                    self._handle_incoming_message()
                    
            except zmq.ZMQError as e:
                if e.errno == zmq.ETERM:
                    break  # Context terminated
                else:
                    # Log error but continue
                    with self._stats_lock:
                        self._stats['messages_failed'] += 1
            except Exception:
                # Log unexpected error but continue
                with self._stats_lock:
                    self._stats['messages_failed'] += 1
    
    def _handle_incoming_message(self):
        """Handle incoming ZMQ message."""
        try:
            # Receive message
            message_data = self.socket.recv_json(zmq.NOBLOCK)
            
            with self._stats_lock:
                self._stats['messages_received'] += 1
            
            # Parse message
            context = self._parse_message(message_data)
            
            # Track client
            if context.client_id:
                with self._clients_lock:
                    self._active_clients[context.client_id] = datetime.utcnow()
            
            # Process message in thread pool
            asyncio.run(self._process_message_async(context))
            
        except zmq.Again:
            # No message available
            pass
        except Exception as e:
            # Send error response
            error_response = {
                'type': 'error',
                'error': f'Message processing error: {e}',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            try:
                self.socket.send_json(error_response, zmq.NOBLOCK)
            except Exception:
                pass  # Best effort
            
            with self._stats_lock:
                self._stats['messages_failed'] += 1
    
    def _parse_message(self, message_data: Dict) -> MessageContext:
        """Parse incoming message into context."""
        return MessageContext(
            message_id=message_data.get('request_id', str(uuid.uuid4())),
            client_id=message_data.get('client_id', 'unknown'),
            message_type=message_data.get('type', 'unknown'),
            timestamp=datetime.utcnow(),
            data=message_data.get('data', message_data)  # Support both formats
        )
    
    async def _process_message_async(self, context: MessageContext):
        """Process message asynchronously."""
        try:
            # Handle message
            response = await self.message_handler.handle_message(context)
            
            # Send response
            self.socket.send_json(response)
            
            with self._stats_lock:
                self._stats['messages_processed'] += 1
                
        except Exception as e:
            # Send error response
            error_response = {
                'type': 'error',
                'message_id': context.message_id,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            try:
                self.socket.send_json(error_response)
            except Exception:
                pass  # Best effort
            
            with self._stats_lock:
                self._stats['messages_failed'] += 1
    
    def _cleanup_loop(self):
        """Background cleanup loop."""
        while self._running and not self._shutdown_event.wait(60):  # Every minute
            try:
                self._cleanup_stale_clients()
            except Exception:
                pass
    
    def _cleanup_stale_clients(self):
        """Remove stale client entries."""
        cutoff = datetime.utcnow().timestamp() - 300  # 5 minutes
        
        with self._clients_lock:
            stale_clients = [
                client_id for client_id, last_seen in self._active_clients.items()
                if last_seen.timestamp() < cutoff
            ]
            
            for client_id in stale_clients:
                del self._active_clients[client_id]
    
    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        with self._stats_lock:
            stats = self._stats.copy()
        
        with self._clients_lock:
            stats['active_clients'] = len(self._active_clients)
            stats['client_list'] = list(self._active_clients.keys())
        
        if stats['start_time']:
            uptime = datetime.utcnow() - stats['start_time']
            stats['uptime_seconds'] = uptime.total_seconds()
        
        stats['running'] = self._running
        stats['bind_address'] = self.bind_address
        
        return stats
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status."""
        return {
            'server_running': self._running,
            'kernel_healthy': self.kernel.is_healthy(),
            'worker_healthy': self.worker_adapter.is_healthy(),
            'socket_bound': self.socket is not None,
            'stats': self.get_server_stats()
        }
    
    def stop(self):
        """Stop the ZMQ server."""
        if not self._running:
            return
        
        # Signal shutdown
        self._running = False
        self._shutdown_event.set()
        
        # Wait for server thread
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=5.0)
        
        # Wait for cleanup thread
        if hasattr(self, '_cleanup_thread') and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=2.0)
        
        # Close socket
        if self.socket:
            self.socket.close()
            self.socket = None
        
        # Shutdown worker adapter
        self.worker_adapter.shutdown()
        
        # Terminate context
        self.zmq_context.term()
    
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()