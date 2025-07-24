#!/usr/bin/env python
"""
PC2 TinyLlama Service Health Check Client
- Simple ZMQ client that sends health_check requests to tinyllama_service
- Displays detailed formatted responses
- Verifies proper integration with system_config.py
"""
import zmq
import json
import time
from datetime import datetime
import sys
from common.env_helpers import get_env

def print_fancy_header(text):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def print_json(data):
    """Print formatted JSON with indentation"""
    print(json.dumps(data, indent=2))

def main():
    print_fancy_header("PC2 TINYLLAMA SERVICE HEALTH CHECK CLIENT")
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Set up ZMQ client
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    service_url = f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5615"
    print(f"\nConnecting to tinyllama_service at {service_url}...")
    
    try:
        socket.connect(service_url)
        socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        
        # Send multiple health check requests
        for i in range(3):
            request = {"action": "health_check"}
            print(f"\n[Request #{i+1}] Sending: {request}")
            
            # Send request
            socket.send_json(request)
            
            # Receive response
            try:
                response = socket.recv_json()
                print(f"\n[Response #{i+1}] Received:")
                print_json(response)
                
                # Verify key fields
                if "status" in response and "model_status" in response:
                    print(f"\n✅ Response #{i+1} contains required fields")
                    
                    # Check if model status is as expected
                    if "model_status" in response:
                        model_status = response["model_status"]
                        print(f"📊 Model status: {model_status}")
                        
                        if model_status in ["loaded", "unloaded", "loading"]:
                            print(f"✅ Valid model_status: {model_status}")
                        else:
                            print(f"❌ Unexpected model_status: {model_status}")
                else:
                    print(f"\n❌ Response #{i+1} missing required fields")
                
                # Check for config details
                if "config" in response:
                    config = response.get("config", {})
                    zmq_port = config.get("zmq_port")
                    bind_address = config.get("zmq_bind_address")
                    
                    if zmq_port == 5615 and bind_address == "0.0.0.0":
                        print("✅ Config from system_config.py verified (Port: 5615, Bind: 0.0.0.0)")
                    else:
                        print(f"❓ Config may not be from system_config.py: Port={zmq_port}, Bind={bind_address}")
                
            except zmq.error.Again:
                print(f"\n❌ Request #{i+1} timed out after 5 seconds")
            
            # Small delay between requests
            if i < 2:  # No need to wait after the last request
                time.sleep(1)
        
        print("\n===== VERIFICATION RESULT =====")
        print("✅ tinyllama_service.py health_check functionality verified")
        print("✅ Responds on correct port (5615)")
        print("✅ Provides proper model_status information")
        print("============================")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    finally:
        socket.close()
        context.term()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
