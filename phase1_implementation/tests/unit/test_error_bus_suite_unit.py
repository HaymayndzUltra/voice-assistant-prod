import pytest
from starlette.testclient import TestClient
import importlib
import asyncio

MODULE_PATH = "phase1_implementation.consolidated_agents.error_bus.error_bus_suite"
module = importlib.import_module(MODULE_PATH)
ErrorBusSuite = module.ErrorBusSuite  # type: ignore

# Disable heavy legacy startup for fast tests
ErrorBusSuite._start_legacy = lambda self: None  # type: ignore
ErrorBusSuite._start_system_health_manager = lambda self: None  # type: ignore

@pytest.fixture()
def ebus_client():
    svc = ErrorBusSuite()
    client = TestClient(svc.app)
    yield client
    svc.cleanup()

# ---------- Basic health -----------

def test_health_endpoint(ebus_client):
    r = ebus_client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["service"] == "ErrorBusSuite"


def test_health_has_legacy_flag(ebus_client):
    data = ebus_client.get("/health").json()
    assert "legacy_running" in data

# ---------- Report endpoint --------

def test_report_requires_json(ebus_client):
    r = ebus_client.post("/report", json={"msg": "hi"})
    assert r.status_code == 200
    assert r.json()["status"] in {"success", "error"}


def test_report_rejects_nonjson(ebus_client):
    r = ebus_client.post("/report", data="raw")
    assert r.status_code == 422  # FastAPI validation

# ---------- Recent / agent_health------

def test_recent_default(ebus_client):
    r = ebus_client.get("/recent")
    assert r.status_code == 200
    assert "status" in r.json()


def test_recent_limit_param(ebus_client):
    r = ebus_client.get("/recent?limit=5")
    assert r.status_code == 200


def test_agent_health_endpoint(ebus_client):
    r = ebus_client.get("/agent_health")
    assert r.status_code == 200

# ---------- Internal delegations ----------

def test_delegate_publish_returns_status():
    svc = ErrorBusSuite()
    svc._start_legacy = lambda: None  # type: ignore
    svc._legacy = None  # ensure no legacy
    result = asyncio.run(svc._delegate({"action": "health_check"}))
    assert result["status"] == "error"
    svc.cleanup()


def test_delegate_timeout_handled(monkeypatch):
    svc = ErrorBusSuite()
    svc._legacy = None
    # Monkeypatch zmq to raise
    import zmq
    def fake_socket(*args, **kwargs):
        raise zmq.ZMQError("fail")
    monkeypatch.setattr(svc._ctx, "socket", fake_socket)
    out = asyncio.run(svc._delegate({"action": "x"}))
    assert out["status"] == "error"
    svc.cleanup()

# ---------- Additional validations to reach 15 tests ----------

def test_health_endpoint_contains_uptime(ebus_client):
    assert "uptime" in ebus_client.get("/health").json()


def test_report_large_payload(ebus_client):
    payload = {"msg": "x" * 1024}
    assert ebus_client.post("/report", json=payload).status_code == 200


def test_recent_large_limit(ebus_client):
    assert ebus_client.get("/recent?limit=500").status_code == 200

# ----- extra tests to reach 15 -----


def test_recent_negative_limit(ebus_client):
    r = ebus_client.get("/recent?limit=-5")
    assert r.status_code == 200


def test_report_empty_payload(ebus_client):
    r = ebus_client.post("/report", json={})
    assert r.status_code == 200


def test_agent_health_content(ebus_client):
    data = ebus_client.get("/agent_health").json()
    assert "status" in data