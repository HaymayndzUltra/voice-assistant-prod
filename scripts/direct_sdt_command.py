#!/usr/bin/env python3
"""
Direct SystemDigitalTwin Command Test

This script bypasses the service_discovery_client and directly sends
commands to SystemDigitalTwin to test the low-level communication.
"""

import os
import sys
import json
import zmq
from pathlib import Path

# Configure arguments
import argparse
from common.env_helpers import get_env
parser = argparse.ArgumentParser(description="Send commands directly to SystemDigitalTwin")
parser.add_argument("--host", default=get_env("BIND_ADDRESS", "0.0.0.0"), help="SystemDigitalTwin host")
parser.add_argument("--port", type=int, default=7120, help="SystemDigitalTwin port")
parser.add_argument("--command", choices=["register", "discover", "ping", "status"], default="status", 
                   help="Command to send")
parser.add_argument("--name", help="Service name for register/discover commands")
args = parser.parse_args()

# Create ZMQ context and socket
context = zmq.Context.instance()
socket = context.socket(zmq.REQ)

# Set timeout
socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout

try:
    # Connect to SystemDigitalTwin
    address = f"tcp://{args.host}:{args.port}"
    print(f"Connecting to SystemDigitalTwin at {address}...")
    socket.connect(address)
    
    # Prepare and send command based on arguments
    if args.command == "register":
        if not args.name:
            print("Error: --name is required for register command")
            sys.exit(1)
            
        request = {
            "command": "REGISTER",
            "payload": {
                "name": args.name,
                "location": "CLI-Test",
                "ip": "127.0.0.1",
                "port": 9999,
                "source": "direct_command_test"
            }
        }
        print(f"Sending REGISTER command: {json.dumps(request, indent=2)}")
        socket.send_json(request)
        
    elif args.command == "discover":
        if not args.name:
            print("Error: --name is required for discover command")
            sys.exit(1)
            
        request = {
            "command": "DISCOVER",
            "payload": {
                "name": args.name
            }
        }
        print(f"Sending DISCOVER command: {json.dumps(request, indent=2)}")
        socket.send_json(request)
        
    elif args.command == "ping":
        print("Sending PING command...")
        socket.send_string("ping")
        
    elif args.command == "status":
        print("Sending GET_ALL_STATUS command...")
        socket.send_string("GET_ALL_STATUS")
    
    # Wait for response
    try:
        if args.command == "ping":
            response = socket.recv_string()
            print(f"Response: {response}")
        else:
            response = socket.recv_json()
            print(f"Response: {json.dumps(response, indent=2)}")
        
        print("\nCommand completed successfully!")
        sys.exit(0)
        
    except zmq.error.Again:
        print("Error: Connection timeout waiting for response")
        sys.exit(1)
        
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
    
finally:
    socket.close()
    context.term() 