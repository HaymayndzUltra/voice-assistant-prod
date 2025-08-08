import asyncio
import pytest

# Detect Docker availability up-front
_has_docker = True
try:
    import docker  # type: ignore
    _client = docker.from_env()
    try:
        _client.ping()
    except Exception:
        _has_docker = False
except Exception:
    _has_docker = False

from testcontainers.core.container import DockerContainer
from unified_observability_center.bus.nats_client import NatsClient

pytestmark = pytest.mark.skipif(not _has_docker, reason="Docker not available in this environment")


@pytest.mark.asyncio
async def test_nats_pub_sub_integration():
    with DockerContainer("nats:2.10").with_exposed_ports(4222) as nats:
        host = nats.get_container_host_ip()
        port = nats.get_exposed_port(4222)
        url = f"nats://{host}:{port}"

        received = asyncio.Event()
        received_data = {}

        async def on_msg(msg):
            received_data["data"] = msg.data
            received.set()

        nc = NatsClient(url=url)
        await nc.connect()
        try:
            await nc.subscribe("uoc.test", cb=on_msg)
            await nc.publish("uoc.test", b"ping")
            # wait for message
            await asyncio.wait_for(received.wait(), timeout=5)
            assert received_data["data"] == b"ping"
        finally:
            await nc.close()