import pytest
import httpx
from httpx import ASGITransport

from unified_observability_center.api.rest import app


@pytest.mark.asyncio
async def test_health_endpoint_ok():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}