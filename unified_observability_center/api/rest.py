import os
import json
from collections import deque
from pathlib import Path
from typing import Deque, List

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest

from unified_observability_center.core.storage import StorageFacade
from unified_observability_center.bus.nats_client import NatsClient
from unified_observability_center.bus import topics


app = FastAPI(title="Unified Observability Center API")


http_bearer = HTTPBearer(auto_error=True)


def _allowed_tokens() -> List[str]:
    raw = os.getenv("UOC_API_TOKENS", "")
    return [t.strip() for t in raw.split(",") if t.strip()]


async def auth(credentials: HTTPAuthorizationCredentials = Depends(http_bearer)) -> str:
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth scheme")
    token = credentials.credentials
    allowed = _allowed_tokens()
    if not allowed:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API not configured with tokens")
    if token not in allowed:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return token


@app.on_event("startup")
async def startup() -> None:
    # Load config
    cfg_path = Path(__file__).resolve().parents[1] / "config" / "default.yaml"
    import yaml

    with open(cfg_path, "r") as f:
        cfg = yaml.safe_load(f)

    storage_cfg = cfg.get("storage", {})
    app.state.storage = StorageFacade(
        vm_url=storage_cfg.get("metrics", {}).get("url", "http://vmselect:8481"),
        loki_url=storage_cfg.get("logs", {}).get("url", "http://loki:3100"),
        circuit_failure_threshold=cfg.get("resilience", {}).get("circuit_breaker", {}).get("failure_threshold", 5),
        circuit_reset_timeout=float(cfg.get("resilience", {}).get("circuit_breaker", {}).get("reset_timeout", 15)),
    )

    # NATS subscriptions for alerts/actions
    nats_url = cfg["nats"]["url"]
    app.state.nc = NatsClient(nats_url)
    await app.state.nc.connect()

    app.state.alerts: Deque[dict] = deque(maxlen=500)
    app.state.actions: Deque[dict] = deque(maxlen=500)

    async def on_alert(msg):
        try:
            app.state.alerts.append(json.loads(msg.data.decode()))
        except Exception:
            pass

    async def on_action(msg):
        try:
            app.state.actions.append(json.loads(msg.data.decode()))
        except Exception:
            pass

    await app.state.nc.subscribe(topics.ALERTS, cb=on_alert)
    await app.state.nc.subscribe(topics.ACTIONS, cb=on_action)


@app.on_event("shutdown")
async def shutdown() -> None:
    if getattr(app.state, "nc", None):
        await app.state.nc.close()
    if getattr(app.state, "storage", None):
        await app.state.storage.close()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/metrics")
async def metrics(_: str = Depends(auth)) -> Response:
    data = generate_latest(REGISTRY)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@app.get("/query")
async def query(
    promql: str = Query(..., description="PromQL expression"),
    start: float = Query(..., description="Start time (unix seconds)"),
    end: float = Query(..., description="End time (unix seconds)"),
    step: int = Query(15, description="Step seconds"),
    _: str = Depends(auth),
):
    res = await app.state.storage.query_range(promql=promql, start_unix=start, end_unix=end, step_seconds=step)
    return res


@app.get("/alerts")
async def get_alerts(limit: int = Query(100, ge=1, le=500), _: str = Depends(auth)) -> List[dict]:
    d = list(app.state.alerts)
    return d[-limit:]


@app.get("/actions")
async def get_actions(limit: int = Query(100, ge=1, le=500), _: str = Depends(auth)) -> List[dict]:
    d = list(app.state.actions)
    return d[-limit:]