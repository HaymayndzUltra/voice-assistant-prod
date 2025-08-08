"""Speech-to-Text Stage (Stub)"""

import asyncio
import logging
from typing import Any, Dict

from ..telemetry import get_global_metrics
import os
import sys


class SpeechToTextStage:
    """Stub implementation for speech-to-text stage."""

    def __init__(self, config: Dict[str, Any], output_queue: asyncio.Queue):
        self.config = config
        self.output_queue = output_queue
        self.logger = logging.getLogger(__name__)
        self.metrics = get_global_metrics()
        self.is_running = False
        self._lease_client = None

        self.logger.info("SpeechToTextStage initialized (stub)")

    async def warmup(self) -> None:
        """Warmup stage and acquire GPU lease if available."""
        try:
            # Attempt to acquire lease for RTAP-GPU
            from ..gpu_lease_client import GpuLeaseClient  # type: ignore
            lease_client = GpuLeaseClient(os.environ.get('MOC_GRPC_ADDR', 'localhost:7212'))
            if lease_client.acquire_for_rtap():
                self._lease_client = lease_client
                self.logger.info("✅ RTAP-GPU lease acquired")
            else:
                self.logger.warning("RTAP-GPU lease not granted; continuing without GPU allocation")
        except Exception as e:
            self.logger.warning(f"Lease client unavailable or failed: {e}")
        # Continue with regular warmup
        await asyncio.sleep(0.01)

    async def run(self) -> None:
        """Stub run loop."""
        self.logger.info("SpeechToTextStage running (stub)")
        self.is_running = True

        try:
            while self.is_running:
                await asyncio.sleep(1.0)

        except asyncio.CancelledError:
            self.logger.info("SpeechToTextStage cancelled")
        finally:
            self.is_running = False

    async def cleanup(self) -> None:
        """Stub cleanup."""
        self.is_running = False
        self.logger.info("SpeechToTextStage cleaned up (stub)")
        try:
            if self._lease_client:
                self._lease_client.release()
                self.logger.info("🔓 Released RTAP-GPU lease")
        except Exception:
            pass
