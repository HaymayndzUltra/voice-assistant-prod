#!/usr/bin/env python3
"""
Simple Test for Contextual Memory Agent
"""
import zmq
import json
import sys
import os

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Port for the contextual memory agent
ZMQ_CONTEXTUAL_MEMORY_PORT = 5596

def send_request(request):
    """Send a request to the Contextual Memory Agent"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.connect(f"tcp://127.0.0.1:{ZMQ_CONTEXTUAL_MEMORY_PORT}")
    
    # Set a timeout
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)
    
    print(f"Sending request: {request}")
    socket.send_string(json.dumps(request))
    
    # Wait with timeout
    if poller.poll(5000):  # 5 second timeout
        response = socket.recv_string()
        print(f"Received response: {response}")
        return json.loads(response)
    else:
        print("ERROR: Timeout waiting for response")
        return {"status": "timeout"}
    
def test_basic_functionality():
    """Run basic tests one by one"""
    
    # Test 1: Get session ID
    print("\n1. Testing get_session_id")
    response = send_request({
        "action": "get_session_id",
        "user_id": "tester",
        "project": "test_project"
    })
    if response.get("status") == "ok":
        print("✅ Get session ID test passed")
    else:
        print("❌ Get session ID test failed")
        return False
    
    # Test 2: Add a simple user query
    print("\n2. Testing add_interaction")
    response = send_request({
        "action": "add_interaction",
        "user_id": "tester",
        "project": "test_project",
        "type": "user_query",
        "content": "This is a test query"
    })
    if response.get("status") == "ok":
        print("✅ Add interaction test passed")
    else:
        print("❌ Add interaction test failed")
        return False
    
    # Test 3: Get a summary
    print("\n3. Testing get_summary")
    response = send_request({
        "action": "get_summary",
        "user_id": "tester",
        "project": "test_project",
        "max_tokens": 200
    })
    if response.get("status") == "ok" and "summary" in response:
        print("✅ Get summary test passed")
        print(f"Summary preview: {response['summary'][:100]}...")
    else:
        print("❌ Get summary test failed")
        return False
    
    # Test 4: Test error handling
    print("\n4. Testing error handling")
    response = send_request({
        "action": "invalid_action",
        "user_id": "tester"
    })
    if response.get("status") == "error":
        print("✅ Error handling test passed")
    else:
        print("❌ Error handling test failed")
        return False
    
    print("\nAll basic tests passed!")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("Simple Contextual Memory Agent Test")
    print("=" * 60)
    
    test_basic_functionality()
