#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Script to test the error reporting flow in the system.
This script will:
1. Connect to the Error Bus as a subscriber
2. Simulate errors from different agents
3. Verify that errors are properly received and formatted
"""

import os
import sys
import json
import time
import zmq
import argparse
import threading
from typing import Dict, List, Any, Optional

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import common utilities if available
try:
    from common_utils.env_loader import get_env
    USE_COMMON_UTILS = True
except ImportError:
    USE_COMMON_UTILS = False
    print("[WARNING] common_utils.env_loader not found. Using default environment settings.")

# Default values
DEFAULT_ERROR_BUS_HOST = "localhost"
DEFAULT_ERROR_BUS_PORT = 7150
DEFAULT_ERROR_BUS_TOPIC = "ERROR:"
DEFAULT_TEST_DURATION = 60  # seconds

class ErrorBusSubscriber:
    """Subscribes to the Error Bus and collects error messages."""
    
    def __init__(self, host: str, port: int, topic: str):
        """Initialize the subscriber."""
        self.host = host
        self.port = port
        self.topic = topic
        self.endpoint = f"tcp://{host}:{port}"
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(self.endpoint)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, topic)
        self.running = False
        self.errors = []
        self.lock = threading.Lock()
    
    def start(self):
        """Start listening for error messages."""
        self.running = True
        self.thread = threading.Thread(target=self._listen)
        self.thread.daemon = True
        self.thread.start()
        print(f"Listening for errors on {self.endpoint} with topic '{self.topic}'")
    
    def stop(self):
        """Stop listening for error messages."""
        self.running = False
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=2)
        self.socket.close()
        self.context.term()
        print("Stopped listening for errors")
    
    def _listen(self):
        """Listen for error messages in a background thread."""
        while self.running:
            try:
                # Set a timeout so we can check if we should stop
                if self.socket.poll(timeout=1000) == 0:
                    continue
                
                # Receive message
                topic, message = self.socket.recv_multipart()
                topic_str = topic.decode('utf-8')
                
                try:
                    # Parse JSON message
                    error_data = json.loads(message.decode('utf-8'))
                    timestamp = time.time()
                    
                    with self.lock:
                        self.errors.append({
                            'timestamp': timestamp,
                            'topic': topic_str,
                            'data': error_data
                        })
                    
                    print(f"[{time.strftime('%H:%M:%S')}] Received error: {error_data.get('error_type', 'Unknown')} - {error_data.get('message', 'No message')}")
                    
                except json.JSONDecodeError:
                    print(f"Error decoding JSON message: {message}")
                except Exception as e:
                    print(f"Error processing message: {e}")
            
            except zmq.ZMQError as e:
                print(f"ZMQ error: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """Get all collected errors."""
        with self.lock:
            return self.errors.copy()

class ErrorSimulator:
    """Simulates errors from different agents."""
    
    def __init__(self, host: str, port: int, topic: str):
        """Initialize the simulator."""
        self.host = host
        self.port = port
        self.topic = topic
        self.endpoint = f"tcp://{host}:{port}"
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.connect(self.endpoint)
    
    def simulate_error(self, agent_name: str, error_type: str, message: str, severity: str = "ERROR", context: Optional[Dict[str, Any]] = None):
        """Simulate an error from an agent."""
        error_data = {
            "timestamp": time.time(),
            "agent": agent_name,
            "error_type": error_type,
            "message": message,
            "severity": severity,
            "context": context or {}
        }
        
        try:
            # Format as JSON and send
            msg = json.dumps(error_data).encode('utf-8')
            self.socket.send_multipart([self.topic.encode('utf-8'), msg])
            print(f"Simulated error from {agent_name}: {error_type} - {message}")
            return True
        except Exception as e:
            print(f"Error simulating error: {e}")
            return False
    
    def close(self):
        """Close the simulator."""
        self.socket.close()
        self.context.term()

def run_test(args):
    """Run the error reporting flow test."""
    # Get environment variables if available
    if USE_COMMON_UTILS:
        error_bus_host = get_env("ERROR_BUS_HOST", args.host)
        error_bus_port = int(get_env("ERROR_BUS_PORT", args.port))
    else:
        error_bus_host = os.environ.get("ERROR_BUS_HOST", args.host)
        error_bus_port = int(os.environ.get("ERROR_BUS_PORT", args.port))
    
    error_bus_topic = args.topic
    
    # Create subscriber
    subscriber = ErrorBusSubscriber(error_bus_host, error_bus_port, error_bus_topic)
    subscriber.start()
    
    # Create simulator
    simulator = ErrorSimulator(error_bus_host, error_bus_port, error_bus_topic)
    
    # Wait for subscriber to connect
    time.sleep(1)
    
    # Simulate errors from different agents
    test_agents = [
        "RequestCoordinator",
        "ModelOrchestrator",
        "SessionMemoryAgent",
        "ContextManager",
        "SpeechToText",
        "ResponseGenerator"
    ]
    
    error_types = [
        "connection_error",
        "timeout_error",
        "validation_error",
        "resource_error",
        "unexpected_error"
    ]
    
    severities = [
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL"
    ]
    
    # Simulate one error from each agent
    for i, agent in enumerate(test_agents):
        error_type = error_types[i % len(error_types)]
        severity = severities[i % len(severities)]
        message = f"Test error message from {agent}"
        context = {"test_id": i, "timestamp": time.time()}
        
        simulator.simulate_error(agent, error_type, message, severity, context)
        time.sleep(1)
    
    # Simulate a burst of errors
    if args.burst:
        print("\nSimulating error burst...")
        for i in range(10):
            agent = test_agents[i % len(test_agents)]
            error_type = "burst_error"
            message = f"Burst error {i} from {agent}"
            simulator.simulate_error(agent, error_type, message, "WARNING")
            time.sleep(0.2)
    
    # Wait for test duration
    remaining_time = args.duration
    while remaining_time > 0:
        print(f"\rWaiting for errors... {remaining_time} seconds remaining", end="")
        time.sleep(1)
        remaining_time -= 1
    
    print("\n\nTest completed")
    
    # Get collected errors
    errors = subscriber.get_errors()
    
    # Print summary
    print(f"\n=== ERROR REPORTING TEST SUMMARY ===")
    print(f"Errors received: {len(errors)}")
    
    # Count errors by agent
    agent_counts = {}
    for error in errors:
        agent = error['data'].get('agent', 'Unknown')
        agent_counts[agent] = agent_counts.get(agent, 0) + 1
    
    print("\nErrors by agent:")
    for agent, count in agent_counts.items():
        print(f"- {agent}: {count}")
    
    # Count errors by severity
    severity_counts = {}
    for error in errors:
        severity = error['data'].get('severity', 'Unknown')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    print("\nErrors by severity:")
    for severity, count in severity_counts.items():
        print(f"- {severity}: {count}")
    
    # Save errors to file
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(errors, f, indent=2)
        print(f"\nSaved {len(errors)} errors to {args.output}")
    
    # Clean up
    simulator.close()
    subscriber.stop()
    
    # Return success if we received at least one error
    return len(errors) > 0

def main():
    """Parse arguments and run the test."""
    parser = argparse.ArgumentParser(description="Test the error reporting flow")
    parser.add_argument("--host", default=DEFAULT_ERROR_BUS_HOST, help=f"Error Bus host (default: {DEFAULT_ERROR_BUS_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_ERROR_BUS_PORT, help=f"Error Bus port (default: {DEFAULT_ERROR_BUS_PORT})")
    parser.add_argument("--topic", default=DEFAULT_ERROR_BUS_TOPIC, help=f"Error Bus topic (default: {DEFAULT_ERROR_BUS_TOPIC})")
    parser.add_argument("--duration", type=int, default=DEFAULT_TEST_DURATION, help=f"Test duration in seconds (default: {DEFAULT_TEST_DURATION})")
    parser.add_argument("--burst", action="store_true", help="Simulate a burst of errors")
    parser.add_argument("--output", help="Output file for collected errors (JSON format)")
    
    args = parser.parse_args()
    
    try:
        success = run_test(args)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"Error running test: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 