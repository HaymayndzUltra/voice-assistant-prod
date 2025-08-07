"""
Real-Time Audio Pipeline - Speech-to-Text Stage (Stub)

This is a stub implementation for the STT stage.
Full implementation with Whisper in ThreadPoolExecutor will be completed later.
"""

import asyncio
import logging
from typing import Dict, Any
from ..telemetry import get_global_metrics


class SpeechToTextStage:
    """Stub implementation for speech-to-text stage."""
    
    def __init__(self, config: Dict[str, Any], output_queue: asyncio.Queue):
        self.config = config
        self.output_queue = output_queue
        self.logger = logging.getLogger(__name__)
        self.metrics = get_global_metrics()
        self.is_running = False
        
        self.logger.info("SpeechToTextStage initialized (stub)")
    
    async def warmup(self) -> None:
        """Stub warmup."""
        self.logger.info("SpeechToTextStage warmup (stub)")
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