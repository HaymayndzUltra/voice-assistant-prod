"""
Real-Time Audio Pipeline - Transport Schemas

Pydantic models for consistent JSON structure across ZMQ and WebSocket transports.
Optimized for low-latency serialization and efficient network transmission.
"""

import time
import uuid
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TranscriptEvent(BaseModel):
    """
    Primary transcript event schema for real-time audio processing results.

    This model represents the complete output of the RTAP pipeline, including
    the transcribed text, confidence scores, language analysis, and performance
    metadata. Designed for efficient JSON serialization and network transmission.
    """

    # Core transcript data
    transcript: str = Field(..., description="Transcribed text from speech recognition")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall transcript confidence (0-1)")

    # Timing information (critical for latency tracking)
    timestamp: float = Field(default_factory=time.time, description="Event timestamp (Unix epoch)")
    audio_start_time: Optional[float] = Field(None, description="Audio segment start time")
    audio_end_time: Optional[float] = Field(None, description="Audio segment end time")
    processing_time_ms: int = Field(..., description="Total processing time in milliseconds")

    # Language analysis results
    language: str = Field(default="unknown", description="Detected language code (ISO 639-1)")
    language_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Language detection confidence")
    sentiment: str = Field(default="neutral", description="Sentiment analysis result")
    sentiment_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Sentiment confidence")

    # Technical metadata
    pipeline_version: str = Field(default="1.0", description="RTAP pipeline version")
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique session identifier")
    sequence_number: int = Field(..., description="Sequential message number within session")

    # Audio characteristics
    sample_rate: int = Field(default=16000, description="Audio sample rate in Hz")
    channels: int = Field(default=1, description="Number of audio channels")
    audio_duration_ms: float = Field(..., description="Audio segment duration in milliseconds")

    # Performance monitoring (optional for detailed analysis)
    stage_latencies: Optional[Dict[str, float]] = Field(
        None,
        description="Per-stage processing latencies in milliseconds"
    )

    class Config:
        """Pydantic configuration for optimal JSON serialization."""
        # Enable fast JSON serialization
        json_encoders = {
            float: lambda v: round(v, 3),  # Limit float precision for network efficiency
        }
        # Allow population by field name for API compatibility
        allow_population_by_field_name = True
        # Validate assignment to catch runtime errors
        validate_assignment = True


class EventNotification(BaseModel):
    """
    System event notification schema for pipeline state changes and alerts.

    Used for broadcasting non-transcript events like wake word detections,
    processing state changes, errors, and system health notifications.
    """

    # Event classification
    event_type: str = Field(..., description="Event type (wake_word_detected, processing_started, error_occurred, etc.)")
    timestamp: float = Field(default_factory=time.time, description="Event timestamp (Unix epoch)")

    # Event data
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event-specific metadata")
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Session identifier")

    # Severity and routing
    level: str = Field(default="info", description="Event level (debug, info, warning, error, critical)")
    source: str = Field(default="rtap", description="Event source component")

    class Config:
        """Pydantic configuration for event serialization."""
        json_encoders = {
            float: lambda v: round(v, 3),
        }
        allow_population_by_field_name = True


class WebSocketMessage(BaseModel):
    """
    WebSocket message wrapper for browser clients.

    Provides a consistent envelope for different message types sent over
    WebSocket connections, enabling proper client-side routing and handling.
    """

    # Message routing
    message_type: str = Field(..., description="Message type (transcript, event, status, error)")
    timestamp: float = Field(default_factory=time.time, description="Message timestamp")

    # Payload (one of the following will be populated)
    transcript: Optional[TranscriptEvent] = Field(None, description="Transcript event payload")
    event: Optional[EventNotification] = Field(None, description="System event payload")
    status: Optional[Dict[str, Any]] = Field(None, description="Status information payload")
    error: Optional[Dict[str, str]] = Field(None, description="Error information payload")

    # Client metadata
    client_id: Optional[str] = Field(None, description="Client connection identifier")

    class Config:
        """WebSocket message configuration."""
        json_encoders = {
            float: lambda v: round(v, 3),
        }


class PipelineStatus(BaseModel):
    """
    Pipeline health and status information schema.

    Used for health checks, monitoring dashboards, and diagnostic endpoints.
    Provides comprehensive view of pipeline performance and state.
    """

    # Operational status
    state: str = Field(..., description="Current pipeline state")
    uptime_seconds: float = Field(..., description="Pipeline uptime in seconds")
    is_healthy: bool = Field(..., description="Overall health status")

    # Performance metrics
    frames_processed: int = Field(default=0, description="Total frames processed")
    transcripts_completed: int = Field(default=0, description="Total transcripts completed")
    average_latency_ms: float = Field(default=0.0, description="Average end-to-end latency")

    # Buffer and queue status
    buffer_utilization: float = Field(default=0.0, ge=0.0, le=1.0, description="Audio buffer utilization ratio")
    queue_sizes: Dict[str, int] = Field(default_factory=dict, description="Inter-stage queue sizes")

    # Error tracking
    total_errors: int = Field(default=0, description="Total error count")
    error_rate_per_hour: float = Field(default=0.0, description="Error rate per hour")

    # System resources
    cpu_usage_percent: Optional[float] = Field(None, description="CPU usage percentage")
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")

    # Timestamps
    last_transcript_time: Optional[float] = Field(None, description="Last transcript timestamp")
    status_timestamp: float = Field(default_factory=time.time, description="Status generation timestamp")

    class Config:
        """Pipeline status configuration."""
        json_encoders = {
            float: lambda v: round(v, 2),
        }


# Utility functions for schema operations

def create_transcript_event(
    transcript: str,
    confidence: float,
    processing_time_ms: int,
    audio_duration_ms: float,
    sequence_number: int,
    session_id: Optional[str] = None,
    **kwargs
) -> TranscriptEvent:
    """
    Factory function for creating transcript events with sensible defaults.

    Args:
        transcript: The transcribed text
        confidence: Transcript confidence (0-1)
        processing_time_ms: Total processing time
        audio_duration_ms: Audio segment duration
        sequence_number: Message sequence number
        session_id: Optional session ID (generates UUID if None)
        **kwargs: Additional optional fields

    Returns:
        Configured TranscriptEvent instance
    """
    return TranscriptEvent(
        transcript=transcript,
        confidence=confidence,
        processing_time_ms=processing_time_ms,
        audio_duration_ms=audio_duration_ms,
        sequence_number=sequence_number,
        session_id=session_id or str(uuid.uuid4()),
        **kwargs
    )


def create_event_notification(
    event_type: str,
    metadata: Optional[Dict[str, Any]] = None,
    level: str = "info",
    session_id: Optional[str] = None
) -> EventNotification:
    """
    Factory function for creating system event notifications.

    Args:
        event_type: Type of event (e.g., 'wake_word_detected')
        metadata: Optional event-specific data
        level: Event severity level
        session_id: Optional session ID

    Returns:
        Configured EventNotification instance
    """
    return EventNotification(
        event_type=event_type,
        metadata=metadata or {},
        level=level,
        session_id=session_id or str(uuid.uuid4())
    )


def create_websocket_message(
    message_type: str,
    payload: Any,
    client_id: Optional[str] = None
) -> WebSocketMessage:
    """
    Factory function for creating WebSocket messages.

    Args:
        message_type: Type of message ('transcript', 'event', 'status', 'error')
        payload: Message payload (TranscriptEvent, EventNotification, etc.)
        client_id: Optional client identifier

    Returns:
        Configured WebSocketMessage instance
    """
    message_data = {"message_type": message_type, "client_id": client_id}

    if message_type == "transcript" and isinstance(payload, TranscriptEvent):
        message_data["transcript"] = payload
    elif message_type == "event" and isinstance(payload, EventNotification):
        message_data["event"] = payload
    elif message_type == "status":
        message_data["status"] = payload
    elif message_type == "error":
        message_data["error"] = payload
    else:
        raise ValueError(f"Invalid message_type '{message_type}' or payload type mismatch")

    return WebSocketMessage(**message_data)


# Schema validation utilities

def validate_transcript_event(data: Dict[str, Any]) -> TranscriptEvent:
    """Validate and parse transcript event data."""
    return TranscriptEvent.parse_obj(data)


def validate_event_notification(data: Dict[str, Any]) -> EventNotification:
    """Validate and parse event notification data."""
    return EventNotification.parse_obj(data)


# JSON serialization helpers

def serialize_for_zmq(obj: BaseModel) -> bytes:
    """Serialize Pydantic model to JSON bytes for ZMQ transmission."""
    return obj.json(separators=(',', ':')).encode('utf-8')


def serialize_for_websocket(obj: BaseModel) -> str:
    """Serialize Pydantic model to JSON string for WebSocket transmission."""
    return obj.json(separators=(',', ':'))


# Constants for common event types
class EventTypes:
    """Common event type constants."""
    WAKE_WORD_DETECTED = "wake_word_detected"
    PROCESSING_STARTED = "processing_started"
    PROCESSING_COMPLETED = "processing_completed"
    TRANSCRIPT_READY = "transcript_ready"
    ERROR_OCCURRED = "error_occurred"
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_STOPPED = "pipeline_stopped"
    BUFFER_OVERFLOW = "buffer_overflow"
    STAGE_ERROR = "stage_error"


# Constants for message types
class MessageTypes:
    """WebSocket message type constants."""
    TRANSCRIPT = "transcript"
    EVENT = "event"
    STATUS = "status"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
