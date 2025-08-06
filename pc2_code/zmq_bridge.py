"""
ZMQ Bridge for Cross-Machine Communication
-----------------------------------------
Provides a dedicated ZMQ bridge to connect Main PC and PC2
- Binds to all interfaces (0.0.0.0) for remote access
- Handles message routing between machines
- Includes health check and status monitoring
"""
import zmq
import json
import time
import logging
import sys
import os
import signal
import threading
from pathlib import Path
from datetime import datetime
from common.utils.log_setup import configure_logging

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent)
from common_utils.error_handling import SafeExecutor

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / str(PathManager.get_logs_dir() / "zmq_bridge.log")

logger = configure_logging(__name__)  # 1 second timeout for receives
            
            logger.info("ZMQ Bridge initialized successfully")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind ZMQ socket: {e}")
            raise
    
    def run(self):
        """Run the ZMQ bridge"""
        logger.info("ZMQ Bridge running...")
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Start status thread
        status_thread = threading.Thread(target=self._status_monitor)
        status_thread.daemon = True
        status_thread.start()
        
        # Main message handling loop
        while self.running:
            try:
                # Wait for message
                message_json = self.socket.recv_json()
                logger.info(f"Received message: {message_json}")
                
                # Process message
                response = self._process_message(message_json)
                
                # Send response
                self.socket.send_json(response)
                logger.info(f"Sent response: {response}")
                
            except zmq.error.Again:
                # Socket timeout, just continue
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                SafeExecutor.execute_with_fallback(
                    lambda: self.socket.send_json({"status": "error", "error": str(e)}),
                    fallback_value=None,
                    context="send ZMQ error response",
                    expected_exceptions=(zmq.ZMQError, json.JSONEncodeError)
                )
        
        logger.info("ZMQ Bridge stopped")
    
    def _process_message(self, message):
        """Process incoming message and generate response"""
        # Extract message type/action
        action = message.get("action", message.get("type", "unknown")
        
        if action == "health_check":
            # Health check request
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "ZMQ Bridge",
                "uptime_seconds": int(time.time() - self.start_time)
            }
        elif action == "echo":
            # Echo request for testing
            message["echo_timestamp"] = datetime.now().isoformat()
            return message
        elif action == "test":
            # Test request - just echo back for cross-machine testing
            return message
        else:
            # Unknown action
            return {
                "status": "error",
                "error": f"Unknown action: {action}",
                "timestamp": datetime.now().isoformat()
            }
    
    def _status_monitor(self):
        """Monitor and log bridge status periodically"""
        while self.running:
            SafeExecutor.execute_with_fallback(
                lambda: [
                    logger.debug(f"ZMQ Bridge status: Running on {self.bind_address}:{self.port}"),
                    time.sleep(30)  # Status update every 30 seconds
                ],
                fallback_value=None,
                context="ZMQ bridge status monitoring",
                expected_exceptions=(Exception,)  # Any exception during status monitoring
            )
    
    def _signal_handler(self, sig, frame):
        """Handle signals for graceful shutdown"""
        logger.info(f"Received signal {sig}, shutting down...")
        self.running = False
    
    def stop(self):
        """Stop the ZMQ bridge"""
        logger.info("Stopping ZMQ Bridge...")
        self.running = False
        
        # Close socket and terminate context
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        
        logger.info("ZMQ Bridge stopped")


if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ZMQ Bridge for cross-machine communication")
    parser.add_argument("--port", type=int, default=DEFAULT_BRIDGE_PORT, help="Port to bind to")
    parser.add_argument("--bind", type=str, default=DEFAULT_BIND_ADDRESS, help="Address to bind to (0.0.0.0 for all interfaces)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    # Set debug mode if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Display bridge info
    print(f"===== ZMQ Bridge =====")
    print(f"Binding to: {args.bind}:{args.port}")
    print(f"This bridge allows cross-machine communication between Main PC and PC2")
    print(f"Press Ctrl+C to stop")
    print(f"======================")
    
    while True:
        try:
            # Create and run bridge
            print("Starting ZMQ Bridge...")
            bridge = ZMQBridge(port=args.port, bind_address=args.bind)
            bridge.start_time = time.time()
            
            # Explicitly flush stdout to ensure logs are visible
            sys.stdout.flush()
            
            bridge.run()
            
        except KeyboardInterrupt:
            logger.info("Bridge interrupted by user")
            if 'bridge' in locals():
                bridge.stop()
            break
            
        except Exception as e:
            logger.error(f"Bridge error: {e}")
            import traceback

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager
            traceback.print_exc()
            
            # If bridge was created, try to clean it up
            if 'bridge' in locals():
                SafeExecutor.execute_with_fallback(
                    lambda: bridge.stop(),
                    fallback_value=None,
                    context="bridge cleanup on error",
                    expected_exceptions=(Exception,)  # Any exception during cleanup
                )
                    
            # Wait before retrying
            print(f"Error: {e}. Retrying in 5 seconds...")
            time.sleep(5)
