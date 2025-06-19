import zmq
import logging

logging.basicConfig(level=logging.INFO)
BRIDGE_ADDR = "tcp://192.168.1.27:5600"  # Main PC IP (update if needed)
TEST_MESSAGE = b"ping_from_pc2"

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect(BRIDGE_ADDR)

logging.info(f"Sending test message to ZMQ Bridge at {BRIDGE_ADDR}")
socket.send(TEST_MESSAGE)

try:
    if socket.poll(3000, zmq.POLLIN):
        reply = socket.recv()
        logging.info(f"Received reply: {reply}")
        with open("PC2_DISTRIBUTED_TEST_RESULT.log", "w") as f:
            f.write(f"SUCCESS: Received reply: {reply.decode(errors='ignore')}\n")
    else:
        logging.error("No reply from bridge (timeout)")
        with open("PC2_DISTRIBUTED_TEST_RESULT.log", "w") as f:
            f.write("FAIL: No reply from bridge (timeout)\n")
except Exception as e:
    logging.error(f"Exception during distributed test: {e}")
    with open("PC2_DISTRIBUTED_TEST_RESULT.log", "w") as f:
        f.write(f"FAIL: Exception {e}\n")
finally:
    socket.close()
    context.term()
