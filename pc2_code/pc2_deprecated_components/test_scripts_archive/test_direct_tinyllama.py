"""
Test script for verifying self-management of tinyllama_service.py.
This tests on-demand loading and idle unloading functionality.
"""
import zmq
import json
import time
import uuid

# Configuration values from tinyllama_service.py
TINYLAMA_SERVICE_PORT = 5615  # Default port used in tinyllama_service.py
TINYLAMA_SERVICE_IDLE_TIMEOUT = 35  # Default timeout (30s) + buffer (5s)

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.setsockopt(zmq.LINGER, 0)
socket.setsockopt(zmq.RCVTIMEO, 180000)  # 180s (3 minutes) timeout for inference to accommodate model loading
socket.setsockopt(zmq.SNDTIMEO, 5000)
socket.connect(f"tcp://localhost:{TINYLAMA_SERVICE_PORT}")

def send_tiny_request(payload):
    print(f"\n>>> Sending to TinyLlama Service: {json.dumps(payload)}")
    try:
        socket.send_json(payload)
        response = socket.recv_json()
        print(f"<<< Received from TinyLlama Service: {json.dumps(response, indent=2)}")
        return response
    except zmq.error.Again:
        print("!!! TinyLlama Service request timed out.")
        return None
    except Exception as e:
        print(f"!!! Error during TinyLlama Service request: {e}")
        return None

print("--- Test 1.1: Initial State (TinyLlama should be unloaded) ---")
# Walang ipapadala, i-check lang sa logs ng tinyllama_service.py kung hindi pa loaded.
print("ACTION: Check tinyllama_service.py logs. Model should NOT be loaded yet.")
input("Press Enter to continue after checking logs...")

print("\n--- Test 1.2: Trigger On-Demand Load via Inference Request ---")
inference_payload = {
    "action": "generate",  # Based on tinyllama_service.py code
    "prompt": "Once upon a time", 
    "max_tokens": 50,
    "request_id": str(uuid.uuid4())
}
send_tiny_request(inference_payload)
print(f"ACTION: Check tinyllama_service.py logs. Model should have loaded. Output should be a generation.")
input("Press Enter to continue...")

print(f"\n--- Test 1.3: Trigger Self-Idle Unload ---")
print(f"Waiting for {TINYLAMA_SERVICE_IDLE_TIMEOUT} seconds for TinyLlama to self-unload...")
time.sleep(TINYLAMA_SERVICE_IDLE_TIMEOUT)
print(f"ACTION: Check tinyllama_service.py logs. Model should have unloaded due to idle timeout.")
input("Press Enter to finish direct TinyLlama test...")

socket.close()
context.term()
