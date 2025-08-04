# tests/test_mainpc_inter_service_calls.py
import requests, pytest

CASES = [
    ("coordination", 51100, "/delegate", "language_stack", 51400),
    ("memory_stack", 51600, "/retrieve", "reasoning_gpu", 51700),
    ("utility_cpu", 52000, "/exec", "translation_services", 51900),
]

@pytest.mark.parametrize("src,src_p,endpoint,dst,dst_p", CASES)
def test_cross_calls(src, src_p, endpoint, dst, dst_p):
    payload = {"target": f"http://{dst}:{dst_p}/health"}
    r = requests.post(f"http://localhost:{src_p}{endpoint}", json=payload, timeout=6)
    assert r.status_code == 200
    assert r.json()["target_status"] == "ok"
