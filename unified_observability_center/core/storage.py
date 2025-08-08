import asyncio
import json
import time
from typing import Any, Dict, List, Optional

import httpx

from unified_observability_center.resiliency.circuit_breaker import CircuitBreaker


class StorageFacade:
    def __init__(
        self,
        vm_url: str,
        loki_url: str,
        circuit_failure_threshold: int = 5,
        circuit_reset_timeout: float = 15.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.vm_url = vm_url.rstrip("/")
        self.loki_url = loki_url.rstrip("/")
        self._http = client or httpx.AsyncClient(timeout=10.0)
        self._breaker = CircuitBreaker(
            failure_threshold=circuit_failure_threshold,
            reset_timeout_seconds=circuit_reset_timeout,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def write_logs(self, stream_labels: Dict[str, str], lines: List[str]) -> None:
        # Loki push API
        url = f"{self.loki_url}/loki/api/v1/push"
        ts_now_ns = int(time.time() * 1e9)
        values = [[str(ts_now_ns + i), line] for i, line in enumerate(lines)]
        payload = {
            "streams": [
                {
                    "stream": stream_labels,
                    "values": values,
                }
            ]
        }

        async def do_request() -> None:
            resp = await self._http.post(url, json=payload)
            resp.raise_for_status()

        await self._breaker.call(do_request)

    async def write_metrics(self, _metrics: List[Dict[str, Any]]) -> None:
        # Placeholder: depending on ingestion strategy, use VM /api/v1/import or Influx line protocol.
        # For now, no-op to keep interface intact.
        return None

    async def query_range(
        self,
        promql: str,
        start_unix: float,
        end_unix: float,
        step_seconds: int,
    ) -> Dict[str, Any]:
        # VictoriaMetrics query_range compatible endpoint
        params = {
            "query": promql,
            "start": start_unix,
            "end": end_unix,
            "step": step_seconds,
        }
        url = f"{self.vm_url}/api/v1/query_range"

        async def do_request() -> Dict[str, Any]:
            resp = await self._http.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

        return await self._breaker.call(do_request)