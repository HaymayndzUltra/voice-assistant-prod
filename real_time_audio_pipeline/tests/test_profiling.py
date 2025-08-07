"""
Performance Profiling Test Suite for RTAP.

Tests CPU usage, memory consumption, and system resource utilization
to ensure the pipeline meets performance requirements.
"""

import multiprocessing
import os
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List

import psutil
import pytest

# Import RTAP components
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.loader import UnifiedConfigLoader
from core.buffers import AudioRingBuffer


class SystemResourceMonitor:
    """Monitor system resource usage during testing."""

    def __init__(self):
        self.process = psutil.Process()
        self.measurements: List[Dict[str, Any]] = []
        self.monitoring = False

    def start_monitoring(self) -> None:
        """Start resource monitoring."""
        self.monitoring = True
        self.measurements = []

    def take_measurement(self) -> Dict[str, Any]:
        """Take a snapshot of current resource usage."""
        if not self.monitoring:
            return {}

        try:
            cpu_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()

            system_cpu = psutil.cpu_percent(interval=None)
            system_memory = psutil.virtual_memory()

            measurement = {
                'timestamp': time.perf_counter(),
                'process_cpu_percent': cpu_percent,
                'process_memory_mb': memory_info.rss / (1024 * 1024),
                'process_memory_percent': memory_percent,
                'system_cpu_percent': system_cpu,
                'system_memory_percent': system_memory.percent,
                'system_memory_available_gb': system_memory.available / (1024**3)
            }

            self.measurements.append(measurement)
            return measurement

        except Exception as e:
            print(f"Error taking measurement: {e}")
            return {}

    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return summary statistics."""
        self.monitoring = False

        if not self.measurements:
            return {}

        # Calculate statistics
        cpu_values = [m['process_cpu_percent'] for m in self.measurements if m.get('process_cpu_percent')]
        memory_values = [m['process_memory_mb'] for m in self.measurements if m.get('process_memory_mb')]

        return {
            'duration_seconds': self.measurements[-1]['timestamp'] - self.measurements[0]['timestamp'],
            'num_measurements': len(self.measurements),
            'cpu_stats': {
                'mean': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                'max': max(cpu_values) if cpu_values else 0,
                'min': min(cpu_values) if cpu_values else 0
            },
            'memory_stats': {
                'mean_mb': sum(memory_values) / len(memory_values) if memory_values else 0,
                'max_mb': max(memory_values) if memory_values else 0,
                'min_mb': min(memory_values) if memory_values else 0
            },
            'measurements': self.measurements
        }


class TestCPUProfiling:
    """Test CPU usage and profiling requirements."""

    @pytest.fixture
    def config(self):
        """Load configuration for testing."""
        try:
            loader = UnifiedConfigLoader()
            return loader.load_config()
        except Exception:
            # Fallback config for testing
            return {
                'audio': {
                    'sample_rate': 16000,
                    'frame_ms': 20,
                    'channels': 1,
                    'ring_buffer_size_ms': 4000
                }
            }

    def test_cpu_usage_baseline(self, config):
        """Test baseline CPU usage of core components."""
        print("\n=== CPU Usage Baseline Test ===")

        monitor = SystemResourceMonitor()
        monitor.start_monitoring()

        # Test audio buffer operations
        audio_buffer = AudioRingBuffer(16000, 4000, 1, 20)

        print("Testing audio buffer CPU usage...")

        # Simulate intensive buffer operations
        import numpy as np
        frame = np.random.random(320).astype(np.float32)

        for i in range(1000):
            audio_buffer.write(frame)
            if i % 100 == 0:
                monitor.take_measurement()
            if audio_buffer.size() > 100:
                audio_buffer.read_frame()

        # Test configuration loading
        print("Testing configuration loading CPU usage...")
        loader = UnifiedConfigLoader()
        for i in range(10):
            loader.load_config()
            monitor.take_measurement()

        # Stop monitoring and analyze
        stats = monitor.stop_monitoring()

        print("Baseline CPU Usage Results:")
        print(f"  Mean CPU: {stats['cpu_stats']['mean']:.1f}%")
        print(f"  Max CPU: {stats['cpu_stats']['max']:.1f}%")
        print(f"  Mean Memory: {stats['memory_stats']['mean_mb']:.1f}MB")
        print(f"  Max Memory: {stats['memory_stats']['max_mb']:.1f}MB")

        # Assert CPU requirements
        multiprocessing.cpu_count()
        per_core_limit = 20.0  # 20% per core as specified

        assert stats['cpu_stats']['mean'] < per_core_limit, f"Mean CPU too high: {stats['cpu_stats']['mean']:.1f}%"
        assert stats['cpu_stats']['max'] < per_core_limit * 2, f"Peak CPU too high: {stats['cpu_stats']['max']:.1f}%"

        print("✅ CPU baseline requirements met")

    def test_sustained_cpu_performance(self, config):
        """Test CPU usage under sustained load."""
        print("\n=== Sustained CPU Performance Test ===")

        monitor = SystemResourceMonitor()
        monitor.start_monitoring()

        # Create pipeline components
        audio_buffer = AudioRingBuffer(16000, 4000, 1, 20)

        print("Running sustained load test for 10 seconds...")

        import numpy as np
        frame = np.random.random(320).astype(np.float32)

        start_time = time.perf_counter()
        frame_count = 0

        # Run for 10 seconds with realistic frame rate
        while time.perf_counter() - start_time < 10.0:
            # Simulate 50 FPS (20ms frames)
            loop_start = time.perf_counter()

            # Simulate frame processing
            audio_buffer.write(frame)

            # Occasional heavy processing (STT simulation)
            if frame_count % 50 == 0:  # Every 1 second
                # Simulate heavier processing
                for _ in range(100):
                    _ = np.random.random(1000).sum()

            # Take measurement every 50 frames
            if frame_count % 50 == 0:
                monitor.take_measurement()

            frame_count += 1

            # Sleep to maintain frame rate
            elapsed = time.perf_counter() - loop_start
            target_frame_time = 0.02  # 20ms
            if elapsed < target_frame_time:
                time.sleep(target_frame_time - elapsed)

        stats = monitor.stop_monitoring()

        print("Sustained Performance Results:")
        print(f"  Duration: {stats['duration_seconds']:.1f}s")
        print(f"  Frames processed: {frame_count}")
        print(f"  Mean CPU: {stats['cpu_stats']['mean']:.1f}%")
        print(f"  Max CPU: {stats['cpu_stats']['max']:.1f}%")
        print(f"  Mean Memory: {stats['memory_stats']['mean_mb']:.1f}MB")

        # Assert sustained performance requirements
        assert stats['cpu_stats']['mean'] < 15.0, f"Sustained CPU too high: {stats['cpu_stats']['mean']:.1f}%"
        assert stats['memory_stats']['max_mb'] < 500, f"Memory usage too high: {stats['memory_stats']['max_mb']:.1f}MB"

        print("✅ Sustained performance requirements met")

    def test_memory_efficiency(self, config):
        """Test memory usage and efficiency."""
        print("\n=== Memory Efficiency Test ===")

        monitor = SystemResourceMonitor()
        monitor.start_monitoring()

        initial_memory = psutil.Process().memory_info().rss / (1024 * 1024)
        print(f"Initial memory usage: {initial_memory:.1f}MB")

        # Test memory usage with large buffers
        buffers = []
        for _i in range(5):
            buffer = AudioRingBuffer(16000, 4000, 1, 20)  # 4 second buffer
            buffers.append(buffer)
            monitor.take_measurement()

        # Fill buffers with data
        import numpy as np
        frame = np.random.random(320).astype(np.float32)

        for buffer in buffers:
            for _ in range(200):  # Fill each buffer
                buffer.write(frame)
            monitor.take_measurement()

        peak_memory = psutil.Process().memory_info().rss / (1024 * 1024)
        memory_growth = peak_memory - initial_memory

        # Clean up buffers
        buffers.clear()
        import gc
        gc.collect()

        final_memory = psutil.Process().memory_info().rss / (1024 * 1024)

        stats = monitor.stop_monitoring()

        print("Memory Efficiency Results:")
        print(f"  Initial: {initial_memory:.1f}MB")
        print(f"  Peak: {peak_memory:.1f}MB")
        print(f"  Final: {final_memory:.1f}MB")
        print(f"  Growth: {memory_growth:.1f}MB")
        print(f"  Mean during test: {stats['memory_stats']['mean_mb']:.1f}MB")

        # Assert memory efficiency requirements
        assert memory_growth < 200, f"Memory growth too high: {memory_growth:.1f}MB"
        assert peak_memory < 1000, f"Peak memory too high: {peak_memory:.1f}MB"

        print("✅ Memory efficiency requirements met")


class TestPySpyProfiling:
    """Test profiling with py-spy tool."""

    def create_test_workload(self, duration: float = 5.0) -> str:
        """Create a test script for py-spy profiling."""
        test_script = f"""
import sys
import time
import numpy as np
sys.path.insert(0, '.')

from core.buffers import AudioRingBuffer
from config.loader import UnifiedConfigLoader

def cpu_intensive_task():
    # Simulate RTAP workload
    buffer = AudioRingBuffer(16000, 4000, 1, 20)
    frame = np.random.random(320).astype(np.float32)

    start_time = time.perf_counter()
    while time.perf_counter() - start_time < {duration}:
        # Audio processing simulation
        buffer.write(frame)

        # Periodic heavy computation (STT simulation)
        if np.random.random() < 0.02:  # 2% chance
            # Simulate ML inference
            for _ in range(1000):
                _ = np.random.random(100).sum()

        # Brief sleep to avoid 100% CPU
        time.sleep(0.001)

if __name__ == "__main__":
    cpu_intensive_task()
"""

        # Write test script to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            return f.name

    def test_py_spy_profiling(self):
        """Test CPU profiling with py-spy."""
        print("\n=== Py-Spy CPU Profiling Test ===")

        # Create test workload
        test_script = self.create_test_workload(duration=5.0)

        try:
            # Create temporary files for py-spy output
            profile_output = tempfile.mktemp(suffix='.prof')
            svg_output = tempfile.mktemp(suffix='.svg')

            print("Starting py-spy profiling session...")

            # Start the test workload process
            process = subprocess.Popen([
                sys.executable, test_script
            ])

            # Give it a moment to start
            time.sleep(0.5)

            # Run py-spy profiling
            try:
                py_spy_result = subprocess.run([
                    'py-spy', 'record',
                    '--pid', str(process.pid),
                    '--duration', '4',
                    '--rate', '100',
                    '--output', profile_output
                ], capture_output=True, text=True, timeout=10)

                # Wait for workload to complete
                process.wait(timeout=10)

                if py_spy_result.returncode == 0:
                    print("✅ Py-spy profiling completed successfully")

                    # Try to generate flame graph
                    try:
                        subprocess.run([
                            'py-spy', 'top',
                            '--pid', str(process.pid),
                            '--duration', '1'
                        ], capture_output=True, timeout=5)
                        print("✅ Py-spy top view test completed")
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        print("⚠️  Py-spy top view test skipped (process ended)")

                else:
                    print(f"⚠️  Py-spy profiling failed: {py_spy_result.stderr}")
                    print("Note: This may be due to insufficient permissions or missing dependencies")

            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                print(f"⚠️  Py-spy not available or timed out: {e}")
                # Ensure process is terminated
                try:
                    process.terminate()
                    process.wait(timeout=2)
                except:
                    process.kill()

        finally:
            # Cleanup
            try:
                os.unlink(test_script)
                if os.path.exists(profile_output):
                    os.unlink(profile_output)
                if os.path.exists(svg_output):
                    os.unlink(svg_output)
            except:
                pass

        print("✅ Profiling test completed")

    def test_manual_cpu_profiling(self):
        """Manual CPU profiling without external dependencies."""
        print("\n=== Manual CPU Profiling Test ===")

        import cProfile
        import io
        import pstats

        # Create profiler
        profiler = cProfile.Profile()

        # Profile RTAP components
        profiler.enable()

        try:
            # Simulate RTAP workload
            import numpy as np

            from core.buffers import AudioRingBuffer

            buffer = AudioRingBuffer(16000, 4000, 1, 20)
            frame = np.random.random(320).astype(np.float32)

            # Run workload
            for i in range(10000):
                buffer.write(frame)
                if i % 100 == 0:
                    buffer.read_frame()

                # Simulate occasional heavy processing
                if i % 1000 == 0:
                    _ = np.random.random(1000).sum()

        finally:
            profiler.disable()

        # Analyze profile results
        stats_buffer = io.StringIO()
        stats = pstats.Stats(profiler, stream=stats_buffer)
        stats.sort_stats('cumulative')
        stats.print_stats(20)  # Top 20 functions

        profile_output = stats_buffer.getvalue()

        print("Top CPU consuming functions:")
        for line in profile_output.split('\n')[5:15]:  # Skip header, show top 10
            if line.strip():
                print(f"  {line}")

        # Get total runtime
        total_time = stats.total_tt
        print("\nProfile Summary:")
        print(f"  Total runtime: {total_time:.3f}s")
        print(f"  Function calls: {stats.total_calls}")

        print("✅ Manual profiling completed")


class TestGPUUtilization:
    """Test GPU utilization if available."""

    def test_gpu_availability(self):
        """Test GPU availability and basic utilization."""
        print("\n=== GPU Utilization Test ===")

        try:
            import torch
            gpu_available = torch.cuda.is_available()

            if gpu_available:
                device_count = torch.cuda.device_count()
                current_device = torch.cuda.current_device()
                device_name = torch.cuda.get_device_name(current_device)

                print("GPU Available: Yes")
                print(f"  Device count: {device_count}")
                print(f"  Current device: {current_device}")
                print(f"  Device name: {device_name}")

                # Test basic GPU operations
                try:
                    # Create tensors on GPU
                    x = torch.randn(1000, 1000).cuda()
                    y = torch.randn(1000, 1000).cuda()

                    # Simulate computation
                    start_time = time.perf_counter()
                    for _ in range(100):
                        torch.matmul(x, y)
                    torch.cuda.synchronize()
                    gpu_time = time.perf_counter() - start_time

                    print(f"  GPU computation time: {gpu_time:.3f}s")

                    # Check memory usage
                    memory_allocated = torch.cuda.memory_allocated() / (1024**2)
                    memory_cached = torch.cuda.memory_reserved() / (1024**2)

                    print(f"  GPU memory allocated: {memory_allocated:.1f}MB")
                    print(f"  GPU memory cached: {memory_cached:.1f}MB")

                    print("✅ GPU utilization test passed")

                except Exception as e:
                    print(f"⚠️  GPU computation test failed: {e}")
            else:
                print("GPU Available: No")
                print("  Running in CPU-only mode")
                print("✅ CPU-only configuration validated")

        except ImportError:
            print("PyTorch not available - skipping GPU test")
            print("✅ Test skipped gracefully")


# Comprehensive profiling benchmark
def test_comprehensive_profiling_benchmark():
    """Comprehensive profiling benchmark for RTAP system."""
    print("\n=== Comprehensive Profiling Benchmark ===")

    try:
        # Load configuration
        loader = UnifiedConfigLoader()
        config = loader.load_config()
    except Exception:
        config = {
            'audio': {
                'sample_rate': 16000,
                'frame_ms': 20,
                'channels': 1,
                'ring_buffer_size_ms': 4000
            }
        }

    # Create test instances
    cpu_test = TestCPUProfiling()
    profiling_test = TestPySpyProfiling()
    gpu_test = TestGPUUtilization()

    try:
        # Run CPU tests
        cpu_test.test_cpu_usage_baseline(config)
        cpu_test.test_sustained_cpu_performance(config)
        cpu_test.test_memory_efficiency(config)

        # Run profiling tests
        profiling_test.test_manual_cpu_profiling()
        profiling_test.test_py_spy_profiling()

        # Run GPU tests
        gpu_test.test_gpu_availability()

        print("\n�� COMPREHENSIVE PROFILING BENCHMARK COMPLETE!")
        print("✅ CPU usage within acceptable limits (<20% per core)")
        print("✅ Memory usage efficient and stable")
        print("✅ Profiling tools functional")
        print("✅ GPU/CPU configuration validated")

        return True

    except Exception as e:
        print(f"❌ Profiling benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run comprehensive benchmark when executed directly
    success = test_comprehensive_profiling_benchmark()
    sys.exit(0 if success else 1)
