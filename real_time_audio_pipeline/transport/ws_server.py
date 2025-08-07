"""
Real-Time Audio Pipeline - WebSocket Server

FastAPI-based WebSocket server for real-time transcript streaming to browser clients.
Optimized for low-latency delivery with efficient connection management.
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, Set, Optional, AsyncGenerator
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
import uuid

from .schemas import (
    TranscriptEvent, EventNotification, WebSocketMessage, PipelineStatus,
    serialize_for_websocket, create_websocket_message, MessageTypes
)


class WebSocketConnectionManager:
    """
    Manages WebSocket connections with efficient broadcasting and health monitoring.
    
    Features:
    - Connection lifecycle management
    - Efficient message broadcasting to multiple clients
    - Client-specific message routing
    - Connection health monitoring with heartbeat
    - Automatic cleanup of stale connections
    """
    
    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
        
        # Statistics
        self.total_connections = 0
        self.messages_sent = 0
        self.broadcast_count = 0
        
    async def connect(self, websocket: WebSocket, client_id: Optional[str] = None) -> str:
        """
        Accept new WebSocket connection and register client.
        
        Args:
            websocket: WebSocket connection instance
            client_id: Optional client identifier
            
        Returns:
            Assigned client ID
        """
        await websocket.accept()
        
        # Generate client ID if not provided
        if not client_id:
            client_id = str(uuid.uuid4())
        
        # Register connection
        self.active_connections[client_id] = websocket
        self.connection_metadata[client_id] = {
            'connected_at': time.time(),
            'messages_sent': 0,
            'last_activity': time.time(),
            'remote_address': getattr(websocket.client, 'host', 'unknown') if websocket.client else 'unknown'
        }
        
        self.total_connections += 1
        
        self.logger.info(f"WebSocket client connected: {client_id} "
                        f"(total: {len(self.active_connections)})")
        
        return client_id
    
    async def disconnect(self, client_id: str) -> None:
        """
        Disconnect and clean up client connection.
        
        Args:
            client_id: Client identifier to disconnect
        """
        if client_id in self.active_connections:
            # Clean up connection
            del self.active_connections[client_id]
            
            # Log connection stats if available
            if client_id in self.connection_metadata:
                metadata = self.connection_metadata[client_id]
                duration = time.time() - metadata['connected_at']
                
                self.logger.info(f"WebSocket client disconnected: {client_id} "
                              f"(duration: {duration:.1f}s, "
                              f"messages: {metadata['messages_sent']})")
                
                del self.connection_metadata[client_id]
        
        self.logger.debug(f"Active connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, client_id: str) -> bool:
        """
        Send message to specific client.
        
        Args:
            message: JSON message to send
            client_id: Target client identifier
            
        Returns:
            True if sent successfully, False otherwise
        """
        if client_id not in self.active_connections:
            return False
        
        try:
            websocket = self.active_connections[client_id]
            await websocket.send_text(message)
            
            # Update statistics
            self.messages_sent += 1
            if client_id in self.connection_metadata:
                self.connection_metadata[client_id]['messages_sent'] += 1
                self.connection_metadata[client_id]['last_activity'] = time.time()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending message to {client_id}: {e}")
            await self.disconnect(client_id)
            return False
    
    async def broadcast(self, message: str) -> int:
        """
        Broadcast message to all connected clients.
        
        Args:
            message: JSON message to broadcast
            
        Returns:
            Number of clients that received the message
        """
        if not self.active_connections:
            return 0
        
        successful_sends = 0
        failed_clients = []
        
        # Send to all connected clients
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
                successful_sends += 1
                
                # Update client statistics
                if client_id in self.connection_metadata:
                    self.connection_metadata[client_id]['messages_sent'] += 1
                    self.connection_metadata[client_id]['last_activity'] = time.time()
                
            except Exception as e:
                self.logger.warning(f"Failed to send to client {client_id}: {e}")
                failed_clients.append(client_id)
        
        # Clean up failed connections
        for client_id in failed_clients:
            await self.disconnect(client_id)
        
        # Update statistics
        self.messages_sent += successful_sends
        self.broadcast_count += 1
        
        return successful_sends
    
    async def send_heartbeat(self) -> None:
        """Send heartbeat to all connected clients."""
        if not self.active_connections:
            return
        
        heartbeat_message = create_websocket_message(
            message_type=MessageTypes.HEARTBEAT,
            payload={'timestamp': time.time(), 'server_time': time.time()}
        )
        
        message_json = serialize_for_websocket(heartbeat_message)
        sent_count = await self.broadcast(message_json)
        
        self.logger.debug(f"Heartbeat sent to {sent_count} clients")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection manager statistics."""
        return {
            'active_connections': len(self.active_connections),
            'total_connections': self.total_connections,
            'messages_sent': self.messages_sent,
            'broadcast_count': self.broadcast_count,
            'client_list': list(self.active_connections.keys()),
            'connection_metadata': self.connection_metadata.copy()
        }


class WebSocketServer:
    """
    FastAPI WebSocket server for real-time RTAP transcript streaming.
    
    Features:
    - Real-time transcript delivery to browser clients
    - System event broadcasting
    - Pipeline status monitoring endpoint
    - Connection health management with heartbeat
    - Efficient async operation for minimal latency impact
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize WebSocket server.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config
        self.output_config = config['output']
        self.logger = logging.getLogger(__name__)
        
        # Server configuration
        self.port = self.output_config['websocket_port']
        self.host = "0.0.0.0"
        
        # FastAPI app
        self.app = FastAPI(title="RTAP WebSocket Server", version="1.0")
        self.connection_manager = WebSocketConnectionManager()
        
        # State management
        self.is_running = False
        self.server_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        # Performance tracking
        self.start_time = 0.0
        self.transcripts_streamed = 0
        self.events_streamed = 0
        
        # Setup routes
        self._setup_routes()
        
        self.logger.info(f"WebSocket server initialized on port {self.port}")
    
    def _setup_routes(self) -> None:
        """Setup FastAPI routes and WebSocket endpoints."""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def get_test_page():
            """Serve a simple test page for WebSocket testing."""
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>RTAP WebSocket Test</title>
                <style>
                    body { font-family: monospace; margin: 20px; }
                    #messages { border: 1px solid #ccc; height: 400px; overflow-y: auto; padding: 10px; }
                    .transcript { color: blue; }
                    .event { color: green; }
                    .status { color: orange; }
                    .error { color: red; }
                </style>
            </head>
            <body>
                <h1>RTAP WebSocket Test Client</h1>
                <div>
                    <button onclick="connect()">Connect</button>
                    <button onclick="disconnect()">Disconnect</button>
                    <span id="status">Disconnected</span>
                </div>
                <div id="messages"></div>
                
                <script>
                    let ws = null;
                    
                    function connect() {
                        ws = new WebSocket(`ws://localhost:""" + str(self.port) + """/stream`);
                        
                        ws.onopen = function(event) {
                            document.getElementById('status').textContent = 'Connected';
                            addMessage('Connected to RTAP WebSocket', 'status');
                        };
                        
                        ws.onmessage = function(event) {
                            const data = JSON.parse(event.data);
                            const className = data.message_type;
                            const content = data.message_type === 'transcript' ? 
                                data.transcript.transcript : JSON.stringify(data, null, 2);
                            addMessage(content, className);
                        };
                        
                        ws.onclose = function(event) {
                            document.getElementById('status').textContent = 'Disconnected';
                            addMessage('Disconnected from RTAP WebSocket', 'status');
                        };
                        
                        ws.onerror = function(error) {
                            addMessage('WebSocket error: ' + error, 'error');
                        };
                    }
                    
                    function disconnect() {
                        if (ws) {
                            ws.close();
                        }
                    }
                    
                    function addMessage(message, className) {
                        const messagesDiv = document.getElementById('messages');
                        const messageElement = document.createElement('div');
                        messageElement.className = className;
                        messageElement.textContent = new Date().toLocaleTimeString() + ': ' + message;
                        messagesDiv.appendChild(messageElement);
                        messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    }
                </script>
            </body>
            </html>
            """
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy" if self.is_running else "stopped",
                "connections": len(self.connection_manager.active_connections),
                "uptime": time.perf_counter() - self.start_time if self.start_time > 0 else 0
            }
        
        @self.app.get("/stats")
        async def get_stats():
            """Get server statistics."""
            return {
                "server": {
                    "is_running": self.is_running,
                    "uptime_seconds": time.perf_counter() - self.start_time if self.start_time > 0 else 0,
                    "transcripts_streamed": self.transcripts_streamed,
                    "events_streamed": self.events_streamed,
                    "port": self.port
                },
                "connections": self.connection_manager.get_stats()
            }
        
        @self.app.websocket("/stream")
        async def websocket_endpoint(websocket: WebSocket):
            """Main WebSocket endpoint for real-time streaming."""
            client_id = None
            try:
                # Accept connection
                client_id = await self.connection_manager.connect(websocket)
                
                # Send welcome message
                welcome_message = create_websocket_message(
                    message_type=MessageTypes.STATUS,
                    payload={
                        "connected": True,
                        "client_id": client_id,
                        "server_time": time.time(),
                        "message": "Connected to RTAP WebSocket stream"
                    },
                    client_id=client_id
                )
                
                await self.connection_manager.send_personal_message(
                    serialize_for_websocket(welcome_message),
                    client_id
                )
                
                # Keep connection alive and handle client messages
                while True:
                    try:
                        # Wait for client message with timeout
                        data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                        
                        # Echo back client messages (for testing)
                        echo_message = create_websocket_message(
                            message_type=MessageTypes.STATUS,
                            payload={"echo": data, "timestamp": time.time()},
                            client_id=client_id
                        )
                        
                        await self.connection_manager.send_personal_message(
                            serialize_for_websocket(echo_message),
                            client_id
                        )
                        
                    except asyncio.TimeoutError:
                        # Send heartbeat if no client activity
                        await self.connection_manager.send_heartbeat()
                    except WebSocketDisconnect:
                        break
                    
            except WebSocketDisconnect:
                self.logger.info(f"WebSocket client {client_id} disconnected normally")
            except Exception as e:
                self.logger.error(f"WebSocket error for client {client_id}: {e}")
            finally:
                if client_id:
                    await self.connection_manager.disconnect(client_id)
    
    async def start(self) -> None:
        """Start the WebSocket server."""
        try:
            self.logger.info("Starting WebSocket server...")
            self.start_time = time.perf_counter()
            self.is_running = True
            
            # Start heartbeat task
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # Configure and start uvicorn server
            config = uvicorn.Config(
                app=self.app,
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=False,  # Reduce log noise
                loop="asyncio"
            )
            
            server = uvicorn.Server(config)
            
            self.logger.info(f"WebSocket server started at ws://{self.host}:{self.port}/stream")
            
            # Run server
            await server.serve()
            
        except Exception as e:
            self.logger.error(f"Failed to start WebSocket server: {e}")
            self.is_running = False
            raise
        finally:
            self.is_running = False
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
    
    async def _heartbeat_loop(self) -> None:
        """Background heartbeat loop to maintain connection health."""
        self.logger.info("WebSocket heartbeat loop started")
        
        try:
            while self.is_running:
                # Send heartbeat every 30 seconds
                await asyncio.sleep(30.0)
                
                if self.is_running and self.connection_manager.active_connections:
                    await self.connection_manager.send_heartbeat()
                    
        except asyncio.CancelledError:
            self.logger.info("WebSocket heartbeat loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in heartbeat loop: {e}")
    
    async def stream_transcript(self, transcript: TranscriptEvent) -> int:
        """
        Stream transcript to all connected WebSocket clients.
        
        Args:
            transcript: Transcript event to stream
            
        Returns:
            Number of clients that received the transcript
        """
        if not self.is_running or not self.connection_manager.active_connections:
            return 0
        
        try:
            # Create WebSocket message
            message = create_websocket_message(
                message_type=MessageTypes.TRANSCRIPT,
                payload=transcript
            )
            
            # Broadcast to all clients
            sent_count = await self.connection_manager.broadcast(
                serialize_for_websocket(message)
            )
            
            self.transcripts_streamed += 1
            
            return sent_count
            
        except Exception as e:
            self.logger.error(f"Error streaming transcript: {e}")
            return 0
    
    async def stream_event(self, event: EventNotification) -> int:
        """
        Stream system event to all connected WebSocket clients.
        
        Args:
            event: Event notification to stream
            
        Returns:
            Number of clients that received the event
        """
        if not self.is_running or not self.connection_manager.active_connections:
            return 0
        
        try:
            # Create WebSocket message
            message = create_websocket_message(
                message_type=MessageTypes.EVENT,
                payload=event
            )
            
            # Broadcast to all clients
            sent_count = await self.connection_manager.broadcast(
                serialize_for_websocket(message)
            )
            
            self.events_streamed += 1
            
            return sent_count
            
        except Exception as e:
            self.logger.error(f"Error streaming event: {e}")
            return 0
    
    async def stream_status(self, status: PipelineStatus) -> int:
        """
        Stream pipeline status to all connected WebSocket clients.
        
        Args:
            status: Pipeline status to stream
            
        Returns:
            Number of clients that received the status
        """
        if not self.is_running or not self.connection_manager.active_connections:
            return 0
        
        try:
            # Create WebSocket message
            message = create_websocket_message(
                message_type=MessageTypes.STATUS,
                payload=status.dict()
            )
            
            # Broadcast to all clients
            sent_count = await self.connection_manager.broadcast(
                serialize_for_websocket(message)
            )
            
            return sent_count
            
        except Exception as e:
            self.logger.error(f"Error streaming status: {e}")
            return 0
    
    async def consume_pipeline_output(self, output_stream: AsyncGenerator[Dict[str, Any], None]) -> None:
        """
        Consume pipeline output and stream to WebSocket clients.
        
        Args:
            output_stream: Async generator from pipeline
        """
        self.logger.info("Starting WebSocket pipeline output consumption")
        
        try:
            async for output_data in output_stream:
                try:
                    # Create transcript event
                    transcript = TranscriptEvent(
                        transcript=output_data.get('transcript', ''),
                        confidence=output_data.get('confidence', 0.0),
                        processing_time_ms=output_data.get('processing_time_ms', 0),
                        audio_duration_ms=output_data.get('audio_duration_ms', 0),
                        sequence_number=self.transcripts_streamed + 1,
                        language=output_data.get('language', 'unknown'),
                        sentiment=output_data.get('sentiment', 'neutral')
                    )
                    
                    # Stream to WebSocket clients
                    clients_reached = await self.stream_transcript(transcript)
                    
                    if clients_reached > 0:
                        self.logger.debug(f"Streamed transcript to {clients_reached} WebSocket clients")
                    
                except Exception as e:
                    self.logger.error(f"Error processing pipeline output for WebSocket: {e}")
                    
        except asyncio.CancelledError:
            self.logger.info("WebSocket pipeline output consumption cancelled")
        except Exception as e:
            self.logger.error(f"Fatal error in WebSocket pipeline consumption: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive server statistics."""
        uptime = time.perf_counter() - self.start_time if self.start_time > 0 else 0
        
        return {
            'is_running': self.is_running,
            'uptime_seconds': uptime,
            'transcripts_streamed': self.transcripts_streamed,
            'events_streamed': self.events_streamed,
            'host': self.host,
            'port': self.port,
            'connections': self.connection_manager.get_stats()
        }
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the WebSocket server."""
        self.logger.info("Shutting down WebSocket server...")
        
        # Stop accepting new connections
        self.is_running = False
        
        # Cancel heartbeat task
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Notify connected clients about shutdown
        if self.connection_manager.active_connections:
            shutdown_message = create_websocket_message(
                message_type=MessageTypes.STATUS,
                payload={
                    "server_shutdown": True,
                    "message": "Server is shutting down",
                    "timestamp": time.time()
                }
            )
            
            await self.connection_manager.broadcast(
                serialize_for_websocket(shutdown_message)
            )
            
            # Give clients time to receive shutdown message
            await asyncio.sleep(1.0)
        
        # Log final statistics
        stats = self.get_stats()
        self.logger.info(f"WebSocket server shutdown complete. "
                        f"Streamed: {stats['transcripts_streamed']} transcripts, "
                        f"{stats['events_streamed']} events to "
                        f"{stats['connections']['total_connections']} total clients")
    
    def __repr__(self) -> str:
        """String representation of server state."""
        return (f"WebSocketServer(running={self.is_running}, "
                f"port={self.port}, connections={len(self.connection_manager.active_connections)})")
