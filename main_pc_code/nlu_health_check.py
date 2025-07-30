import zmq
import json

AGENT_PORT = 5709
HEALTH_PORT = AGENT_PORT + 1

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.setsockopt(zmq.RCVTIMEO, 5000)
socket.setsockopt(zmq.SNDTIMEO, 5000)
socket.connect(f"tcp://localhost:{HEALTH_PORT}")

request = {"action": "health_check"}
print(f"Sending health check to NLUAgent on port {HEALTH_PORT}: {request}")
socket.send_json(request)

try:
    response = socket.recv_json()
    print("Received response from NLUAgent:")
    print(json.dumps(response, indent=2))
except Exception as e:
    print(f"Health check failed: {e}")
finally:
    socket.close()
    context.term() 