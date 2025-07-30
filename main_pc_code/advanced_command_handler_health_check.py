import zmq
import json

AGENT_PORT = 5710
HEALTH_PORT = AGENT_PORT + 1

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.setsockopt(zmq.RCVTIMEO, 5000)
socket.setsockopt(zmq.SNDTIMEO, 5000)
socket.connect(f"tcp://localhost:{HEALTH_PORT}")

request = {"action": "health"}
print(f"Sending health check to AdvancedCommandHandler on port {HEALTH_PORT}: {request}")
socket.send(json.dumps(request).encode("utf-8"))

try:
    response_bytes = socket.recv()
    response = json.loads(response_bytes.decode("utf-8"))
    print("Received response from AdvancedCommandHandler:")
    print(json.dumps(response, indent=2))
except Exception as e:
    print(f"Health check failed: {e}")
finally:
    socket.close()
    context.term() 