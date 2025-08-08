"""
Real-Time Audio Pipeline - ZeroMQ Publisher

High-performance ZMQ PUB sockets for real-time event and transcript broadcasting.
Optimized for ultra-low latency (≤150ms p95) with efficient async operation.
"""

import asyncio
import logging
import time
from typing import Any, AsyncGenerator, Dict, Optional

import zmq
import zmq.asyncio

from .schemas import (
    EventNotification,
    EventTypes,
    TranscriptEvent,
    create_event_notification,
    serialize_for_zmq,
)


class ZmqPublisher:
    """
    High-performance ZeroMQ publisher for RTAP events and transcripts.

    Manages dual PUB sockets for broadcasting:
    - Port 6552: System events (wake word, errors, status changes)
    - Port 6553: Transcript results (primary output for downstream agents)

    Key Features:
    - Async operation for minimal latency impact
    - Efficient JSON serialization optimized for network transmission
    - Connection monitoring and error recovery
    - Performance metrics and health tracking
    - Graceful shutdown with message queue flushing
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize ZMQ publisher with configuration.

        Args:
            config: Pipeline configuration containing output ports
        """
        self.config = config
        self.output_config = config['output']
        self.logger = logging.getLogger(__name__)

        # ZMQ configuration
        self.events_port = self.output_config['zmq_pub_port_events']
        self.transcripts_port = self.output_config['zmq_pub_port_transcripts']

        # ZMQ context and sockets
        self.context: Optional[zmq.asyncio.Context] = None
        self.events_socket: Optional[zmq.asyncio.Socket] = None
        self.transcripts_socket: Optional[zmq.asyncio.Socket] = None

        # State management
        self.is_running = False
        self.is_connected = False
        self.session_id = None

        # Performance tracking
        self.events_published = 0
        self.transcripts_published = 0
        self.total_bytes_sent = 0
        self.start_time = 0.0
        self.last_publish_time = 0.0

        # Error tracking
        self.publish_errors = 0
        self.connection_errors = 0

        # Message queues for graceful shutdown
        self.pending_events = asyncio.Queue(maxsize=100)
        self.pending_transcripts = asyncio.Queue(maxsize=50)

        self.logger.info(f"ZmqPublisher initialized: events={self.events_port}, "
                        f"transcripts={self.transcripts_port}")

    async def start(self) -> None:
        """
        Start the ZMQ publisher and establish socket connections.
        """
        try:
            self.logger.info("Starting ZMQ publisher...")
            self.start_time = time.perf_counter()

            # Initialize ZMQ context with optimal settings
            self.context = zmq.asyncio.Context()

            # Configure context for low-latency operation
            self.context.setsockopt(zmq.MAX_SOCKETS, 1024)
            self.context.setsockopt(zmq.IO_THREADS, 2)

            # Create and configure sockets
            await self._create_sockets()

            # Start publishing tasks
            self.is_running = True

            # Create background tasks for message processing
            events_task = asyncio.create_task(self._events_publisher_loop())
            transcripts_task = asyncio.create_task(self._transcripts_publisher_loop())

            self.logger.info(f"ZMQ publisher started: events=tcp://*:{self.events_port}, "
                           f"transcripts=tcp://*:{self.transcripts_port}")

            # Wait for shutdown
            try:
                await asyncio.gather(events_task, transcripts_task)
            except asyncio.CancelledError:
                self.logger.info("ZMQ publisher tasks cancelled")

        except Exception as e:
            self.logger.error(f"Failed to start ZMQ publisher: {e}")
            await self._emergency_cleanup()
            raise

    async def _create_sockets(self) -> None:
        """Create and configure ZMQ PUB sockets."""
        try:
            # Events socket (port 6552)
            self.events_socket = self.context.socket(zmq.PUB)
            self.events_socket.setsockopt(zmq.SNDHWM, 1000)  # Send high water mark
            self.events_socket.setsockopt(zmq.LINGER, 1000)  # Linger on close
            self.events_socket.setsockopt(zmq.IMMEDIATE, 1)  # Don't queue if no peers
            self.events_socket.bind(f"tcp://*:{self.events_port}")

            # Transcripts socket (port 6553)
            self.transcripts_socket = self.context.socket(zmq.PUB)
            self.transcripts_socket.setsockopt(zmq.SNDHWM, 1000)
            self.transcripts_socket.setsockopt(zmq.LINGER, 1000)
            self.transcripts_socket.setsockopt(zmq.IMMEDIATE, 1)
            self.transcripts_socket.bind(f"tcp://*:{self.transcripts_port}")

            # Brief settle time for socket binding
            await asyncio.sleep(0.1)

            self.is_connected = True
            self.logger.info("ZMQ sockets created and bound successfully")

        except Exception as e:
            self.logger.error(f"Failed to create ZMQ sockets: {e}")
            self.connection_errors += 1
            raise

    async def _events_publisher_loop(self) -> None:
        """Background loop for publishing events."""
        self.logger.info("Events publisher loop started")

        try:
            while self.is_running:
                try:
                    # Wait for event with timeout
                    event = await asyncio.wait_for(
                        self.pending_events.get(),
                        timeout=1.0
                    )

                    # Publish event
                    await self._publish_event_internal(event)

                except asyncio.TimeoutError:
                    # No events to publish, continue
                    continue
                except Exception as e:
                    self.logger.error(f"Error in events publisher loop: {e}")
                    self.publish_errors += 1
                    await asyncio.sleep(0.1)  # Brief pause on error

        except asyncio.CancelledError:
            self.logger.info("Events publisher loop cancelled")
        except Exception as e:
            self.logger.error(f"Fatal error in events publisher loop: {e}")

    async def _transcripts_publisher_loop(self) -> None:
        """Background loop for publishing transcripts."""
        self.logger.info("Transcripts publisher loop started")

        try:
            while self.is_running:
                try:
                    # Wait for transcript with timeout
                    transcript = await asyncio.wait_for(
                        self.pending_transcripts.get(),
                        timeout=1.0
                    )

                    # Publish transcript
                    await self._publish_transcript_internal(transcript)

                except asyncio.TimeoutError:
                    # No transcripts to publish, continue
                    continue
                except Exception as e:
                    self.logger.error(f"Error in transcripts publisher loop: {e}")
                    self.publish_errors += 1
                    await asyncio.sleep(0.1)  # Brief pause on error

        except asyncio.CancelledError:
            self.logger.info("Transcripts publisher loop cancelled")
        except Exception as e:
            self.logger.error(f"Fatal error in transcripts publisher loop: {e}")

    async def publish_event(self, event: EventNotification) -> bool:
        """
        Queue an event for publication.

        Args:
            event: Event notification to publish

        Returns:
            True if queued successfully, False if queue is full
        """
        if not self.is_running or not self.is_connected:
            self.logger.warning("Cannot publish event: publisher not running or connected")
            return False

        try:
            # Try to queue event (non-blocking)
            self.pending_events.put_nowait(event)
            return True
        except asyncio.QueueFull:
            self.logger.warning("Events queue full, dropping event")
            return False

    async def publish_transcript(self, transcript: TranscriptEvent) -> bool:
        """
        Queue a transcript for publication.

        Args:
            transcript: Transcript event to publish

        Returns:
            True if queued successfully, False if queue is full
        """
        if not self.is_running or not self.is_connected:
            self.logger.warning("Cannot publish transcript: publisher not running or connected")
            return False

        try:
            # Try to queue transcript (non-blocking)
            self.pending_transcripts.put_nowait(transcript)
            return True
        except asyncio.QueueFull:
            self.logger.warning("Transcripts queue full, dropping transcript")
            return False

    async def _publish_event_internal(self, event: EventNotification) -> None:
        """Internal method to publish event to ZMQ socket."""
        try:
            # Serialize event to JSON bytes
            event_data = serialize_for_zmq(event)

            # Publish with topic for filtering
            topic = f"event.{event.event_type}".encode()
            await self.events_socket.send_multipart([topic, event_data])

            # Update metrics
            self.events_published += 1
            self.total_bytes_sent += len(event_data)
            self.last_publish_time = time.perf_counter()

        except Exception as e:
            self.logger.error(f"Failed to publish event: {e}")
            self.publish_errors += 1
            raise

    async def _publish_transcript_internal(self, transcript: TranscriptEvent) -> None:
        """Internal method to publish transcript to ZMQ socket."""
        try:
            # Serialize transcript to JSON bytes
            transcript_data = serialize_for_zmq(transcript)

            # Publish with topic for filtering
            topic = f"transcript.{transcript.language}".encode()
            await self.transcripts_socket.send_multipart([topic, transcript_data])

            # Update metrics
            self.transcripts_published += 1
            self.total_bytes_sent += len(transcript_data)
            self.last_publish_time = time.perf_counter()

            # Log transcript for debugging (limited)
            if self.transcripts_published % 10 == 0:
                self.logger.debug(f"Published transcript #{self.transcripts_published}: "
                                f"{transcript.transcript[:50]}...")

        except Exception as e:
            self.logger.error(f"Failed to publish transcript: {e}")
            self.publish_errors += 1
            raise

    async def consume_pipeline_output(self, output_stream: AsyncGenerator[Dict[str, Any], None]) -> None:
        """
        Consume pipeline output stream and publish to appropriate channels.

        Args:
            output_stream: Async generator from pipeline providing output data
        """
        self.logger.info("Starting pipeline output consumption")

        try:
            async for output_data in output_stream:
                try:
                    # Create transcript event from pipeline output
                    transcript = TranscriptEvent(
                        transcript=output_data.get('transcript', ''),
                        confidence=output_data.get('confidence', 0.0),
                        processing_time_ms=output_data.get('processing_time_ms', 0),
                        audio_duration_ms=output_data.get('audio_duration_ms', 0),
                        sequence_number=self.transcripts_published + 1,
                        language=output_data.get('language', 'unknown'),
                        language_confidence=output_data.get('language_confidence', 0.0),
                        sentiment=output_data.get('sentiment', 'neutral'),
                        sentiment_confidence=output_data.get('sentiment_confidence', 0.0),
                        session_id=self.session_id,
                        stage_latencies=output_data.get('stage_latencies')
                    )

                    # Queue transcript for publication
                    success = await self.publish_transcript(transcript)

                    if success:
                        # Also publish a transcript ready event
                        event = create_event_notification(
                            event_type=EventTypes.TRANSCRIPT_READY,
                            metadata={
                                'transcript_length': len(transcript.transcript),
                                'confidence': transcript.confidence,
                                'language': transcript.language,
                                'processing_time_ms': transcript.processing_time_ms
                            },
                            session_id=self.session_id
                        )
                        await self.publish_event(event)

                except Exception as e:
                    self.logger.error(f"Error processing pipeline output: {e}")

                    # Publish error event
                    error_event = create_event_notification(
                        event_type=EventTypes.ERROR_OCCURRED,
                        metadata={
                            'error_type': 'output_processing_error',
                            'error_message': str(e)
                        },
                        level='error',
                        session_id=self.session_id
                    )
                    await self.publish_event(error_event)

        except asyncio.CancelledError:
            self.logger.info("Pipeline output consumption cancelled")
        except Exception as e:
            self.logger.error(f"Fatal error in pipeline output consumption: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive publisher statistics."""
        uptime = time.perf_counter() - self.start_time if self.start_time > 0 else 0

        return {
            'is_running': self.is_running,
            'is_connected': self.is_connected,
            'uptime_seconds': uptime,
            'events_published': self.events_published,
            'transcripts_published': self.transcripts_published,
            'total_bytes_sent': self.total_bytes_sent,
            'publish_errors': self.publish_errors,
            'connection_errors': self.connection_errors,
            'events_queue_size': self.pending_events.qsize(),
            'transcripts_queue_size': self.pending_transcripts.qsize(),
            'last_publish_time': self.last_publish_time,
            'events_port': self.events_port,
            'transcripts_port': self.transcripts_port,
        }

    async def publish_system_event(self, event_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Convenience method to publish system events.

        Args:
            event_type: Type of event (use EventTypes constants)
            metadata: Optional event metadata

        Returns:
            True if published successfully
        """
        event = create_event_notification(
            event_type=event_type,
            metadata=metadata or {},
            session_id=self.session_id
        )
        return await self.publish_event(event)

    async def shutdown(self) -> None:
        """Gracefully shutdown the ZMQ publisher."""
        self.logger.info("Shutting down ZMQ publisher...")

        # Stop accepting new messages
        self.is_running = False

        # Flush pending messages with timeout
        try:
            flush_timeout = 2.0
            start_time = time.perf_counter()

            while (self.pending_events.qsize() > 0 or self.pending_transcripts.qsize() > 0):
                if time.perf_counter() - start_time > flush_timeout:
                    self.logger.warning("Timeout flushing pending messages")
                    break
                await asyncio.sleep(0.1)

        except Exception as e:
            self.logger.error(f"Error flushing pending messages: {e}")

        # Close sockets and context
        await self._cleanup_sockets()

        # Log final statistics
        stats = self.get_stats()
        self.logger.info(f"ZMQ publisher shutdown complete. "
                        f"Published: {stats['events_published']} events, "
                        f"{stats['transcripts_published']} transcripts, "
                        f"{stats['total_bytes_sent']} bytes")

    async def _cleanup_sockets(self) -> None:
        """Clean up ZMQ sockets and context."""
        try:
            if self.events_socket:
                self.events_socket.close()
                self.events_socket = None

            if self.transcripts_socket:
                self.transcripts_socket.close()
                self.transcripts_socket = None

            if self.context:
                self.context.term()
                self.context = None

            self.is_connected = False
            self.logger.info("ZMQ sockets and context cleaned up")

        except Exception as e:
            self.logger.error(f"Error cleaning up ZMQ resources: {e}")

    async def _emergency_cleanup(self) -> None:
        """Emergency cleanup for critical errors."""
        self.logger.error("Emergency ZMQ cleanup initiated")
        self.is_running = False
        self.is_connected = False

        try:
            await self._cleanup_sockets()
        except Exception as e:
            self.logger.error(f"Error in emergency cleanup: {e}")

    def set_session_id(self, session_id: str) -> None:
        """Set session ID for all published messages."""
        self.session_id = session_id
        self.logger.info(f"ZMQ publisher session ID set: {session_id}")

    def __repr__(self) -> str:
        """String representation of publisher state."""
        return (f"ZmqPublisher(running={self.is_running}, connected={self.is_connected}, "
                f"events={self.events_published}, transcripts={self.transcripts_published})")
