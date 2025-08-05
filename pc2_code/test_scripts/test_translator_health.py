import zmq
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent)

# Configuration
CONFIG_MAIN_PC_REP_PORT = 5563
CONFIG_ZMQ_BIND_ADDRESS = "0.0.0.0"
CONFIG_HEALTH_REP_PORT = 5559

def test_health_check():
    """Test the health check endpoint"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://{CONFIG_ZMQ_BIND_ADDRESS}:{CONFIG_HEALTH_REP_PORT}")
    
    print("Testing health check...")
    socket.send_string(json.dumps({"action": "health_check"})
    
    if socket.poll(5000) == 0:
        print("Error: Health check request timed out")
        return False
        
    response = json.loads(socket.recv_string()
    print(f"Health check response: {json.dumps(response, indent=2)}")
    return response.get("status") == "ok"

def test_basic_translation():
    """Test basic translation functionality"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://{CONFIG_ZMQ_BIND_ADDRESS}:{CONFIG_MAIN_PC_REP_PORT}")
    
    test_phrases = [
        "buksan mo ang file",
        "i-save mo ang document",
        "magsimula ng bagong project"
    ]
    
    print("\nTesting basic translations...")
    for phrase in test_phrases:
        print(f"\nTranslating: '{phrase}'")
        socket.send_string(json.dumps({
            "action": "translate",
            "text": phrase,
            "source_lang": "tl",
            "target_lang": "en"
        })
        
        if socket.poll(5000) == 0:
            print(f"Error: Translation request timed out for '{phrase}'")
            continue
            
        response = json.loads(socket.recv_string()
        print(f"Response: {json.dumps(response, indent=2)}")
        
        if response.get("status") != "ok":
            print(f"Error: Translation failed for '{phrase}'")
            continue
            
        print(f"Translation: '{response.get('translation', '')}'")

def test_error_handling():
    """Test error handling with invalid requests"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://{CONFIG_ZMQ_BIND_ADDRESS}:{CONFIG_MAIN_PC_REP_PORT}")
    
    invalid_requests = [
        {"action": "invalid_action"},
        {"action": "translate", "text": ""},
        {"action": "translate", "text": "test", "source_lang": "invalid"}
    ]
    
    print("\nTesting error handling...")
    for request in invalid_requests:
        print(f"\nSending invalid request: {json.dumps(request)}")
        socket.send_string(json.dumps(request)
        
        if socket.poll(5000) == 0:
            print("Error: Request timed out")
            continue
            
        response = json.loads(socket.recv_string()
        print(f"Response: {json.dumps(response, indent=2)}")
        
        if response.get("status") == "error":
            print("Expected error response received")
        else:
            print("Warning: Unexpected successful response for invalid request")

if __name__ == "__main__":
    print("Starting TranslatorAgent tests...")
    
    # Test health check
    if not test_health_check():
        print("Health check failed, aborting further tests")
        sys.exit(1)
        
    # Test basic translation
    test_basic_translation()
    
    # Test error handling
    test_error_handling()
    
    print("\nAll tests completed") 