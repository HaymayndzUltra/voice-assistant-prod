import json
import zmq
import time
import threading
from pathlib import Path

# Contract test for APC multipart framing and EmotionalContext schema
# Preconditions: APC publisher topic 'affect' on port 5591 (or resolved via config)

APC_PUB_ADDR = "tcp://127.0.0.1:5591"
TOPIC = b"affect"

# Minimal EmotionalContext-like payload per unified schema
EC_SAMPLE = {
    "version": "1.0",
    "timestamp": "2025-01-01T00:00:00Z",
    "emotion_vector": [0.1, 0.2, 0.7],
    "primary_emotion": "happy",
    "emotion_confidence": 0.92,
    "valence": 0.6,
    "arousal": 0.5,
    "module_contributions": {"audio": 0.3, "text": 0.4, "face": 0.3},
    "processing_latency_ms": 12.5,
    "metadata": {"source": "affective_processing_center", "vector_dim": 3, "contributing_modules": ["audio", "text", "face"]},
}


def _publisher_thread(stop_evt):
    ctx = zmq.Context.instance()
    s = ctx.socket(zmq.PUB)
    s.bind("tcp://127.0.0.1:0")  # bind dynamic for isolation
    endpoint = s.getsockopt_string(zmq.LAST_ENDPOINT)
    # Publish a few frames to allow subscriber to connect
    for _ in range(5):
        s.send_multipart([TOPIC, json.dumps(EC_SAMPLE).encode("utf-8")])
        time.sleep(0.1)
    stop_evt.set()
    s.close(0)


def test_apc_multipart_contract():
    # Subscriber should receive [topic, json] framing
    ctx = zmq.Context.instance()
    sub = ctx.socket(zmq.SUB)
    sub.setsockopt_string(zmq.SUBSCRIBE, TOPIC.decode("utf-8"))
    # Bind local publisher
    stop_evt = threading.Event()
    t = threading.Thread(target=_publisher_thread, args=(stop_evt,), daemon=True)
    t.start()

    # Connect to local publisher
    sub.connect(APC_PUB_ADDR)  # In CI, route via a bridge or inject

    try:
        topic, payload = sub.recv_multipart(flags=0)
        assert topic == TOPIC
        data = json.loads(payload.decode("utf-8"))
        # Validate required EmotionalContext keys
        for k in [
            "emotion_vector",
            "primary_emotion",
            "emotion_confidence",
            "valence",
            "arousal",
            "module_contributions",
            "processing_latency_ms",
        ]:
            assert k in data, f"Missing key {k} in EmotionalContext payload"
    finally:
        sub.close(0)
        stop_evt.wait(timeout=1.0)