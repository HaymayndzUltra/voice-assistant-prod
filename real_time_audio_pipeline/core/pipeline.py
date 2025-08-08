"""
Real-Time Audio Pipeline - Core State Machine

This module implements the master AudioPipeline class that orchestrates all
processing stages and manages state transitions for ultra-low-latency audio
processing (≤150ms p95).
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from .buffers import AudioRingBuffer
from .stages.capture import AudioCaptureStage
from .stages.language import LanguageAnalysisStage
from .stages.preprocess import PreprocessStage
from .stages.stt import SpeechToTextStage
from .stages.wakeword import WakeWordStage
from .telemetry import PipelineMetrics


class PipelineState(Enum):
    """Pipeline state machine states."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    EMIT = "emit"
    SHUTDOWN = "shutdown"
    ERROR = "error"


class AudioPipeline:
    """
    Master state machine for Real-Time Audio Pipeline.

    Orchestrates async stages and manages state transitions for ultra-low-latency
    audio processing. Coordinates audio capture, wake word detection, preprocessing,
    speech recognition, and language analysis.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize AudioPipeline with configuration."""
        self.config = config
        self.state = PipelineState.IDLE
        self.logger = logging.getLogger(__name__)

        # Performance tracking
        self.start_time = 0.0
        self.frame_count = 0
        self.state_transitions = 0

        # Core components
        self.audio_buffer = self._create_audio_buffer()
        self.metrics = PipelineMetrics()

        # Inter-stage communication queues
        self.wakeword_queue = asyncio.Queue(maxsize=32)
        self.preprocess_queue = asyncio.Queue(maxsize=32)
        self.stt_queue = asyncio.Queue(maxsize=16)
        self.language_queue = asyncio.Queue(maxsize=16)
        self.output_queue = asyncio.Queue(maxsize=8)

        # Stage instances
        self.stages = {}
        self._initialize_stages()

        # Task management
        self.stage_tasks: List[asyncio.Task] = []
        self.pipeline_task: Optional[asyncio.Task] = None
        self.shutdown_event = asyncio.Event()

        self.logger.info(f"AudioPipeline initialized with config version {config.get('version', 'unknown')}")

    def _create_audio_buffer(self) -> AudioRingBuffer:
        """Create audio buffer from configuration."""
        audio_config = self.config['audio']
        return AudioRingBuffer(
            sample_rate=audio_config['sample_rate'],
            buffer_duration_ms=audio_config['ring_buffer_size_ms'],
            channels=audio_config['channels'],
            frame_duration_ms=audio_config['frame_ms']
        )

    def _initialize_stages(self) -> None:
        """Initialize all processing stages."""
        try:
            self.stages = {
                'capture': AudioCaptureStage(self.config, self.audio_buffer),
                'wakeword': WakeWordStage(self.config, self.audio_buffer, self.wakeword_queue),
                'preprocess': PreprocessStage(self.config, self.preprocess_queue),
                'stt': SpeechToTextStage(self.config, self.stt_queue),
                'language': LanguageAnalysisStage(self.config, self.language_queue),
            }
            self.logger.info(f"Initialized {len(self.stages)} processing stages")
        except Exception as e:
            self.logger.error(f"Failed to initialize stages: {e}")
            raise

    async def start(self) -> None:
        """Start the audio pipeline."""
        try:
            self.logger.info("Starting Real-Time Audio Pipeline...")
            self.start_time = time.perf_counter()

            # Warm up models and initialize hardware
            await self._warmup_pipeline()

            # Spawn stage tasks
            await self._spawn_stage_tasks()

            self.logger.info("AudioPipeline started successfully")

        except Exception as e:
            self.logger.error(f"Pipeline startup failed: {e}")
            raise

    async def _warmup_pipeline(self) -> None:
        """Warm up models and initialize hardware to reduce first-request latency."""
        self.logger.info("Warming up pipeline components...")

        warmup_start = time.perf_counter()

        # Warm up each stage
        for stage_name, stage in self.stages.items():
            if hasattr(stage, 'warmup'):
                stage_start = time.perf_counter()
                await stage.warmup()
                stage_time = time.perf_counter() - stage_start
                self.logger.debug(f"Warmed up {stage_name} in {stage_time*1000:.1f}ms")

        warmup_time = time.perf_counter() - warmup_start
        self.logger.info(f"Pipeline warmup completed in {warmup_time*1000:.1f}ms")

    async def _spawn_stage_tasks(self) -> None:
        """Spawn async tasks for all pipeline stages."""
        self.logger.info("Spawning stage tasks...")

        # Create tasks for each stage
        for stage_name, stage in self.stages.items():
            task = asyncio.create_task(
                stage.run(),
                name=f"stage_{stage_name}"
            )
            self.stage_tasks.append(task)
            self.logger.debug(f"Spawned task for {stage_name} stage")

        self.logger.info(f"Spawned {len(self.stage_tasks)} stage tasks")

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics."""
        uptime = time.perf_counter() - self.start_time

        return {
            'state': self.state.value,
            'uptime_seconds': uptime,
            'state_transitions': self.state_transitions,
            'frame_count': self.frame_count,
            'buffer_stats': self.audio_buffer.get_audio_stats(),
            'stage_count': len(self.stages),
            'queue_sizes': {
                'wakeword': self.wakeword_queue.qsize(),
                'preprocess': self.preprocess_queue.qsize(),
                'stt': self.stt_queue.qsize(),
                'language': self.language_queue.qsize(),
                'output': self.output_queue.qsize(),
            }
        }

    async def shutdown(self) -> None:
        """Gracefully shutdown the pipeline."""
        self.logger.info("Initiating pipeline shutdown...")

        # Set shutdown event
        self.shutdown_event.set()

        # Cancel all stage tasks
        for task in self.stage_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete with timeout
        if self.stage_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.stage_tasks, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                self.logger.warning("Some stage tasks did not complete within timeout")

        # Close stage resources
        for stage in self.stages.values():
            if hasattr(stage, 'cleanup'):
                try:
                    await stage.cleanup()
                except Exception as e:
                    self.logger.error(f"Error cleaning up stage: {e}")

        # Final metrics
        final_stats = self.get_pipeline_stats()
        self.logger.info(f"Pipeline shutdown complete. Final stats: {final_stats}")

    def __repr__(self) -> str:
        """String representation of pipeline state."""
        uptime = time.perf_counter() - self.start_time if self.start_time > 0 else 0
        return (f"AudioPipeline(state={self.state.value}, "
                f"uptime={uptime:.1f}s, stages={len(self.stages)})")
