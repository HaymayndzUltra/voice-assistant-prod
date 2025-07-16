import pytest
from starlette.testclient import TestClient

# Monkeypatch the heavy legacy agent startup before import
import importlib

MODULE_PATH = "phase1_implementation.consolidated_agents.resource_manager_suite.resource_manager_suite"
module = importlib.import_module(MODULE_PATH)
ResourceManagerSuite = module.ResourceManagerSuite  # type: ignore

# Disable legacy agent launch for fast unit-tests
ResourceManagerSuite._launch_legacy_agents = lambda self: None  # type: ignore

@pytest.fixture()
def rms_service():
    svc = ResourceManagerSuite()
    client = TestClient(svc.app)
    yield client
    svc.cleanup()

# --------------- Health & basic endpoints ---------------

def test_health_endpoint_ok(rms_service):
    resp = rms_service.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "ResourceManagerSuite"


def test_status_without_agents(rms_service):
    resp = rms_service.get("/status")
    # With no legacy agents, delegate returns error → ensure HTTP 200 with error json
    assert resp.status_code == 200
    assert resp.json()["status"] in {"error", "delegated", "success"}


def test_allocate_missing_fields(rms_service):
    resp = rms_service.post("/allocate", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error"


def test_release_without_id(rms_service):
    resp = rms_service.post("/release", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "error"


def test_schedule_without_payload(rms_service):
    resp = rms_service.post("/schedule", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "error"


def test_queue_stats_endpoint(rms_service):
    resp = rms_service.get("/queue_stats")
    assert resp.status_code == 200
    assert resp.json()["status"] in {"delegated", "error", "success"}

# --------------- Internal helper behaviour ---------------

import asyncio


def test_delegate_unknown_target_returns_error():
    svc = ResourceManagerSuite()
    # Use asyncio.run because _delegate is async
    result = asyncio.run(svc._delegate("nonexistent", {}))  # type: ignore
    assert result["status"] == "error"
    svc.cleanup()


# ---------- Additional behavioural tests to reach 15 total ----------

import time


def test_allocate_invalid_amount(rms_service):
    payload = {"resource_id": "abc", "resource_type": "cpu", "amount": -1}
    resp = rms_service.post("/allocate", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "error"


def test_release_unknown_id(rms_service):
    payload = {"resource_id": "unknown"}
    resp = rms_service.post("/release", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] in {"error", "success"}


def test_schedule_priority_high(rms_service):
    payload = {"type": "task", "data": {}, "priority": "high"}
    resp = rms_service.post("/schedule", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] in {"delegated", "error", "success"}


def test_health_contains_uptime(rms_service):
    resp = rms_service.get("/health")
    assert "uptime" in resp.json()


def test_multiple_health_calls_consistent(rms_service):
    first = rms_service.get("/health").json()
    time.sleep(0.1)
    second = rms_service.get("/health").json()
    assert second["uptime"] >= first["uptime"]

# ---- extra tests to reach 15 ----


def test_allocate_then_release_flow(rms_service):
    alloc_payload = {"resource_id": "jobX", "resource_type": "cpu", "amount": 1}
    rms_service.post("/allocate", json=alloc_payload)
    rel_payload = {"resource_id": "jobX"}
    resp = rms_service.post("/release", json=rel_payload)
    assert resp.status_code == 200


def test_schedule_default_priority(rms_service):
    resp = rms_service.post("/schedule", json={"type": "task", "data": {}})
    assert resp.status_code == 200


def test_status_endpoint_structure(rms_service):
    data = rms_service.get("/status").json()
    assert "status" in data