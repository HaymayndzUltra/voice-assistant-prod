"""ZeroMQ publisher for broadcasting Emotional Context Vectors (ECV)."""

import zmq
import zmq.asyncio
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
import threading
from dataclasses import asdict

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schemas import EmotionalContext, EmotionType

logger = logging.getLogger(__name__)


class ZmqPublisher:
    """
    ZeroMQ publisher for broadcasting Emotional Context Vectors.
    
    This class manages a PUB socket that broadcasts ECV results to
    downstream consumers in real-time.
    """
    
    def __init__(
        self, 
        port: int = 5591, 
        topic: str = "affect",
        bind_address: str = "tcp://*",
        high_water_mark: int = 1000
    ):
        """
        Initialize ZMQ publisher.
        
        Args:
            port: Port number to bind to
            topic: Topic prefix for published messages
            bind_address: Address pattern to bind to
            high_water_mark: Maximum number of queued messages
        """
        self.port = port
        self.topic = topic
        self.bind_address = bind_address
        self.high_water_mark = high_water_mark
        
        # ZMQ components
        self.context: Optional[zmq.asyncio.Context] = None
        self.socket: Optional[zmq.asyncio.Socket] = None
        
        # State tracking
        self.is_running = False
        self.is_connected = False
        
        # Statistics
        self.stats = {
            'messages_published': 0,
            'bytes_published': 0,
            'publish_errors': 0,
            'last_publish_time': None,
            'uptime_start': None
        }
        
        # Thread safety
        self._lock = threading.Lock()
        
        logger.info(f"ZmqPublisher initialized: {bind_address}:{port} topic='{topic}'")
    
    async def start(self) -> None:
        """Start the ZMQ publisher."""
        if self.is_running:
            logger.warning("Publisher already running")
            return
        
        try:
            # Create ZMQ context and socket
            self.context = zmq.asyncio.Context()
            self.socket = self.context.socket(zmq.PUB)
            
            # Configure socket options
            self.socket.setsockopt(zmq.SNDHWM, self.high_water_mark)
            self.socket.setsockopt(zmq.LINGER, 1000)  # 1 second linger
            
            # Bind to address
            bind_url = f"{self.bind_address}:{self.port}"
            self.socket.bind(bind_url)
            
            self.is_running = True
            self.is_connected = True
            self.stats['uptime_start'] = datetime.utcnow()
            
            logger.info(f"ZMQ Publisher started on {bind_url}")
            
            # Small delay to allow socket to establish
            await asyncio.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Failed to start ZMQ publisher: {e}")
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """Stop the ZMQ publisher."""
        if not self.is_running:
            return
        
        try:
            self.is_running = False
            self.is_connected = False
            
            if self.socket:
                self.socket.close()
                self.socket = None
            
            if self.context:
                self.context.term()
                self.context = None
            
            logger.info("ZMQ Publisher stopped")
            
        except Exception as e:
            logger.error(f"Error stopping ZMQ publisher: {e}")
    
    async def publish_ecv(self, emotional_context: EmotionalContext) -> bool:
        """
        Publish an Emotional Context Vector.
        
        Args:
            emotional_context: ECV to publish
            
        Returns:
            True if published successfully, False otherwise
        """
        if not self.is_running or not self.socket:
            logger.warning("Publisher not running, cannot publish ECV")
            return False
        
        try:
            # Convert to publishable format
            message_data = self._serialize_ecv(emotional_context)
            
            # Create topic message
            topic_bytes = self.topic.encode('utf-8')
            message_bytes = json.dumps(message_data).encode('utf-8')
            
            # Publish multipart message: [topic, data]
            await self.socket.send_multipart([topic_bytes, message_bytes])
            
            # Update statistics
            with self._lock:
                self.stats['messages_published'] += 1
                self.stats['bytes_published'] += len(topic_bytes) + len(message_bytes)
                self.stats['last_publish_time'] = datetime.utcnow()
            
            logger.debug(f"Published ECV: emotion={emotional_context.primary_emotion.value}, "
                        f"confidence={emotional_context.emotion_confidence:.3f}")
            
            return True
            
        except Exception as e:
            with self._lock:
                self.stats['publish_errors'] += 1
            
            logger.error(f"Failed to publish ECV: {e}")
            return False
    
    def _serialize_ecv(self, emotional_context: EmotionalContext) -> Dict[str, Any]:
        """
        Serialize EmotionalContext to publishable format.
        
        Args:
            emotional_context: ECV to serialize
            
        Returns:
            Serializable dictionary
        """
        return {
            'version': '1.0',
            'timestamp': emotional_context.timestamp.isoformat(),
            'emotion_vector': emotional_context.emotion_vector,
            'primary_emotion': emotional_context.primary_emotion.value,
            'emotion_confidence': emotional_context.emotion_confidence,
            'valence': emotional_context.valence,
            'arousal': emotional_context.arousal,
            'module_contributions': emotional_context.module_contributions,
            'processing_latency_ms': emotional_context.processing_latency_ms,
            'metadata': {
                'source': 'affective_processing_center',
                'vector_dim': len(emotional_context.emotion_vector),
                'contributing_modules': list(emotional_context.module_contributions.keys())
            }
        }
    
    async def publish_heartbeat(self) -> bool:
        """
        Publish a heartbeat message to indicate service health.
        
        Returns:
            True if published successfully
        """
        if not self.is_running or not self.socket:
            return False
        
        try:
            heartbeat_data = {
                'type': 'heartbeat',
                'timestamp': datetime.utcnow().isoformat(),
                'stats': self.get_stats(),
                'status': 'healthy' if self.is_connected else 'degraded'
            }
            
            topic_bytes = f"{self.topic}.heartbeat".encode('utf-8')
            message_bytes = json.dumps(heartbeat_data).encode('utf-8')
            
            await self.socket.send_multipart([topic_bytes, message_bytes])
            
            logger.debug("Published heartbeat")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish heartbeat: {e}")
            return False
    
    async def publish_batch(self, emotional_contexts: List[EmotionalContext]) -> int:
        """
        Publish a batch of ECVs efficiently.
        
        Args:
            emotional_contexts: List of ECVs to publish
            
        Returns:
            Number of successfully published ECVs
        """
        if not emotional_contexts:
            return 0
        
        successful_count = 0
        
        for ecv in emotional_contexts:
            if await self.publish_ecv(ecv):
                successful_count += 1
            else:
                logger.warning("Failed to publish ECV in batch")
        
        logger.debug(f"Published batch: {successful_count}/{len(emotional_contexts)} ECVs")
        return successful_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get publisher statistics."""
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
            stats['messages_per_second'] = stats['messages_published'] / stats['uptime_seconds']
            stats['bytes_per_second'] = stats['bytes_published'] / stats['uptime_seconds']
        else:
            stats['messages_per_second'] = 0
            stats['bytes_per_second'] = 0
        
        # Add connection info
        stats.update({
            'is_running': self.is_running,
            'is_connected': self.is_connected,
            'port': self.port,
            'topic': self.topic,
            'bind_address': self.bind_address
        })
        
        return stats
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for diagnostics."""
        return {
            'publisher': {
                'address': f"{self.bind_address}:{self.port}",
                'topic': self.topic,
                'status': 'connected' if self.is_connected else 'disconnected',
                'high_water_mark': self.high_water_mark
            },
            'subscribers': {
                'note': 'ZMQ PUB sockets do not track subscriber count',
                'connection_pattern': 'tcp://localhost:5591 (or remote IP)',
                'subscription_pattern': f'{self.topic}.*'
            }
        }
    
    async def test_connection(self) -> bool:
        """
        Test the publisher connection.
        
        Returns:
            True if connection is healthy
        """
        if not self.is_running:
            return False
        
        try:
            # Publish a test message
            test_data = {
                'type': 'connection_test',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            topic_bytes = f"{self.topic}.test".encode('utf-8')
            message_bytes = json.dumps(test_data).encode('utf-8')
            
            await self.socket.send_multipart([topic_bytes, message_bytes])
            
            logger.debug("Connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            self.is_connected = False
            return False
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()


class BroadcastManager:
    """
    Higher-level manager for coordinating ECV broadcasts.
    
    This class provides additional features like batching, rate limiting,
    and multiple topic management.
    """
    
    def __init__(self, publishers: List[ZmqPublisher]):
        """Initialize with multiple publishers."""
        self.publishers = publishers
        self.broadcast_queue = asyncio.Queue(maxsize=1000)
        self.is_running = False
        self._broadcast_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start all publishers and the broadcast manager."""
        # Start all publishers
        for publisher in self.publishers:
            await publisher.start()
        
        # Start broadcast task
        self.is_running = True
        self._broadcast_task = asyncio.create_task(self._broadcast_worker())
        
        logger.info(f"BroadcastManager started with {len(self.publishers)} publishers")
    
    async def stop(self) -> None:
        """Stop all publishers and the broadcast manager."""
        self.is_running = False
        
        # Cancel broadcast task
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        
        # Stop all publishers
        for publisher in self.publishers:
            await publisher.stop()
        
        logger.info("BroadcastManager stopped")
    
    async def queue_for_broadcast(self, emotional_context: EmotionalContext) -> bool:
        """Queue an ECV for broadcast."""
        try:
            self.broadcast_queue.put_nowait(emotional_context)
            return True
        except asyncio.QueueFull:
            logger.warning("Broadcast queue full, dropping ECV")
            return False
    
    async def _broadcast_worker(self) -> None:
        """Background worker for broadcasting queued ECVs."""
        while self.is_running:
            try:
                # Wait for ECV with timeout
                ecv = await asyncio.wait_for(
                    self.broadcast_queue.get(), 
                    timeout=1.0
                )
                
                # Broadcast to all publishers
                for publisher in self.publishers:
                    await publisher.publish_ecv(ecv)
                
            except asyncio.TimeoutError:
                # Periodic heartbeat when no ECVs
                for publisher in self.publishers:
                    await publisher.publish_heartbeat()
                    
            except Exception as e:
                logger.error(f"Broadcast worker error: {e}")
                await asyncio.sleep(0.1)
    
    def get_aggregate_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics from all publishers."""
        total_stats = {
            'total_messages': 0,
            'total_bytes': 0,
            'total_errors': 0,
            'publishers': []
        }
        
        for i, publisher in enumerate(self.publishers):
            stats = publisher.get_stats()
            total_stats['total_messages'] += stats['messages_published']
            total_stats['total_bytes'] += stats['bytes_published']
            total_stats['total_errors'] += stats['publish_errors']
            total_stats['publishers'].append({
                'index': i,
                'topic': publisher.topic,
                'port': publisher.port,
                'stats': stats
            })
        
        return total_stats