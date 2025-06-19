import zmq
import sys
import json
import time

def health_check(host, port):
    ctx = zmq.Context()
    sock = ctx.socket(zmq.REQ)
    sock.connect(f"tcp://{host}:{port}")
    try:
        sock.send_json({'action': 'health_check'})
        if sock.poll(3000):  # 3 second timeout
            resp = sock.recv_json()
            print(json.dumps(resp, indent=2))
        else:
            print('{"error": "Timeout waiting for response"}')
    finally:
        sock.close()
        ctx.term()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 health_check_client.py <host> <port>")
        sys.exit(1)
    health_check(sys.argv[1], int(sys.argv[2])) 