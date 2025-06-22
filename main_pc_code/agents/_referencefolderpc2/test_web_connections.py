import zmq
import time
import sys

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

def test_connection(port):
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
    socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
    try:
        socket.connect(f"tcp://localhost:{port}")
        socket.send_string("TEST")
        try:
            response = socket.recv_string(flags=zmq.NOBLOCK)
            print(f"✅ Successfully connected to port {port}")
            return True
        except zmq.error.Again:
            print(f"❌ No response from port {port}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to port {port}: {e}")
        return False
    finally:
        socket.close()
        context.term()

def main():
    # Test both web service ports
    ports = [5604, 5605]
    results = {port: test_connection(port) for port in ports}
    
    # Print summary
    print("\nConnection Test Summary:")
    for port, success in results.items():
        status = "Connected" if success else "Failed"
        print(f"Port {port}: {status}")
    
    # Exit with error if any connection failed
    if not all(results.values()):
        sys.exit(1)

if __name__ == "__main__":
    main() 