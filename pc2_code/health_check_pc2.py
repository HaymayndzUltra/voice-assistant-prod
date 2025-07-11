#!/usr/bin/env python3
"""Quick PC2 health checker for essential ZMQ services"""
import zmq
import json
import sys
from main_pc_code.utils.network_utils import get_zmq_connection_string, get_machine_ip
services = [
    ("primary_translator", 5563, {"action": "health_check"}),
    ("fallback_translator", 5564, {"action": "health_check"}),
    ("nllb_adapter", 5581, {"action": "health_check"}),
    ("tinyllama_service", 5615, {"action": "health_check"}),
    ("memory_main", 5590, {"action": "health_check"}),
    ("memory_health", 5598, {"action": "health_check"}),
    ("contextual_memory", 5596, {"action": "health_check"}),
    ("digital_twin", 5597, {"action": "health_check"}),
    ("error_pattern_memory", 5611, {"action": "health_check"}),
    ("context_summarizer", 5610, {"action": "health_check"}),
    ("cot_agent", 5612, {"action": "health_check"}),
    ("rca_agent", 5557, {"request_type": "check_status", "model": "phi3"}),
]
ctx = zmq.Context()
print("PC2 ESSENTIAL SERVICES QUICK HEALTH CHECK\n" + "="*45)
for name, port, payload in services:
    sock = ctx.socket(zmq.REQ)
    sock.setsockopt(zmq.RCVTIMEO, 1500)
    status = "UNKNOWN"
    resp = None
    try:
        sock.connect(get_zmq_connection_string({port}, "localhost")))
        sock.send_json(payload)
        resp = sock.recv_json()
        status = "ONLINE"
    except Exception as e:
        status = f"OFFLINE ({type(e).__name__})"
    finally:
        sock.close()
    print(f"{name.ljust(22)} | port {str(port).ljust(5)} | {status}")
    if resp is not None:
        print(f"  ↳ reply: {json.dumps(resp)[:120]}")
ctx.term()
