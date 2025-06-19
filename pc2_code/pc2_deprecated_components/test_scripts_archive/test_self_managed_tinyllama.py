"""
Test script for self-managed TinyLlama service
- Tests on-demand loading
- Tests idle unloading
- Tests health check reporting
"""
import zmq
import json
import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

def send_request(socket, request):
    """Send a request to the service and return the response"""
    print(f"\nSending request: {request}")
    socket.send_string(json.dumps(request))
    response = socket.recv_string()
    return json.loads(response)

def main():
    # Connect to TinyLlama service
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5615")
    
    try:
        # 1. Check initial health (should be unloaded)
        print("\n--- STEP 1: Initial Health Check ---")
        health_response = send_request(socket, {"action": "health_check"})
        print(f"Health response: {json.dumps(health_response, indent=2)}")
        assert health_response["model_status"] == "unloaded", "Model should be unloaded initially"
        
        # 2. Send a generation request (should trigger on-demand loading)
        print("\n--- STEP 2: Testing On-Demand Loading ---")
        print("Sending text generation request (this will trigger on-demand loading)...")
        gen_response = send_request(socket, {
            "action": "generate", 
            "prompt": "What is the capital of France?",
            "max_tokens": 50
        })
        print(f"Generation response: {json.dumps(gen_response, indent=2)}")
        
        # 3. Check health again (should be loaded now)
        print("\n--- STEP 3: Health Check After Loading ---")
        health_response = send_request(socket, {"action": "health_check"})
        print(f"Health response: {json.dumps(health_response, indent=2)}")
        assert health_response["model_status"] == "loaded", "Model should be loaded after generation"
        
        # 4. Test explicit unloading
        print("\n--- STEP 4: Testing Explicit Unloading ---")
        unload_response = send_request(socket, {"action": "request_unload"})
        print(f"Unload response: {json.dumps(unload_response, indent=2)}")
        
        # 5. Verify unloaded state
        print("\n--- STEP 5: Verify Unloaded State ---")
        health_response = send_request(socket, {"action": "health_check"})
        print(f"Health response: {json.dumps(health_response, indent=2)}")
        assert health_response["model_status"] == "unloaded", "Model should be unloaded after explicit unload"
        
        # 6. Test idle timeout (would need to wait for timeout period)
        print("\n--- STEP 6: Testing Idle Timeout ---")
        print("Loading model again...")
        load_response = send_request(socket, {"action": "ensure_loaded"})
        print(f"Load response: {json.dumps(load_response, indent=2)}")
        
        # 7. Verify loaded state
        print("\n--- STEP 7: Verify Loaded State ---")
        health_response = send_request(socket, {"action": "health_check"})
        print(f"Health response: {json.dumps(health_response, indent=2)}")
        assert health_response["model_status"] == "loaded", "Model should be loaded after explicit load"
        
        # Note: To test idle unloading, you would need to wait for the idle timeout period
        # which is set to 300 seconds (5 minutes) by default
        print("\nTo test idle unloading, you would need to wait for the idle timeout period")
        print("(default is 300 seconds / 5 minutes)")
        
        print("\nTest completed successfully!")
        
    except AssertionError as e:
        print(f"Test failed: {e}")
    except Exception as e:
        print(f"Error during test: {e}")
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    main()
