import zmq
import time
import json
import os
import sys
from pathlib import Path
from zmq.utils import z85

# Add project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# --- CONFIGURATION ---
SDT_HOST = "127.0.0.1"
SDT_PORT = 7120
CONNECTION_TIMEOUT_S = 30  # 30 seconds should be sufficient with our fix
DEBUG = True
# ---------------------

def create_temporary_certificates():
    try:
        import zmq.auth
    except ImportError as e:
        print(f"Import error: {e}")
        certs_dir = project_root / "certificates"
        certs_dir.mkdir(exist_ok=True)

        client_public, client_secret = zmq.curve_keypair()
        server_public, server_secret = zmq.curve_keypair()

        client_public_z85 = z85.encode(client_public).decode()
        client_secret_z85 = z85.encode(client_secret).decode()
        server_public_z85 = z85.encode(server_public).decode()
        server_secret_z85 = z85.encode(server_secret).decode()

        with open(certs_dir / "client.key", "w") as f:
            f.write(client_public_z85)
        with open(certs_dir / "client.key_secret", "w") as f:
            f.write(client_secret_z85)
        with open(certs_dir / "server.key", "w") as f:
            f.write(server_public_z85)
        with open(certs_dir / "server.key_secret", "w") as f:
            f.write(server_secret_z85)

        print("✅ Temporary certificates created successfully.")
        return client_public_z85.encode(), client_secret_z85.encode(), server_public_z85.encode()
    except Exception as e:
        print(f"❌ Error creating temporary certificates: {e}")
        return None, None, None

def clean_temporary_certificates():
    try:
        certs_dir = project_root / "certificates"
        if certs_dir.exists():
            for cert_file in ["client.key", "client.key_secret", "server.key", "server.key_secret"]:
                cert_path = certs_dir / cert_file
                if cert_path.exists():
                    cert_path.unlink()
            print("🧹 Temporary certificates cleaned up.")
    except Exception as e:
        print(f"❌ Error cleaning up certificates: {e}")

def test_local_sdt_connection():
    client_public_key = None
    client_secret_key = None
    server_public_key = None
    secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"

    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, 5000)
        socket.setsockopt(zmq.SNDTIMEO, 5000)

        if DEBUG:
            print(f"ZMQ Version: {zmq.zmq_version()}")
            print(f"PyZMQ Version: {zmq.__version__}")

        if secure_zmq:
            certs_dir = project_root / "certificates"
            client_public_key, client_secret_key, server_public_key = create_temporary_certificates()

            if client_public_key and client_secret_key and server_public_key:
                print("🔐 Configuring socket for secure ZMQ connection...")
                socket.curve_secretkey = client_secret_key
                socket.curve_publickey = client_public_key
                socket.curve_serverkey = server_public_key
            else:
                print("⚠️ Failed to create certificates, falling back to non-secure ZMQ.")
                secure_zmq = False
        else:
            print("📡 Using standard non-secure ZMQ.")

        target_address = f"tcp://{SDT_HOST}:{SDT_PORT}"
        print(f"🌐 Connecting to {'SECURE ' if secure_zmq else ''}SystemDigitalTwin at {target_address}...")
        socket.connect(target_address)

        ping_message = {"action": "ping"}
        print(f"📤 Sending health check: {ping_message}")
        socket.send_json(ping_message)

        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        start_time = time.time()
        elapsed = 0

        while elapsed < CONNECTION_TIMEOUT_S:
            socks = dict(poller.poll(1000))
            elapsed = time.time() - start_time
            if socket in socks and socks[socket] == zmq.POLLIN:
                try:
                    message = socket.recv_json()
                    print(f"✅ SUCCESS: Received reply:\n{json.dumps(message, indent=2)}")
                    return True
                except zmq.ZMQError as e:
                    print(f"❌ ZMQ error receiving reply: {e}")
                    break
            print(f"⌛ Waiting... {elapsed:.2f}s elapsed")

        print(f"❌ TIMEOUT: No reply in {CONNECTION_TIMEOUT_S} seconds.")
        return False

    finally:
        print("🔚 Cleaning up...")
        if 'socket' in locals():
            socket.close()
        if 'context' in locals():
            context.term()
        if secure_zmq:
            clean_temporary_certificates()

def send_direct_ping():
    print("\n🚀 Trying direct string-based ping...")
    context = zmq.Context()
    socket = context.socket(zmq.REQ)

    try:
        socket.connect(f"tcp://{SDT_HOST}:{SDT_PORT}")
        socket.send_string("ping")
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)

        start_time = time.time()
        elapsed = 0

        while elapsed < CONNECTION_TIMEOUT_S:
            result = dict(poller.poll(1000))
            elapsed = time.time() - start_time
            if socket in result:
                try:
                    reply = socket.recv_string()
                    print(f"✅ Received: {reply}")
                    return True
                except zmq.ZMQError as e:
                    print(f"❌ Error receiving direct ping: {e}")
                    break
            print(f"⌛ Waiting (direct)... {elapsed:.2f}s")

        print(f"❌ No reply after {elapsed:.2f}s (direct ping)")
        return False
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    print("=== SystemDigitalTwin Connection Test ===")
    secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
    print(f"Secure ZMQ mode: {'✅ ENABLED' if secure_zmq else '❌ DISABLED'}")
    print("To enable: export SECURE_ZMQ=1")
    print("To disable: export SECURE_ZMQ=0\n")

    print("Testing connection to SystemDigitalTwin...")
    success = test_local_sdt_connection()
    if not success:
        send_direct_ping() 