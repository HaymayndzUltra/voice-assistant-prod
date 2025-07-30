#!/usr/bin/env python3
"""
Minimal Agent Implementation
"""

import os
import sys
import time
import zmq
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('minimal_agent.log')
    ]
)
logger = logging.getLogger("MinimalAgent")

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = SCRIPT_DIR

# Add project root to Python path
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

class MinimalAgent:
    """TODO: Add description for MinimalAgent."""
    def __init__(self, name="MinimalAgent", port=7777):
        """TODO: Add description for __init__."""
        self.name = name
        self.port = port
        self.health_port = port + 1
        self.running = True
        self.start_time = time.time()

        # Initialize ZMQ
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.health_socket = self.context.socket(zmq.REP)

        # Bind sockets
        try:
            self.socket.bind(f"tcp://*:{self.port}")
            logger.info(f"Bound main socket to port {self.port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind main socket to port {self.port}: {e}")
            sys.exit(1)

        try:
            self.health_socket.bind(f"tcp://*:{self.health_port}")
            logger.info(f"Bound health socket to port {self.health_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind health socket to port {self.health_port}: {e}")
            self.socket.close()
            sys.exit(1)

    def _health_check_loop(self):
        """Health check loop"""
        logger.info("Starting health check loop")

        while self.running:
            try:
                # Check for health check requests with timeout
                if self.health_socket.poll(100) != 0:
                    # Receive request (don't care about content)
                    message = self.health_socket.recv()
                    logger.info(f"Received health check request: {message}")

                    # Send response
                    response = {
                        "status": "ok",
                        "name": self.name,
                        "uptime": time.time() - self.start_time
                    }
                    self.health_socket.send_json(response)
                    logger.info("Sent health check response")
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")

            time.sleep(1)

    def run(self):
        """Main run loop"""
        logger.info(f"Starting {self.name}")

        import threading
        health_thread = threading.Thread(target=self._health_check_loop)
        health_thread.daemon = True
        health_thread.start()

        try:
            while self.running:
                # Check for main socket messages with timeout
                if self.socket.poll(1000) != 0:
                    # Receive request
                    message = self.socket.recv()
                    logger.info(f"Received message: {message}")

                    # Send response
                    response = {
                        "status": "ok",
                        "message": "Hello from MinimalAgent"
                    }
                    self.socket.send_json(response)
                    logger.info("Sent response")

                # Log that we're still alive
                if int(time.time()) % 10 == 0:  # Log every 10 seconds
                    logger.info(f"{self.name} is running (uptime: {time.time() - self.start_time:.1f}s)")
                    time.sleep(1)  # Avoid multiple logs in the same second
                else:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources")
        self.running = False
        time.sleep(1)  # Give threads time to finish

        if hasattr(self, 'socket'):
            self.socket.close()

        if hasattr(self, 'health_socket'):
            self.health_socket.close()

        if hasattr(self, 'context'):
            self.context.term()

        logger.info(f"{self.name} stopped")

if __name__ == "__main__":
    agent = MinimalAgent()
    agent.run()
