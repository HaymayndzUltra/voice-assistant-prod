#!/usr/bin/env python3
"""
Test script to verify Task Router health check
"""
import zmq
import json
import time
import sys
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

# Network Configuration
MAIN_PC_IP = "192.168.100.16"  # Main PC IP
TASK_ROUTER_PORT = 8570        # Task Router port

def test_task_router_health():
    """Test the health check endpoint of Task Router"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://{MAIN_PC_IP}:{TASK_ROUTER_PORT}")
    
    print(f"Connecting to Task Router at {MAIN_PC_IP}:{TASK_ROUTER_PORT}")
    
    # Send health check request
    request = {"type": "health_check"}
    print("\nSending health check request:", request)
    socket.send_json(request)
    
    try:
        # Set up poller for timeout
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        
        # Wait for response with timeout
        socks = dict(poller.poll(3000))  # 3 second timeout
        
        if socks.get(socket) == zmq.POLLIN:
            response = socket.recv_json()
            print("\nReceived response:", json.dumps(response, indent=2))
            
            if response.get("status") == "ok":
                print("\n✅ Task Router is healthy!")
            else:
                print("\n❌ Task Router returned non-ok status")
        else:
            print("\n❌ No response from Task Router (timeout)")
            
    except Exception as e:
        print("\n❌ Error during health check:", str(e))
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    test_task_router_health() 