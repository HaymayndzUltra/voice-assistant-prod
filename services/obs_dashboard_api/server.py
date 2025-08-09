from fastapi import FastAPI, HTTPException
import os, requests
from prometheus_client import start_http_server

UOC_URL = os.getenv("UOC_URL", os.getenv("OBS_HUB", "http://localhost:9100"))
UOC_TOKEN = os.getenv("UOC_TOKEN", "")
METRICS_PORT = int(os.getenv("METRICS_PORT", "9107"))

app = FastAPI(title="ObservabilityDashboardAPI")
start_http_server(METRICS_PORT)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/metrics/raw")
def proxy_metrics():
    try:
        headers = {"Authorization": f"Bearer {UOC_TOKEN}"} if UOC_TOKEN else {}
        r = requests.get(f"{UOC_URL}/metrics", timeout=5, headers=headers)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))
