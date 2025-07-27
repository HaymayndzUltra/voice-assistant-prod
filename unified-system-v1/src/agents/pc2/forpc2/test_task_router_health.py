import zmq
import json
import time
from common.env_helpers import get_env
from common.config_manager import get_service_ip, get_service_url, get_redis_url

# CONFIGURE THESE:
MAIN_PC_IP = "localhost"  # Palitan ng actual IP ng main PC kung remote
TASK_ROUTER_PORT = 8571    # Testing port 8571

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect(f"tcp://{MAIN_PC_IP}:{TASK_ROUTER_PORT}")

# Send health check request
socket.send_json({"type": "health_check"})

# Wait for response
try:
    # Wait up to 3 seconds
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)
    socks = dict(poller.poll(3000))
    if socks.get(socket) == zmq.POLLIN:
        response = socket.recv_json()
        print("Task Router Health Response:", response)
    else:
        print("No response from Task Router (timeout)")
except Exception as e:
    print("Error during health check:", e) 