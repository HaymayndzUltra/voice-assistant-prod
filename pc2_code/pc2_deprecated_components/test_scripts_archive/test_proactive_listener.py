#!/usr/bin/env python
"""
Test Proactive Event Listener

Simple script to listen for proactive events on the proactive event bus.
Used to verify that proactive reminder broadcasting is working correctly.
"""

import zmq
import json
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
PROACTIVE_EVENT_PORT = 5595

def listen_for_proactive_events(duration=60):
    """
    Listen for proactive events for a specified duration.
    
    Args:
        duration: Duration to listen for in seconds (default: 60 seconds)
    """
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(f"tcp://localhost:{PROACTIVE_EVENT_PORT}")
    socket.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all topics
    
    logger.info(f"Listening for proactive events on port {PROACTIVE_EVENT_PORT}...")
    logger.info(f"Will listen for {duration} seconds. Press Ctrl+C to stop early.")
    
    # Don't try to bind the port since the memory agent should already have it bound
    logger.info(f"Connected SUB socket to port {PROACTIVE_EVENT_PORT}")
    
    try:
        end_time = time.time() + duration
        event_count = 0
        
        while time.time() < end_time:
            try:
                # Set a timeout for polling
                if socket.poll(timeout=1000) == 0:  # 1 second timeout
                    continue
                
                event = socket.recv_json()
                event_count += 1
                logger.info(f"Received proactive event #{event_count}:")
                logger.info(json.dumps(event, indent=2))
                
            except zmq.error.Again:
                # Timeout, continue listening
                pass
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received. Stopping...")
                break
            except Exception as e:
                logger.error(f"Error receiving event: {e}")
                
        logger.info(f"Finished listening. Received {event_count} events.")
        
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    try:
        listen_for_proactive_events()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Exiting...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
