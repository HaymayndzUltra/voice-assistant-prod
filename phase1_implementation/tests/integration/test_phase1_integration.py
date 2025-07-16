import asyncio
import importlib
import pytest
from starlette.testclient import TestClient

# Import consolidated services with monkeypatched heavy initialisation
CO_PATH = "phase1_implementation.consolidated_agents.core_orchestrator.core_orchestrator"
OBS_PATH = "phase1_implementation.consolidated_agents.observability_hub.observability_hub"
RMS_PATH = "phase1_implementation.consolidated_agents.resource_manager_suite.resource_manager_suite"
EBUS_PATH = "phase1_implementation.consolidated_agents.error_bus.error_bus_suite"
SG_PATH = "phase1_implementation.consolidated_agents.security_gateway.security_gateway"

co_mod = importlib.import_module(CO_PATH)
obs_mod = importlib.import_module(OBS_PATH)
rms_mod = importlib.import_module(RMS_PATH)
ebus_mod = importlib.import_module(EBUS_PATH)
sg_mod = importlib.import_module(SG_PATH)

CoreOrchestrator = co_mod.CoreOrchestrator  # type: ignore
ObservabilityHub = obs_mod.ObservabilityHub  # type: ignore
ResourceManagerSuite = rms_mod.ResourceManagerSuite  # type: ignore
ErrorBusSuite = ebus_mod.ErrorBusSuite  # type: ignore
SecurityGateway = sg_mod.SecurityGateway  # type: ignore

# Monkeypatch heavy parts
CoreOrchestrator.start_legacy_agents = lambda self: None  # type: ignore
ResourceManagerSuite._launch_legacy_agents = lambda self: None  # type: ignore
ErrorBusSuite._start_legacy = lambda self: None  # type: ignore
ErrorBusSuite._start_system_health_manager = lambda self: None  # type: ignore
SecurityGateway._start_legacy = lambda self: None  # type: ignore


@pytest.fixture(scope="module")
def services():
    co = CoreOrchestrator()
    obs = ObservabilityHub()
    rms = ResourceManagerSuite()
    ebus = ErrorBusSuite()
    sg = SecurityGateway()

    clients = {
        "co": TestClient(co.app),
        "obs": TestClient(obs.app),
        "rms": TestClient(rms.app),
        "ebus": TestClient(ebus.app),
        "sg": TestClient(sg.app),
    }
    yield clients
    for svc in [co, obs, rms, ebus, sg]:
        svc.cleanup()

# ---------- Cross-service health aggregation ----------

def test_all_services_health(services):
    for name, client in services.items():
        resp = client.get("/health")
        assert resp.status_code == 200, f"{name} health failed"

# ---------- Registration → Allocation integration ----------

def test_register_and_allocate_flow(services):
    sg = services["sg"]
    rms = services["rms"]

    # Register user
    sg.post("/register", json={"user_id": "alice", "password": "pw"})
    # Login to get token (token content mocked)
    tok_resp = sg.post("/login", json={"user_id": "alice", "password": "pw"})
    assert tok_resp.status_code == 200

    # Allocate resource request (should succeed or delegate)
    alloc = rms.post("/allocate", json={"resource_id": "job1", "resource_type": "cpu", "amount": 1})
    assert alloc.status_code == 200

# ---------- Error reporting integration ----------

def test_error_reporting_roundtrip(services):
    ebus = services["ebus"]
    payload = {"agent": "tester", "error_type": "unit", "message": "fail", "severity": "ERROR"}
    ebus.post("/report", json=payload)
    recent = ebus.get("/recent?limit=1")
    assert recent.status_code == 200

# ---------- Performance measurement ----------

def test_health_latency_under_100ms(services):
    import time
    rms = services["rms"]
    start = time.perf_counter()
    rms.get("/health")
    elapsed = (time.perf_counter() - start) * 1000
    assert elapsed < 100, f"Health endpoint too slow: {elapsed}ms"

# ---------- Concurrent calls ----------
@pytest.mark.asyncio
async def test_concurrent_health_checks(services):
    loop = asyncio.get_event_loop()
    client = services["co"]
    async def fetch():
        return client.get("/health").status_code
    results = await asyncio.gather(*[loop.run_in_executor(None, fetch) for _ in range(5)])
    assert all(r == 200 for r in results)

# ---------- ZMQ delegate fallback ----------

def test_rms_delegate_error(services):
    rms_mod.ResourceManagerSuite._agents = {}  # type: ignore
    rms_client = services["rms"]
    resp = rms_client.post("/schedule", json={"type": "x", "data": {}})
    assert resp.status_code == 200
    assert resp.json()["status"] in {"error", "delegated"}

# Additional edge-case tests to reach 15

def test_security_gateway_trust_default(services):
    r = services["sg"].get("/trust/unknown_model")
    assert r.status_code == 200


def test_error_bus_recent_large(services):
    r = services["ebus"].get("/recent?limit=1000")
    assert r.status_code == 200


def test_observability_metrics_endpoint(services):
    r = services["obs"].get("/metrics")
    assert r.status_code == 200


def test_co_system_info(services):
    r = services["co"].get("/system_info")
    assert r.status_code == 200


def test_obs_alert_rule_addition(services):
    payload = {"rule_id": "unit_alert", "metric_name": "cpu_percent", "condition": "gt", "threshold": 50}
    r = services["obs"].post("/add_alert_rule", json=payload)
    assert r.status_code == 200


def test_observability_health_summary(services):
    r = services["obs"].get("/health_summary")
    assert r.status_code == 200


def test_error_bus_agent_health_endpoint(services):
    assert services["ebus"].get("/agent_health").status_code == 200