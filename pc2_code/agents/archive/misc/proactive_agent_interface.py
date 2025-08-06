#!/usr/bin/env python
"""
Proactive Agent Interface Module

This module provides functions for sending proactive events between agents.
Used primarily for broadcasting reminders and notifications to listening agents.
"""

import zmq
import logging
import time
from typing import Optional
from common.utils.log_setup import configure_logging

# Constants
PROACTIVE_EVENT_PORT = 5595

def send_proactive_event(
    event_type: str, 
    text: str = "", 
    user: Optional[str] = None, 
    emotion: str = "neutral", 
    **kwargs
) -> bool:
    """
    Send a proactive event to the proactive event bus.
    
    Args:
        event_type: Type of the event (e.g., "reminder", "notification")
        text: Text content of the event
        user: User ID the event is for (optional)
        emotion: Emotion associated with the event (default: "neutral")
        **kwargs: Additional event data
        
    Returns:
        bool: True if event was sent successfully, False otherwise
    """
    try:
        context = zmq.Context()
        socket = context.socket(zmq.PUB)
        socket.connect(f"tcp://localhost:{PROACTIVE_EVENT_PORT}")
        
        # Allow a brief moment for connection to establish
        time.sleep(0.1)
        
        event_data = {
            "event_type": event_type,
            "text": text,
            "user": user,
            "emotion": emotion,
            "timestamp": time.time(),
            **kwargs
        }
        
        # Send the event
        socket.send_json(event_data)
        logging.info(f"[Proactive] Sent {event_type} event: {text[:50]}...")
        
        # Allow time for the message to be delivered before closing
        time.sleep(0.1)
        return True
    except Exception as e:
        logging.error(f"[Proactive] Failed to send event: {str(e)}")
        return False
    finally:
        if 'socket' in locals():
            socket.close()
        if 'context' in locals():
            context.term()
            
if __name__ == "__main__":
    # Simple test if run directly
    logger = configure_logging(__name__, level="INFO")
    print("Sending test proactive event...")
    result = send_proactive_event(
        event_type="test", 
        text="This is a test proactive event", 
        user="test_user"
    )
    print(f"Event sent: {result}")
