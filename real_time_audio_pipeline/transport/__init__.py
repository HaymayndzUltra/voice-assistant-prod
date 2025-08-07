"""
Real-Time Audio Pipeline - Transport Layer

High-performance transport layer for RTAP providing ZeroMQ and WebSocket
interfaces for real-time event and transcript broadcasting.
"""

# Core schemas (always available)
from .schemas import (
    TranscriptEvent, EventNotification, WebSocketMessage, PipelineStatus,
    create_transcript_event, create_event_notification, create_websocket_message,
    EventTypes, MessageTypes
)

# ZMQ Publisher (with graceful fallback)
try:
    from .zmq_pub import ZmqPublisher
    ZMQ_AVAILABLE = True
except ImportError:
    ZmqPublisher = None
    ZMQ_AVAILABLE = False

# WebSocket Server (with graceful fallback)
try:
    from .ws_server import WebSocketServer
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WebSocketServer = None
    WEBSOCKET_AVAILABLE = False

__all__ = [
    'TranscriptEvent', 'EventNotification', 'WebSocketMessage', 'PipelineStatus',
    'create_transcript_event', 'create_event_notification', 'create_websocket_message',
    'EventTypes', 'MessageTypes',
    'ZmqPublisher', 'WebSocketServer',
    'ZMQ_AVAILABLE', 'WEBSOCKET_AVAILABLE'
]
