"""
Self-Healing Supervisor
‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
• Polls health-check endpoints of all running containers every 30 s
• On failure → docker restart + Prometheus counter
• Requires /var/run/docker.sock mount (read-write)
"""
import asyncio, os, json, time, logging
import docker, aiohttp
from prometheus_client import start_http_server, Counter

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("self-healer")

POLL_SEC = int(os.getenv("HEALTH_POLL_SEC", "30"))
METRICS_PORT = int(os.getenv("METRICS_PORT", "9108"))
HEALTH_TIMEOUT = int(os.getenv("HEALTH_TIMEOUT_SEC", "5"))

RESTARTS = Counter("container_restarts_total", "Auto restarts", ["name"])

client = docker.DockerClient(base_url="unix://var/run/docker.sock")
start_http_server(METRICS_PORT)

async def check_container(cont):
    url = cont.labels.get("health_check_url")
    if not url:
        port = cont.labels.get("health_check_port")
        if port:
            url = f"http://localhost:{port}/health"
    if not url:
        return
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=HEALTH_TIMEOUT)) as sess:
            async with sess.get(url) as r:
                if r.status != 200:
                    raise RuntimeError(f"Bad status {r.status}")
    except Exception as e:
        LOG.warning("Health failed for %s – restarting: %s", cont.name, e)
        RESTARTS.labels(cont.name).inc()
        cont.restart()

async def loop():
    while True:
        for cont in client.containers.list():
            await check_container(cont)
        await asyncio.sleep(POLL_SEC)

if __name__ == "__main__":
    asyncio.run(loop())
