#!/usr/bin/env python3
"""Simple ZMQ connection test"""

import zmq
import json
import time

def test_simple_zmq():
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
    socket.setsockopt(zmq.SNDTIMEO, 5000)   # 5 second send timeout
    
    try:
        print("Connecting to port 9901...")
        socket.connect("tcp://localhost:9901")
        time.sleep(2)  # Give some time for connection
        
        # Send a simple ping-like message
        print("Sending simple message...")
        simple_msg = {"method": "ping"}
        socket.send_json(simple_msg)
        
        print("Waiting for response...")
        response = socket.recv_json()
        print(f"Response: {response}")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    test_simple_zmq()
