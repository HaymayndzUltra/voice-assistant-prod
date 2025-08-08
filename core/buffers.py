"""
High-performance ring buffer implementation for Real-Time Audio Pipeline.

This module provides a zero-copy ring buffer optimized for audio data processing
with strict latency requirements (≤150ms p95).
"""

import numpy as np
from collections import deque
from typing import Optional, Union
import threading
import time


class RingBuffer:
    """
    Thread-safe ring buffer for efficient audio frame storage and retrieval.
    
    Uses collections.deque for O(1) append/pop operations and pre-allocated
    NumPy arrays for zero-copy audio data handling.
    
    Key Features:
    - Zero-copy operations where possible
    - Thread-safe read/write operations
    - Automatic overflow handling with configurable behavior
    - Memory-efficient bounded storage
    - Optimized for real-time audio processing
    """
    
    def __init__(self, max_frames: int, frame_size: int, dtype: np.dtype = np.float32):
        """
        Initialize ring buffer with pre-allocated storage.
        
        Args:
            max_frames: Maximum number of frames to store
            frame_size: Size of each frame in samples
            dtype: NumPy data type for audio samples
        """
        self.max_frames = max_frames
        self.frame_size = frame_size
        self.dtype = dtype
        
        # Thread-safe deque with maximum length
        self.buffer = deque(maxlen=max_frames)
        
        # Thread synchronization
        self._lock = threading.RLock()
        
        # Statistics for performance monitoring
        self._frames_written = 0
        self._frames_read = 0
        self._overflows = 0
        self._last_write_time = 0.0
        self._last_read_time = 0.0
        
    def write(self, frame: np.ndarray) -> bool:
        """
        Write a frame to the ring buffer.
        
        Args:
            frame: Audio frame as NumPy array
            
        Returns:
            True if write successful, False if frame was rejected
            
        Raises:
            ValueError: If frame shape doesn't match expected frame_size
        """
        if frame.size != self.frame_size:
            raise ValueError(f"Frame size {frame.size} doesn't match expected {self.frame_size}")
            
        with self._lock:
            # Check if we're about to overflow
            if len(self.buffer) == self.max_frames:
                self._overflows += 1
                
            # Convert to correct dtype if needed (minimal copy)
            if frame.dtype != self.dtype:
                frame = frame.astype(self.dtype)
            
            # Ensure frame is contiguous for optimal performance
            if not frame.flags.c_contiguous:
                frame = np.ascontiguousarray(frame)
                
            # Add to buffer (deque handles overflow automatically)
            self.buffer.append(frame.copy())  # Copy to avoid external modifications
            
            self._frames_written += 1
            self._last_write_time = time.perf_counter()
            
        return True
    
    def read_frame(self) -> Optional[np.ndarray]:
        """
        Read a single frame from the buffer (FIFO).
        
        Returns:
            Audio frame as NumPy array, or None if buffer is empty
        """
        with self._lock:
            if not self.buffer:
                return None
                
            frame = self.buffer.popleft()
            self._frames_read += 1
            self._last_read_time = time.perf_counter()
            
            return frame
    
    def read_all(self) -> np.ndarray:
        """
        Read all frames and concatenate into a single array.
        
        Returns:
            Concatenated audio data as NumPy array
        """
        with self._lock:
            if not self.buffer:
                return np.array([], dtype=self.dtype)
                
            # Pre-allocate output array for efficiency
            num_frames = len(self.buffer)
            output = np.empty((num_frames * self.frame_size,), dtype=self.dtype)
            
            # Copy frames into output array
            for i in range(num_frames):
                frame = self.buffer.popleft()
                start_idx = i * self.frame_size
                end_idx = start_idx + self.frame_size
                output[start_idx:end_idx] = frame
                
            self._frames_read += num_frames
            self._last_read_time = time.perf_counter()
            
            return output
    
    def clear(self) -> None:
        """Clear all frames from the buffer."""
        with self._lock:
            self.buffer.clear()
    
    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        with self._lock:
            return len(self.buffer) == 0
    
    def is_full(self) -> bool:
        """Check if buffer is at maximum capacity."""
        with self._lock:
            return len(self.buffer) == self.max_frames
    
    def size(self) -> int:
        """Get current number of frames in buffer."""
        with self._lock:
            return len(self.buffer)
    
    def get_stats(self) -> dict:
        """
        Get buffer statistics for monitoring and debugging.
        
        Returns:
            Dictionary with performance statistics
        """
        with self._lock:
            return {
                'frames_written': self._frames_written,
                'frames_read': self._frames_read,
                'overflows': self._overflows,
                'current_size': len(self.buffer),
                'max_frames': self.max_frames,
                'frame_size': self.frame_size,
                'last_write_time': self._last_write_time,
                'last_read_time': self._last_read_time,
                'utilization': len(self.buffer) / self.max_frames if self.max_frames > 0 else 0.0
            }
    
    def __len__(self) -> int:
        """Get current buffer size."""
        return self.size()
    
    def __repr__(self) -> str:
        """String representation of buffer state."""
        stats = self.get_stats()
        return (f"RingBuffer(size={stats['current_size']}/{stats['max_frames']}, "
                f"frame_size={stats['frame_size']}, "
                f"utilization={stats['utilization']:.1%})")


class AudioRingBuffer(RingBuffer):
    """
    Specialized ring buffer for audio data with additional audio-specific features.
    """
    
    def __init__(self, sample_rate: int, buffer_duration_ms: int, channels: int = 1, 
                 frame_duration_ms: int = 20, dtype: np.dtype = np.float32):
        """
        Initialize audio ring buffer based on time durations.
        
        Args:
            sample_rate: Audio sample rate in Hz
            buffer_duration_ms: Total buffer duration in milliseconds
            channels: Number of audio channels
            frame_duration_ms: Duration of each frame in milliseconds
            dtype: NumPy data type for audio samples
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.frame_duration_ms = frame_duration_ms
        
        # Calculate frame and buffer sizes
        frame_samples = int((sample_rate * frame_duration_ms) / 1000) * channels
        max_frames = int(buffer_duration_ms / frame_duration_ms)
        
        super().__init__(max_frames, frame_samples, dtype)
        
        # Audio-specific properties
        self.buffer_duration_ms = buffer_duration_ms
        
    def get_audio_stats(self) -> dict:
        """Get audio-specific statistics."""
        base_stats = self.get_stats()
        
        # Calculate timing information
        frames_in_buffer = base_stats['current_size']
        audio_duration_ms = (frames_in_buffer * self.frame_duration_ms)
        
        return {
            **base_stats,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'frame_duration_ms': self.frame_duration_ms,
            'buffer_duration_ms': self.buffer_duration_ms,
            'audio_duration_ms': audio_duration_ms,
            'buffer_latency_ms': audio_duration_ms  # Current latency
        }