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
from typing import List, Dict, Any, Optional, AsyncGenerator
import signal
import sys

from .buffers import AudioRingBuffer
from .stages.capture import AudioCaptureStage
from .stages.wakeword import WakeWordStage
from .stages.preprocess import PreprocessStage
from .stages.stt import SpeechToTextStage
from .stages.language import LanguageAnalysisStage
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
    
    Key Features:
    - Async coroutine-based architecture
    - State machine with proper transitions
    - Inter-stage communication via asyncio.Queue
    - Performance monitoring and telemetry
    - Graceful shutdown handling
    - Error recovery and resilience
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize AudioPipeline with configuration.
        
        Args:
            config: Pipeline configuration dictionary
        """
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
        
        # State transition handlers
        self.state_handlers = {
            PipelineState.IDLE: self._handle_idle_state,
            PipelineState.LISTENING: self._handle_listening_state,
            PipelineState.PROCESSING: self._handle_processing_state,
            PipelineState.EMIT: self._handle_emit_state,
        }
        
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
        """
        Start the audio pipeline.
        
        Spawns all async stage tasks and begins the main state loop.
        """
        try:
            self.logger.info("Starting Real-Time Audio Pipeline...")
            self.start_time = time.perf_counter()
            
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            # Warm up models and initialize hardware
            await self._warmup_pipeline()
            
            # Spawn stage tasks
            await self._spawn_stage_tasks()
            
            # Start main state machine loop
            self.pipeline_task = asyncio.create_task(self._state_machine_loop())
            
            self.logger.info("AudioPipeline started successfully")
            
            # Wait for shutdown
            await self.pipeline_task
            
        except Exception as e:
            self.logger.error(f"Pipeline startup failed: {e}")
            await self._emergency_shutdown()
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
        
        # Record warmup metrics
        self.metrics.record_warmup_time(warmup_time)
    
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
    
    async def _state_machine_loop(self) -> None:
        """
        Main state machine loop.
        
        Continuously processes state transitions and coordinates between stages.
        This is the heart of the pipeline's orchestration logic.
        """
        self.logger.info("Starting state machine loop")
        
        try:
            # Transition to LISTENING state
            await self._transition_to_state(PipelineState.LISTENING)
            
            while not self.shutdown_event.is_set():
                loop_start = time.perf_counter()
                
                # Execute current state handler
                if self.state in self.state_handlers:
                    try:
                        await self.state_handlers[self.state]()
                    except Exception as e:
                        self.logger.error(f"Error in state {self.state}: {e}")
                        await self._transition_to_state(PipelineState.ERROR)
                
                # Record state loop timing
                loop_time = time.perf_counter() - loop_start
                self.metrics.record_state_loop_time(loop_time)
                
                # Small yield to prevent CPU hogging
                await asyncio.sleep(0.001)  # 1ms yield
                
        except asyncio.CancelledError:
            self.logger.info("State machine loop cancelled")
        except Exception as e:
            self.logger.error(f"Critical error in state machine: {e}")
            await self._transition_to_state(PipelineState.ERROR)
        finally:
            await self._transition_to_state(PipelineState.SHUTDOWN)
    
    async def _handle_idle_state(self) -> None:
        """Handle IDLE state - waiting for activation."""
        # In IDLE, we just wait for external activation
        await asyncio.sleep(0.1)
    
    async def _handle_listening_state(self) -> None:
        """Handle LISTENING state - monitoring for wake word."""
        try:
            # Check for wake word detection
            if not self.wakeword_queue.empty():
                wakeword_event = await asyncio.wait_for(
                    self.wakeword_queue.get(), 
                    timeout=0.001
                )
                
                if wakeword_event.get('detected', False):
                    self.logger.info(f"Wake word detected: {wakeword_event}")
                    self.metrics.record_wakeword_detection()
                    await self._transition_to_state(PipelineState.PROCESSING)
                    
        except asyncio.TimeoutError:
            # No wake word event, continue listening
            pass
    
    async def _handle_processing_state(self) -> None:
        """Handle PROCESSING state - active speech recognition."""
        try:
            # Check for preprocessing completion
            if not self.preprocess_queue.empty():
                preprocess_result = await asyncio.wait_for(
                    self.preprocess_queue.get(),
                    timeout=0.001
                )
                
                # Forward to STT queue
                await self.stt_queue.put(preprocess_result)
            
            # Check for STT completion
            if not self.stt_queue.empty():
                stt_result = await asyncio.wait_for(
                    self.language_queue.get(),
                    timeout=0.001
                )
                
                if stt_result.get('transcript'):
                    self.logger.info(f"Transcript: {stt_result['transcript']}")
                    await self._transition_to_state(PipelineState.EMIT)
                    
        except asyncio.TimeoutError:
            # Continue processing
            pass
    
    async def _handle_emit_state(self) -> None:
        """Handle EMIT state - output results and return to listening."""
        try:
            # Check for language analysis completion
            if not self.language_queue.empty():
                language_result = await asyncio.wait_for(
                    self.language_queue.get(),
                    timeout=0.001
                )
                
                # Prepare final output
                output_data = {
                    'timestamp': time.time(),
                    'transcript': language_result.get('transcript', ''),
                    'language': language_result.get('language', 'unknown'),
                    'sentiment': language_result.get('sentiment', 'neutral'),
                    'confidence': language_result.get('confidence', 0.0),
                    'processing_time_ms': language_result.get('processing_time_ms', 0),
                }
                
                # Emit to output queue
                await self.output_queue.put(output_data)
                
                # Record metrics
                self.metrics.record_transcript_completion(output_data)
                
                # Return to listening
                await self._transition_to_state(PipelineState.LISTENING)
                
        except asyncio.TimeoutError:
            # Continue in emit state
            pass
    
    async def _transition_to_state(self, new_state: PipelineState) -> None:
        """
        Transition to a new pipeline state.
        
        Args:
            new_state: Target state to transition to
        """
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            self.state_transitions += 1
            
            transition_time = time.perf_counter() - self.start_time
            self.logger.debug(f"State transition: {old_state.value} → {new_state.value} @ {transition_time:.3f}s")
            
            # Record state transition metrics
            self.metrics.record_state_transition(old_state.value, new_state.value)
    
    async def output_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Async generator for pipeline output.
        
        Yields processed transcription results as they become available.
        
        Yields:
            Dictionary containing transcript, language, sentiment, and metadata
        """
        try:
            while not self.shutdown_event.is_set():
                try:
                    # Wait for output with timeout
                    output_data = await asyncio.wait_for(
                        self.output_queue.get(),
                        timeout=1.0
                    )
                    yield output_data
                    
                except asyncio.TimeoutError:
                    # No output available, continue
                    continue
                    
        except asyncio.CancelledError:
            self.logger.info("Output stream cancelled")
        except Exception as e:
            self.logger.error(f"Error in output stream: {e}")
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics."""
        uptime = time.perf_counter() - self.start_time
        
        return {
            'state': self.state.value,
            'uptime_seconds': uptime,
            'state_transitions': self.state_transitions,
            'frame_count': self.frame_count,
            'buffer_stats': self.audio_buffer.get_audio_stats(),
            'metrics': self.metrics.get_stats(),
            'stage_count': len(self.stages),
            'queue_sizes': {
                'wakeword': self.wakeword_queue.qsize(),
                'preprocess': self.preprocess_queue.qsize(),
                'stt': self.stt_queue.qsize(),
                'language': self.language_queue.qsize(),
                'output': self.output_queue.qsize(),
            }
        }
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
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
        
        # Cancel pipeline task
        if self.pipeline_task and not self.pipeline_task.done():
            self.pipeline_task.cancel()
        
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
    
    async def _emergency_shutdown(self) -> None:
        """Emergency shutdown for critical errors."""
        self.logger.error("Emergency shutdown initiated")
        
        # Force cancel all tasks
        for task in self.stage_tasks:
            task.cancel()
        
        if self.pipeline_task:
            self.pipeline_task.cancel()
        
        # Set shutdown event
        self.shutdown_event.set()
    
    def __repr__(self) -> str:
        """String representation of pipeline state."""
        uptime = time.perf_counter() - self.start_time if self.start_time > 0 else 0
        return (f"AudioPipeline(state={self.state.value}, "
                f"uptime={uptime:.1f}s, stages={len(self.stages)})")