import os
import random
import signal
import sys
import time
import zmq
import logging

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("ModelManagerRouter")

# Mapping of FRONTEND_PORT -> {"legacy": backend_port, "suite": suite_port}
# All backends are assumed to live on localhost within the Docker overlay network.
FRONTENDS = {
    5570: {"legacy": 5570, "suite": 7211},  # ModelManagerAgent ⇔ ModelManagerSuite
    5575: {"legacy": 5575, "suite": 7211},  # GGUFModelManager  ⇔ ModelManagerSuite
    5617: {"legacy": 5617, "suite": 7211},  # PredictiveLoader  ⇔ ModelManagerSuite
    7222: {"legacy": 7222, "suite": 7211},  # ModelEvaluationFramework ⇔ ModelManagerSuite
}

TRAFFIC_PERCENT_VAR = "SUITE_TRAFFIC_PERCENT"
DEFAULT_PERCENT = 5  # Start with 5 % traffic to the suite


def get_suite_percentage() -> int:
    """Return current percentage of traffic to route to the Suite."""
    try:
        return int(os.getenv(TRAFFIC_PERCENT_VAR, DEFAULT_PERCENT))
    except ValueError:
        return DEFAULT_PERCENT


def graceful_exit(signum, frame):
    logger.info("Received signal %s – shutting down router gracefully…", signum)
    sys.exit(0)


for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, graceful_exit)

logger.info("Starting ModelManager Router – initial suite traffic %s%%", get_suite_percentage())

ctx = zmq.Context.instance()

# Prepare poller for all frontend sockets
poller = zmq.Poller()
frontend_sockets = {}

for port in FRONTENDS.keys():
    sock = ctx.socket(zmq.REP)
    sock.bind(f"tcp://*:{port}")
    poller.register(sock, zmq.POLLIN)
    frontend_sockets[sock] = port
    logger.info("Listening on tcp://*:%s", port)


def route_message(front_socket):
    """Forward request to appropriate backend and proxy reply back."""
    port = frontend_sockets[front_socket]
    message = front_socket.recv_multipart()

    # Decide routing
    suite_share = get_suite_percentage()
    send_to_suite = random.randint(1, 100) <= suite_share
    backend_port = FRONTENDS[port]["suite" if send_to_suite else "legacy"]
    backend_addr = f"tcp://localhost:{backend_port}"

    logger.debug("Port %s → backend %s (suite=%s)", port, backend_port, send_to_suite)

    # Simple REQ → REP round-trip to backend
    backend_socket = ctx.socket(zmq.REQ)
    backend_socket.connect(backend_addr)
    backend_socket.send_multipart(message)
    reply = backend_socket.recv_multipart()
    frontend_socket.send_multipart(reply)
    backend_socket.close()


while True:
    events = dict(poller.poll(1000))
    for sock in events:
        if events[sock] == zmq.POLLIN:
            route_message(sock)