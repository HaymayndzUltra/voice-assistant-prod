#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url

"""
StreamingAudioCapture Test Script
--------------------------------
Tests the StreamingAudioCapture agent in isolation
"""

import os
import sys
import time
import argparse
import logging
import zmq
import json
import pickle
from pathlib import Path
from common.env_helpers import get_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AudioCaptureTest")

# ANSI color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS_DIR = os.path.join(SCRIPT_DIR, "agents")

def run_audio_capture_test(dummy_mode=False, timeout=30):
    """Run the StreamingAudioCapture agent and test its functionality."""
    import subprocess
    import threading
    import time
    
    # Set up environment variables
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{SCRIPT_DIR}:{os.path.dirname(SCRIPT_DIR)}:{os.path.dirname(os.path.dirname(SCRIPT_DIR))}:{env.get('PYTHONPATH', '')}"
    
    if dummy_mode:
        env["USE_DUMMY_AUDIO"] = "true"
        print(f"{YELLOW}Running in dummy audio mode{RESET}")
    
    # Path to the agent file
    agent_path = os.path.join(AGENTS_DIR, "streaming_audio_capture.py")
    
    if not os.path.exists(agent_path):
        print(f"{RED}Error: StreamingAudioCapture agent not found at {agent_path}{RESET}")
        return False
    
    # Set the port
    port = 5660
    env["AGENT_PORT"] = str(port)
    
    # Start the agent process
    print(f"{BLUE}Starting StreamingAudioCapture agent on port {port}...{RESET}")
    process = subprocess.Popen(
        [sys.executable, agent_path],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=SCRIPT_DIR
    )
    
    # Set up ZMQ subscriber to listen for messages
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.connect(f"tcp://localhost:{port}")
    subscriber.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all messages
    
    # Set a timeout for receiving messages
    subscriber.setsockopt(zmq.RCVTIMEO, 5000)  # 5 seconds timeout
    
    # Flag to track if we received any messages
    received_messages = False
    
    # Function to monitor process output
    def monitor_output(pipe, is_stderr):
        prefix = f"{RED}[ERR]{RESET}" if is_stderr else f"{GREEN}[OUT]{RESET}"
        for line in pipe:
            line = line.strip()
            if line:
                print(f"{prefix} {line}")
    
    # Start threads to monitor process output
    threading.Thread(target=monitor_output, args=(process.stdout, False), daemon=True).start()
    threading.Thread(target=monitor_output, args=(process.stderr, True), daemon=True).start()
    
    # Wait for the agent to start
    print(f"{YELLOW}Waiting for agent to initialize...{RESET}")
    time.sleep(5)
    
    # Try to receive messages
    start_time = time.time()
    print(f"{BLUE}Listening for messages from StreamingAudioCapture...{RESET}")
    print(f"{YELLOW}(This test will run for {timeout} seconds){RESET}")
    
    try:
        while time.time() - start_time < timeout:
            try:
                message = subscriber.recv()
                
                # Try to parse the message
                try:
                    # First try as JSON string
                    if isinstance(message, bytes) and message.startswith(b"WAKE_WORD_EVENT:"):
                        event_json = message.decode('utf-8').replace("WAKE_WORD_EVENT: ", "")
                        event = json.loads(event_json)
                        print(f"{GREEN}Received wake word event: {event}{RESET}")
                        received_messages = True
                    else:
                        # Try as pickled data
                        data = pickle.loads(message)
                        if isinstance(data, dict) and 'audio_chunk' in data:
                            audio_data = data['audio_chunk']
                            timestamp = data.get('timestamp', 'unknown')
                            audio_level = data.get('audio_level', 'unknown')
                            print(f"{GREEN}Received audio chunk: timestamp={timestamp}, level={audio_level}, shape={audio_data.shape}{RESET}")
                            received_messages = True
                        elif isinstance(data, dict) and 'error' in data and data['error']:
                            print(f"{RED}Received error: {data['error_type']} - {data['message']}{RESET}")
                            received_messages = True
                        else:
                            print(f"{YELLOW}Received unknown message format{RESET}")
                except Exception as e:
                    print(f"{RED}Error parsing message: {e}{RESET}")
                    print(f"{YELLOW}Raw message: {message[:100]}...{RESET}")
                    
            except zmq.error.Again:
                # Timeout occurred, just continue
                print(f"{YELLOW}.{RESET}", end="", flush=True)
                time.sleep(1)
                continue
                
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test interrupted by user{RESET}")
    finally:
        # Clean up
        print(f"\n{BLUE}Cleaning up...{RESET}")
        subscriber.close()
        context.term()
        
        # Terminate the process
        if process.poll() is None:  # Process is still running
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        
        # Check if we received any messages
        if received_messages:
            print(f"\n{GREEN}{BOLD}Test PASSED: Received messages from StreamingAudioCapture{RESET}")
            return True
        else:
            print(f"\n{RED}{BOLD}Test FAILED: No messages received from StreamingAudioCapture{RESET}")
            return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test the StreamingAudioCapture agent")
    parser.add_argument("--dummy", action="store_true", help="Run in dummy audio mode (no actual audio capture)")
    parser.add_argument("--timeout", type=int, default=30, help="Test duration in seconds (default: 30)")
    args = parser.parse_args()
    
    print(f"{BLUE}{BOLD}StreamingAudioCapture Test{RESET}")
    print(f"Agent path: {os.path.join(AGENTS_DIR, 'streaming_audio_capture.py')}")
    print(f"Dummy mode: {args.dummy}")
    print(f"Timeout: {args.timeout} seconds\n")
    
    success = run_audio_capture_test(dummy_mode=args.dummy, timeout=args.timeout)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 