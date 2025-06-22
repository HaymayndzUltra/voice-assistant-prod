"""
Quick automated test for TinyLlama service
- Tests health check
- Tests model loading
- Tests generation
- No user interaction required
"""
import zmq
import json
import time
import uuid
import sys

# Configuration
TINYLAMA_SERVICE_PORT = 5615
MAX_RETRIES = 3
TIMEOUT_MS = 180000  # 3 minutes

def log(message):
    print(f"[{time.strftime('%H:%M:%S')}] {message}")
    sys.stdout.flush()  # Force output to display immediately

# Setup ZMQ connection
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.setsockopt(zmq.LINGER, 0)
socket.setsockopt(zmq.RCVTIMEO, TIMEOUT_MS)
socket.setsockopt(zmq.SNDTIMEO, 5000)
socket.connect(f"tcp://localhost:{TINYLAMA_SERVICE_PORT}")

def send_request(payload, description):
    """Send request to TinyLlama service with retry logic"""
    log(f"TEST: {description}")
    log(f"Sending: {json.dumps(payload)}")
    
    for attempt in range(MAX_RETRIES):
        try:
            socket.send_json(payload)
            response = socket.recv_json()
            log(f"Response: {json.dumps(response)}")
            return response
        except zmq.error.Again:
            log(f"Request timed out (attempt {attempt+1}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES - 1:
                # Create new socket for retry
                socket.close()
                new_socket = context.socket(zmq.REQ)
                new_socket.setsockopt(zmq.LINGER, 0)
                new_socket.setsockopt(zmq.RCVTIMEO, TIMEOUT_MS)
                new_socket.setsockopt(zmq.SNDTIMEO, 5000)
                new_socket.connect(f"tcp://localhost:{TINYLAMA_SERVICE_PORT}")
                globals()['socket'] = new_socket
            else:
                log("All retries failed")
                return None
        except Exception as e:
            log(f"Error: {e}")
            return None

def run_tests():
    """Run all tests in sequence"""
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Health check (should show unloaded initially)
    response = send_request({"action": "health_check"}, "Initial health check")
    if response and response.get("status") == "ok":
        log("✅ Health check passed")
        log(f"Model status: {response.get('model_status', 'unknown')}")
        tests_passed += 1
    else:
        log("❌ Health check failed")
        tests_failed += 1
    
    # Test 2: Explicit load request
    response = send_request({"action": "ensure_loaded"}, "Explicit load request")
    if response and response.get("status") == "success" and response.get("success", False):
        log("✅ Model load request passed")
        tests_passed += 1
    else:
        log("❌ Model load request failed")
        tests_failed += 1
    
    # Test 3: Generation request
    test_prompt = "Translate this to English: Magandang umaga po"
    response = send_request({
        "action": "generate",
        "prompt": test_prompt,
        "max_tokens": 30,
        "request_id": str(uuid.uuid4())
    }, "Text generation test")
    
    if response and response.get("status") == "success" and response.get("text"):
        log(f"✅ Generation passed. Output: {response.get('text')}")
        tests_passed += 1
    else:
        log("❌ Generation failed")
        tests_failed += 1
    
    # Test 4: Final health check (should show loaded)
    response = send_request({"action": "health_check"}, "Final health check")
    if response and response.get("status") == "ok" and response.get("model_status") == "loaded":
        log("✅ Final health check passed (model is loaded)")
        tests_passed += 1
    else:
        log("❌ Final health check failed or model not loaded")
        tests_failed += 1
    
    # Test 5: Unload request
    response = send_request({"action": "request_unload"}, "Unload request")
    if response and response.get("status") == "success" and response.get("success", False):
        log("✅ Model unload request passed")
        tests_passed += 1
    else:
        log("❌ Model unload request failed")
        tests_failed += 1
    
    # Summary
    log(f"\nTEST SUMMARY: {tests_passed} passed, {tests_failed} failed")
    
    # Cleanup
    socket.close()
    context.term()

if __name__ == "__main__":
    log("Starting TinyLlama service tests...")
    run_tests()
