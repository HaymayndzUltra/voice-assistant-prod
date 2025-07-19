import zmq
import json
import time
from main_pc_code.utils.config_loader import load_config

config = load_config()

# Ports from config
LOD_PORT = config.get('lod_port', 7200)
LOS_PORT = config.get('los_port', 7210)
MEF_PORT = config.get('mef_port', 7220)
LOD_HEALTH = config.get('lod_health_port', 7201)
LOS_HEALTH = config.get('los_health_port', 7211)
MEF_HEALTH = config.get('mef_health_port', 7221)

# Helper to send/receive ZMQ REQ/REP

def zmq_request(port, payload, timeout=5000):
    ctx = zmq.Context()
    sock = ctx.socket(zmq.REQ)
    sock.setsockopt(zmq.RCVTIMEO, timeout)
    sock.setsockopt(zmq.SNDTIMEO, timeout)
    sock.connect(f"tcp://localhost:{port}")
    try:
        sock.send_json(payload)
        resp = sock.recv_json()
    except Exception as e:
        resp = {'status': 'error', 'message': str(e)}
    sock.close()
    ctx.term()
    return resp

# 1. Health checks
print("[TEST] Health check: LOD")
print(zmq_request(LOD_HEALTH, {}))
print("[TEST] Health check: LOS")
print(zmq_request(LOS_HEALTH, {}))
print("[TEST] Health check: MEF")
print(zmq_request(MEF_HEALTH, {}))

# 2. Simulate a learning opportunity to LOD
print("[TEST] Send learning opportunity to LOD")
learning_opportunity = {
    'user_query': "What is the capital of France?",
    'agent_response': "The capital of France is Berlin.",
    'user_correction': "No, it's Paris.",
    'timestamp': time.time()
}
# LOD expects interactions via its monitored sockets, but for test, call handle_request directly
lod_payload = {
    'action': 'test_inject_interaction',
    'interaction': learning_opportunity
}
resp = zmq_request(LOD_PORT, lod_payload)
print(resp)

# 3. Check LOS for new training cycle
print("[TEST] Get training cycles from LOS")
los_payload = {'action': 'get_training_cycles', 'limit': 5}
resp = zmq_request(LOS_PORT, los_payload)
print(resp)

# 4. Log a model evaluation score to MEF
print("[TEST] Log model evaluation score to MEF")
from uuid import uuid4
from datetime import datetime
from common.env_helpers import get_env
model_eval = {
    'evaluation': {
        'evaluation_id': str(uuid4()),
        'model_name': 'ChitChatLLM_v2',
        'cycle_id': str(uuid4()),
        'trust_score': 0.92,
        'accuracy': 0.89,
        'f1_score': 0.87,
        'avg_latency_ms': 120.5,
        'evaluation_timestamp': datetime.utcnow().isoformat(),
        'comparison_data': {'previous_version': 'ChitChatLLM_v1', 'trust_score_delta': 0.05}
    }
}
resp = zmq_request(MEF_PORT, {'action': 'log_model_evaluation', **model_eval})
print(resp)

# 5. Retrieve model evaluation scores from MEF
print("[TEST] Get model evaluation scores from MEF")
get_eval = {'action': 'get_model_evaluation_scores', 'model_name': 'ChitChatLLM_v2', 'limit': 3}
resp = zmq_request(MEF_PORT, get_eval)
print(resp)

# 6. Simulate error reporting (send a fake error to the error bus)
print("[TEST] Simulate error reporting to Error Bus")
try:
    ctx = zmq.Context()
    pub = ctx.socket(zmq.PUB)
    error_bus_port = config.get('error_bus_port', 7150)
    pub.connect(f"tcp://localhost:{error_bus_port}")
    error_event = {
        'type': 'test_error',
        'message': 'This is a test error from integration test',
        'severity': 'ERROR',
        'timestamp': time.time()
    }
    # Topic is 'ERROR:'
    pub.send_string('ERROR:', zmq.SNDMORE)
    pub.send_json(error_event)
    print("Error event published to Error Bus.")
    pub.close()
    ctx.term()
except Exception as e:
    print(f"Error publishing to Error Bus: {e}")

print("[TEST] Integration test complete.") 