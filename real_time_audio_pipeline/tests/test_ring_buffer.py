"""
Test suite for Ring Buffer implementation.

Critical tests for wraparound behavior, performance characteristics,
and thread safety required for ≤150ms p95 latency target.
"""

import gc
import os

# Import the ring buffer implementation
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.buffers import AudioRingBuffer, RingBuffer


class TestRingBuffer:
    """Test suite for basic RingBuffer functionality."""

    def test_ring_buffer_initialization(self):
        """Test ring buffer initialization with various parameters."""
        # Test basic initialization
        buffer = RingBuffer(max_frames=10, frame_size=320)
        assert buffer.max_frames == 10
        assert buffer.frame_size == 320
        assert buffer.size() == 0
        assert not buffer.is_full()

        # Test with different parameters
        buffer2 = RingBuffer(max_frames=100, frame_size=512, dtype=np.float64)
        assert buffer2.max_frames == 100
        assert buffer2.frame_size == 512
        assert buffer2.dtype == np.float64

    def test_ring_buffer_write_read(self):
        """Test basic write and read operations."""
        buffer = RingBuffer(max_frames=5, frame_size=4)

        # Test writing frames
        frame1 = np.array([1, 2, 3, 4], dtype=np.float32)
        frame2 = np.array([5, 6, 7, 8], dtype=np.float32)

        assert buffer.write(frame1)
        assert buffer.size() == 1

        assert buffer.write(frame2)
        assert buffer.size() == 2

        # Test reading frames
        read_frame = buffer.read_frame()
        np.testing.assert_array_equal(read_frame, frame1)
        assert buffer.size() == 1

        read_frame2 = buffer.read_frame()
        np.testing.assert_array_equal(read_frame2, frame2)
        assert buffer.size() == 0

    def test_ring_buffer_wraparound(self):
        """Test critical wraparound behavior when buffer is full."""
        buffer = RingBuffer(max_frames=3, frame_size=2)

        # Fill buffer to capacity
        frames = [
            np.array([1, 1], dtype=np.float32),
            np.array([2, 2], dtype=np.float32),
            np.array([3, 3], dtype=np.float32),
        ]

        for frame in frames:
            assert buffer.write(frame)

        assert buffer.is_full()
        assert buffer.size() == 3

        # Test wraparound - writing to full buffer should overwrite oldest
        frame4 = np.array([4, 4], dtype=np.float32)
        assert buffer.write(frame4)
        assert buffer.size() == 3  # Size should remain the same

        # First frame should now be frame2 (frame1 was overwritten)
        read_frame = buffer.read_frame()
        np.testing.assert_array_equal(read_frame, frames[1])

        # Second frame should be frame3
        read_frame = buffer.read_frame()
        np.testing.assert_array_equal(read_frame, frames[2])

        # Third frame should be frame4
        read_frame = buffer.read_frame()
        np.testing.assert_array_equal(read_frame, frame4)

        assert buffer.size() == 0

    def test_ring_buffer_overflow_handling(self):
        """Test overflow behavior and statistics tracking."""
        buffer = RingBuffer(max_frames=2, frame_size=3)

        # Fill buffer
        frame1 = np.array([1, 1, 1], dtype=np.float32)
        frame2 = np.array([2, 2, 2], dtype=np.float32)

        buffer.write(frame1)
        buffer.write(frame2)

        # Get initial stats
        initial_stats = buffer.get_stats()
        assert initial_stats['overflows'] == 0

        # Cause overflow
        frame3 = np.array([3, 3, 3], dtype=np.float32)
        buffer.write(frame3)  # This should cause an overflow

        # Check overflow was recorded
        stats = buffer.get_stats()
        assert stats['overflows'] == 1
        assert stats['frames_written'] == 3

    def test_ring_buffer_read_multiple(self):
        """Test reading multiple frames at once."""
        buffer = RingBuffer(max_frames=5, frame_size=2)

        # Write multiple frames
        frames = [
            np.array([1, 1], dtype=np.float32),
            np.array([2, 2], dtype=np.float32),
            np.array([3, 3], dtype=np.float32),
        ]

        for frame in frames:
            buffer.write(frame)

        # Read all frames
        all_frames = buffer.read_frames(3)
        assert len(all_frames) == 3

        for i, frame in enumerate(all_frames):
            np.testing.assert_array_equal(frame, frames[i])

        assert buffer.size() == 0

    def test_ring_buffer_performance(self):
        """Test ring buffer performance for latency requirements."""
        buffer = RingBuffer(max_frames=1000, frame_size=320)  # ~20 seconds at 16kHz

        # Test write performance
        frame = np.random.random(320).astype(np.float32)
        num_writes = 1000

        start_time = time.perf_counter()
        for _i in range(num_writes):
            buffer.write(frame)
        write_time = time.perf_counter() - start_time

        avg_write_time = write_time / num_writes
        assert avg_write_time < 0.001, f"Write time too slow: {avg_write_time*1000:.2f}ms"

        # Test read performance
        start_time = time.perf_counter()
        for _i in range(num_writes):
            buffer.read_frame()
        read_time = time.perf_counter() - start_time

        avg_read_time = read_time / num_writes
        assert avg_read_time < 0.001, f"Read time too slow: {avg_read_time*1000:.2f}ms"

    def test_ring_buffer_thread_safety(self):
        """Test ring buffer thread safety for concurrent access."""
        buffer = RingBuffer(max_frames=100, frame_size=10)

        # Shared state for tracking
        write_count = 0
        read_count = 0
        errors = []

        def writer_task():
            nonlocal write_count
            try:
                for i in range(50):
                    frame = np.full(10, i, dtype=np.float32)
                    if buffer.write(frame):
                        write_count += 1
                    time.sleep(0.001)  # Small delay to encourage contention
            except Exception as e:
                errors.append(f"Writer error: {e}")

        def reader_task():
            nonlocal read_count
            try:
                for _i in range(50):
                    if buffer.size() > 0:
                        frame = buffer.read_frame()
                        if frame is not None:
                            read_count += 1
                    time.sleep(0.001)  # Small delay
            except Exception as e:
                errors.append(f"Reader error: {e}")

        # Run concurrent threads
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []

            # Start multiple writers and readers
            for _ in range(2):
                futures.append(executor.submit(writer_task))
                futures.append(executor.submit(reader_task))

            # Wait for completion
            for future in futures:
                future.result()

        # Check for errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"

        # Verify reasonable operation counts
        assert write_count > 0, "No successful writes"
        # Note: read_count may be less than write_count due to timing


class TestAudioRingBuffer:
    """Test suite for AudioRingBuffer specialized functionality."""

    def test_audio_buffer_initialization(self):
        """Test audio-specific buffer initialization."""
        buffer = AudioRingBuffer(
            sample_rate=16000,
            buffer_duration_ms=4000,
            channels=1,
            frame_duration_ms=20
        )

        # Verify calculated parameters
        assert buffer.sample_rate == 16000
        assert buffer.channels == 1
        assert buffer.frame_duration_ms == 20
        assert buffer.frame_size == 320  # 16000 * 0.02 * 1
        assert buffer.max_frames == 200  # 4000ms / 20ms
        assert buffer.buffer_duration_ms == 4000

    def test_audio_buffer_timing_calculations(self):
        """Test audio timing and duration calculations."""
        buffer = AudioRingBuffer(
            sample_rate=16000,
            buffer_duration_ms=2000,
            channels=1,
            frame_duration_ms=10
        )

        # Add some frames
        frame = np.random.random(160).astype(np.float32)  # 10ms at 16kHz

        for _i in range(50):  # 500ms of audio
            buffer.write(frame)

        stats = buffer.get_audio_stats()

        # Check timing calculations
        assert stats['audio_duration_ms'] == 500.0
        assert 0.24 <= stats['utilization'] <= 0.26  # ~25% of 2000ms buffer

        # Check buffer latency
        assert stats['buffer_latency_ms'] == 500.0

    def test_audio_buffer_wraparound_timing(self):
        """Test timing calculations during wraparound."""
        buffer = AudioRingBuffer(
            sample_rate=16000,
            buffer_duration_ms=1000,  # 1 second buffer
            channels=1,
            frame_duration_ms=20  # 20ms frames
        )

        frame = np.random.random(320).astype(np.float32)

        # Fill buffer completely (50 frames * 20ms = 1000ms)
        for _i in range(50):
            buffer.write(frame)

        assert buffer.is_full()

        # Add more frames to trigger wraparound
        for _i in range(10):
            buffer.write(frame)

        stats = buffer.get_audio_stats()

        # Buffer should still show 1000ms of audio (full capacity)
        assert stats['audio_duration_ms'] == 1000.0
        assert stats['utilization'] == 1.0
        assert stats['overflows'] == 10

    def test_audio_buffer_performance_requirements(self):
        """Test that audio buffer meets performance requirements."""
        # Test with realistic RTAP parameters
        buffer = AudioRingBuffer(
            sample_rate=16000,
            buffer_duration_ms=4000,
            channels=1,
            frame_duration_ms=20
        )

        frame = np.random.random(320).astype(np.float32)

        # Performance test - should handle real-time audio streaming
        num_operations = 1000

        # Test sustained write performance
        start_time = time.perf_counter()
        for _i in range(num_operations):
            buffer.write(frame)
        write_duration = time.perf_counter() - start_time

        avg_write_time = write_duration / num_operations * 1000  # Convert to ms

        # Should be much faster than frame duration (20ms)
        assert avg_write_time < 1.0, f"Write time too slow: {avg_write_time:.3f}ms"

        # Test read performance
        start_time = time.perf_counter()
        for _i in range(min(num_operations, buffer.size())):
            buffer.read_frame()
        read_duration = time.perf_counter() - start_time

        avg_read_time = read_duration / min(num_operations, buffer.size()) * 1000
        assert avg_read_time < 1.0, f"Read time too slow: {avg_read_time:.3f}ms"


class TestRingBufferEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_buffer_operations(self):
        """Test operations on empty buffer."""
        buffer = RingBuffer(max_frames=5, frame_size=4)

        # Reading from empty buffer should return None
        assert buffer.read_frame() is None
        assert buffer.read_frames(3) == []
        assert buffer.size() == 0

        # Stats should be sensible
        stats = buffer.get_stats()
        assert stats['frames_written'] == 0
        assert stats['frames_read'] == 0

    def test_invalid_frame_sizes(self):
        """Test handling of incorrect frame sizes."""
        buffer = RingBuffer(max_frames=5, frame_size=4)

        # Frame too small
        small_frame = np.array([1, 2], dtype=np.float32)
        assert not buffer.write(small_frame)

        # Frame too large
        large_frame = np.array([1, 2, 3, 4, 5, 6], dtype=np.float32)
        assert not buffer.write(large_frame)

        # Correct size should work
        correct_frame = np.array([1, 2, 3, 4], dtype=np.float32)
        assert buffer.write(correct_frame)

    def test_memory_efficiency(self):
        """Test memory usage and garbage collection behavior."""
        # Create buffer and fill it
        buffer = RingBuffer(max_frames=100, frame_size=1000)

        # Fill with large frames
        large_frame = np.random.random(1000).astype(np.float32)

        for _i in range(100):
            buffer.write(large_frame)

        # Force garbage collection
        gc.collect()

        # Buffer should still function correctly
        assert buffer.size() == 100
        assert buffer.is_full()

        # Reading should work
        read_frame = buffer.read_frame()
        assert read_frame is not None
        assert len(read_frame) == 1000


# Performance benchmark test
def test_ring_buffer_latency_benchmark():
    """Benchmark ring buffer for RTAP latency requirements."""
    print("\n=== Ring Buffer Latency Benchmark ===")

    # Test with RTAP-realistic parameters
    buffer = AudioRingBuffer(
        sample_rate=16000,
        buffer_duration_ms=4000,
        channels=1,
        frame_duration_ms=20
    )

    frame = np.random.random(320).astype(np.float32)

    # Benchmark write operations
    num_tests = 10000
    write_times = []

    for _i in range(num_tests):
        start = time.perf_counter()
        buffer.write(frame)
        end = time.perf_counter()
        write_times.append((end - start) * 1000)  # Convert to ms

    # Calculate statistics
    avg_write_time = np.mean(write_times)
    p95_write_time = np.percentile(write_times, 95)
    max_write_time = np.max(write_times)

    print("Write Performance:")
    print(f"  Average: {avg_write_time:.3f}ms")
    print(f"  P95: {p95_write_time:.3f}ms")
    print(f"  Max: {max_write_time:.3f}ms")

    # Benchmark read operations
    read_times = []

    for _i in range(min(num_tests, buffer.size())):
        start = time.perf_counter()
        buffer.read_frame()
        end = time.perf_counter()
        read_times.append((end - start) * 1000)

    avg_read_time = np.mean(read_times)
    p95_read_time = np.percentile(read_times, 95)
    max_read_time = np.max(read_times)

    print("Read Performance:")
    print(f"  Average: {avg_read_time:.3f}ms")
    print(f"  P95: {p95_read_time:.3f}ms")
    print(f"  Max: {max_read_time:.3f}ms")

    # Assert performance requirements
    assert avg_write_time < 0.1, f"Average write time too slow: {avg_write_time:.3f}ms"
    assert p95_write_time < 0.5, f"P95 write time too slow: {p95_write_time:.3f}ms"
    assert avg_read_time < 0.1, f"Average read time too slow: {avg_read_time:.3f}ms"
    assert p95_read_time < 0.5, f"P95 read time too slow: {p95_read_time:.3f}ms"

    print("✅ Ring buffer meets latency requirements!")


if __name__ == "__main__":
    # Run the benchmark when executed directly
    test_ring_buffer_latency_benchmark()
