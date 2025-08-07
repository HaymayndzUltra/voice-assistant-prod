"""
Streaming Translation Proxy
---------------------------
WebSocket endpoint  `/ws`   → sentence-level translation
HTTP health check   `/health`
Prometheus metrics  `:9106/metrics`
Depends on existing CloudTranslationService for heavy lifting.
"""
import os, asyncio, httpx
from fastapi import FastAPI, WebSocket, Depends
from fastapi.responses import JSONResponse
from prometheus_client import start_http_server, Counter

OPENAI_URL  = os.getenv("OPENAI_URL", "https://api.openai.com/v1/chat/completions")
OPENAI_KEY  = os.getenv("OPENAI_API_KEY", "")
MODEL       = os.getenv("OPENAI_MODEL", "gpt-4o")
METRICS_PORT = int(os.getenv("METRICS_PORT", "9106"))

TX_COUNTER = Counter("translation_requests_total", "Total translation requests", ["target"])

app = FastAPI(title="StreamingTranslationProxy")

@app.get("/health")
def health():
    return JSONResponse({"status": "ok"})

async def translate(text: str, target: str) -> str:
    TX_COUNTER.labels(target).inc()
    headers = {"Authorization": f"Bearer {OPENAI_KEY}"} if OPENAI_KEY else {}
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": f"Translate to {target}: {text}"}],
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=30.0) as cli:
        r = await cli.post(OPENAI_URL, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data = await ws.receive_json()
            text = data["text"]
            target = data.get("target_lang", "en")
            result = await translate(text, target)
            await ws.send_json({"translated": result})
    except Exception:
        await ws.close()

# Metrics
start_http_server(METRICS_PORT)
