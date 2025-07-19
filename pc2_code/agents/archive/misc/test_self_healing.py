#!/usr/bin/env python3
"""
Test Self-Healing Agent
---------------------
Simplified version just for ZMQ port testing.
"""

import zmq
import json
import time
import logging
import sys
import os
from pathlib import Path
from common.env_helpers import get_env

# Setup logging
LOG_DIR = Path(os.path.dirname(__file__)).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_PATH = LOG_DIR / "test_self_healing.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TestSelfHealing")

# ZMQ ports
SELF_HEALING_PORT = 5614  # Main REP socket for commands
HEALTH_BROADCAST_PORT = 5616  # PUB socket for broadcasting health status

def main():
    """Test ZMQ socket binding"""
    context = zmq.Context()
    
    # REP socket for receiving commands
    rep_socket = context.socket(zmq.REP)
    rep_socket.bind(f"tcp://127.0.0.1:{SELF_HEALING_PORT}")
    logger.info(f"REP socket bound to port {SELF_HEALING_PORT}")
    
    # PUB socket for broadcasting health status
    pub_socket = context.socket(zmq.PUB)
    pub_socket.bind(f"tcp://127.0.0.1:{HEALTH_BROADCAST_PORT}")
    logger.info(f"PUB socket bound to port {HEALTH_BROADCAST_PORT}")
    
    # Test health broadcast
    status_message = json.dumps({
        "event": "health_status_update",
        "status": "online",
        "timestamp": time.time()
    })
    pub_socket.send_string(status_message)
    logger.info("Sent test health status message")
    
    logger.info("Self-healing agent test initialized successfully")
    logger.info("Press Ctrl+C to exit")
    
    try:
        while True:
            try:
                # Wait for messages with a timeout
                if rep_socket.poll(1000) != 0:  # 1 second timeout
                    request_json = rep_socket.recv_string()
                    logger.info(f"Received: {request_json}")
                    
                    # Send response
                    response = {"status": "ok", "message": "Test self-healing agent running"}
                    rep_socket.send_string(json.dumps(response))
                
                # Broadcast health status periodically
                status_message = json.dumps({
                    "event": "health_status_update",
                    "status": "online",
                    "timestamp": time.time()
                })
                pub_socket.send_string(status_message)
                
                time.sleep(5)  # Wait 5 seconds between status updates
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
    
    except KeyboardInterrupt:
        logger.info("Test self-healing agent interrupted by user")
    finally:
        # Clean up
        rep_socket.close()
        pub_socket.close()
        context.term()
        logger.info("Test self-healing agent stopped")

if __name__ == "__main__":
    main()
