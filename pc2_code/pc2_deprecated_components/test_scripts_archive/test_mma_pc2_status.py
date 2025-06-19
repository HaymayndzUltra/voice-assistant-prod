"""
Test script for verifying status reporting of the Model Manager Agent (MMA-PC2)
for tinyllama_service.py.
"""
import zmq
import json
import time
import uuid
import sys
from pathlib import Path

# Add parent directory to path to import config
sys.path.append(str(Path(__file__).parent))
from config.system_config import config

# Configuration values
MMA_PC2_PORT = config.get('zmq.model_manager_port', 5556)  # Default MMA port from config
TINYLAMA_MODEL_ID_IN_CONFIG = "tinyllama"  # Based on model_manager_agent.py
TINYLAMA_SERVICE_PORT = 5615  # Port used by tinyllama_service.py
TINYLAMA_SERVICE_IDLE_TIMEOUT = 35  # Default timeout (30s) + buffer (5s)
HEALTH_CHECK_INTERVAL = 30  # Default health check interval + buffer

context = zmq.Context()
mma_socket = context.socket(zmq.REQ)
mma_socket.setsockopt(zmq.LINGER, 0)
mma_socket.setsockopt(zmq.RCVTIMEO, 5000)
mma_socket.setsockopt(zmq.SNDTIMEO, 5000)
mma_socket.connect(f"tcp://localhost:{MMA_PC2_PORT}")

def get_tiny_status_from_mma():
    print(f"\n>>> Requesting status of {TINYLAMA_MODEL_ID_IN_CONFIG} from MMA-PC2...")
    payload = {
        "request_type": "get_model_status", 
        "model": TINYLAMA_MODEL_ID_IN_CONFIG,  # Changed from model_id to model based on handler code
        "request_id": str(uuid.uuid4())
    }
    try:
        mma_socket.send_json(payload)
        response = mma_socket.recv_json()
        print(f"<<< Received from MMA-PC2: {json.dumps(response, indent=2)}")
        return response
    except zmq.error.Again:
        print("!!! MMA-PC2 request timed out.")
        return None
    except Exception as e:
        print(f"!!! Error during MMA-PC2 request: {e}")
        return None

print("--- Test 2.1: Initial Status via MMA-PC2 ---")
# Assuming TinyLlama service just started and MMA-PC2 had its first health check cycle
get_tiny_status_from_mma()
# Expected: MMA-PC2 should report TinyLlama as "offline" or "unloaded"
print("ACTION: Verify MMA-PC2 logs for health check on TinyLlama.")
input("Press Enter to continue...")

print("\n--- Test 2.2: Status After TinyLlama Loads (Trigger Manually) ---")
print(f"ACTION: Please run test_direct_tinyllama.py (or send an inference request to port {TINYLAMA_SERVICE_PORT}) to make it load its model.")
input("Press Enter once TinyLlama model is loaded...")

print("Waiting a few seconds for MMA-PC2's next health check cycle...")
time.sleep(HEALTH_CHECK_INTERVAL + 5)  # Wait for MMA health check interval + buffer

get_tiny_status_from_mma()
# Expected: MMA-PC2 should now report TinyLlama as "online" or "loaded".
print("ACTION: Verify MMA-PC2 logs. It should have detected TinyLlama as online.")
input("Press Enter to continue...")

print(f"\n--- Test 2.3: Status After TinyLlama Self-Unloads (Trigger Manually) ---")
print(f"ACTION: Wait for {TINYLAMA_SERVICE_IDLE_TIMEOUT} seconds for TinyLlama to self-unload.")
print(f"         (Ensure no new requests are sent to TinyLlama service during this time).")
time.sleep(TINYLAMA_SERVICE_IDLE_TIMEOUT)
input(f"Press Enter once you believe TinyLlama has self-unloaded...")

print("Waiting a few seconds for MMA-PC2's next health check cycle...")
time.sleep(HEALTH_CHECK_INTERVAL + 5)

get_tiny_status_from_mma()
# Expected: MMA-PC2 should report TinyLlama as "offline" or "unloaded" again.
print("ACTION: Verify MMA-PC2 logs. It should have detected TinyLlama as offline/unloaded.")
input("Press Enter to finish MMA-PC2 status test...")

mma_socket.close()
context.term()
