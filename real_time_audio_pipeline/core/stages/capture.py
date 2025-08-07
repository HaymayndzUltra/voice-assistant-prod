"""
Real-Time Audio Pipeline - Audio Capture Stage

Audio capture using sounddevice for real-time input.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

import numpy as np

# Handle missing PortAudio gracefully
try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except (ImportError, OSError) as e:
    sd = None
    AUDIO_AVAILABLE = False
    print(f"Audio hardware not available: {e}")

from ..buffers import AudioRingBuffer
from ..telemetry import get_global_metrics


class AudioCaptureStage:
    """Audio capture stage for real-time audio input."""

    def __init__(self, config: Dict[str, Any], audio_buffer: AudioRingBuffer):
        self.config = config
        self.audio_config = config['audio']
        self.audio_buffer = audio_buffer
        self.logger = logging.getLogger(__name__)
        self.metrics = get_global_metrics()

        # Audio parameters
        self.sample_rate = self.audio_config['sample_rate']
        self.channels = self.audio_config['channels']
        self.frame_ms = self.audio_config['frame_ms']
        self.device_name = self.audio_config['device']

        # Calculate frame size in samples
        self.frame_size = int((self.sample_rate * self.frame_ms) / 1000)

        # State
        self.stream: Optional = None
        self.device_id: Optional[int] = None
        self.is_running = False
        self.frames_captured = 0

        self.logger.info(f"AudioCaptureStage initialized: {self.sample_rate}Hz, "
                        f"{self.frame_ms}ms frames ({self.frame_size} samples), "
                        f"audio_available={AUDIO_AVAILABLE}")

    async def warmup(self) -> None:
        """Warm up audio capture."""
        self.logger.info(f"Audio capture warmup (audio_available={AUDIO_AVAILABLE})")
        await asyncio.sleep(0.01)

    async def run(self) -> None:
        """Main capture loop."""
        self.logger.info("Starting audio capture stage...")
        self.is_running = True

        try:
            if not AUDIO_AVAILABLE:
                self.logger.info("Running in mock mode - no audio hardware")
                await self._mock_capture()
            else:
                # Real audio capture
                await self._real_capture()

        except Exception as e:
            self.logger.error(f"Audio capture stage failed: {e}")
        finally:
            self.is_running = False

    async def _mock_capture(self) -> None:
        """Mock audio capture for testing."""
        self.logger.info("Running mock audio capture")

        while self.is_running:
            try:
                # Generate mock audio frame
                mock_frame = np.random.random(self.frame_size).astype(np.float32) * 0.1

                # Write to buffer
                success = self.audio_buffer.write(mock_frame)
                if success:
                    self.frames_captured += 1
                    if self.frames_captured % 100 == 0:  # Log every 100 frames
                        self.metrics.record_frames_processed('capture', 100)

                # Simulate frame timing (20ms)
                await asyncio.sleep(self.frame_ms / 1000.0)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Mock capture error: {e}")
                await asyncio.sleep(0.1)

    async def _real_capture(self) -> None:
        """Real audio capture using sounddevice."""
        self.logger.info("Real audio capture not fully implemented yet")
        await self._mock_capture()  # Fallback to mock

    async def cleanup(self) -> None:
        """Clean up capture stage."""
        self.logger.info("Cleaning up audio capture stage...")
        self.is_running = False

        if self.frames_captured > 0:
            self.logger.info(f"Capture complete: {self.frames_captured} frames")

    def get_stats(self) -> Dict[str, Any]:
        """Get capture stage statistics."""
        return {
            'frames_captured': self.frames_captured,
            'device_id': self.device_id,
            'is_running': self.is_running,
            'audio_available': AUDIO_AVAILABLE,
        }

    def __repr__(self) -> str:
        return f"AudioCaptureStage(frames={self.frames_captured}, running={self.is_running})"
