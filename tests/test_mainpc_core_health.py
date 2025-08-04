# tests/test_mainpc_core_health.py
import requests, pytest, time, os

SERVICES = {
    "coordination": 51100,
    "emotion_system": 51200,
    "infra_core": 51300,
    "language_stack": 51400,
    "learning_gpu": 51500,
    "memory_stack": 51600,
    "reasoning_gpu": 51700,
    "speech_gpu": 51800,
    "translation_services": 51900,
    "utility_cpu": 52000,
    "vision_gpu": 52100,
}

@pytest.mark.parametrize("svc,port", SERVICES.items())
def test_health_endpoints(svc, port):
    r = requests.get(f"http://localhost:{port}/health", timeout=5)
    assert r.status_code == 200, f"{svc} unhealthy"
    assert r.json().get("status") == "ok"

def test_trace_ingestion():
    r = requests.get("http://localhost:51400/demo/ping", timeout=5)
    trace_id = r.headers.get("trace-id")
    assert trace_id, "trace header missing"
    time.sleep(2)
    obs = requests.get(f"http://localhost:5601/traces/{trace_id}", timeout=5)
    assert obs.status_code == 200
