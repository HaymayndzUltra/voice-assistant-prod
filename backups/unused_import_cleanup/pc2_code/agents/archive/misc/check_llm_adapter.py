import zmq
import json
from common.core.base_agent import BaseAgent
from common.env_helpers import get_env

PORT = 5581
HOST = get_env("BIND_ADDRESS", "0.0.0.0")  # Adapter should be listening on 0.0.0.0


def check_adapter_status():
    """Send a 'stats' request to the LLM Translation Adapter and evaluate the response."""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)

    try:
        socket.connect(f"tcp://{HOST}:{PORT}")
    except Exception as e:
        print(f"[ERROR] Failed to connect to LLM adapter at tcp://{HOST}:{PORT}: {e}")
        return False

    # Set send/recv timeouts (milliseconds)
    socket.setsockopt(zmq.SNDTIMEO, 2000)  # 2 seconds send timeout
    socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 seconds recv timeout (model load can be slow)

    try:
        print(f"[INFO] Sending 'stats' request to LLM adapter on tcp://{HOST}:{PORT} ...")
        socket.send_json({"action": "stats"})
        response = socket.recv_json()
        print("[INFO] Received response:\n" + json.dumps(response, indent=2))

        if response.get("status") == "success":
            model = response.get("model_name", "N/A")
            device = response.get("device", "N/A")
            print(f"[INFO] Adapter is up. Model: {model} | Device: {device}")
            if device == "cuda":
                print("[INFO] PyTorch with CUDA appears functional.")
            elif device == "cpu":
                print("[WARNING] Adapter running on CPU; ensure GPU is available if desired.")
            return True
        else:
            print("[ERROR] Adapter responded with non-success status.")
            return False
    except zmq.error.Again:
        print("[ERROR] Timeout waiting for adapter response. Adapter may be loading or unresponsive.")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False
    finally:
        socket.close()
        context.term()


if __name__ == "__main__":
    success = check_adapter_status()
    exit(0 if success else 1)
