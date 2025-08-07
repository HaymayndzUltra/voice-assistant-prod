"""
Central Error Bus
-----------------
• SUB socket (ipc:///tmp/agent_errors) – agents send JSON error events
• PUB socket (tcp://*:7150)          – broadcasts to any subscribers
• Prometheus counter at :9105/metrics
"""
import asyncio, json, os, signal, zmq, zmq.asyncio
from prometheus_client import start_http_server, Counter

PORT          = int(os.getenv("ERROR_BUS_PORT", "7150"))
SUB_ENDPOINT  = os.getenv("SUB_ENDPOINT", "ipc:///tmp/agent_errors")
PUB_ENDPOINT  = f"tcp://*:{PORT}"

ERROR_CNT = Counter("error_events_total", "Error events", ["source"])

ctx  = zmq.asyncio.Context()
sub = ctx.socket(zmq.SUB); sub.bind(SUB_ENDPOINT); sub.setsockopt_string(zmq.SUBSCRIBE, "")
pub = ctx.socket(zmq.PUB); pub.bind(PUB_ENDPOINT)

async def forward():
    while True:
        raw = await sub.recv()
        try:
            msg = json.loads(raw)
            ERROR_CNT.labels(msg.get("agent", "unknown")).inc()
        except Exception:
            msg = {"raw": raw.decode(errors="ignore")}
            ERROR_CNT.labels("malformed").inc()
        await pub.send_json(msg)

def main() -> None:
    start_http_server(9105)
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, loop.stop)
    loop.add_signal_handler(signal.SIGTERM, loop.stop)
    loop.run_until_complete(forward())

if __name__ == "__main__":
    main()
