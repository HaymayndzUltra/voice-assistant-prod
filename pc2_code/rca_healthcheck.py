import zmq
import json
import time

rca_addr = "tcp://localhost:5557"
ctx = zmq.Context()
sock = ctx.socket(zmq.REQ)
sock.setsockopt(zmq.RCVTIMEO, 3000)
sock.connect(rca_addr)

payload = {"request_type": "check_status", "model": "phi3"}
print(f"Sending: {payload}")
sock.send_json(payload)
try:
    resp = sock.recv_json()
    print(f"Received: {resp}")
except zmq.error.Again:
    print("Timeout: No response from RCA on 5557")
finally:
    sock.close()
    ctx.term()
