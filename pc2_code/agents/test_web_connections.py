import zmq
import time
import sys
from common.env_helpers import get_env
from common.config_manager import get_service_ip, get_service_url, get_redis_url

def test_connection(port):
    context = None  # Using pool
    socket = get_req_socket(endpoint).socket
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