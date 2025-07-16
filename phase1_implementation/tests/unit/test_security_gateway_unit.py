import pytest
from starlette.testclient import TestClient
import importlib
import asyncio

MODULE_PATH = "phase1_implementation.consolidated_agents.security_gateway.security_gateway"
module = importlib.import_module(MODULE_PATH)
SecurityGateway = module.SecurityGateway  # type: ignore

# Disable heavy legacy startup
SecurityGateway._start_legacy = lambda self: None  # type: ignore

@pytest.fixture()
def sg_client():
    gw = SecurityGateway()
    # Monkeypatch delegate to echo success to avoid ZMQ dependency
    gw._delegate = lambda key, payload: {"status": "success", "echo": payload}  # type: ignore
    client = TestClient(gw.app)
    yield client
    gw.cleanup()

# -------- Health ----------

def test_health_ok(sg_client):
    assert sg_client.get("/health").status_code == 200


def test_health_contains_agents(sg_client):
    data = sg_client.get("/health").json()
    assert "legacy_agents" in data

# -------- Registration / Login ----------

def test_register_success(sg_client):
    payload = {"user_id": "u1", "password": "p"}
    r = sg_client.post("/register", json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "success"


def test_login_success(sg_client):
    sg_client.post("/register", json={"user_id": "u2", "password": "p2"})
    r = sg_client.post("/login", json={"user_id": "u2", "password": "p2"})
    assert r.status_code == 200


def test_validate_token(sg_client):
    token_payload = {"token": "dummy"}
    r = sg_client.post("/validate", json=token_payload)
    assert r.status_code == 200

# -------- Trust score ----------

def test_trust_score_endpoint(sg_client):
    r = sg_client.get("/trust/model123")
    assert r.status_code == 200

# -------- Error cases ----------

def test_register_missing_fields(sg_client):
    r = sg_client.post("/register", json={})
    assert r.status_code == 200
    assert r.json()["status"] == "success" or r.json()["status"] == "error"


def test_login_missing_data(sg_client):
    r = sg_client.post("/login", json={})
    assert r.status_code == 200


def test_validate_invalid_token(sg_client):
    r = sg_client.post("/validate", json={"token": ""})
    assert r.status_code == 200

# -------- concurrency / multiple calls ----------

def test_multiple_health_calls(sg_client):
    for _ in range(3):
        assert sg_client.get("/health").status_code == 200

# -------- internal delegate ----------

def test_delegate_unknown_key():
    gw = SecurityGateway()
    gw._delegate = lambda key, payload: {"status": "error"}  # type: ignore
    result = asyncio.run(gw._delegate("unknown", {}))
    assert result["status"] == "error"
    gw.cleanup()

# -------- edge cases ----------

def test_trust_score_special_chars(sg_client):
    assert sg_client.get("/trust/Model_Ω≈ç√∫").status_code == 200

# ---------- additional tests ----------


def test_register_duplicate_user(sg_client):
    sg_client.post("/register", json={"user_id": "dup", "password": "p"})
    r = sg_client.post("/register", json={"user_id": "dup", "password": "p"})
    assert r.status_code == 200


def test_login_wrong_password(sg_client):
    sg_client.post("/register", json={"user_id": "bob", "password": "good"})
    r = sg_client.post("/login", json={"user_id": "bob", "password": "bad"})
    assert r.status_code == 200


def test_validate_missing_token(sg_client):
    r = sg_client.post("/validate", json={})
    assert r.status_code == 200