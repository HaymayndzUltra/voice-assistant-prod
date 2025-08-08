"""GPU Lease Client wrapper.

Acquires and releases GPU VRAM leases from the ModelOps Coordinator gRPC API.

Defaults:
- Server: localhost:7212 (override with MOC_GRPC_ADDR)
- APC defaults: VRAM 14000 MB, TTL 60s (override with APC_VRAM_ESTIMATE_MB, APC_LEASE_TTL_SEC)
- RTAP-GPU defaults: VRAM 6000 MB, TTL 30s (override with RTAP_VRAM_ESTIMATE_MB, RTAP_LEASE_TTL_SEC)
"""

from __future__ import annotations

import os
import time
from typing import Optional

import grpc

try:
    # Allow import from within model_ops_coordinator and from repo root
    from model_ops_coordinator import model_ops_pb2 as pb2  # type: ignore
    from model_ops_coordinator import model_ops_pb2_grpc as pb2_grpc  # type: ignore
except Exception:
    import model_ops_pb2 as pb2  # type: ignore
    import model_ops_pb2_grpc as pb2_grpc  # type: ignore


def _env_int(name: str, default_value: int) -> int:
    try:
        return int(os.environ.get(name, str(default_value)))
    except Exception:
        return default_value


class GpuLeaseClient:
    def __init__(self, address: Optional[str] = None):
        self.address = address or os.environ.get("MOC_GRPC_ADDR", "localhost:7212")
        self.channel = grpc.insecure_channel(self.address)
        self.stub = pb2_grpc.ModelOpsStub(self.channel)
        self.lease_id: Optional[str] = None

    def acquire(self, client: str, model: str, mb: int, priority: int = 2, ttl_seconds: int = 30) -> bool:
        backoff = 0.25
        for _ in range(6):
            rep: pb2.GpuLeaseReply = self.stub.AcquireGpuLease(
                pb2.GpuLeaseRequest(
                    client=client,
                    model_name=model,
                    vram_estimate_mb=mb,
                    priority=priority,
                    ttl_seconds=ttl_seconds,
                )
            )
            if rep.granted:
                self.lease_id = rep.lease_id
                return True
            time.sleep(min(max(rep.retry_after_ms / 1000.0, backoff), 2.0))
            backoff = min(backoff * 2, 2.0)
        return False

    def release(self) -> None:
        if self.lease_id:
            try:
                self.stub.ReleaseGpuLease(pb2.GpuLeaseRelease(lease_id=self.lease_id))
            finally:
                self.lease_id = None

    # Convenience helpers for APC and RTAP-GPU with env overrides
    def acquire_for_apc(self, model: str = "apc", priority: int = 2) -> bool:
        mb = _env_int("APC_VRAM_ESTIMATE_MB", 14000)
        ttl = _env_int("APC_LEASE_TTL_SEC", 60)
        return self.acquire(client="APC", model=model, mb=mb, priority=priority, ttl_seconds=ttl)

    def acquire_for_rtap(self, model: str = "rtap-gpu", priority: int = 2) -> bool:
        mb = _env_int("RTAP_VRAM_ESTIMATE_MB", 6000)
        ttl = _env_int("RTAP_LEASE_TTL_SEC", 30)
        return self.acquire(client="RTAP-GPU", model=model, mb=mb, priority=priority, ttl_seconds=ttl)

