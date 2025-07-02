import zmq
import time

# --- CONFIGURATION ---
# The user will replace this with the actual IP address of PC2.
PC2_IP = "YOUR_PC2_IP_ADDRESS" 
SDT_PORT = 7120
CONNECTION_TIMEOUT_S = 3
# ---------------------

def test_sdt_connection():
    """
    Tests the connection to the SystemDigitalTwin on PC2.
    """
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    
    target_address = f"tcp://{PC2_IP}:{SDT_PORT}"
    print(f"Attempting to connect to SystemDigitalTwin at {target_address}...")

    try:
        # Set a timeout for the connection attempt itself if needed,
        # but polling is more robust for send/recv.
        socket.connect(target_address)
        
        # Send a ping message as JSON
        print("Sending ping request...")
        socket.send_json({"action": "ping"})

        # Use a poller to wait for a reply with a timeout
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        
        socks = dict(poller.poll(CONNECTION_TIMEOUT_S * 1000)) # poll expects milliseconds
        
        if socket in socks and socks[socket] == zmq.POLLIN:
            try:
                # Try to receive as JSON first
                message = socket.recv_json()
                print(f"SUCCESS: Received JSON reply from SystemDigitalTwin!")
                print(f"Status: {message.get('status', 'unknown')}")
                print(f"Agent: {message.get('agent', 'unknown')}")
                print(f"Port: {message.get('port', 'unknown')}")
                print(f"Metrics thread alive: {message.get('metrics_thread_alive', 'unknown')}")
            except zmq.ZMQError:
                # Fall back to string if not JSON
                message = socket.recv_string()
                print(f"SUCCESS: Received string reply: '{message}'")
        else:
            print(f"FAILURE: No reply received within {CONNECTION_TIMEOUT_S} seconds.")
            print("Please check:")
            print(f"1. Is SystemDigitalTwin running on PC2?")
            print(f"2. Is PC2 reachable at IP {PC2_IP}?")
            print(f"3. Is the agent bound to '0.0.0.0' and not 'localhost'?")
            print(f"4. Are there any firewalls blocking port {SDT_PORT}?")

    except zmq.ZMQError as e:
        print(f"FAILURE: An error occurred: {e}")
    finally:
        print("Closing socket and context.")
        socket.close()
        context.term()

if __name__ == "__main__":
    if PC2_IP == "YOUR_PC2_IP_ADDRESS":
        print("ERROR: Please edit this script and replace 'YOUR_PC2_IP_ADDRESS' with the actual IP of PC2.")
    else:
        test_sdt_connection() 