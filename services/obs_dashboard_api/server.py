from fastapi import FastAPI, HTTPException
import os, requests
from prometheus_client import start_http_server

OBS_HUB = os.getenv("OBS_HUB", "http://localhost:9000")
METRICS_PORT = int(os.getenv("METRICS_PORT", "9107"))

app = FastAPI(title="ObservabilityDashboardAPI")
start_http_server(METRICS_PORT)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/metrics/raw")
def proxy_metrics():
    try:
        r = requests.get(f"{OBS_HUB}/metrics", timeout=5)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))
