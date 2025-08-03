# tests/test_inter_service.py
import requests, json, os, time

def test_memory_to_async_pipeline():
    payload = {"cmd": "status"}
    r = requests.post("http://localhost:50100/async/status", json=payload, timeout=5)
    assert r.status_code == 200
    assert r.json()["memory_ok"]

def test_observability_trace():
    # Call tutoring CPU, then query ObservabilityHub to verify trace ingestion
    r = requests.get("http://localhost:50400/health", timeout=5)
    assert r.status_code == 200
    trace_id = r.headers.get("trace-id")
    time.sleep(2)
    obs = requests.get(f"http://observabilityhub:5601/traces/{trace_id}", timeout=5)
    assert obs.status_code == 200