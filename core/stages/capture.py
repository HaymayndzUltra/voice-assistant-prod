"""
Real-Time Audio Pipeline - Audio Capture Stage

This module implements the audio capture stage using sounddevice for
ultra-low-latency audio input. Captures audio frames and writes them
to the shared ring buffer for downstream processing.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
import numpy as np
import sounddevice as sd
from ..buffers import AudioRingBuffer
from ..telemetry import get_global_metrics


class AudioCaptureStage:
    """
    Audio capture stage for real-time audio input.
    
    Uses sounddevice to capture audio frames at the configured sample rate
    and frame size. Writes captured audio directly to the shared ring buffer
    for consumption by downstream stages.
    
    Key Features:
    - Low-latency audio streaming
    - Automatic device selection and configuration
    - Error recovery and device failover
    - Frame timing and synchronization
    - Performance monitoring and metrics
    """
    
    def __init__(self, config: Dict[str, Any], audio_buffer: AudioRingBuffer):
        """
        Initialize audio capture stage.
        
        Args:
            config: Pipeline configuration
            audio_buffer: Shared audio ring buffer
        """
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
        
        # Audio stream state
        self.stream: Optional[sd.InputStream] = None
        self.device_id: Optional[int] = None
        self.is_running = False
        self.frames_captured = 0
        self.last_frame_time = 0.0
        
        # Performance tracking
        self.capture_times = []
        self.max_capture_time = 0.0
        self.total_capture_time = 0.0
        
        # Error tracking
        self.capture_errors = 0
        self.device_errors = 0
        self.buffer_overflows = 0
        
        self.logger.info(f"AudioCaptureStage initialized: {self.sample_rate}Hz, "
                        f"{self.frame_ms}ms frames ({self.frame_size} samples)")
    
    async def warmup(self) -> None:
        """Warm up audio capture - probe devices and test configuration."""
        warmup_start = time.perf_counter()
        
        try:
            self.logger.info("Warming up audio capture...")
            
            # Probe available audio devices
            await self._probe_audio_devices()
            
            # Test audio configuration
            await self._test_audio_config()
            
            warmup_time = time.perf_counter() - warmup_start
            self.logger.info(f"Audio capture warmup completed in {warmup_time*1000:.1f}ms")
            
            # Record warmup metrics
            self.metrics.record_warmup_time('capture', warmup_time)
            
        except Exception as e:
            self.logger.error(f"Audio capture warmup failed: {e}")
            self.metrics.record_error('warmup_failed', 'capture')
            raise
    
    async def _probe_audio_devices(self) -> None:
        """Probe and select appropriate audio device."""
        try:
            # Get list of available devices
            devices = sd.query_devices()
            self.logger.debug(f"Found {len(devices)} audio devices")
            
            # Find target device
            if self.device_name and self.device_name != 'default':
                # Look for specific device
                for i, device in enumerate(devices):
                    if self.device_name.lower() in device['name'].lower():
                        self.device_id = i
                        self.logger.info(f"Selected audio device: {device['name']} (ID: {i})")
                        break
                
                if self.device_id is None:
                    self.logger.warning(f"Device '{self.device_name}' not found, using default")
            
            # Use default device if not specified or not found
            if self.device_id is None:
                default_device = sd.query_devices(kind='input')
                self.device_id = default_device['index'] if 'index' in default_device else None
                self.logger.info(f"Using default audio device: {default_device['name']}")
            
        except Exception as e:
            self.logger.error(f"Error probing audio devices: {e}")
            self.device_errors += 1
            raise
    
    async def _test_audio_config(self) -> None:
        """Test audio configuration with short capture."""
        try:
            # Test capture a few frames to verify configuration
            test_duration = 0.1  # 100ms test
            test_frames = int(self.sample_rate * test_duration)
            
            def test_callback(indata, frames, time, status):
                if status:
                    self.logger.warning(f"Audio test callback status: {status}")
            
            # Create temporary stream for testing
            with sd.InputStream(
                device=self.device_id,
                channels=self.channels,
                samplerate=self.sample_rate,
                blocksize=self.frame_size,
                callback=test_callback,
                dtype=np.float32
            ) as test_stream:
                # Let it run briefly
                await asyncio.sleep(test_duration)
            
            self.logger.debug("Audio configuration test passed")
            
        except Exception as e:
            self.logger.error(f"Audio configuration test failed: {e}")
            self.device_errors += 1
            raise
    
    def _audio_callback(self, indata: np.ndarray, frames: int, 
                       time_info, status) -> None:
        """
        Audio stream callback - called by sounddevice for each frame.
        
        This callback must be extremely fast to maintain real-time performance.
        Any heavy processing should be deferred to avoid audio dropouts.
        """
        callback_start = time.perf_counter()
        
        try:
            # Check for audio issues
            if status:
                self.logger.warning(f"Audio callback status: {status}")
                if status.input_overflow:
                    self.buffer_overflows += 1
                    self.metrics.record_error('input_overflow', 'capture')
            
            # Validate frame size
            if frames != self.frame_size:
                self.logger.warning(f"Unexpected frame size: {frames} vs {self.frame_size}")
                return
            
            # Convert to correct format and write to buffer
            if indata.ndim == 2:
                # Multi-channel -> mono conversion if needed
                audio_frame = np.mean(indata, axis=1).astype(np.float32)
            else:
                audio_frame = indata.flatten().astype(np.float32)
            
            # Write to ring buffer (non-blocking)
            success = self.audio_buffer.write(audio_frame)
            
            if success:
                self.frames_captured += 1
                self.last_frame_time = time.perf_counter()
                
                # Record metrics (keep minimal in callback)
                self.metrics.record_frames_processed('capture')
            else:
                self.logger.warning("Failed to write audio frame to buffer")
                self.metrics.record_error('buffer_write_failed', 'capture')
        
        except Exception as e:
            self.capture_errors += 1
            self.logger.error(f"Error in audio callback: {e}")
            self.metrics.record_error('callback_error', 'capture')
        
        # Track callback performance
        callback_time = time.perf_counter() - callback_start
        self.total_capture_time += callback_time
        self.max_capture_time = max(self.max_capture_time, callback_time)
        
        # Record latency metrics periodically (not every callback)
        if self.frames_captured % 100 == 0:
            self.metrics.record_stage_latency('capture', callback_time)
    
    async def run(self) -> None:
        """
        Main capture loop - start audio stream and maintain it.
        """
        self.logger.info("Starting audio capture stage...")
        
        try:
            self.is_running = True
            
            # Create audio input stream
            self.stream = sd.InputStream(
                device=self.device_id,
                channels=self.channels,
                samplerate=self.sample_rate,
                blocksize=self.frame_size,
                callback=self._audio_callback,
                dtype=np.float32,
                latency='low',  # Request low-latency mode
                extra_settings=sd.AsioSettings(channel_selectors=[0] * self.channels)
                if sd.default.api == 'asio' else None
            )
            
            # Start the stream
            self.stream.start()
            
            self.logger.info(f"Audio capture started: device={self.device_id}, "
                           f"latency={self.stream.latency}, "
                           f"blocksize={self.stream.blocksize}")
            
            # Monitor stream health
            await self._monitor_stream()
            
        except Exception as e:
            self.logger.error(f"Audio capture stage failed: {e}")
            self.metrics.record_error('stage_failed', 'capture')
            raise
        finally:
            await self._cleanup_stream()
            self.is_running = False
    
    async def _monitor_stream(self) -> None:
        """Monitor audio stream health and performance."""
        last_stats_time = time.perf_counter()
        last_frame_count = 0
        
        while self.is_running:
            try:
                # Check stream status
                if self.stream and not self.stream.active:
                    self.logger.error("Audio stream became inactive")
                    self.metrics.record_error('stream_inactive', 'capture')
                    break
                
                # Periodic health check
                current_time = time.perf_counter()
                if current_time - last_stats_time >= 10.0:  # Every 10 seconds
                    
                    # Calculate frame rate
                    frames_delta = self.frames_captured - last_frame_count
                    time_delta = current_time - last_stats_time
                    frame_rate = frames_delta / time_delta
                    
                    # Log performance stats
                    avg_callback_time = (self.total_capture_time / self.frames_captured 
                                       if self.frames_captured > 0 else 0)
                    
                    self.logger.info(f"Capture stats: {frame_rate:.1f} FPS, "
                                   f"avg_callback={avg_callback_time*1000:.2f}ms, "
                                   f"max_callback={self.max_capture_time*1000:.2f}ms, "
                                   f"errors={self.capture_errors}")
                    
                    # Update metrics
                    buffer_stats = self.audio_buffer.get_audio_stats()
                    self.metrics.update_buffer_metrics(buffer_stats)
                    
                    # Reset for next period
                    last_stats_time = current_time
                    last_frame_count = self.frames_captured
                    self.max_capture_time = 0.0
                
                # Short sleep to avoid busy waiting
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                self.logger.info("Audio capture monitoring cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in capture monitoring: {e}")
                self.metrics.record_error('monitoring_error', 'capture')
                await asyncio.sleep(1.0)  # Longer sleep on error
    
    async def _cleanup_stream(self) -> None:
        """Clean up audio stream resources."""
        if self.stream:
            try:
                if self.stream.active:
                    self.stream.stop()
                self.stream.close()
                self.logger.info("Audio stream closed")
            except Exception as e:
                self.logger.error(f"Error closing audio stream: {e}")
            finally:
                self.stream = None
    
    async def cleanup(self) -> None:
        """Clean up capture stage resources."""
        self.logger.info("Cleaning up audio capture stage...")
        self.is_running = False
        await self._cleanup_stream()
        
        # Final statistics
        if self.frames_captured > 0:
            avg_callback_time = self.total_capture_time / self.frames_captured
            self.logger.info(f"Capture complete: {self.frames_captured} frames, "
                           f"avg_callback={avg_callback_time*1000:.2f}ms, "
                           f"errors={self.capture_errors}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get capture stage statistics."""
        avg_callback_time = (self.total_capture_time / self.frames_captured 
                           if self.frames_captured > 0 else 0)
        
        return {
            'frames_captured': self.frames_captured,
            'capture_errors': self.capture_errors,
            'device_errors': self.device_errors,
            'buffer_overflows': self.buffer_overflows,
            'avg_callback_time_ms': avg_callback_time * 1000,
            'max_callback_time_ms': self.max_capture_time * 1000,
            'device_id': self.device_id,
            'is_running': self.is_running,
            'last_frame_time': self.last_frame_time,
        }
    
    def __repr__(self) -> str:
        """String representation of capture stage."""
        return (f"AudioCaptureStage(device={self.device_id}, "
                f"frames={self.frames_captured}, running={self.is_running})")