"""Wake Word Detection Stage (Stub)"""

import asyncio
import logging
import time
from typing import Any, Dict

from ..buffers import AudioRingBuffer
from ..telemetry import get_global_metrics


class WakeWordStage:
    """Stub implementation for wake word detection stage."""

    def __init__(self, config: Dict[str, Any], audio_buffer: AudioRingBuffer, output_queue: asyncio.Queue):
        self.config = config
        self.audio_buffer = audio_buffer
        self.output_queue = output_queue
        self.logger = logging.getLogger(__name__)
        self.metrics = get_global_metrics()
        self.is_running = False

        self.logger.info("WakeWordStage initialized (stub)")

    async def warmup(self) -> None:
        """Stub warmup."""
        self.logger.info("WakeWordStage warmup (stub)")
        await asyncio.sleep(0.01)

    async def run(self) -> None:
        """Stub run loop."""
        self.logger.info("WakeWordStage running (stub)")
        self.is_running = True

        try:
            while self.is_running:
                # Simulate wake word detection every 15 seconds
                await asyncio.sleep(15.0)

                if not self.is_running:
                    break

                # Simulate wake word detection
                await self.output_queue.put({
                    'detected': True,
                    'confidence': 0.95,
                    'timestamp': time.time()
                })
                self.logger.info("Simulated wake word detection")

        except asyncio.CancelledError:
            self.logger.info("WakeWordStage cancelled")
        finally:
            self.is_running = False

    async def cleanup(self) -> None:
        """Stub cleanup."""
        self.is_running = False
        self.logger.info("WakeWordStage cleaned up (stub)")
