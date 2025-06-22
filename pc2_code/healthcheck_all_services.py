import zmq
import json
import time

# List of agents from start_all_pc2_agents.bat with likely ports
SOT = [
  {"service_name": "Enhanced Model Router", "port": 5598, "health_check_payload": {"action": "health_check"}},
  {"service_name": "Advanced Router", "port": 5599, "health_check_payload": {"action": "health_check"}},
  {"service_name": "Unified Memory Reasoning Agent", "port": 5591, "health_check_payload": {"action": "health_check"}},
  {"service_name": "Memory Decay Manager", "port": 5592, "health_check_payload": {"action": "health_check"}},
  {"service_name": "Episodic Memory Agent", "port": 5593, "health_check_payload": {"action": "health_check"}},
  {"service_name": "Cognitive Model Agent", "port": 5594, "health_check_payload": {"action": "health_check"}},
  {"service_name": "Learning Adjuster Agent", "port": 5595, "health_check_payload": {"action": "health_check"}},
  {"service_name": "Self Training Orchestrator", "port": 5596, "health_check_payload": {"action": "health_check"}},
  {"service_name": "Dream World Agent", "port": 5597, "health_check_payload": {"action": "health_check"}},
  {"service_name": "Dreaming Mode Agent", "port": 5601, "health_check_payload": {"action": "health_check"}},
  {"service_name": "Agent Trust Scorer", "port": 5602, "health_check_payload": {"action": "health_check"}},
  {"service_name": "TinyLLaMA Service", "port": 5615, "health_check_payload": {"action": "health_check"}},
  {"service_name": "Self Healing Agent", "port": 5614, "health_check_payload": {"action": "health_check"}},
  {"service_name": "Performance Logger Agent", "port": 5603, "health_check_payload": {"action": "health_check"}},
  {"service_name": "Unified Web Agent", "port": 5604, "health_check_payload": {"action": "health_check"}},
  {"service_name": "Remote Connector Agent", "port": 5557, "health_check_payload": {"action": "health_check"}},
  {"service_name": "Consolidated Translator", "port": 5563, "health_check_payload": {"action": "health_check"}},
  {"service_name": "Filesystem Assistant Agent", "port": 5605, "health_check_payload": {"action": "health_check"}},
  {"service_name": "Tutoring Service Agent", "port": 5606, "health_check_payload": {"action": "health_check"}},
]

results = []

context = zmq.Context()
for entry in SOT:
    name = entry["service_name"]
    port = entry["port"]
    payload = entry["health_check_payload"]
    addr = f"tcp://127.0.0.1:{port}"
    sock = context.socket(zmq.REQ)
    sock.setsockopt(zmq.LINGER, 0)
    sock.setsockopt(zmq.RCVTIMEO, 2000)
    sock.setsockopt(zmq.SNDTIMEO, 2000)
    try:
        sock.connect(addr)
        sock.send_string(json.dumps(payload))
        resp = sock.recv_string()
        try:
            resp_json = json.loads(resp)
            if resp_json.get("status") in ("ok", "success", "healthy") or resp_json.get("service") or resp_json.get("available") is not False:
                results.append({"Service Name": name, "Port": port, "Health Check Payload Used": payload, "Health Check Result": "Healthy"})
            else:
                results.append({"Service Name": name, "Port": port, "Health Check Payload Used": payload, "Health Check Result": f"Unhealthy: {resp_json}"})
        except Exception:
            results.append({"Service Name": name, "Port": port, "Health Check Payload Used": payload, "Health Check Result": f"Invalid JSON: {resp}"})
    except Exception as e:
        results.append({"Service Name": name, "Port": port, "Health Check Payload Used": payload, "Health Check Result": f"No response ({e})"})
    finally:
        sock.close()
context.term()

with open("healthcheck_all_services_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("HEALTH CHECK COMPLETE. Results saved to healthcheck_all_services_results.json.")
