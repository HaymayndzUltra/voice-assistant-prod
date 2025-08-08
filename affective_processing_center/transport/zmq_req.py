"""ZeroMQ REP server for on-demand emotion synthesis requests."""

import zmq
import zmq.asyncio
import json
import logging
import asyncio
import time
from typing import Optional, Dict, Any, Callable
from datetime import datetime
import threading
import base64

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schemas import SynthesisRequest, SynthesisResponse, EmotionType
from resiliency.circuit_breaker import CircuitBreaker
from resiliency.bulkhead import Bulkhead

logger = logging.getLogger(__name__)


class ZmqSynthesisServer:
    """
    ZeroMQ REP server for handling emotion synthesis requests.
    
    This server listens for synthesis requests, processes them using
    the synthesis module, and returns the generated audio.
    """
    
    def __init__(
        self,
        port: int = 5706,
        bind_address: str = "tcp://*",
        synthesis_handler: Optional[Callable] = None,
        max_request_size: int = 1024 * 1024,  # 1MB
        request_timeout: int = 30000  # 30 seconds
    ):
        """
        Initialize ZMQ synthesis server.
        
        Args:
            port: Port number to bind to
            bind_address: Address pattern to bind to
            synthesis_handler: Function to handle synthesis requests
            max_request_size: Maximum request size in bytes
            request_timeout: Request timeout in milliseconds
        """
        self.port = port
        self.bind_address = bind_address
        self.synthesis_handler = synthesis_handler
        self.max_request_size = max_request_size
        self.request_timeout = request_timeout
        
        # ZMQ components
        self.context: Optional[zmq.asyncio.Context] = None
        self.socket: Optional[zmq.asyncio.Socket] = None
        
        # State tracking
        self.is_running = False
        self.is_serving = False
        
        # Statistics
        self.stats = {
            'requests_received': 0,
            'requests_processed': 0,
            'requests_failed': 0,
            'bytes_received': 0,
            'bytes_sent': 0,
            'avg_processing_time_ms': 0.0,
            'last_request_time': None,
            'uptime_start': None
        }
        
        # Processing times for statistics
        self._processing_times = []
        self._lock = threading.Lock()
        
        # Resiliency components
        from resiliency.circuit_breaker import CircuitBreakerConfig
        breaker_config = CircuitBreakerConfig()
        breaker_config.failure_threshold = 5
        breaker_config.timeout_duration = 30.0
        
        self.circuit_breaker = CircuitBreaker(
            name="synthesis_server",
            config=breaker_config
        )
        
        from resiliency.bulkhead import BulkheadConfig
        bulkhead_config = BulkheadConfig(
            name="synthesis_server",
            max_concurrent=4,
            max_queue_size=10
        )
        
        self.bulkhead = Bulkhead(bulkhead_config)
        
        # Server task
        self._server_task: Optional[asyncio.Task] = None
        
        logger.info(f"ZmqSynthesisServer initialized: {bind_address}:{port}")
    
    def set_synthesis_handler(self, handler: Callable) -> None:
        """Set the synthesis handler function."""
        self.synthesis_handler = handler
        logger.info("Synthesis handler set")
    
    async def start(self) -> None:
        """Start the ZMQ synthesis server."""
        if self.is_running:
            logger.warning("Server already running")
            return
        
        if not self.synthesis_handler:
            raise ValueError("Synthesis handler must be set before starting server")
        
        try:
            # Create ZMQ context and socket
            self.context = zmq.asyncio.Context()
            self.socket = self.context.socket(zmq.REP)
            
            # Configure socket options
            self.socket.setsockopt(zmq.RCVTIMEO, self.request_timeout)
            self.socket.setsockopt(zmq.SNDTIMEO, self.request_timeout)
            self.socket.setsockopt(zmq.MAXMSGSIZE, self.max_request_size)
            self.socket.setsockopt(zmq.LINGER, 1000)
            
            # Bind to address
            bind_url = f"{self.bind_address}:{self.port}"
            self.socket.bind(bind_url)
            
            self.is_running = True
            self.is_serving = True
            self.stats['uptime_start'] = datetime.utcnow()
            
            # Start server task
            self._server_task = asyncio.create_task(self._server_loop())
            
            logger.info(f"ZMQ Synthesis Server started on {bind_url}")
            
        except Exception as e:
            logger.error(f"Failed to start ZMQ synthesis server: {e}")
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """Stop the ZMQ synthesis server."""
        if not self.is_running:
            return
        
        try:
            self.is_running = False
            self.is_serving = False
            
            # Cancel server task
            if self._server_task:
                self._server_task.cancel()
                try:
                    await self._server_task
                except asyncio.CancelledError:
                    pass
            
            # Close socket and context
            if self.socket:
                self.socket.close()
                self.socket = None
            
            if self.context:
                self.context.term()
                self.context = None
            
            logger.info("ZMQ Synthesis Server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping ZMQ synthesis server: {e}")
    
    async def _server_loop(self) -> None:
        """Main server loop for handling requests."""
        logger.info("Synthesis server loop started")
        
        while self.is_running and self.socket:
            try:
                # Wait for request
                request_data = await self.socket.recv_string()
                
                # Process request asynchronously
                asyncio.create_task(self._handle_request(request_data))
                
            except zmq.Again:
                # Timeout - continue loop
                continue
                
            except Exception as e:
                logger.error(f"Server loop error: {e}")
                # Send error response if possible
                try:
                    error_response = self._create_error_response(str(e))
                    await self.socket.send_string(json.dumps(error_response))
                except Exception:
                    pass
                
                await asyncio.sleep(0.1)
        
        logger.info("Synthesis server loop ended")
    
    async def _handle_request(self, request_data: str) -> None:
        """
        Handle a synthesis request.
        
        Args:
            request_data: JSON string containing the request
        """
        start_time = time.time()
        
        # Update statistics
        with self._lock:
            self.stats['requests_received'] += 1
            self.stats['bytes_received'] += len(request_data)
            self.stats['last_request_time'] = datetime.utcnow()
        
        try:
            # Parse request
            request_json = json.loads(request_data)
            synthesis_request = SynthesisRequest(**request_json)
            
            # Use bulkhead for resource protection
            async with self.bulkhead:
                # Use circuit breaker for fault tolerance
                response = await self.circuit_breaker.call(
                    self._process_synthesis_request, 
                    synthesis_request
                )
            
            # Send successful response
            response_json = json.dumps(response)
            await self.socket.send_string(response_json)
            
            # Update success statistics
            processing_time = (time.time() - start_time) * 1000
            with self._lock:
                self.stats['requests_processed'] += 1
                self.stats['bytes_sent'] += len(response_json)
                self._processing_times.append(processing_time)
                
                # Keep only recent processing times
                if len(self._processing_times) > 100:
                    self._processing_times = self._processing_times[-100:]
                
                # Update average processing time
                self.stats['avg_processing_time_ms'] = sum(self._processing_times) / len(self._processing_times)
            
            logger.debug(f"Synthesis request processed in {processing_time:.2f}ms")
            
        except Exception as e:
            # Handle error
            await self._handle_request_error(e, start_time)
    
    async def _process_synthesis_request(self, request: SynthesisRequest) -> Dict[str, Any]:
        """
        Process a synthesis request using the synthesis handler.
        
        Args:
            request: Synthesis request to process
            
        Returns:
            Response dictionary
        """
        if not self.synthesis_handler:
            raise ValueError("No synthesis handler available")
        
        # Call synthesis handler (should return SynthesisResponse or bytes)
        result = await self.synthesis_handler(request)
        
        if isinstance(result, bytes):
            # Raw audio bytes - wrap in response
            response = SynthesisResponse(
                audio_data=result,
                sample_rate=22050,
                duration_ms=len(result) // 44,  # Rough estimate
                processing_time_ms=0.0
            )
        elif hasattr(result, 'audio_data'):
            # Already a SynthesisResponse
            response = result
        else:
            raise ValueError(f"Invalid synthesis result type: {type(result)}")
        
        # Convert to serializable format
        return {
            'status': 'success',
            'audio_data_base64': base64.b64encode(response.audio_data).decode('utf-8'),
            'sample_rate': response.sample_rate,
            'duration_ms': response.duration_ms,
            'processing_time_ms': response.processing_time_ms,
            'metadata': {
                'emotion': request.emotion.value,
                'text_length': len(request.text),
                'intensity': request.intensity
            }
        }
    
    async def _handle_request_error(self, error: Exception, start_time: float) -> None:
        """Handle request processing errors."""
        processing_time = (time.time() - start_time) * 1000
        
        with self._lock:
            self.stats['requests_failed'] += 1
        
        logger.error(f"Synthesis request failed after {processing_time:.2f}ms: {error}")
        
        # Send error response
        try:
            error_response = self._create_error_response(str(error))
            response_json = json.dumps(error_response)
            await self.socket.send_string(response_json)
            
            with self._lock:
                self.stats['bytes_sent'] += len(response_json)
                
        except Exception as send_error:
            logger.error(f"Failed to send error response: {send_error}")
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create an error response dictionary."""
        return {
            'status': 'error',
            'error': error_message,
            'timestamp': datetime.utcnow().isoformat(),
            'audio_data_base64': '',
            'sample_rate': 0,
            'duration_ms': 0,
            'processing_time_ms': 0.0
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        with self._lock:
            stats = self.stats.copy()
        
        # Calculate uptime
        if stats['uptime_start']:
            uptime_seconds = (datetime.utcnow() - stats['uptime_start']).total_seconds()
            stats['uptime_seconds'] = uptime_seconds
        else:
            stats['uptime_seconds'] = 0
        
        # Calculate rates
        if stats['uptime_seconds'] > 0:
            stats['requests_per_second'] = stats['requests_received'] / stats['uptime_seconds']
            stats['bytes_per_second_in'] = stats['bytes_received'] / stats['uptime_seconds']
            stats['bytes_per_second_out'] = stats['bytes_sent'] / stats['uptime_seconds']
        else:
            stats['requests_per_second'] = 0
            stats['bytes_per_second_in'] = 0
            stats['bytes_per_second_out'] = 0
        
        # Calculate success rate
        if stats['requests_received'] > 0:
            stats['success_rate'] = stats['requests_processed'] / stats['requests_received']
        else:
            stats['success_rate'] = 0
        
        # Add server info
        stats.update({
            'is_running': self.is_running,
            'is_serving': self.is_serving,
            'port': self.port,
            'bind_address': self.bind_address,
            'circuit_breaker_state': str(self.circuit_breaker._state),
            'bulkhead_usage': f"{getattr(self.bulkhead, 'current_tasks', 0)}/{self.bulkhead.config.max_concurrent}"
        })
        
        return stats
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get server health status."""
        stats = self.get_stats()
        
        # Determine health status
        is_healthy = (
            self.is_running and 
            self.is_serving and
            self.circuit_breaker._state.name != 'OPEN' and
            stats['success_rate'] > 0.8
        )
        
        return {
            'status': 'healthy' if is_healthy else 'degraded',
            'is_running': self.is_running,
            'is_serving': self.is_serving,
            'circuit_breaker_state': str(self.circuit_breaker._state),
            'success_rate': stats['success_rate'],
            'requests_per_second': stats['requests_per_second'],
            'avg_processing_time_ms': stats['avg_processing_time_ms'],
            'uptime_seconds': stats['uptime_seconds']
        }
    
    async def test_synthesis(self, test_text: str = "Hello world") -> Dict[str, Any]:
        """
        Test the synthesis functionality.
        
        Args:
            test_text: Text to synthesize for testing
            
        Returns:
            Test result dictionary
        """
        if not self.synthesis_handler:
            return {
                'success': False,
                'error': 'No synthesis handler available'
            }
        
        try:
            # Create test request
            test_request = SynthesisRequest(
                text=test_text,
                emotion=EmotionType.NEUTRAL,
                intensity=1.0
            )
            
            # Process synthesis
            start_time = time.time()
            response = await self._process_synthesis_request(test_request)
            processing_time = (time.time() - start_time) * 1000
            
            return {
                'success': True,
                'processing_time_ms': processing_time,
                'audio_size_bytes': len(base64.b64decode(response['audio_data_base64'])),
                'sample_rate': response['sample_rate'],
                'duration_ms': response['duration_ms']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()


class SynthesisRequestHandler:
    """
    Handler for synthesis requests that coordinates with synthesis modules.
    """
    
    def __init__(self, synthesis_module):
        """
        Initialize with a synthesis module.
        
        Args:
            synthesis_module: Module that can perform synthesis
        """
        self.synthesis_module = synthesis_module
        self.request_count = 0
        self._lock = threading.Lock()
    
    async def handle_request(self, request: SynthesisRequest) -> SynthesisResponse:
        """
        Handle a synthesis request.
        
        Args:
            request: Synthesis request to process
            
        Returns:
            Synthesis response with audio data
        """
        with self._lock:
            self.request_count += 1
        
        start_time = time.time()
        
        try:
            # Use synthesis module to generate audio
            if hasattr(self.synthesis_module, 'synthesize_emotion'):
                audio_data = await self.synthesis_module.synthesize_emotion(request)
            else:
                # Fallback to generic synthesis
                audio_data = await self._synthesize_fallback(request)
            
            processing_time = (time.time() - start_time) * 1000
            
            # Calculate audio properties
            sample_rate = 22050
            duration_ms = len(audio_data) // (sample_rate * 2 // 1000)  # 16-bit audio
            
            return SynthesisResponse(
                audio_data=audio_data,
                sample_rate=sample_rate,
                duration_ms=duration_ms,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Synthesis request handling failed: {e}")
            raise
    
    async def _synthesize_fallback(self, request: SynthesisRequest) -> bytes:
        """
        Fallback synthesis implementation.
        
        Args:
            request: Synthesis request
            
        Returns:
            Generated audio bytes
        """
        # Simple tone generation based on emotion
        import numpy as np
        
        sample_rate = 22050
        duration_seconds = min(len(request.text) * 0.1, 5.0)  # Max 5 seconds
        samples = int(duration_seconds * sample_rate)
        
        # Generate tone based on emotion
        emotion_frequencies = {
            EmotionType.HAPPY: 440.0,
            EmotionType.SAD: 220.0,
            EmotionType.ANGRY: 550.0,
            EmotionType.FEARFUL: 330.0,
            EmotionType.SURPRISED: 660.0,
            EmotionType.DISGUSTED: 200.0,
            EmotionType.NEUTRAL: 400.0
        }
        
        frequency = emotion_frequencies.get(request.emotion, 400.0)
        frequency *= request.intensity  # Apply intensity
        
        # Generate sine wave
        t = np.linspace(0, duration_seconds, samples)
        audio_signal = np.sin(2 * np.pi * frequency * t)
        
        # Add some modulation for more natural sound
        modulation = np.sin(2 * np.pi * 5 * t) * 0.1
        audio_signal = audio_signal * (1 + modulation)
        
        # Convert to 16-bit PCM
        audio_signal = (audio_signal * 32767).astype(np.int16)
        
        return audio_signal.tobytes()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics."""
        with self._lock:
            return {
                'total_requests': self.request_count,
                'synthesis_module': type(self.synthesis_module).__name__
            }