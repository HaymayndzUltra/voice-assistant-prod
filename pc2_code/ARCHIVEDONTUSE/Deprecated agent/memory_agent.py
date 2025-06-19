#!/usr/bin/env python3
"""
Memory Agent (Base) - PC2
Minimal stub version for restoration/health check. Replace with full implementation as needed.
"""
import zmq
import time
import logging
import sys
import threading
import traceback
from pathlib import Path

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "memory_agent.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("MemoryAgent")

class MemoryAgent:
    def __init__(self, port=5590, bind_address="0.0.0.0"):
        logger.info("=" * 80)
        logger.info("Initializing Memory Agent")
        logger.info("=" * 80)
        
        self.port = port
        self.bind_address = bind_address
        self.running = True
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        
        # Critical: Set timeout so we don't block indefinitely
        self.socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2 second timeout
        
        # Bind to all interfaces for external access
        self.bind_address = f"tcp://{bind_address}:{port}"
        logger.info(f"Binding to {self.bind_address}")
        self.socket.bind(self.bind_address)
        
        # Track statistics
        self.start_time = time.time()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.health_check_requests = 0
        
        logger.info("Memory Agent initialized successfully")
        logger.info("=" * 80)

    def run(self):
        """Main service loop with timeout handling"""
        logger.info("Memory Agent service loop started")
        
        while self.running:
            try:
                # Wait for next request with timeout
                message = self.socket.recv_json()
                logger.info(f"Received request: {message}")
                
                # Process request
                action = message.get("request_type", message.get("action", "unknown"))
                logger.info(f"Processing action: {action}")
                
                if action == "health_check":
                    self.health_check_requests += 1
                    response = self._handle_health_check()
                else:
                    response = {
                        "status": "error",
                        "message": f"Unknown action: {action}"
                    }
                    self.failed_requests += 1
                
                # Send response
                logger.info(f"Sending response: {response}")
                self.socket.send_json(response)
                self.total_requests += 1
                if response.get("status") == "ok":
                    self.successful_requests += 1
                
            except zmq.error.Again:
                # Timeout - just continue the loop
                continue
            except Exception as e:
                error_msg = f"Error in service loop: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                try:
                    self.socket.send_json({
                        "status": "error",
                        "message": error_msg
                    })
                except:
                    pass
                self.failed_requests += 1
                time.sleep(0.1)  # Small delay to prevent CPU spinning
    
    def _handle_health_check(self):
        """Handle health check request"""
        logger.info("Processing health check request")
        response = {
            "status": "ok",
            "service": "memory_agent",
            "timestamp": time.time(),
            "uptime_seconds": time.time() - self.start_time,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "health_check_requests": self.health_check_requests,
            "bind_address": self.bind_address
        }
        logger.info(f"Health check response: {response}")
        return response

    def stop(self):
        """Stop the Memory Agent"""
        logger.info("Stopping Memory Agent...")
        self.running = False
        self.socket.close()
        self.context.term()
        logger.info("Memory Agent stopped")

if __name__ == "__main__":
    try:
        # Create and start the agent
        agent = MemoryAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        agent.stop()
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)
