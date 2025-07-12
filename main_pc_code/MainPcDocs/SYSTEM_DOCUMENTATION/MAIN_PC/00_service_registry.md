# Service Registry Agent

**Agent Name:** `ServiceRegistry`

| Property  | Value |
|-----------|-------|
| Script Path | `main_pc_code/agents/service_registry_agent.py` |
| Main Port | **7100** |
| Health Port | **8100** |
| Required | `true` |

---

## Overview
The Service Registry is a minimal, always‐on component that allows agents to discover
one another without coupling to the `SystemDigitalTwinAgent`.  By isolating
service discovery, we reduce the blast-radius in case the Digital-Twin becomes
overloaded or unavailable.

### Core Responsibilities
* **register_agent** – Agents call this endpoint to advertise their host/port.
* **get_agent_endpoint** – Agents query this endpoint to resolve another agent’s endpoint.
* **Health** – Standard `ping`, `health`, or `health_check` actions report a JSON
  health payload.

All data are held in-memory, making the registry extremely fast.  Future phases
will introduce optional Redis/SQLite persistence.

---

## API Reference
### 1. Register Agent
```
Request:
{
  "action": "register_agent",
  "agent_id": "ModelManagerAgent",
  "host": "model-manager",
  "port": 5570,
  "health_check_port": 6570,
  "capabilities": ["load_model", "unload_model"],
  "metadata": {"owner": "infra"}
}

Response:
{"status": "success"}
```

### 2. Get Agent Endpoint
```
Request:
{
  "action": "get_agent_endpoint",
  "agent_name": "ModelManagerAgent"
}

Response:
{
  "status": "success",
  "host": "model-manager",
  "port": 5570,
  "health_check_port": 6570,
  "agent_type": "service",
  "capabilities": [...],
  "metadata": {...},
  "last_registered": "2025-07-12T15:00:00Z"
}
```

### 3. Health Check
```
curl -X POST http://localhost:8100 -d '{"action":"health"}'
```

---

## Example Usage
An agent can register itself during start-up:
```python
registry_host = os.getenv("SERVICE_REGISTRY_HOST", "localhost")
registry_port = int(os.getenv("SERVICE_REGISTRY_PORT", 7100))

with zmq.Context() as ctx:
    sock = ctx.socket(zmq.REQ)
    sock.connect(f"tcp://{registry_host}:{registry_port}")
    sock.send_json({
        "action": "register_agent",
        "agent_id": "MyAgent",
        "host": "my-agent",
        "port": 6000,
        "health_check_port": 7000,
        "capabilities": ["foo"],
        "metadata": {}
    })
    print(sock.recv_json())
```

---

## Future Work
* **HA & Persistence:** Optionally back the registry with Redis or etcd.
* **Authentication:** Add mutual-TLS or token auth for registration events.
* **Expiration:** Auto-expire registrations that have not been refreshed.
